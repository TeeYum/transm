"""Single-track audio capture via system loopback recording.

Records audio from a virtual loopback device (e.g., BlackHole on macOS)
while a streaming service plays the track. Saves as tagged FLAC.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path

import numpy as np
import requests
import soundfile as sf

from transm.types import AudioBuffer, TrackMetadata

logger = logging.getLogger(__name__)

_SPOTIFY_TRACK_PATTERN = re.compile(
    r"(?:spotify:track:|https?://open\.spotify\.com/track/)([a-zA-Z0-9]+)"
)


def parse_spotify_url(url: str) -> str:
    """Extract track ID from a Spotify URL or URI.

    Accepts:
        https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8
        https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8?si=...
        spotify:track:4PTG3Z6ehGkBFwjybzWkR8
    """
    match = _SPOTIFY_TRACK_PATTERN.search(url)
    if not match:
        msg = f"Could not parse Spotify track ID from: {url}"
        raise ValueError(msg)
    return match.group(1)


def get_track_metadata(track_id: str, token: str) -> TrackMetadata:
    """Fetch track metadata from the Spotify API."""
    resp = requests.get(
        f"https://api.spotify.com/v1/tracks/{track_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    artists = ", ".join(a["name"] for a in data.get("artists", []))
    album = data.get("album", {})

    return TrackMetadata(
        title=data.get("name", "Unknown"),
        artist=artists,
        album=album.get("name", "Unknown"),
        album_artist=", ".join(a["name"] for a in album.get("artists", [])),
        track_number=data.get("track_number", 0),
        disc_number=data.get("disc_number", 1),
        duration_ms=data.get("duration_ms", 0),
        isrc=data.get("external_ids", {}).get("isrc", ""),
        source_uri=f"spotify:track:{track_id}",
        release_date=album.get("release_date", ""),
        genre=[],  # Spotify moved genres to the artist endpoint
        album_art_url=(album.get("images", [{}])[0].get("url", "") if album.get("images") else ""),
    )


def start_playback(track_uri: str, token: str) -> None:
    """Start playback of a track on the user's active Spotify device."""
    resp = requests.put(
        "https://api.spotify.com/v1/me/player/play",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"uris": [track_uri]},
        timeout=10,
    )
    if resp.status_code == 404:
        msg = (
            "No active Spotify device found. "
            "Open Spotify and start playing something first."
        )
        raise RuntimeError(msg)
    resp.raise_for_status()


def pause_playback(token: str) -> None:
    """Pause playback on the user's active Spotify device."""
    import contextlib

    with contextlib.suppress(Exception):
        requests.put(
            "https://api.spotify.com/v1/me/player/pause",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )


def record_loopback(
    device_name: str,
    duration_s: float,
    sample_rate: int = 44100,
) -> AudioBuffer:
    """Record audio from a loopback device for the specified duration.

    Returns an AudioBuffer with the captured audio.
    """
    try:
        import soundcard  # type: ignore[import-untyped]
    except ImportError as e:
        msg = (
            "Audio capture requires the 'soundcard' package. "
            "Install with: pip install transm[capture]"
        )
        raise ImportError(msg) from e

    # Find the loopback device
    mics = soundcard.all_microphones(include_loopback=True)
    device = None
    for mic in mics:
        if device_name.lower() in mic.name.lower():
            device = mic
            break

    if device is None:
        available = [m.name for m in mics]
        msg = (
            f"Loopback device '{device_name}' not found. "
            f"Available devices: {available}"
        )
        raise RuntimeError(msg)

    num_frames = int(duration_s * sample_rate)
    logger.info(
        "Recording from '%s' for %.1fs at %d Hz...",
        device.name,
        duration_s,
        sample_rate,
    )

    with device.recorder(samplerate=sample_rate, channels=2) as recorder:
        data = recorder.record(numframes=num_frames)

    return AudioBuffer(data=data.astype(np.float32), sample_rate=sample_rate)


def list_loopback_devices() -> list[str]:
    """List available loopback/input audio devices."""
    try:
        import soundcard  # type: ignore[import-untyped]
    except ImportError:
        return ["(soundcard not installed — pip install transm[capture])"]

    mics = soundcard.all_microphones(include_loopback=True)
    return [m.name for m in mics]


