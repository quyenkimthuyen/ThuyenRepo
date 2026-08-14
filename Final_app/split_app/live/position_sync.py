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
    interventions = list(t.get("interventions") or [])
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
