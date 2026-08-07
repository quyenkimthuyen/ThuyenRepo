"""Shared Live desk stats — today/week PnL, open trade, unrealized R."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def fmt_px(value) -> str:
  try:
    return f"{float(value):.5f}"
  except (TypeError, ValueError):
    return "—"


def unrealized_r(trade: dict, connection: dict) -> float | None:
  """Estimate open R from live bid/ask vs entry/SL."""
  try:
    entry = float(
      trade.get("entry_px") if trade.get("entry_px") is not None else trade.get("entry")
    )
    sl = float(trade["sl"])
  except (TypeError, ValueError, KeyError):
    return None
  risk = abs(entry - sl)
  if risk <= 0:
    return None
  direction = str(trade.get("direction") or trade.get("dir") or "").upper()
  bid, ask = connection.get("bid"), connection.get("ask")
  try:
    if direction in ("BUY", "LONG"):
      mark = float(bid)
      return round((mark - entry) / risk, 3)
    if direction in ("SELL", "SHORT"):
      mark = float(ask)
      return round((entry - mark) / risk, 3)
  except (TypeError, ValueError):
    return None
  return None


def open_trades(trades: list[dict], *, mode: str | None = "auto") -> list[dict]:
  from mt5_bridge.trade_journal import trade_mode

  out = []
  for t in trades or []:
    if str(t.get("status") or "").upper() != "OPEN":
      continue
    if mode is None or trade_mode(t) == mode:
      out.append(t)
  return out


def open_trade(trades: list[dict]) -> dict | None:
  opens = open_trades(trades, mode=None)
  return opens[-1] if opens else None


def count_open(trades: list[dict], *, mode: str | None = "auto") -> int:
  return len(open_trades(trades, mode=mode))


def period_stats(
  trades: list[dict],
  *,
  today: date | None = None,
  model_id: str | None = None,
) -> tuple[dict, dict]:
  """Desk PnL = Auto only (Trade Model). Manual-edited fills stay out."""
  from mt5_bridge.trade_journal import compute_stats, filter_trades

  today = today or date.today()
  week_from = today - timedelta(days=today.weekday())
  today_stats = compute_stats(
    filter_trades(trades, date_from=today, date_to=today, mode="auto", model_id=model_id),
  )
  week_stats = compute_stats(
    filter_trades(trades, date_from=week_from, date_to=today, mode="auto", model_id=model_id),
  )
  return today_stats, week_stats


def snapshot_live_desk(
  *,
  bridge_dir=None,
  today: date | None = None,
  model_ids: list[str] | None = None,
) -> dict[str, Any]:
  """One-shot Live desk snapshot for dashboard (no Streamlit)."""
  from mt5_bridge import background as bridge_bg
  from mt5_bridge.protocol import (
    connection_path,
    decision_path,
    normalize_model_ids,
    read_json,
    read_models_roster,
    resolve_live_bridge_dir,
    status_path,
  )
  from mt5_bridge.trade_journal import load_trades, trade_mode
  from gui.mt5_live_chart import connection_health

  bdir = bridge_dir or resolve_live_bridge_dir()
  today = today or date.today()
  connection = read_json(connection_path(bdir)) or {}
  decision = read_json(decision_path(bdir)) or {}
  file_status = read_json(status_path(bdir)) or {}
  service_status = bridge_bg.get_status()
  trades = load_trades(bdir)
  health = connection_health(connection, stale_after_seconds=10.0, bridge_dir=bdir)
  today_stats, week_stats = period_stats(trades, today=today)

  cfg = bridge_bg.load_config()
  roster = read_models_roster(bdir)
  roster_ids = [
    str(r.get("id"))
    for r in (roster.get("models") or [])
    if isinstance(r, dict) and r.get("id")
  ]
  ids = normalize_model_ids(
    model_ids if model_ids is not None else (cfg.get("model_ids") or roster_ids),
    fallback=cfg.get("model_id") or decision.get("model_id"),
  )
  per_model = []
  for mid in ids:
    t_stats, w_stats = period_stats(trades, today=today, model_id=mid)
    opens = [t for t in open_trades(trades, mode="auto") if str(t.get("model_id") or "") == mid]
    ot = opens[-1] if opens else None
    per_model.append({
      "model_id": mid,
      "today_stats": t_stats,
      "week_stats": w_stats,
      "open_trade": ot,
      "unrealized_r": unrealized_r(ot, connection) if ot else None,
      "open_count": len(opens),
      "last_action": ((file_status.get("per_model") or {}).get(mid) or {}).get("action"),
      "magic": next(
        (r.get("magic") for r in (roster.get("models") or [])
         if isinstance(r, dict) and str(r.get("id")) == mid),
        None,
      ),
    })

  opens_all = open_trades(trades, mode="auto")
  ot = opens_all[-1] if opens_all else open_trade(trades)
  ur = unrealized_r(ot, connection) if ot else None
  open_auto = count_open(trades, mode="auto")
  open_manual = sum(
    1 for t in trades
    if str(t.get("status") or "").upper() == "OPEN" and trade_mode(t) != "auto"
  )
  return {
    "connection": connection,
    "decision": decision,
    "file_status": file_status,
    "service_status": service_status,
    "trades": trades,
    "health": health,
    "today_stats": today_stats,
    "week_stats": week_stats,
    "open_trade": ot,
    "open_trades": opens_all,
    "unrealized_r": ur,
    "open_auto": open_auto,
    "open_manual": open_manual,
    "model_ids": ids,
    "per_model": per_model,
    "today": today,
  }
