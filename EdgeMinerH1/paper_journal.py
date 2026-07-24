"""Persistent paper trade journal — period stats / reset like MT5 Bridge."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_backtest import REPORT_DIR

TRADES_NAME = "paper_trades.json"
TRADES_PATH = REPORT_DIR / TRADES_NAME
_lock = threading.RLock()


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read() -> dict:
  if not TRADES_PATH.exists():
    return {"updated_at": None, "monitor_from": None, "trades": []}
  try:
    with open(TRADES_PATH, encoding="utf-8-sig") as handle:
      data = json.load(handle)
    if not isinstance(data, dict):
      return {"updated_at": None, "monitor_from": None, "trades": []}
    trades = data.get("trades")
    if not isinstance(trades, list):
      trades = []
    return {
      "updated_at": data.get("updated_at"),
      "monitor_from": data.get("monitor_from"),
      "trades": trades,
    }
  except (OSError, json.JSONDecodeError):
    return {"updated_at": None, "monitor_from": None, "trades": []}


def _write(payload: dict) -> None:
  REPORT_DIR.mkdir(parents=True, exist_ok=True)
  tmp = TRADES_PATH.with_suffix(TRADES_PATH.suffix + ".tmp")
  with open(tmp, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, ensure_ascii=False, default=str)
  tmp.replace(TRADES_PATH)


def load_meta() -> dict:
  data = _read()
  return {
    "updated_at": data.get("updated_at"),
    "monitor_from": data.get("monitor_from"),
    "n_trades": len(data.get("trades") or []),
  }


def load_trades() -> list[dict]:
  return list(_read().get("trades") or [])


def save_trades(trades: list[dict], *, monitor_from: str | None = None) -> None:
  with _lock:
    data = _read()
    payload = {
      "updated_at": _now(),
      "monitor_from": (
        monitor_from if monitor_from is not None else data.get("monitor_from")
      ),
      "trades": list(trades),
    }
    _write(payload)


def _parse_ts(value) -> Any:
  if value in (None, ""):
    return None
  try:
    import pandas as pd
    return pd.Timestamp(value)
  except Exception:
    return None


def _trade_key(row: dict) -> str:
  return "|".join([
    str(row.get("entry") or row.get("entry_time") or ""),
    str(row.get("dir") or row.get("direction") or ""),
    str(row.get("entry_px") or ""),
  ])


def _normalize_row(row: dict, *, model_id: str | None = None) -> dict | None:
  status = str(row.get("status") or "CLOSED").upper()
  if status == "SIGNAL":
    return None
  entry = row.get("entry") or row.get("entry_time")
  if not entry:
    return None
  direction = row.get("dir") or row.get("direction")
  r_val = row.get("r")
  result = None
  if status == "CLOSED" and r_val is not None:
    try:
      rv = float(r_val)
      result = "WIN" if rv > 0 else ("LOSS" if rv < 0 else "BE")
    except (TypeError, ValueError):
      result = None
  return {
    "status": "OPEN" if status == "OPEN" else "CLOSED",
    "result": result,
    "direction": direction,
    "dir": direction,
    "signal_time": row.get("signal_time"),
    "entry_time": entry,
    "entry": entry,
    "exit_time": row.get("exit"),
    "exit": row.get("exit"),
    "entry_px": row.get("entry_px"),
    "exit_px": row.get("exit_px"),
    "sl": row.get("sl"),
    "tp": row.get("tp"),
    "r": row.get("r"),
    "pnl_pips": row.get("pnl_pips"),
    "reason": row.get("reason"),
    "risk_pips": row.get("risk_pips"),
    "risk_pct": row.get("risk_pct"),
    "pnl_pct": row.get("pnl_pct"),
    "rr": row.get("rr"),
    "model_id": row.get("model_id") or model_id,
    "strategy_name": row.get("strategy_name"),
    "updated_at": _now(),
  }


def sync_from_state(state: dict | None) -> list[dict]:
  """Merge CLOSED/OPEN paper orders into the persistent journal."""
  if not state or state.get("error") or state.get("pending"):
    return load_trades()

  monitor_from = _parse_ts((_read() or {}).get("monitor_from"))
  model_id = state.get("model_id")
  strategy_name = (state.get("strategy") or {}).get("name")
  incoming: list[dict] = []
  for row in list(state.get("orders") or []) + list(state.get("recent_trades") or []):
    norm = _normalize_row(
      {**row, "strategy_name": row.get("strategy_name") or strategy_name},
      model_id=model_id,
    )
    if not norm:
      continue
    entry_ts = _parse_ts(norm.get("entry_time"))
    if monitor_from is not None and entry_ts is not None and entry_ts < monitor_from:
      continue
    incoming.append(norm)

  with _lock:
    data = _read()
    by_key = {_trade_key(t): t for t in (data.get("trades") or [])}
    for row in incoming:
      key = _trade_key(row)
      prev = by_key.get(key)
      if prev and prev.get("status") == "CLOSED" and row.get("status") == "OPEN":
        continue
      by_key[key] = {**(prev or {}), **row}
    trades = sorted(
      by_key.values(),
      key=lambda t: str(t.get("entry_time") or t.get("exit_time") or ""),
    )
    _write({
      "updated_at": _now(),
      "monitor_from": data.get("monitor_from"),
      "trades": trades,
    })
    return trades


def filter_trades(
  trades: list[dict] | None = None,
  *,
  date_from=None,
  date_to=None,
  use_exit_time: bool = True,
) -> list[dict]:
  trades = trades if trades is not None else load_trades()
  if date_from is None and date_to is None:
    return list(trades)

  import pandas as pd
  start = pd.Timestamp(date_from).normalize() if date_from is not None else None
  end = (
    (pd.Timestamp(date_to).normalize() + pd.Timedelta(days=1))
    if date_to is not None else None
  )
  out: list[dict] = []
  for trade in trades:
    if trade.get("status") == "CLOSED" and use_exit_time and trade.get("exit_time"):
      ts = _parse_ts(trade.get("exit_time"))
    else:
      ts = _parse_ts(
        trade.get("entry_time") or trade.get("exit_time") or trade.get("updated_at")
      )
    if ts is None:
      continue
    if start is not None and ts < start:
      continue
    if end is not None and ts >= end:
      continue
    out.append(trade)
  return out


def compute_stats(trades: list[dict] | None = None) -> dict[str, Any]:
  trades = list(trades if trades is not None else load_trades())
  closed = [t for t in trades if t.get("status") == "CLOSED"]
  open_n = sum(1 for t in trades if t.get("status") == "OPEN")
  wins = [t for t in closed if t.get("result") == "WIN" or float(t.get("r") or 0) > 0]
  losses = [t for t in closed if t.get("result") == "LOSS" or float(t.get("r") or 0) < 0]
  bes = [t for t in closed if t.get("result") == "BE" or float(t.get("r") or 0) == 0]
  # Prefer explicit result classification when present
  if any(t.get("result") for t in closed):
    wins = [t for t in closed if t.get("result") == "WIN"]
    losses = [t for t in closed if t.get("result") == "LOSS"]
    bes = [t for t in closed if t.get("result") == "BE"]

  closed_sorted = sorted(
    closed,
    key=lambda t: str(t.get("exit_time") or t.get("entry_time") or ""),
  )
  rs = [float(t["r"]) for t in closed_sorted if t.get("r") is not None]
  total_r = round(sum(rs), 3) if rs else 0.0
  wr = round(100.0 * len(wins) / len(closed), 1) if closed else None
  avg_r = round(sum(rs) / len(rs), 3) if rs else None
  peak = eq = 0.0
  max_dd = 0.0
  for r in rs:
    eq += r
    peak = max(peak, eq)
    max_dd = min(max_dd, eq - peak)
  pips = [
    float(t["pnl_pips"]) for t in closed if t.get("pnl_pips") is not None
  ]
  by_reason: dict[str, int] = {}
  for t in closed:
    reason = str(t.get("reason") or "other")
    by_reason[reason] = by_reason.get(reason, 0) + 1
  return {
    "n_filtered": len(trades),
    "n_trades": len(closed),
    "n_open": open_n,
    "n_wins": len(wins),
    "n_losses": len(losses),
    "n_be": len(bes),
    "n_long": sum(1 for t in closed if str(t.get("direction") or t.get("dir")).upper() in ("LONG", "BUY")),
    "n_short": sum(1 for t in closed if str(t.get("direction") or t.get("dir")).upper() in ("SHORT", "SELL")),
    "win_rate_pct": wr,
    "total_r": total_r,
    "avg_r": avg_r,
    "max_drawdown_r": round(abs(max_dd), 3),
    "total_pips": round(sum(pips), 1) if pips else 0.0,
    "by_reason": by_reason,
  }


def clear_trades() -> None:
  with _lock:
    data = _read()
    _write({
      "updated_at": _now(),
      "monitor_from": data.get("monitor_from"),
      "trades": [],
    })


def reset_monitor() -> dict:
  """Wipe journal + set monitor_from=now so remine history before reset is ignored."""
  from paper_service import STATE_PATH

  stamp = _now()
  with _lock:
    _write({
      "updated_at": stamp,
      "monitor_from": stamp,
      "trades": [],
    })
  try:
    STATE_PATH.unlink(missing_ok=True)
  except OSError:
    pass
  return {"monitor_from": stamp, "updated_at": stamp}
