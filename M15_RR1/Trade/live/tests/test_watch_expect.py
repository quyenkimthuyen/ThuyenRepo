"""Expect vs current formatting for Live Now watch."""
from __future__ import annotations

import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
if str(LIVE) not in sys.path:
  sys.path.insert(0, str(LIVE))

from watch_expect import (  # noqa: E402
  _chart_tail_for_period,
  _collect_watch_lines,
  _hit_x_for_axis,
  broker_wall_to_display,
  build_watch_figure,
  collect_model_lines,
  format_watch_expect,
  period_fill_marks,
  slice_pack_to_period,
)


def test_all_rules_show_now_vs_need():
  strat = {
    "min_rules_match": 2,
    "long_rules": [
      {"feat": "squeeze_break_up", "op": "eq1", "thr": 0.5, "w": 0.07},
      {"feat": "session_vwap_dist", "op": "lt", "thr": -1.415, "w": 64.0},
    ],
    "short_rules": [
      {"feat": "macd_cross_dn", "op": "eq1", "thr": 0.5, "w": 0.0},
      {"feat": "session_vwap_dist", "op": "gt", "thr": 0.108, "w": 5.96},
    ],
  }
  out = format_watch_expect(
    strat,
    {"session_vwap_dist": 0.204, "squeeze_break_up": 0.0, "macd_cross_dn": 0.0},
    action="FLAT",
    reason="no_signal",
  )
  assert [x["text"] for x in out["buy_lines"]] == [
    "VWAP 0.204 < -1.42",
    "squeeze↑ 0 = 1",
  ]
  assert [x["hit"] for x in out["buy_lines"]] == [False, False]
  assert [x["text"] for x in out["sell_lines"]] == [
    "VWAP 0.204 > 0.108",
    "MACD↓ 0 = 1",
  ]
  assert [x["hit"] for x in out["sell_lines"]] == [True, False]
  assert out["buy_gate"] == "0/2"
  assert out["sell_gate"] == "1/2"
  assert "SELL 1/2 miss MACD↓" in out["why"]
  assert "BUY 0/2" in out["why"]


def test_why_sell_in_lists_hit_rules():
  strat = {
    "min_rules_match": 2,
    "long_rules": [
      {"feat": "squeeze_break_up", "op": "eq1", "thr": 0.5, "w": 1.0},
      {"feat": "session_vwap_dist", "op": "lt", "thr": -1.415, "w": 64.0},
    ],
    "short_rules": [
      {"feat": "macd_cross_dn", "op": "eq1", "thr": 0.5, "w": 0.1},
      {"feat": "session_vwap_dist", "op": "gt", "thr": 0.108, "w": 5.96},
      {"feat": "swing_strength", "op": "gt", "thr": 0.61, "w": 2.0},
    ],
  }
  out = format_watch_expect(
    strat,
    {
      "session_vwap_dist": 0.204,
      "squeeze_break_up": 0.0,
      "macd_cross_dn": 0.0,
      "swing_strength": 0.8,
    },
    action="SELL",
    reason="signal",
  )
  assert out["sell_ready"] is True
  assert out["sell_gate"] == "2/3"
  assert out["why"].startswith("SELL in ·")
  assert "VWAP" in out["why"]
  assert "swing" in out["why"]


def test_flag_hit_and_miss():
  strat = {
    "min_rules_match": 1,
    "long_rules": [{"feat": "squeeze_break_up", "op": "eq1", "thr": 0.5, "w": 1.0}],
    "short_rules": [{"feat": "macd_cross_dn", "op": "eq1", "thr": 0.5, "w": 1.0}],
  }
  out = format_watch_expect(strat, {"squeeze_break_up": 1.0, "macd_cross_dn": 0.0})
  assert out["buy_lines"][0]["text"] == "squeeze↑ 1 = 1"
  assert out["sell_lines"][0]["text"] == "MACD↓ 0 = 1"
  assert out["buy_ready"] is True
  assert out["sell_ready"] is False
  assert "wait ML/score/chase" in out["why"] or "wait B " in out["why"] or "ML" in out["why"]
  assert out["wait"] == "ML≈"
  assert out["wait_code"] == "ml"
  assert "≈" in out["ml_buy"]