def trim_silence(
    buffer: AudioBuffer,
    threshold_db: float = -50.0,
    min_samples: int = 1024,
) -> AudioBuffer:
    """Trim leading and trailing silence from an AudioBuffer.

    Silence is defined as frames below threshold_db RMS.
    """
    data = buffer.data
    threshold_linear = 10.0 ** (threshold_db / 20.0)

    # Compute per-frame RMS (mono sum)
    mono = np.mean(np.abs(data), axis=1)

    # Find first and last non-silent sample
    above = np.where(mono > threshold_linear)[0]
    if len(above) == 0:
        # Entire buffer is silence
        return buffer

    start = max(0, above[0] - min_samples)
    end = min(len(data), above[-1] + min_samples)

    return AudioBuffer(data=data[start:end].copy(), sample_rate=buffer.sample_rate)


def save_flac_with_metadata(
    buffer: AudioBuffer,
    metadata: TrackMetadata,
    output_dir: Path,
) -> Path:
    """Save AudioBuffer as a tagged FLAC file.

    Filename: {Artist} - {Title}.flac
    """
    # Sanitize filename
    safe_artist = re.sub(r'[<>:"/\\|?*]', "_", metadata.artist)
    safe_title = re.sub(r'[<>:"/\\|?*]', "_", metadata.title)
    filename = f"{safe_artist} - {safe_title}.flac"

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    # Write FLAC via soundfile
    sf.write(
        str(output_path),
        buffer.data,
        buffer.sample_rate,
        format="FLAC",
        subtype="PCM_24",
    )

    # Tag with metadata via mutagen
    try:
        from mutagen.flac import FLAC

        audio = FLAC(str(output_path))
        audio["title"] = metadata.title
        audio["artist"] = metadata.artist
        audio["album"] = metadata.album
        if metadata.album_artist:
            audio["albumartist"] = metadata.album_artist
        if metadata.track_number:
            audio["tracknumber"] = str(metadata.track_number)
        if metadata.disc_number:
            audio["discnumber"] = str(metadata.disc_number)
        if metadata.release_date:
            audio["date"] = metadata.release_date
        if metadata.isrc:
            audio["isrc"] = metadata.isrc
        audio.save()
    except ImportError:
        logger.warning("mutagen not installed — FLAC saved without metadata tags.")

    return output_path


def capture_track(
    spotify_url: str,
    output_dir: Path | str | None = None,
    device_name: str = "BlackHole 2ch",
    token: str | None = None,
) -> Path:
    """Capture a single track from Spotify via loopback recording.

    Steps:
    1. Parse Spotify URL
    2. Get track metadata
    3. Start playback
    4. Record loopback for track duration + buffer
    5. Stop playback
    6. Trim silence
    7. Save as tagged FLAC
    """
    if output_dir is None:
        output_dir = Path.home() / "Music" / "transm-captures"
    output_dir = Path(output_dir)

    # 1. Auth
    if token is None:
        from transm.spotify_auth import get_access_token

        token = get_access_token()

    # 2. Parse URL and get metadata
    track_id = parse_spotify_url(spotify_url)
    metadata = get_track_metadata(track_id, token)
    duration_s = metadata.duration_ms / 1000.0

    logger.info(
        "Capturing: %s - %s (%.0fs)",
        metadata.artist,
        metadata.title,
        duration_s,
    )

    # 3. Start playback
    start_playback(metadata.source_uri, token)
    time.sleep(0.5)  # Small delay for playback to begin

    # 4. Record with buffer
    buffer_s = 2.0
    recording = record_loopback(
        device_name=device_name,
        duration_s=duration_s + buffer_s,
        sample_rate=44100,
    )

    # 5. Stop playback
    pause_playback(token)

    # 6. Trim silence
    trimmed = trim_silence(recording)

    # 7. Save
    output_path = save_flac_with_metadata(trimmed, metadata, output_dir)
    logger.info("Saved: %s", output_path)

    return output_path
