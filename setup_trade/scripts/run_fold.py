#!/usr/bin/env python3
"""Walk-forward fold runner — Phase 3/4 pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.research.fold import run_fold_step  # noqa: E402


STEPS = (
    "label_status",
    "auto_label",
    "analyze",
    "optimize",
    "final_backtest",
    "full_pipeline",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", default="fold_a")
    parser.add_argument("--step", choices=STEPS, default="full_pipeline")
    parser.add_argument("--max-add", type=int, default=50)
    parser.add_argument("--method", default="greedy")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()

    result = run_fold_step(
        args.fold,
        args.step,
        max_add=args.max_add,
        method=args.method,
        save_best=not args.no_save,
        apply_disable=args.step in ("analyze", "full_pipeline"),
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
