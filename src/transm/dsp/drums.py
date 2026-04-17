"""Drum processing chain — transient shaping, expansion, and EQ."""

from __future__ import annotations

import numpy as np
from pedalboard import HighShelfFilter, LowShelfFilter, Pedalboard

from transm.dsp.expander import expand_downward
from transm.dsp.gate import noise_gate
from transm.dsp.transient_shaper import shape_transients
from transm.types import AudioBuffer, PresetParams


def process_drums(buffer: AudioBuffer, params: PresetParams) -> AudioBuffer:
    """Drum processing chain. All gains scaled by intensity.

    Chain order:
    1. Transient shaper (attack boost + sustain cut)
    2. Downward expander (restore dynamics)
    3. High-shelf EQ (tame cymbals)
    4. Low-shelf EQ (kick weight)
    """
    intensity = params.global_params.intensity
    if intensity == 0.0:
        return buffer

    drums = params.drums
    sr = buffer.sample_rate

    # 0. Noise gate — silence Demucs artifacts in quiet passages
    result = noise_gate(buffer, threshold_db=params.global_params.gate_threshold_db)

    # 1. Transient shaper
    result = shape_transients(
        result,
        attack_gain_db=drums.transient_attack_db * intensity,
        sustain_gain_db=drums.transient_sustain_db * intensity,
    )

    # 2. Downward expander
    result = expand_downward(
        result,
        threshold_db=drums.expander_threshold_db,
        ratio=drums.expander_ratio,
    )

    # 3 & 4. EQ via pedalboard
    board = Pedalboard(
        [
            HighShelfFilter(
                cutoff_frequency_hz=drums.high_shelf_freq_hz,
                gain_db=drums.high_shelf_gain_db * intensity,
            ),
            LowShelfFilter(
                cutoff_frequency_hz=drums.low_shelf_freq_hz,
                gain_db=drums.low_shelf_gain_db * intensity,
            ),
        ]
    )

    # Pedalboard expects (channels, samples) float32; we store (samples, channels)
    data = result.data.copy()
    processed = board(data.T, sample_rate=float(sr)).T

    return AudioBuffer(data=processed.astype(np.float32), sample_rate=sr)