def test_gate_is_hits_over_total_rules_not_min_need():
  strat = {
    "min_rules_match": 1,
    "long_rules": [{"feat": "macd_hist", "op": "gt", "thr": 0.19, "w": 1.0}],
    "short_rules": [
      {"feat": "price_vs_ema21", "op": "gt", "thr": 1.06, "w": 7.0},
      {"feat": "price_vs_ema50", "op": "gt", "thr": 0.53, "w": 4.0},
      {"feat": "ema_slope_21", "op": "gt", "thr": 0.10, "w": 1.0},
    ],
  }
  out = format_watch_expect(
    strat,
    {"macd_hist": -0.036, "price_vs_ema21": 1.20, "price_vs_ema50": 1.44, "ema_slope_21": 0.064},
    action="FLAT",
    reason="no_signal",
  )
  assert out["sell_gate"] == "2/3"
  assert out["sell_ready"] is True
  assert out["buy_gate"] == "0/1"
  assert "2/1" not in out["sell_gate"]

def test_hard_gate_why():
  out = format_watch_expect(
    {"min_rules_match": 1, "long_rules": [], "short_rules": []},
    {},
    action="FLAT",
    reason="min_bars_between",
  )
  assert out["why"] == "too close to last trade"
  assert out["wait"] == "Gap"


def test_session_wait_even_when_sell_rules_hit():
  strat = {
    "min_rules_match": 1,
    "session_filter": True,
    "session_start_hour": 7,
    "session_end_hour": 20,
    "long_rules": [{"feat": "macd_hist", "op": "gt", "thr": 0.1, "w": 1.0}],
    "short_rules": [
      {"feat": "price_vs_ema21", "op": "gt", "thr": 1.0, "w": 1.0},
      {"feat": "ema_slope_21", "op": "gt", "thr": 0.05, "w": 1.0},
    ],
  }
  out = format_watch_expect(
    strat,
    {"macd_hist": -0.01, "price_vs_ema21": 1.2, "ema_slope_21": 0.1},
    action="FLAT",
    reason="no_signal",
    bar_time="2026.08.21 02:15",
  )
  assert out["sell_ready"] is True
  assert out["sell_gate"] == "2/2"
  assert out["wait"] == "Sess 2h"
  assert out["wait_code"] == "session"
  assert out["session_ok"] is False
  assert out["session_gate"] == "2/7-20"
  assert "session 02h" in out["why"]
  assert "need 7-20" in out["why"]


def test_chase_wait_when_session_open():
  strat = {
    "min_rules_match": 1,
    "session_filter": True,
    "session_start_hour": 7,
    "session_end_hour": 20,
    "anti_chase": True,
    "anti_chase_rsi_short_max": 58.0,
    "anti_chase_logic": "or",
    "short_rules": [{"feat": "price_vs_ema21", "op": "gt", "thr": 1.0, "w": 1.0}],
    "long_rules": [{"feat": "macd_hist", "op": "gt", "thr": 0.2, "w": 1.0}],
  }
  out = format_watch_expect(
    strat,
    {"price_vs_ema21": 1.4, "macd_hist": 0.0, "rsi": 61.0},
    action="FLAT",
    reason="no_signal",
    bar_time="2026.08.21 10:15",
  )
  assert out["sell_ready"] is True
  assert out["session_ok"] is True
  assert out["wait"] == "Chase"
  assert "chase" in out["why"].lower()


def test_collect_model_lines_primary_heaviest_only():
  strat = {
    "anti_chase": True,
    "anti_chase_rsi_short_max": 58,
    "anti_chase_rsi_long_min": 42,
    "long_rules": [
      {"feat": "squeeze_break_up", "op": "eq1", "thr": 0.5, "w": 0.07},
      {"feat": "session_vwap_dist", "op": "lt", "thr": -1.415, "w": 64.0},
    ],
    "short_rules": [
      {"feat": "macd_cross_dn", "op": "eq1", "thr": 0.5, "w": 0.0},
      {"feat": "session_vwap_dist", "op": "gt", "thr": 0.108, "w": 5.96},
    ],
  }
  lines = collect_model_lines(strat)
  assert set(lines) == {"session_vwap_dist"}
  assert {row["side"] for row in lines["session_vwap_dist"]} == {"B", "S"}
  assert "rsi" not in lines
  assert "htf_trend" not in lines
  assert "squeeze_break_up" not in lines
  assert "macd_cross_dn" not in lines
  empty_sel = collect_model_lines(strat, selected=[])
  assert set(empty_sel) == {"session_vwap_dist"}


