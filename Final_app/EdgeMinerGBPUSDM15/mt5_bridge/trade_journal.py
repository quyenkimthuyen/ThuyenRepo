"""Journal + stats for MT5 Bridge live trades (win/loss detail).

Modes (for fair strategy review):
  - auto   — strategy open, no user SL/TP edit, closed by SL/TP/trail/max_hold/EA
  - manual — test market button, user SL/TP edit, or user close on MT5
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mt5_bridge.comm_log import append_event
from mt5_bridge.protocol import BRIDGE_DIR, ensure_bridge_dir, atomic_write_json, read_json

TRADES_NAME = "trades.json"
FILLS_LOG_NAME = "fills.jsonl"
EA_FILLS_QUEUE_NAME = "ea_fills.jsonl"

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
    trades = list(data.get("trades") or [])
  elif isinstance(data, list):
    trades = data
  else:
    trades = []
  return dedupe_trades(trades)


def save_trades(trades: list[dict], bridge_dir: Path | None = None) -> None:
  atomic_write_json(trades_path(bridge_dir), {
    "updated_at": _now(),
    "trades": dedupe_trades(trades),
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



def _is_reconcile_placeholder(row: dict) -> bool:
  """Ghost closes from position_sync (no EA fill yet) — allow real fill to overwrite."""
  interventions = [str(x) for x in (row.get("interventions") or [])]
  reason = str(row.get("reason") or "").lower()
  if any(
    tag in interventions
    for tag in (
      "journal_desync",
      "ea_reconnect_reconcile",
      "worker_start_reconcile",
      "mt5_flat",
      "magic_not_in_roster",
    )
  ):
    return True
  if reason in (
    "ea_reconnect_reconcile",
    "worker_start_reconcile",
    "mt5_flat",
    "magic_not_in_roster",
  ):
    return True
  return False


def _find_open(
  trades: list[dict],
  *,
  signal_id: str | None = None,
  ticket: int | str | None = None,
  model_id: str | None = None,
  magic: int | str | None = None,
) -> dict | None:
  mid = str(model_id) if model_id else None
  mag = str(magic) if magic is not None and str(magic) != "" else None

  def _side_ok(t: dict) -> bool:
    if mid and str(t.get("model_id") or "") not in ("", mid):
      # Allow empty model_id on legacy rows only when magic matches.
      if mag is None or str(t.get("magic") or "") != mag:
        return False
    if mag is not None and str(t.get("magic") or "") not in ("", mag):
      if mid is None or str(t.get("model_id") or "") != mid:
        return False
    return True

  for t in reversed(trades):
    if t.get("status") != "OPEN":
      continue
    if not _side_ok(t):
      continue
    if ticket is not None and str(t.get("ticket")) == str(ticket):
      return t
    if signal_id and t.get("signal_id") == signal_id:
      return t
  for t in reversed(trades):
    if t.get("status") != "OPEN":
      continue
    if not _side_ok(t):
      continue
    return t
  # Legacy fallback: only when no model/magic scope requested
  if mid is None and mag is None:
    for t in reversed(trades):
      if t.get("status") == "OPEN":
        return t
  return None


def _find_by_ticket_or_signal(
  trades: list[dict],
  *,
  signal_id: str | None = None,
  ticket: int | str | None = None,
  statuses: tuple[str, ...] | None = None,
) -> dict | None:
  """Latest trade matching ticket/signal_id (optionally filtered by status)."""
  for t in reversed(trades):
    if statuses and str(t.get("status") or "").upper() not in statuses:
      continue
    if ticket is not None and str(t.get("ticket")) == str(ticket):
      return t
    if signal_id and t.get("signal_id") == signal_id:
      return t
  return None


def dedupe_trades(trades: list[dict]) -> list[dict]:
  """Keep one row per ticket (preferred) or id — HistoryFeed may re-send closes."""
  if not trades:
    return []

  def _prefer(prev: dict, cur: dict) -> dict:
    prev_closed = str(prev.get("status") or "").upper() == "CLOSED"
    cur_closed = str(cur.get("status") or "").upper() == "CLOSED"
    if cur_closed and not prev_closed:
      return cur
    if prev_closed and not cur_closed:
      return prev
    # Prefer row with strategy_name / richer fields
    prev_named = bool(prev.get("strategy_name"))
    cur_named = bool(cur.get("strategy_name"))
    if cur_named and not prev_named:
      return cur
    if prev_named and not cur_named:
      return prev
    if str(cur.get("updated_at") or "") >= str(prev.get("updated_at") or ""):
      return cur
    return prev

  by_ticket: dict[str, dict] = {}
  no_ticket: list[dict] = []
  for t in trades:
    ticket = t.get("ticket")
    if ticket is None or ticket == "":
      no_ticket.append(t)
      continue
    key = str(ticket)
    if key not in by_ticket:
      by_ticket[key] = t
    else:
      by_ticket[key] = _prefer(by_ticket[key], t)

  # Dedupe ticket-less rows by id
  by_id: dict[str, dict] = {}
  orphan: list[dict] = []
  for t in no_ticket:
    tid = t.get("id")
    if not tid:
      orphan.append(t)
      continue
    if tid not in by_id:
      by_id[tid] = t
    else:
      by_id[tid] = _prefer(by_id[tid], t)

  # Preserve roughly original order
  seen_tickets: set[str] = set()
  seen_ids: set[str] = set()
  out: list[dict] = []
  for t in trades:
    ticket = t.get("ticket")
    if ticket is not None and ticket != "":
      key = str(ticket)
      if key in seen_tickets:
        continue
      seen_tickets.add(key)
      out.append(by_ticket[key])
      continue
    tid = t.get("id")
    if tid:
      if tid in seen_ids:
        continue
      seen_ids.add(tid)
      out.append(by_id[tid])
      continue
    out.append(t)
  return out


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
      "manual_close", "ea_close", "stop_out", "trail",
      "end_range", "journal_desync", "sim_end_reconcile",
    ):
      event = "close"
    else:
      act = str(fill.get("action") or "").upper()
      if act in ("BUY", "SELL") and fill.get("ok", True):
        event = "open"

  trades = load_trades(bridge_dir)

  if event == "open":
    action = str(fill.get("action") or (decision or {}).get("action") or "").upper()
    if action not in ("BUY", "SELL"):
      return None
    sid = fill.get("signal_id") or (decision or {}).get("signal_id")
    ticket = fill.get("ticket")
    # Idempotent: Live restart / sticky fill.json must not spawn duplicate rows
    if sid:
      for t in trades:
        if t.get("signal_id") == sid and t.get("status") in ("OPEN", "CLOSED"):
          return t
    if ticket is not None:
      existing = _find_by_ticket_or_signal(
        trades, ticket=ticket, statuses=("OPEN", "CLOSED"),
      )
      if existing:
        return existing
    entry = fill.get("price") or fill.get("entry") or (decision or {}).get("entry")
    sl = fill.get("sl") if fill.get("sl") is not None else (decision or {}).get("sl")
    tp = fill.get("tp") if fill.get("tp") is not None else (decision or {}).get("tp")
    is_manual, source = _infer_open_manual(fill, decision)
    row = {
      "id": f"bt_{sid or fill.get('ticket') or _now()}",
      "signal_id": sid,
      "ticket": ticket,
      "symbol": fill.get("symbol") or "GBPUSD",
      "direction": action,
      "status": "OPEN",
      "mode": MODE_MANUAL if is_manual else MODE_AUTO,
      "origin": source,
      "intervened": is_manual,
      "interventions": ["manual_test_open"] if is_manual else [],
      "entry_time": fill.get("bar_time") or (decision or {}).get("bar_time") or fill.get("time") or _now(),
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
      "model_id": model_id or (decision or {}).get("model_id") or fill.get("model_id"),
      "magic": fill.get("magic") if fill.get("magic") is not None else (decision or {}).get("magic"),
      "bar_time": (decision or {}).get("bar_time") or fill.get("bar_time"),
      "strategy_name": (decision or {}).get("strategy_name"),
      "updated_at": _now(),
    }
    _append_fill_log({**fill, "event": event}, bridge_dir)
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
    mid = model_id or (decision or {}).get("model_id") or fill.get("model_id")
    mag = fill.get("magic") if fill.get("magic") is not None else (decision or {}).get("magic")
    row = _find_open(trades, signal_id=sid, ticket=ticket, model_id=mid, magic=mag)
    if not row:
      return None
    _append_fill_log({**fill, "event": event}, bridge_dir)
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
    mid = model_id or (decision or {}).get("model_id") or fill.get("model_id")
    mag = fill.get("magic") if fill.get("magic") is not None else (decision or {}).get("magic")
    row = _find_open(trades, signal_id=sid, ticket=ticket, model_id=mid, magic=mag)
    # EA / Live service restart often re-reads sticky fill.json. After the first
    # close the OPEN row is gone — update existing CLOSED, never append orphans.
    if not row:
      row = _find_by_ticket_or_signal(
        trades, signal_id=sid, ticket=ticket, statuses=("CLOSED",),
      )
      # Already finalized with a real exit — no-op.
      # Reconcile placeholders (BE @ entry, journal_desync) MUST be upgradable
      # when the real EA close fill arrives later.
      if row is not None and row.get("exit_px") is not None and not _is_reconcile_placeholder(row):
        return row
    if not row:
      is_manual, source = _infer_open_manual(fill, decision)
      row = {
        "id": f"bt_close_{ticket or _now()}",
        "signal_id": sid,
        "ticket": ticket,
        "symbol": fill.get("symbol") or "GBPUSD",
        "direction": str(fill.get("action") or "").upper() or "?",
        "status": "CLOSED",
        "mode": MODE_MANUAL if is_manual else MODE_AUTO,
        "origin": source,
        "intervened": is_manual,
        "interventions": ["orphan_close"],
        "entry_time": fill.get("bar_time") or (decision or {}).get("bar_time") or fill.get("time"),
        "entry_px": (
          fill.get("entry") if fill.get("entry") is not None
          else fill.get("entry_px") if fill.get("entry_px") is not None
          else fill.get("open_price")
        ),
        "sl": fill.get("sl"),
        "tp": fill.get("tp"),
        "sl_initial": fill.get("sl"),
        "tp_initial": fill.get("tp"),
        "lots": fill.get("lots"),
        "model_id": mid,
        "magic": mag,
      }
      if row["entry_px"] is not None:
        try:
          row["entry_px"] = float(row["entry_px"])
        except (TypeError, ValueError):
          row["entry_px"] = None
      trades.append(row)

    _append_fill_log({**fill, "event": event}, bridge_dir)
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
      "exit_time": fill.get("bar_time") or fill.get("time") or _now(),
      "exit_px": float(exit_px) if exit_px is not None else row.get("exit_px"),
      "profit": float(fill["profit"]) if fill.get("profit") is not None else row.get("profit"),
      "r": r if r is not None else row.get("r"),
      "result": result or row.get("result"),
      "reason": close_reason or row.get("reason"),
      "lots": fill.get("lots") if fill.get("lots") is not None else row.get("lots"),
      "updated_at": _now(),
    })
    # Prefer logical bar clock; reject wall-clock exits that dwarf max hold (HistoryFeed)
    exit_raw = row.get("exit_time")
    entry_raw = row.get("entry_time") or row.get("bar_time")
    if exit_raw and entry_raw and not fill.get("bar_time"):
      try:
        import pandas as pd
        et = pd.Timestamp(str(entry_raw).replace(".", "-")[:16])
        xt = pd.Timestamp(str(exit_raw).replace(".", "-")[:19])
        if xt < et or (xt - et) > pd.Timedelta(days=10):
          # Keep bar_time from fill.time only if it looks like broker minutes stamp
          tfill = str(fill.get("time") or "")
          if tfill.count(":") == 1 or (len(tfill) <= 16 and "T" not in tfill):
            row["exit_time"] = tfill
          else:
            row["exit_time"] = entry_raw  # last resort: mark close at entry bar
      except Exception:
        pass
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
  model_id: str | None = None,
) -> list[dict]:
  """
  Filter trades by time window and optional mode (auto|manual) / model_id.
  Closed trades: prefer exit_time (else entry_time).
  Open trades: entry_time.
  """
  trades = trades if trades is not None else load_trades(bridge_dir)
  mode_l = str(mode).lower() if mode else None
  if mode_l in ("", "all", "none"):
    mode_l = None
  mid = str(model_id) if model_id else None

  import pandas as pd
  start = pd.Timestamp(date_from).normalize() if date_from is not None else None
  end = (pd.Timestamp(date_to).normalize() + pd.Timedelta(days=1)) if date_to is not None else None

  out: list[dict] = []
  for t in trades:
    if mode_l and trade_mode(t) != mode_l:
      continue
    if mid and str(t.get("model_id") or "") != mid:
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
  use_exit_time: bool = True,
  model_id: str | None = None,
) -> dict[str, Any]:
  raw = trades if trades is not None else load_trades(bridge_dir)
  filtered = filter_trades(
    raw,
    date_from=date_from,
    date_to=date_to,
    mode=mode,
    use_exit_time=use_exit_time,
    model_id=model_id,
  )
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


def clear_decision(bridge_dir: Path | None = None) -> None:
  """Wipe stale decision.json so desk/Parity don't show leftover tip.

  Writes a neutral FLAT (no strategy/week/fp) so EA reads a safe file instead of
  an old tip from a previous model — without requiring Start Live to sync.
  """
  from datetime import datetime, timezone

  from mt5_bridge.protocol import atomic_write_json, decision_path, ensure_bridge_dir

  bridge_dir = ensure_bridge_dir(bridge_dir)
  now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
  atomic_write_json(
    decision_path(bridge_dir),
    {
      "action": "FLAT",
      "reason": "cleared_journal",
      "strategy_name": None,
      "week_start": None,
      "conditions_fp": None,
      "model_id": None,
      "updated_at": now,
      "signal_id": None,
      "entry": None,
      "sl": None,
      "tp": None,
    },
  )


def clear_trades(bridge_dir: Path | None = None, *, clear_decision_file: bool = True) -> None:
  save_trades([], bridge_dir)
  path = fills_log_path(bridge_dir)
  if path.exists():
    path.unlink()
  if clear_decision_file:
    clear_decision(bridge_dir)


def clear_sticky_fill_files(bridge_dir: Path | None = None) -> list[str]:
  """Remove single-slot fill.json / ea_fills queue without wiping the journal.

  Live Start must not re-ingest a sticky open fill after a previous Stop —
  that recreates ghost OPEN rows and freezes models on HOLD.
  """
  d = ensure_bridge_dir(bridge_dir)
  removed: list[str] = []
  for name in ("fill.json", EA_FILLS_QUEUE_NAME):
    path = d / name
    if path.exists():
      try:
        path.unlink()
        removed.append(name)
      except OSError:
        pass
  return removed


def drain_ea_fills_queue(bridge_dir: Path | None = None) -> list[dict[str, Any]]:
  """Atomically claim ``ea_fills.jsonl`` so EA appends during drain are not lost.

  Old path read-then-truncate raced multi-model closes at low delay_ms: EA could
  append a close between read and truncate, App wiped it, journal stayed OPEN
  forever (engine HOLD / position_open).
  """
  d = ensure_bridge_dir(bridge_dir)
  path = d / EA_FILLS_QUEUE_NAME
  if not path.exists():
    return []
  try:
    if path.stat().st_size <= 0:
      return []
  except OSError:
    return []

  claimed = d / f".ea_fills_drain_{time.time_ns()}.jsonl"
  raw = ""
  try:
    os.replace(path, claimed)
    raw = claimed.read_text(encoding="utf-8-sig")
  except OSError:
    # Rename busy (EA has handle) — best-effort read + truncate + re-read.
    try:
      raw = path.read_text(encoding="utf-8-sig")
      path.write_text("", encoding="utf-8")
      extra = path.read_text(encoding="utf-8-sig")
      if extra.strip():
        raw = (raw or "") + ("\n" if raw and not raw.endswith("\n") else "") + extra
        path.write_text("", encoding="utf-8")
    except OSError:
      return []
  finally:
    try:
      if claimed.exists():
        claimed.unlink()
    except OSError:
      pass

  out: list[dict[str, Any]] = []
  for line in (raw or "").splitlines():
    line = line.strip()
    if not line:
      continue
    try:
      payload = json.loads(line)
    except Exception:
      continue
    if isinstance(payload, dict):
      out.append(payload)
  return out


def close_ghost_journal_opens(
  bridge_dir: Path | None = None,
  *,
  reason: str = "journal_desync",
  model_id: str | None = None,
) -> int:
  """Mark journal OPEN rows CLOSED when EA/paper is already flat (desync repair)."""
  trades = load_trades(bridge_dir)
  mid = str(model_id) if model_id else None
  n = 0
  now = _now()
  for t in trades:
    if str(t.get("status") or "").upper() != "OPEN":
      continue
    if mid and str(t.get("model_id") or "") != mid:
      continue
    t["status"] = "CLOSED"
    t["exit_time"] = t.get("exit_time") or now
    if t.get("exit_px") is None:
      t["exit_px"] = t.get("entry_px")
    t["reason"] = reason
    if t.get("result") is None:
      t["result"] = "BE"
    if t.get("r") is None:
      t["r"] = 0.0
    t["updated_at"] = now
    interventions = list(t.get("interventions") or [])
    if "journal_desync" not in interventions:
      interventions.append("journal_desync")
    t["interventions"] = interventions
    n += 1
  if n:
    save_trades(trades, bridge_dir)
    append_event(
      "system",
      "journal_desync_cleared",
      bridge_dir=bridge_dir,
      summary=f"closed {n} ghost OPEN ({reason})",
      payload={"n": n, "reason": reason, "model_id": mid},
    )
  clear_sticky_fill_files(bridge_dir)
  return n


def count_open_trades(bridge_dir: Path | None = None, *, model_id: str | None = None) -> int:
  mid = str(model_id) if model_id else None
  n = 0
  for t in load_trades(bridge_dir):
    if str(t.get("status") or "").upper() != "OPEN":
      continue
    if mid and str(t.get("model_id") or "") != mid:
      continue
    n += 1
  return n
