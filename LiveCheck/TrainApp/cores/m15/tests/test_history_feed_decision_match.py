"""HistoryFeed must match decision.bar_time exactly (not expires_bar_time).

Bug: WaitDecisionForBar used StringFind(json, want_bar_time), so a stale
decision for bar T (expires_bar_time = T+1h) was accepted while waiting for
bar T+1 → paper open one bar late vs Python OOS (~+1H on H1).
"""
from __future__ import annotations


def _mql_string_find_match(want_bar_time: str, decision: dict) -> bool:
  """Old EA logic (buggy)."""
  import json

  bt = str(decision.get("bar_time") or decision.get("time") or "")
  raw = json.dumps(decision, default=str)
  return bt == want_bar_time or (want_bar_time in raw)


def _exact_bar_time_match(want_bar_time: str, decision: dict) -> bool:
  """Fixed EA logic."""
  bt = str(decision.get("bar_time") or decision.get("time") or "")
  return bt == want_bar_time


def test_stale_decision_expires_must_not_match_next_bar():
  stale = {
    "action": "SELL",
    "bar_time": "2026.06.05 10:00",
    "entry_time": "2026-06-05 08:00:00",
    "expires_bar_time": "2026.06.05 11:00",
    "entry": 1.16302,
  }
  want_next = "2026.06.05 11:00"
  assert _mql_string_find_match(want_next, stale) is True  # documents the bug
  assert _exact_bar_time_match(want_next, stale) is False


def test_exact_match_accepts_current_bar_only():
  decision = {
    "action": "SELL",
    "bar_time": "2026.06.05 10:00",
    "expires_bar_time": "2026.06.05 11:00",
  }
  assert _exact_bar_time_match("2026.06.05 10:00", decision) is True
  assert _exact_bar_time_match("2026.06.05 11:00", decision) is False


def test_live_buy_schema_only_matches_exact_bar_time():
  """Live WaitDecisionForBar + OpenFromDecision contract (file side)."""
  decision = {
    "action": "BUY",
    "signal_id": "sig_live_schema_1",
    "bar_time": "2026.03.10 10:00",
    "expires_bar_time": "2026.03.10 10:15",
    "entry": 1.1000,
    "sl": 1.0990,
    "tp": 1.1020,
    "magic": 20261021,
    "model_id": "tm_live_pipeline",
  }
  assert str(decision["action"]).upper() == "BUY"
  assert float(decision["sl"]) > 0 and float(decision["tp"]) > 0
  assert decision["signal_id"]
  assert _exact_bar_time_match("2026.03.10 10:00", decision) is True
  # Next M15 bar must not accept this decision (would open 1 bar late)
  assert _exact_bar_time_match("2026.03.10 10:15", decision) is False
  assert _mql_string_find_match("2026.03.10 10:15", decision) is True  # documents old bug
