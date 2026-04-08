"""Tests for the vocal processing chain."""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt

from transm.dsp.vocals import process_vocals
from transm.types import GlobalParams, PresetParams, VocalsParams


def _make_preset(intensity: float = 0.35) -> PresetParams:
    """Create a PresetParams with default values and the given intensity."""
    return PresetParams(
        name="test-vocals",
        global_params=GlobalParams(intensity=intensity),
        vocals=VocalsParams(),
    )


def _band_energy(data: np.ndarray, sr: int, low: float, high: float) -> float:
    """Compute RMS energy in a frequency band."""
    sos = butter(4, [low, high], btype="bandpass", fs=sr, output="sos")
    # Use first channel
    filtered = sosfilt(sos, data[:, 0])
    return float(np.sqrt(np.mean(filtered**2)))


def test_process_vocals_reduces_sibilance(sibilant_vocal):
    """Processing should reduce energy in the 6-9 kHz sibilance band."""
    params = _make_preset(intensity=0.35)
    sr = sibilant_vocal.sample_rate

    input_sibilance = _band_energy(sibilant_vocal.data, sr, 6000.0, 9000.0)
    output = process_vocals(sibilant_vocal, params)
    output_sibilance = _band_energy(output.data, sr, 6000.0, 9000.0)

    assert output_sibilance < input_sibilance, (
        f"Sibilance should decrease: input={input_sibilance:.6f}, output={output_sibilance:.6f}"
    )


def test_process_vocals_preserves_shape(sibilant_vocal):
    """Output shape and sample rate must match input."""
    params = _make_preset(intensity=0.35)
    output = process_vocals(sibilant_vocal, params)

    assert output.data.shape == sibilant_vocal.data.shape
    assert output.sample_rate == sibilant_vocal.sample_rate


def test_process_vocals_zero_intensity(sibilant_vocal):
    """With intensity=0, output should approximate input.

    The de-esser still runs at default settings when intensity > 0,
    but at intensity=0 we early-exit, so output should exactly equal input.
    """
    params = _make_preset(intensity=0.0)
    output = process_vocals(sibilant_vocal, params)

    np.testing.assert_array_equal(output.data, sibilant_vocal.data)
    assert output.sample_rate == sibilant_vocal.sample_rate


def test_process_vocals_level_adjust(sibilant_vocal):
    """Output should be quieter than input (level_adjust_db is negative)."""
    params = _make_preset(intensity=0.35)
    output = process_vocals(sibilant_vocal, params)

    input_rms = np.sqrt(np.mean(sibilant_vocal.data**2))
    output_rms = np.sqrt(np.mean(output.data**2))

    assert output_rms < input_rms, (
        f"Output should be quieter: input_rms={input_rms:.6f}, output_rms={output_rms:.6f}"
    )
