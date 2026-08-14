#!/usr/bin/env python3
"""Schedule-parity replay — simulate that matches lab OOS (backtest_mined).

For each enabled model with a frozen ``*_schedule.json``:
  week genome → generate_signals_mined → backtest_mined
  (same path as Health walk-forward / GUIDE metrics)

This is the accuracy mode for Live Simulate. The bar-by-bar EA paper path
remains for protocol smoke; parity mode is what traders should trust for R/WR.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

LIVE = Path(__file__).resolve().parent
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))

from books import bridge_dir, group_models_by_book  # noqa: E402
from live_config import RESULTS_DIR  # noqa: E402
from materialize_models import materialize_enabled  # noqa: E402
from package_store import load_roster  # noqa: E402
from runtime_bootstrap import bootstrap_host  # noqa: E402
from runtime_host import normalize_symbol, normalize_timeframe  # noqa: E402


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + ".tmp")
  tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
  tmp.replace(path)


def seed_exact(symbol: str, timeframe: str) -> Path:
  """Force Live cache = exact lab parquet (no drifted extra bars)."""
  import importlib.util

  spec = importlib.util.spec_from_file_location(
    "seed_mt5_cache", LIVE / "scripts" / "seed_mt5_cache.py",
  )
  mod = importlib.util.module_from_spec(spec)
  assert spec.loader is not None
  spec.loader.exec_module(mod)
  info = mod.seed(symbol, timeframe)
  return Path(info["dest"])


def load_schedule(model_id: str) -> dict | None:
  from trade_model_schedule import load_model_schedule

  return load_model_schedule(model_id)


def replay_model_parity(
  *,
  model_id: str,
  symbol: str,
  timeframe: str,
  oos_from: str,
  oos_to: str,
  df: pd.DataFrame,
) -> dict[str, Any]:
  """Replay one model via frozen schedule + backtest_mined."""
  from feature_engine import FeatureMatrix
  from data_loader import get_train_window_indices, get_week_indices
  from config import MIN_TRAIN_BARS
  from strategy_miner import (
    backtest_mined,
    generate_signals_mined,
    mining_search_space_from_dict,
  )
  from trade_model_kb_pin import load_kb_for_run
  from trade_model_schedule import attach_ml_scorer, strategy_from_dict

  # Prefer Live materialized store (package), then desk get_model_by_id.
  model: dict = {}
  store = _read(RESULTS_DIR / "trade_models.json") or {}
  for m in store.get("models") or []:
    if str(m.get("id")) == str(model_id):
      model = dict(m)
      break
  if not model:
    try:
      from gui.trade_model import get_model_by_id
      model = get_model_by_id(model_id) or {}
    except Exception:
      model = {}
  sched = load_schedule(model_id)
  weekly = list((sched or {}).get("weekly") or [])
  if not weekly:
    return {
      "model_id": model_id,
      "ok": False,
      "error": "missing_schedule",
      "total_r": 0.0,
      "n_trades": 0,
    }

  feature_profile = model.get("feature_profile") or (
    "m5_parity" if timeframe == "M5" else "current"
  )
  spread = float(model.get("spread_pips") or 1.0)
  slip = float(model.get("slippage_pips") or 0.3)
  use_kb = bool(model.get("use_kb", True))
  kb_profile = model.get("kb_profile")
  kb_snapshot = model.get("kb_snapshot")
  search_payload = model.get("mining_search_space")
  search_space = mining_search_space_from_dict(search_payload) if search_payload else None

  kb = None
  if use_kb:
    kb = load_kb_for_run(
      use_learning=True,
      kb_profile=kb_profile,
      kb_snapshot=kb_snapshot,
      kb_pin_path=model.get("kb_pin_path"),
    )

  fm = FeatureMatrix(df, profile=feature_profile)
  all_trades = []
  week_rows = []
  oos_from_ts = pd.Timestamp(oos_from)
  oos_to_ts = pd.Timestamp(oos_to)

  for entry in weekly:
    ws = pd.Timestamp(entry.get("week_start"))
    we = pd.Timestamp(entry.get("week_end") or (ws + pd.Timedelta(days=7)))
    if ws < oos_from_ts or ws > oos_to_ts:
      continue
    strat_d = entry.get("strategy")
    if not isinstance(strat_d, dict):
      continue
    strat = strategy_from_dict(strat_d)
    # Always recompute train window from calendar week — stored train_*_idx can
    # drift when lab parquet grows/shifts and would poison ML labels.
    tw = int(model.get("train_weeks") or 6)
    ts, te = get_train_window_indices(df, ws, tw)
    if ts is None or (te - ts) < MIN_TRAIN_BARS:
      week_rows.append({"week_start": str(ws.date()), "status": "skip_train"})
      continue

    attach_ml_scorer(
      strat, fm, ts, te, kb=kb, as_of=ws, search_space=search_space,
    )
    oos_s, oos_e = get_week_indices(df, ws, we)
    if oos_s is None:
      week_rows.append({"week_start": str(ws.date()), "status": "skip_oos"})
      continue
    signals = generate_signals_mined(fm, strat, oos_s, oos_e)
    trades = backtest_mined(
      fm, strat, signals, oos_s, oos_e,
      spread_pips=spread, slippage_pips=slip,
    )
    all_trades.extend(trades)
    wr = (sum(1 for t in trades if t.r_multiple > 0) / len(trades) * 100) if trades else 0.0
    tot = sum(float(t.r_multiple) for t in trades)
    week_rows.append({
      "week_start": str(ws.date()),
      "strategy": getattr(strat, "name", None),
      "n_trades": len(trades),
      "total_r": round(tot, 3),
      "win_rate_pct": round(wr, 2),
      "lab_oos_r": entry.get("oos_r"),
      "lab_oos_trades": entry.get("oos_trades"),
    })

  n = len(all_trades)
  wins = sum(1 for t in all_trades if t.r_multiple > 0)
  total_r = sum(float(t.r_multiple) for t in all_trades)
  lab_overall = ((sched or {}).get("meta") or {}).get("overall") or {}
  return {
    "model_id": model_id,
    "label": model.get("label"),
    "ok": True,
    "n_trades": n,
    "win_rate_pct": round(100.0 * wins / n, 2) if n else 0.0,
    "total_r": round(total_r, 3),
    "profit_factor": _pf(all_trades),
    "max_drawdown_r": _max_dd(all_trades),
    "lab_total_r": lab_overall.get("total_r"),
    "lab_win_rate_pct": lab_overall.get("win_rate_pct"),
    "lab_n_trades": lab_overall.get("n_trades"),
    "delta_r": round(total_r - float(lab_overall.get("total_r") or 0), 3),
    "weeks": week_rows,
    "symbol": symbol,
    "timeframe": timeframe,
  }


def _pf(trades: list) -> float:
  gp = sum(float(t.r_multiple) for t in trades if t.r_multiple > 0)
  gl = abs(sum(float(t.r_multiple) for t in trades if t.r_multiple < 0))
  if gl <= 1e-12:
    return 99.0 if gp > 0 else 0.0
  return round(gp / gl, 3)


def _max_dd(trades: list) -> float:
  eq = peak = 0.0
  dd = 0.0
  for t in trades:
    eq += float(t.r_multiple)
    peak = max(peak, eq)
    dd = max(dd, peak - eq)
  return round(dd, 3)


def run_book_parity(
  symbol: str,
  timeframe: str,
  *,
  oos_from: str = "2026-01-01",
  oos_to: str = "2026-08-07",
) -> dict[str, Any]:
  symbol = normalize_symbol(symbol)
  timeframe = normalize_timeframe(timeframe)
  roster = load_roster()
  enabled = [
    r for r in (roster.get("models") or [])
    if r.get("enabled")
    and normalize_symbol(r.get("symbol")) == symbol
    and normalize_timeframe(r.get("timeframe")) == timeframe
  ]
  if not enabled:
    return {"ok": False, "error": "no_enabled_models", "symbol": symbol, "timeframe": timeframe}

  materialize_enabled(roster=roster)
  desk = bootstrap_host(symbol, timeframe, force=True)
  cache = seed_exact(symbol, timeframe)

  try:
    df = pd.read_parquet(cache)
  except Exception as exc:
    return {
      "ok": False,
      "error": f"cache_read_failed:{exc}",
      "symbol": symbol,
      "timeframe": timeframe,
      "cache": str(cache),
    }
  if df is None or len(df) < 100:
    return {
      "ok": False,
      "error": f"cache_too_small:{len(df) if df is not None else 0}",
      "symbol": symbol,
      "timeframe": timeframe,
      "cache": str(cache),
    }
  rename = {
    c: c[:1].upper() + c[1:] if c.lower() in ("open", "high", "low", "close", "volume") else c
    for c in df.columns
  }
  # standardize Open/High/Low/Close/Volume
  colmap = {}
  for c in df.columns:
    cl = c.lower()
    if cl == "open":
      colmap[c] = "Open"
    elif cl == "high":
      colmap[c] = "High"
    elif cl == "low":
      colmap[c] = "Low"
    elif cl == "close":
      colmap[c] = "Close"
    elif cl == "volume":
      colmap[c] = "Volume"
  if colmap:
    df = df.rename(columns=colmap)
  if not isinstance(df.index, pd.DatetimeIndex):
    for c in ("time", "timestamp", "datetime"):
      if c in df.columns:
        df[c] = pd.to_datetime(df[c])
        df = df.set_index(c)
        break

  bdir = bridge_dir(symbol, timeframe, sim=True)
  bdir.mkdir(parents=True, exist_ok=True)
  results = []
  for row in enabled:
    mid = str(row["model_id"])
    print(f"[parity] {symbol} {timeframe} · {mid}", flush=True)
    out = replay_model_parity(
      model_id=mid,
      symbol=symbol,
      timeframe=timeframe,
      oos_from=oos_from,
      oos_to=oos_to,
      df=df,
    )
    results.append(out)
    print(
      f"  -> R={out.get('total_r')} WR={out.get('win_rate_pct')} n={out.get('n_trades')} "
      f"lab_R={out.get('lab_total_r')} dR={out.get('delta_r')} err={out.get('error')}",
      flush=True,
    )

  summary = {
    "updated_at": _now(),
    "mode": "schedule_parity",
    "host": desk.name,
    "symbol": symbol,
    "timeframe": timeframe,
    "oos_from": oos_from,
    "oos_to": oos_to,
    "cache": str(cache),
    "models": results,
    "ok": all(r.get("ok") for r in results),
  }
  out_path = RESULTS_DIR / f"parity_{symbol.lower()}_{timeframe.lower()}.json"
  _write(out_path, summary)
  _write(RESULTS_DIR / "replay_last.json", {
    "status": "completed",
    "mode": "schedule_parity",
    "symbol": symbol,
    "timeframe": timeframe,
    "date_from": oos_from,
    "date_to": oos_to,
    "models": [r.get("model_id") for r in results],
    "n_fills": sum(int(r.get("n_trades") or 0) for r in results),
    "summaries": results,
    "updated_at": _now(),
  })
  return summary


def run_all_enabled_parity(
  *,
  oos_from: str = "2026-01-01",
  oos_to: str = "2026-08-07",
) -> dict[str, Any]:
  roster = load_roster()
  enabled = [r for r in (roster.get("models") or []) if r.get("enabled")]
  groups = group_models_by_book(enabled)
  books = []
  for (sym, tf), _ in groups.items():
    books.append(run_book_parity(sym, tf, oos_from=oos_from, oos_to=oos_to))
  payload = {
    "updated_at": _now(),
    "oos_from": oos_from,
    "oos_to": oos_to,
    "books": books,
    "ok": all(b.get("ok") for b in books),
  }
  _write(RESULTS_DIR / "parity_oos_batch.json", payload)
  try:
    from replay_history import archive_parity_batch
    entry = archive_parity_batch(payload)
    payload["run_id"] = entry.get("run_id")
    print(f"[parity] archived {entry.get('run_id')} total_r={entry.get('total_r')}", flush=True)
  except Exception as exc:
    print(f"[parity] archive failed: {exc}", flush=True)
  return payload
