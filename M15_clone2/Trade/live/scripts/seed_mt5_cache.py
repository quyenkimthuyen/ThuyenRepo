#!/usr/bin/env python3
"""Bootstrap Live OHLC parquet.

Live's source of truth is the EA bridge (bars.json + history_sync), not Train.
Default seed:
  1. Keep an existing Live parquet (do not clobber with lab history).
  2. Else build parquet from Trade ``mt5/bridge_live_*/bars.json``.

Lab copy is opt-in for Replay / schedule-parity:
  ``--src PATH`` or ``--allow-lab``.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

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
MIN_LIVE_BARS = 32
BROKER_TIMEZONE = os.environ.get("EDGEMINER_BROKER_TIMEZONE", "Europe/Helsinki")
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


def cache_path(symbol: str, timeframe: str) -> Path:
  symbol = normalize_symbol(symbol)
  timeframe = normalize_timeframe(timeframe)
  return RESULTS_DIR / "data" / f"mt5_{symbol.lower()}_{timeframe.lower()}.parquet"


def live_bars_json_path(symbol: str, timeframe: str) -> Path:
  from books import bridge_dir
  return bridge_dir(symbol, timeframe, sim=False) / "bars.json"


def train_runtime_candidates(symbol: str, timeframe: str) -> list[Path]:
  """Lab TrainApp parquet (Replay / --allow-lab only)."""
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


def find_lab_source(symbol: str, timeframe: str, src: Path | None = None) -> Path:
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
  for root in (FINAL, FINAL.parent / "backtest", FINAL.parent / "backtestM5"):
    if not root.exists():
      continue
    for desk2 in root.glob("EdgeMiner*"):
      for tmpl in DESK_DATA_CANDIDATES:
        candidates.append(desk2 / tmpl.format(sym=sym, tf=tf))
  good = [p for p in candidates if _looks_like_parquet(p)]
  if not good:
    raise FileNotFoundError(
      f"No lab parquet for {symbol} {timeframe}. Pass --src PATH."
    )
  return max(good, key=lambda p: p.stat().st_size)


def find_source(symbol: str, timeframe: str, src: Path | None = None) -> Path:
  """Back-compat alias: explicit --src or lab search (callers that want lab)."""
  return find_lab_source(symbol, timeframe, src)


def _parse_broker_time(value):
  import pandas as pd
  ts = pd.Timestamp(value)
  if ts.tzinfo is None:
    ts = ts.tz_localize(
      ZoneInfo(BROKER_TIMEZONE), ambiguous=True, nonexistent="shift_forward",
    )
  return ts.tz_convert("UTC").tz_localize(None)


def bars_json_to_frame(path: Path):
  import pandas as pd
  data = json.loads(path.read_text(encoding="utf-8"))
  bars = data.get("bars") if isinstance(data, dict) else data
  if not isinstance(bars, list):
    raise ValueError(f"No bars list in {path}")
  rows: list[dict] = []
  index: list = []
  for bar in bars:
    if not isinstance(bar, dict):
      continue
    try:
      index.append(_parse_broker_time(bar.get("time") or bar.get("bar_time")))
      rows.append({
        "Open": float(bar["open"]),
        "High": float(bar["high"]),
        "Low": float(bar["low"]),
        "Close": float(bar["close"]),
        "Volume": float(bar.get("volume") or bar.get("tick_volume") or 0),
        "SpreadPoints": float(bar.get("spread_points") or 0),
      })
    except (KeyError, TypeError, ValueError):
      continue
  if len(rows) < MIN_LIVE_BARS:
    raise ValueError(
      f"{path} has {len(rows)} usable bars; need >= {MIN_LIVE_BARS}"
    )
  frame = pd.DataFrame(rows, index=pd.DatetimeIndex(index))
  frame = frame.sort_index()
  return frame[~frame.index.duplicated(keep="last")]


def _payload_for_dest(dest: Path, *, source: str, kind: str) -> dict:
  payload = {
    "updated_at": _now(),
    "source": source,
    "source_kind": kind,
    "dest": str(dest),
    "bytes": dest.stat().st_size if dest.exists() else 0,
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
  return payload


def _write_meta(dest: Path, payload: dict) -> None:
  meta = dest.with_name(dest.stem + "_meta.json")
  meta.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _copy_parquet(src_path: Path, dest: Path, *, kind: str) -> dict:
  dest.parent.mkdir(parents=True, exist_ok=True)
  shutil.copy2(src_path, dest)
  payload = _payload_for_dest(dest, source=str(src_path), kind=kind)
  payload["symbol"] = payload.get("symbol")
  _write_meta(dest, payload)
  return payload


def seed(
  symbol: str,
  timeframe: str,
  *,
  src: Path | None = None,
  allow_lab: bool = False,
  force: bool = False,
) -> dict:
  symbol = normalize_symbol(symbol)
  timeframe = normalize_timeframe(timeframe)
  dest = cache_path(symbol, timeframe)
  dest.parent.mkdir(parents=True, exist_ok=True)

  if src is not None:
    src_path = find_lab_source(symbol, timeframe, src)
    payload = _copy_parquet(src_path, dest, kind="explicit_src")
    payload["symbol"] = symbol
    payload["timeframe"] = timeframe
    _write_meta(dest, payload)
    return payload

  if dest.exists() and _looks_like_parquet(dest) and not force:
    payload = _payload_for_dest(dest, source=str(dest), kind="existing_live")
    payload["symbol"] = symbol
    payload["timeframe"] = timeframe
    payload["reused"] = True
    return payload

  bars_path = live_bars_json_path(symbol, timeframe)
  if bars_path.is_file():
    frame = bars_json_to_frame(bars_path)
    tmp = dest.with_suffix(".parquet.tmp")
    frame.to_parquet(tmp)
    tmp.replace(dest)
    payload = _payload_for_dest(dest, source=str(bars_path), kind="live_bars_json")
    payload["symbol"] = symbol
    payload["timeframe"] = timeframe
    _write_meta(dest, payload)
    return payload

  if allow_lab:
    src_path = find_lab_source(symbol, timeframe)
    payload = _copy_parquet(src_path, dest, kind="lab")
    payload["symbol"] = symbol
    payload["timeframe"] = timeframe
    _write_meta(dest, payload)
    return payload

  raise FileNotFoundError(
    f"No Live OHLC for {symbol} {timeframe}. "
    f"Start the EA so it writes {bars_path}, then history_sync fills the cache. "
    f"For Replay · Live-like only: pass --src PATH or --allow-lab."
  )


def main() -> int:
  ap = argparse.ArgumentParser(
    description="Seed Live MT5 parquet from EA bars.json (default) or lab parquet",
  )
  ap.add_argument("--symbol", default="EURUSD")
  ap.add_argument("--timeframe", default="M15")
  ap.add_argument("--src", type=Path, default=None, help="Copy this parquet (lab/replay)")
  ap.add_argument(
    "--allow-lab",
    action="store_true",
    help="If Live bars.json is missing, copy Train/EdgeMiner parquet",
  )
  ap.add_argument(
    "--force",
    action="store_true",
    help="Rebuild even when Live parquet already exists",
  )
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
      info = seed(
        sym, tf, src=args.src, allow_lab=args.allow_lab, force=args.force,
      )
      print(f"OK {sym} {tf} ← {info['source']} ({info.get('bytes')} bytes)")
    return 0

  info = seed(
    args.symbol, args.timeframe,
    src=args.src, allow_lab=args.allow_lab, force=args.force,
  )
  print(json.dumps(info, indent=2))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
