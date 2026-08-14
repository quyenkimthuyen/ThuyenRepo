"""Read Live trade journal / fills from bridge_live."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from live_config import BRIDGE_DIR

# User-facing period keys
PERIODS = ("today", "week", "month", "all")
PERIOD_LABELS = {
  "today": "Today",
  "week": "This week",
  "month": "This month",
  "all": "All time",
}


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def load_trades(bridge_dir: Path | None = None) -> list[dict]:
  bdir = Path(bridge_dir or BRIDGE_DIR)
  data = _read(bdir / "trades.json")
  if isinstance(data, dict):
    return list(data.get("trades") or [])
  if isinstance(data, list):
    return data
  return []


def load_recent_fills(bridge_dir: Path | None = None, limit: int = 50) -> list[dict]:
  bdir = Path(bridge_dir or BRIDGE_DIR)
  rows: list[dict] = []
  for name in ("fills.jsonl", "ea_fills.jsonl"):
    path = bdir / name
    if not path.exists():
      continue
    with open(path, encoding="utf-8") as f:
      for line in f:
        line = line.strip()
        if not line:
          continue
        try:
          rows.append(json.loads(line))
        except json.JSONDecodeError:
          continue
  return rows[-limit:]


def load_trades_many(bridge_dirs: list[Path]) -> list[dict]:
  """Merge trades.json from several bridge dirs (dedupe by signal/ticket)."""
  out: list[dict] = []
  seen: set[tuple] = set()
  for bdir in bridge_dirs:
    for t in load_trades(bdir):
      key = (
        t.get("signal_id"),
        t.get("ticket"),
        t.get("model_id"),
        t.get("exit_time") or t.get("closed_at") or t.get("entry_time"),
      )
      if key in seen:
        continue
      seen.add(key)
      out.append({**t, "_bridge": str(bdir)})
  return out


def journal_summary_many(
  bridge_dirs: list[Path],
  *,
  period: str = "all",
) -> dict[str, Any]:
  trades = filter_trades_by_period(load_trades_many(bridge_dirs), period)
  closed = [t for t in trades if _is_closed(t)]
  r_vals = [r for t in closed if (r := _trade_r(t)) is not None]
  wins = sum(1 for t in closed if _trade_result(t) == "WIN")
  losses = sum(1 for t in closed if _trade_result(t) == "LOSS")
  fills = 0
  for b in bridge_dirs:
    fills += len(load_recent_fills(b, limit=5000))
  return {
    "period": period,
    "period_label": PERIOD_LABELS.get(period, period),
    "n_trades": len(trades),
    "n_closed": len(closed),
    "total_r": round(sum(r_vals), 3) if r_vals else 0.0,
    "wins": wins,
    "losses": losses,
    "win_rate_pct": round(100.0 * wins / len(closed), 1) if closed else None,
    "recent_fills": fills,
  }


def stats_by_model_many(
  bridge_dirs: list[Path],
  *,
  period: str = "all",
) -> list[dict[str, Any]]:
  all_trades = load_trades_many(bridge_dirs)
  trades = filter_trades_by_period(all_trades, period)
  labels = _label_map()
  markets: dict[str, tuple[str, str]] = {}
  groups: dict[str, list[dict]] = {}
  for t in trades:
    groups.setdefault(_model_key(t), []).append(t)
  try:
    from package_store import default_roster_from_installed, load_roster
    for row in (load_roster().get("models") or default_roster_from_installed()):
      mid = row.get("model_id")
      if mid:
        mid_s = str(mid)
        groups.setdefault(mid_s, [])
        if row.get("label"):
          labels[mid_s] = str(row["label"])
        markets[mid_s] = (
          str(row.get("symbol") or ""),
          str(row.get("timeframe") or ""),
        )
  except Exception:
    pass
  rows = []
  for mid, group in groups.items():
    s = _summarize_group(group)
    sym, tf = markets.get(mid, ("", ""))
    if not sym and group:
      sym = str(group[0].get("symbol") or "")
      tf = str(group[0].get("timeframe") or group[0].get("period") or "")
    rows.append({
      "model_id": mid,
      "label": labels.get(mid) or mid,
      "symbol": sym or None,
      "timeframe": tf or None,
      "period": period,
      "period_label": PERIOD_LABELS.get(period, period),
      **s,
    })
  rows.sort(key=lambda r: (-int(r.get("n_closed") or 0), -float(r.get("total_r") or 0)))
  return rows


def _is_closed(t: dict) -> bool:
  st = str(t.get("status") or "").upper()
  if st == "CLOSED":
    return True
  if st == "OPEN":
    return False
  if t.get("exit") is not None or t.get("exit_price") is not None or t.get("exit_time"):
    return True
  return str(t.get("status") or "").lower() == "closed"


def _is_open(t: dict) -> bool:
  if _is_closed(t):
    return False
  st = str(t.get("status") or "").upper()
  return st in ("", "OPEN") or t.get("exit") is None


def _parse_ts(raw: Any) -> datetime | None:
  """Parse journal/EA timestamps. Naive MT5 wall times stay local (not UTC)."""
  if not raw:
    return None
  if isinstance(raw, datetime):
    if raw.tzinfo:
      return raw
    return raw.replace(tzinfo=_now_local().tzinfo) if _now_local().tzinfo else raw
  s = str(raw).strip()
  if not s:
    return None
  try:
    if s.endswith("Z"):
      s = s[:-1] + "+00:00"
    # EA TimeToString: "YYYY.MM.DD HH:MM" or "YYYY.MM.DD HH:MM:SS"
    if len(s) >= 10 and s[4] == "." and s[7] == ".":
      s = s.replace(".", "-", 2)
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
      local_tz = _now_local().tzinfo
      if local_tz is not None:
        dt = dt.replace(tzinfo=local_tz)
    return dt
  except ValueError:
    return None


def _trade_r(t: dict) -> float | None:
  try:
    if t.get("r") is not None:
      return float(t["r"])
  except (TypeError, ValueError):
    pass
  return None


def _trade_result(t: dict) -> str | None:
  res = t.get("result")
  if res:
    return str(res).upper()
  r = _trade_r(t)
  if r is None:
    return None
  if r > 1e-9:
    return "WIN"
  if r < -1e-9:
    return "LOSS"
  return "BE"


def _model_key(t: dict) -> str:
  mid = t.get("model_id") or t.get("id")
  if mid:
    return str(mid)
  mag = t.get("magic")
  if mag is not None:
    return f"magic:{mag}"
  return "(unknown)"


def _label_map() -> dict[str, str]:
  out: dict[str, str] = {}
  try:
    from package_store import list_installed, load_roster
    for row in (load_roster().get("models") or []):
      mid = row.get("model_id")
      if mid:
        out[str(mid)] = str(row.get("label") or mid)
    for row in list_installed():
      mid = row.get("model_id")
      if mid and str(mid) not in out:
        out[str(mid)] = str(row.get("label") or mid)
  except Exception:
    pass
  return out


def _now_local() -> datetime:
  return datetime.now().astimezone()


def period_bounds(period: str | None) -> tuple[datetime | None, datetime | None]:
  """Inclusive start (local), exclusive end (None = open-ended)."""
  p = (period or "all").lower().strip()
  now = _now_local()
  if p in ("today", "day"):
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, None
  if p in ("week", "this_week"):
    # Monday 00:00 local
    start = (now - timedelta(days=now.weekday())).replace(
      hour=0, minute=0, second=0, microsecond=0,
    )
    return start, None
  if p in ("month", "this_month"):
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, None
  return None, None  # all


def _trade_close_ts(t: dict) -> datetime | None:
  return _parse_ts(
    t.get("exit_time") or t.get("closed_at") or t.get("updated_at") or t.get("ts")
  )


def _in_period(ts: datetime | None, start: datetime | None, end: datetime | None) -> bool:
  if start is None and end is None:
    return True
  if ts is None:
    return False
  if ts.tzinfo is None:
    local_tz = _now_local().tzinfo
    ts = ts.replace(tzinfo=local_tz) if local_tz else ts
  else:
    ts = ts.astimezone()
  if start is not None and ts < start:
    return False
  if end is not None and ts >= end:
    return False
  return True


def filter_trades_by_period(
  trades: list[dict],
  period: str | None = "all",
  *,
  closed_only: bool = False,
) -> list[dict]:
  start, end = period_bounds(period)
  out = []
  for t in trades:
    if closed_only and not _is_closed(t):
      continue
    if _is_open(t) and (period or "all") != "all":
      # Open positions only count in "all" snapshot; period views = closed in window
      continue
    if _is_closed(t):
      if not _in_period(_trade_close_ts(t), start, end):
        continue
    elif start is not None or end is not None:
      continue
    out.append(t)
  return out


def _summarize_group(trades: list[dict]) -> dict[str, Any]:
  closed = [t for t in trades if _is_closed(t)]
  opens = [t for t in trades if _is_open(t)]
  rs: list[float] = []
  wins = losses = bes = 0
  for t in closed:
    r = _trade_r(t)
    result = _trade_result(t)
    if result == "WIN":
      wins += 1
    elif result == "LOSS":
      losses += 1
    elif result == "BE":
      bes += 1
    if r is not None:
      rs.append(r)
  n_closed = len(closed)
  return {
    "n_trades": len(trades),
    "n_closed": n_closed,
    "n_open": len(opens),
    "wins": wins,
    "losses": losses,
    "be": bes,
    "total_r": round(sum(rs), 3) if rs else 0.0,
    "avg_r": round(sum(rs) / len(rs), 3) if rs else None,
    "win_rate_pct": round(100.0 * wins / n_closed, 1) if n_closed else None,
  }


def journal_summary(
  bridge_dir: Path | None = None,
  *,
  period: str = "all",
) -> dict[str, Any]:
  trades = filter_trades_by_period(load_trades(bridge_dir), period)
  closed = [t for t in trades if _is_closed(t)]
  r_vals = [r for t in closed if (r := _trade_r(t)) is not None]
  wins = sum(1 for t in closed if _trade_result(t) == "WIN")
  losses = sum(1 for t in closed if _trade_result(t) == "LOSS")
  return {
    "period": period,
    "period_label": PERIOD_LABELS.get(period, period),
    "n_trades": len(trades),
    "n_closed": len(closed),
    "total_r": round(sum(r_vals), 3) if r_vals else 0.0,
    "wins": wins,
    "losses": losses,
    "win_rate_pct": round(100.0 * wins / len(closed), 1) if closed else None,
    "recent_fills": len(load_recent_fills(bridge_dir, limit=500)),
  }


def stats_by_model(
  bridge_dir: Path | None = None,
  *,
  period: str = "all",
  include_roster: bool = True,
) -> list[dict[str, Any]]:
  """Per-model summary for a period (today / week / month / all)."""
  all_trades = load_trades(bridge_dir)
  trades = filter_trades_by_period(all_trades, period)
  labels = _label_map()

  groups: dict[str, list[dict]] = {}
  for t in trades:
    groups.setdefault(_model_key(t), []).append(t)

  if include_roster:
    try:
      from package_store import default_roster_from_installed, load_roster
      roster = load_roster().get("models") or default_roster_from_installed()
      for row in roster:
        mid = row.get("model_id")
        if mid:
          groups.setdefault(str(mid), [])
          if row.get("label"):
            labels[str(mid)] = str(row["label"])
    except Exception:
      pass

  # For period views, still show open count from live book (all-time open)
  opens_by_model: dict[str, int] = {}
  if period != "all":
    for t in all_trades:
      if _is_open(t):
        mid = _model_key(t)
        opens_by_model[mid] = opens_by_model.get(mid, 0) + 1

  rows: list[dict[str, Any]] = []
  for mid, group in groups.items():
    s = _summarize_group(group)
    if period != "all":
      s["n_open"] = opens_by_model.get(mid, 0)
    rows.append({
      "model_id": mid,
      "label": labels.get(mid) or mid,
      "period": period,
      "period_label": PERIOD_LABELS.get(period, period),
      **s,
    })

  rows.sort(
    key=lambda r: (-int(r.get("n_closed") or 0), -float(r.get("total_r") or 0), str(r.get("label")))
  )
  return rows


def stats_by_model_table(
  bridge_dir: Path | None = None,
  *,
  period: str = "all",
  compact: bool = False,
) -> list[dict[str, Any]]:
  """UI dataframe rows. compact=True for desk strip."""
  out = []
  for r in stats_by_model(bridge_dir, period=period):
    if compact:
      out.append({
        "Model": r.get("label"),
        "Closed": r.get("n_closed"),
        "W/L": f"{r.get('wins')}/{r.get('losses')}",
        "WR%": r.get("win_rate_pct"),
        "R": r.get("total_r"),
        "Avg R": r.get("avg_r"),
        "Open": r.get("n_open"),
      })
    else:
      out.append({
        "Model": r.get("label"),
        "Period": r.get("period_label"),
        "Open": r.get("n_open"),
        "Closed": r.get("n_closed"),
        "W": r.get("wins"),
        "L": r.get("losses"),
        "WR%": r.get("win_rate_pct"),
        "Total R": r.get("total_r"),
        "Avg R": r.get("avg_r"),
      })
  return out
