"""Khóa hợp đồng fill Bid/Ask dùng chung miner / nhãn / paper / live projection."""
from __future__ import annotations

import importlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from execution import (
  PIP,
  entry_fill_price,
  hit_sl_tp,
  limit_exit_price,
  market_exit_price,
  plan_levels,
  rebase_levels,
  stop_exit_price,
)
from mt5_bridge.paper_fill import PaperBook
from strategy_miner import MinedStrategy, _label_outcomes, backtest_mined

SPREAD = 1.9
SLIP = 0.3
TRAIN_ROOT = Path(__file__).resolve().parents[3]


def test_buy_entry_is_ask_plus_slip():
  bid = 1.16000
  assert entry_fill_price(bid, 1, SPREAD, SLIP) == pytest.approx(
    bid + SPREAD * PIP + SLIP * PIP,
  )


def test_sell_entry_is_bid_minus_slip():
  bid = 1.16000
  assert entry_fill_price(bid, -1, SPREAD, SLIP) == pytest.approx(bid - SLIP * PIP)


def test_sell_sl_needs_ask_not_bid_wick():
  sl = 1.16768
  reason, _ = hit_sl_tp(-1, 1.16740, 1.16700, sl, 1.16600, SPREAD, SLIP)
  assert reason is None
  reason, fill = hit_sl_tp(-1, 1.16760, 1.16734, sl, 1.16600, SPREAD, SLIP)
  assert reason == "sl"
  assert fill == pytest.approx(stop_exit_price(sl, -1, SLIP))


def test_tp_is_exact_sl_has_adverse_slip():
  tp = 1.10200
  sl = 1.09900
  reason, fill = hit_sl_tp(1, 1.10300, 1.10000, sl, tp, SPREAD, SLIP)
  assert reason == "tp"
  assert fill == pytest.approx(limit_exit_price(tp))
  assert fill == pytest.approx(tp)

  reason, fill = hit_sl_tp(1, 1.10050, 1.09850, sl, tp, SPREAD, SLIP)
  assert reason == "sl"
  assert fill == pytest.approx(stop_exit_price(sl, 1, SLIP))
  assert fill < sl


def test_plan_levels_buy_geometry():
  entry, sl, tp, risk = plan_levels(1.10, 1, 0.0004, 0.9, 2.5, SPREAD, SLIP)
  assert entry == pytest.approx(entry_fill_price(1.10, 1, SPREAD, SLIP))
  assert risk == pytest.approx(0.9 * 0.0004 + SPREAD * PIP)
  assert sl == pytest.approx(entry - risk)
  assert tp == pytest.approx(entry + risk * 2.5)


class _ParityFm:
  def __init__(self):
    n = 12
    self.index = pd.date_range("2026-08-26 08:00", periods=n, freq="15min")
    self.n = n
    self.warmup = 0
    self.open = np.full(n, 1.10000)
    self.high = np.full(n, 1.10010)
    self.low = np.full(n, 1.09985)
    self.close = np.full(n, 1.10000)
    self.atr = np.full(n, 0.000333)
    self.hours = self.index.hour.to_numpy()
    self.high[2] = 1.10350
    self.low[5] = 1.09600


def _full_strat(**kwargs):
  defaults = dict(
    atr_mult_sl=0.9, rr_ratio=2.0, max_hold_bars=96, max_trades_per_day=9,
    session_filter=False, min_bars_between=1, exit_mode="full", anti_chase=False,
  )
  defaults.update(kwargs)
  return MinedStrategy(**defaults)


def test_backtest_mined_matches_paperbook_r(tmp_path: Path):
  fm = _ParityFm()
  signals = np.zeros(fm.n, dtype=np.int8)
  signals[0] = 1
  strat = _full_strat()
  trades = backtest_mined(
    fm, strat, signals, 0, fm.n, spread_pips=SPREAD, slippage_pips=SLIP,
  )
  assert len(trades) == 1

  planned = plan_levels(
    float(fm.open[1]), 1, float(fm.atr[0]), strat.atr_mult_sl, strat.rr_ratio,
    SPREAD, SLIP,
  )
  book = PaperBook(
    bridge_dir=tmp_path, model_id="tm_parity",
    spread_pips=SPREAD, slippage_pips=SLIP,
  )
  book.queue_decision({
    "action": "BUY",
    "signal_id": "sig_parity",
    "entry": planned[0],
    "sl": planned[1],
    "tp": planned[2],
    "rr": strat.rr_ratio,
    "exit_mode": "full",
    "max_hold_bars": strat.max_hold_bars,
    "model_id": "tm_parity",
  })
  fills = []
  for i in range(1, fm.n):
    fills.extend(book.on_bar(
      open_=float(fm.open[i]), high=float(fm.high[i]),
      low=float(fm.low[i]), close=float(fm.close[i]),
      bar_time=str(fm.index[i]),
    ))
    if any(f.get("event") == "close" for f in fills):
      break
  close = next(f for f in fills if f["event"] == "close")
  open_f = next(f for f in fills if f["event"] == "open")
  assert open_f["price"] == pytest.approx(trades[0].entry_price, abs=1e-12)
  assert close["price"] == pytest.approx(trades[0].exit_price, abs=1e-12)
  paper_r = (close["price"] - open_f["price"]) / abs(open_f["price"] - open_f["sl"])
  assert paper_r == pytest.approx(trades[0].r_multiple, abs=1e-9)


