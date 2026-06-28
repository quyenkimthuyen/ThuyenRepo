#!/usr/bin/env python3
"""
Download default BTC/USD data from Dukascopy and save as gzipped JSON.

Timeframes: H4, D1, W

Usage:
  python3 scripts/fetch-default-data.py [--years 10] [--output data/defaults]
  python3 scripts/fetch-default-data.py --timeframes D1,W

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
    "BTCUSD": "BTC/USD",
}

PRICE_DECIMALS = {
    "BTCUSD": 2,
}

TIMEFRAMES = {
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


def df_to_candles(df, symbol: str) -> list:
    decimals = PRICE_DECIMALS.get(symbol, 2)
    candles = []
    for ts, row in df.iterrows():
        candles.append(
            {
                "timestamp": int(ts.timestamp() * 1000),
                "open": round(float(row["open"]), decimals),
                "high": round(float(row["high"]), decimals),
                "low": round(float(row["low"]), decimals),
                "close": round(float(row["close"]), decimals),
                "volume": round(float(row["volume"]), 2),
            }
        )
    return candles


def fetch_symbol_timeframe(symbol: str, timeframe: str, start: datetime, end: datetime) -> list:
    instrument = SYMBOLS[symbol]
    interval = TIMEFRAMES[timeframe]
    all_candles = []
    for chunk_start, chunk_end in month_ranges(start, end):
        df = d.fetch(
            instrument,
            interval,
            chunk_start,
            chunk_end,
            offer_side=d.OFFER_SIDE_BID,
        )
        if df is not None and not df.empty:
            all_candles.extend(df_to_candles(df, symbol))
    # Deduplicate by timestamp
    seen = set()
    unique = []
    for c in sorted(all_candles, key=lambda x: x["timestamp"]):
        if c["timestamp"] not in seen:
            seen.add(c["timestamp"])
            unique.append(c)
    return unique


def main():
    parser = argparse.ArgumentParser(description="Fetch BTCUSD default data")
    parser.add_argument("--years", type=int, default=10, help="Years of history")
    parser.add_argument("--output", type=Path, default=Path("data/defaults"))
    parser.add_argument("--timeframes", default="H4,D1,W", help="Comma-separated timeframes")
    args = parser.parse_args()

    end = datetime.utcnow()
    start = end - timedelta(days=args.years * 365)
    timeframes = [t.strip() for t in args.timeframes.split(",") if t.strip() in TIMEFRAMES]
    args.output.mkdir(parents=True, exist_ok=True)

    manifest_datasets = []
    for symbol in SYMBOLS:
        for tf in timeframes:
            print(f"Fetching {symbol} {tf}…")
            candles = fetch_symbol_timeframe(symbol, tf, start, end)
            out_name = f"{symbol}_{tf}.json.gz"
            out_path = args.output / out_name
            with gzip.open(out_path, "wt", encoding="utf-8") as f:
                json.dump({"symbol": symbol, "timeframe": tf, "candles": candles}, f)
            print(f"  → {len(candles)} candles → {out_path}")
            if candles:
                manifest_datasets.append({
                    "symbol": symbol,
                    "timeframe": tf,
                    "file": out_name,
                    "count": len(candles),
                    "firstTimestamp": candles[0]["timestamp"],
                    "lastTimestamp": candles[-1]["timestamp"],
                })

    manifest = {
        "source": "Dukascopy (bid, UTC)",
        "from": start.isoformat() + "Z",
        "to": end.isoformat() + "Z",
        "datasets": manifest_datasets,
    }
    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
