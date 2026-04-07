"""Tests for the Pipeline orchestrator.

Tests marked @slow/@integration require model downloads.
test_pipeline_run_mocked uses a mocked separator so it runs without downloads.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf

from tests.conftest import generate_sine
from transm.audio_io import write_audio
from transm.pipeline import Pipeline
from transm.preset_loader import load_preset
from transm.separation import StemSeparator
from transm.types import Metrics, PresetParams, StemSet

SR = 44100


def _write_test_wav(path: Path, duration_s: float = 2.0) -> None:
    """Write a synthetic stereo WAV file."""
    n = int(SR * duration_s)
    t = np.arange(n, dtype=np.float32) / SR
    mono = (0.5 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)
    data = np.column_stack([mono, mono])
    sf.write(str(path), data, SR, format="WAV", subtype="FLOAT")


class TestPipelineInit:
    def test_pipeline_init(self) -> None:
        """Pipeline should instantiate with a default preset."""
        preset = PresetParams(name="default")
        pipeline = Pipeline(preset=preset)

        assert pipeline.preset.name == "default"
        assert pipeline.backend == "demucs"
        assert pipeline.output_format == "wav"

    def test_pipeline_init_custom_backend(self) -> None:
        """Pipeline should accept alternate backend."""
        preset = PresetParams(name="custom")
        pipeline = Pipeline(preset=preset, backend="roformer", output_format="flac")

        assert pipeline.backend == "roformer"
        assert pipeline.output_format == "flac"

    def test_pipeline_init_model_name(self) -> None:
        """Pipeline should forward model_name to the separator."""
        preset = PresetParams(name="test")
        pipeline = Pipeline(preset=preset, model_name="custom.yaml")

        assert pipeline._separator.model_name == "custom.yaml"


class TestPipelineAnalysisOnly:
    def test_pipeline_analysis_only(self) -> None:
        """run_analysis_only should return valid Metrics from a WAV file."""
        preset = PresetParams(name="test")
        pipeline = Pipeline(preset=preset)

        with tempfile.TemporaryDirectory() as tmp_dir:
            wav_path = Path(tmp_dir) / "test_input.wav"
            _write_test_wav(wav_path)

            metrics = pipeline.run_analysis_only(wav_path)

            assert isinstance(metrics, Metrics)
            assert not np.isinf(metrics.lufs_integrated)
            assert metrics.spectral_centroid_hz > 0


def test_pipeline_run_mocked(tmp_path: Path) -> None:
    """Full pipeline with mocked separator — no model download needed."""
    # Create a real input WAV
    buf = generate_sine(duration_s=2.0)
    input_path = tmp_path / "input.wav"
    write_audio(buf, input_path)

    # Mock the separator to return 4 copies of the input as stems
    mock_stems = StemSet(vocals=buf, drums=buf, bass=buf, other=buf)

    with patch.object(StemSeparator, "separate", return_value=mock_stems):
        preset = load_preset("2000s-metalcore")
        pipeline = Pipeline(preset=preset)
        result = pipeline.run(input_path, tmp_path / "output.wav")

    assert result.output_path.exists()
    assert result.processing_time_s > 0
    # Output should have valid metrics
    assert result.output_metrics.lufs_integrated != 0
