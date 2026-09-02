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
  "today": "D",
  "week": "W",
  "month": "M",
  "all": "ALL",
}
PERIOD_TITLES = {
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
  now: datetime | None = None,
) -> dict[str, Any]:
  trades = filter_trades_by_period(load_trades_many(bridge_dirs), period, now=now)
  closed = [t for t in trades if _is_closed(t)]
  r_vals = [r for t in closed if (r := _trade_r(t)) is not None]
  wins = sum(1 for t in closed if _trade_result(t) == "WIN")
  losses = sum(1 for t in closed if _trade_result(t) == "LOSS")
  bes = sum(1 for t in closed if _trade_result(t) == "BE")
  decided = wins + losses
  fills = 0
  for b in bridge_dirs:
    fills += len(load_recent_fills(b, limit=5000))
  return {
    "period": period,
    "period_label": PERIOD_TITLES.get(period, PERIOD_LABELS.get(period, period)),
    "n_trades": len(trades),
    "n_closed": len(closed),
    "total_r": round(sum(r_vals), 3) if r_vals else 0.0,
    "wins": wins,
    "losses": losses,
    "be": bes,
    "win_rate_pct": round(100.0 * wins / decided, 1) if decided else None,
    "recent_fills": fills,
  }


def stats_by_model_many(
  bridge_dirs: list[Path],
  *,
  period: str = "all",
  now: datetime | None = None,
) -> list[dict[str, Any]]:
  all_trades = load_trades_many(bridge_dirs)
  trades = filter_trades_by_period(all_trades, period, now=now)
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
      "period_label": PERIOD_TITLES.get(period, PERIOD_LABELS.get(period, period)),
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


_FX_CONTRACT = 100000.0


def _num(val: Any) -> float | None:
  if val is None or val == "":
    return None
  try:
    return float(val)
  except (TypeError, ValueError):
    return None


def _entry_px(t: dict) -> float | None:
  if t.get("entry_px") is not None:
    return _num(t.get("entry_px"))
  return _num(t.get("entry"))


def _exit_px(t: dict) -> float | None:
  if t.get("exit_px") is not None:
    return _num(t.get("exit_px"))
  return _num(t.get("exit"))


def _sl_px(t: dict) -> float | None:
  if t.get("sl_initial") is not None:
    return _num(t.get("sl_initial"))
  return _num(t.get("sl"))


def _signs_disagree(a: float | None, b: float | None) -> bool:
  if a is None or b is None:
    return False
  return (a > 1e-9 and b < -1e-9) or (a < -1e-9 and b > 1e-9)


def _r_from_prices(t: dict) -> float | None:
  entry = _entry_px(t)
  exit_px = _exit_px(t)
  sl = _sl_px(t)
  if entry is None or exit_px is None or sl is None:
    return None
  risk = abs(entry - sl)
  if risk <= 0:
    return None
  d = str(t.get("direction") or t.get("action") or "").upper()
  if d in ("BUY", "LONG"):
    return round((exit_px - entry) / risk, 3)
  if d in ("SELL", "SHORT"):
    return round((entry - exit_px) / risk, 3)
  return None


def _r_from_profit(t: dict, profit: float | None = None) -> float | None:
  p = _num(profit if profit is not None else t.get("profit"))
  lots = _num(t.get("lots"))
  entry = _entry_px(t)
  sl = _sl_px(t)
  if p is None or lots is None or lots <= 0 or entry is None or sl is None:
    return None
  risk_px = abs(entry - sl)
  if risk_px <= 0:
    return None
  risk_money = lots * _FX_CONTRACT * risk_px
  if risk_money <= 0:
    return None
  return round(p / risk_money, 3)


def _profit_looks_like_r(t: dict, profit: float | None, stored: float | None) -> bool:
  """HistoryFeed paper fills write R-multiple into ``profit`` (e.g. -1.0), not USD."""
  if profit is None:
    return False
  if stored is not None and abs(profit - stored) <= 0.051:
    return True
  lots = _num(t.get("lots"))
  if lots is not None and lots > 0.02 and abs(profit) < 2.5:
    return True
  return False


def _trade_r(t: dict) -> float | None:
  stored: float | None = None
  try:
    if t.get("r") is not None:
      stored = float(t["r"])
  except (TypeError, ValueError):
    stored = None
  profit = _num(t.get("profit"))
  if _profit_looks_like_r(t, profit, stored):
    if stored is not None:
      return stored
    price_r = _r_from_prices(t)
    if price_r is not None:
      return price_r
    return round(profit, 3) if profit is not None else None
  price_r = _r_from_prices(t)
  rp = _r_from_profit(t, profit)
  if _signs_disagree(stored, profit) or _signs_disagree(price_r, profit):
    if rp is not None:
      return rp
    if profit is not None and profit < -1e-9 and str(t.get("reason") or "").lower() == "sl":
      return -1.0
  reason_l = str(t.get("reason") or "").lower()
  if (
    rp is not None
    and stored is not None
    and abs(rp - stored) > 0.3
    and reason_l in ("sl", "tp", "stop_out")
  ):
    # Same-sign but fill price was another deal; broker profit vs planned SL is fairer.
    return rp
  return stored


