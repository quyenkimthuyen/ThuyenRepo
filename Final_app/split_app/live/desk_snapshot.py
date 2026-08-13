"""Aggregate Live bridge state for the trader desk UI."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from books import bridge_dir, group_models_by_book
from chart_validate import read_chart_identity
from live_config import BRIDGE_DIR, RESULTS_DIR
from journal_view import (
  journal_summary,
  journal_summary_many,
  load_recent_fills,
  load_trades,
  load_trades_many,
  stats_by_model,
  stats_by_model_many,
)
from package_store import default_roster_from_installed, list_installed, load_roster
from safety import is_kill_switch_armed
from bridge_control import status as bridge_status


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def _parse_ts(raw: Any) -> datetime | None:
  if not raw:
    return None
  s = str(raw).strip()
  try:
    if s.endswith("Z"):
      s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)
  except ValueError:
    return None


def _age_seconds(ts: datetime | None) -> float | None:
  if ts is None:
    return None
  now = datetime.now(timezone.utc)
  if ts.tzinfo is None:
    ts = ts.replace(tzinfo=timezone.utc)
  return max(0.0, (now - ts.astimezone(timezone.utc)).total_seconds())


def _fmt_age(sec: float | None) -> str:
  if sec is None:
    return "—"
  if sec < 5:
    return "now"
  if sec < 60:
    return f"{int(sec)}s"
  if sec < 3600:
    return f"{int(sec // 60)}m"
  return f"{int(sec // 3600)}h"


def _decision_tone(action: str | None) -> str:
  a = (action or "").upper()
  if a in ("BUY", "LONG"):
    return "long"
  if a in ("SELL", "SHORT"):
    return "short"
  if a in ("FLAT", "CLOSE", "HOLD"):
    return "flat"
  return "unknown"


def load_decisions(bridge_dir: Path | None = None) -> list[dict]:
  bdir = Path(bridge_dir or BRIDGE_DIR)
  rows: list[dict] = []
  primary = _read(bdir / "decision.json")
  if isinstance(primary, dict):
    rows.append({**primary, "_file": "decision.json", "_bridge": str(bdir)})
  dec_dir = bdir / "decisions"
  if dec_dir.is_dir():
    for p in sorted(dec_dir.glob("*.json")):
      data = _read(p)
      if isinstance(data, dict):
        rows.append({
          **data,
          "_file": p.name,
          "model_id": data.get("model_id") or p.stem,
          "_bridge": str(bdir),
        })
  by_mid: dict[str, dict] = {}
  for r in rows:
    mid = str(r.get("model_id") or ("__primary__" if r.get("_file") == "decision.json" else r.get("_file")))
    if mid == "__primary__" and by_mid:
      continue
    by_mid[mid] = r
  return list(by_mid.values()) or rows


def open_trades(bridge_dir: Path | None = None) -> list[dict]:
  out = []
  for t in load_trades(bridge_dir):
    if t.get("exit") is not None or t.get("status") == "closed":
      continue
    st = str(t.get("status") or "").upper()
    if st == "CLOSED":
      continue
    out.append(t)
  return out


def today_r(bridge_dir: Path | None = None) -> dict[str, Any]:
  today = datetime.now().astimezone().date()
  r_vals: list[float] = []
  n = 0
  for t in load_trades(bridge_dir):
    st = str(t.get("status") or "").upper()
    if st != "CLOSED" and t.get("exit") is None and t.get("status") != "closed":
      continue
    ts = _parse_ts(t.get("closed_at") or t.get("exit_time") or t.get("updated_at") or t.get("ts"))
    if ts is None:
      continue
    if ts.astimezone().date() != today:
      continue
    try:
      if t.get("r") is not None:
        r_vals.append(float(t["r"]))
        n += 1
    except (TypeError, ValueError):
      pass
  return {
    "n": n,
    "total_r": round(sum(r_vals), 3) if r_vals else 0.0,
    "wins": sum(1 for r in r_vals if r > 0),
    "losses": sum(1 for r in r_vals if r < 0),
  }


def book_models() -> list[dict]:
  roster = load_roster()
  models = roster.get("models") or default_roster_from_installed()
  return [m for m in models if m.get("enabled")]


def _bridge_dirs_for_enabled(enabled: list[dict], *, sim: bool = False) -> list[Path]:
  dirs: list[Path] = []
  seen = set()
  for (sym, tf), _ in group_models_by_book(enabled).items():
    p = bridge_dir(sym, tf, sim=sim)
    if str(p) not in seen:
      dirs.append(p)
      seen.add(str(p))
  if not sim and str(BRIDGE_DIR) not in seen:
    dirs.append(BRIDGE_DIR)
  return dirs


def desk_snapshot(*, sim: bool = False) -> dict[str, Any]:
  from replay_control import is_replay_running, load_sim_progress

  bstat = bridge_status()
  enabled = book_models()
  bdirs = _bridge_dirs_for_enabled(enabled, sim=sim)

  all_decisions: list[dict] = []
  charts = []
  bars = []
  for bdir in bdirs:
    all_decisions.extend(load_decisions(bdir))
    ch = read_chart_identity(bdir)
    if ch.get("symbol") or ch.get("timeframe"):
      charts.append(ch)
    bar = _read(bdir / "bar.json")
    if isinstance(bar, dict) and bar:
      bars.append({**bar, "_bridge": str(bdir)})

  primary = {}
  for d in all_decisions:
    if str(d.get("action") or "").upper() in ("BUY", "SELL"):
      primary = d
      break
  if not primary and all_decisions:
    primary = all_decisions[0]

  action = str(primary.get("action") or "—").upper()
  chart = charts[0] if charts else read_chart_identity(bdirs[0] if bdirs else BRIDGE_DIR)
  bar = bars[0] if bars else {}

  bar_ts = _parse_ts(bar.get("time") or bar.get("bar_time") or bar.get("updated_at"))
  # Replay bar_time is historical (2026) — treat as "online" if sim_control running / fresh file mtime
  if sim:
    ea_online = bool(bars) or is_replay_running()
    ea_fresh = 0.0 if ea_online else None
  else:
    ea_fresh = _age_seconds(bar_ts)
    ea_online = bool(charts) and (ea_fresh is None or ea_fresh < 180)

  workers = bstat.get("workers") or []
  alive_workers = [w for w in workers if w.get("alive")]
  n_models = len(enabled)

  kill = bool(bstat.get("kill_switch") or is_kill_switch_armed())
  if sim:
    journal = journal_summary_many(bdirs, period="all")
    day = {
      "n": journal.get("n_closed") or 0,
      "total_r": journal.get("total_r") or 0.0,
      "wins": journal.get("wins") or 0,
      "losses": journal.get("losses") or 0,
    }
    opens = []
    seen_t = set()
    for t in load_trades_many(bdirs):
      if t.get("exit") is not None or str(t.get("status") or "").upper() == "CLOSED":
        continue
      key = (t.get("ticket"), t.get("signal_id"), t.get("model_id"))
      if key in seen_t:
        continue
      seen_t.add(key)
      opens.append(t)
    by_model = stats_by_model_many(bdirs, period="all")
    recent = []
    for bdir in bdirs:
      recent.extend(load_recent_fills(bdir, limit=20))
    recent = recent[-20:]
    replay = load_sim_progress()
  else:
    journal = journal_summary()
    day = today_r()
    opens = []
    seen_t = set()
    for bdir in bdirs:
      for t in open_trades(bdir):
        key = (t.get("ticket"), t.get("signal_id"), t.get("model_id"))
        if key in seen_t:
          continue
        seen_t.add(key)
        opens.append(t)
    by_model = stats_by_model()
    recent = load_recent_fills(limit=12)
    replay = {"running": False, "books": []}

  if sim:
    if replay.get("running"):
      health, health_tone = "REPLAY", "ok"
    elif journal.get("n_closed"):
      health, health_tone = "SIM DONE", "ok"
    else:
      health, health_tone = "SIM IDLE", "muted"
  elif kill:
    health, health_tone = "HALTED", "danger"
  elif not enabled:
    health, health_tone = "NO MODELS", "warn"
  elif bstat.get("running") and ea_online:
    health, health_tone = "LIVE", "ok"
  elif bstat.get("running"):
    health, health_tone = "WAITING EA", "warn"
  else:
    health, health_tone = "IDLE", "muted"

  cfg = _read(RESULTS_DIR / "mt5_bridge_config.json") or {}
  subtitle = f"{n_models} model{'s' if n_models != 1 else ''} on"
  if sim:
    subtitle = "REPLAY · " + subtitle

  try:
    from live_health import build_live_health
    health_detail = build_live_health(sim=sim)
  except Exception as exc:
    health_detail = {
      "overall": "warn",
      "summary": "HEALTH ERR",
      "n_alerts": 1,
      "alerts": [{"level": "warn", "message": str(exc)}],
      "books": [],
    }

  return {
    "mode": "replay" if sim else "live",
    "health": health,
    "health_tone": health_tone,
    "health_detail": health_detail,
    "bridge_running": bool(bstat.get("running")) if not sim else bool(replay.get("running")),
    "bridge_pid": bstat.get("pid") if not sim else replay.get("pid"),
    "bridge_state": "running" if (replay.get("running") if sim else bstat.get("running")) else "stopped",
    "n_workers": len(alive_workers),
    "workers": alive_workers,
    "kill_switch": kill,
    "ea_online": ea_online,
    "ea_age": _fmt_age(ea_fresh) if not sim else (bar.get("bar_time") or "—"),
    "chart_ok": True,
    "chart_errors": [],
    "chart_warnings": [],
    "subtitle": subtitle,
    "symbol": chart.get("symbol") or bar.get("symbol") or "—",
    "timeframe": chart.get("timeframe") or bar.get("period") or "—",
    "bar": {
      "time": bar.get("time") or bar.get("bar_time"),
      "close": bar.get("close"),
      "spread_points": bar.get("spread_points"),
      "age": _fmt_age(_age_seconds(bar_ts)) if not sim else (bar.get("bar_time") or "—"),
    },
    "decision": {
      "action": action,
      "tone": _decision_tone(action),
      "reason": primary.get("reason") or primary.get("halt_source") or "",
      "model_id": primary.get("model_id"),
      "bar_time": primary.get("bar_time") or primary.get("time"),
      "updated_at": primary.get("updated_at"),
      "age": _fmt_age(_age_seconds(_parse_ts(primary.get("updated_at")))) if primary.get("updated_at") else "—",
      "halt": bool(primary.get("halt")),
    },
    "decisions": all_decisions,
    "models": enabled,
    "n_installed": len(list_installed()),
    "open_trades": opens,
    "n_open": len(opens),
    "journal": journal,
    "by_model": by_model,
    "today": day,
    "loss_guard_tripped": bool(cfg.get("loss_guard_tripped")) if not sim else False,
    "loss_guard_reason": cfg.get("loss_guard_tripped_reason") if not sim else None,
    "risk_pct": cfg.get("risk_pct"),
    "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "recent_fills": recent,
    "replay": replay,
    "bridge_dirs": [str(p) for p in bdirs],
  }
