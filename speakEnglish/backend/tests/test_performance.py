"""Performance / latency tests — đảm bảo phản hồi nhanh."""

import time

import pytest

MAX_EVALUATE_MS = 5000
MAX_HEALTH_MS = 200


def test_health_latency(client):
    t0 = time.perf_counter()
    r = client.get("/api/v1/health")
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert r.status_code == 200
    assert elapsed_ms < MAX_HEALTH_MS, f"health took {elapsed_ms:.0f}ms"


def test_evaluate_latency_single_word(client, sample_wav, hello_phonemes):
    with open(sample_wav, "rb") as f:
        t0 = time.perf_counter()
        r = client.post(
            "/api/v1/evaluate",
            files={"file": ("test.wav", f, "audio/wav")},
            data={
                "target_word": "hello",
                "target_ipa": "/həˈloʊ/",
                "target_phonemes": hello_phonemes,
            },
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
    assert r.status_code == 200
    assert elapsed_ms < MAX_EVALUATE_MS, f"evaluate took {elapsed_ms:.0f}ms (max {MAX_EVALUATE_MS})"


def test_evaluate_latency_p95_simulation(client, sample_wav, hello_phonemes):
    """5 lần gọi liên tiếp — không request nào vượt ngưỡng."""
    times = []
    for _ in range(5):
        with open(sample_wav, "rb") as f:
            t0 = time.perf_counter()
            r = client.post(
                "/api/v1/evaluate",
                files={"file": ("test.wav", f, "audio/wav")},
                data={
                    "target_word": "hello",
                    "target_ipa": "/həˈloʊ/",
                    "target_phonemes": hello_phonemes,
                },
            )
            times.append((time.perf_counter() - t0) * 1000)
        assert r.status_code == 200
    assert max(times) < MAX_EVALUATE_MS, f"max latency {max(times):.0f}ms"
    assert sum(times) / len(times) < MAX_EVALUATE_MS * 0.7, f"avg {sum(times)/len(times):.0f}ms"
