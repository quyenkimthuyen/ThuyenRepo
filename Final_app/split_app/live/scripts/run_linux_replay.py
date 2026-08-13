#!/usr/bin/env python3
"""Linux Live simulate: decision worker + OHLC replay feeder (no MT5/Windows EA).

Example (fast smoke — 5 trading days):
  cd Final_app/split_app
  ../../EdgeMinerM15B5/.venv/bin/python live/scripts/seed_mt5_cache.py \\
      --symbol EURUSD --timeframe M15
  ../../EdgeMinerM15B5/.venv/bin/python live/scripts/run_linux_replay.py \\
      --symbol EURUSD --timeframe M15 \\
      --from 2026-01-05 --to 2026-01-10 --delay-ms 0

Feeder writes bar/fill into mt5/bridge_sim_live_<sym>_<tf>/;
decision service (--sim) remine+decides on the same protocol as real Live.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))

from books import bridge_dir, book_key  # noqa: E402
from live_config import RESULTS_DIR  # noqa: E402
from magic_allocator import assign_magics  # noqa: E402
from materialize_models import materialize_enabled  # noqa: E402
from package_store import load_roster, save_roster  # noqa: E402
from replay_feeder import run_replay  # noqa: E402
from runtime_host import normalize_symbol, normalize_timeframe  # noqa: E402
from shared.constants import LIVE_SIM_MAGIC_BASE, LIVE_SIM_PORT  # noqa: E402
from sync_bridge_roster import write_models_json  # noqa: E402


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _kill(pid: int | None) -> None:
  if not pid:
    return
  try:
    os.kill(pid, signal.SIGTERM)
  except OSError:
    return
  for _ in range(50):
    try:
      os.kill(pid, 0)
    except OSError:
      return
    time.sleep(0.05)
  try:
    os.kill(pid, signal.SIGKILL)
  except OSError:
    pass


def prepare_sim_book(symbol: str, timeframe: str) -> dict:
  symbol = normalize_symbol(symbol)
  timeframe = normalize_timeframe(timeframe)
  roster = load_roster()
  # Keep live magics in roster; build a sim-magic copy for this book only.
  live_rows = assign_magics(roster.get("models") or [], sim=False)
  save_roster(live_rows, active_book=roster.get("active_book"))
  sim_rows = assign_magics(live_rows, sim=True)

  book_sim = [
    r for r in sim_rows
    if r.get("enabled")
    and normalize_symbol(r.get("symbol")) == symbol
    and normalize_timeframe(r.get("timeframe")) == timeframe
  ]
  if not book_sim:
    raise SystemExit(
      f"No enabled models for {symbol} {timeframe}. Enable some in Live roster first."
    )

  mat = materialize_enabled(roster={"models": live_rows})
  bdir = bridge_dir(symbol, timeframe, sim=True)
  write_models_json(bdir, book_sim, base_magic=LIVE_SIM_MAGIC_BASE)
  return {
    "symbol": symbol,
    "timeframe": timeframe,
    "bridge_dir": bdir,
    "model_ids": [str(r["model_id"]) for r in book_sim],
    "rows": book_sim,
    "materialize": mat,
  }


def start_decision_worker(
  *,
  bridge_dir_path: Path,
  symbol: str,
  timeframe: str,
  model_ids: list[str],
  poll: float,
  log_path: Path,
) -> subprocess.Popen:
  script = LIVE / "scripts" / "mt5_bridge_service_live.py"
  cmd = [
    sys.executable,
    str(script),
    "--bridge-dir", str(bridge_dir_path),
    "--symbol", symbol,
    "--timeframe", timeframe,
    "--model-ids", ",".join(model_ids),
    "--risk-pct", "1.0",
    "--poll", str(poll),
    "--monitor-port", str(LIVE_SIM_PORT),
    "--sim",
  ]
  log_path.parent.mkdir(parents=True, exist_ok=True)
  logf = open(log_path, "a", encoding="utf-8")
  logf.write(f"\n--- replay worker start {_now()} ---\n")
  logf.flush()
  return subprocess.Popen(
    cmd,
    cwd=str(LIVE),
    stdout=logf,
    stderr=subprocess.STDOUT,
    start_new_session=True,
  )


def main() -> int:
  ap = argparse.ArgumentParser(description="Linux Live OHLC replay (sim bridge)")
  ap.add_argument("--symbol", default="EURUSD")
  ap.add_argument("--timeframe", default="M15")
  ap.add_argument("--from", dest="date_from", required=True)
  ap.add_argument("--to", dest="date_to", required=True)
  ap.add_argument("--delay-ms", type=int, default=0, help="0 = max speed")
  ap.add_argument("--decision-timeout", type=float, default=12.0)
  ap.add_argument("--poll", type=float, default=0.15)
  ap.add_argument("--parquet", type=Path, default=None)
  ap.add_argument("--seed", action="store_true", help="Seed cache from lab before run")
  args = ap.parse_args()

  symbol = normalize_symbol(args.symbol)
  timeframe = normalize_timeframe(args.timeframe)

  if args.seed or not (RESULTS_DIR / "data" / f"mt5_{normalize_symbol(args.symbol).lower()}_{normalize_timeframe(args.timeframe).lower()}.parquet").exists():
    # inline seed import (scripts/ is not a package)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
      "seed_mt5_cache", LIVE / "scripts" / "seed_mt5_cache.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    info = mod.seed(symbol, timeframe, src=args.parquet)
    print(f"[replay] seeded cache ← {info['source']}", flush=True)

  cache = RESULTS_DIR / "data" / f"mt5_{symbol.lower()}_{timeframe.lower()}.parquet"
  parquet = Path(args.parquet) if args.parquet else cache
  if not parquet.exists():
    raise SystemExit(f"Missing parquet: {parquet} (run with --seed)")

  prep = prepare_sim_book(symbol, timeframe)
  bdir: Path = prep["bridge_dir"]
  key = book_key(symbol, timeframe)
  log_path = RESULTS_DIR / "workers" / f"sim_{key}.log"
  print(
    f"[replay] book={symbol}/{timeframe} models={prep['model_ids']} dir={bdir}",
    flush=True,
  )

  proc = start_decision_worker(
    bridge_dir_path=bdir,
    symbol=symbol,
    timeframe=timeframe,
    model_ids=prep["model_ids"],
    poll=args.poll,
    log_path=log_path,
  )
  print(f"[replay] decision worker pid={proc.pid} log={log_path}", flush=True)
  # Give worker time to bootstrap host + load history
  time.sleep(3.0)
  if proc.poll() is not None:
    print(f"[replay] worker exited early rc={proc.returncode} — see {log_path}", flush=True)
    return 1

  def on_prog(p: dict) -> None:
    print(
      f"[replay] {p.get('bars_done')}/{p.get('bars_total')} "
      f"bar={p.get('last_bar')} fills={p.get('n_fills')} dec={p.get('decisions')}",
      flush=True,
    )

  try:
    summary = run_replay(
      bridge_dir=bdir,
      parquet=parquet,
      symbol=symbol,
      timeframe=timeframe,
      date_from=args.date_from,
      date_to=args.date_to,
      delay_ms=int(args.delay_ms),
      decision_timeout_sec=float(args.decision_timeout),
      clear=True,
      on_progress=on_prog,
    )
  except KeyboardInterrupt:
    print("[replay] interrupted", flush=True)
    summary = {"status": "interrupted"}
  finally:
    _kill(proc.pid)

  out = RESULTS_DIR / "replay_last.json"
  payload = {**summary, "updated_at": _now(), "worker_log": str(log_path)}
  out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  print(json.dumps(payload, indent=2), flush=True)
  return 0 if summary.get("status") == "completed" else 1


if __name__ == "__main__":
  raise SystemExit(main())