def test_label_outcomes_match_backtest_direction():
  fm = _ParityFm()
  long_win, short_win = _label_outcomes(
    fm, 0, fm.n, rr=2.0, atr_mult=0.9, max_hold_bars=8,
    spread_pips=SPREAD, slippage_pips=SLIP,
  )
  signals = np.zeros(fm.n, dtype=np.int8)
  signals[0] = 1
  buy = backtest_mined(
    fm, _full_strat(max_hold_bars=8), signals, 0, fm.n,
    spread_pips=SPREAD, slippage_pips=SLIP,
  )
  assert len(buy) == 1
  assert (long_win[0] == 1) == (buy[0].r_multiple > 0)

  signals[0] = -1
  sell = backtest_mined(
    fm, _full_strat(max_hold_bars=8), signals, 0, fm.n,
    spread_pips=SPREAD, slippage_pips=SLIP,
  )
  assert len(sell) == 1
  assert (short_win[0] == 1) == (sell[0].r_multiple > 0)


def test_no_mid_adjust_helpers_remain():
  roots = [
    TRAIN_ROOT / "cores" / "m15",
    TRAIN_ROOT / "gui",
    TRAIN_ROOT / "scripts",
  ]
  skip_names = {"test_fill_contract.py"}
  hits: list[str] = []
  for root in roots:
    if not root.exists():
      continue
    for path in root.rglob("*.py"):
      if path.name in skip_names or "_archive" in path.parts:
        continue
      text = path.read_text(encoding="utf-8", errors="replace")
      if "adjust_entry_price" in text or "adjust_exit_price" in text:
        hits.append(str(path.relative_to(TRAIN_ROOT)))
  assert hits == [], hits


def test_desk_yaml_spreads():
  import yaml
  e21 = yaml.safe_load((TRAIN_ROOT / "desks" / "e21.yaml").read_text(encoding="utf-8"))
  g23 = yaml.safe_load((TRAIN_ROOT / "desks" / "g23.yaml").read_text(encoding="utf-8"))
  assert e21["spread_pips"] == 1.9
  assert e21["slippage_pips"] == 0.3
  assert g23["spread_pips"] == 2.3
  assert g23["slippage_pips"] == 0.3


def test_config_reads_desk_spread(monkeypatch):
  monkeypatch.setenv("TRAINAPP_ROOT", str(TRAIN_ROOT))
  monkeypatch.setenv("TRAINAPP_DESK", "e21")
  import config as cfg
  importlib.reload(cfg)
  assert cfg.DEFAULT_SPREAD_PIPS == pytest.approx(1.9)
  assert cfg.DEFAULT_SLIPPAGE_PIPS == pytest.approx(0.3)
  monkeypatch.setenv("TRAINAPP_DESK", "g23")
  importlib.reload(cfg)
  assert cfg.DEFAULT_SPREAD_PIPS == pytest.approx(2.3)
  monkeypatch.delenv("TRAINAPP_DESK", raising=False)
  monkeypatch.delenv("TRAINAPP_ROOT", raising=False)
  importlib.reload(cfg)


def test_rebase_preserves_risk():
  sl, tp, risk = rebase_levels(-1, 1.15478, 1.15446, 1.15482, 1.15339, 3.0)
  assert risk == pytest.approx(abs(1.15446 - 1.15482))
  assert sl == pytest.approx(1.15478 + risk)
  assert tp == pytest.approx(1.15478 - risk * 3.0)


def test_market_timeout_sell_uses_ask():
  close = 1.16000
  px = market_exit_price(close, -1, SPREAD, SLIP)
  assert px == pytest.approx(close + SPREAD * PIP + SLIP * PIP)
  px_buy = market_exit_price(close, 1, SPREAD, SLIP)
  assert px_buy == pytest.approx(close - SLIP * PIP)
