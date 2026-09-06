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


def effective_rr(
  entry: float,
  sl: float,
  tp: float,
  *,
  fallback: float = 2.0,
) -> float:
  """RR from planned SL/TP. Prefer this over genome rr so TP-clip survives rebase."""
  risk = abs(float(entry) - float(sl))
  if risk <= 0:
    return float(fallback) if fallback > 0 else 2.0
  return abs(float(tp) - float(entry)) / risk


def rebase_fill_levels(
  *,
  direction: int,
  fill_entry: float,
  planned_entry: float,
  planned_sl: float,
  planned_tp: float,
  rr: float | None = None,
) -> tuple[float, float, float]:
  """Rebase SL/TP onto the Bid/Ask fill. RR always from planned geometry (clip-safe).

  Live EA / HistoryFeed / Compare / miner must share this: genome ``rr_ratio``
  is not used when SL and TP are present — otherwise ``tp_ignores_spread_buffer``
  is undone (TP becomes SL×genome-RR).
  """
  direction = int(direction)
  fill = float(fill_entry)
  planned = float(planned_entry or 0.0)
  p_sl = float(planned_sl or 0.0)
  p_tp = float(planned_tp or 0.0)
  planned_risk = abs(planned - p_sl) if planned > 0 and p_sl > 0 else 0.0
  geom = effective_rr(planned, p_sl, p_tp, fallback=0.0) if planned > 0 and p_sl > 0 and p_tp > 0 else 0.0
  use_rr = geom if geom > 0 else (float(rr) if rr is not None and float(rr) > 0 else 2.0)
  if planned_risk > 0:
    if direction == 1:
      sl, tp = fill - planned_risk, fill + planned_risk * use_rr
    else:
      sl, tp = fill + planned_risk, fill - planned_risk * use_rr
    return sl, tp, planned_risk
  if planned > 0:
    delta = fill - planned
    return p_sl + delta, p_tp + delta, abs(fill - (p_sl + delta))
  return p_sl, p_tp, abs(fill - p_sl)


def confirm_fill_price(direction: int, ref_price: float, sl_d: float, confirm_r: float) -> float:
  """Pending-stop fill: BUY stop above Ask ref, SELL stop below Bid ref."""
  return float(ref_price) + int(direction) * float(sl_d) * float(confirm_r)


def confirm_bar_result(
  *,
  direction: int,
  ref_price: float,
  sl_d: float,
  confirm_r: float,
  cancel_r: float,
  bid_high: float,
  bid_low: float,
  spread_px: float = 0.0,
) -> str:
  """One completed M15 bar vs pending stop. ``cancel`` | ``fill`` | ``wait``.

  Same-bar confirm+cancel → ``cancel`` (path unknown), matching ``_confirm_stop_fill``.
  BUY manages on Bid; SELL on Ask = Bid + spread.
  """
  if sl_d <= 0 or confirm_r <= 0:
    return "wait"
  direction = int(direction)
  fill_px = confirm_fill_price(direction, ref_price, sl_d, confirm_r)
  cancel_px = float(ref_price) - direction * float(sl_d) * float(cancel_r)
  bid_h, bid_l = float(bid_high), float(bid_low)
  spr = max(0.0, float(spread_px))
  if direction > 0:
    if bid_l <= cancel_px:
      return "cancel"
    if bid_h >= fill_px:
      return "fill"
    return "wait"
  ask_h, ask_l = bid_h + spr, bid_l + spr
  if ask_h >= cancel_px:
    return "cancel"
  if ask_l <= fill_px:
    return "fill"
  return "wait"
