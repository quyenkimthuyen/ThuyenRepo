"""Per-phoneme GOP / classifier scoring."""

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from config import SCORING_METHOD, THRESHOLD_OK, THRESHOLD_WARN
from services.audio_processor import load_wav, slice_audio
from services.phoneme_utils import build_phoneme_result


class BaseScorer(ABC):
    @abstractmethod
    def score_phonemes(
        self,
        wav_path: Path,
        segments: list[dict],
        word: str,
    ) -> list[dict]:
        ...


class FallbackScorer(BaseScorer):
    """
    MFCC-based pseudo-GOP scorer for local demo without heavy models.
    Uses energy, spectral features, and deterministic seed from audio hash
    to produce realistic-looking scores for testing.
    """

    def score_phonemes(self, wav_path: Path, segments: list[dict], word: str) -> list[dict]:
        data, sr = load_wav(wav_path)
        results = []
        audio_hash = hashlib.md5(data.tobytes()).hexdigest()

        for i, seg in enumerate(segments):
            chunk = slice_audio(data, sr, seg["start"], seg["end"])
            score = self._compute_score(chunk, sr, seg["ipa"], i, audio_hash, word)
            results.append(
                build_phoneme_result(
                    seg["ipa"], seg["start"], seg["end"],
                    score, THRESHOLD_OK, THRESHOLD_WARN,
                )
            )
        return results

    def _compute_score(
        self,
        chunk: np.ndarray,
        sr: int,
        ipa: str,
        index: int,
        audio_hash: str,
        word: str,
    ) -> float:
        if len(chunk) < 10:
            return 0.25

        # Energy-based quality signal
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        energy_score = min(1.0, rms * 15)

        # Zero-crossing rate (consonants vs vowels)
        zcr = float(np.mean(np.abs(np.diff(np.sign(chunk)))) / 2)
        is_vowel = ipa in "aeiouɑæɛɪʌɜːɔʊuːaʊaɪeɪoʊɔɪ"
        zcr_score = (1.0 - zcr) if is_vowel else min(1.0, zcr * 3)

        # Spectral centroid proxy
        fft = np.abs(np.fft.rfft(chunk))
        freqs = np.fft.rfftfreq(len(chunk), 1 / sr)
        centroid = float(np.sum(freqs * fft) / (np.sum(fft) + 1e-8))
        centroid_score = min(1.0, centroid / 3000) if is_vowel else min(1.0, centroid / 5000)

        base = 0.4 * energy_score + 0.3 * zcr_score + 0.3 * centroid_score

        # Deterministic variation for demo reproducibility
        seed_val = int(audio_hash[index * 2:(index * 2) + 2], 16) / 255.0
        base = 0.6 * base + 0.4 * seed_val

        return float(np.clip(base, 0.1, 0.98))


class GOPScorer(BaseScorer):
    """GOP scoring using acoustic model log-likelihood ratios (when MFA models available)."""

    def score_phonemes(self, wav_path: Path, segments: list[dict], word: str) -> list[dict]:
        # Placeholder: requires Kaldi/MFA acoustic model integration
        # Falls back to MFCC scorer until models are configured
        return FallbackScorer().score_phonemes(wav_path, segments, word)


class Wav2Vec2Scorer(BaseScorer):
    """wav2vec2 MDD classifier (optional advanced mode)."""

    _model = None
    _processor = None

    def _load_model(self):
        if self._model is not None:
            return
        try:
            import torch
            from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
            model_name = "facebook/wav2vec2-base-960h"
            self._processor = Wav2Vec2Processor.from_pretrained(model_name)
            self._model = Wav2Vec2ForCTC.from_pretrained(model_name)
            self._model.eval()
        except Exception:
            self._model = "unavailable"

    def score_phonemes(self, wav_path: Path, segments: list[dict], word: str) -> list[dict]:
        self._load_model()
        if self._model == "unavailable":
            return FallbackScorer().score_phonemes(wav_path, segments, word)

        import torch
        data, sr = load_wav(wav_path)
        results = []
        for seg in segments:
            chunk = slice_audio(data, sr, seg["start"], seg["end"])
            inputs = self._processor(chunk, sampling_rate=sr, return_tensors="pt", padding=True)
            with torch.no_grad():
                logits = self._model(inputs.input_values).logits
                probs = torch.softmax(logits, dim=-1)
                max_prob = float(probs.max())
            results.append(
                build_phoneme_result(
                    seg["ipa"], seg["start"], seg["end"],
                    max_prob, THRESHOLD_OK, THRESHOLD_WARN,
                )
            )
        return results


def get_scorer() -> BaseScorer:
    method = SCORING_METHOD.lower()
    if method == "gop":
        return GOPScorer()
    if method == "wav2vec2":
        return Wav2Vec2Scorer()
    return FallbackScorer()