def _trade_result(t: dict) -> str | None:
  profit = _num(t.get("profit"))
  r = _trade_r(t)
  if profit is not None:
    if profit > 1e-9:
      return "WIN"
    if profit < -1e-9:
      return "LOSS"
  if r is not None:
    if r > 1e-9:
      return "WIN"
    if r < -1e-9:
      return "LOSS"
    return "BE"
  res = t.get("result")
  if res:
    return str(res).upper()
  return None


def wl_text(wins: Any, losses: Any, be: Any = 0) -> str:
  s = f"{int(wins or 0)}/{int(losses or 0)}"
  n_be = int(be or 0)
  if n_be:
    s += f" · {n_be} BE"
  return s


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


_STATS_ASOF: datetime | None = None


def set_stats_asof(now: datetime | None) -> None:
  """Replay cursor for D/W/M. ``None`` = wall clock."""
  global _STATS_ASOF
  _STATS_ASOF = now


def _as_local(dt: datetime) -> datetime:
  if dt.tzinfo is None:
    tz = _now_local().tzinfo
    return dt.replace(tzinfo=tz) if tz is not None else dt
  return dt.astimezone()


def _effective_now(now: datetime | None = None) -> datetime:
  if now is not None:
    return _as_local(now)
  if _STATS_ASOF is not None:
    return _as_local(_STATS_ASOF)
  return _now_local()


def period_bounds(
  period: str | None,
  *,
  now: datetime | None = None,
) -> tuple[datetime | None, datetime | None]:
  """Inclusive start, exclusive end (local). ``now`` = Replay as-of or wall clock."""
  p = (period or "all").lower().strip()
  ts = _effective_now(now)
  if p in ("today", "day"):
    start = ts.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)
  if p in ("week", "this_week"):
    start = (ts - timedelta(days=ts.weekday())).replace(
      hour=0, minute=0, second=0, microsecond=0,
    )
    return start, start + timedelta(days=7)
  if p in ("month", "this_month"):
    start = ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
      end = start.replace(year=start.year + 1, month=1)
    else:
      end = start.replace(month=start.month + 1)
    return start, end
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
  now: datetime | None = None,
) -> list[dict]:
  start, end = period_bounds(period, now=now)
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
  decided = wins + losses
  return {
    "n_trades": len(trades),
    "n_closed": n_closed,
    "n_open": len(opens),
    "wins": wins,
    "losses": losses,
    "be": bes,
    "total_r": round(sum(rs), 3) if rs else 0.0,
    "avg_r": round(sum(rs) / len(rs), 3) if rs else None,
    "win_rate_pct": round(100.0 * wins / decided, 1) if decided else None,
  }


def journal_summary(
  bridge_dir: Path | None = None,
  *,
  period: str = "all",
  now: datetime | None = None,
) -> dict[str, Any]:
  trades = filter_trades_by_period(load_trades(bridge_dir), period, now=now)
  closed = [t for t in trades if _is_closed(t)]
  r_vals = [r for t in closed if (r := _trade_r(t)) is not None]
  wins = sum(1 for t in closed if _trade_result(t) == "WIN")
  losses = sum(1 for t in closed if _trade_result(t) == "LOSS")
  bes = sum(1 for t in closed if _trade_result(t) == "BE")
  decided = wins + losses
  return {
    "period": period,
    "period_label": PERIOD_TITLES.get(period, PERIOD_LABELS.get(period, period)),
    "n_trades": len(trades),
    "n_closed": len(closed),
    "total_r": round(sum(r_vals), 3) if r_vals else 0.0,
    "wins": wins,
    "losses": losses,
    "be": bes,
    "win_rate_pct": round(100.0 * wins / decided, 1) if decided else None,
    "recent_fills": len(load_recent_fills(bridge_dir, limit=500)),
  }


def stats_by_model(
  bridge_dir: Path | None = None,
  *,
  period: str = "all",
  include_roster: bool = True,
  now: datetime | None = None,
) -> list[dict[str, Any]]:
  """Per-model summary for a period (today / week / month / all)."""
  all_trades = load_trades(bridge_dir)
  trades = filter_trades_by_period(all_trades, period, now=now)
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
      "period_label": PERIOD_TITLES.get(period, PERIOD_LABELS.get(period, period)),
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
