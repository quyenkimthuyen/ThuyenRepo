"""Audio resampling and normalization."""

import io
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from config import TARGET_CHANNELS, TARGET_SAMPLE_RATE


def resample_audio(input_path: Path, output_path: Path | None = None) -> Path:
    """Resample audio to 16kHz mono WAV using ffmpeg."""
    if output_path is None:
        output_path = input_path.with_suffix(".16k.wav")

    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-ar", str(TARGET_SAMPLE_RATE),
        "-ac", str(TARGET_CHANNELS),
        "-f", "wav",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    return output_path


def load_wav(path: Path) -> tuple[np.ndarray, int]:
    """Load WAV file as float32 numpy array."""
    try:
        import soundfile as sf
        data, sr = sf.read(str(path), dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        return data, sr
    except ImportError:
        pass

    # Fallback: use scipy if soundfile unavailable
    from scipy.io import wavfile
    sr, data = wavfile.read(str(path))
    data = data.astype(np.float32)
    if data.max() > 1.0:
        data = data / 32768.0
    if data.ndim > 1:
        data = data.mean(axis=1)
    return data, sr


def get_duration(path: Path) -> float:
    """Get audio duration in seconds."""
    data, sr = load_wav(path)
    return len(data) / sr


def slice_audio(data: np.ndarray, sr: int, start: float, end: float) -> np.ndarray:
    """Slice audio array by time range."""
    s = max(0, int(start * sr))
    e = min(len(data), int(end * sr))
    return data[s:e]
