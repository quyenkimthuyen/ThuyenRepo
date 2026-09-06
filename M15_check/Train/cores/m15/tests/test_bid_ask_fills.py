"""Lab / Compare fills must match live: BUY Ask, SELL Bid."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from execution import (
  PIP, POINT, adjust_entry_price, adjust_exit_price, spread_from_quote,
)
from feature_engine import FeatureMatrix
from mt5_bridge import history_sync
from mt5_bridge.paper_fill import PaperBook
from strategy_miner import MinedStrategy, backtest_mined


def test_spread_from_quote_prefers_bar_points():
  assert spread_from_quote(1.0, 19) == pytest.approx(19 * POINT)
  assert spread_from_quote(1.9, 0) == pytest.approx(1.9 * PIP)
  assert spread_from_quote(0, 0) == 0.0


def test_buy_entry_is_ask_plus_slip():
  bid = 1.10000
  px = adjust_entry_price(bid, 1, spread_pips=1.9, slippage_pips=0.3)
  assert px == pytest.approx(bid + 1.9 * PIP + 0.3 * PIP)


def test_sell_entry_is_bid_minus_slip():
  bid = 1.10000
  px = adjust_entry_price(bid, -1, spread_pips=1.9, slippage_pips=0.3)
  assert px == pytest.approx(bid - 0.3 * PIP)


def test_timeout_sell_exits_at_ask():
  bid_close = 1.10000
  px = adjust_exit_price(bid_close, -1, spread_pips=2.0, slippage_pips=0.0)
  assert px == pytest.approx(bid_close + 2.0 * PIP)


def test_paper_buy_fills_at_ask(tmp_path: Path):
  book = PaperBook(bridge_dir=tmp_path, model_id="tm_ask")
  book.queue_decision({
    "action": "BUY",
    "signal_id": "s-buy",
    "entry": 1.10000,
    "sl": 1.09900,
    "tp": 1.10200,
    "rr": 2.0,
    "exit_mode": "full",
    "max_hold_bars": 10,
    "spread_pips": 1.0,
  })
  fills = book.on_bar(
    open_=1.10000, high=1.10000, low=1.10000, close=1.10000,
    bar_time="t0", spread_points=20,
  )
  assert len(fills) == 1
  assert fills[0]["price"] == pytest.approx(1.10020)
  assert book.sl == pytest.approx(1.09920)


def test_paper_sell_max_hold_at_ask_close(tmp_path: Path):
  book = PaperBook(bridge_dir=tmp_path, model_id="tm_hold")
  book.queue_decision({
    "action": "SELL",
    "signal_id": "s-hold",
    "entry": 1.10000,
    "sl": 1.12000,
    "tp": 1.08000,
    "rr": 2.0,
    "exit_mode": "full",
    "max_hold_bars": 1,
    "spread_pips": 1.0,
  })
  book.on_bar(
    open_=1.10000, high=1.10010, low=1.09990, close=1.10000,
    bar_time="t0", spread_points=20,
  )
  assert book.open
  fills = book.on_bar(
    open_=1.10000, high=1.10020, low=1.09980, close=1.10010,
    bar_time="t1", spread_points=20,
  )
  assert fills and fills[0]["reason"] == "max_hold"
  assert fills[0]["price"] == pytest.approx(1.10010 + 20 * POINT)


def test_paper_max_hold_zero_stays_open(tmp_path: Path):
  book = PaperBook(bridge_dir=tmp_path, model_id="tm_full")
  book.queue_decision({
    "action": "BUY",
    "signal_id": "s-full",
    "entry": 1.10000,
    "sl": 1.09000,
    "tp": 1.20000,
    "rr": 10.0,
    "exit_mode": "full",
    "max_hold_bars": 0,
  })
  book.on_bar(
    open_=1.10000, high=1.10010, low=1.09990, close=1.10000,
    bar_time="t0", spread_points=20,
  )
  fills = book.on_bar(
    open_=1.10000, high=1.10020, low=1.09980, close=1.10010,
    bar_time="t1", spread_points=20,
  )
  assert fills == []
  assert book.open


def test_backtest_buy_entry_is_ask():
  n = 6
  fm = _bt_fm(n)
  signals = np.zeros(n, dtype=np.int8)
  signals[0] = 1
  strat = MinedStrategy(
    atr_mult_sl=0.9, rr_ratio=3.0, max_hold_bars=96, max_trades_per_day=2,
    session_filter=False, min_bars_between=1, exit_mode="full", anti_chase=False,
  )
  trades = backtest_mined(
    fm, strat, signals, 0, n, spread_pips=1.9, slippage_pips=0.3,
  )
  assert len(trades) == 1
  assert trades[0].entry_price == pytest.approx(1.10 + 1.9 * PIP + 0.3 * PIP)


def test_backtest_prefers_bar_spread_points_over_settings():
  n = 6
  fm = _bt_fm(n)
  fm.spread_points[:] = 0
  fm.spread_points[1] = 24  # fill bar (signal at 0 → entry next open)
  signals = np.zeros(n, dtype=np.int8)
  signals[0] = 1
  strat = MinedStrategy(
    atr_mult_sl=0.9, rr_ratio=3.0, max_hold_bars=96, max_trades_per_day=2,
    session_filter=False, min_bars_between=1, exit_mode="full", anti_chase=False,
  )
  trades = backtest_mined(
    fm, strat, signals, 0, n, spread_pips=1.9, slippage_pips=0.0,
  )
  assert len(trades) == 1
  assert trades[0].entry_price == pytest.approx(1.10 + 24 * POINT)
  assert trades[0].entry_price != pytest.approx(1.10 + 1.9 * PIP)


def test_project_levels_prefers_bar_spread_points():
  from paper_monitor import _project_signal_levels

  fm = _bt_fm(6)
  fm.spread_points[:] = 0
  fm.spread_points[1] = 24
  strat = MinedStrategy(atr_mult_sl=0.9, rr_ratio=3.0)
  proj = _project_signal_levels(fm, strat, 0, 1, spread_pips=1.9, slippage_pips=0.0)
  assert proj is not None
  assert proj["entry_px"] == pytest.approx(round(1.10 + 24 * POINT, 5))
  sl_d = abs(proj["entry_px"] - proj["sl"])
  assert sl_d == pytest.approx(0.9 * float(fm.atr[0]) + 24 * POINT, abs=1.5e-5)


def test_merge_bar_writes_spread_points(tmp_path):
  from mt5_bridge.engine import BridgeEngine

  cache = tmp_path / "iso.parquet"
  seed = pd.DataFrame(
    {
      "Open": [1.1], "High": [1.11], "Low": [1.09], "Close": [1.1],
      "Volume": [1.0], "SpreadPoints": [16.0],
    },
    index=pd.DatetimeIndex([pd.Timestamp("2026-01-02 08:00")]),
  )
  seed.to_parquet(cache)
  eng = BridgeEngine(mt5_cache=cache)
  ts = eng.merge_bar({
    "time": "2026.01.02 12:15",
    "open": 1.2, "high": 1.21, "low": 1.19, "close": 1.20,
    "volume": 5, "spread_points": 33,
  })
  frame = eng.load()
  assert "SpreadPoints" in frame.columns
  assert float(frame.loc[ts, "SpreadPoints"]) == 33.0


def test_history_stores_spread_points(tmp_path, monkeypatch):
  monkeypatch.setattr(history_sync, "MT5_CACHE_PATH", tmp_path / "mt5.parquet")
  monkeypatch.setattr(history_sync, "MT5_META_PATH", tmp_path / "meta.json")
  history_sync.merge_history_bars([{
    "time": "2026.07.15 10:00",
    "open": 1.1, "high": 1.101, "low": 1.099, "close": 1.1005,
    "tick_volume": 10, "spread_points": 24,
  }])
  frame = history_sync.load_mt5_cache()
  assert "SpreadPoints" in frame.columns
  assert float(frame.iloc[0]["SpreadPoints"]) == 24
  fm = FeatureMatrix(frame)
  assert fm.spread_points[0] == 24


class _BtFm:
  def __init__(self, n: int):
    self.index = pd.date_range("2026-08-26 11:00", periods=n, freq="15min")
    self.n = n
    self.warmup = 0
    self.open = np.full(n, 1.10)
    self.high = np.full(n, 1.10012)
    self.low = np.full(n, 1.09990)
    self.close = np.full(n, 1.10)
    self.low[3] = 1.09800
    self.atr = np.full(n, 0.000333)
    self.hours = self.index.hour.to_numpy()
    self.spread_points = np.zeros(n)


def _bt_fm(n: int = 6) -> _BtFm:
  return _BtFm(n)


def test_confirm_stop_fills_on_follow_through():
  n = 8
  fm = _bt_fm(n)
  fm.atr[:] = 0.001
  fm.high[:] = 1.10005
  fm.low[:] = 1.09995
  fm.high[1] = 1.10025  # 0.2R above Bid open with spread=0
  fm.high[4] = 1.10300  # TP
  signals = np.zeros(n, dtype=np.int8)
  signals[0] = 1
  strat = MinedStrategy(
    atr_mult_sl=1.0, rr_ratio=2.0, max_hold_bars=96, max_trades_per_day=2,
    session_filter=False, min_bars_between=1, exit_mode="full", anti_chase=False,
    confirm_r=0.20, confirm_wait_bars=4, confirm_cancel_r=0.50,
  )
  trades = backtest_mined(fm, strat, signals, 0, n, spread_pips=0.0, slippage_pips=0.0)
  assert len(trades) == 1
  assert trades[0].entry_price == pytest.approx(1.10 + 0.20 * 0.001)
  assert trades[0].exit_reason == "tp"


def test_confirm_stop_skips_when_price_dies_first():
  n = 8
  fm = _bt_fm(n)
  fm.atr[:] = 0.001
  fm.high[:] = 1.10005
  fm.low[:] = 1.09995
  fm.low[1] = 1.09940  # 0.6R adverse before confirm
  signals = np.zeros(n, dtype=np.int8)
  signals[0] = 1
  strat = MinedStrategy(
    atr_mult_sl=1.0, rr_ratio=2.0, max_hold_bars=96, max_trades_per_day=2,
    session_filter=False, min_bars_between=1, exit_mode="full", anti_chase=False,
    confirm_r=0.20, confirm_wait_bars=4, confirm_cancel_r=0.50,
  )
  trades = backtest_mined(fm, strat, signals, 0, n, spread_pips=0.0, slippage_pips=0.0)
  assert trades == []

