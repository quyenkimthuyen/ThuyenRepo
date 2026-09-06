#!/usr/bin/env python3
"""Replace Live roster with 12 models from backtest + backtestM5 desks.

Per desk: Balance, bestWR, bestTotalR (labels forced). Source desks:
  backtest/EdgeMinerEURUSDM15, EdgeMinerGBPUSDM15
  backtestM5/EdgeMinerEURUSDM5, EdgeMinerGBPUSDM5
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO = Path(r"C:\Work\ThuyenRepo")
SPLIT = REPO / "Final_app" / "split_app"
LIVE = SPLIT / "live"
sys.path.insert(0, str(SPLIT))
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT / "lab"))

from export_trade_package import DESK_META, export_one, load_models  # noqa: E402
from import_trade_package import import_one  # noqa: E402
from live_config import INSTALLED_DIR  # noqa: E402
from magic_allocator import assign_magics  # noqa: E402
from package_store import default_roster_from_installed, save_roster  # noqa: E402

# (root_dir, desk_folder, [(live_label, model_id), ...])
PICKS: list[tuple[Path, str, list[tuple[str, str]]]] = [
  (
    REPO / "backtest",
    "EdgeMinerEURUSDM15",
    [
      ("Balance", "tm_breakthrough_elite_60_3_vwap_c1ad2c33"),
      ("bestWR", "tm_h_c_3_tu_n_h_c_2025-2026-6th_f574b07e"),
      ("bestTotalR", "tm_breakthrough_anti_chase_fixe_bdedbc09"),
    ],
  ),
  (
    REPO / "backtest",
    "EdgeMinerGBPUSDM15",
    [
      ("Balance", "tm_gbpusd_wr60_alt_79_5r_wr60_d7b0f5ed"),
      ("bestWR", "tm_gbpusd_riskadj_79_7r_dd2_wr6_160c0c79"),
      ("bestTotalR", "tm_gbpusd_bestr_99_7r_wr53_6bcb3684"),
    ],
  ),
  (
    REPO / "backtestM5",
    "EdgeMinerEURUSDM5",
    [
      ("Balance", "tm_balance_49829f42"),
      ("bestWR", "tm_bestwinrate_61a3b401"),
      ("bestTotalR", "tm_bestbalance_2_fdca2f6b"),
    ],
  ),
  (
    REPO / "backtestM5",
    "EdgeMinerGBPUSDM5",
    [
      ("Balance", "tm_bestpf_f7e2ce53"),
      ("bestWR", "tm_bestquality_28e7e716"),
      ("bestTotalR", "tm_besttotalr_2d9abef9"),
    ],
  ),
]


def wipe_installed() -> int:
  n = 0
  INSTALLED_DIR.mkdir(parents=True, exist_ok=True)
  for p in list(INSTALLED_DIR.iterdir()):
    if p.name.startswith("_"):
      continue
    if p.is_dir():
      shutil.rmtree(p)
      n += 1
  save_roster([])
  print(f"Wiped {n} installed package(s) + empty roster", flush=True)
  return n


def main() -> int:
  out_dir = SPLIT / "packages_out" / "live12"
  if out_dir.exists():
    shutil.rmtree(out_dir)
  out_dir.mkdir(parents=True, exist_ok=True)

  wipe_installed()

  exported: list[Path] = []
  for root, desk_name, picks in PICKS:
    desk = root / desk_name
    if desk_name not in DESK_META:
      raise SystemExit(f"Unknown desk meta: {desk_name}")
    if not desk.exists():
      raise SystemExit(f"Missing desk: {desk}")
    by_id = {m.get("id"): m for m in load_models(desk)}
    print(f"\n=== {desk_name} @ {desk} ===", flush=True)
    for live_label, mid in picks:
      model = by_id.get(mid)
      if not model:
        raise SystemExit(f"{desk_name}: model {mid} not found for {live_label}")
      src_label = model.get("label")
      print(
        f"  pick {live_label} <- {src_label!r} ({mid}) "
        f"R={model.get('total_r')} WR={model.get('win_rate_pct')} PF={model.get('profit_factor')}",
        flush=True,
      )
      path = export_one(
        desk_name,
        model,
        out_dir,
        ensure_sched=False,
        desk_path=desk,
        label_override=live_label,
      )
      exported.append(path)
      print(f"  OK → {path.name}", flush=True)

  print(f"\nImporting {len(exported)} packages…", flush=True)
  for pkg in exported:
    dest = import_one(pkg)
    print(f"  installed {dest.name}", flush=True)

  rows = assign_magics(default_roster_from_installed())
  save_roster(rows)
  enabled = [r for r in rows if r.get("enabled")]
  print(f"\nRoster: {len(enabled)} On / {len(rows)} total", flush=True)
  for r in sorted(enabled, key=lambda x: (x.get("symbol"), x.get("timeframe"), x.get("label"))):
    print(
      f"  {r.get('symbol')} {r.get('timeframe')} · {r.get('label')} "
      f"magic={r.get('magic')} ready={r.get('ready')}",
      flush=True,
    )
  if len(enabled) != 12:
    return 1
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