def test_collect_model_lines_selected_adds_ticked_rules():
  strat = {
    "long_rules": [
      {"feat": "squeeze_break_up", "op": "eq1", "thr": 0.5, "w": 0.07},
      {"feat": "session_vwap_dist", "op": "lt", "thr": -1.415, "w": 64.0},
    ],
    "short_rules": [
      {"feat": "macd_cross_dn", "op": "eq1", "thr": 0.5, "w": 0.0},
      {"feat": "session_vwap_dist", "op": "gt", "thr": 0.108, "w": 5.96},
    ],
  }
  lines = collect_model_lines(
    strat,
    selected=[
      ("session_vwap_dist", "B", -1.415),
      ("squeeze_break_up", "B", 0.5),
      ("session_vwap_dist", "S", 0.108),
    ],
  )
  assert set(lines) == {"session_vwap_dist", "squeeze_break_up"}
  assert {row["side"] for row in lines["session_vwap_dist"]} == {"B", "S"}
  assert lines["squeeze_break_up"][0]["side"] == "B"
  assert "macd_cross_dn" not in lines


def test_load_week_strategy_uses_schedule_without_live_weeks(tmp_path, monkeypatch):
  import json
  import watch_expect as we

  tm = tmp_path / "trade_models"
  tm.mkdir()
  mid = "tm_chart"
  (tm / f"{mid}_schedule.json").write_text(
    json.dumps({
      "weekly": [
        {
          "week_start": "2026-08-10",
          "strategy": {
            "long_rules": [
              {"feat": "session_vwap_dist", "op": "lt", "thr": -1.4, "w": 1.0},
            ],
            "short_rules": [
              {"feat": "macd_cross_dn", "op": "eq1", "thr": 0.5, "w": 1.0},
            ],
          },
        }
      ]
    }),
    encoding="utf-8",
  )
  monkeypatch.setattr(we, "RESULTS_DIR", tmp_path)
  strat = we.load_week_strategy(mid)
  assert strat["long_rules"][0]["feat"] == "session_vwap_dist"
  assert collect_model_lines(strat)


def test_collect_watch_lines_dedupes_same_threshold(monkeypatch):
  strats = {
    "tm_a": {
      "long_rules": [{"feat": "session_vwap_dist", "op": "lt", "thr": -1.415, "w": 64.0}],
      "short_rules": [{"feat": "session_vwap_dist", "op": "gt", "thr": 0.108, "w": 5.96}],
    },
    "tm_b": {
      "long_rules": [{"feat": "session_vwap_dist", "op": "lt", "thr": -1.415, "w": 64.0}],
      "short_rules": [{"feat": "price_vs_ema50", "op": "gt", "thr": -0.962, "w": 12.0}],
    },
  }

  import watch_expect as we
  monkeypatch.setattr(we, "load_week_strategy", lambda mid: strats[mid])
  lines = _collect_watch_lines(["tm_a", "tm_b"])
  assert set(lines) == {"session_vwap_dist", "price_vs_ema50"}
  vwap = lines["session_vwap_dist"]
  assert {row["side"] for row in vwap} == {"B", "S"}
  assert len(vwap) == 2
  assert len(lines["price_vs_ema50"]) == 1


def test_build_watch_figure_draws_series_and_expect_lines():
  times = ["2026-08-20 16:00", "2026-08-20 16:15", "2026-08-20 16:30"]
  fig = build_watch_figure(
    title="EURUSD M15 · last 96 bars",
    times=times,
    series={"session_vwap_dist": [-0.4, -0.2, 0.001]},
    lines_by_feat={
      "session_vwap_dist": [
        {"side": "B", "thr": -1.415, "label": "BUY VWAP < -1.42"},
        {"side": "S", "thr": 0.108, "label": "SELL VWAP > 0.108"},
      ],
    },
  )
  assert fig is not None
  assert len(fig.data) == 4
  ys = [trace.y[-1] for trace in fig.data]
  assert 0.001 in ys
  assert -1.415 in ys
  assert 0.108 in ys


def test_build_watch_figure_skips_missing_series():
  fig = build_watch_figure(
    title="empty",
    times=["t1"],
    series={"other": [1.0]},
    lines_by_feat={"session_vwap_dist": [{"side": "B", "thr": -1.0}]},
  )
  assert fig is None


def test_hit_x_snaps_to_visible_time_axis():
  times = ["2026-08-21 08:00", "2026-08-21 08:15", "2026-08-21 08:30"]
  assert _hit_x_for_axis("2026.08.21 08:15", times) == "2026-08-21 08:15"
  assert _hit_x_for_axis("2026.08.21 08:16", times) == "2026-08-21 08:15"
  assert _hit_x_for_axis("2026.08.20 08:00", times) is None


