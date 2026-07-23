"""Journal + stats for MT5 Bridge live trades (win/loss detail)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mt5_bridge.comm_log import append_event
from mt5_bridge.protocol import BRIDGE_DIR, ensure_bridge_dir, atomic_write_json, read_json

TRADES_NAME = "trades.json"
FILLS_LOG_NAME = "fills.jsonl"


def trades_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / TRADES_NAME


def fills_log_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / FILLS_LOG_NAME


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_trades(bridge_dir: Path | None = None) -> list[dict]:
  data = read_json(trades_path(bridge_dir))
  if isinstance(data, dict):
    return list(data.get("trades") or [])
  if isinstance(data, list):
    return data
  return []


def save_trades(trades: list[dict], bridge_dir: Path | None = None) -> None:
  atomic_write_json(trades_path(bridge_dir), {
    "updated_at": _now(),
    "trades": trades,
  })


def _append_fill_log(fill: dict, bridge_dir: Path | None = None) -> None:
  path = fills_log_path(bridge_dir)
  with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps({"ts": _now(), **fill}, ensure_ascii=False, default=str) + "\n")


def _risk_dist(entry: float | None, sl: float | None) -> float | None:
  if entry is None or sl is None:
    return None
  d = abs(float(entry) - float(sl))
  return d if d > 0 else None


def _compute_r(direction: str, entry: float, exit_px: float, sl: float) -> float | None:
  risk = _risk_dist(entry, sl)
  if not risk:
    return None
  d = (direction or "").upper()
  if d in ("BUY", "LONG"):
    return round((float(exit_px) - float(entry)) / risk, 3)
  if d in ("SELL", "SHORT"):
    return round((float(entry) - float(exit_px)) / risk, 3)
  return None


def _find_open(
  trades: list[dict],
  *,
  signal_id: str | None = None,
  ticket: int | str | None = None,
) -> dict | None:
  for t in reversed(trades):
    if t.get("status") != "OPEN":
      continue
    if ticket is not None and str(t.get("ticket")) == str(ticket):
      return t
    if signal_id and t.get("signal_id") == signal_id:
      return t
  # fallback: latest open
  for t in reversed(trades):
    if t.get("status") == "OPEN":
      return t
  return None


def process_fill(
  fill: dict,
  *,
  bridge_dir: Path | None = None,
  decision: dict | None = None,
  model_id: str | None = None,
) -> dict | None:
  """
  Ingest EA fill.json event.
  event: open | close (also accept detail=opened / closed)
  Returns updated trade row or None.
  """
  if not isinstance(fill, dict):
    return None
  if fill.get("ok") is False:
    append_event(
      "ea_to_app", "fill_rejected", bridge_dir=bridge_dir, payload=fill,
      summary=f"reject {fill.get('action')} {fill.get('detail')}",
    )
    _append_fill_log(fill, bridge_dir)
    return None

  event = str(fill.get("event") or "").lower()
  detail = str(fill.get("detail") or "").lower()
  if not event:
    if detail in ("opened", "open"):
      event = "open"
    elif detail in ("closed", "close", "sl", "tp", "max_hold", "manual"):
      event = "close"
    else:
      # legacy: action BUY/SELL + ok => open
      act = str(fill.get("action") or "").upper()
      if act in ("BUY", "SELL") and fill.get("ok", True):
        event = "open"

  _append_fill_log({**fill, "event": event}, bridge_dir)
  trades = load_trades(bridge_dir)

  if event == "open":
    action = str(fill.get("action") or (decision or {}).get("action") or "").upper()
    if action not in ("BUY", "SELL"):
      return None
    sid = fill.get("signal_id") or (decision or {}).get("signal_id")
    # dedupe same signal open
    if sid:
      for t in trades:
        if t.get("signal_id") == sid and t.get("status") in ("OPEN", "CLOSED"):
          return t
    entry = fill.get("price") or fill.get("entry") or (decision or {}).get("entry")
    sl = fill.get("sl") if fill.get("sl") is not None else (decision or {}).get("sl")
    tp = fill.get("tp") if fill.get("tp") is not None else (decision or {}).get("tp")
    row = {
      "id": f"bt_{sid or fill.get('ticket') or _now()}",
      "signal_id": sid,
      "ticket": fill.get("ticket"),
      "symbol": fill.get("symbol") or "EURUSD",
      "direction": action,
      "status": "OPEN",
      "entry_time": fill.get("time") or _now(),
      "entry_px": float(entry) if entry is not None else None,
      "sl": float(sl) if sl is not None else None,
      "tp": float(tp) if tp is not None else None,
      "lots": float(fill["lots"]) if fill.get("lots") is not None else None,
      "exit_time": None,
      "exit_px": None,
      "profit": None,
      "r": None,
      "result": None,  # WIN / LOSS / BE
      "reason": None,
      "model_id": model_id or (decision or {}).get("model_id"),
      "bar_time": (decision or {}).get("bar_time") or fill.get("bar_time"),
      "strategy_name": (decision or {}).get("strategy_name"),
      "updated_at": _now(),
    }
    trades.append(row)
    save_trades(trades, bridge_dir)
    append_event(
      "ea_to_app", "trade_opened", bridge_dir=bridge_dir, payload=row,
      summary=f"OPEN {action} ticket={row.get('ticket')} entry={row.get('entry_px')}",
    )
    return row

  if event == "close":
    ticket = fill.get("ticket")
    sid = fill.get("signal_id")
    row = _find_open(trades, signal_id=sid, ticket=ticket)
    if not row:
      # orphan close — still record
      row = {
        "id": f"bt_close_{ticket or _now()}",
        "signal_id": sid,
        "ticket": ticket,
        "symbol": fill.get("symbol") or "EURUSD",
        "direction": str(fill.get("action") or "").upper() or "?",
        "status": "CLOSED",
        "entry_time": None,
        "entry_px": fill.get("entry"),
        "sl": fill.get("sl"),
        "tp": fill.get("tp"),
        "lots": fill.get("lots"),
        "model_id": model_id,
      }
      trades.append(row)

    exit_px = fill.get("price") or fill.get("exit_px") or fill.get("close_price")
    entry = row.get("entry_px")
    sl = row.get("sl") if row.get("sl") is not None else fill.get("sl")
    direction = row.get("direction") or fill.get("action")
    r = None
    if entry is not None and exit_px is not None and sl is not None:
      r = _compute_r(str(direction), float(entry), float(exit_px), float(sl))
    elif fill.get("profit") is not None and fill.get("risk_money"):
      try:
        r = round(float(fill["profit"]) / float(fill["risk_money"]), 3)
      except (TypeError, ValueError, ZeroDivisionError):
        r = None

    result = None
    if r is not None:
      if r > 0.05:
        result = "WIN"
      elif r < -0.05:
        result = "LOSS"
      else:
        result = "BE"
    elif fill.get("profit") is not None:
      p = float(fill["profit"])
      result = "WIN" if p > 0 else ("LOSS" if p < 0 else "BE")

    row.update({
      "status": "CLOSED",
      "exit_time": fill.get("time") or _now(),
      "exit_px": float(exit_px) if exit_px is not None else row.get("exit_px"),
      "profit": float(fill["profit"]) if fill.get("profit") is not None else row.get("profit"),
      "r": r if r is not None else row.get("r"),
      "result": result or row.get("result"),
      "reason": fill.get("reason") or fill.get("detail") or row.get("reason"),
      "lots": fill.get("lots") if fill.get("lots") is not None else row.get("lots"),
      "updated_at": _now(),
    })
    save_trades(trades, bridge_dir)
    append_event(
      "ea_to_app", "trade_closed", bridge_dir=bridge_dir, payload=row,
      summary=(
        f"CLOSE {row.get('direction')} {row.get('result')} "
        f"R={row.get('r')} profit={row.get('profit')} reason={row.get('reason')}"
      ),
    )
    return row

  return None


def _parse_trade_ts(val) -> Any:
  if val is None or val == "":
    return None
  try:
    import pandas as pd
    ts = pd.Timestamp(val)
    if getattr(ts, "tzinfo", None) is not None:
      ts = ts.tz_convert(None)
    return ts
  except Exception:
    return None


def filter_trades(
  trades: list[dict] | None = None,
  *,
  bridge_dir: Path | None = None,
  date_from=None,
  date_to=None,
  use_exit_time: bool = True,
) -> list[dict]:
  """
  Filter trades by time window.
  Closed trades: prefer exit_time (else entry_time).
  Open trades: entry_time.
  date_from/date_to inclusive by calendar day [from, to].
  """
  trades = trades if trades is not None else load_trades(bridge_dir)
  if date_from is None and date_to is None:
    return list(trades)

  import pandas as pd
  start = pd.Timestamp(date_from).normalize() if date_from is not None else None
  end = (pd.Timestamp(date_to).normalize() + pd.Timedelta(days=1)) if date_to is not None else None

  out: list[dict] = []
  for t in trades:
    if t.get("status") == "CLOSED" and use_exit_time and t.get("exit_time"):
      ts = _parse_trade_ts(t.get("exit_time"))
    else:
      ts = _parse_trade_ts(t.get("entry_time") or t.get("exit_time") or t.get("updated_at"))
    if ts is None:
      continue
    if start is not None and ts < start:
      continue
    if end is not None and ts >= end:
      continue
    out.append(t)
  return out


def compute_stats(
  trades: list[dict] | None = None,
  bridge_dir: Path | None = None,
  *,
  date_from=None,
  date_to=None,
) -> dict[str, Any]:
  raw = trades if trades is not None else load_trades(bridge_dir)
  filtered = filter_trades(raw, date_from=date_from, date_to=date_to)
  closed = [t for t in filtered if t.get("status") == "CLOSED"]
  open_n = sum(1 for t in filtered if t.get("status") == "OPEN")
  wins = [t for t in closed if t.get("result") == "WIN"]
  losses = [t for t in closed if t.get("result") == "LOSS"]
  bes = [t for t in closed if t.get("result") == "BE"]
  # equity curve in exit-time order
  closed_sorted = sorted(
    closed,
    key=lambda t: str(t.get("exit_time") or t.get("entry_time") or ""),
  )
  rs = [float(t["r"]) for t in closed_sorted if t.get("r") is not None]
  profits = [float(t["profit"]) for t in closed if t.get("profit") is not None]

  total_r = round(sum(rs), 3) if rs else 0.0
  wr = round(100.0 * len(wins) / len(closed), 1) if closed else None
  avg_r = round(sum(rs) / len(rs), 3) if rs else None
  peak = 0.0
  eq = 0.0
  max_dd = 0.0
  for r in rs:
    eq += r
    peak = max(peak, eq)
    max_dd = min(max_dd, eq - peak)

  return {
    "n_trades": len(closed),
    "n_open": open_n,
    "n_wins": len(wins),
    "n_losses": len(losses),
    "n_be": len(bes),
    "win_rate_pct": wr,
    "total_r": total_r,
    "avg_r": avg_r,
    "max_drawdown_r": round(abs(max_dd), 3) if rs else 0.0,
    "total_profit": round(sum(profits), 2) if profits else None,
    "date_from": str(date_from) if date_from is not None else None,
    "date_to": str(date_to) if date_to is not None else None,
    "n_filtered": len(filtered),
    "updated_at": _now(),
  }


def clear_trades(bridge_dir: Path | None = None) -> None:
  save_trades([], bridge_dir)
