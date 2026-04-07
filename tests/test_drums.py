"""Tests for the drum processing chain."""

from __future__ import annotations

import numpy as np

from tests.conftest import generate_crushed_drum_pattern
from transm.dsp.drums import process_drums
from transm.types import DrumsParams, GlobalParams, PresetParams


def _make_preset(intensity: float = 0.35) -> PresetParams:
    """Create a PresetParams with default values and the given intensity."""
    return PresetParams(
        name="test-drums",
        global_params=GlobalParams(intensity=intensity),
        drums=DrumsParams(),
    )


def test_process_drums_increases_dynamics(crushed_drums):
    """Processing crushed drums should increase the crest factor (peak-to-RMS ratio)."""
    params = _make_preset(intensity=0.35)

    input_data = crushed_drums.data
    output = process_drums(crushed_drums, params)
    output_data = output.data

    # Crest factor = peak / RMS (in linear domain)
    def crest_factor(data):
        rms = np.sqrt(np.mean(data**2))
        peak = np.max(np.abs(data))
        if rms == 0:
            return 0.0
        return peak / rms

    input_crest = crest_factor(input_data)
    output_crest = crest_factor(output_data)

    assert output_crest > input_crest, (
        f"Crest factor should increase: input={input_crest:.3f}, output={output_crest:.3f}"
    )


def test_process_drums_preserves_shape(crushed_drums):
    """Output shape and sample rate must match input."""
    params = _make_preset(intensity=0.35)
    output = process_drums(crushed_drums, params)

    assert output.data.shape == crushed_drums.data.shape
    assert output.sample_rate == crushed_drums.sample_rate


def test_process_drums_zero_intensity(crushed_drums):
    """With intensity=0, output should equal input (early exit)."""
    params = _make_preset(intensity=0.0)
    output = process_drums(crushed_drums, params)

    np.testing.assert_array_equal(output.data, crushed_drums.data)
    assert output.sample_rate == crushed_drums.sample_rate


def test_process_drums_no_clipping(crushed_drums):
    """Output max absolute value should not exceed 1.0."""
    params = _make_preset(intensity=0.35)
    output = process_drums(crushed_drums, params)

    max_abs = np.max(np.abs(output.data))
    assert max_abs <= 1.0, f"Output clipped: max abs = {max_abs:.6f}"
