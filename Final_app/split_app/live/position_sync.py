"""Reconcile Live journal OPEN rows against EA MT5 positions snapshot.

EA writes ``positions.json`` (per-ticket). App closes ghost OPEN rows when the
ticket/magic is gone from MT5 — especially after EA/app restart or magic remap.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def _write(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + f".tmp.{time.time_ns()}")
  tmp.write_text(
    json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n",
    encoding="utf-8",
  )
  tmp.replace(path)


def load_ea_positions(bridge_dir: Path) -> dict[str, Any] | None:
  """Return parsed positions.json or None if missing/stale/unreadable."""
  path = Path(bridge_dir) / "positions.json"
  data = _read(path)
  if not isinstance(data, dict):
    return None
  try:
    age = time.time() - path.stat().st_mtime
  except OSError:
    return None
  # Heartbeat should refresh often; allow up to 3 minutes for quiet markets.
  if age > 180:
    data = dict(data)
    data["_stale"] = True
    data["_age_sec"] = age
  return data


def roster_magics(bridge_dir: Path) -> set[int]:
  models = _read(Path(bridge_dir) / "models.json") or {}
  out: set[int] = set()
  for m in models.get("models") or []:
    try:
      out.add(int(m.get("magic")))
    except (TypeError, ValueError):
      pass
  return out


def ea_position_keys(snapshot: dict[str, Any] | None) -> tuple[set[int], set[int]]:
  """Return (tickets, magics) currently open on EA."""
  tickets: set[int] = set()
  magics: set[int] = set()
  if not isinstance(snapshot, dict):
    return tickets, magics
  for p in snapshot.get("positions") or []:
    if not isinstance(p, dict):
      continue
    try:
      tickets.add(int(p.get("ticket")))
    except (TypeError, ValueError):
      pass
    try:
      magics.add(int(p.get("magic")))
    except (TypeError, ValueError):
      pass
  return tickets, magics


def connection_position_count(bridge_dir: Path) -> int | None:
  conn = _read(Path(bridge_dir) / "connection.json") or {}
  if not isinstance(conn, dict) or "positions" not in conn:
    return None
  try:
    return int(conn.get("positions"))
  except (TypeError, ValueError):
    return None


def _risk_dist(entry: float, sl: float) -> float | None:
  try:
    d = abs(float(entry) - float(sl))
  except (TypeError, ValueError):
    return None
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


def _matching_close_fill(
  bridge_dir: Path,
  *,
  ticket: int = 0,
  signal_id: str | None = None,
) -> dict[str, Any] | None:
  """Prefer sticky fill.json close, then recent fills.jsonl close for this ticket."""
  bdir = Path(bridge_dir)
  candidates: list[dict[str, Any]] = []
  sticky = _read(bdir / "fill.json")
  if isinstance(sticky, dict):
    candidates.append(sticky)
  for name in ("fills.jsonl", "ea_fills.jsonl"):
    path = bdir / name
    if not path.is_file():
      continue
    try:
      lines = path.read_text(encoding="utf-8").splitlines()[-80:]
    except OSError:
      continue
    for line in reversed(lines):
      line = line.strip()
      if not line:
        continue
      try:
        row = json.loads(line)
      except json.JSONDecodeError:
        continue
      if isinstance(row, dict):
        candidates.append(row)

  for fill in candidates:
    event = str(fill.get("event") or "").lower()
    detail = str(fill.get("detail") or fill.get("reason") or "").lower()
    is_close = event == "close" or detail in (
      "closed", "close", "sl", "tp", "max_hold", "manual",
      "manual_close", "ea_close", "stop_out", "trail", "end_range",
    )
    if not is_close:
      continue
    try:
      ft = int(fill.get("ticket") or 0)
    except (TypeError, ValueError):
      ft = 0
    if ticket and ft and ft == ticket:
      return fill
    if signal_id and fill.get("signal_id") == signal_id:
      return fill
  return None


def _apply_close_from_fill(trade: dict[str, Any], fill: dict[str, Any], *, now: str) -> None:
  exit_px = fill.get("price") or fill.get("exit_px") or fill.get("close_price")
  entry = trade.get("entry_px")
  if entry is None:
    entry = fill.get("entry") or fill.get("entry_px")
  sl_for_r = trade.get("sl_initial")
  if sl_for_r is None:
    sl_for_r = trade.get("sl") if trade.get("sl") is not None else fill.get("sl")
  direction = trade.get("direction") or fill.get("action")
  r = None
  if entry is not None and exit_px is not None and sl_for_r is not None:
    r = _compute_r(str(direction), float(entry), float(exit_px), float(sl_for_r))
  result = None
  if r is not None:
    if r > 0.05:
      result = "WIN"
    elif r < -0.05:
      result = "LOSS"
    else:
      result = "BE"
  elif fill.get("profit") is not None:
    try:
      p = float(fill["profit"])
      result = "WIN" if p > 0 else ("LOSS" if p < 0 else "BE")
    except (TypeError, ValueError):
      result = None

  trade["status"] = "CLOSED"
  # Prefer existing wall-clock exit (reconcile/ISO) over broker-minute fill.time
  # so period filters (Today / This week) stay correct.
  if not trade.get("exit_time"):
    trade["exit_time"] = fill.get("time") or fill.get("bar_time") or now
  elif fill.get("bar_time") and "T" not in str(trade.get("exit_time")):
    trade["exit_time"] = fill.get("bar_time") or fill.get("time") or trade.get("exit_time")
  if exit_px is not None:
    try:
      trade["exit_px"] = float(exit_px)
    except (TypeError, ValueError):
      trade["exit_px"] = trade.get("exit_px") or trade.get("entry_px")
  elif trade.get("exit_px") is None:
    trade["exit_px"] = trade.get("entry_px")
  if fill.get("profit") is not None:
    try:
      trade["profit"] = float(fill["profit"])
    except (TypeError, ValueError):
      pass
  if r is not None:
    trade["r"] = r
  elif trade.get("r") is None:
    trade["r"] = 0.0
  if result:
    trade["result"] = result
  elif trade.get("result") is None:
    trade["result"] = "BE"
  trade["reason"] = str(fill.get("reason") or fill.get("detail") or trade.get("reason") or "ea_close")
  trade["updated_at"] = now


def reconcile_bridge_positions(
  bridge_dir: Path | str,
  *,
  reason: str = "ea_reconnect_reconcile",
) -> dict[str, Any]:
  """Close journal OPEN ghosts that are not on EA; report orphans.

  Rules:
  1. If positions.json present and fresh: close OPEN whose ticket not in snapshot
     (and magic not in snapshot either as soft match).
  2. Else if connection.positions == 0: close all OPEN (flat on MT5).
  3. Always close OPEN whose magic is not in this book's models.json roster
     (stale after magic remap / Rebuild roster).
  Prefer matching EA close fill (fill.json / fills.jsonl) over inventing BE @ entry.
  """
  bdir = Path(bridge_dir)
  trades_path = bdir / "trades.json"
  payload = _read(trades_path) or {}
  trades = list(payload.get("trades") or [])
  if not trades:
    return {"ok": True, "closed": 0, "orphans": [], "bridge_dir": str(bdir)}

  snap = load_ea_positions(bdir)
  tickets, ea_magics = ea_position_keys(snap)
  has_snap = isinstance(snap, dict) and not snap.get("_stale") and "positions" in snap
  conn_n = connection_position_count(bdir)
  book_magics = roster_magics(bdir)

  closed = 0
  now = _now()
  for t in trades:
    if str(t.get("status") or "").upper() != "OPEN":
      continue
    try:
      ticket = int(t.get("ticket") or 0)
    except (TypeError, ValueError):
      ticket = 0
    try:
      magic = int(t.get("magic") or 0)
    except (TypeError, ValueError):
      magic = 0

    ghost = False
    detail = reason

    if book_magics and magic and magic not in book_magics:
      ghost = True
      detail = "magic_not_in_roster"
    elif has_snap:
      if ticket and ticket not in tickets:
        ghost = True
        detail = reason
      elif not ticket and magic and magic not in ea_magics:
        ghost = True
        detail = reason
    elif conn_n == 0:
      ghost = True
      detail = "mt5_flat"

    if not ghost:
      continue

    fill = _matching_close_fill(
      bdir, ticket=ticket, signal_id=str(t.get("signal_id") or "") or None,
    )
    interventions = list(t.get("interventions") or [])
    if fill:
      _apply_close_from_fill(t, fill, now=now)
      if "fill_recovered" not in interventions:
        interventions.append("fill_recovered")
    else:
      t["status"] = "CLOSED"
      t["exit_time"] = t.get("exit_time") or now
      if t.get("exit_px") is None:
        t["exit_px"] = t.get("entry_px")
      t["reason"] = detail
      if t.get("result") is None:
        t["result"] = "BE"
      if t.get("r") is None:
        t["r"] = 0.0
      t["updated_at"] = now
      if "journal_desync" not in interventions:
        interventions.append("journal_desync")
    if detail not in interventions:
      interventions.append(detail)
    t["interventions"] = interventions
    closed += 1

  orphans: list[dict[str, Any]] = []
  if has_snap:
    journal_tickets = set()
    for t in trades:
      if str(t.get("status") or "").upper() != "OPEN":
        continue
      try:
        journal_tickets.add(int(t.get("ticket") or 0))
      except (TypeError, ValueError):
        pass
    for p in snap.get("positions") or []:
      if not isinstance(p, dict):
        continue
      try:
        tk = int(p.get("ticket") or 0)
      except (TypeError, ValueError):
        continue
      if tk and tk not in journal_tickets:
        orphans.append(p)

  if closed:
    _write(trades_path, {"updated_at": now, "trades": trades})

  result = {
    "ok": True,
    "closed": closed,
    "orphans": orphans,
    "bridge_dir": str(bdir),
    "ea_positions": len(tickets) if has_snap else conn_n,
    "has_snapshot": has_snap,
    "reason": reason,
  }
  if closed or orphans:
    print(
      f"[position_sync] {bdir.name}: closed={closed} orphans={len(orphans)} "
      f"ea_pos={result['ea_positions']} snap={has_snap}",
      flush=True,
    )
  return result


def reconcile_all_live_bridges(*, sim: bool = False) -> dict[str, Any]:
  from books import bridge_dir, group_models_by_book
  from package_store import load_roster

  roster = load_roster()
  enabled = [r for r in (roster.get("models") or []) if r.get("enabled")]
  results = []
  total_closed = 0
  for (sym, tf), _rows in group_models_by_book(enabled).items():
    bdir = bridge_dir(sym, tf, sim=sim)
    r = reconcile_bridge_positions(bdir)
    results.append(r)
    total_closed += int(r.get("closed") or 0)
  return {"ok": True, "closed": total_closed, "books": results}
