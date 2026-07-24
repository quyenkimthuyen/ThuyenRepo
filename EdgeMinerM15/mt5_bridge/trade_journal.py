"""Journal + stats for MT5 Bridge live trades (win/loss detail).

Modes (for fair strategy review):
  - auto   — strategy open, no user SL/TP edit, closed by SL/TP/trail/max_hold/EA
  - manual — test market button, user SL/TP edit, or user close on MT5
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mt5_bridge.comm_log import append_event
from mt5_bridge.protocol import BRIDGE_DIR, ensure_bridge_dir, atomic_write_json, read_json

TRADES_NAME = "trades.json"
FILLS_LOG_NAME = "fills.jsonl"

MODE_AUTO = "auto"
MODE_MANUAL = "manual"

_MANUAL_CLOSE_REASONS = {
  "manual_close",
  "manual_test_close",
  "client",
  "user",
  "manual",
}
_MANUAL_OPEN_MARKERS = ("manual_test", "manual_bridge", "manual_close")


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
  for t in reversed(trades):
    if t.get("status") == "OPEN":
      return t
  return None


def _mark_manual(row: dict, reason: str) -> None:
  row["mode"] = MODE_MANUAL
  row["intervened"] = True
  flags = list(row.get("interventions") or [])
  if reason and reason not in flags:
    flags.append(reason)
  row["interventions"] = flags


def trade_mode(trade: dict) -> str:
  """Normalize mode for filtering (legacy rows → auto unless markers present)."""
  m = str(trade.get("mode") or "").lower()
  if m in (MODE_AUTO, MODE_MANUAL):
    return m
  if trade.get("intervened"):
    return MODE_MANUAL
  sid = str(trade.get("signal_id") or "")
  if any(sid.startswith(p) for p in ("manual_test", "manual_close")):
    return MODE_MANUAL
  reason = str(trade.get("reason") or "").lower()
  if reason in _MANUAL_CLOSE_REASONS or "manual" in reason:
    return MODE_MANUAL
  return MODE_AUTO


def _infer_open_manual(fill: dict, decision: dict | None) -> tuple[bool, str]:
  if fill.get("manual") is True:
    src = str(fill.get("source") or "manual_test")
    return True, src
  src = str(fill.get("source") or "").lower()
  if src in ("manual_test", "user_edit", "manual"):
    return True, src or "manual_test"
  sid = str(fill.get("signal_id") or (decision or {}).get("signal_id") or "")
  reason = str(fill.get("reason") or "").lower()
  if any(sid.startswith(p) for p in _MANUAL_OPEN_MARKERS) or "manual" in reason:
    return True, "manual_test"
  return False, "strategy"


def process_fill(
  fill: dict,
  *,
  bridge_dir: Path | None = None,
  decision: dict | None = None,
  model_id: str | None = None,
) -> dict | None:
  """
  Ingest EA fill.json event.
  event: open | modify | close
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
    elif detail in ("user_sl_tp", "ea_trail", "modify"):
      event = "modify"
    elif detail in (
      "closed", "close", "sl", "tp", "max_hold", "manual",
      "manual_close", "ea_close", "stop_out",
    ):
      event = "close"
    else:
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
    if sid:
      for t in trades:
        if t.get("signal_id") == sid and t.get("status") in ("OPEN", "CLOSED"):
          return t
    entry = fill.get("price") or fill.get("entry") or (decision or {}).get("entry")
    sl = fill.get("sl") if fill.get("sl") is not None else (decision or {}).get("sl")
    tp = fill.get("tp") if fill.get("tp") is not None else (decision or {}).get("tp")
    is_manual, source = _infer_open_manual(fill, decision)
    row = {
      "id": f"bt_{sid or fill.get('ticket') or _now()}",
      "signal_id": sid,
      "ticket": fill.get("ticket"),
      "symbol": fill.get("symbol") or "EURUSD",
      "direction": action,
      "status": "OPEN",
      "mode": MODE_MANUAL if is_manual else MODE_AUTO,
      "origin": source,
      "intervened": is_manual,
      "interventions": ["manual_test_open"] if is_manual else [],
      "entry_time": fill.get("time") or _now(),
      "entry_px": float(entry) if entry is not None else None,
      "sl": float(sl) if sl is not None else None,
      "tp": float(tp) if tp is not None else None,
      "sl_initial": float(sl) if sl is not None else None,
      "tp_initial": float(tp) if tp is not None else None,
      "lots": float(fill["lots"]) if fill.get("lots") is not None else None,
      "exit_time": None,
      "exit_px": None,
      "profit": None,
      "r": None,
      "result": None,
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
      summary=(
        f"OPEN {action} mode={row['mode']} ticket={row.get('ticket')} "
        f"entry={row.get('entry_px')}"
      ),
    )
    return row

  if event == "modify":
    ticket = fill.get("ticket")
    sid = fill.get("signal_id")
    row = _find_open(trades, signal_id=sid, ticket=ticket)
    if not row:
      return None
    detail_l = detail or str(fill.get("reason") or "").lower()
    if fill.get("sl") is not None:
      row["sl"] = float(fill["sl"])
    if fill.get("tp") is not None:
      row["tp"] = float(fill["tp"])
    if fill.get("lots") is not None:
      try:
        row["lots"] = float(fill["lots"])
      except (TypeError, ValueError):
        pass
    # EA trail sync keeps auto mode; user edit → manual
    if detail_l in ("user_sl_tp",) or fill.get("manual") is True or str(fill.get("source") or "") == "user_edit":
      _mark_manual(row, "user_sl_tp")
    elif detail_l == "ea_trail":
      flags = list(row.get("interventions") or [])
      if "ea_trail" not in flags:
        flags.append("ea_trail")
      row["interventions"] = flags
    row["updated_at"] = _now()
    save_trades(trades, bridge_dir)
    append_event(
      "ea_to_app", "trade_modified", bridge_dir=bridge_dir, payload=row,
      summary=(
        f"MODIFY {row.get('direction')} mode={trade_mode(row)} "
        f"sl={row.get('sl')} tp={row.get('tp')} detail={detail_l}"
      ),
    )
    return row

  if event == "close":
    ticket = fill.get("ticket")
    sid = fill.get("signal_id")
    row = _find_open(trades, signal_id=sid, ticket=ticket)
    if not row:
      is_manual, source = _infer_open_manual(fill, decision)
      row = {
        "id": f"bt_close_{ticket or _now()}",
        "signal_id": sid,
        "ticket": ticket,
        "symbol": fill.get("symbol") or "EURUSD",
        "direction": str(fill.get("action") or "").upper() or "?",
        "status": "CLOSED",
        "mode": MODE_MANUAL if is_manual else MODE_AUTO,
        "origin": source,
        "intervened": is_manual,
        "interventions": ["orphan_close"],
        "entry_time": None,
        "entry_px": fill.get("entry"),
        "sl": fill.get("sl"),
        "tp": fill.get("tp"),
        "sl_initial": fill.get("sl"),
        "tp_initial": fill.get("tp"),
        "lots": fill.get("lots"),
        "model_id": model_id,
      }
      trades.append(row)

    exit_px = fill.get("price") or fill.get("exit_px") or fill.get("close_price")
    entry = row.get("entry_px")
    # Fair R: always vs planned (initial) SL
    sl_for_r = row.get("sl_initial")
    if sl_for_r is None:
      sl_for_r = row.get("sl") if row.get("sl") is not None else fill.get("sl")
    direction = row.get("direction") or fill.get("action")
    r = None
    if entry is not None and exit_px is not None and sl_for_r is not None:
      r = _compute_r(str(direction), float(entry), float(exit_px), float(sl_for_r))
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

    close_reason = str(fill.get("reason") or fill.get("detail") or row.get("reason") or "")
    close_l = close_reason.lower()
    if (
      fill.get("manual") is True
      or close_l in _MANUAL_CLOSE_REASONS
      or "manual" in close_l
      or trade_mode(row) == MODE_MANUAL
    ):
      tag = "manual_close" if close_l in _MANUAL_CLOSE_REASONS or "manual" in close_l else "intervened"
      _mark_manual(row, tag)

    # Keep current SL/TP from fill if present (last synced levels)
    if fill.get("sl") is not None:
      row["sl"] = float(fill["sl"])
    if fill.get("tp") is not None:
      row["tp"] = float(fill["tp"])

    row.update({
      "status": "CLOSED",
      "exit_time": fill.get("time") or _now(),
      "exit_px": float(exit_px) if exit_px is not None else row.get("exit_px"),
      "profit": float(fill["profit"]) if fill.get("profit") is not None else row.get("profit"),
      "r": r if r is not None else row.get("r"),
      "result": result or row.get("result"),
      "reason": close_reason or row.get("reason"),
      "lots": fill.get("lots") if fill.get("lots") is not None else row.get("lots"),
      "updated_at": _now(),
    })
    if "mode" not in row or not row.get("mode"):
      row["mode"] = trade_mode(row)
    save_trades(trades, bridge_dir)
    append_event(
      "ea_to_app", "trade_closed", bridge_dir=bridge_dir, payload=row,
      summary=(
        f"CLOSE {row.get('direction')} mode={trade_mode(row)} {row.get('result')} "
        f"R={row.get('r')} reason={row.get('reason')}"
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
  mode: str | None = None,
) -> list[dict]:
  """
  Filter trades by time window and optional mode (auto|manual).
  Closed trades: prefer exit_time (else entry_time).
  Open trades: entry_time.
  """
  trades = trades if trades is not None else load_trades(bridge_dir)
  mode_l = str(mode).lower() if mode else None
  if mode_l in ("", "all", "none"):
    mode_l = None

  import pandas as pd
  start = pd.Timestamp(date_from).normalize() if date_from is not None else None
  end = (pd.Timestamp(date_to).normalize() + pd.Timedelta(days=1)) if date_to is not None else None

  out: list[dict] = []
  for t in trades:
    if mode_l and trade_mode(t) != mode_l:
      continue
    if date_from is None and date_to is None:
      out.append(t)
      continue
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
  mode: str | None = None,
) -> dict[str, Any]:
  raw = trades if trades is not None else load_trades(bridge_dir)
  filtered = filter_trades(raw, date_from=date_from, date_to=date_to, mode=mode)
  closed = [t for t in filtered if t.get("status") == "CLOSED"]
  open_n = sum(1 for t in filtered if t.get("status") == "OPEN")
  wins = [t for t in closed if t.get("result") == "WIN"]
  losses = [t for t in closed if t.get("result") == "LOSS"]
  bes = [t for t in closed if t.get("result") == "BE"]
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

  mode_norm = str(mode).lower() if mode else None
  if mode_norm in ("", "all", "none"):
    mode_norm = None

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
    "mode": mode_norm,
  }


def clear_trades(bridge_dir: Path | None = None) -> None:
  save_trades([], bridge_dir)
  path = fills_log_path(bridge_dir)
  if path.exists():
    path.unlink()
