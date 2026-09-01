"""HistoryFeed last_bar drives Live D/W/M during Replay."""
from __future__ import annotations

import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
if str(LIVE) not in sys.path:
  sys.path.insert(0, str(LIVE))

from replay_control import parse_feed_bar_time  # noqa: E402


def test_parse_feed_bar_time_dotted_mt5():
  dt = parse_feed_bar_time("2026.08.14 07:45")
  assert dt is not None
  assert dt.year == 2026
  assert dt.month == 8
  assert dt.day == 14
  assert dt.hour == 7
  assert dt.minute == 45


def test_parse_feed_bar_time_iso():
  dt = parse_feed_bar_time("2026-08-14 07:45")
  assert dt is not None
  assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2026, 8, 14, 7, 45)


def test_parse_feed_bar_time_rejects_short():
  assert parse_feed_bar_time("") is None
  assert parse_feed_bar_time("2026.08") is None
