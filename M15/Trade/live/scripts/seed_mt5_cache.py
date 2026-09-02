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
MIN_PARQUET_BYTES = 1024
TRAIN_DESK_BY_BOOK = {
  ("EURUSD", "M15"): "e21",
  ("GBPUSD", "M15"): "g23",
  ("EURUSD", "M5"): "e21",
  ("GBPUSD", "M5"): "g23",
}


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _looks_like_parquet(path: Path) -> bool:
  try:
    if not path.is_file() or path.stat().st_size < MIN_PARQUET_BYTES:
      return False
    with path.open("rb") as f:
      head = f.read(4)
      f.seek(-4, 2)
      tail = f.read(4)
    return head == b"PAR1" and tail == b"PAR1"
  except OSError:
    return False


def train_runtime_candidates(symbol: str, timeframe: str) -> list[Path]:
  """TrainApp runtime parquet: e21 EUR / g23 GBP under Train/runtime/<desk>/data."""
  sym = normalize_symbol(symbol)
  tf = normalize_timeframe(timeframe)
  name = f"mt5_{sym.lower()}_{tf.lower()}.parquet"
  desk_id = TRAIN_DESK_BY_BOOK.get((sym, tf))
  roots = [FINAL / "Train"]
  parent = FINAL.parent
  for extra in (
    parent / "LiveCheck2" / "Train",
    parent / "LiveCheck" / "TrainApp2",
    parent / "M15" / "Train",
  ):
    if extra not in roots:
      roots.append(extra)
  out: list[Path] = []
  seen: set[str] = set()

  def _add(path: Path) -> None:
    key = str(path)
    if key in seen:
      return
    seen.add(key)
    out.append(path)

  if desk_id:
    for root in roots:
      _add(root / "runtime" / desk_id / "data" / name)
  for root in roots:
    runtime = root / "runtime"
    if not runtime.is_dir():
      continue
    for path in runtime.glob(f"*/data/{name}"):
      _add(path)
  return out


def find_source(symbol: str, timeframe: str, src: Path | None = None) -> Path:
  if src:
    p = Path(src)
    if not p.exists():
      raise FileNotFoundError(p)
    if not _looks_like_parquet(p):
      raise ValueError(f"Not a readable parquet: {p} ({p.stat().st_size} bytes)")
    return p
  sym = normalize_symbol(symbol).lower()
  tf = normalize_timeframe(timeframe).lower()
  candidates: list[Path] = []
  try:
    desk = resolve_host_desk(symbol, timeframe)
    for tmpl in DESK_DATA_CANDIDATES:
      candidates.append(desk / tmpl.format(sym=sym, tf=tf))
  except (FileNotFoundError, ValueError):
    pass
  candidates.extend(train_runtime_candidates(symbol, timeframe))
  # Final_app sibling desks + nearby backtest trees
  for root in (FINAL, FINAL.parent / "backtest", FINAL.parent / "backtestM5"):
    if not root.exists():
      continue
    for desk2 in root.glob("EdgeMiner*"):
      for tmpl in DESK_DATA_CANDIDATES:
        candidates.append(desk2 / tmpl.format(sym=sym, tf=tf))
  good = [p for p in candidates if _looks_like_parquet(p)]
  if not good:
    raise FileNotFoundError(
      f"No readable parquet for {symbol} {timeframe}. Pass --src PATH or place "
      f"mt5_{sym}_{tf}.parquet under Train/runtime/e21|g23/data/."
    )
  # Prefer largest (usually longest history)
  return max(good, key=lambda p: p.stat().st_size)


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
