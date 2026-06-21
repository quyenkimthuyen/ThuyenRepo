"""Pytest fixtures."""

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    from main import app
    return TestClient(app)


@pytest.fixture
def sample_wav(tmp_path: Path) -> Path:
    """0.8s 440Hz mono WAV @ 16kHz."""
    path = tmp_path / "sample.wav"
    cmd = [
        "ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=0.8",
        "-ar", "16000", "-ac", "1", str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip(f"ffmpeg not available: {result.stderr}")
    return path


@pytest.fixture
def hello_phonemes():
    return '["h","ə","l","oʊ"]'
