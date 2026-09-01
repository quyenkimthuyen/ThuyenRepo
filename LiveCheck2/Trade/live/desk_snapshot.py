"""Aggregate Live bridge state for the trader desk UI."""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from books import bridge_dir, group_models_by_book
from chart_validate import read_chart_identity
from live_config import BRIDGE_DIR, RESULTS_DIR
from journal_view import (
  journal_summary_many,
  load_recent_fills,
  load_trades,
  load_trades_many,
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
  """Parse bridge timestamps. Naive MT5 wall times stay local (not UTC)."""
  if not raw:
    return None
  if isinstance(raw, datetime):
    if raw.tzinfo:
      return raw
    local_tz = datetime.now().astimezone().tzinfo
    return raw.replace(tzinfo=local_tz) if local_tz else raw
  s = str(raw).strip()
  if not s:
    return None
  try:
    if s.endswith("Z"):
      s = s[:-1] + "+00:00"
    # EA TimeToString: "YYYY.MM.DD HH:MM[:SS]"
    if len(s) >= 10 and s[4] == "." and s[7] == ".":
      s = s.replace(".", "-", 2)
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
      local_tz = datetime.now().astimezone().tzinfo
      if local_tz is not None:
        dt = dt.replace(tzinfo=local_tz)
    return dt
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


_WATCH_ACTION_RANK = {
  "BUY": 0, "LONG": 0, "SELL": 1, "SHORT": 1, "HOLD": 2, "FLAT": 3,
}


def _fmt_watch_px(value) -> str:
  if value is None or value == "":
    return "—"
  try:
    return f"{float(value):.5f}".rstrip("0").rstrip(".")
  except (TypeError, ValueError):
    return str(value)


def short_watch_name(label: str | None, symbol: str | None = "") -> str:
  """EUR WR57.1 from 'EURUSD M15 · WR57.1R66.4DD3.9'."""
  text = str(label or "")
  m = re.search(r"(WR[\d.]+)", text, re.I)
  wr = m.group(1).upper() if m else (text.split("·")[-1].strip()[:16] or "—")
  blob = f"{symbol or ''} {text}".upper()
  if "EUR" in blob:
    return f"EUR {wr}"
  if "GBP" in blob:
    return f"GBP {wr}"
  return wr


def _trade_day_key(raw: Any) -> str:
  s = str(raw or "").strip().replace(".", "-")
  return s[:10] if len(s) >= 10 and s[4] == "-" else ""


def _watch_bar_day(raw: Any) -> str:
  key = _trade_day_key(raw)
  if key:
    return key
  return datetime.now().astimezone().strftime("%Y-%m-%d")


def max_trades_per_day_map() -> dict[str, int]:
  data = _read(RESULTS_DIR / "trade_models.json") or {}
  out: dict[str, int] = {}
  for m in data.get("models") or []:
    mid = str(m.get("id") or m.get("model_id") or "")
    if not mid:
      continue
    try:
      out[mid] = max(0, int(m.get("max_trades_per_day") or 2))
    except (TypeError, ValueError):
      out[mid] = 2
  return out


def _count_day_trades(trades: list[dict], *, model_id: str, day: str) -> int:
  return len(_day_hit_marks(trades, model_id=model_id, day=day))


def _day_hit_marks(trades: list[dict], *, model_id: str, day: str) -> list[dict[str, Any]]:
  """Today's strategy fills for one model — entry time + side, oldest first."""
  out: list[dict[str, Any]] = []
  mid = str(model_id or "")
  for t in trades:
    if str(t.get("model_id") or "") != mid:
      continue
    st = str(t.get("status") or "").upper()
    if st not in ("OPEN", "CLOSED"):
      continue
    entry = t.get("entry_time") or t.get("bar_time") or t.get("updated_at")
    if _trade_day_key(entry) != day:
      continue
    side = str(t.get("direction") or t.get("action") or "").upper()
    out.append({
      "time": entry,
      "side": side,
      "status": st,
      "ticket": t.get("ticket"),
    })
  out.sort(key=lambda h: str(h.get("time") or ""))
  return out


PERIOD_TAG = {
  "today": "D",
  "week": "W",
  "month": "M",
  "all": "ALL",
}


def inspect_model_label(row: dict | None, *, period: str | None = None) -> str:
  """Model name in Now inspect / radio: only the selected D/W/M/ALL count."""
  row = row or {}
  name = str(row.get("model") or row.get("short") or row.get("model_id") or "—")
  p = str(period or row.get("period") or "today").lower().strip()
  n = None
  counts = row.get("period_counts")
  if isinstance(counts, dict) and p in counts:
    n = counts.get(p)
  if n is None:
    n = row.get("period_n")
  if n is None:
    hits = row.get("period_hits")
    if isinstance(hits, list):
      n = len(hits)
  if n is None:
    return name
  try:
    n_i = int(n)
  except (TypeError, ValueError):
    return name
  tag = PERIOD_TAG.get(p, p.upper()[:1] if p else "D")
  return f"{name} · {tag}({n_i})"


def _day_slots_pack(
  *,
  model: dict,
  dec: dict,
  trades: list[dict],
  day: str,
  max_map: dict[str, int],
) -> dict[str, Any]:
  mid = str(model.get("model_id") or dec.get("model_id") or "")
  raw_max = (
    model.get("max_trades_per_day")
    if model.get("max_trades_per_day") is not None
    else dec.get("max_trades_per_day")
  )
  if raw_max is None:
    raw_max = max_map.get(mid, 2)
  try:
    max_day = max(0, int(raw_max))
  except (TypeError, ValueError):
    max_day = 2
  hits = _day_hit_marks(trades, model_id=mid, day=day)
  taken = len(hits)
  remaining = max(0, max_day - taken)
  return {
    "max_trades_per_day": max_day,
    "day_taken": taken,
    "slots_remaining": remaining,
    "day_slots": f"{taken}/{max_day}",
    "day_full": taken >= max_day,
    "day_hits": hits,
  }


def now_watch_rows(snap: dict | None) -> list[dict[str, Any]]:
  """One row per enabled model for the Live Now watch table."""
  snap = snap or {}
  health = snap.get("health_detail") or {}
  books = list(health.get("books") or [])
  by_dec: dict[str, dict] = {}
  for d in snap.get("decisions") or []:
    mid = str(d.get("model_id") or "")
    if mid:
      by_dec[mid] = d
  max_map = max_trades_per_day_map()
  snap_trades = list(snap.get("open_trades") or []) + list(snap.get("journal_trades") or [])
  trades_by_dir: dict[str, list[dict]] = {}

  def _trades_for(book: dict | None) -> list[dict]:
    bdir = str((book or {}).get("bridge_dir") or "").strip()
    if not bdir:
      return snap_trades
    if bdir not in trades_by_dir:
      try:
        trades_by_dir[bdir] = list(load_trades(Path(bdir)))
      except Exception:
        trades_by_dir[bdir] = []
    return trades_by_dir[bdir] or snap_trades

  rows: list[dict[str, Any]] = []

  def _append(*, model: dict, book: dict | None, last) -> None:
    mid = str(model.get("model_id") or "")
    dec = by_dec.get(mid) or {}
    day = _watch_bar_day(
      dec.get("bar_time") or model.get("bar_time") or (book or {}).get("bar_time")
    )
    slots = _day_slots_pack(
      model=model, dec=dec, trades=_trades_for(book), day=day, max_map=max_map,
    )
    action = str(model.get("action") or dec.get("action") or "—").upper()
    reason = str(model.get("reason") or dec.get("reason") or dec.get("halt_source") or "—")
    bar_time = dec.get("bar_time") or model.get("bar_time") or (book or {}).get("bar_time") or "—"
    label = str(model.get("label") or mid or "—")
    levels = ""
    if action in ("BUY", "SELL", "LONG", "SHORT"):
      bits = []
      if dec.get("entry") is not None:
        bits.append(_fmt_watch_px(dec.get("entry")))
      if dec.get("sl") is not None:
        bits.append(f"SL {_fmt_watch_px(dec.get('sl'))}")
      if dec.get("tp") is not None:
        bits.append(f"TP {_fmt_watch_px(dec.get('tp'))}")
      levels = " · ".join(bits)
    tone = "hold" if action == "HOLD" else _decision_tone(action)
    expect_cur = {
      "expect": "—", "current": "—", "hits": [], "hit": False,
      "buy_text": "—", "sell_text": "—", "why": reason or "—",
      "buy_lines": [], "sell_lines": [],
      "buy_gate": "—", "sell_gate": "—",
      "buy_ready": False, "sell_ready": False,
      "wait": "—", "wait_ok": True, "wait_code": "",
      "session_gate": "—", "session_ok": True,
    }
    try:
      from watch_expect import watch_expect_current
      expect_cur = watch_expect_current(
        model_id=mid, book=book, action=action, reason=reason, bar_time=bar_time,
        dumped=dec.get("watch") if isinstance(dec.get("watch"), dict) else None,
        fills=slots.get("day_hits") or [],
        timeframe=(book or {}).get("timeframe") or model.get("timeframe") or "M15",
      )
    except Exception:
      pass
    rows.append({
      "action": action,
      "tone": tone,
      "model": label,
      "short": short_watch_name(label, (book or {}).get("symbol") or model.get("symbol") or ""),
      "model_id": mid,
      "reason": reason or "—",
      "why": expect_cur.get("why") or reason or "—",
      "bar_time": bar_time or "—",
      "last": _fmt_watch_px(last),
      "levels": levels,
      "expect": expect_cur.get("expect") or "—",
      "current": expect_cur.get("current") or "—",
      "buy_text": expect_cur.get("buy_text") or "—",
      "sell_text": expect_cur.get("sell_text") or "—",
      "buy_lines": list(expect_cur.get("buy_lines") or []),
      "sell_lines": list(expect_cur.get("sell_lines") or []),
      "buy_gate": expect_cur.get("buy_gate") or "—",
      "sell_gate": expect_cur.get("sell_gate") or "—",
      "buy_ready": bool(expect_cur.get("buy_ready")),
      "sell_ready": bool(expect_cur.get("sell_ready")),
      "wait": expect_cur.get("wait") or "—",
      "wait_ok": bool(expect_cur.get("wait_ok")),
      "wait_code": expect_cur.get("wait_code") or "",
      "session_gate": expect_cur.get("session_gate") or "—",
      "session_ok": bool(expect_cur.get("session_ok", True)),
      "chase_block": bool(expect_cur.get("chase_block")),
      "chase_on": bool(expect_cur.get("chase_on")),
      "score_buy": expect_cur.get("score_buy") or "—",
      "score_sell": expect_cur.get("score_sell") or "—",
      "score_ok": bool(expect_cur.get("score_ok")),
      "ml_buy": expect_cur.get("ml_buy") or "—",
      "ml_sell": expect_cur.get("ml_sell") or "—",
      "ml_ok": bool(expect_cur.get("ml_ok")),
      "ml_live": bool(expect_cur.get("ml_live")),
      "gap": expect_cur.get("gap") or "—",
      "gap_ok": bool(expect_cur.get("gap_ok", True)),
      "gap_on": bool(expect_cur.get("gap_on")),
      "rsi_text": expect_cur.get("rsi_text") or "—",
      "rsi_ok": bool(expect_cur.get("rsi_ok")),
      "htf_text": expect_cur.get("htf_text") or "—",
      "htf_ok": bool(expect_cur.get("htf_ok")),
      "pa_buy": expect_cur.get("pa_buy") or "—",
      "pa_sell": expect_cur.get("pa_sell") or "—",
      "pa_ok": bool(expect_cur.get("pa_ok")),
      "hits": list(expect_cur.get("hits") or []),
      "magic": model.get("magic") or dec.get("magic"),
      "symbol": (book or {}).get("symbol") or model.get("symbol") or "",
      "timeframe": (book or {}).get("timeframe") or model.get("timeframe") or "",
      "slots_remaining": slots.get("slots_remaining"),
      "max_trades_per_day": slots.get("max_trades_per_day"),
      "day_taken": slots.get("day_taken"),
      "day_slots": slots.get("day_slots") or "—",
      "day_full": bool(slots.get("day_full")),
      "day_hits": list(slots.get("day_hits") or []),
    })

  if books:
    for book in books:
      last = book.get("last")
      if last is None:
        last = book.get("bid")
      for model in book.get("models") or []:
        _append(model=model, book=book, last=last)
  else:
    for model in snap.get("models") or []:
      mid = str(model.get("model_id") or "")
      dec = by_dec.get(mid) or {}
      merged = {**model, "action": dec.get("action"), "reason": dec.get("reason"), "bar_time": dec.get("bar_time")}
      _append(model=merged, book=None, last=(snap.get("bar") or {}).get("close"))

  rows.sort(key=lambda r: (
    _WATCH_ACTION_RANK.get(str(r.get("action") or ""), 9),
    str(r.get("symbol") or ""),
    int(r.get("magic") or 0),
    str(r.get("model") or ""),
  ))
  return rows


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


def today_r(bridge_dirs: list[Path] | Path | None = None) -> dict[str, Any]:
  """Closed-trade stats for local calendar today across one or many bridges."""
  if bridge_dirs is None:
    dirs = [BRIDGE_DIR]
  elif isinstance(bridge_dirs, Path):
    dirs = [bridge_dirs]
  else:
    dirs = list(bridge_dirs)
  now = None
  try:
    from replay_control import feed_asof_now
    now = feed_asof_now()
  except Exception:
    now = None
  try:
    from journal_view import set_stats_asof
    set_stats_asof(now)
  except Exception:
    pass
  from journal_view import journal_summary_many as _sum
  day = _sum(dirs, period="today")
  return {
    "n": int(day.get("n_closed") or 0),
    "total_r": float(day.get("total_r") or 0.0),
    "wins": int(day.get("wins") or 0),
    "losses": int(day.get("losses") or 0),
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


def _call_bridge_status(*, sim: bool = False) -> dict[str, Any]:
  """Call status(); tolerate a stale Streamlit copy of bridge_control without sim=."""
  try:
    return bridge_status(sim=sim) or {}
  except TypeError:
    return bridge_status() or {}


def desk_snapshot(*, sim: bool = False) -> dict[str, Any]:
  from replay_control import is_replay_running, load_oos_prefs, load_sim_progress

  bstat = _call_bridge_status(sim=sim)
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
  prefs_mode = ""
  try:
    prefs_mode = str((load_oos_prefs() or {}).get("mode") or "")
  except Exception:
    prefs_mode = ""
  # Replay bar_time is historical (2026) — treat as "online" if sim_control running / fresh file mtime
  if sim and prefs_mode != "ea":
    ea_online = bool(bars) or is_replay_running()
    ea_fresh = 0.0 if ea_online else None
  elif sim:
    # EA Simulate: heartbeat like Live, but on bridge_sim_live_* connection.json
    ea_fresh = None
    for bdir in bdirs:
      for name in ("connection.json", "ea_sync.json", "heartbeat.json", "bar.json"):
        p = Path(bdir) / name
        try:
          if not p.exists():
            continue
          age = max(0.0, time.time() - p.stat().st_mtime)
          if ea_fresh is None or age < ea_fresh:
            ea_fresh = age
        except OSError:
          continue
    ea_online = ea_fresh is not None and ea_fresh < 180
  else:
    # Do NOT use candle bar_time for EA liveness — broker candle clocks can look
    # hours "stale" vs wall clock while connection.json is still heartbeat-fresh.
    ea_fresh = None
    for bdir in bdirs:
      for name in ("connection.json", "ea_sync.json", "heartbeat.json", "bar.json"):
        p = Path(bdir) / name
        try:
          if not p.exists():
            continue
          age = max(0.0, time.time() - p.stat().st_mtime)
          if ea_fresh is None or age < ea_fresh:
            ea_fresh = age
        except OSError:
          continue
    # Fallback: parsed connection updated_at if present
    if ea_fresh is None:
      for bdir in bdirs:
        conn = _read(Path(bdir) / "connection.json") or {}
        sync = _read(Path(bdir) / "ea_sync.json") or {}
        ts = _parse_ts(conn.get("updated_at") or sync.get("updated_at"))
        age = _age_seconds(ts)
        if age is not None and (ea_fresh is None or age < ea_fresh):
          ea_fresh = age
    ea_online = bool(charts) and (ea_fresh is not None and ea_fresh < 180)

  workers = bstat.get("workers") or []
  alive_workers = [w for w in workers if w.get("alive")]
  n_models = len(enabled)

  kill = bool(bstat.get("kill_switch") or is_kill_switch_armed())
  # Always aggregate across enabled books (legacy single BRIDGE_DIR alone misses M5/GBP…).
  journal = journal_summary_many(bdirs, period="all")
  day = today_r(bdirs)
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
    subtitle = ("EA SIMULATE · " if prefs_mode == "ea" else "REPLAY · ") + subtitle

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

  lg_tripped = False if sim else bool(cfg.get("loss_guard_tripped"))
  lg_reason = None if sim else cfg.get("loss_guard_tripped_reason")
  if not sim:
    try:
      from risk_prefs import any_worker_loss_guard_trip
      wt = any_worker_loss_guard_trip()
      if wt.get("tripped"):
        lg_tripped = True
        lg_reason = wt.get("tripped_reason") or lg_reason
    except Exception:
      pass

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
    "loss_guard_tripped": lg_tripped,
    "loss_guard_reason": lg_reason,
    "risk_pct": cfg.get("risk_pct"),
    "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "recent_fills": recent,
    "replay": replay,
    "bridge_dirs": [str(p) for p in bdirs],
  }
