"""Paper fills for Linux replay feeder (EA-side, no journal write).

Mirrors desk ``mt5_bridge.paper_fill.PaperBook`` entry/exit rules, but only
emits fill dicts. The Live decision worker ingests them via fill.json /
ea_fills.jsonl — same as ForgeBridgeLiveSim HistoryFeed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_POINT = 1e-5
_PIP = 1e-4


def _spread_price(spread_points: Any = 0, spread_pips: Any = 0) -> float:
  """Price units for Bid→Ask. Prefer bar points (like live tick), else model pips."""
  try:
    pts = int(spread_points or 0)
  except (TypeError, ValueError):
    pts = 0
  if pts > 0:
    return pts * _POINT
  try:
    pips = float(spread_pips or 0.0)
  except (TypeError, ValueError):
    pips = 0.0
  if pips > 0:
    return pips * _PIP
  return 10 * _POINT  # 1.0 pip on 5-digit


def _exit_mode_code(raw: Any) -> int:
  s = str(raw or "").strip().lower()
  if s in ("full", "0"):
    return 0
  if s in ("hybrid", "1"):
    return 1
  if s in ("trail", "2"):
    return 2
  if s in ("partial", "3"):
    return 3
  return 0


@dataclass
class ReplayPaperBook:
  """One virtual position book (one Trade Model)."""

  model_id: str | None = None
  magic: int | None = None
  symbol: str = "EURUSD"
  period: str = "M15"
  pending: dict | None = None
  open: bool = False
  held: int = 0
  ticket: int = 0
  signal_id: str = ""
  action: str = ""
  entry: float = 0.0
  sl: float = 0.0
  sl_initial: float = 0.0
  tp: float = 0.0
  lots: float = 0.01
  risk: float = 0.0
  exit_mode: int = 0
  trail_act: float = 1.0
  trail_dist: float = 0.5
  max_hold: int = 96
  last_signal_id: str = ""
  n_fills: int = 0
  spread_pips: float = 1.0
  slippage_pips: float = 0.3
  _spread_px: float = 0.0001
  _fills: list[dict] = field(default_factory=list, repr=False)

  def queue_decision(self, decision: dict | None) -> None:
    if not isinstance(decision, dict):
      return
    action = str(decision.get("action") or "").upper()
    if action not in ("BUY", "SELL"):
      return
    sid = str(decision.get("signal_id") or "")
    if sid and sid == self.last_signal_id:
      return
    self.pending = dict(decision)

  def on_bar(
    self,
    *,
    open_: float,
    high: float,
    low: float,
    close: float,
    bar_time: str,
    spread_points: int | float = 0,
  ) -> list[dict]:
    emitted: list[dict] = []
    if self.pending and not self.open:
      fill = self._open_from_decision(
        self.pending, float(open_), bar_time, spread_points=spread_points,
      )
      self.pending = None
      if fill:
        emitted.append(fill)
    if self.open:
      close_fill = self._manage(
        high=float(high),
        low=float(low),
        close=float(close),
        bar_time=bar_time,
        spread_points=spread_points,
      )
      if close_fill:
        emitted.append(close_fill)
    return emitted

  def _base_fill(self, decision: dict | None = None) -> dict:
    return {
      "ok": True,
      "manual": False,
      "source": "strategy",
      "symbol": self.symbol,
      "period": self.period,
      "instance_id": "LIVE_SIM",
      "magic": self.magic if self.magic is not None else (decision or {}).get("magic"),
      "model_id": self.model_id or (decision or {}).get("model_id"),
      "lots": self.lots,
    }

  def _open_from_decision(
    self,
    decision: dict,
    entry_price: float,
    bar_time: str,
    *,
    spread_points: int | float = 0,
  ) -> dict | None:
    action = str(decision.get("action") or "").upper()
    if action not in ("BUY", "SELL"):
      return None
    sid = str(decision.get("signal_id") or "")
    if sid and sid == self.last_signal_id:
      return None

    spread = float(decision.get("spread_pips") or 1.0)
    slip = float(decision.get("slippage_pips") or 0.3)
    spr = _spread_price(spread_points, spread)
    # Same as live OrderSend / HistoryFeed EA: BUY at Ask, SELL at Bid.
    fill_entry = float(entry_price) + spr if action == "BUY" else float(entry_price)
    planned = float(decision.get("entry") or 0.0)

    sl = float(decision.get("sl") or 0.0)
    tp = float(decision.get("tp") or 0.0)
    if sl <= 0 or tp <= 0 or fill_entry <= 0:
      return None

    self.exit_mode = _exit_mode_code(decision.get("exit_mode"))
    self.trail_act = float(decision.get("trail_activate_r") or 1.0)
    self.trail_dist = float(decision.get("trail_distance_r") or 0.5)
    self.max_hold = int(decision.get("max_hold_bars") or 96)
    self.spread_pips = spread
    self.slippage_pips = slip
    self._spread_px = spr

    planned_risk = abs(planned - sl) if planned > 0 else abs(fill_entry - sl)
    rr = float(decision.get("rr") or 0.0)
    if rr <= 0.0 and planned_risk > 0.0 and planned > 0.0:
      rr = abs(tp - planned) / planned_risk
    if rr <= 0.0:
      rr = 2.0

    if planned_risk > 0.0:
      if action == "BUY":
        sl = fill_entry - planned_risk
        tp = fill_entry + planned_risk * rr
      else:
        sl = fill_entry + planned_risk
        tp = fill_entry - planned_risk * rr

    sl_dist = abs(fill_entry - sl)
    if sl_dist <= 0.0 or sl_dist < 0.5 * _PIP:
      return None

    self.ticket += 1
    self.signal_id = sid
    self.action = action
    self.entry = fill_entry
    self.sl = sl
    self.sl_initial = sl
    self.tp = tp
    self.risk = sl_dist
    self.lots = 0.01
    self.open = True
    self.held = 0
    self.last_signal_id = sid
    if decision.get("magic") is not None:
      try:
        self.magic = int(decision["magic"])
      except (TypeError, ValueError):
        pass

    fill = {
      **self._base_fill(decision),
      "event": "open",
      "detail": "opened",
      "reason": "opened",
      "action": action,
      "signal_id": sid,
      "ticket": self.ticket,
      "price": fill_entry,
      "entry": fill_entry,
      "sl": sl,
      "tp": tp,
      "profit": 0.0,
      "bar_time": bar_time,
      "time": bar_time,
    }
    self.n_fills += 1
    self._fills.append(fill)
    return fill

  def _manage(
    self,
    *,
    high: float,
    low: float,
    close: float,
    bar_time: str,
    spread_points: int | float = 0,
  ) -> dict | None:
    if not self.open:
      return None
    self.held += 1
    if self.held <= 1:
      return None

    spr = _spread_price(spread_points, self.spread_pips)
    self._spread_px = spr
    bid_h, bid_l, bid_c = float(high), float(low), float(close)
    ask_h, ask_l, ask_c = bid_h + spr, bid_l + spr, bid_c + spr

    if self.exit_mode in (1, 2):
      if self.action == "BUY":
        if bid_h >= self.entry + self.risk * self.trail_act:
          nsl = bid_h - self.risk * self.trail_dist
          if nsl > self.sl:
            self.sl = nsl
      else:
        if ask_l <= self.entry - self.risk * self.trail_act:
          nsl = ask_l + self.risk * self.trail_dist
          if self.sl == 0 or nsl < self.sl:
            self.sl = nsl

    trail_moved = (
      self.sl_initial > 0.0
      and abs(self.sl - self.sl_initial) > (_POINT * 0.5)
    )

    if self.action == "BUY":
      if self.sl > 0 and bid_l <= self.sl:
        return self._close("trail" if trail_moved else "sl", self.sl, bar_time)
      if self.tp > 0 and bid_h >= self.tp:
        return self._close("tp", self.tp, bar_time)
    else:
      if self.sl > 0 and ask_h >= self.sl:
        return self._close("trail" if trail_moved else "sl", self.sl, bar_time)
      if self.tp > 0 and ask_l <= self.tp:
        return self._close("tp", self.tp, bar_time)

    if self.held - 1 >= self.max_hold and self.max_hold > 0:
      return self._close("max_hold", bid_c if self.action == "BUY" else ask_c, bar_time)
    return None

  def _close(self, reason: str, exit_px: float, bar_time: str) -> dict:
    profit = 0.0
    if self.risk > 0:
      if self.action == "BUY":
        profit = (exit_px - self.entry) / self.risk
      else:
        profit = (self.entry - exit_px) / self.risk
    fill = {
      **self._base_fill(),
      "event": "close",
      "detail": reason,
      "reason": reason,
      "action": self.action,
      "signal_id": self.signal_id,
      "ticket": self.ticket,
      "price": exit_px,
      "entry": self.entry,
      "sl": self.sl,
      "tp": self.tp,
      "profit": round(profit, 4),
      "r": round(profit, 4),
      "bar_time": bar_time,
      "time": bar_time,
    }
    self.open = False
    self.held = 0
    self.n_fills += 1
    self._fills.append(fill)
    return fill
