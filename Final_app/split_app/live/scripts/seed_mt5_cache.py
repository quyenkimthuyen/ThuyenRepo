#!/usr/bin/env python3
"""Copy lab desk OHLC parquet into Live cache so remine/replay need no MT5."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
FINAL = SPLIT.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))

from live_config import RESULTS_DIR  # noqa: E402
from runtime_host import normalize_symbol, normalize_timeframe, resolve_host_desk  # noqa: E402

DESK_DATA_CANDIDATES = (
  "data/mt5_{sym}_{tf}.parquet",
  "data/{sym}_{tf}.parquet",
  "results/data/mt5_{sym}_{tf}.parquet",
)


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def find_source(symbol: str, timeframe: str, src: Path | None = None) -> Path:
  if src:
    p = Path(src)
    if not p.exists():
      raise FileNotFoundError(p)
    return p
  sym = normalize_symbol(symbol).lower()
  tf = normalize_timeframe(timeframe).lower()
  desk = resolve_host_desk(symbol, timeframe)
  for tmpl in DESK_DATA_CANDIDATES:
    p = desk / tmpl.format(sym=sym, tf=tf)
    if p.exists():
      return p
  # Final_app sibling desks
  for desk2 in FINAL.glob("EdgeMiner*"):
    for tmpl in DESK_DATA_CANDIDATES:
      p = desk2 / tmpl.format(sym=sym, tf=tf)
      if p.exists():
        return p
  raise FileNotFoundError(
    f"No parquet for {symbol} {timeframe}. Pass --src PATH or place "
    f"mt5_{sym}_{tf}.parquet under the host desk data/."
  )


def seed(symbol: str, timeframe: str, *, src: Path | None = None) -> dict:
  symbol = normalize_symbol(symbol)
  timeframe = normalize_timeframe(timeframe)
  src_path = find_source(symbol, timeframe, src)
  data_dir = RESULTS_DIR / "data"
  data_dir.mkdir(parents=True, exist_ok=True)
  dest = data_dir / f"mt5_{symbol.lower()}_{timeframe.lower()}.parquet"
  meta = data_dir / f"mt5_{symbol.lower()}_{timeframe.lower()}_meta.json"
  shutil.copy2(src_path, dest)
  payload = {
    "updated_at": _now(),
    "symbol": symbol,
    "timeframe": timeframe,
    "source": str(src_path),
    "dest": str(dest),
    "bytes": dest.stat().st_size,
  }
  try:
    import hashlib
    h = hashlib.sha256()
    with open(dest, "rb") as f:
      for chunk in iter(lambda: f.read(1024 * 1024), b""):
        h.update(chunk)
    payload["sha256"] = h.hexdigest()
    import pandas as pd
    df = pd.read_parquet(dest)
    payload["bars"] = int(len(df))
    payload["start"] = str(df.index.min()) if hasattr(df.index, "min") else None
    payload["end"] = str(df.index.max()) if hasattr(df.index, "max") else None
  except Exception as exc:
    payload["meta_error"] = str(exc)
  meta.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
  return payload


def main() -> int:
  ap = argparse.ArgumentParser(description="Seed Live MT5 parquet cache from lab desk")
  ap.add_argument("--symbol", default="EURUSD")
  ap.add_argument("--timeframe", default="M15")
  ap.add_argument("--src", type=Path, default=None)
  ap.add_argument("--all-enabled", action="store_true", help="Seed every enabled roster book")
  args = ap.parse_args()

  if args.all_enabled:
    from package_store import load_roster
    from books import group_models_by_book

    roster = load_roster()
    enabled = [r for r in (roster.get("models") or []) if r.get("enabled")]
    groups = group_models_by_book(enabled)
    if not groups:
      print("No enabled models")
      return 1
    for (sym, tf), _ in groups.items():
      info = seed(sym, tf)
      print(f"OK {sym} {tf} ← {info['source']} ({info['bytes']} bytes)")
    return 0

  info = seed(args.symbol, args.timeframe, src=args.src)
  print(json.dumps(info, indent=2))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
