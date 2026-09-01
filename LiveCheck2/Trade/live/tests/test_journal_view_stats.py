"""Session stats must follow broker profit / missed SL, not reconnect ghosts."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

LIVE = Path(__file__).resolve().parents[1]
if str(LIVE) not in sys.path:
  sys.path.insert(0, str(LIVE))

from journal_view import (  # noqa: E402
  _summarize_group,
  _trade_r,
  _trade_result,
  wl_text,
)


def _closed(**kw):
  row = {"status": "CLOSED", "direction": "SELL"}
  row.update(kw)
  return row


def test_profit_overrides_fake_win_r():
  t = _closed(
    entry_px=1.35644,
    exit_px=1.35614,
    sl=1.35687,
    sl_initial=1.35687,
    lots=0.22,
    r=0.698,
    result="WIN",
    profit=-9.84,
    reason="sl",
  )
  assert _trade_result(t) == "LOSS"
  assert _trade_r(t) is not None and _trade_r(t) < 0


def test_desync_without_mt5_profit_is_not_invented_loss():
  t = _closed(
    entry_px=1.3554,
    exit_px=1.3554,
    sl=1.35578,
    sl_initial=1.35578,
    lots=0.26,
    r=0.0,
    result="BE",
    profit=None,
    reason="ea_reconnect_reconcile",
    interventions=["journal_desync", "ea_reconnect_reconcile"],
  )
  assert _trade_result(t) == "BE"
  assert abs(_trade_r(t) or 0) < 1e-9


def test_mt5_profit_on_desync_is_loss():
  t = _closed(
    entry_px=1.3554,
    exit_px=1.35578,
    sl=1.35578,
    sl_initial=1.35578,
    lots=0.26,
    r=0.0,
    result="BE",
    profit=-9.88,
    reason="sl",
    interventions=["mt5_deal"],
  )
  assert _trade_result(t) == "LOSS"
  assert _trade_r(t) is not None and _trade_r(t) < 0


def test_sl_profit_repairs_too_small_stored_r():
  t = _closed(
    entry_px=1.35555,
    exit_px=1.35578,
    sl=1.35596,
    sl_initial=1.35596,
    lots=0.24,
    r=-0.561,
    result="LOSS",
    profit=-9.88,
    reason="sl",
  )
  assert _trade_result(t) == "LOSS"
  assert _trade_r(t) is not None and _trade_r(t) < -0.9


def test_true_be_stays_be():
  t = _closed(
    entry_px=1.35,
    exit_px=1.35,
    sl=1.3504,
    sl_initial=1.3504,
    lots=0.2,
    r=0.0,
    result="BE",
    profit=0.0,
    reason="manual_close",
  )
  assert _trade_result(t) == "BE"
  assert abs(_trade_r(t) or 0) < 1e-9


def test_today_seven_losses_when_mt5_profit_present():
  trades = [
    _closed(
      entry_px=1.3554, exit_px=1.35578, sl=1.35578, sl_initial=1.35578, lots=0.26,
      r=-1.0, result="LOSS", profit=-9.88, reason="sl",
    ),
    _closed(
      entry_px=1.35539, exit_px=1.35578, sl=1.35577, sl_initial=1.35577, lots=0.26,
      r=-1.026, result="LOSS", profit=-9.88, reason="sl",
    ),
    _closed(
      entry_px=1.35573, exit_px=1.35614, sl=1.35614, sl_initial=1.35614, lots=0.24,
      r=-1.0, result="LOSS", profit=-9.84, reason="sl",
    ),
    _closed(
      entry_px=1.35558, exit_px=1.35598, sl=1.35598, sl_initial=1.35598, lots=0.24,
      r=-1.0, result="LOSS", profit=-9.60, reason="sl",
    ),
    _closed(
      entry_px=1.35555, exit_px=1.35596, sl=1.35596, sl_initial=1.35596, lots=0.24,
      r=-1.0, result="LOSS", profit=-9.84, reason="sl",
    ),
    _closed(
      entry_px=1.35644, exit_px=1.35687, sl=1.35687, sl_initial=1.35687, lots=0.22,
      r=-1.0, result="LOSS", profit=-9.46, reason="sl",
    ),
    _closed(
      entry_px=1.35586, exit_px=1.35638, sl=1.35638, sl_initial=1.35638, lots=0.18,
      r=-1.0, result="LOSS", profit=-9.36, reason="sl",
    ),
  ]
  s = _summarize_group(trades)
  assert s["n_closed"] == 7
  assert s["wins"] == 0
  assert s["losses"] == 7
  assert s["be"] == 0
  assert s["win_rate_pct"] == 0.0
  assert s["total_r"] < 0
  assert wl_text(s["wins"], s["losses"], s["be"]) == "0/7"


def test_historyfeed_paper_profit_is_r_not_money():
  """Replay WriteFillJsonEx stores R-multiple in profit; must not divide by lot*contract."""
  t = _closed(
    direction="BUY",
    entry_px=1.15966,
    exit_px=1.15914,
    sl=1.15914,
    sl_initial=1.15914,
    lots=0.13,
    r=-1.0,
    result="LOSS",
    profit=-1.0,
    reason="sl",
  )
  assert _trade_r(t) == pytest.approx(-1.0)
  s = _summarize_group([
    t,
    _closed(
      direction="BUY",
      entry_px=1.16,
      exit_px=1.1632,
      sl=1.1592,
      sl_initial=1.1592,
      lots=0.13,
      r=4.0,
      result="WIN",
      profit=4.0,
      reason="tp",
    ),
  ])
  assert s["total_r"] == pytest.approx(3.0)
  assert s["wins"] == 1
  assert s["losses"] == 1


def test_period_bounds_follow_replay_cursor():
  from datetime import datetime

  from journal_view import period_bounds

  now = datetime(2026, 8, 14, 7, 45)
  start, end = period_bounds("today", now=now)
  assert start.date().isoformat() == "2026-08-14"
  assert end is not None and end.date().isoformat() == "2026-08-15"
  w0, w1 = period_bounds("week", now=now)
  assert w0.date().isoformat() == "2026-08-10"
  assert w1 is not None and w1.date().isoformat() == "2026-08-17"
  m0, m1 = period_bounds("month", now=now)
  assert m0.date().isoformat() == "2026-08-01"
  assert m1 is not None and m1.date().isoformat() == "2026-09-01"


def test_filter_trades_today_uses_now_not_wall_clock():
  from datetime import datetime

  from journal_view import filter_trades_by_period

  trades = [
    _closed(exit_time="2026.08.14 08:00", result="WIN", r=1.0, profit=10),
    _closed(exit_time="2026.08.30 08:00", result="WIN", r=1.0, profit=10),
  ]
  asof = datetime(2026, 8, 14, 12, 0)
  day = filter_trades_by_period(trades, "today", now=asof)
  assert len(day) == 1
  assert str(day[0]["exit_time"]).startswith("2026.08.14")
