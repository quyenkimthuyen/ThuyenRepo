"""Python OHLC *sim fills* for Compare Trade / HistoryFeed.

Legacy name ``paper_fill`` / ``PaperBook`` matches EA ``ManagePaperHistory`` /
``InpHistoryPaperFills`` — **not** the retired Paper Monitor GUI desk.

Entry at next bar open after BUY/SELL decision; SL/TP/trail/max_hold start on the
bar after entry (held <= 1 skipped).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mt5_bridge.trade_journal import process_fill

# FX majors 5-digit: Point≈0.00001, pip=0.0001
_POINT = 1e-5
_PIP = 1e-4


def _desk_symbol() -> str:
  """Fallback chart/journal symbol (EUR vs GBP desks). Keep parity with GUI helper."""
  try:
    from config import DEFAULT_PAIR
    pair = str(DEFAULT_PAIR or "").upper().replace("/", "")
    if pair:
      return pair
  except Exception:
    pass
  try:
    from mt5_bridge.protocol import INSTANCE_ID, ROOT
    name = ROOT.name.upper()
    if "GBP" in name or str(INSTANCE_ID).upper().startswith(("M15G", "M5G", "G")):
      return "GBPUSD"
  except Exception:
    pass
  return "EURUSD"


def journal_symbol(*sources: dict | None) -> str:
  """Prefer explicit symbol on fill/decision/bar; else desk default."""
  for src in sources:
    if not isinstance(src, dict):
      continue
    sym = str(src.get("symbol") or "").strip()
    if sym:
      return sym
  return _desk_symbol()

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
class PaperBook:
  """One virtual position book (typically one Trade Model)."""

  bridge_dir: Path
  model_id: str | None = None
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
  _fills: list[dict] = field(default_factory=list, repr=False)

  def queue_decision(self, decision: dict | None) -> None:
    """Queue BUY/SELL for open at the *next* bar's open."""
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
  ) -> list[dict]:
    """Apply pending open then manage SL/TP/trail on this bar. Returns fills."""
    emitted: list[dict] = []
    if self.pending and not self.open:
      fill = self._open_from_decision(self.pending, float(open_), bar_time)
      self.pending = None
      if fill:
        emitted.append(fill)

    if self.open:
      close_fill = self._manage(high=float(high), low=float(low), close=float(close), bar_time=bar_time)
      if close_fill:
        emitted.append(close_fill)
    return emitted

  def _open_from_decision(self, decision: dict, entry_price: float, bar_time: str) -> dict | None:
    action = str(decision.get("action") or "").upper()
    if action not in ("BUY", "SELL"):
      return None
    sid = str(decision.get("signal_id") or "")
    if sid and sid == self.last_signal_id:
      return None

    planned = float(decision.get("entry") or 0.0)
    sl = float(decision.get("sl") or 0.0)
    tp = float(decision.get("tp") or 0.0)
    if sl <= 0 or tp <= 0 or entry_price <= 0:
      return None

    self.exit_mode = _exit_mode_code(decision.get("exit_mode"))
    self.trail_act = float(decision.get("trail_activate_r") or 1.0)
    self.trail_dist = float(decision.get("trail_distance_r") or 0.5)
    self.max_hold = int(decision.get("max_hold_bars") or 96)

    planned_risk = abs(planned - sl) if planned > 0 else 0.0
    rr = float(decision.get("rr") or 0.0)
    if rr <= 0.0 and planned_risk > 0.0 and planned > 0.0:
      rr = abs(tp - planned) / planned_risk
    if rr <= 0.0:
      rr = 2.0

    if planned_risk > 0.0:
      if action == "BUY":
        sl = entry_price - planned_risk
        tp = entry_price + planned_risk * rr
      else:
        sl = entry_price + planned_risk
        tp = entry_price - planned_risk * rr
    elif planned > 0.0:
      delta = entry_price - planned
      sl += delta
      tp += delta

    sl_dist = abs(entry_price - sl)
    if sl_dist <= 0.0 or sl_dist < 0.5 * _PIP:
      return None

    self.ticket += 1
    self.signal_id = sid
    self.action = action
    self.entry = entry_price
    self.sl = sl
    self.sl_initial = sl
    self.tp = tp
    self.risk = sl_dist
    self.lots = 0.01
    self.open = True
    self.held = 0
    self.last_signal_id = sid

    fill = {
      "ok": True,
      "event": "open",
      "detail": "opened",
      "reason": "opened",
      "action": action,
      "signal_id": sid,
      "ticket": self.ticket,
      "price": entry_price,
      "sl": sl,
      "tp": tp,
      "lots": self.lots,
      "profit": 0.0,
      "manual": False,
      "source": "strategy",
      "bar_time": bar_time,
      "symbol": _desk_symbol(),
      "model_id": self.model_id or decision.get("model_id"),
    }
    process_fill(
      fill,
      bridge_dir=self.bridge_dir,
      decision=decision,
      model_id=self.model_id or decision.get("model_id"),
    )
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
  ) -> dict | None:
    if not self.open:
      return None
    self.held += 1
    if self.held <= 1:
      return None

    if self.exit_mode in (1, 2):
      if self.action == "BUY":
        if high >= self.entry + self.risk * self.trail_act:
          nsl = high - self.risk * self.trail_dist
          if nsl > self.sl:
            self.sl = nsl
      else:
        if low <= self.entry - self.risk * self.trail_act:
          nsl = low + self.risk * self.trail_dist
          if self.sl == 0 or nsl < self.sl:
            self.sl = nsl

    trail_moved = (
      self.sl_initial > 0.0
      and abs(self.sl - self.sl_initial) > (_POINT * 0.5)
    )

    if self.action == "BUY":
      if self.sl > 0 and low <= self.sl:
        return self._close("trail" if trail_moved else "sl", self.sl, bar_time)
      if self.tp > 0 and high >= self.tp:
        return self._close("tp", self.tp, bar_time)
    else:
      if self.sl > 0 and high >= self.sl:
        return self._close("trail" if trail_moved else "sl", self.sl, bar_time)
      if self.tp > 0 and low <= self.tp:
        return self._close("tp", self.tp, bar_time)

    if self.held - 1 >= self.max_hold:
      return self._close("max_hold", close, bar_time)
    return None

  def _close(self, reason: str, exit_px: float, bar_time: str) -> dict:
    profit = 0.0
    if self.risk > 0:
      if self.action == "BUY":
        profit = (exit_px - self.entry) / self.risk
      else:
        profit = (self.entry - exit_px) / self.risk

    fill = {
      "ok": True,
      "event": "close",
      "detail": reason,
      "reason": reason,
      "action": self.action,
      "signal_id": self.signal_id,
      "ticket": self.ticket,
      "price": exit_px,
      "exit_px": exit_px,
      "sl": self.sl,
      "tp": self.tp,
      "lots": self.lots,
      "profit": round(profit, 4),
      "manual": False,
      "source": "strategy",
      "bar_time": bar_time,
      "symbol": _desk_symbol(),
      "model_id": self.model_id,
    }
    process_fill(fill, bridge_dir=self.bridge_dir, model_id=self.model_id)
    self.open = False
    self.held = 0
    self.signal_id = ""
    self.sl_initial = 0.0
    self.n_fills += 1
    self._fills.append(fill)
    return fill
