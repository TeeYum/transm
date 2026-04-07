"""Tests for the bass processing chain."""

from __future__ import annotations

import numpy as np

from tests.conftest import generate_sine, SR
from transm.dsp.bass import process_bass
from transm.types import BassParams, GlobalParams, PresetParams


def _make_preset(intensity: float = 0.35) -> PresetParams:
    """Create a PresetParams with default values and the given intensity."""
    return PresetParams(
        name="test-bass",
        global_params=GlobalParams(intensity=intensity),
        bass=BassParams(),
    )


def test_process_bass_preserves_shape():
    """Output shape and sample rate must match input."""
    buf = generate_sine(freq_hz=100.0, duration_s=1.0)
    params = _make_preset(intensity=0.35)
    output = process_bass(buf, params)

    assert output.data.shape == buf.data.shape
    assert output.sample_rate == buf.sample_rate


def test_process_bass_zero_intensity():
    """With intensity=0, output should equal input (early exit)."""
    buf = generate_sine(freq_hz=100.0, duration_s=1.0)
    params = _make_preset(intensity=0.0)
    output = process_bass(buf, params)

    np.testing.assert_array_equal(output.data, buf.data)
    assert output.sample_rate == buf.sample_rate


def test_process_bass_removes_sub_bass():
    """High-pass at 30 Hz should reduce 20 Hz energy while keeping 100 Hz."""
    t = np.arange(int(SR * 1.0), dtype=np.float32) / SR
    # Mix: 20 Hz sub-bass + 100 Hz bass fundamental
    sub = 0.5 * np.sin(2 * np.pi * 20.0 * t)
    fundamental = 0.5 * np.sin(2 * np.pi * 100.0 * t)
    mono = (sub + fundamental).astype(np.float32)
    data = np.column_stack([mono, mono])
    from transm.types import AudioBuffer

    buf = AudioBuffer(data=data, sample_rate=SR)
    params = _make_preset(intensity=1.0)
    output = process_bass(buf, params)

    # Measure 20 Hz energy before and after via correlation with pure 20 Hz sine
    ref_20 = np.sin(2 * np.pi * 20.0 * t).astype(np.float32)
    input_energy_20 = np.abs(np.dot(buf.data[:, 0], ref_20))
    output_energy_20 = np.abs(np.dot(output.data[:, 0], ref_20))

    assert output_energy_20 < input_energy_20 * 0.5, (
        f"20 Hz energy should be significantly reduced: "
        f"input={input_energy_20:.1f}, output={output_energy_20:.1f}"
    )


def test_process_bass_no_clipping():
    """Output max absolute value should not exceed 1.0."""
    buf = generate_sine(freq_hz=100.0, duration_s=1.0, amplitude=0.9)
    params = _make_preset(intensity=1.0)
    output = process_bass(buf, params)

    max_abs = np.max(np.abs(output.data))
    assert max_abs <= 1.0, f"Output clipped: max abs = {max_abs:.6f}"
