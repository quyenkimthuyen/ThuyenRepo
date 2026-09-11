"""HistoryFeed / Linux paper fills use Bid/Ask spread like live."""
from __future__ import annotations

import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
if str(LIVE) not in sys.path:
  sys.path.insert(0, str(LIVE))

from replay_paper import ReplayPaperBook, _spread_price  # noqa: E402


def _buy_decision(**kw):
  d = {
    "action": "BUY",
    "signal_id": "s-buy",
    "entry": 1.10000,
    "sl": 1.09900,
    "tp": 1.10200,
    "rr": 2.0,
    "max_hold_bars": 10,
  }
  d.update(kw)
  return d


def _sell_decision(**kw):
  d = {
    "action": "SELL",
    "signal_id": "s-sell",
    "entry": 1.10000,
    "sl": 1.10100,
    "tp": 1.09800,
    "rr": 2.0,
    "max_hold_bars": 10,
  }
  d.update(kw)
  return d


def test_spread_price_prefers_bar_points():
  assert _spread_price(19, 1.0) == 19 * 1e-5
  assert _spread_price(0, 1.9) == 1.9 * 1e-4
  assert _spread_price(0, 0) == 10 * 1e-5


def test_buy_fills_at_ask_not_bid():
  book = ReplayPaperBook()
  book.queue_decision(_buy_decision())
  fills = book.on_bar(
    open_=1.10000, high=1.10000, low=1.10000, close=1.10000,
    bar_time="t0", spread_points=20,
  )
  assert len(fills) == 1
  assert fills[0]["price"] == 1.10020
  assert book.sl == 1.09920  # rebased from Ask, risk 10 pips
  assert book.entry == 1.10020


def test_sell_fills_at_bid():
  book = ReplayPaperBook()
  book.queue_decision(_sell_decision())
  fills = book.on_bar(
    open_=1.10000, high=1.10000, low=1.10000, close=1.10000,
    bar_time="t0", spread_points=20,
  )
  assert fills[0]["price"] == 1.10000
  assert book.sl == 1.10100


def test_sell_sl_hits_on_entry_bar_ask():
  """Same-bar wick: Bid high misses SL, Ask high hits — must close on fill bar."""
  book = ReplayPaperBook()
  book.queue_decision(_sell_decision())
  fills = book.on_bar(
    open_=1.10000, high=1.10090, low=1.09980, close=1.10040,
    bar_time="t0", spread_points=20,
  )
  reasons = [f.get("reason") for f in fills]
  assert "sl" in reasons
  sl_fill = next(f for f in fills if f.get("reason") == "sl")
  assert sl_fill["r"] == -1.0


def test_sell_sl_hits_on_ask_not_bid_high():
  book = ReplayPaperBook()
  book.queue_decision(_sell_decision())
  book.on_bar(
    open_=1.10000, high=1.10000, low=1.10000, close=1.10000,
    bar_time="t0", spread_points=20,
  )
  # Bid high 1.10090 would miss SL 1.10100; Ask high 1.10110 hits.
  fills = book.on_bar(
    open_=1.10050, high=1.10090, low=1.10040, close=1.10080,
    bar_time="t1", spread_points=20,
  )
  assert fills and fills[0]["reason"] == "sl"
  assert fills[0]["r"] == -1.0


def test_buy_sl_r_is_minus_one_after_ask_fill():
  book = ReplayPaperBook()
  book.queue_decision(_buy_decision())
  book.on_bar(
    open_=1.10000, high=1.10010, low=1.09990, close=1.10000,
    bar_time="t0", spread_points=20,
  )
  fills = book.on_bar(
    open_=1.09950, high=1.09980, low=1.09900, close=1.09920,
    bar_time="t1", spread_points=20,
  )
  assert fills and fills[0]["reason"] == "sl"
  assert fills[0]["r"] == -1.0


def test_max_hold_zero_does_not_close_next_bar():
  """Full-TP genomes send max_hold=0 meaning unlimited, not 'close on bar 2'."""
  book = ReplayPaperBook()
  book.queue_decision(_buy_decision(max_hold_bars=0, sl=1.09000, tp=1.20000, rr=10.0))
  book.on_bar(
    open_=1.10000, high=1.10010, low=1.09990, close=1.10000,
    bar_time="t0", spread_points=20,
  )
  assert book.open
  fills = book.on_bar(
    open_=1.10000, high=1.10020, low=1.09980, close=1.10010,
    bar_time="t1", spread_points=20,
  )
  assert fills == []
  assert book.open
