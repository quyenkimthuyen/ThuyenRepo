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
_AUTO_EXIT_REASONS = {
  "sl",
  "tp",
  "trail",
  "max_hold",
  "ea_close",
  "stop_out",
  "end_range",
  "closed",
  "close",
  "journal_desync",
  "sim_end_reconcile",
}


def _row_symbol(*sources: dict | None) -> str:
  """Symbol for journal rows — lazy import avoids paper_fill ↔ journal cycle."""
  try:
    from mt5_bridge.paper_fill import journal_symbol
    return journal_symbol(*sources)
  except Exception:
    for src in sources:
      if isinstance(src, dict):
        sym = str(src.get("symbol") or "").strip()
        if sym:
          return sym
    return "EURUSD"


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


def _r_from_profit_money(row: dict, profit: float) -> float | None:
  try:
    lots = float(row.get("lots") or 0)
    entry = row.get("entry_px")
    sl = row.get("sl_initial")
    if sl is None:
      sl = row.get("sl")
    entry_f = float(entry)
    sl_f = float(sl)
  except (TypeError, ValueError):
    return None
  if lots <= 0:
    return None
  risk_px = abs(entry_f - sl_f)
  if risk_px <= 0:
    return None
  risk_money = lots * 100000.0 * risk_px
  if risk_money <= 0:
    return None
  return round(float(profit) / risk_money, 3)


def _align_r_with_profit(r: float | None, result: str | None, fill: dict, row: dict) -> tuple[float | None, str | None]:
  """If fill price/R disagrees with broker profit, trust profit vs planned SL."""
  if fill.get("profit") is None:
    return r, result
  try:
    p = float(fill["profit"])
  except (TypeError, ValueError):
    return r, result
  disagree = r is not None and ((p < -1e-9 and r > 0.05) or (p > 1e-9 and r < -0.05))
  if disagree:
    aligned = _r_from_profit_money(row, p)
    if aligned is not None:
      r = aligned
    elif p < 0:
      r = -1.0
    elif p > 0:
      r = abs(r) if r is not None else 1.0
  if p > 1e-9:
    result = "WIN"
  elif p < -1e-9:
    result = "LOSS"
  elif result is None:
    result = "BE"
  return r, result


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
    t_mid = str(t.get("model_id") or "")
    t_mag = str(t.get("magic") or "")
    if mid:
      if t_mid == mid:
        pass
      elif t_mid == "":
        # Legacy empty model_id: allow only when magic matches.
        if mag is None or t_mag != mag:
          return False
      else:
        # Non-empty wrong model_id must never match (even if magic aligns).
        return False
    if mag is not None and t_mag not in ("", mag):
      if mid is None or t_mid != mid:
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
  # Fallback to any scoped OPEN only when caller did not name ticket/signal.
  if ticket is None and not signal_id:
    for t in reversed(trades):
      if t.get("status") != "OPEN":
        continue
      if not _side_ok(t):
        continue
      return t
  # Legacy fallback: only when no model/magic scope requested
  if mid is None and mag is None and ticket is None and not signal_id:
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


def _px_same(a, b, *, eps: float = 1e-6) -> bool:
  try:
    return abs(float(a) - float(b)) <= eps
  except (TypeError, ValueError):
    return a is None and b is None


def _is_manual_test_row(row: dict) -> bool:
  sid = str(row.get("signal_id") or "")
  origin = str(row.get("origin") or "").lower()
  flags = [str(x) for x in (row.get("interventions") or [])]
  if any(sid.startswith(p) for p in _MANUAL_OPEN_MARKERS):
    return True
  if origin in ("manual_test", "manual"):
    return True
  if "manual_test_open" in flags:
    return True
  return False


def _restore_false_user_sl_tp(row: dict) -> bool:
  """Undo EA false-positive user_sl_tp (multi-slot g_sync_sl clash / restart)."""
  if str(row.get("mode") or "").lower() != MODE_MANUAL:
    return False
  if _is_manual_test_row(row):
    return False
  flags = [str(x) for x in (row.get("interventions") or [])]
  origin = str(row.get("origin") or "").lower()
  reason = str(row.get("reason") or "").lower()
  if reason in _MANUAL_CLOSE_REASONS:
    return False
  if any(
    f in ("manual_test_open", "manual_close", "manual_test_close")
    or str(f).startswith("manual_test")
    for f in flags
  ):
    return False
  sl_ok = _px_same(row.get("sl"), row.get("sl_initial")) and _px_same(
    row.get("tp"), row.get("tp_initial")
  )
  status = str(row.get("status") or "").upper()
  if "user_sl_tp" in flags:
    if not sl_ok:
      return False
  elif "intervened" in flags and sl_ok:
    # Close inherited g_user_intervened from a no-op user_sl_tp fill.
    if status == "CLOSED" and reason and reason not in _AUTO_EXIT_REASONS:
      return False
  elif "orphan_close" in flags and origin in ("user_edit", "strategy", ""):
    pass
  else:
    return False
  row["mode"] = MODE_AUTO
  row["intervened"] = False
  if origin in ("user_edit", "manual"):
    row["origin"] = "strategy"
  row["interventions"] = [f for f in flags if f not in ("user_sl_tp", "intervened")]
  row["updated_at"] = _now()
  return True


