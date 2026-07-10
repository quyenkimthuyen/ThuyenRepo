#!/usr/bin/env python3
"""Curate train setups and bar tags to ~50 high-quality labels per year."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.setup_quality import apply_curation, curate_train_setups


def main() -> None:
    parser = argparse.ArgumentParser(description="Curate EURUSD train labels")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not write files")
    parser.add_argument("--preview", action="store_true", help="Show selection stats")
    args = parser.parse_args()

    if args.preview or args.dry_run:
        preview = curate_train_setups()
        stats = preview["stats"]
        print(json.dumps(stats, indent=2))
        if args.dry_run:
            print("\n[dry-run] Không ghi file.")
            return

    report = apply_curation(dry_run=args.dry_run)
    print("Curation complete:")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
