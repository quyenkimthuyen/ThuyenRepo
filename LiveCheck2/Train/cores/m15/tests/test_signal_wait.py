"""Closed-bar BUY/SELL gates: current vs expect."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from strategy_miner import MinedStrategy, Rule, explain_bar_gates


class _FM:
  def __init__(self, *, hour: int = 10, rsi: float = 50.0, n: int = 4):
    self.index = pd.date_range("2026-07-15 10:00", periods=n, freq="15min")
    self.n = n
    self.warmup = 0
    self.hours = np.full(n, hour, dtype=int)
    self.broker_hours = self.hours
    self._rsi = np.full(n, rsi, dtype=float)
    self._zero = np.zeros(n, dtype=float)
    self._one = np.ones(n, dtype=float)

  def get(self, name: str):
    if name == "rsi":
      return self._rsi
    if name in ("htf_trend", "confluence_long", "confluence_short"):
      return self._zero
    return self._one


def _strat() -> MinedStrategy:
  return MinedStrategy(
    long_rules=[Rule("rsi", "long", "lt", 40.0, 2.0)],
    short_rules=[Rule("rsi", "short", "gt", 60.0, 2.0)],
    min_rules_match=1,
    score_threshold=1.0,
    session_filter=True,
    session_start_hour=7,
    session_end_hour=20,
    ml_prob_min=0.4,
  )


def test_rsi_above_long_threshold_waits_on_buy_rule():
  wait = explain_bar_gates(_FM(rsi=52.0), _strat(), 0)
  buy = wait["buy"]
  assert buy["ready"] is False
  assert buy["waiting_n"] >= 1
  rsi_gate = next(g for g in buy["gates"] if g["id"].startswith("rule:rsi"))
  assert rsi_gate["ok"] is False
  assert rsi_gate["current"] == 52.0
  assert rsi_gate["expect"] == "< 40"


def test_rsi_oversold_makes_buy_ready_inside_session():
  wait = explain_bar_gates(_FM(hour=10, rsi=28.0), _strat(), 0)
  assert wait["buy"]["ready"] is True
  assert wait["buy"]["waiting_n"] == 0
  assert wait["sell"]["ready"] is False
  sell_rsi = next(g for g in wait["sell"]["gates"] if g["id"].startswith("rule:rsi"))
  assert sell_rsi["current"] == 28.0
  assert sell_rsi["expect"] == "> 60"
  assert sell_rsi["ok"] is False


def test_outside_session_blocks_both_sides():
  wait = explain_bar_gates(_FM(hour=3, rsi=28.0), _strat(), 0)
  sess = next(g for g in wait["buy"]["gates"] if g["id"] == "session")
  assert sess["ok"] is False
  assert sess["current"] == 3
  assert "7" in str(sess["expect"])
  assert wait["buy"]["ready"] is False
  assert wait["sell"]["ready"] is False


def test_live_now_renders_signal_wait_section():
  root = Path(__file__).resolve().parents[3]
  bridge = (root / "gui" / "views" / "mt5_bridge.py").read_text(encoding="utf-8")
  live = (root / "gui" / "views" / "live_trade_dash.py").read_text(encoding="utf-8")
  shared = (root / "gui" / "signal_wait_ui.py").read_text(encoding="utf-8")
  assert "def _render_signal_wait" in bridge
  assert "render_signal_wait" in live
  assert "Chờ tín hiệu BUY / SELL" in shared
  assert "signal_wait" in shared
  assert live.rfind("render_signal_wait(") > live.rfind("_guard_html")
  stats_tab = bridge[bridge.rfind("def render_tab_stats()"):]
  assert "_render_stats_section()" in stats_tab
  assert "_stats_auto_fragment()" in stats_tab
  assert "_signal_wait_fragment()" not in stats_tab
  assert "def render_tab_risk_control()" in bridge


def test_wait_side_caption_ready_and_waiting():
  from gui.signal_wait_ui import wait_side_caption
  assert wait_side_caption({"ready": True}) == "sẵn sàng"
  assert wait_side_caption({"ready": False, "waiting_n": 2, "total": 8}) == "chờ 2/8"
  assert wait_side_caption(None) == "—"