def restore_false_manual_edits(bridge_dir: Path | None = None) -> int:
  """Reclassify strategy trades that EA tagged as user SL/TP by mistake."""
  trades = load_trades(bridge_dir)
  n = 0
  for t in trades:
    if _restore_false_user_sl_tp(t):
      n += 1
  if n:
    save_trades(trades, bridge_dir)
    append_event(
      "system",
      "false_manual_restored",
      bridge_dir=bridge_dir,
      summary=f"restored {n} auto trades mis-tagged as user_sl_tp",
      payload={"n": n},
    )
  return n


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
      "symbol": _row_symbol(fill, decision),
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
    sl_changed = fill.get("sl") is not None and not _px_same(fill.get("sl"), row.get("sl"))
    tp_changed = fill.get("tp") is not None and not _px_same(fill.get("tp"), row.get("tp"))
    if fill.get("sl") is not None:
      row["sl"] = float(fill["sl"])
    if fill.get("tp") is not None:
      row["tp"] = float(fill["tp"])
    if fill.get("lots") is not None:
      try:
        row["lots"] = float(fill["lots"])
      except (TypeError, ValueError):
        pass
    # EA trail sync keeps auto mode; user edit → manual.
    # No-op modify (same SL/TP) is a false user_sl_tp from multi-slot EA sync.
    user_edit = (
      detail_l in ("user_sl_tp",)
      or fill.get("manual") is True
      or str(fill.get("source") or "") == "user_edit"
    )
    if user_edit and (sl_changed or tp_changed):
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
      # Already finalized — no-op (prevents Live Health/Risk inflation)
      if row is not None and row.get("exit_px") is not None:
        return row
    if not row:
      is_manual, source = _infer_open_manual(fill, decision)
      row = {
        "id": f"bt_close_{ticket or _now()}",
        "signal_id": sid,
        "ticket": ticket,
        "symbol": _row_symbol(fill, decision),
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

    r, result = _align_r_with_profit(r, result, fill, row)

    close_reason = str(fill.get("reason") or fill.get("detail") or row.get("reason") or "")
    close_l = close_reason.lower()
    sl_now = fill.get("sl") if fill.get("sl") is not None else row.get("sl")
    tp_now = fill.get("tp") if fill.get("tp") is not None else row.get("tp")
    false_ea_manual = (
      not _is_manual_test_row(row)
      and close_l in _AUTO_EXIT_REASONS
      and _px_same(sl_now, row.get("sl_initial"))
      and _px_same(tp_now, row.get("tp_initial"))
      and (
        fill.get("manual") is True
        or str(fill.get("source") or "").lower() in ("user_edit", "manual")
        or trade_mode(row) == MODE_MANUAL
      )
    )
    if false_ea_manual:
      pass
    elif (
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


EA_FLAT_RECONCILE_MAX_AGE_SEC = 15.0
REDECIDE_REQUEST_NAME = "redecide_request.json"


def ea_heartbeat_age_sec(bridge_dir: Path | None = None) -> float | None:
  from mt5_bridge.protocol import connection_path

  try:
    return max(0.0, time.time() - connection_path(bridge_dir).stat().st_mtime)
  except OSError:
    return None


def ea_position_count(connection: dict | None) -> int | None:
  if not isinstance(connection, dict) or "positions" not in connection:
    return None
  try:
    return int(connection.get("positions"))
  except (TypeError, ValueError):
    return None


def ea_is_fresh_flat(
  connection: dict | None,
  heartbeat_age_sec: float | None,
  *,
  max_age_sec: float = EA_FLAT_RECONCILE_MAX_AGE_SEC,
) -> bool:
  if heartbeat_age_sec is None or heartbeat_age_sec > float(max_age_sec):
    return False
  return ea_position_count(connection) == 0


def request_live_redecide(bridge_dir: Path | None = None) -> None:
  """Ask the live worker to drop HOLD cache and decide the current bar again."""
  atomic_write_json(
    ensure_bridge_dir(bridge_dir) / REDECIDE_REQUEST_NAME,
    {"requested_at": time.time(), "reason": "hold_without_mt5"},
  )


def consume_live_redecide(bridge_dir: Path | None = None) -> bool:
  path = ensure_bridge_dir(bridge_dir) / REDECIDE_REQUEST_NAME
  if not path.exists():
    return False
  try:
    path.unlink()
  except OSError:
    return True
  return True


def reconcile_ghost_opens_if_ea_flat(
  bridge_dir: Path | None = None,
  *,
  connection: dict | None = None,
  require_fresh_heartbeat: bool = True,
  max_age_sec: float = EA_FLAT_RECONCILE_MAX_AGE_SEC,
) -> int:
  """Close journal OPEN rows when EA reports 0 positions.

  Auto poll uses ``reconcile_journal_from_ea_positions`` (deals.json first).
  Manual dashboard confirm (``require_fresh_heartbeat=False``) may still
  force-close ghosts when MT5 is verified flat.
  """
  out = reconcile_journal_from_ea_positions(
    bridge_dir,
    connection=connection,
    require_fresh_heartbeat=require_fresh_heartbeat,
    max_age_sec=max_age_sec,
  )
  n = int(out.get("closed_ghosts") or out.get("closed") or 0)
  if n > 0 or out.get("skipped"):
    return n
  if not require_fresh_heartbeat:
    from mt5_bridge.protocol import connection_path, read_json
    conn = connection if isinstance(connection, dict) else (read_json(connection_path(bridge_dir)) or {})
    if ea_position_count(conn) == 0 and count_open_trades(bridge_dir) > 0:
      return close_ghost_journal_opens(bridge_dir, reason="journal_desync")
  return 0


def read_ea_positions_snapshot(bridge_dir: Path | None = None) -> tuple[list[dict], int | None]:
  """Open MT5 positions written by EA (source of truth for Live sync)."""
  from mt5_bridge.protocol import positions_path, read_json

  data = read_json(positions_path(bridge_dir))
  if not isinstance(data, dict):
    return [], None
  rows = [p for p in (data.get("positions") or []) if isinstance(p, dict)]
  try:
    n = int(data.get("n", len(rows)))
  except (TypeError, ValueError):
    n = len(rows)
  return rows, n


def _mt5_ticket(p: dict) -> int | None:
  try:
    return int(p.get("ticket"))
  except (TypeError, ValueError):
    return None


def _mt5_magic(p: dict) -> int | None:
  try:
    return int(p.get("magic"))
  except (TypeError, ValueError):
    return None


def _apply_mt5_position_to_journal(row: dict, mt5p: dict) -> bool:
  """Update journal OPEN row from EA/MT5 snapshot. Returns True if fields changed."""
  changed = False
  ticket = _mt5_ticket(mt5p)
  if ticket is not None and row.get("ticket") != ticket:
    row["ticket"] = ticket
    changed = True
  magic = _mt5_magic(mt5p)
  if magic is not None and row.get("magic") != magic:
    row["magic"] = magic
    changed = True
  mid = str(mt5p.get("model_id") or "").strip()
  if mid and str(row.get("model_id") or "") != mid:
    row["model_id"] = mid
    changed = True
  typ = str(mt5p.get("type") or "").upper()
  if typ in ("BUY", "SELL") and str(row.get("direction") or "").upper() != typ:
    row["direction"] = typ
    changed = True
  for jkey, mkey in (
    ("entry_px", "price_open"),
    ("sl", "sl"),
    ("tp", "tp"),
    ("lots", "volume"),
  ):
    try:
      mv = float(mt5p.get(mkey))
    except (TypeError, ValueError):
      continue
    if not _px_same(row.get(jkey), mv):
      row[jkey] = mv
      changed = True
  if changed:
    row["updated_at"] = _now()
    flags = list(row.get("interventions") or [])
    if "ea_sync_update" not in flags:
      flags.append("ea_sync_update")
    row["interventions"] = flags
  return changed


def _import_mt5_position_row(mt5p: dict) -> dict:
  typ = str(mt5p.get("type") or "BUY").upper()
  ticket = _mt5_ticket(mt5p)
  sid = f"ea_sync_{ticket}" if ticket is not None else f"ea_sync_{_now()}"
  try:
    entry = float(mt5p.get("price_open"))
  except (TypeError, ValueError):
    entry = None
  try:
    sl = float(mt5p.get("sl"))
  except (TypeError, ValueError):
    sl = None
  try:
    tp = float(mt5p.get("tp"))
  except (TypeError, ValueError):
    tp = None
  return {
    "id": f"bt_{sid}",
    "signal_id": sid,
    "ticket": ticket,
    "symbol": _row_symbol(mt5p),
    "direction": typ,
    "status": "OPEN",
    "mode": MODE_AUTO,
    "origin": "ea_sync_import",
    "intervened": False,
    "interventions": ["ea_sync_import"],
    "entry_time": mt5p.get("time") or _now(),
    "entry_px": entry,
    "sl": sl,
    "tp": tp,
    "sl_initial": sl,
    "tp_initial": tp,
    "lots": float(mt5p["volume"]) if mt5p.get("volume") is not None else None,
    "exit_time": None,
    "exit_px": None,
    "profit": mt5p.get("profit"),
    "r": None,
    "result": None,
    "reason": None,
    "model_id": mt5p.get("model_id"),
    "magic": _mt5_magic(mt5p),
    "bar_time": None,
    "strategy_name": None,
    "updated_at": _now(),
  }


def sync_open_positions_from_ea(bridge_dir: Path | None = None) -> dict[str, Any]:
  """Update OPEN journal rows from MT5 snapshot + import orphan tickets."""
  summary: dict[str, Any] = {"updated": 0, "imported": 0}
  mt5_rows, _mt5_n = read_ea_positions_snapshot(bridge_dir)
  if not mt5_rows:
    return summary

  trades = load_trades(bridge_dir)
  by_ticket = {_mt5_ticket(p): p for p in mt5_rows if _mt5_ticket(p) is not None}
  by_magic = {_mt5_magic(p): p for p in mt5_rows if _mt5_magic(p) is not None}
  matched_tickets: set[int] = set()
  changed = False

  for row in trades:
    if str(row.get("status") or "").upper() != "OPEN":
      continue
    mt5p = None
    ticket = row.get("ticket")
    if ticket is not None:
      try:
        mt5p = by_ticket.get(int(ticket))
      except (TypeError, ValueError):
        mt5p = None
    if mt5p is None and row.get("magic") is not None:
      try:
        mt5p = by_magic.get(int(row.get("magic")))
      except (TypeError, ValueError):
        mt5p = None
    if mt5p is None:
      continue
    tix = _mt5_ticket(mt5p)
    if tix is not None:
      matched_tickets.add(tix)
    if _apply_mt5_position_to_journal(row, mt5p):
      summary["updated"] += 1
      changed = True

  open_tickets = {
    _mt5_ticket(t)
    for t in trades
    if str(t.get("status") or "").upper() == "OPEN" and _mt5_ticket(t) is not None
  }
  for mt5p in mt5_rows:
    tix = _mt5_ticket(mt5p)
    if tix is not None and tix in open_tickets:
      continue
    if tix is not None and tix in matched_tickets:
      continue
    trades.append(_import_mt5_position_row(mt5p))
    summary["imported"] += 1
    changed = True
    if tix is not None:
      open_tickets.add(tix)

  if changed:
    save_trades(trades, bridge_dir)
    if summary["imported"]:
      clear_sticky_fill_files(bridge_dir)
  return summary


def reconcile_journal_from_ea_positions(
  bridge_dir: Path | None = None,
  *,
  connection: dict | None = None,
  require_fresh_heartbeat: bool = True,
  max_age_sec: float = EA_FLAT_RECONCILE_MAX_AGE_SEC,
) -> dict[str, Any]:
  """Full EA↔journal sync: deals-based close + MT5 open-field sync + import."""
  from mt5_bridge.position_sync import reconcile_bridge_positions
  from mt5_bridge.protocol import connection_path, read_json

  conn = connection if isinstance(connection, dict) else (read_json(connection_path(bridge_dir)) or {})
  if require_fresh_heartbeat:
    age = ea_heartbeat_age_sec(bridge_dir)
    if age is None or age > float(max_age_sec):
      return {"skipped": True, "skip_reason": "stale_heartbeat", "closed_ghosts": 0}

  rec = reconcile_bridge_positions(bridge_dir, reason="ea_reconnect_reconcile")
  sync = sync_open_positions_from_ea(bridge_dir)
  return {
    "skipped": False,
    "closed_ghosts": int(rec.get("closed") or 0),
    "closed": int(rec.get("closed") or 0),
    "repaired": int(rec.get("repaired") or 0),
    "awaiting": int(rec.get("awaiting") or 0),
    "updated": int(sync.get("updated") or 0),
    "imported": int(sync.get("imported") or 0),
    "orphans": rec.get("orphans") or [],
    "ea_positions": rec.get("ea_positions"),
    "n_deals": rec.get("n_deals"),
    "connection_positions": ea_position_count(conn),
  }
