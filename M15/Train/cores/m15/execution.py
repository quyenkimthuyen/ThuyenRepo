"""Execution cost model — spread & slippage (EUR/USD)."""
from __future__ import annotations

PIP = 0.0001


def round_trip_cost_pips(spread_pips: float, slippage_pips: float) -> float:
  return spread_pips + 2.0 * slippage_pips


def spread_price(spread_pips: float) -> float:
  """One spread in price units (5-digit FX)."""
  return max(0.0, float(spread_pips)) * PIP


def atr_stop_distance(atr: float, atr_mult: float, spread_pips: float = 0.0) -> float:
  """Stop distance that still leaves ATR room after the broker hits the opposite quote.

  Live SELL SL fills on Ask, BUY SL on Bid. OHLC is Bid. Adding one spread to the
  ATR stop keeps the intended ATR adverse room instead of dying inside the spread.
  """
  return float(atr_mult) * float(atr) + spread_price(spread_pips)


def cost_r_from_pips(cost_pips: float, risk_price: float) -> float:
  if risk_price <= 0:
    return 0.0
  return (cost_pips * PIP) / risk_price


def adjust_entry_price(raw_open: float, direction: int, spread_pips: float, slippage_pips: float) -> float:
  half = (spread_pips / 2.0 + slippage_pips) * PIP
  return raw_open + half if direction == 1 else raw_open - half


def adjust_exit_price(raw_price: float, direction: int, spread_pips: float, slippage_pips: float) -> float:
  half = (spread_pips / 2.0 + slippage_pips) * PIP
  # Long exit (sell): worse = lower; Short exit (buy): worse = higher
  return raw_price - half if direction == 1 else raw_price + half


def apply_cost_to_r(pnl_r: float, risk_price: float, spread_pips: float, slippage_pips: float) -> float:
  cost_r = cost_r_from_pips(round_trip_cost_pips(spread_pips, slippage_pips), risk_price)
  return pnl_r - cost_r
