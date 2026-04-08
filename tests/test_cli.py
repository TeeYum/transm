"""Tests for the Transm CLI."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import soundfile as sf
from typer.testing import CliRunner

from transm.cli import app

runner = CliRunner()


def _make_temp_wav(
    tmp_path: Path,
    name: str = "test.wav",
    freq_hz: float = 440.0,
    duration_s: float = 1.0,
    sr: int = 44100,
    amplitude: float = 0.5,
) -> Path:
    """Write a synthetic sine-wave WAV file and return its path."""
    t = np.arange(int(sr * duration_s), dtype=np.float32) / sr
    mono = (amplitude * np.sin(2 * np.pi * freq_hz * t)).astype(np.float32)
    data = np.column_stack([mono, mono])
    path = tmp_path / name
    sf.write(str(path), data, sr, format="WAV", subtype="FLOAT")
    return path


# --- Help rendering ---


def test_help_renders() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "transm" in result.output.lower()


def test_analyze_help() -> None:
    result = runner.invoke(app, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "analyze" in result.output.lower()


def test_process_help() -> None:
    result = runner.invoke(app, ["process", "--help"])
    assert result.exit_code == 0
    assert "process" in result.output.lower() or "remaster" in result.output.lower()


def test_separate_help() -> None:
    result = runner.invoke(app, ["separate", "--help"])
    assert result.exit_code == 0


def test_compare_help() -> None:
    result = runner.invoke(app, ["compare", "--help"])
    assert result.exit_code == 0


# --- Analyze command ---


def test_analyze_command(tmp_path: Path) -> None:
    wav = _make_temp_wav(tmp_path)
    result = runner.invoke(app, ["analyze", str(wav)])
    assert result.exit_code == 0
    # Should contain loudness-related output
    output_lower = result.output.lower()
    assert "lufs" in output_lower or "loudness" in output_lower


def test_analyze_json_output(tmp_path: Path) -> None:
    wav = _make_temp_wav(tmp_path)
    result = runner.invoke(app, ["analyze", "--json", str(wav)])
    assert result.exit_code == 0
    # Strip ANSI codes and Rich markup, then parse JSON
    # The CliRunner captures raw output; find the JSON object in it
    output = result.output.strip()
    parsed = json.loads(output)
    assert "lufs_integrated" in parsed
    assert "true_peak_dbtp" in parsed
    assert "crest_factor_db" in parsed


# --- Compare command ---


def test_compare_command(tmp_path: Path) -> None:
    wav_a = _make_temp_wav(tmp_path, name="a.wav", freq_hz=440.0, amplitude=0.5)
    wav_b = _make_temp_wav(tmp_path, name="b.wav", freq_hz=440.0, amplitude=0.3)
    result = runner.invoke(app, ["compare", str(wav_a), str(wav_b)])
    assert result.exit_code == 0
    output_lower = result.output.lower()
    assert "lufs" in output_lower or "before" in output_lower or "comparison" in output_lower


def test_compare_json_output(tmp_path: Path) -> None:
    wav_a = _make_temp_wav(tmp_path, name="a.wav", freq_hz=440.0, amplitude=0.5)
    wav_b = _make_temp_wav(tmp_path, name="b.wav", freq_hz=440.0, amplitude=0.3)
    result = runner.invoke(app, ["compare", "--json", str(wav_a), str(wav_b)])
    assert result.exit_code == 0
    parsed = json.loads(result.output.strip())
    assert "metrics_a" in parsed
    assert "metrics_b" in parsed


# --- Missing file ---


def test_missing_file() -> None:
    result = runner.invoke(app, ["analyze", "/nonexistent_file_abc123.wav"])
    assert result.exit_code != 0


# --- No args shows help ---


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    # Typer with no_args_is_help=True exits with code 0 or 2 depending on version
    assert result.exit_code in (0, 2)
    output_lower = result.output.lower()
    assert "usage" in output_lower or "transm" in output_lower or "commands" in output_lower
