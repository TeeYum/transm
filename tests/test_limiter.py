"""Tests for final true-peak limiter — unit tests."""

from __future__ import annotations

import numpy as np

from transm.analysis import measure_lufs, measure_true_peak
from transm.limiter import apply_final_limiter
from transm.types import AudioBuffer

SR = 44100


def _make_sine(
    freq_hz: float = 440.0,
    amplitude: float = 0.8,
    duration_s: float = 2.0,
) -> AudioBuffer:
    """Create a stereo sine wave."""
    n = int(SR * duration_s)
    t = np.arange(n, dtype=np.float32) / SR
    mono = (amplitude * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)
    data = np.column_stack([mono, mono])
    return AudioBuffer(data=data, sample_rate=SR)


class TestLimiterReachesTarget:
    def test_limiter_reaches_target_lufs(self) -> None:
        """Output LUFS should be within +/-1.0 LU of target."""
        buf = _make_sine(amplitude=0.8, duration_s=2.0)
        target = -14.0

        result = apply_final_limiter(buf, target_lufs=target)
        result_lufs = measure_lufs(result)

        assert abs(result_lufs - target) <= 1.0, (
            f"Output LUFS {result_lufs:.1f} not within 1.0 LU of target {target}"
        )


class TestLimiterRespectsCeiling:
    def test_limiter_respects_ceiling(self) -> None:
        """Output true peak should be at or below ceiling_dbtp (with 0.5 dB tolerance)."""
        buf = _make_sine(amplitude=0.9, duration_s=2.0)
        ceiling = -1.0

        result = apply_final_limiter(buf, ceiling_dbtp=ceiling)
        result_tp = measure_true_peak(result)

        assert result_tp <= ceiling + 0.5, (
            f"True peak {result_tp:.1f} dBTP exceeds ceiling {ceiling} + 0.5 dB tolerance"
        )


class TestLimiterCeilingEnforced:
    def test_limiter_ceiling_enforced_sparse_impulses(self) -> None:
        """Ceiling must be respected even when LUFS and ceiling conflict (high crest factor)."""
        sr = 44100
        x = np.zeros((sr * 3, 2), dtype=np.float32)
        x[:: sr // 2] = 0.9  # sparse impulses
        buf = AudioBuffer(data=x, sample_rate=sr)
        out = apply_final_limiter(buf, target_lufs=-14.0, ceiling_dbtp=-1.0)
        tp = measure_true_peak(out)
        assert tp <= -0.5, f"True peak {tp:.1f} dBTP exceeds ceiling"
        assert np.max(np.abs(out.data)) <= 1.0, "Sample peak exceeds 1.0"


class TestLimiterPreservesShape:
    def test_limiter_preserves_shape(self) -> None:
        """Shape and sample rate should be preserved."""
        buf = _make_sine(duration_s=2.0)
        result = apply_final_limiter(buf)

        assert result.data.shape == buf.data.shape
        assert result.sample_rate == buf.sample_rate
