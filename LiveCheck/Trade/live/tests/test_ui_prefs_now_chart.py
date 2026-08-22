"""Now chart checkbox prefs survive F5 via ui_prefs.json."""
from __future__ import annotations

import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
GUI = LIVE / "gui"
for p in (LIVE, GUI):
  if str(p) not in sys.path:
    sys.path.insert(0, str(p))

import theme as th  # noqa: E402


def test_now_chart_checks_roundtrip(tmp_path, monkeypatch):
  monkeypatch.setattr(th, "_prefs_path", lambda: tmp_path / "ui_prefs.json")
  mid = "tm_wr50"
  checks = {"B|session_vwap_dist|-1.4150": True, "B|squeeze_break_up|0.5000": True}
  th.save_now_chart_checks(mid, checks)
  got = th.load_now_chart_checks(mid)
  assert got == checks
  assert th.now_chart_check_id("B", "session_vwap_dist", -1.415) == "B|session_vwap_dist|-1.4150"


def test_restore_widget_choice_keeps_mounted_and_replays_pref():
  valid = ("today", "week", "month", "all")
  # Widget still on page — do not clobber the click.
  assert th.restore_widget_choice("week", "today", valid, "today") == "week"
  # Streamlit dropped the key after a tab hop — restore from disk (F5 path).
  assert th.restore_widget_choice(None, "all", valid, "today") == "all"
  assert th.restore_widget_choice("", "month", valid, "today") == "month"
  assert th.restore_widget_choice("nope", "bogus", valid, "today") == "today"


def test_now_picked_model_roundtrip(tmp_path, monkeypatch):
  monkeypatch.setattr(th, "_prefs_path", lambda: tmp_path / "ui_prefs.json")
  th.save_now_picked_model("EURUSD M15", "tm_wr57")
  assert th.load_now_picked_model("EURUSD M15") == "tm_wr57"
  prefs = th.load_ui_prefs()
  assert prefs["live_stats_period"] in ("today", "week", "month", "all")
  assert prefs["live_desk_section"] in ("now", "pipeline", "session")
  assert "now_chart_checks" in prefs
