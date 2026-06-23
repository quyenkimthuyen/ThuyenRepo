#!/usr/bin/env python3
"""
Download default forex data (EURUSD, GBPUSD) from Dukascopy and save as gzipped JSON.

Timeframes: H1, H4, D1, W

Usage:
  python3 scripts/fetch-default-data.py [--years 3] [--output data/defaults]
  python3 scripts/fetch-default-data.py --timeframes H4,D1,W   # skip H1

Requires: pip install dukascopy-python
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import dukascopy_python as d
except ImportError:
    print("Install dependency: pip install dukascopy-python", file=sys.stderr)
    sys.exit(1)

SYMBOLS = {
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
}

TIMEFRAMES = {
    "H1": d.INTERVAL_HOUR_1,
    "H4": d.INTERVAL_HOUR_4,
    "D1": d.INTERVAL_DAY_1,
    "W": d.INTERVAL_WEEK_1,
}


def month_ranges(start: datetime, end: datetime):
    """Yield (chunk_start, chunk_end) pairs by calendar month."""
    cursor = datetime(start.year, start.month, 1)
    while cursor < end:
        if cursor.month == 12:
            nxt = datetime(cursor.year + 1, 1, 1)
        else:
            nxt = datetime(cursor.year, cursor.month + 1, 1)
        chunk_start = max(cursor, start)
        chunk_end = min(nxt, end)
        if chunk_start < chunk_end:
            yield chunk_start, chunk_end
        cursor = nxt


def df_to_candles(df) -> list:
    candles = []
    for ts, row in df.iterrows():
        candles.append(
            {
                "timestamp": int(ts.timestamp() * 1000),
                "open": round(float(row["open"]), 5),
                "high": round(float(row["high"]), 5),
                "low": round(float(row["low"]), 5),
                "close": round(float(row["close"]), 5),
                "volume": round(float(row["volume"]), 2),
            }
        )
    return candles


def fetch_timeframe(symbol: str, instrument: str, timeframe: str, interval, start: datetime, end: datetime):
    import pandas as pd

    frames = []
    if timeframe == "H1":
        for chunk_start, chunk_end in month_ranges(start, end):
            label = chunk_start.strftime("%Y-%m")
            print(f"  {symbol} {timeframe} {label} ...", flush=True)
            df = d.fetch(instrument, interval, d.OFFER_SIDE_BID, chunk_start, chunk_end)
            if df is not None and len(df) > 0:
                frames.append(df)
    else:
        print(f"  {symbol} {timeframe} ...", flush=True)
        df = d.fetch(instrument, interval, d.OFFER_SIDE_BID, start, end)
        if df is not None and len(df) > 0:
            frames.append(df)

    if not frames:
        return []

    merged = pd.concat(frames)
    merged = merged[~merged.index.duplicated(keep="last")]
    merged.sort_index(inplace=True)
    return df_to_candles(merged)


def save_dataset(output_dir: Path, symbol: str, timeframe: str, candles: list) -> Path:
    payload = {"symbol": symbol, "timeframe": timeframe, "candles": candles}
    raw = json.dumps(payload, separators=(",", ":"))
    gz_out = output_dir / f"{symbol}_{timeframe}.json.gz"
    with gzip.open(gz_out, "wt", encoding="utf-8") as f:
        f.write(raw)
    plain_out = output_dir / f"{symbol}_{timeframe}.json"
    plain_out.write_text(raw, encoding="utf-8")
    return gz_out


def main():
    parser = argparse.ArgumentParser(description="Fetch default PARL forex data from Dukascopy")
    parser.add_argument("--years", type=int, default=3, help="Years of history (default: 3)")
    parser.add_argument("--output", type=Path, default=Path("data/defaults"))
    parser.add_argument(
        "--timeframes",
        type=str,
        default=",".join(TIMEFRAMES.keys()),
        help="Comma-separated timeframes (default: H1,H4,D1,W)",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=",".join(SYMBOLS.keys()),
        help="Comma-separated symbols (default: EURUSD,GBPUSD)",
    )
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    for sym in symbols:
        if sym not in SYMBOLS:
            print(f"Unknown symbol: {sym}. Supported: {', '.join(SYMBOLS)}", file=sys.stderr)
            sys.exit(1)

    timeframes = [tf.strip().upper() for tf in args.timeframes.split(",") if tf.strip()]
    for tf in timeframes:
        if tf not in TIMEFRAMES:
            print(f"Unknown timeframe: {tf}. Supported: {', '.join(TIMEFRAMES)}", file=sys.stderr)
            sys.exit(1)

    end = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=args.years * 365)

    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Range: {start.date()} → {end.date()} ({args.years}y)")
    print(f"Timeframes: {', '.join(timeframes)}")

    manifest = {
        "source": "Dukascopy (bid, UTC)",
        "from": start.isoformat() + "Z",
        "to": end.isoformat() + "Z",
        "datasets": [],
    }

    for symbol in symbols:
        instrument = SYMBOLS[symbol]
        print(f"Fetching {symbol} ...")
        for timeframe in timeframes:
            candles = fetch_timeframe(symbol, instrument, timeframe, TIMEFRAMES[timeframe], start, end)
            if not candles:
                print(f"ERROR: no candles for {symbol} {timeframe}", file=sys.stderr)
                sys.exit(1)
            out = save_dataset(output_dir, symbol, timeframe, candles)
            size_kb = out.stat().st_size / 1024
            print(f"  → {out.name} ({len(candles)} candles, {size_kb:.1f} KB)")
            manifest["datasets"].append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "file": out.name,
                    "count": len(candles),
                    "firstTimestamp": candles[0]["timestamp"],
                    "lastTimestamp": candles[-1]["timestamp"],
                }
            )

    manifest_path = output_dir / "manifest.json"
    existing = []
    if manifest_path.exists():
        try:
            prev = json.loads(manifest_path.read_text(encoding="utf-8"))
            keep_tfs = set(timeframes)
            keep_syms = set(symbols)
            existing = [
                ds for ds in prev.get("datasets", [])
                if ds.get("timeframe") not in keep_tfs or ds.get("symbol") not in keep_syms
            ]
        except (json.JSONDecodeError, OSError):
            existing = []

    merged = existing + manifest["datasets"]
    order = {"H1": 0, "H4": 1, "D1": 2, "W": 3}
    merged.sort(key=lambda ds: (ds.get("symbol", ""), order.get(ds.get("timeframe", ""), 9)))
    manifest["datasets"] = merged

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest: {manifest_path} ({len(manifest['datasets'])} datasets)")


if __name__ == "__main__":
    main()
