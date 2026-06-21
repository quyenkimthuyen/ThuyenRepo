"""Tests for chế độ Chấm điểm (score mode) — API contract + pass/fail."""

import pytest


def _evaluate(client, wav_path, word="hello", ipa="/həˈloʊ/", phonemes='["h","ə","l","oʊ"]'):
    with open(wav_path, "rb") as f:
        return client.post(
            "/api/v1/evaluate",
            files={"file": ("test.wav", f, "audio/wav")},
            data={
                "target_word": word,
                "target_ipa": ipa,
                "target_phonemes": phonemes,
            },
        )


def test_score_mode_response_contract(client, sample_wav, hello_phonemes):
    """JSON đủ field để frontend render phoneme boxes."""
    r = _evaluate(client, sample_wav, phonemes=hello_phonemes)
    assert r.status_code == 200
    data = r.json()

    assert data["word"] == "hello"
    assert isinstance(data["overall_score"], int)
    assert 0 <= data["overall_score"] <= 100
    assert isinstance(data["passed"], bool)
    assert isinstance(data["phonemes"], list)
    assert len(data["phonemes"]) == 4

    for p in data["phonemes"]:
        assert p["ipa"]
        assert isinstance(p["score"], (int, float))
        assert p["label"] in ("ok", "warn", "mis")
        assert "start" in p and "end" in p
        assert "suggestion" in p


def test_score_mode_phoneme_labels_use_thresholds(client, sample_wav, hello_phonemes):
    r = _evaluate(client, sample_wav, phonemes=hello_phonemes)
    data = r.json()
    for p in data["phonemes"]:
        if p["score"] >= 0.75:
            assert p["label"] == "ok"
        elif p["score"] >= 0.5:
            assert p["label"] == "warn"
        else:
            assert p["label"] == "mis"


def test_score_mode_pass_logic_all_ok_or_overall(client, sample_wav, hello_phonemes):
    r = _evaluate(client, sample_wav, phonemes=hello_phonemes)
    data = r.json()
    all_ok = all(p["label"] == "ok" for p in data["phonemes"])
    expected_pass = all_ok or data["overall_score"] >= 80
    assert data["passed"] == expected_pass


@pytest.mark.parametrize("word,ipa,phonemes", [
    ("think", "/θɪŋk/", '["θ","ɪ","ŋ","k"]'),
    ("water", "/ˈwɔːtər/", '["w","ɔ","t","ər"]'),
])
def test_score_mode_multiple_words(client, sample_wav, word, ipa, phonemes):
    r = _evaluate(client, sample_wav, word=word, ipa=ipa, phonemes=phonemes)
    assert r.status_code == 200
    data = r.json()
    assert data["word"] == word
    assert len(data["phonemes"]) == len(__import__("json").loads(phonemes))


def test_score_mode_rejects_empty_audio(client, tmp_path):
    tiny = tmp_path / "tiny.wav"
    tiny.write_bytes(b"RIFF" + b"\x00" * 50)
    r = _evaluate(client, tiny)
    assert r.status_code == 400
    detail = r.json()["detail"]
    err = detail.get("error", detail) if isinstance(detail, dict) else detail
    assert "short" in str(err).lower() or "error" in str(err).lower()


def test_score_mode_health_shows_methods(client):
    """Footer score mode cần alignment/scoring method."""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data.get("alignment_method")
    assert data.get("scoring_method")
