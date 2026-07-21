#!/usr/bin/env python3
"""Export Trade Model → MT5 Expert Advisor package."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from mt5_export.package import export_mt5_package


def main():
  p = argparse.ArgumentParser(description="Export ForexForge Trade Model to MT5 EA")
  p.add_argument("--model-id", help="Trade model ID (mặc định: active)")
  p.add_argument("--out", type=Path, help="Thư mục output (mặc định: mt5/output)")
  p.add_argument(
    "--no-remine",
    action="store_true",
    help="Dùng last_strategy từ report (không mine lại tuần hiện tại)",
  )
  args = p.parse_args()

  out = export_mt5_package(
    model_id=args.model_id,
    out_dir=args.out,
    remine=not args.no_remine,
  )
  print(f"Đã export MT5 EA → {out}")
  print("Copy thư mục này vào MT5: MQL5/Experts/ForexForgeEA/")
  print("Compile ForexForgeEA.mq5 trong MetaEditor, gắn lên chart GBPUSD H1.")


if __name__ == "__main__":
  main()
