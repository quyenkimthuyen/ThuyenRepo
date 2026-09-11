"""Tests for Compare Trade — paper fill + multi-model isolation + charts."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from gui.bridge_model_monitor import (
  build_multi_model_equity_figure,
  build_multi_model_monthly_figure,
  build_multi_model_daily_figure,
)
from mt5_bridge.compare_runner import (
  additional_spread_points,
  bump_spread_points,
  clamp_additional_spread_pips,
  slice_replay_frame,
)
from mt5_bridge.engine import (
  BridgeEngine,
  _causal_scan_end,
  _journal_open_and_day_count,
  _journal_last_auto_signal_idx,
  _normalize,
  _spacing_ok,
)
from mt5_bridge.history_sync import utc_to_broker_time
from mt5_bridge.paper_fill import PaperBook
from mt5_bridge.trade_journal import clear_trades, filter_trades, load_trades, save_trades


def _bar_time(ts: pd.Timestamp) -> str:
  return utc_to_broker_time(ts).strftime("%Y.%m.%d %H:%M")


def test_paper_fill_open_next_bar_and_tp(tmp_path: Path):
  book = PaperBook(bridge_dir=tmp_path, model_id="tm_a")
  decision = {
    "action": "BUY",
    "signal_id": "sig_buy_1",
    "entry": 1.1000,
    "sl": 1.0990,
    "tp": 1.1020,
    "rr": 2.0,
    "exit_mode": "full",
    "max_hold_bars": 96,
    "model_id": "tm_a",
  }
  # Decision queued → open at next bar Ask; SL/TP active on the fill bar
  book.queue_decision(decision)
  assert book.pending is not None
  fills0 = book.on_bar(
    open_=1.1005, high=1.1008, low=1.1002, close=1.1006,
    bar_time="2026.01.02 08:00", spread_points=20,
  )
  assert len(fills0) == 1
  assert fills0[0]["event"] == "open"
  assert fills0[0]["price"] == pytest.approx(1.10070)
  assert book.open is True
  # Next bar: held becomes 2 → SL/TP active; high hits TP
  fills1 = book.on_bar(
    open_=1.1005, high=1.1030, low=1.1000, close=1.1025,
    bar_time="2026.01.02 08:15", spread_points=20,
  )
  assert len(fills1) == 1
  assert fills1[0]["event"] == "close"
  assert fills1[0]["reason"] == "tp"
  trades = load_trades(tmp_path)
  closed = [t for t in trades if t.get("status") == "CLOSED"]
  assert len(closed) == 1
  assert closed[0]["model_id"] == "tm_a"
  assert closed[0]["r"] is not None or closed[0]["profit"] is not None


def test_paper_fill_sl_sell(tmp_path: Path):
  book = PaperBook(bridge_dir=tmp_path, model_id="tm_b")
  book.queue_decision({
    "action": "SELL",
    "signal_id": "sig_sell_1",
    "entry": 1.2000,
    "sl": 1.2010,
    "tp": 1.1980,
    "rr": 2.0,
    "exit_mode": "full",
    "max_hold_bars": 10,
    "model_id": "tm_b",
  })
  book.on_bar(open_=1.2000, high=1.2002, low=1.1998, close=1.1999, bar_time="2026.02.01 10:00")
  book.on_bar(open_=1.1999, high=1.2001, low=1.1995, close=1.1998, bar_time="2026.02.01 10:15")
  fills = book.on_bar(open_=1.2002, high=1.2015, low=1.1990, close=1.2012, bar_time="2026.02.01 10:30")
  assert len(fills) == 1
  assert fills[0]["reason"] == "sl"


def test_journal_open_scoped_by_model_id(tmp_path: Path):
  clear_trades(tmp_path)
  save_trades([
    {
      "id": "a1", "signal_id": "a1", "status": "OPEN", "mode": "auto",
      "model_id": "tm_a", "entry_time": "2026-01-05 09:00", "direction": "BUY",
    },
    {
      "id": "b1", "signal_id": "b1", "status": "CLOSED", "mode": "auto",
      "model_id": "tm_b", "entry_time": "2026-01-05 11:00", "direction": "SELL",
    },
  ], tmp_path)
  day = pd.Timestamp("2026-01-05").date()
  open_a, day_a = _journal_open_and_day_count(tmp_path, day, model_id="tm_a")
  open_b, day_b = _journal_open_and_day_count(tmp_path, day, model_id="tm_b")
  assert open_a is True
  assert day_a == 1
  assert open_b is False
  assert day_b == 1


def test_journal_open_ignores_empty_model_id_when_scoped(tmp_path: Path):
  """BUG-04: orphan/legacy rows without model_id must not match every model."""
  clear_trades(tmp_path)
  save_trades([
    {
      "id": "orphan", "signal_id": "o1", "status": "OPEN", "mode": "auto",
      "model_id": "", "entry_time": "2026-01-05 09:00", "direction": "BUY",
    },
    {
      "id": "a1", "signal_id": "a1", "status": "CLOSED", "mode": "auto",
      "model_id": "tm_a", "entry_time": "2026-01-05 11:00", "direction": "BUY",
    },
  ], tmp_path)
  day = pd.Timestamp("2026-01-05").date()
  open_a, day_a = _journal_open_and_day_count(tmp_path, day, model_id="tm_a")
  open_b, day_b = _journal_open_and_day_count(tmp_path, day, model_id="tm_b")
  assert open_a is False
  assert day_a == 1
  assert open_b is False
  assert day_b == 0


class _FmStub:
  def __init__(self, index: list[pd.Timestamp]):
    self.index = pd.DatetimeIndex(index)


def test_journal_spacing_enforces_min_bars_between(tmp_path: Path):
  from mt5_bridge.history_sync import parse_broker_time

  bars = [
    parse_broker_time(f"2026.01.05 {h:02d}:{m:02d}")
    for h, m in ((9, 0), (9, 15), (9, 30), (9, 45), (10, 0))
  ]
  fm = _FmStub(bars)
  clear_trades(tmp_path)
  save_trades([
    {
      "id": "t1", "signal_id": "s1", "status": "CLOSED", "mode": "auto",
      "model_id": "tm_a", "bar_time": "2026.01.05 09:00", "direction": "BUY",
      "entry_time": "2026.01.05 09:00",
    },
  ], tmp_path)
  day = utc_to_broker_time(bars[0]).date()
  assert _journal_last_auto_signal_idx(fm, tmp_path, day, model_id="tm_a") == 0

  ok_near, _, since_near = _spacing_ok(
    fm, tmp_path, 2, day, model_id="tm_a", min_bars_between=12,
  )
  assert since_near == 2
  assert ok_near is False

  ok_far, _, since_far = _spacing_ok(
    fm, tmp_path, 12, day, model_id="tm_a", min_bars_between=12,
  )
  assert since_far == 12
  assert ok_far is True


def test_journal_spacing_scoped_by_model_id(tmp_path: Path):
  from mt5_bridge.history_sync import parse_broker_time

  bars = [parse_broker_time("2026.01.05 09:00"), parse_broker_time("2026.01.05 09:15")]
  fm = _FmStub(bars)
  clear_trades(tmp_path)
  save_trades([
    {
      "id": "b1", "signal_id": "b1", "status": "CLOSED", "mode": "auto",
      "model_id": "tm_b", "bar_time": "2026.01.05 09:00", "direction": "SELL",
    },
  ], tmp_path)
  day = utc_to_broker_time(bars[0]).date()
  assert _journal_last_auto_signal_idx(fm, tmp_path, day, model_id="tm_a") is None
  ok, _, _ = _spacing_ok(fm, tmp_path, 1, day, model_id="tm_a", min_bars_between=12)
  assert ok is True


def test_compare_bar_dict_uses_desk_symbol(monkeypatch):
  """BUG-03: replay bars must not hardcode EURUSD on GBP desks."""
  from mt5_bridge import compare_runner

  monkeypatch.setattr(compare_runner, "_replay_symbol", lambda: "GBPUSD")
  ts = pd.Timestamp("2026-07-15 10:00:00")
  row = pd.Series({"Open": 1.25, "High": 1.26, "Low": 1.24, "Close": 1.255, "Volume": 10})
  bar = compare_runner._bar_dict(ts, row)
  assert bar["symbol"] == "GBPUSD"


def test_filter_trades_requires_model_id(tmp_path: Path):
  save_trades([
    {"id": "1", "status": "CLOSED", "mode": "auto", "model_id": "tm_a", "entry_time": "2026-01-01"},
    {"id": "2", "status": "CLOSED", "mode": "auto", "model_id": "tm_b", "entry_time": "2026-01-01"},
  ], tmp_path)
  only_a = filter_trades(bridge_dir=tmp_path, model_id="tm_a")
  assert len(only_a) == 1
  assert only_a[0]["model_id"] == "tm_a"


def test_two_paper_books_do_not_block_each_other(tmp_path: Path):
  dir_a = tmp_path / "a"
  dir_b = tmp_path / "b"
  dir_a.mkdir()
  dir_b.mkdir()
  a = PaperBook(bridge_dir=dir_a, model_id="tm_a")
  b = PaperBook(bridge_dir=dir_b, model_id="tm_b")
  decision = {
    "action": "BUY",
    "entry": 1.10,
    "sl": 1.09,
    "tp": 1.12,
    "rr": 2.0,
    "exit_mode": "full",
    "max_hold_bars": 5,
  }
  a.queue_decision({**decision, "signal_id": "a1", "model_id": "tm_a"})
  b.queue_decision({**decision, "signal_id": "b1", "model_id": "tm_b"})
  a.on_bar(open_=1.10, high=1.11, low=1.095, close=1.105, bar_time="2026.03.01 08:00")
  b.on_bar(open_=1.10, high=1.11, low=1.095, close=1.105, bar_time="2026.03.01 08:00")
  assert a.open and b.open
  assert len(load_trades(dir_a)) == 1
  assert len(load_trades(dir_b)) == 1
  assert load_trades(dir_a)[0]["model_id"] == "tm_a"
  assert load_trades(dir_b)[0]["model_id"] == "tm_b"


def test_slice_replay_frame_by_broker_date():
  idx = pd.to_datetime([
    "2026-01-01 10:00",
    "2026-01-02 10:00",
    "2026-01-03 10:00",
  ], utc=True).tz_convert(None)
  df = _normalize(pd.DataFrame({
    "Open": [1.0, 1.1, 1.2],
    "High": [1.01, 1.11, 1.21],
    "Low": [0.99, 1.09, 1.19],
    "Close": [1.005, 1.105, 1.205],
    "Volume": [1, 1, 1],
  }, index=idx))
  out = slice_replay_frame(df, "2026-01-02", "2026-01-02")
  assert len(out) == 1


def test_clamp_and_points_for_additional_spread():
  assert clamp_additional_spread_pips(None) == 0.0
  assert clamp_additional_spread_pips(-1) == 0.0
  assert clamp_additional_spread_pips(9) == 5.0
  assert additional_spread_points(0) == 0
  assert additional_spread_points(1.0) == 10
  assert additional_spread_points(0.5) == 5


def test_bump_spread_points_only_on_replay_index():
  idx = pd.to_datetime(["2026-01-01 10:00", "2026-01-02 10:00"], utc=True).tz_convert(None)
  df = pd.DataFrame({
    "Open": [1.0, 1.1],
    "SpreadPoints": [19.0, 21.0],
  }, index=idx)
  out = bump_spread_points(df, 10, index=idx[1:])
  assert out.loc[idx[0], "SpreadPoints"] == 19.0
  assert out.loc[idx[1], "SpreadPoints"] == 31.0
  assert df.loc[idx[0], "SpreadPoints"] == 19.0  # original unchanged
  assert bump_spread_points(df, 0) is df


def test_paper_fill_additional_spread_widens_buy_ask(tmp_path: Path):
  book = PaperBook(bridge_dir=tmp_path, model_id="tm_a")
  book.queue_decision({
    "action": "BUY",
    "signal_id": "sig_buy_extra",
    "entry": 1.1000,
    "sl": 1.0990,
    "tp": 1.1020,
    "rr": 2.0,
    "exit_mode": "full",
    "max_hold_bars": 96,
    "model_id": "tm_a",
  })
  quote_pts = 20
  extra = additional_spread_points(1.0)  # +10 points = +1 pip
  fills = book.on_bar(
    open_=1.1005, high=1.1008, low=1.1002, close=1.1006,
    bar_time="2026.01.02 08:00", spread_points=quote_pts + extra,
  )
  assert len(fills) == 1
  assert fills[0]["price"] == pytest.approx(1.1005 + (quote_pts + extra) * 0.00001)


def test_compare_bar_dict_adds_extra_spread_points():
  from mt5_bridge import compare_runner

  ts = pd.Timestamp("2026-07-15 10:00:00")
  row = pd.Series({
    "Open": 1.25, "High": 1.26, "Low": 1.24, "Close": 1.255,
    "Volume": 10, "SpreadPoints": 19,
  })
  bar0 = compare_runner._bar_dict(ts, row, 0)
  bar1 = compare_runner._bar_dict(ts, row, 10)
  assert bar0["spread_points"] == 19
  assert bar1["spread_points"] == 29


def test_multi_model_equity_figure_has_two_series():
  eq_a = pd.DataFrame({
    "entry": pd.to_datetime(["2026-01-01", "2026-01-02"]),
    "equity_r": [1.0, 2.0],
    "drawdown_r": [0.0, 0.0],
  })
  eq_b = pd.DataFrame({
    "entry": pd.to_datetime(["2026-01-01", "2026-01-03"]),
    "equity_r": [0.5, 1.5],
    "drawdown_r": [0.0, 0.2],
  })
  fig = build_multi_model_equity_figure({"Model A": eq_a, "Model B": eq_b})
  assert fig is not None
  # equity + dd per model
  assert len(fig.data) >= 2


def test_multi_model_weekly_figure():
  from gui.bridge_model_monitor import build_multi_model_weekly_figure

  w_a = pd.DataFrame({
    "week": ["2026-08-17", "2026-08-24"],
    "total_r": [1.0, -0.5],
    "cum_r": [1.0, 0.5],
  })
  w_b = pd.DataFrame({
    "week": ["2026-08-17", "2026-08-24"],
    "total_r": [0.5, 2.0],
    "cum_r": [0.5, 2.5],
  })
  fig = build_multi_model_weekly_figure({"A": w_a, "B": w_b})
  assert fig is not None
  assert len(fig.data) >= 2


def test_prepare_live_chart_trades_filters_and_colors():
  from mt5_bridge.live_monitor_server import prepare_live_chart_trades

  trades = [
    {"status": "CLOSED", "model_id": "tm_a", "ticket": 1},
    {"status": "OPEN", "model_id": "tm_b", "ticket": 2},
    {"status": "CLOSED", "model_id": "tm_a", "ticket": 3},
  ]
  ids = ["tm_a", "tm_b"]
  labels = {"tm_a": "Alpha", "tm_b": "Beta"}
  all_rows = prepare_live_chart_trades(
    trades, model_ids=ids, model_filter=None, labels=labels,
  )
  assert len(all_rows) == 3
  assert all_rows[0]["model_label"] == "Alpha"
  assert all_rows[0].get("model_color")
  assert all_rows[1]["model_label"] == "Beta"
  one = prepare_live_chart_trades(
    trades, model_ids=ids, model_filter="tm_a", labels=labels,
  )
  assert len(one) == 2
  assert all(t["model_id"] == "tm_a" for t in one)
  assert "model_color" not in one[0]


def test_multi_model_monthly_figure():
  mo_a = pd.DataFrame({
    "month": ["2026-01", "2026-02"],
    "total_r": [2.0, 1.0],
    "cum_r": [2.0, 3.0],
  })
  mo_b = pd.DataFrame({
    "month": ["2026-01", "2026-02"],
    "total_r": [1.0, 2.0],
    "cum_r": [1.0, 3.0],
  })
  fig = build_multi_model_monthly_figure({"A": mo_a, "B": mo_b})
  assert fig is not None
  assert len(fig.data) >= 2


def test_multi_model_daily_figure():
  d_a = pd.DataFrame({
    "day": ["2026-01-05", "2026-01-06"],
    "total_r": [1.0, -0.5],
    "cum_r": [1.0, 0.5],
  })
  d_b = pd.DataFrame({
    "day": ["2026-01-05", "2026-01-06"],
    "total_r": [0.5, 2.0],
    "cum_r": [0.5, 2.5],
  })
  fig = build_multi_model_daily_figure({"A": d_a, "B": d_b})
  assert fig is not None
  assert len(fig.data) >= 2


def test_causal_scan_end_stops_at_closed_bar():
  assert _causal_scan_end(100, 40) == 41
  assert _causal_scan_end(41, 40) == 41
  assert _causal_scan_end(40, 40) == 40


def test_decide_for_bar_does_not_scan_future_week_bars(tmp_path, monkeypatch):
  """Replay with full-week cache must not scan afternoon bars when deciding 08:00."""
  import numpy as np
  from mt5_bridge.history_sync import parse_broker_time, utc_to_broker_time

  stamps = [
    parse_broker_time(f"2026.09.07 {h:02d}:{m:02d}")
    for h in range(7, 18)
    for m in (0, 15, 30, 45)
  ]
  df = _normalize(pd.DataFrame({
    "Open": [1.160 + i * 0.00001 for i in range(len(stamps))],
    "High": [1.161 + i * 0.00001 for i in range(len(stamps))],
    "Low": [1.159 + i * 0.00001 for i in range(len(stamps))],
    "Close": [1.1605 + i * 0.00001 for i in range(len(stamps))],
    "Volume": [10] * len(stamps),
    "SpreadPoints": [16] * len(stamps),
  }, index=pd.DatetimeIndex(stamps)))
  cache = tmp_path / "mt5.parquet"
  df.to_parquet(cache)
  bridge = tmp_path / "bridge"
  bridge.mkdir()

  closed = parse_broker_time("2026.09.07 08:00")
  closed_idx = int(df.index.get_loc(closed))
  week_end_idx = get_week_indices_end(df, closed)
  assert week_end_idx > closed_idx + 1

  captured: dict = {}

  def fake_gen(fm, strat, start_idx=0, end_idx=None, *, include_last_bar=False):
    captured["end_idx"] = end_idx
    captured["start_idx"] = start_idx
    captured["include_last_bar"] = include_last_bar
    captured["fm_n"] = fm.n
    return np.zeros(fm.n, dtype=np.int8)

  class _Strat:
    name = "causal-replay"
    max_trades_per_day = 2
    min_bars_between = 0
    ml_scorer = None
    rr_ratio = 3.0
    atr_mult_sl = 1.05
    exit_mode = "full"
    trail_activate_r = 1.0
    trail_distance_r = 0.5
    max_hold_bars = 64
    tp_ignores_spread_buffer = True
    confirm_r = 0.0
    confirm_wait_bars = 4
    confirm_cancel_r = 0.5

  monkeypatch.setattr("mt5_bridge.engine.generate_signals_mined", fake_gen)
  monkeypatch.setattr("mt5_bridge.engine.backtest_mined", lambda *a, **k: ([], None))
  monkeypatch.setattr("mt5_bridge.engine.explain_bar_gates", lambda *a, **k: None)
  monkeypatch.setattr("mt5_bridge.engine.apply_oos_exit_overlay", lambda s, *_a, **_k: s)

  eng = BridgeEngine(model_id="tm_causal_replay", mt5_cache=cache, bridge_dir=bridge)
  eng._model = {
    "id": "tm_causal_replay",
    "data_source": "mt5_ea",
    "data_timeframe": "M15",
    "feature_schema": 2,
  }
  eng._params = {
    "trade_model_id": "tm_causal_replay",
    "train_weeks": 8,
    "use_learning": False,
    "feature_profile": "current",
    "spread_pips": 1.9,
    "slippage_pips": 0.0,
  }
  eng._df = df.copy()
  eng._remine_week_strategy = lambda **_k: _Strat()

  row = df.loc[closed]
  decision = eng.decide_for_bar({
    "time": utc_to_broker_time(closed).strftime("%Y.%m.%d %H:%M"),
    "open": float(row.Open),
    "high": float(row.High),
    "low": float(row.Low),
    "close": float(row.Close),
    "volume": float(row.Volume),
    "spread_points": 16,
  })
  assert captured.get("end_idx") == closed_idx + 1
  assert captured["end_idx"] < week_end_idx
  assert captured["end_idx"] < captured["fm_n"]
  assert decision.get("reason") in ("no_signal", "no_oos_week", "bar_not_in_series")


def get_week_indices_end(df: pd.DataFrame, ts: pd.Timestamp) -> int:
  from data_loader import get_week_indices
  from paper_monitor import _week_bounds_for_ts

  start, end = _week_bounds_for_ts(ts)
  oos_s, oos_e = get_week_indices(df, start, end)
  assert oos_s is not None
  return int(oos_e)


def test_multi_model_price_figure_markers():
  from gui.bridge_model_monitor import build_multi_model_price_figure

  idx = pd.to_datetime([
    "2026-01-02 08:00",
    "2026-01-02 08:15",
    "2026-01-02 08:30",
    "2026-01-02 08:45",
  ])
  ohlc = pd.DataFrame({
    "Open": [1.10, 1.101, 1.102, 1.1015],
    "High": [1.101, 1.103, 1.104, 1.102],
    "Low": [1.099, 1.100, 1.101, 1.1005],
    "Close": [1.1005, 1.102, 1.1018, 1.1012],
    "Volume": [1, 1, 1, 1],
  }, index=idx)
  trades = {
    "Model A": [{
      "status": "CLOSED",
      "direction": "BUY",
      "entry_time": "2026.01.02 08:15",
      "entry_px": 1.101,
      "exit_time": "2026.01.02 08:45",
      "exit_px": 1.1015,
      "r": 0.5,
      "reason": "tp",
    }],
    "Model B": [{
      "status": "CLOSED",
      "direction": "SELL",
      "entry_time": "2026.01.02 08:00",
      "entry_px": 1.10,
      "exit_time": "2026.01.02 08:30",
      "exit_px": 1.1018,
      "r": -0.8,
      "reason": "sl",
    }],
  }
  fig = build_multi_model_price_figure(ohlc, trades, show_connectors=True)
  assert fig is not None
  # candlestick + entries + exits + connectors
  assert len(fig.data) >= 5
  types = {type(t).__name__ for t in fig.data}
  assert "Candlestick" in types
