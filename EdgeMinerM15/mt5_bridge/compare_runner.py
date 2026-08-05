"""Multi-model Compare Trade runner — history replay without EA.

Uses MT5 parquet cache + BridgeEngine decisions + Python paper fills.
Each model gets an isolated journal under results/compare_trade/<run_id>/models/<id>/.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from mt5_bridge.engine import BridgeEngine, _normalize
from mt5_bridge.history_sync import MT5_CACHE_PATH, load_mt5_cache, utc_to_broker_time
from mt5_bridge.paper_fill import PaperBook
from mt5_bridge.protocol import atomic_write_json, ensure_bridge_dir
from mt5_bridge.trade_journal import clear_trades, compute_stats, load_trades
from run_backtest import REPORT_DIR

COMPARE_ROOT = REPORT_DIR / "compare_trade"
LATEST_PATH = COMPARE_ROOT / "latest.json"
MAX_MODELS = 5

ProgressCb = Callable[[dict[str, Any]], None]
CancelCb = Callable[[], bool]


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, data: dict) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  atomic_write_json(path, data)


def load_run(run_id: str) -> dict | None:
  path = COMPARE_ROOT / run_id / "run.json"
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except Exception:
    return None


def load_latest_run() -> dict | None:
  if not LATEST_PATH.exists():
    # Fall back to newest run dir
    if not COMPARE_ROOT.exists():
      return None
    dirs = sorted(
      [p for p in COMPARE_ROOT.iterdir() if p.is_dir() and (p / "run.json").exists()],
      key=lambda p: p.stat().st_mtime,
      reverse=True,
    )
    if not dirs:
      return None
    return load_run(dirs[0].name)
  try:
    meta = json.loads(LATEST_PATH.read_text(encoding="utf-8"))
  except Exception:
    return None
  rid = meta.get("run_id")
  return load_run(rid) if rid else None


def save_run(run: dict) -> dict:
  run_id = run["run_id"]
  run = {**run, "updated_at": _now()}
  _write_json(COMPARE_ROOT / run_id / "run.json", run)
  _write_json(LATEST_PATH, {"run_id": run_id, "updated_at": run["updated_at"]})
  return run


def model_dir(run_id: str, model_id: str) -> Path:
  return ensure_bridge_dir(COMPARE_ROOT / run_id / "models" / model_id)


def _bar_dict(ts: pd.Timestamp, row: pd.Series) -> dict:
  broker = utc_to_broker_time(ts)
  return {
    "time": broker.strftime("%Y.%m.%d %H:%M"),
    "open": float(row["Open"]),
    "high": float(row["High"]),
    "low": float(row["Low"]),
    "close": float(row["Close"]),
    "volume": float(row["Volume"] if "Volume" in row.index else 0.0),
    "symbol": "EURUSD",
  }


def _broker_date(ts: pd.Timestamp):
  return utc_to_broker_time(ts).date()


def slice_replay_frame(
  df: pd.DataFrame,
  date_from: str,
  date_to: str,
) -> pd.DataFrame:
  """Bars whose broker calendar date falls in [date_from, date_to]."""
  if df is None or df.empty:
    return pd.DataFrame()
  start = pd.Timestamp(str(date_from)[:10]).date()
  end = pd.Timestamp(str(date_to)[:10]).date()
  mask = [_broker_date(ts) >= start and _broker_date(ts) <= end for ts in df.index]
  return df.loc[mask]


def model_stats_rows(run: dict) -> list[dict]:
  """One stats row per model for the Compare Trade table."""
  from gui.trade_model import format_model_label, get_model_by_id

  rows = []
  run_id = run.get("run_id")
  for mid in run.get("model_ids") or []:
    m = get_model_by_id(mid)
    label = format_model_label(m) if m else mid
    mdir = model_dir(str(run_id), str(mid))
    stats = compute_stats(load_trades(mdir), mode="auto", use_exit_time=False)
    per = (run.get("per_model") or {}).get(mid) or {}
    rows.append({
      "Model": label,
      "model_id": mid,
      "Total R": stats.get("total_r"),
      "WR %": stats.get("win_rate_pct"),
      "Trades": stats.get("n_trades"),
      "Open": stats.get("n_open"),
      "Max DD": stats.get("max_drawdown_r"),
      "Avg R": stats.get("avg_r"),
      "Fills": per.get("n_fills", stats.get("n_trades")),
    })
  return rows


def run_compare(
  *,
  model_ids: list[str],
  date_from: str,
  date_to: str,
  risk_pct: float = 1.0,
  run_id: str | None = None,
  on_progress: ProgressCb | None = None,
  should_cancel: CancelCb | None = None,
  mt5_cache: Path | None = None,
) -> dict:
  """Replay history for each model; return final run manifest."""
  ids = [str(m) for m in (model_ids or []) if m]
  if len(ids) < 2:
    raise ValueError("Compare Trade cần ít nhất 2 trade model.")
  if len(ids) > MAX_MODELS:
    raise ValueError(f"Tối đa {MAX_MODELS} model / run.")

  cache_path = Path(mt5_cache) if mt5_cache else MT5_CACHE_PATH
  raw = load_mt5_cache() if cache_path.resolve() == MT5_CACHE_PATH.resolve() else None
  if raw is None:
    if not cache_path.exists():
      raise RuntimeError(
        f"Không có lịch sử MT5 cache: {cache_path}. Đồng bộ history từ MT5 Bridge trước."
      )
    raw = pd.read_parquet(cache_path)
  full = _normalize(raw)
  replay = slice_replay_frame(full, date_from, date_to)
  if replay.empty:
    raise ValueError(f"Không có bar trong khoảng {date_from} → {date_to}.")

  rid = run_id or f"ct_{datetime.now(timezone.utc).astimezone().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
  run: dict[str, Any] = {
    "run_id": rid,
    "status": "running",
    "model_ids": ids,
    "date_from": str(date_from)[:10],
    "date_to": str(date_to)[:10],
    "risk_pct": float(risk_pct),
    "bars_done": 0,
    "bars_total": len(replay),
    "progress": 0.0,
    "per_model": {mid: {"n_fills": 0, "error": None} for mid in ids},
    "error": None,
    "started_at": _now(),
    "finished_at": None,
    "source": "mt5_cache_paper",
  }
  save_run(run)

  engines: dict[str, BridgeEngine] = {}
  books: dict[str, PaperBook] = {}
  for mid in ids:
    mdir = model_dir(rid, mid)
    clear_trades(mdir)
    eng = BridgeEngine(
      model_id=mid,
      risk_pct=float(risk_pct),
      mt5_cache=cache_path,
      bridge_dir=mdir,
    )
    # Prefill full history for remine (avoid per-bar parquet writes)
    eng._df = full.copy()
    engines[mid] = eng
    books[mid] = PaperBook(bridge_dir=mdir, model_id=mid)

  total = len(replay)
  try:
    for i, (ts, row) in enumerate(replay.iterrows(), start=1):
      if should_cancel and should_cancel():
        run["status"] = "cancelled"
        run["finished_at"] = _now()
        save_run(run)
        raise InterruptedError("Compare Trade cancelled")

      bar = _bar_dict(ts, row)
      bar_time = bar["time"]

      for mid in ids:
        book = books[mid]
        eng = engines[mid]
        # 1) fills at this bar open / manage open position
        book.on_bar(
          open_=bar["open"],
          high=bar["high"],
          low=bar["low"],
          close=bar["close"],
          bar_time=bar_time,
        )
        # 2) decide on closed bar → pending for next open
        try:
          decision = eng.decide_for_bar(bar)
        except Exception as e:
          run["per_model"][mid]["error"] = str(e)
          decision = None
        book.queue_decision(decision)
        run["per_model"][mid]["n_fills"] = book.n_fills

      run["bars_done"] = i
      run["progress"] = round(i / total, 4)
      if i == 1 or i == total or i % 25 == 0:
        save_run(run)
        if on_progress:
          on_progress({
            "bars_done": i,
            "bars_total": total,
            "progress": run["progress"],
            "run_id": rid,
            "last_bar": bar_time,
          })

    run["status"] = "completed"
    run["finished_at"] = _now()
    for mid in ids:
      run["per_model"][mid]["n_fills"] = books[mid].n_fills
      stats = compute_stats(load_trades(model_dir(rid, mid)), mode="auto", use_exit_time=False)
      run["per_model"][mid]["stats"] = {
        "total_r": stats.get("total_r"),
        "win_rate_pct": stats.get("win_rate_pct"),
        "n_trades": stats.get("n_trades"),
        "max_drawdown_r": stats.get("max_drawdown_r"),
      }
    save_run(run)
    if on_progress:
      on_progress({
        "bars_done": total,
        "bars_total": total,
        "progress": 1.0,
        "run_id": rid,
        "status": "completed",
      })
    return run
  except InterruptedError:
    raise
  except Exception as e:
    run["status"] = "error"
    run["error"] = str(e)
    run["finished_at"] = _now()
    save_run(run)
    raise
