"""Per-stem noise gate — silence Demucs separation artifacts in quiet passages."""

from __future__ import annotations

import numpy as np

from transm.dsp.common import (
    apply_gain_curve,
    envelope_follower,
    linear_to_db,
    smooth_gain,
    time_to_coeff,
)
from transm.types import AudioBuffer


def noise_gate(
    buffer: AudioBuffer,
    threshold_db: float = -50.0,
    attack_ms: float = 0.5,
    release_ms: float = 50.0,
    range_db: float = -80.0,
) -> AudioBuffer:
    """Apply a noise gate to silence low-level artifacts.

    Algorithm
    ---------
    1. Compute envelope → convert to dB.
    2. Below threshold: apply ``range_db`` attenuation (hard gate).
    3. Smooth gain curve to prevent clicks.

    Stereo handling: envelope from mid (L+R)/2, gain applied to both channels.
    """
    sr = buffer.sample_rate
    data = buffer.data

    # --- mono analysis signal ---
    analysis = (data[:, 0] + data[:, 1]) / 2.0 if data.shape[1] >= 2 else data[:, 0].copy()
    analysis = analysis.astype(np.float64)

    # --- envelope ---
    att = time_to_coeff(attack_ms, sr)
    rel = time_to_coeff(release_ms, sr)
    env = envelope_follower(analysis, att, rel)
    env_db = np.asarray(linear_to_db(env, floor_db=-120.0))

    # --- gate: open above threshold, attenuate below ---
    gain_db = np.where(env_db >= threshold_db, 0.0, range_db).astype(np.float64)

    # --- smooth to prevent clicks ---
    gain_db_smoothed = smooth_gain(gain_db, cutoff_hz=100.0, sr=sr).astype(np.float32)

    # --- apply ---
    result = apply_gain_curve(data, gain_db_smoothed)
    return AudioBuffer(data=result, sample_rate=sr)
