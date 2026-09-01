"""Execution cost model — Bid/Ask like live OrderSend (5-digit FX).

OHLC from MT5/CopyRates is Bid. Live fills BUY at Ask and SELL at Bid.
Lab / Compare / gridsearch use the same geometry: Ask = Bid + spread.
``slippage_pips`` is extra adverse on market fills (quoted live has none).
"""
from __future__ import annotations

PIP = 0.0001
POINT = 0.00001  # 5-digit: 1 pip = 10 points


def round_trip_cost_pips(spread_pips: float, slippage_pips: float) -> float:
  return spread_pips + 2.0 * slippage_pips


def spread_price(spread_pips: float) -> float:
  """One spread in price units (5-digit FX)."""
  return max(0.0, float(spread_pips)) * PIP


def spread_from_quote(spread_pips: float = 0.0, spread_points: float = 0.0) -> float:
  """Bid→Ask in price. Prefer bar ``spread_points`` (live/replay), else model pips."""
  try:
    pts = float(spread_points or 0.0)
  except (TypeError, ValueError):
    pts = 0.0
  if pts > 0:
    return pts * POINT
  return spread_price(spread_pips)


def carry_spread_points(points: float, last: float) -> tuple[float, float]:
  """Reuse last non-zero bar spread (EA HistSpreadPrice — skip weekend 0)."""
  try:
    pts = float(points or 0.0)
  except (TypeError, ValueError):
    pts = 0.0
  if pts > 0:
    return pts, pts
  last = float(last or 0.0)
  if last > 0:
    return last, last
  return 0.0, last


def atr_stop_distance(
  atr: float,
  atr_mult: float,
  spread_pips: float = 0.0,
  spread_points: float = 0.0,
) -> float:
  """Stop distance that still leaves ATR room after the broker hits the opposite quote.

  Live SELL SL fills on Ask, BUY SL on Bid. OHLC is Bid. Adding one spread to the
  ATR stop keeps the intended ATR adverse room instead of dying inside the spread.
  Prefer per-bar ``spread_points`` when known.
  """
  return float(atr_mult) * float(atr) + spread_from_quote(spread_pips, spread_points)


def stop_and_target_distances(
  atr: float,
  atr_mult: float,
  rr: float,
  spread_pips: float = 0.0,
  spread_points: float = 0.0,
  *,
  tp_ignores_spread_buffer: bool = False,
) -> tuple[float, float]:
  """Live SL = ATR×mult + 1 spread; TP defaults to SL×RR.

  When ``tp_ignores_spread_buffer``, TP uses ATR×mult×RR only. The spread
  buffer stays on SL (Ask/Bid) so live does not die inside the quote, but is
  not multiplied into the target — that double tax is what crushed WR after
  Bid/Ask fills.
  """
  spr = spread_from_quote(spread_pips, spread_points)
  atr_sl = float(atr_mult) * float(atr)
  sl_d = atr_sl + spr
  tp_d = atr_sl * float(rr) if tp_ignores_spread_buffer else sl_d * float(rr)
  return sl_d, tp_d


def cost_r_from_pips(cost_pips: float, risk_price: float) -> float:
  if risk_price <= 0:
    return 0.0
  return (cost_pips * PIP) / risk_price


def adjust_entry_price(
  raw_open: float,
  direction: int,
  spread_pips: float,
  slippage_pips: float,
  spread_points: float = 0.0,
) -> float:
  """BUY at Ask = Bid open + spread; SELL at Bid open. Slippage extra adverse."""
  spr = spread_from_quote(spread_pips, spread_points)
  slip = max(0.0, float(slippage_pips)) * PIP
  raw = float(raw_open)
  if int(direction) == 1:
    return raw + spr + slip
  return raw - slip


def adjust_exit_price(
  raw_price: float,
  direction: int,
  spread_pips: float,
  slippage_pips: float,
  spread_points: float = 0.0,
) -> float:
  """Market/timeout close: BUY at Bid, SELL at Ask. Do not use on SL/TP hits."""
  spr = spread_from_quote(spread_pips, spread_points)
  slip = max(0.0, float(slippage_pips)) * PIP
  raw = float(raw_price)
  if int(direction) == 1:
    return raw - slip
  return raw + spr + slip


def apply_cost_to_r(pnl_r: float, risk_price: float, spread_pips: float, slippage_pips: float) -> float:
  cost_r = cost_r_from_pips(round_trip_cost_pips(spread_pips, slippage_pips), risk_price)
  return pnl_r - cost_r
