#!/usr/bin/env python3
"""Download EURUSD 15m data from Dukascopy."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from systemtrain.data.ingest import download_eurusd_15m_dukascopy, save_csv, save_parquet
from systemtrain.data.quality import check_quality


def main() -> int:
    parser = argparse.ArgumentParser(description="Download EURUSD 15m from Dukascopy")
    parser.add_argument("--years", type=int, default=3, help="Years of history (default: 3)")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/store",
        help="Output directory",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    def progress(start, end, done, total):
        print(f"  [{done}/{total}] {start.date()} -> {end.date()} ...", flush=True)

    print(f"Downloading EURUSD 15m — last {args.years} years from Dukascopy (UTC)...")
    df = download_eurusd_15m_dukascopy(years=args.years, on_progress=progress)

    parquet_path = save_parquet(df, out_dir / "eurusd_15m.parquet")
    csv_path = save_csv(df, out_dir / "eurusd_15m.csv")
    quality = check_quality(df)

    print(f"\nDone.")
    print(f"  Bars     : {len(df):,}")
    print(f"  From     : {df.index.min()}")
    print(f"  To       : {df.index.max()}")
    print(f"  Parquet  : {parquet_path}")
    print(f"  CSV      : {csv_path}")
    print(f"  Quality  : {'OK' if quality['ok'] else quality['issues']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
