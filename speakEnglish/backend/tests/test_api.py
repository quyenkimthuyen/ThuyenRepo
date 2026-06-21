"""API endpoint tests."""

import time

import pytest


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "alignment_method" in data
    assert "scoring_method" in data


def test_evaluate_success(client, sample_wav, hello_phonemes):
    with open(sample_wav, "rb") as f:
        r = client.post(
            "/api/v1/evaluate",
            files={"file": ("test.wav", f, "audio/wav")},
            data={
                "target_word": "hello",
                "target_ipa": "/həˈloʊ/",
                "target_phonemes": hello_phonemes,
            },
        )
    assert r.status_code == 200
    data = r.json()
    assert data["word"] == "hello"
    assert "overall_score" in data
    assert isinstance(data["phonemes"], list)
    assert len(data["phonemes"]) == 4
    for p in data["phonemes"]:
        assert "ipa" in p
        assert "score" in p
        assert p["label"] in ("ok", "warn", "mis")
        assert "start" in p and "end" in p


def test_evaluate_missing_word(client, sample_wav):
    with open(sample_wav, "rb") as f:
        r = client.post(
            "/api/v1/evaluate",
            files={"file": ("test.wav", f, "audio/wav")},
            data={"target_word": "", "target_ipa": "", "target_phonemes": "[]"},
        )
    assert r.status_code == 400
    detail = r.json()["detail"]
    err = detail.get("error", detail) if isinstance(detail, dict) else detail
    assert "target_word" in str(err).lower() or "required" in str(err).lower()


def test_evaluate_audio_too_short(client, tmp_path):
    tiny = tmp_path / "tiny.wav"
    tiny.write_bytes(b"RIFF")
    with open(tiny, "rb") as f:
        r = client.post(
            "/api/v1/evaluate",
            files={"file": ("tiny.wav", f, "audio/wav")},
            data={"target_word": "hello"},
        )
    assert r.status_code == 400


def test_evaluate_invalid_phonemes_json(client, sample_wav):
    with open(sample_wav, "rb") as f:
        r = client.post(
            "/api/v1/evaluate",
            files={"file": ("test.wav", f, "audio/wav")},
            data={
                "target_word": "hello",
                "target_phonemes": "[invalid",
            },
        )
    assert r.status_code == 400


def test_evaluate_unsupported_format(client, tmp_path):
    bad = tmp_path / "file.txt"
    bad.write_text("not audio")
    with open(bad, "rb") as f:
        r = client.post(
            "/api/v1/evaluate",
            files={"file": ("file.txt", f, "text/plain")},
            data={"target_word": "hello"},
        )
    assert r.status_code == 400


def test_audio_cleanup(client, sample_wav, hello_phonemes):
    with open(sample_wav, "rb") as f:
        client.post(
            "/api/v1/evaluate",
            files={"file": ("test.wav", f, "audio/wav")},
            data={"target_word": "hello", "target_phonemes": hello_phonemes},
        )
    r = client.delete("/api/v1/audio/cleanup")
    assert r.status_code == 200
    assert "deleted" in r.json()


@pytest.mark.parametrize("word,ipa,phonemes", [
    ("think", "/θɪŋk/", '["θ","ɪ","ŋ","k"]'),
    ("station", "/ˈsteɪʃən/", '["s","t","eɪ","ʃ","ə","n"]'),
    ("hello", "/həˈloʊ/", '["h","ə","l","oʊ"]'),
])
def test_evaluate_multiple_words(client, sample_wav, word, ipa, phonemes):
    with open(sample_wav, "rb") as f:
        r = client.post(
            "/api/v1/evaluate",
            files={"file": ("test.wav", f, "audio/wav")},
            data={
                "target_word": word,
                "target_ipa": ipa,
                "target_phonemes": phonemes,
            },
        )
    assert r.status_code == 200
    assert r.json()["word"] == word
