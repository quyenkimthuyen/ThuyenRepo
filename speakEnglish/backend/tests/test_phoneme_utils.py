"""Unit tests for phoneme utilities."""

from services.phoneme_utils import (
    build_phoneme_result,
    get_suggestion,
    ipa_from_word_data,
    parse_phonemes,
    score_to_label,
)


def test_parse_phonemes_json():
    assert parse_phonemes('["h","ə","l"]') == ["h", "ə", "l"]


def test_parse_phonemes_list():
    assert parse_phonemes(["s", "t"]) == ["s", "t"]


def test_parse_phonemes_comma():
    assert parse_phonemes("h, ə, l") == ["h", "ə", "l"]


def test_ipa_from_explicit_phonemes():
    assert ipa_from_word_data("hello", "/həˈloʊ/", ["h", "ə"]) == ["h", "ə"]


def test_ipa_from_ipa_string():
    phones = ipa_from_word_data("think", "/θɪŋk/", None)
    assert "θ" in phones
    assert len(phones) >= 3


def test_score_to_label_thresholds():
    assert score_to_label(0.8, 0.75, 0.5) == "ok"
    assert score_to_label(0.6, 0.75, 0.5) == "warn"
    assert score_to_label(0.3, 0.75, 0.5) == "mis"


def test_suggestion_ok_empty():
    assert get_suggestion("θ", "ok", 0.9) == ""


def test_suggestion_mis_has_vietnamese():
    s = get_suggestion("θ", "mis", 0.2)
    assert s and ("lưỡi" in s or "răng" in s)


def test_build_phoneme_result_shape():
    r = build_phoneme_result("t", 0.1, 0.2, 0.85, 0.75, 0.5)
    assert r["ipa"] == "t"
    assert r["label"] == "ok"
    assert r["start"] == 0.1
    assert "suggestion" in r


# helper if missing - check phoneme_utils doesn't have words_match_phoneme_label