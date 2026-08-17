"""Reconcile Live journal against real MT5 positions + OUT deals.

EA writes ``positions.json`` (open tickets) and ``deals.json`` (History OUT deals).
App never invents BE/SL: a journal OPEN is only closed when an MT5 deal or
ticket-matched close fill exists.
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


def _deal_reason_tag(reason: int | None) -> str:
  # MQL5 ENUM_DEAL_REASON
  return {
    0: "manual_close",  # CLIENT
    1: "manual_close",  # MOBILE
    2: "manual_close",  # WEB
    3: "ea_close",
    4: "sl",
    5: "tp",
    6: "stop_out",
  }.get(int(reason or -1), "closed")


def load_mt5_close_deals(bridge_dir: Path) -> dict[int, dict[str, Any]]:
  """position ticket → OUT deal. Prefer EA deals.json (MT5 history), else terminal API."""
  bdir = Path(bridge_dir)
  out: dict[int, dict[str, Any]] = {}
  data = _read(bdir / "deals.json")
  if data is None:
    rows = _deals_from_terminal(bdir)
  elif isinstance(data, dict):
    rows = list(data.get("deals") or [])
  elif isinstance(data, list):
    rows = data
  else:
    rows = []
  for d in rows:
    if not isinstance(d, dict):
      continue
    try:
      pid = int(d.get("position_id") or d.get("ticket") or 0)
    except (TypeError, ValueError):
      pid = 0
    if pid and pid not in out:
      out[pid] = d
  return out


def _deals_from_terminal(bridge_dir: Path) -> list[dict[str, Any]]:
  """Optional fallback: MetaTrader5 Python API on the same Windows terminal."""
  conn = _read(Path(bridge_dir) / "connection.json") or {}
  symbol = str(conn.get("symbol") or "")
  magics = roster_magics(bridge_dir)
  try:
    import MetaTrader5 as mt5  # type: ignore
  except ImportError:
    return []
  try:
    if not mt5.initialize():
      return []
    from datetime import datetime, timedelta
    raw = mt5.history_deals_get(
      datetime.now() - timedelta(days=8),
      datetime.now() + timedelta(days=1),
    )
  except Exception:
    return []
  if raw is None:
    return []
  rows: list[dict[str, Any]] = []
  for d in raw:
    try:
      entry = int(getattr(d, "entry", -1))
      if entry not in (1, 2):  # DEAL_ENTRY_OUT, OUT_BY
        continue
      if symbol and str(getattr(d, "symbol", "")) != symbol:
        continue
      magic = int(getattr(d, "magic", 0) or 0)
      if magics and magic not in magics:
        continue
      pid = int(getattr(d, "position_id", 0) or 0)
      profit = (
        float(getattr(d, "profit", 0) or 0)
        + float(getattr(d, "swap", 0) or 0)
        + float(getattr(d, "commission", 0) or 0)
      )
      dtype = int(getattr(d, "type", 0) or 0)
      t = getattr(d, "time", None)
      time_s = ""
      if t:
        try:
          from datetime import datetime as _dt
          time_s = _dt.fromtimestamp(int(t)).strftime("%Y.%m.%d %H:%M:%S")
        except (OSError, TypeError, ValueError, OverflowError):
          time_s = str(t)
      rows.append({
        "deal": int(getattr(d, "ticket", 0) or 0),
        "position_id": pid,
        "ticket": pid,
        "magic": magic,
        "type": "SELL" if dtype == 1 else "BUY",
        "volume": float(getattr(d, "volume", 0) or 0),
        "price": float(getattr(d, "price", 0) or 0),
        "profit": round(profit, 2),
        "reason": _deal_reason_tag(getattr(d, "reason", None)),
        "time": time_s,
        "source": "mt5_terminal",
      })
    except (TypeError, ValueError, AttributeError):
      continue
  return rows


def _deal_as_fill(deal: dict[str, Any], trade: dict[str, Any]) -> dict[str, Any]:
  return {
    "event": "close",
    "ticket": deal.get("position_id") or deal.get("ticket") or trade.get("ticket"),
    "price": deal.get("price"),
    "profit": deal.get("profit"),
    "reason": deal.get("reason") or "closed",
    "detail": deal.get("reason") or "closed",
    "time": deal.get("time"),
    "sl": trade.get("sl") if trade.get("sl") is not None else trade.get("sl_initial"),
    "action": trade.get("direction") or deal.get("type"),
    "lots": deal.get("volume") if deal.get("volume") is not None else trade.get("lots"),
    "source": "mt5_deal",
  }


def _needs_deal_repair(trade: dict[str, Any], deal: dict[str, Any]) -> bool:
  st = str(trade.get("status") or "").upper()
  if st not in ("CLOSED", "CLOSING"):
    return False
  try:
    dp = float(deal.get("profit"))
  except (TypeError, ValueError):
    return False
  if trade.get("profit") is None:
    return True
  try:
    if abs(float(trade["profit"]) - dp) > 0.009:
      return True
  except (TypeError, ValueError):
    return True
  dpx = deal.get("price")
  tpx = trade.get("exit_px") if trade.get("exit_px") is not None else trade.get("exit")
  try:
    if dpx is not None and tpx is not None and abs(float(dpx) - float(tpx)) > 1e-6:
      return True
  except (TypeError, ValueError):
    return True
  if str(trade.get("result") or "").upper() in ("BE", "") and abs(dp) > 1e-9:
    return True
  return False


def _r_from_profit_money(trade: dict[str, Any], profit: float) -> float | None:
  try:
    lots = float(trade.get("lots") or 0)
    entry = trade.get("entry_px")
    if entry is None:
      entry = trade.get("entry")
    sl = trade.get("sl_initial")
    if sl is None:
      sl = trade.get("sl")
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


def _matching_close_fill(
  bridge_dir: Path,
  *,
  ticket: int = 0,
  signal_id: str | None = None,
) -> dict[str, Any] | None:
  """Prefer sticky fill.json close, then fills.jsonl close for this ticket.

  Match by ticket only. Signal-id fallback is unsafe with multi-model fills
  (EA used to stamp the last open's signal_id on other tickets).
  """
  bdir = Path(bridge_dir)
  candidates: list[dict[str, Any]] = []
  sticky = _read(bdir / "fill.json")
  if isinstance(sticky, dict):
    candidates.append(sticky)
  for name in ("ea_fills.jsonl", "fills.jsonl"):
    path = bdir / name
    if not path.is_file():
      continue
    try:
      lines = path.read_text(encoding="utf-8").splitlines()[-4000:]
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

  sid = str(signal_id or "")
  for fill in candidates:
    event = str(fill.get("event") or "").lower()
    if event not in ("close", "closed"):
      continue
    try:
      ft = int(fill.get("ticket") or 0)
    except (TypeError, ValueError):
      ft = 0
    if ticket and ft and ft == ticket:
      return fill
    if ticket and ft and ft != ticket:
      continue
    if (not ticket or not ft) and sid and str(fill.get("signal_id") or "") == sid:
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
  if r is not None and result in ("WIN", "LOSS") and fill.get("profit") is not None:
    try:
      p = float(fill["profit"])
    except (TypeError, ValueError):
      p = None
    if p is not None and ((p < -1e-9 and r > 0.05) or (p > 1e-9 and r < -0.05)):
      # Fill price was another ticket's deal / current Bid. Trust profit vs planned SL.
      aligned = _r_from_profit_money(trade, p)
      if aligned is not None:
        r = aligned
      elif p < 0:
        r = -1.0
      result = "WIN" if p > 0 else ("LOSS" if p < 0 else "BE")
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
  """Sync journal to real MT5 state.

  OPEN is closed only when an OUT deal (deals.json / terminal) or a
  ticket-matched close fill exists. Missing deal → leave OPEN (retry next poll).
  Already-CLOSED rows with no/wrong profit are repaired from the same deals.
  """
  bdir = Path(bridge_dir)
  trades_path = bdir / "trades.json"
  payload = _read(trades_path) or {}
  trades = list(payload.get("trades") or [])
  if not trades:
    return {"ok": True, "closed": 0, "repaired": 0, "orphans": [], "bridge_dir": str(bdir)}

  snap = load_ea_positions(bdir)
  tickets, ea_magics = ea_position_keys(snap)
  has_snap = isinstance(snap, dict) and not snap.get("_stale") and "positions" in snap
  conn_n = connection_position_count(bdir)
  book_magics = roster_magics(bdir)
  deals = load_mt5_close_deals(bdir)

  closed = 0
  repaired = 0
  awaiting = 0
  now = _now()
  dirty = False
  for t in trades:
    try:
      ticket = int(t.get("ticket") or 0)
    except (TypeError, ValueError):
      ticket = 0
    try:
      magic = int(t.get("magic") or 0)
    except (TypeError, ValueError):
      magic = 0
    deal = deals.get(ticket) if ticket else None
    st = str(t.get("status") or "").upper()

    if st == "CLOSED" and deal and _needs_deal_repair(t, deal):
      _apply_close_from_fill(t, _deal_as_fill(deal, t), now=now)
      interventions = list(t.get("interventions") or [])
      if "mt5_deal" not in interventions:
        interventions.append("mt5_deal")
      t["interventions"] = [x for x in interventions if x != "sl_assumed"]
      repaired += 1
      dirty = True
      continue

    if st != "OPEN":
      continue

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

    fill = None
    source = None
    if deal:
      fill = _deal_as_fill(deal, t)
      source = "mt5_deal"
    else:
      fill = _matching_close_fill(
        bdir, ticket=ticket, signal_id=str(t.get("signal_id") or "") or None,
      )
      if fill:
        source = "fill_recovered"

    interventions = list(t.get("interventions") or [])
    if not fill:
      # Position gone on MT5 but History has no OUT deal yet — do not invent R.
      if "awaiting_mt5_deal" not in interventions:
        interventions.append("awaiting_mt5_deal")
        t["interventions"] = interventions
        dirty = True
      awaiting += 1
      continue

    _apply_close_from_fill(t, fill, now=now)
    if source and source not in interventions:
      interventions.append(source)
    if detail not in interventions:
      interventions.append(detail)
    t["interventions"] = interventions
    closed += 1
    dirty = True

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

  if dirty:
    _write(trades_path, {"updated_at": now, "trades": trades})

  result = {
    "ok": True,
    "closed": closed,
    "repaired": repaired,
    "awaiting": awaiting,
    "orphans": orphans,
    "bridge_dir": str(bdir),
    "ea_positions": len(tickets) if has_snap else conn_n,
    "has_snapshot": has_snap,
    "n_deals": len(deals),
    "reason": reason,
  }
  if closed or repaired or awaiting or orphans:
    print(
      f"[position_sync] {bdir.name}: closed={closed} repaired={repaired} "
      f"awaiting={awaiting} orphans={len(orphans)} deals={len(deals)} "
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
