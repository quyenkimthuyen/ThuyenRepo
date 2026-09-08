"""Manual remine IPC (GUI → Live worker)."""
from __future__ import annotations

from pathlib import Path


def test_request_consume_remine_roundtrip(tmp_path: Path):
  from mt5_bridge.manual_remine import (
    consume_live_remine,
    read_remine_status,
    request_live_remine,
  )

  payload = request_live_remine(
    tmp_path,
    model_ids=["tm_a", "tm_b"],
    week_start="2026-08-24",
  )
  assert payload["model_ids"] == ["tm_a", "tm_b"]
  st = read_remine_status(tmp_path)
  assert st.get("state") == "queued"

  got = consume_live_remine(tmp_path)
  assert got["week_start"] == "2026-08-24"
  assert got["model_ids"] == ["tm_a", "tm_b"]
  assert consume_live_remine(tmp_path) is None


def test_apply_manual_remine_calls_engines(tmp_path: Path):
  from mt5_bridge.manual_remine import (
    apply_manual_remine_request,
    read_remine_status,
    request_live_remine,
  )

  class _Eng:
    def __init__(self, mid):
      self.model_id = mid
      self.calls = []

    def force_remine_week(self, week_start=None):
      self.calls.append(week_start)
      return {
        "ok": True,
        "week_start": "2026-08-24",
        "model_id": self.model_id,
        "name": f"{self.model_id} #NEW",
        "source": "manual_remine",
      }

  a, b = _Eng("tm_a"), _Eng("tm_b")
  request_live_remine(tmp_path, model_ids=["tm_a"], week_start="2026-08-24")
  ran = apply_manual_remine_request({"tm_a": a, "tm_b": b}, tmp_path)
  assert ran is True
  assert len(a.calls) == 1
  assert b.calls == []
  st = read_remine_status(tmp_path)
  assert st.get("state") == "done"
  assert st["results"][0]["ok"] is True
