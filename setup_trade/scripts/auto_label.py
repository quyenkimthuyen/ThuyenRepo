#!/usr/bin/env python3
"""Auto-label gate-pass signals trên label period (Phase 4)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.research.label_scan import auto_label_period, label_status  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="train_2022")
    parser.add_argument("--max", type=int, default=50)
    parser.add_argument("--status-only", action="store_true")
    args = parser.parse_args()

    if args.status_only:
        print(json.dumps(label_status(args.period), indent=2))
        return

    result = auto_label_period(args.period, max_add=args.max)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
