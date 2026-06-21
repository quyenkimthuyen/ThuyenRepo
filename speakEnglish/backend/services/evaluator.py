"""Main evaluation pipeline orchestrator."""

import shutil
import uuid
from pathlib import Path

from config import OVERALL_PASS_SCORE, UPLOAD_DIR
from services.aligner import get_aligner
from services.audio_processor import resample_audio
from services.phoneme_utils import ipa_from_word_data, parse_phonemes
from services.scorer import get_scorer


def evaluate_pronunciation(
    audio_path: Path,
    target_word: str,
    target_ipa: str,
    target_phonemes_raw: str | list | None,
    original_filename: str = "recording.webm",
) -> dict:
    """
    Full pipeline: resample → align → score → JSON response.
    """
    phonemes = parse_phonemes(target_phonemes_raw)
    if not phonemes:
        phonemes = ipa_from_word_data(target_word, target_ipa, None)

    # Save uploaded file
    upload_id = uuid.uuid4().hex[:12]
    ext = Path(original_filename).suffix or ".webm"
    saved_path = UPLOAD_DIR / f"{upload_id}{ext}"
    shutil.copy2(audio_path, saved_path)

    # Resample to 16kHz mono WAV
    wav_path = resample_audio(saved_path)

    # Align
    aligner = get_aligner()
    segments = aligner.align(wav_path, target_word, target_ipa, phonemes)

    # Ensure segment count matches target phonemes
    if len(segments) != len(phonemes) and phonemes:
        from services.aligner import FallbackAligner
        segments = FallbackAligner().align(wav_path, target_word, target_ipa, phonemes)

    # Score
    scorer = get_scorer()
    phoneme_results = scorer.score_phonemes(wav_path, segments, target_word)

    # Overall score
    if phoneme_results:
        overall = int(round(sum(p["score"] for p in phoneme_results) / len(phoneme_results) * 100))
    else:
        overall = 0

    all_ok = all(p["label"] == "ok" for p in phoneme_results)
    passed = all_ok or overall >= OVERALL_PASS_SCORE

    return {
        "word": target_word,
        "ipa": target_ipa,
        "overall_score": overall,
        "passed": passed,
        "phonemes": phoneme_results,
        "audio_url": f"/api/v1/audio/{upload_id}{ext}",
    }
