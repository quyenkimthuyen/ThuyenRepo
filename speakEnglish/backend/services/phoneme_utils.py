"""Phoneme parsing, IPA utilities, and Vietnamese suggestions."""

import json
import re
from typing import Any

# CMU ARPABET → IPA (simplified mapping for common phonemes)
ARPABET_TO_IPA: dict[str, str] = {
    "AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ",
    "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "EH": "ɛ", "ER": "ɜː",
    "EY": "eɪ", "F": "f", "G": "ɡ", "HH": "h", "IH": "ɪ", "IY": "iː",
    "JH": "dʒ", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ",
    "OW": "oʊ", "OY": "ɔɪ", "P": "p", "R": "r", "S": "s", "SH": "ʃ",
    "T": "t", "TH": "θ", "UH": "ʊ", "UW": "uː", "V": "v", "W": "w",
    "Y": "j", "Z": "z", "ZH": "ʒ",
}

# Vietnamese suggestions for common mispronunciation patterns
SUGGESTIONS_VI: dict[str, str] = {
    "θ": "đặt lưỡi giữa răng, thổi nhẹ (âm th voiceless)",
    "ð": "đặt lưỡi giữa răng, rung thanh quản (âm th voiced)",
    "v": "chạm môi dưới vào răng trên, rung thanh quản",
    "w": "tròn môi, không chạm răng",
    "r": "cuộn lưỡi nhẹ phía sau, không chạm vòm miệng",
    "l": "đầu lưỡi chạm vùng sau răng trên",
    "ŋ": "đầu lưỡi chạm vòm miệng mềm (âm ng)",
    "ʃ": "môi hơi tròn, lưỡi sau hơi cong",
    "tʃ": "bắt đầu như t, kết thúc như sh",
    "æ": "miệng mở rộng hơn âm e, lưỡi thấp",
    "ɜː": "miệng hơi mở, lưỡi giữa (âm er)",
    "ɑ": "miệng mở rộng tối đa, lưỡi thấp và lùi",
    "ʌ": "miệng hơi mở, lưỡi trung gian (âm u ngắn)",
    "default_vowel": "vowel quá mở hoặc quá khép — điều chỉnh hình miệng",
    "default_consonant": "thiếu voicing hoặc vị trí lưỡi sai — thử lại chậm hơn",
    "missing": "thiếu âm này — phát âm rõ hơn",
    "extra": "thừa âm — nói ngắn gọn hơn",
    "voicing": "thiếu rung thanh quản (voicing)",
}


def parse_phonemes(raw: str | list | None) -> list[str]:
    """Parse target_phonemes from JSON string or list."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(p).strip() for p in raw if str(p).strip()]
    if isinstance(raw, str):
        raw = raw.strip()
        if raw.startswith("["):
            try:
                return [str(p).strip() for p in json.loads(raw) if str(p).strip()]
            except json.JSONDecodeError:
                pass
        return [p.strip() for p in re.split(r"[,/\s]+", raw) if p.strip()]
    return []


def ipa_from_word_data(word: str, ipa: str, phonemes: list[str] | None) -> list[str]:
    """Resolve phoneme list from explicit list or IPA string."""
    if phonemes:
        return phonemes
    # Strip slashes and stress marks, split into phoneme tokens
    clean = re.sub(r"[ˈˌ/]", "", ipa)
    tokens = re.findall(
        r"tʃ|dʒ|aʊ|aɪ|eɪ|oʊ|ɔɪ|ɜː|iː|uː|.|.",
        clean,
    )
    return [t for t in tokens if t.strip()]


def score_to_label(score: float, threshold_ok: float, threshold_warn: float) -> str:
    if score >= threshold_ok:
        return "ok"
    if score >= threshold_warn:
        return "warn"
    return "mis"


def get_suggestion(ipa: str, label: str, score: float) -> str:
    if label == "ok":
        return ""
    if ipa in SUGGESTIONS_VI:
        return SUGGESTIONS_VI[ipa]
    if ipa in "aeiouɑæɛɪʌɜːɔʊuː":
        return SUGGESTIONS_VI["default_vowel"]
    return SUGGESTIONS_VI["default_consonant"]


def build_phoneme_result(
    ipa: str,
    start: float,
    end: float,
    score: float,
    threshold_ok: float,
    threshold_warn: float,
) -> dict[str, Any]:
    label = score_to_label(score, threshold_ok, threshold_warn)
    return {
        "ipa": ipa,
        "start": round(start, 3),
        "end": round(end, 3),
        "score": round(score, 3),
        "label": label,
        "suggestion": get_suggestion(ipa, label, score),
    }
