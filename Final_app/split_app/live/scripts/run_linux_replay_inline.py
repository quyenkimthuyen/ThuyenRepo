#!/usr/bin/env python3
"""Linux Live OHLC replay — inline decide (no separate worker IPC).

Faster & reliable for long OOS windows: bootstrap host → for each bar
BridgeEngine.decide_for_bar → paper fill. Same bridge_sim_live_* artifacts.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
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
from replay_feeder import (  # noqa: E402
  _emit_fill,
  _write_bar,
  _write_connection,
  _write_sim_control,
  clear_replay_artifacts,
  load_ohlc,
  mt5_bar_time,
)
from replay_paper import ReplayPaperBook  # noqa: E402
from runtime_bootstrap import bootstrap_host  # noqa: E402
from runtime_host import normalize_symbol, normalize_timeframe  # noqa: E402
from shared.constants import LIVE_SIM_MAGIC_BASE  # noqa: E402
from sync_bridge_roster import write_models_json  # noqa: E402


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _seed(symbol: str, timeframe: str, src: Path | None) -> Path:
  cache = RESULTS_DIR / "data" / f"mt5_{symbol.lower()}_{timeframe.lower()}.parquet"
  if src and Path(src).exists() and Path(src).resolve() == cache.resolve() and cache.exists():
    return cache
  if cache.exists() and src is None:
    return cache
  spec = importlib.util.spec_from_file_location("seed_mt5_cache", LIVE / "scripts" / "seed_mt5_cache.py")
  mod = importlib.util.module_from_spec(spec)
  assert spec.loader is not None
  spec.loader.exec_module(mod)
  info = mod.seed(symbol, timeframe, src=src)
  print(f"[inline] seeded ← {info['source']}", flush=True)
  return Path(info["dest"])


def prepare_sim_book(symbol: str, timeframe: str, *, materialize: bool = True) -> dict:
  roster = load_roster()
  live_rows = assign_magics(roster.get("models") or [], sim=False)
  # Batch parent already materializes + save_roster once. Parallel book workers
  # must not rewrite live_roster.json (Windows WinError 32 file lock).
  if materialize:
    save_roster(live_rows, active_book=roster.get("active_book"))
    materialize_enabled(roster={"models": live_rows})
  sim_rows = assign_magics(live_rows, sim=True)
  book_sim = [
    r for r in sim_rows
    if r.get("enabled")
    and normalize_symbol(r.get("symbol")) == symbol
    and normalize_timeframe(r.get("timeframe")) == timeframe
  ]
  if not book_sim:
    raise SystemExit(f"No enabled models for {symbol} {timeframe}")
  bdir = bridge_dir(symbol, timeframe, sim=True)
  write_models_json(bdir, book_sim, base_magic=LIVE_SIM_MAGIC_BASE)
  return {
    "bridge_dir": bdir,
    "model_ids": [str(r["model_id"]) for r in book_sim],
    "rows": book_sim,
  }


def main() -> int:
  ap = argparse.ArgumentParser(description="Inline Linux Live OOS replay")
  ap.add_argument("--symbol", default="EURUSD")
  ap.add_argument("--timeframe", default="M15")
  ap.add_argument("--from", dest="date_from", required=True)
  ap.add_argument("--to", dest="date_to", required=True)
  ap.add_argument("--delay-ms", type=int, default=0)
  ap.add_argument("--parquet", type=Path, default=None)
  ap.add_argument("--seed", action="store_true")
  ap.add_argument("--progress-every", type=int, default=100)
  ap.add_argument(
    "--skip-materialize",
    action="store_true",
    help="Parent batch already materialized — avoid concurrent trade_models writes",
  )
  args = ap.parse_args()

  symbol = normalize_symbol(args.symbol)
  timeframe = normalize_timeframe(args.timeframe)
  if args.seed or not (
    RESULTS_DIR / "data" / f"mt5_{symbol.lower()}_{timeframe.lower()}.parquet"
  ).exists():
    parquet = _seed(symbol, timeframe, args.parquet)
  else:
    parquet = Path(args.parquet) if args.parquet else (
      RESULTS_DIR / "data" / f"mt5_{symbol.lower()}_{timeframe.lower()}.parquet"
    )

  prep = prepare_sim_book(symbol, timeframe, materialize=not args.skip_materialize)
  bdir: Path = prep["bridge_dir"]
  model_ids = prep["model_ids"]
  print(f"[inline] {symbol}/{timeframe} models={model_ids} dir={bdir}", flush=True)

  desk = bootstrap_host(symbol, timeframe, force=True)
  print(f"[inline] host={desk.name}", flush=True)

  import mt5_bridge.protocol as protocol
  from mt5_bridge.background import build_engines
  from mt5_bridge.protocol import write_model_decision
  from mt5_bridge.trade_journal import clear_trades, process_fill

  protocol.BRIDGE_SIM_DIR = bdir
  protocol.DEFAULT_MAGIC = int(LIVE_SIM_MAGIC_BASE)

  engines = build_engines(
    model_ids,
    risk_pct=1.0,
    bridge_dir=bdir,
    base_magic=int(LIVE_SIM_MAGIC_BASE),
  )
  for eng in engines.values():
    eng.ensure_history()
  primary = next(iter(engines.values()))
  primary_id = primary.model_id
  print(f"[inline] history bars={len(primary.load())} engines={list(engines.keys())}", flush=True)

  clear_replay_artifacts(bdir)
  clear_trades(bdir)
  # wipe leftover journals from prior runs
  for name in ("fills.jsonl", "ea_fills.jsonl", "trades.json"):
    p = bdir / name
    if p.exists():
      try:
        p.unlink()
      except OSError:
        pass
  df = load_ohlc(parquet, date_from=args.date_from, date_to=args.date_to)
  roster = prep["rows"]
  primary_magic = int(roster[0].get("magic") or LIVE_SIM_MAGIC_BASE)
  books = {
    mid: ReplayPaperBook(
      model_id=mid,
      magic=int(next(r["magic"] for r in roster if str(r["model_id"]) == mid)),
      symbol=symbol,
      period=timeframe,
    )
    for mid in model_ids
  }

  _write_sim_control(
    bdir,
    enabled=True,
    **{
      "from": args.date_from.replace("-", "."),
      "to": args.date_to.replace("-", "."),
      "delay_ms": int(args.delay_ms),
      "ea_status": "running",
      "bars_done": 0,
      "bars_total": len(df),
      "last_bar": "",
      "error": "",
      "source": "linux_replay_inline",
    },
  )
  _write_connection(bdir, symbol=symbol, period=timeframe, magic=primary_magic)

  n_fills = 0
  n_signals = 0
  sleep_sec = max(0.0, float(args.delay_ms) / 1000.0)
  t0 = time.time()
  every = max(1, int(args.progress_every))
  pending_meta: dict[str, dict] = {}

  for i, (ts, row) in enumerate(df.iterrows()):
    bt = mt5_bar_time(ts)
    # manage / open pending at this bar
    for mid, book in books.items():
      for fill in book.on_bar(
        open_=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        bar_time=bt,
      ):
        _emit_fill(bdir, fill)
        try:
          process_fill(
            fill,
            bridge_dir=bdir,
            decision=pending_meta.get(mid),
            model_id=mid,
          )
        except Exception as exc:
          print(f"[inline] process_fill warn: {exc}", flush=True)
        n_fills += 1

    bar = _write_bar(
      bdir, symbol=symbol, period=timeframe, magic=primary_magic, ts=ts, row=row,
    )

    # decide inline (same engine as Live)
    for mid, eng in engines.items():
      try:
        decision = eng.decide_for_bar(bar)
      except Exception as exc:
        decision = {
          "action": "FLAT",
          "bar_time": bt,
          "model_id": mid,
          "reason": f"decide_error:{exc}",
          "magic": eng.magic,
        }
      if not isinstance(decision, dict):
        continue
      decision.setdefault("model_id", mid)
      decision.setdefault("bar_time", bt)
      write_model_decision(
        decision,
        bridge_dir=bdir,
        mirror_primary=True,
        primary_model_id=primary_id,
      )
      action = str(decision.get("action") or "").upper()
      if action in ("BUY", "SELL"):
        n_signals += 1
        books[mid].queue_decision(decision)
        pending_meta[mid] = decision

    done = i + 1
    # Always refresh last_bar so UI progress is live; print less often.
    if done == 1 or done == len(df) or done % max(5, every // 5) == 0:
      _write_sim_control(
        bdir,
        ea_status="running",
        bars_done=done,
        bars_total=len(df),
        last_bar=bt,
        n_fills=n_fills,
        n_signals=n_signals,
      )
    if done == 1 or done == len(df) or done % every == 0:
      elapsed = time.time() - t0
      rate = done / max(elapsed, 1e-6)
      eta = (len(df) - done) / max(rate, 1e-6)
      print(
        f"[inline] {done}/{len(df)} bar={bt} fills={n_fills} signals={n_signals} "
        f"{rate:.1f} bar/s eta={eta/60:.1f}m",
        flush=True,
      )
    if sleep_sec:
      time.sleep(sleep_sec)

  _write_sim_control(
    bdir,
    enabled=False,
    ea_status="completed",
    bars_done=len(df),
    bars_total=len(df),
    n_fills=n_fills,
    n_signals=n_signals,
    error="",
  )
  elapsed = round(time.time() - t0, 2)
  summary = {
    "status": "completed",
    "mode": "inline",
    "bars_total": len(df),
    "n_fills": n_fills,
    "n_signals": n_signals,
    "elapsed_sec": elapsed,
    "bridge_dir": str(bdir),
    "symbol": symbol,
    "timeframe": timeframe,
    "date_from": args.date_from,
    "date_to": args.date_to,
    "models": model_ids,
    "updated_at": _now(),
  }
  # Per-book summary only (shared replay_last.json races under parallel books)
  out_book = RESULTS_DIR / f"replay_last_{symbol.lower()}_{timeframe.lower()}.json"
  out_book.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  print(json.dumps(summary, indent=2), flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
