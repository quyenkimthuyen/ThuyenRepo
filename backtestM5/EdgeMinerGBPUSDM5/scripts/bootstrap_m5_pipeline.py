"""Bootstrap M5 desk data via MetaTrader5 API, then optionally run KB+grid.

Usage:
  py -3 scripts/bootstrap_m5_pipeline.py              # data only
  py -3 scripts/bootstrap_m5_pipeline.py --run-pipeline
  py -3 scripts/bootstrap_m5_pipeline.py --run-pipeline --promote-top 3
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BROKER_TZ = ZoneInfo("Europe/Helsinki")


def _now_iso() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _detect_symbol() -> str:
  from mt5_bridge.protocol import INSTANCE_ID
  if INSTANCE_ID.upper().startswith("M5G") or "GBP" in ROOT.name.upper():
    return "GBPUSD"
  return "EURUSD"


def _cache_paths(symbol: str) -> tuple[Path, Path]:
  from mt5_bridge.history_sync import MT5_CACHE_PATH, MT5_META_PATH
  # Prefer protocol paths (already M5-named per desk)
  return MT5_CACHE_PATH, MT5_META_PATH


def pull_m5_ohlc(symbol: str, *, date_from: str = "2025-01-01") -> pd.DataFrame:
  import MetaTrader5 as mt5

  if not mt5.initialize():
    raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
  try:
    info = mt5.account_info()
    # Pull in chunks from date_from to now
    start = pd.Timestamp(date_from, tz=BROKER_TZ)
    end = pd.Timestamp.now(tz=BROKER_TZ)
    # API: treat returned unix as broker wall-clock (XM quirk), then → UTC naive
    chunks: list[pd.DataFrame] = []
    cursor = start
    step = pd.Timedelta(days=30)
    while cursor < end:
      chunk_end = min(cursor + step, end)
      rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_M5,
        cursor.to_pydatetime(),
        chunk_end.to_pydatetime(),
      )
      if rates is not None and len(rates) > 0:
        df = pd.DataFrame(rates)
        ts = pd.to_datetime(df["time"], unit="s")
        ts = (
          ts.dt.tz_localize(BROKER_TZ, ambiguous=True, nonexistent="shift_forward")
          .dt.tz_convert("UTC")
          .dt.tz_localize(None)
        )
        out = pd.DataFrame(
          {
            "Open": df["open"].astype(float).values,
            "High": df["high"].astype(float).values,
            "Low": df["low"].astype(float).values,
            "Close": df["close"].astype(float).values,
            "Volume": df["tick_volume"].astype(float).values,
          },
          index=ts,
        )
        chunks.append(out)
        print(f"  {symbol} {cursor.date()}→{chunk_end.date()}: {len(out)} bars", flush=True)
      cursor = chunk_end
    if not chunks:
      raise RuntimeError(f"No M5 rates for {symbol}: {mt5.last_error()}")
    frame = pd.concat(chunks).sort_index()
    frame = frame[~frame.index.duplicated(keep="last")].dropna()
    # Drop forming bar (last incomplete)
    if len(frame) > 1:
      frame = frame.iloc[:-1]
    meta_src = {
      "server": getattr(info, "server", None) if info else None,
      "account": getattr(info, "login", None) if info else None,
      "symbol": symbol,
    }
    return frame, meta_src
  finally:
    mt5.shutdown()


def write_cache(frame: pd.DataFrame, meta_src: dict, cache_path: Path, meta_path: Path) -> None:
  from mt5_bridge.protocol import atomic_write_json, safe_replace

  cache_path.parent.mkdir(parents=True, exist_ok=True)
  tmp = cache_path.with_suffix(".parquet.tmp")
  frame.to_parquet(tmp)
  safe_replace(tmp, cache_path)
  diffs = frame.index.to_series().diff().dropna()
  gaps = int(((diffs > pd.Timedelta(minutes=5)) & (diffs < pd.Timedelta(hours=48))).sum())
  fingerprint = hashlib.sha256(
    pd.util.hash_pandas_object(frame, index=True).values.tobytes(),
  ).hexdigest()
  atomic_write_json(meta_path, {
    # Gates in trade_model/engine expect mt5_ea; API pull is still provenance.
    "source": "mt5_ea",
    "sync_method": "mt5_api",
    "broker": meta_src.get("server") or meta_src.get("broker"),
    "account": meta_src.get("account"),
    "pair": meta_src.get("symbol") or meta_src.get("pair"),
    "timeframe": "M5",
    "broker_timezone": "Europe/Helsinki",
    "bars": len(frame),
    "start": str(frame.index[0]) if len(frame) else None,
    "end": str(frame.index[-1]) if len(frame) else None,
    "gap_count": gaps,
    "fingerprint": fingerprint,
    "synced_at": _now_iso(),
  })
  print(f"  wrote {cache_path.name}: {len(frame)} bars  {frame.index[0]} → {frame.index[-1]}", flush=True)


def seed_app_settings() -> None:
  """Copy M15 settings eras/presets if M5 desk has none."""
  dst = ROOT / "results" / "app_settings.json"
  if dst.exists():
    print("  app_settings.json already present", flush=True)
    return
  # Prefer sibling M15 desk settings
  candidates = [
    Path(r"C:\Work\ThuyenRepo\backtest\EdgeMinerEURUSDM15\results\app_settings.json"),
    Path(r"C:\Work\ThuyenRepo\backtest\EdgeMinerGBPUSDM15\results\app_settings.json"),
  ]
  if "GBP" in ROOT.name.upper():
    candidates = list(reversed(candidates))
  src = next((p for p in candidates if p.exists()), None)
  dst.parent.mkdir(parents=True, exist_ok=True)
  if src:
    data = json.loads(src.read_text(encoding="utf-8"))
    data["updated_at"] = _now_iso()
    # Keep GBP spread if this is GBP desk
    if "GBP" in ROOT.name.upper():
      data["spread_pips"] = float(data.get("spread_pips") or 1.5)
      if data.get("spread_pips") == 1.0:
        data["spread_pips"] = 1.5
    dst.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  seeded app_settings from {src}", flush=True)
  else:
    from gui.app_settings import DEFAULT_SETTINGS, save_settings
    save_settings(dict(DEFAULT_SETTINGS))
    print("  wrote default app_settings", flush=True)


def run_pipeline() -> None:
  script = ROOT / "scripts" / "run_kb_then_grid.py"
  print(f"=== Running {script} ===", flush=True)
  subprocess.run([sys.executable, str(script)], cwd=str(ROOT), check=True)


def promote_top(n: int = 3) -> list[dict]:
  from gui.grid_search_engine import load_latest_grid_run
  from gui.trade_model import create_trade_model

  run = load_latest_grid_run()
  if not run:
    print("  no grid run to promote", flush=True)
    return []
  rows = [r for r in (run.get("rows") or []) if not r.get("error")]
  rows = sorted(rows, key=lambda r: float(r.get("total_r") or -1e9), reverse=True)
  created = []
  labels = ["BestTotalR", "BestWinRate", "Balance"]
  # pick diversified: best total_r, best win_rate, best risk_adjusted if present
  picks: list[tuple[str, dict]] = []
  if rows:
    picks.append((labels[0], rows[0]))
  by_wr = sorted(rows, key=lambda r: float(r.get("win_rate_pct") or 0), reverse=True)
  if by_wr and by_wr[0] not in [p[1] for p in picks]:
    picks.append((labels[1], by_wr[0]))
  by_ra = sorted(
    rows,
    key=lambda r: float(r.get("risk_adjusted") or r.get("score") or r.get("total_r") or -1e9),
    reverse=True,
  )
  for row in by_ra:
    if row not in [p[1] for p in picks]:
      picks.append((labels[2] if len(picks) == 2 else f"Top{len(picks)+1}", row))
      break
  for label, row in picks[:n]:
    m = create_trade_model(row, run_id=run.get("run_id"), label=label, set_active=(len(created) == 0))
    created.append(m)
    print(f"  Trade Model {m.get('id')} · {m.get('label')} · {m.get('total_r')}R", flush=True)
  return created


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--run-pipeline", action="store_true")
  ap.add_argument("--promote-top", type=int, default=0)
  ap.add_argument("--from-date", default="2025-01-01")
  args = ap.parse_args()

  symbol = _detect_symbol()
  cache_path, meta_path = _cache_paths(symbol)
  print(f"Desk {ROOT.name} · symbol {symbol}", flush=True)
  print("=== Pull M5 history via MT5 API ===", flush=True)
  frame, meta_src = pull_m5_ohlc(symbol, date_from=args.from_date)
  write_cache(frame, meta_src, cache_path, meta_path)
  seed_app_settings()

  if args.run_pipeline:
    run_pipeline()
  if args.promote_top > 0:
    promote_top(args.promote_top)
  print("=== DONE ===", flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
