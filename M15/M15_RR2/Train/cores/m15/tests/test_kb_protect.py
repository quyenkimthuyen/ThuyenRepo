"""Locked KB profiles survive wipe / reset / delete."""
from __future__ import annotations

import pytest


@pytest.fixture()
def kb_tmp(tmp_path, monkeypatch):
  import kb_profiles as kbp

  profiles = tmp_path / "kb_profiles"
  profiles.mkdir()
  know = tmp_path / "knowledge.json"
  monkeypatch.setattr(kbp, "PROFILES_DIR", profiles)
  monkeypatch.setattr(kbp, "INDEX_PATH", profiles / "index.json")
  monkeypatch.setattr(kbp, "SNAPSHOTS_DIR", profiles / "snapshots")
  monkeypatch.setattr(kbp, "KNOWLEDGE_PATH", know)
  return {"profiles": profiles, "know": know, "kbp": kbp}


def _touch_profile(kbp, pid: str) -> None:
  path = kbp.profile_path(pid)
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text("{}", encoding="utf-8")
  kbp.register_profile(pid, pid, "2025-07-01", "2025-12-31", 3)


def test_protect_blocks_delete_and_wipe(kb_tmp):
  kbp = kb_tmp["kbp"]
  _touch_profile(kbp, "era_win")
  _touch_profile(kbp, "era_old")
  kbp.protect_profile("era_win", snapshots=[3], reason="tm:tm_demo")

  assert kbp.is_profile_protected("era_win")
  assert kbp.is_snapshot_protected("era_win", 1)
  assert not kbp.delete_profile("era_win")
  assert kbp.profile_path("era_win").exists()

  out = kbp.wipe_unprotected_profiles()
  assert "era_win" in out["kept"]
  assert "era_old" in out["deleted"]
  assert kbp.profile_path("era_win").exists()
  assert not kbp.profile_path("era_old").exists()


def test_protect_from_models_and_unprotect(kb_tmp):
  kbp = kb_tmp["kbp"]
  _touch_profile(kbp, "era_2025_h2")
  locked = kbp.protect_from_models([
    {"id": "tm_a", "use_kb": True, "kb_profile": "era_2025_h2", "kb_snapshot": 3},
    {"id": "tm_b", "use_kb": True, "kb_profile": "era_2025_h2", "kb_snapshot": 2},
  ])
  assert locked == ["era_2025_h2"]
  meta = kbp.get_profile("era_2025_h2") or {}
  assert meta.get("protected") is True
  assert set(meta.get("protected_snapshots") or []) >= {2, 3}

  kbp.unprotect_profile("era_2025_h2")
  assert not kbp.is_profile_protected("era_2025_h2")
  assert kbp.delete_profile("era_2025_h2")
  assert not kbp.profile_path("era_2025_h2").exists()


def test_ensure_profile_learned_continues_delta(kb_tmp, monkeypatch):
  kbp = kb_tmp["kbp"]
  _touch_profile(kbp, "era_2024_h1")  # epochs=3
  called = {}

  def fake_exec(**kwargs):
    called.update(kwargs)
    return {"epochs": kwargs.get("epochs")}

  monkeypatch.setattr("gui.services.execute_learning", fake_exec)
  from gui.era_compare import ensure_profile_learned

  spec = {
    "kb_profile": "era_2024_h1",
    "kb_name": "2024 H1",
    "learn_from": "2024-01-01",
    "learn_until": "2024-06-30",
  }
  skipped = ensure_profile_learned(spec, epochs=3, reset=False)
  assert skipped.get("skipped") is True
  assert not called

  out = ensure_profile_learned(spec, epochs=5, reset=False)
  assert called.get("epochs") == 2
  assert called.get("reset_kb") is False
  assert out.get("epochs") == 2


def test_register_preserves_protect_flag(kb_tmp):
  kbp = kb_tmp["kbp"]
  _touch_profile(kbp, "era_2024_h1")
  kbp.protect_profile("era_2024_h1", snapshots=[1], reason="manual")
  kbp.register_profile("era_2024_h1", "2024 H1", "2024-01-01", "2024-06-30", 3, note="relearn")
  meta = kbp.get_profile("era_2024_h1") or {}
  assert meta.get("protected") is True
  assert 1 in (meta.get("protected_snapshots") or [])


def test_ensure_profile_learned_skips_protected(kb_tmp, monkeypatch):
  kbp = kb_tmp["kbp"]
  _touch_profile(kbp, "era_lock")
  kbp.protect_profile("era_lock", reason="tm:x")

  from gui.era_compare import ensure_profile_learned

  def boom(*_a, **_k):
    raise AssertionError("execute_learning must not run on locked KB")

  monkeypatch.setattr("gui.services.execute_learning", boom)
  out = ensure_profile_learned(
    {
      "kb_profile": "era_lock",
      "kb_name": "lock",
      "learn_from": "2025-07-01",
      "learn_until": "2025-12-31",
    },
    epochs=3,
    reset=True,
  )
  assert out.get("skipped") is True
  assert out.get("protected") is True


def test_execute_learning_refuses_protected(kb_tmp):
  kbp = kb_tmp["kbp"]
  _touch_profile(kbp, "era_lock")
  kbp.protect_profile("era_lock", reason="tm:x")
  from gui.services import execute_learning

  with pytest.raises(ValueError, match="khóa"):
    execute_learning(epochs=1, kb_profile="era_lock", reset_kb=True)


def test_schedule_feature_usage_counts_weeks():
  from trade_model_schedule import schedule_feature_usage

  payload = {
    "weekly": [
      {
        "week_start": "2026-01-05",
        "strategy": {
          "long_rules": [
            {"feat": "range_buy", "op": "eq1", "thr": 0.5},
            {"feat": "range_buy", "op": "eq1", "thr": 0.5},
          ],
          "short_rules": [{"feat": "range_sell", "op": "eq1", "thr": 0.5}],
        },
      },
      {
        "week_start": "2026-01-12",
        "strategy": {
          "long_rules": [{"feat": "sweep_low_fade", "op": "gt", "thr": 0.2}],
          "short_rules": [{"feat": "range_sell", "op": "eq1", "thr": 0.5}],
        },
      },
    ]
  }
  usage = schedule_feature_usage(payload)
  assert usage["n_weeks"] == 2
  long_by = {r["feat"]: r for r in usage["long"]}
  short_by = {r["feat"]: r for r in usage["short"]}
  assert long_by["range_buy"]["weeks"] == 1
  assert long_by["sweep_low_fade"]["weeks"] == 1
  assert short_by["range_sell"]["weeks"] == 2
  assert short_by["range_sell"]["pct_weeks"] == 100.0
  assert "eq1" in short_by["range_sell"]["common_thr"]
