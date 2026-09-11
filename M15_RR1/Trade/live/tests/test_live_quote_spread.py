"""Live quote / spread formatting from EA connection + bar."""
from __future__ import annotations

import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
if str(LIVE) not in sys.path:
  sys.path.insert(0, str(LIVE))

from live_health import live_quote  # noqa: E402


def test_spread_pips_from_5_digit_points():
  q = live_quote(
    {"bid": 1.15818, "ask": 1.15837, "spread_points": 19},
    {"digits": 5, "point": 0.00001},
  )
  assert q["spread_points"] == 19
  assert q["spread_pips"] == 1.9
  assert q["spread_text"] == "1.9p"


def test_spread_from_bid_ask_when_points_missing():
  q = live_quote(
    {"bid": 1.35498, "ask": 1.35526},
    {"digits": 5, "point": 0.00001},
  )
  assert q["spread_points"] == 28
  assert q["spread_text"] == "2.8p"


def test_spread_from_ea_connection_payload_without_bar():
  q = live_quote(
    {
      "symbol": "EURUSD",
      "bid": 1.15782,
      "ask": 1.15801,
      "spread_points": 19,
      "bar": {"close": 1.15782, "tick_volume": 568},
    },
    {},
  )
  assert q["spread_points"] == 19
  assert q["spread_text"] == "1.9p"
  assert q["bid"] == 1.15782
