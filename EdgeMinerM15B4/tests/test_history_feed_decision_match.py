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
