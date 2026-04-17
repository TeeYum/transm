"""Bass processing chain — high-pass, mud cut, harmonic boost, and compression."""

from __future__ import annotations

import numpy as np
from pedalboard import Compressor, HighpassFilter, PeakFilter, Pedalboard

from transm.dsp.gate import noise_gate
from transm.types import AudioBuffer, PresetParams


def process_bass(buffer: AudioBuffer, params: PresetParams) -> AudioBuffer:
    """Bass processing chain. Gain params scaled by intensity.

    Chain order:
    1. High-pass filter (remove sub-rumble below ~30 Hz)
    2. Mud cut (narrow cut at 200-300 Hz)
    3. Harmonic boost (add clarity at 800-1200 Hz)
    4. Light compression (even out bass dynamics)
    """
    intensity = params.global_params.intensity
    if intensity == 0.0:
        return buffer

    bass = params.bass
    sr = buffer.sample_rate

    # 0. Noise gate — silence Demucs artifacts in quiet passages
    gated = noise_gate(buffer, threshold_db=params.global_params.gate_threshold_db)

    board = Pedalboard(
        [
            # 1. High-pass filter — remove sub-rumble
            HighpassFilter(cutoff_frequency_hz=bass.hp_freq_hz),
            # 2. Mud cut — narrow cut in the mud range
            PeakFilter(
                cutoff_frequency_hz=bass.mud_cut_freq_hz,
                gain_db=bass.mud_cut_gain_db * intensity,
                q=bass.mud_cut_q,
            ),
            # 3. Harmonic boost — add clarity
            PeakFilter(
                cutoff_frequency_hz=bass.harmonic_freq_hz,
                gain_db=bass.harmonic_gain_db * intensity,
                q=1.5,
            ),
            # 4. Light compression — even out dynamics
            Compressor(
                threshold_db=-20.0,
                ratio=bass.comp_ratio,
                attack_ms=bass.comp_attack_ms,
                release_ms=200.0,
            ),
        ]
    )

    # Pedalboard expects (channels, samples) float32; we store (samples, channels)
    data = gated.data.copy()
    processed = board(data.T, sample_rate=float(sr)).T

    return AudioBuffer(data=processed.astype(np.float32), sample_rate=sr)
