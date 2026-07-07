#!/usr/bin/env python3
"""Download EURUSD H1 from Dukascopy (2022-01-01 → now) and save CSV."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "eurusd_h1.csv"


def month_ranges(start: datetime, end: datetime):
    cursor = datetime(start.year, start.month, 1, tzinfo=timezone.utc)
    while cursor < end:
        if cursor.month == 12:
            nxt = datetime(cursor.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            nxt = datetime(cursor.year, cursor.month + 1, 1, tzinfo=timezone.utc)
        chunk_start = max(cursor, start)
        chunk_end = min(nxt, end)
        if chunk_start < chunk_end:
            yield chunk_start, chunk_end
        cursor = nxt


def fetch_dukascopy(start: datetime, end: datetime) -> pd.DataFrame:
    try:
        import dukascopy_python as d
    except ImportError:
        print("pip install dukascopy-python", file=sys.stderr)
        sys.exit(1)

    frames = []
    for chunk_start, chunk_end in month_ranges(start, end):
        label = chunk_start.strftime("%Y-%m")
        print(f"  Fetching {label}...", flush=True)
        df = d.fetch("EUR/USD", d.INTERVAL_HOUR_1, d.OFFER_SIDE_BID, chunk_start, chunk_end)
        if df is not None and len(df) > 0:
            frames.append(df)

    if not frames:
        raise RuntimeError("No data returned from Dukascopy")

    merged = pd.concat(frames)
    merged = merged[~merged.index.duplicated(keep="last")]
    merged.sort_index(inplace=True)
    merged.index = merged.index.tz_convert("UTC") if merged.index.tz else merged.index.tz_localize("UTC")
    return merged


def merge_forex_json(path: Path, df: pd.DataFrame) -> pd.DataFrame:
    """Merge candles from sibling Forex project if available."""
    if not path.exists():
        return df
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for c in payload.get("candles", []):
        ts = pd.Timestamp(c["timestamp"], unit="ms", tz="UTC")
        rows.append(
            {
                "datetime": ts,
                "open": c["open"],
                "high": c["high"],
                "low": c["low"],
                "close": c["close"],
                "volume": c.get("volume", 0),
            }
        )
    extra = pd.DataFrame(rows).set_index("datetime")
    combined = pd.concat([df, extra])
    combined = combined[~combined.index.duplicated(keep="last")]
    combined.sort_index(inplace=True)
    return combined


def to_csv(df: pd.DataFrame, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    export = df.reset_index()
    export.columns = [c.lower() for c in export.columns]
    if "index" in export.columns:
        export = export.rename(columns={"index": "datetime"})
    export.to_csv(out, index=False)
    print(f"Saved {len(export)} rows → {out}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="date_from", default="2022-01-01")
    parser.add_argument("--to", dest="date_to", default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--merge-forex",
        type=Path,
        default=ROOT.parent / "Forex" / "data" / "defaults" / "EURUSD_H1.json",
    )
    args = parser.parse_args()

    start = datetime.fromisoformat(args.date_from).replace(tzinfo=timezone.utc)
    end = (
        datetime.fromisoformat(args.date_to).replace(tzinfo=timezone.utc)
        if args.date_to
        else datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    )

    print(f"EURUSD H1: {start.date()} → {end.date()}")
    df = fetch_dukascopy(start, end)
    df = merge_forex_json(args.merge_forex, df)
    to_csv(df, args.output)


if __name__ == "__main__":
    main()
