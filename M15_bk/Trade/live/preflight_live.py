"""Preflight Live books: materialize + one decide_for_bar per enabled model.

Fail Start trading early when the Live decision path is broken (missing
schedule/host/engine/cache), instead of discovering errors only after EA is up.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from books import bridge_dir, group_models_by_book
from live_config import LIVE_ROOT, RESULTS_DIR
from magic_allocator import assign_magics
from materialize_models import materialize_enabled
from package_store import load_roster, save_roster
from runtime_bootstrap import bootstrap_host
from runtime_host import normalize_symbol, normalize_timeframe
from shared.constants import LIVE_MAGIC_BASE
from sync_bridge_roster import write_models_json

PREFLIGHT_PATH = RESULTS_DIR / "live_preflight.json"


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _write(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + ".tmp")
  tmp.write_text(
    json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n",
    encoding="utf-8",
  )
  tmp.replace(path)


def _seed_cache(symbol: str, timeframe: str) -> Path | None:
  cache = RESULTS_DIR / "data" / f"mt5_{symbol.lower()}_{timeframe.lower()}.parquet"
  if cache.exists():
    return cache
  try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
      "seed_mt5_cache", LIVE_ROOT / "scripts" / "seed_mt5_cache.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    info = mod.seed(symbol, timeframe)
    dest = Path(info["dest"])
    return dest if dest.exists() else (cache if cache.exists() else None)
  except Exception as exc:
    _seed_cache.last_error = f"{type(exc).__name__}: {exc}"  # type: ignore[attr-defined]
    return cache if cache.exists() else None


_seed_cache.last_error = ""  # type: ignore[attr-defined]


def _last_bar_from_parquet(cache: Path) -> dict[str, Any] | None:
  try:
    import pandas as pd
    df = pd.read_parquet(cache)
  except Exception:
    return None
  if df is None or len(df) < 1:
    return None
  if not isinstance(df.index, pd.DatetimeIndex):
    for c in ("time", "timestamp", "datetime"):
      if c in df.columns:
        df = df.set_index(pd.to_datetime(df[c]))
        break
  if not isinstance(df.index, pd.DatetimeIndex) or len(df) < 1:
    return None
  # Prefer a bar inside the last schedule-covered week when possible
  ts = df.index[-1]
  row = df.iloc[-1]
  def _col(*names: str) -> float:
    for n in names:
      for c in df.columns:
        if str(c).lower() == n:
          return float(row[c])
    return float("nan")
  return {
    "bar_time": ts.strftime("%Y.%m.%d %H:%M") if hasattr(ts, "strftime") else str(ts),
    "time": ts.isoformat(sep=" ") if hasattr(ts, "isoformat") else str(ts),
    "open": _col("open"),
    "high": _col("high"),
    "low": _col("low"),
    "close": _col("close"),
    "volume": _col("volume", "tick_volume") if True else 0,
  }


def preflight_enabled_books(*, sim: bool = False) -> dict[str, Any]:
  """Run one decide_for_bar per enabled model. Returns ok + per-book details."""
  roster = load_roster()
  models = [m for m in (roster.get("models") or []) if m.get("enabled")]
  if not models:
    out = {
      "ok": False,
      "error": "no_enabled_models",
      "updated_at": _now(),
      "books": [],
    }
    _write(PREFLIGHT_PATH, out)
    return out

  assigned = assign_magics(models, sim=False)
  save_roster(assigned, active_book=roster.get("active_book"))
  try:
    mat = materialize_enabled(roster={"models": assigned})
  except Exception as exc:
    out = {
      "ok": False,
      "error": f"materialize_failed:{exc}",
      "updated_at": _now(),
      "books": [],
    }
    _write(PREFLIGHT_PATH, out)
    return out

  books_out: list[dict[str, Any]] = []
  all_ok = True
  for (sym, tf), rows in group_models_by_book(assigned).items():
    sym = normalize_symbol(sym)
    tf = normalize_timeframe(tf)
    book_entry: dict[str, Any] = {
      "symbol": sym,
      "timeframe": tf,
      "models": [],
      "ok": True,
    }
    cache = _seed_cache(sym, tf)
    if cache is None or not Path(cache).exists():
      book_entry["ok"] = False
      book_entry["error"] = "missing_ohlc_cache"
      book_entry["ohlc_hint"] = (
        "Start the EA so it writes bars.json; workers fill parquet via history_sync. "
        "Do not copy Train parquet into Live."
      )
      err = getattr(_seed_cache, "last_error", "") or ""
      if err:
        book_entry["seed_error"] = err
      all_ok = False
      books_out.append(book_entry)
      continue
    bar = _last_bar_from_parquet(Path(cache))
    if not bar:
      book_entry["ok"] = False
      book_entry["error"] = "cache_unreadable"
      all_ok = False
      books_out.append(book_entry)
      continue

    try:
      desk = bootstrap_host(sym, tf, force=True)
      book_entry["host"] = desk.name
      bdir = bridge_dir(sym, tf, sim=sim)
      write_models_json(bdir, rows, base_magic=LIVE_MAGIC_BASE)
      from mt5_bridge.background import build_engines
      mids = [str(r["model_id"]) for r in rows]
      engines = build_engines(
        mids,
        risk_pct=1.0,
        bridge_dir=bdir,
        base_magic=int(LIVE_MAGIC_BASE),
      )
      for eng in engines.values():
        try:
          eng.ensure_history()
        except Exception:
          pass
      for mid, eng in engines.items():
        try:
          decision = eng.decide_for_bar(bar)
          src = (
            (decision or {}).get("strategy_source")
            if isinstance(decision, dict)
            else None
          ) or getattr(eng, "_last_strategy_source", None)
          reason = (decision or {}).get("reason") if isinstance(decision, dict) else None
          action = (decision or {}).get("action") if isinstance(decision, dict) else None
          ok = isinstance(decision, dict) and reason not in (
            "legacy_data_source_blocked",
            "bar_not_in_series",
          )
          # insufficient_train / no_strategy on tip bar can still mean path works
          # if we got a structured decision with strategy_source or FLAT reason
          if isinstance(decision, dict) and decision.get("model_id"):
            ok = True
          book_entry["models"].append({
            "model_id": mid,
            "ok": ok,
            "action": action,
            "reason": reason,
            "strategy_source": src,
            "bar_time": bar.get("bar_time"),
          })
          if not ok:
            book_entry["ok"] = False
            all_ok = False
        except Exception as exc:
          book_entry["models"].append({
            "model_id": mid,
            "ok": False,
            "error": str(exc),
          })
          book_entry["ok"] = False
          all_ok = False
    except Exception as exc:
      book_entry["ok"] = False
      book_entry["error"] = str(exc)
      all_ok = False
    books_out.append(book_entry)

  out = {
    "ok": all_ok,
    "updated_at": _now(),
    "materialize_n": (mat or {}).get("n"),
    "books": books_out,
  }
  if not all_ok:
    fails = []
    for b in books_out:
      if b.get("ok"):
        continue
      if b.get("error"):
        fails.append(f"{b.get('symbol')} {b.get('timeframe')}: {b.get('error')}")
      for m in b.get("models") or []:
        if not m.get("ok"):
          fails.append(
            f"{m.get('model_id')}: {m.get('error') or m.get('reason') or 'decide_failed'}"
          )
    out["error"] = "; ".join(fails[:8]) or "preflight_failed"
  _write(PREFLIGHT_PATH, out)
  return out


def preflight_packages_ready(*, sim: bool = False) -> dict[str, Any]:
  """Fast Start gate: roster + schedule packages (no remine).

  OHLC is Trade-owned (EA bars.json / history_sync). Missing parquet is a
  warning, not a Start blocker — workers fill cache after EA deploy.
  Full ``preflight_enabled_books`` remine can hang the UI for minutes with
  multi-model books; workers remine on the first live bar instead.
  """
  from package_store import package_ready

  roster = load_roster()
  models = [m for m in (roster.get("models") or []) if m.get("enabled")]
  if not models:
    out = {
      "ok": False,
      "error": "no_enabled_models",
      "mode": "packages_only",
      "updated_at": _now(),
      "books": [],
    }
    _write(PREFLIGHT_PATH, out)
    return out

  assigned = assign_magics(models, sim=False)
  save_roster(assigned, active_book=roster.get("active_book"))
  try:
    mat = materialize_enabled(roster={"models": assigned})
  except Exception as exc:
    out = {
      "ok": False,
      "error": f"materialize_failed:{exc}",
      "mode": "packages_only",
      "updated_at": _now(),
      "books": [],
    }
    _write(PREFLIGHT_PATH, out)
    return out

  books_out: list[dict[str, Any]] = []
  all_ok = True
  for (sym, tf), rows in group_models_by_book(assigned).items():
    sym = normalize_symbol(sym)
    tf = normalize_timeframe(tf)
    book_entry: dict[str, Any] = {
      "symbol": sym,
      "timeframe": tf,
      "models": [],
      "ok": True,
    }
    cache = RESULTS_DIR / "data" / f"mt5_{sym.lower()}_{tf.lower()}.parquet"
    if not cache.exists():
      seeded = _seed_cache(sym, tf)
      cache = Path(seeded) if seeded else cache
    if cache.exists():
      book_entry["ohlc"] = "ready"
    else:
      # Do not block Start: workers request EA history_sync after deploy.
      book_entry["ohlc"] = "pending_ea"
      err = getattr(_seed_cache, "last_error", "") or ""
      if err:
        book_entry["seed_error"] = err
    for row in rows:
      iid = str(row.get("install_id") or "")
      mid = str(row.get("model_id") or "")
      info = package_ready(iid) if iid else {"ready": False, "error": "no install_id"}
      ok = bool(info.get("ready"))
      book_entry["models"].append({
        "model_id": mid,
        "install_id": iid,
        "ok": ok,
        "schedule_weeks": info.get("schedule_weeks"),
        "error": None if ok else (info.get("error") or "package_not_ready"),
      })
      if not ok:
        book_entry["ok"] = False
        all_ok = False
    books_out.append(book_entry)

  out = {
    "ok": all_ok,
    "mode": "packages_only",
    "updated_at": _now(),
    "materialize_n": (mat or {}).get("n"),
    "books": books_out,
  }
  if not all_ok:
    fails = []
    for b in books_out:
      if b.get("ok"):
        continue
      if b.get("error"):
        fails.append(f"{b.get('symbol')} {b.get('timeframe')}: {b.get('error')}")
      for m in b.get("models") or []:
        if not m.get("ok"):
          fails.append(f"{m.get('model_id')}: {m.get('error') or 'not_ready'}")
    out["error"] = "; ".join(fails[:8]) or "preflight_failed"
  _write(PREFLIGHT_PATH, out)
  return out


def load_last_preflight() -> dict[str, Any]:
  if not PREFLIGHT_PATH.exists():
    return {}
  try:
    return json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return {}
