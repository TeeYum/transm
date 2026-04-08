"""Vocal processing chain — de-essing, expansion, presence EQ, and level adjust."""

from __future__ import annotations

import numpy as np
from pedalboard import PeakFilter, Pedalboard

from transm.dsp.common import db_to_linear
from transm.dsp.deesser import deess
from transm.dsp.expander import expand_downward
from transm.types import AudioBuffer, PresetParams


def process_vocals(buffer: AudioBuffer, params: PresetParams) -> AudioBuffer:
    """Vocal processing chain. All gains scaled by intensity.

    Chain order:
    1. De-esser (reduce sibilance)
    2. Light downward expander (fixed threshold, configurable ratio)
    3. Presence EQ (pedalboard PeakFilter)
    4. Level adjust (linear gain)
    """
    intensity = params.global_params.intensity
    if intensity == 0.0:
        return buffer

    vocals = params.vocals
    sr = buffer.sample_rate

    # 1. De-esser
    result = deess(
        buffer,
        freq_low=vocals.deesser_freq_low_hz,
        freq_high=vocals.deesser_freq_high_hz,
    )

    # 2. Light downward expander (fixed threshold at -35 dB)
    result = expand_downward(
        result,
        threshold_db=-35.0,
        ratio=vocals.expander_ratio,
    )

    # 3. Presence EQ via pedalboard
    board = Pedalboard(
        [
            PeakFilter(
                cutoff_frequency_hz=vocals.presence_freq_hz,
                gain_db=vocals.presence_gain_db * intensity,
                q=1.0,
            ),
        ]
    )

    data = result.data.copy()
    processed = board(data.T, sample_rate=float(sr)).T

    # 4. Level adjust
    gain_linear = db_to_linear(vocals.level_adjust_db * intensity)
    processed = processed * gain_linear

    return AudioBuffer(data=processed.astype(np.float32), sample_rate=sr)
