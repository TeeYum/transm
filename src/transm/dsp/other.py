"""Guitar/other stem processing chain — mid boost, high-shelf rolloff, stereo width."""

from __future__ import annotations

import math

import numpy as np
from pedalboard import HighShelfFilter, PeakFilter, Pedalboard

from transm.dsp.gate import noise_gate
from transm.types import AudioBuffer, PresetParams


def process_other(buffer: AudioBuffer, params: PresetParams) -> AudioBuffer:
    """Guitar/other stem processing chain. Gain params scaled by intensity.

    Chain order:
    1. Mid-boost EQ (add body in mid-scoop region)
    2. High-shelf rolloff (reduce fizz above ~10 kHz)
    3. M/S stereo width adjustment
    4. Level normalization (prevent clipping)
    """
    intensity = params.global_params.intensity
    if intensity == 0.0:
        return buffer

    other = params.other
    sr = buffer.sample_rate

    # 0. Noise gate — silence Demucs artifacts in quiet passages
    gated = noise_gate(buffer, threshold_db=params.global_params.gate_threshold_db)

    # 1 & 2. EQ via pedalboard
    # Mid boost: single PeakFilter at geometric mean of the range with wide Q
    mid_center_hz = math.sqrt(other.mid_boost_low_hz * other.mid_boost_high_hz)

    board = Pedalboard(
        [
            # 1. Mid-boost — add body in the mid-scoop region
            PeakFilter(
                cutoff_frequency_hz=mid_center_hz,
                gain_db=other.mid_boost_gain_db * intensity,
                q=0.7,  # wide Q to cover the full mid range
            ),
            # 2. High-shelf rolloff — reduce fizz
            HighShelfFilter(
                cutoff_frequency_hz=other.high_shelf_freq_hz,
                gain_db=other.high_shelf_gain_db * intensity,
            ),
        ]
    )

    # Pedalboard expects (channels, samples) float32; we store (samples, channels)
    data = gated.data.copy()
    processed = board(data.T, sample_rate=float(sr)).T

    # 3. M/S stereo width (only meaningful for stereo signals)
    if processed.shape[1] >= 2:
        left = processed[:, 0]
        right = processed[:, 1]

        mid = (left + right) / 2.0
        side = (left - right) / 2.0

        # Lerp width toward target based on intensity
        width = 1.0 + (other.stereo_width - 1.0) * intensity
        side_scaled = side * width

        processed[:, 0] = mid + side_scaled
        processed[:, 1] = mid - side_scaled

    # 4. Level normalization — prevent clipping
    peak = np.max(np.abs(processed))
    if peak > 0.95:
        processed = processed * (0.95 / peak)

    return AudioBuffer(data=processed.astype(np.float32), sample_rate=sr)
