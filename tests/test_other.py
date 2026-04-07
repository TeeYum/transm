"""Tests for the guitar/other processing chain."""

from __future__ import annotations

import numpy as np

from tests.conftest import generate_sine, SR
from transm.dsp.other import process_other
from transm.types import AudioBuffer, GlobalParams, OtherParams, PresetParams


def _make_preset(intensity: float = 0.35) -> PresetParams:
    """Create a PresetParams with default values and the given intensity."""
    return PresetParams(
        name="test-other",
        global_params=GlobalParams(intensity=intensity),
        other=OtherParams(),
    )


def test_process_other_preserves_shape():
    """Output shape and sample rate must match input."""
    buf = generate_sine(freq_hz=1000.0, duration_s=1.0)
    params = _make_preset(intensity=0.35)
    output = process_other(buf, params)

    assert output.data.shape == buf.data.shape
    assert output.sample_rate == buf.sample_rate


def test_process_other_zero_intensity():
    """With intensity=0, output should equal input (early exit)."""
    buf = generate_sine(freq_hz=1000.0, duration_s=1.0)
    params = _make_preset(intensity=0.0)
    output = process_other(buf, params)

    np.testing.assert_array_equal(output.data, buf.data)
    assert output.sample_rate == buf.sample_rate


def test_process_other_stereo_width():
    """With stereo_width=1.5, the side channel energy should increase."""
    # Create a stereo signal where L and R differ (different frequencies)
    t = np.arange(int(SR * 1.0), dtype=np.float32) / SR
    left = (0.5 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)
    right = (0.5 * np.sin(2 * np.pi * 660.0 * t)).astype(np.float32)
    data = np.column_stack([left, right])
    buf = AudioBuffer(data=data, sample_rate=SR)

    params = PresetParams(
        name="test-other-width",
        global_params=GlobalParams(intensity=1.0),
        other=OtherParams(stereo_width=1.5),
    )
    output = process_other(buf, params)

    # Measure side channel energy before and after
    input_side = (buf.data[:, 0] - buf.data[:, 1]) / 2.0
    output_side = (output.data[:, 0] - output.data[:, 1]) / 2.0

    input_side_energy = np.sqrt(np.mean(input_side**2))
    output_side_energy = np.sqrt(np.mean(output_side**2))

    assert output_side_energy > input_side_energy, (
        f"Side channel energy should increase with width=1.5: "
        f"input={input_side_energy:.6f}, output={output_side_energy:.6f}"
    )


def test_process_other_no_clipping():
    """Output max absolute value should not exceed 1.0."""
    buf = generate_sine(freq_hz=1000.0, duration_s=1.0, amplitude=0.9)
    params = _make_preset(intensity=1.0)
    output = process_other(buf, params)

    max_abs = np.max(np.abs(output.data))
    assert max_abs <= 1.0, f"Output clipped: max abs = {max_abs:.6f}"