def test_build_watch_figure_draws_hit_vlines():
  times = ["2026-08-21 08:00", "2026-08-21 08:15", "2026-08-21 08:30", "2026-08-21 08:45"]
  fig = build_watch_figure(
    title="",
    times=times,
    series={"session_vwap_dist": [-0.4, -0.2, 0.001, 0.02], "rsi": [52, 55, 48, 50]},
    lines_by_feat={
      "session_vwap_dist": [{"side": "S", "thr": 0.108, "label": "SELL VWAP"}],
      "rsi": [{"side": "S", "thr": 58, "label": "SELL RSI"}],
    },
    hit_times=[
      {
        "time": "2026.08.21 08:00",
        "exit_time": "2026.08.21 08:30",
        "side": "SELL",
        "status": "CLOSED",
        "result": "LOSS",
      },
      {
        "time": "2026.08.21 08:15",
        "exit_time": "2026.08.21 08:45",
        "side": "BUY",
        "status": "CLOSED",
        "result": "WIN",
      },
    ],
  )
  assert fig is not None
  shapes = list(fig.layout.shapes or [])
  xs = [str(s.x0) for s in shapes if getattr(s, "type", None) == "line"]
  assert "2026-08-21 08:00" in xs
  assert "2026-08-21 08:15" in xs
  assert "2026-08-21 08:30" in xs
  rects = [s for s in shapes if getattr(s, "type", None) == "rect"]
  loss_rect = next(s for s in rects if str(s.x0) == "2026-08-21 08:00")
  win_rect = next(s for s in rects if str(s.x0) == "2026-08-21 08:15")
  assert "190, 18, 60" in str(loss_rect.fillcolor)
  assert "15, 118, 110" in str(win_rect.fillcolor)
  texts = [str(a.text) for a in (fig.layout.annotations or [])]
  assert "S 08:00" in texts
  assert "X 08:30" in texts
  assert "B 08:15" in texts


def test_broker_wall_to_display_is_vietnam_time():
  summer = broker_wall_to_display("2026.08.21 16:30")
  assert summer.hour == 20
  assert summer.minute == 30
  winter = broker_wall_to_display("2026.01.15 16:30")
  assert winter.hour == 21
  assert winter.minute == 30


def test_chart_tail_grows_for_month_and_all():
  assert _chart_tail_for_period("today") == 720
  assert _chart_tail_for_period("week") == 720
  assert _chart_tail_for_period("month") >= 2500
  assert _chart_tail_for_period("all") > _chart_tail_for_period("month")


def test_slice_pack_to_period_today_is_vietnam_day():
  from datetime import datetime
  from zoneinfo import ZoneInfo

  now = datetime(2026, 8, 21, 20, 44, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
  pack = {
    "times": [
      "2026.08.20 22:00",  # VN 2026-08-21 02:00 — still previous VN day? 22:00 broker +4 = 02:00 next VN day Aug 21
      "2026.08.20 16:00",  # VN 20:00 Aug 20 — yesterday
      "2026.08.21 08:00",  # VN 12:00 Aug 21
      "2026.08.21 16:30",  # VN 20:30 Aug 21
    ],
    "series": {"rsi": [1, 2, 3, 4]},
  }
  out = slice_pack_to_period(pack, "today", now=now)
  assert out["times"] == ["2026.08.20 22:00", "2026.08.21 08:00", "2026.08.21 16:30"]
  assert out["series"]["rsi"] == [1, 3, 4]
  week = slice_pack_to_period(pack, "week", now=now)
  assert "2026.08.20 16:00" in week["times"]
  month = slice_pack_to_period(pack, "month", now=now)
  assert len(month["times"]) == 4
  allp = slice_pack_to_period(pack, "all", now=now)
  assert allp["times"] == pack["times"]


def test_period_fill_marks_follow_now_window():
  from datetime import datetime
  from zoneinfo import ZoneInfo

  now = datetime(2026, 8, 21, 20, 44, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
  trades = [
    {"model_id": "tm_a", "status": "CLOSED", "entry_time": "2026.08.20 16:00", "direction": "SELL"},
    {"model_id": "tm_a", "status": "CLOSED", "entry_time": "2026.08.21 08:00", "exit_time": "2026.08.21 10:00", "direction": "SELL", "result": "LOSS", "profit": -8.2},
    {"model_id": "tm_a", "status": "OPEN", "entry_time": "2026.08.21 15:15", "direction": "SELL"},
    {"model_id": "tm_b", "status": "CLOSED", "entry_time": "2026.08.21 09:00", "direction": "BUY"},
  ]
  day = period_fill_marks(trades, model_id="tm_a", period="today", now=now)
  assert [h["time"] for h in day] == ["2026.08.21 08:00", "2026.08.21 15:15"]
  assert day[0]["exit_time"] == "2026.08.21 10:00"
  assert day[0]["result"] == "LOSS"
  assert day[1]["exit_time"] is None
  assert day[1]["result"] is None
  week = period_fill_marks(trades, model_id="tm_a", period="week", now=now)
  assert len(week) == 3
  assert period_fill_marks(trades, model_id="tm_b", period="today", now=now)[0]["side"] == "BUY"


def test_score_wait_when_rules_hit_but_combined_low():
  strat = {
    "min_rules_match": 2,
    "score_threshold": 0.6,
    "ml_prob_min": 0.4,
    "long_rules": [
      {"feat": "a", "op": "gt", "thr": 0.0, "w": 0.05},
      {"feat": "b", "op": "gt", "thr": 0.0, "w": 0.05},
    ],
    "short_rules": [],
  }
  out = format_watch_expect(
    strat, {"a": 1.0, "b": 1.0},
    dumped={"ml_live": True, "buy": {"ml": 0.5}},
  )
  assert out["buy_ready"] is True
  assert out["wait_code"] == "score"
  assert out["wait"] == "Score"
  assert "wait B " in out["why"]


def test_ml_wait_uses_engine_probability():
  strat = {
    "min_rules_match": 1,
    "score_threshold": 0.6,
    "ml_prob_min": 0.40,
    "long_rules": [{"feat": "a", "op": "gt", "thr": 0.0, "w": 2.0}],
    "short_rules": [],
  }
  out = format_watch_expect(
    strat, {"a": 1.0},
    dumped={"ml_live": True, "buy": {"ml": 0.31, "score": 1.4, "score_ok": True, "ml_ok": False}},
  )
  assert out["wait_code"] == "ml"
  assert out["wait"] == "ML"
  assert "0.31" in out["ml_buy"]
  assert "≈" not in out["ml_buy"]


def test_gap_countdown_same_broker_day():
  strat = {
    "min_rules_match": 1,
    "min_bars_between": 12,
    "score_threshold": 0.6,
    "long_rules": [{"feat": "a", "op": "gt", "thr": 0.0, "w": 2.0}],
    "short_rules": [],
  }
  out = format_watch_expect(
    strat, {"a": 1.0},
    bar_time="2026.08.21 12:00",
    fills=[{"time": "2026.08.21 11:00"}],
    timeframe="M15",
    dumped={"ml_live": True, "buy": {"ml": 0.55, "score": 1.4, "score_ok": True, "ml_ok": True}},
  )
  assert out["gap"] == "4/12"
  assert out["gap_ok"] is False
  assert out["wait_code"] == "gap"
  assert "4/12" in out["why"]


def test_extra_gate_lines_add_rsi_chase_and_htf():
  from watch_expect import extra_gate_lines
  lines = extra_gate_lines({
    "anti_chase": True,
    "anti_chase_rsi_short_max": 58,
    "anti_chase_rsi_long_min": 42,
    "anti_chase_vwap_short_max": 1.5,
  })
  assert "rsi" in lines
  assert {row["side"] for row in lines["rsi"]} == {"B", "S"}
  assert "htf_trend" in lines
  assert "session_vwap_dist" in lines


def test_gate_chips_follow_displayed_values():
  """Chip color follows the numbers: Score miss, ML/RSI/HTF/PA hit."""
  strat = {
    "min_rules_match": 2,
    "score_threshold": 0.6,
    "ml_prob_min": 0.4,
    "anti_chase": True,
    "anti_chase_fixed_rsi": 55.0,
    "long_rules": [{"feat": "a", "op": "gt", "thr": 1.0, "w": 1.0}],
    "short_rules": [{"feat": "b", "op": "gt", "thr": 1.0, "w": 1.0}],
  }
  out = format_watch_expect(
    strat,
    {
      "a": 0.0,
      "b": 0.0,
      "rsi": 34.8,
      "htf_trend": 1.0,
      "confluence_long": 0.5,
      "confluence_short": 0.5,
    },
  )
  assert out["buy_ready"] is False
  assert out["sell_ready"] is False
  assert out["score_ok"] is False
  assert out["ml_ok"] is True
  assert "≈" in out["ml_buy"]
  assert out["rsi_ok"] is True
  assert "34.8" in out["rsi_text"]
  assert "55" in out["rsi_text"]
  assert out["htf_ok"] is True
  assert out["pa_ok"] is True