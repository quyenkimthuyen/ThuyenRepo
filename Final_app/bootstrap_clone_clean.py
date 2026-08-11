#!/usr/bin/env python3
"""Clone 4 source desks into Final_app, clean train state, specialize IDs.

Sources:
  backtest/EdgeMinerEURUSDM15  → Final_app/EdgeMinerEURUSDM15  (M15F1)
  backtest/EdgeMinerGBPUSDM15  → Final_app/EdgeMinerGBPUSDM15  (M15F2)
  backtestM5/EdgeMinerEURUSDM5 → Final_app/EdgeMinerEURUSDM5   (M5F3)
  backtestM5/EdgeMinerGBPUSDM5 → Final_app/EdgeMinerGBPUSDM5   (M5F4)

Does NOT start training — use run_final_train.sh after this.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FINAL = REPO / "Final_app"
OOS_FROM, OOS_TO = "2026-01-01", "2026-08-07"

# Gap 20 between magic bases; ports reserved for Final_app only.
DESKS = [
  {
    "src": REPO / "backtest/EdgeMinerEURUSDM15",
    "dst_name": "EdgeMinerEURUSDM15",
    "instance": "M15F1",
    "tf": "M15",
    "symbol": "EUR",
    "app_port": 8511,
    "bridge_port": 9511,
    "sim_port": 9611,
    "compare_port": 9711,
    "magic_live": 20261501,
    "magic_sim": 20262501,
    "old_bridge": "bridge_m15e21",
    "old_bridge_sim": "bridge_sim_m15e21",
    "bridge": "bridge_m15f1",
    "bridge_sim": "bridge_sim_m15f1",
    "old_instance": "M15E21",
    "old_magic_live": 20261021,
    "old_magic_sim": 20262021,
    "ea_live": "ForgeBridgeM15E21.mq5",
    "ea_sim": "ForgeBridgeM15E21Sim.mq5",
    "ea_live_new": "ForgeBridgeM15F1.mq5",
    "ea_sim_new": "ForgeBridgeM15F1Sim.mq5",
    "spread": 1.0,
    "feature_profile_default": "current",
  },
  {
    "src": REPO / "backtest/EdgeMinerGBPUSDM15",
    "dst_name": "EdgeMinerGBPUSDM15",
    "instance": "M15F2",
    "tf": "M15",
    "symbol": "GBP",
    "app_port": 8521,
    "bridge_port": 9521,
    "sim_port": 9621,
    "compare_port": 9721,
    "magic_live": 20261521,
    "magic_sim": 20262521,
    "old_bridge": "bridge_m15g23",
    "old_bridge_sim": "bridge_sim_m15g23",
    "bridge": "bridge_m15f2",
    "bridge_sim": "bridge_sim_m15f2",
    "old_instance": "M15G23",
    "old_magic_live": 20261041,
    "old_magic_sim": 20262041,
    "ea_live": "ForgeBridgeM15G23.mq5",
    "ea_sim": "ForgeBridgeM15G23Sim.mq5",
    "ea_live_new": "ForgeBridgeM15F2.mq5",
    "ea_sim_new": "ForgeBridgeM15F2Sim.mq5",
    "spread": 1.5,
    "feature_profile_default": "current",
  },
  {
    "src": REPO / "backtestM5/EdgeMinerEURUSDM5",
    "dst_name": "EdgeMinerEURUSDM5",
    "instance": "M5F3",
    "tf": "M5",
    "symbol": "EUR",
    "app_port": 8531,
    "bridge_port": 9531,
    "sim_port": 9631,
    "compare_port": 9731,
    "magic_live": 20261541,
    "magic_sim": 20262541,
    "old_bridge": "bridge_m5e31",
    "old_bridge_sim": "bridge_sim_m5e31",
    "bridge": "bridge_m5f3",
    "bridge_sim": "bridge_sim_m5f3",
    "old_instance": "M5E31",
    "old_magic_live": 20261061,
    "old_magic_sim": 20262061,
    "ea_live": "ForgeBridgeM5E31.mq5",
    "ea_sim": "ForgeBridgeM5E31Sim.mq5",
    "ea_live_new": "ForgeBridgeM5F3.mq5",
    "ea_sim_new": "ForgeBridgeM5F3Sim.mq5",
    "spread": 1.0,
    "feature_profile_default": "m5_parity",
  },
  {
    "src": REPO / "backtestM5/EdgeMinerGBPUSDM5",
    "dst_name": "EdgeMinerGBPUSDM5",
    "instance": "M5F4",
    "tf": "M5",
    "symbol": "GBP",
    "app_port": 8541,
    "bridge_port": 9541,
    "sim_port": 9641,
    "compare_port": 9741,
    "magic_live": 20261561,
    "magic_sim": 20262561,
    "old_bridge": "bridge_m5g33",
    "old_bridge_sim": "bridge_sim_m5g33",
    "bridge": "bridge_m5f4",
    "bridge_sim": "bridge_sim_m5f4",
    "old_instance": "M5G33",
    "old_magic_live": 20261081,
    "old_magic_sim": 20262081,
    "ea_live": "ForgeBridgeM5G33.mq5",
    "ea_sim": "ForgeBridgeM5G33Sim.mq5",
    "ea_live_new": "ForgeBridgeM5F4.mq5",
    "ea_sim_new": "ForgeBridgeM5F4Sim.mq5",
    "spread": 1.5,
    "feature_profile_default": "m5_parity",
  },
]

RSYNC_EXCLUDES = [
  "--exclude=.venv",
  "--exclude=__pycache__",
  "--exclude=*.pyc",
  "--exclude=results",
  "--exclude=learning",
  "--exclude=archive",
  "--exclude=.pytest_cache",
  "--exclude=mt5/bridge*/trades.json",
  "--exclude=mt5/bridge*/fills",
  "--exclude=mt5/bridge*/decisions",
  "--exclude=mt5/bridge*/comm_log.jsonl",
  "--exclude=mt5/bridge*/history_status.json",
  "--exclude=mt5/bridge_sim*/trades.json",
  "--exclude=mt5/bridge_sim*/fills",
  "--exclude=mt5/bridge_sim*/decisions",
  "--exclude=mt5/bridge_sim*/comm_log.jsonl",
]


def log(msg: str) -> None:
  print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def rsync_clone(src: Path, dst: Path) -> None:
  if dst.exists():
    log(f"Remove existing {dst}")
    shutil.rmtree(dst)
  dst.parent.mkdir(parents=True, exist_ok=True)
  cmd = ["rsync", "-a", *RSYNC_EXCLUDES, f"{src}/", f"{dst}/"]
  subprocess.run(cmd, check=True)
  log(f"Cloned {src.name} → {dst}")


def symlink_data(src: Path, dst: Path) -> None:
  sdata, ddata = src / "data", dst / "data"
  if ddata.exists():
    shutil.rmtree(ddata)
  ddata.mkdir(parents=True)
  if not sdata.exists():
    log(f"WARN no data at {sdata}")
    return
  for f in sdata.iterdir():
    target = ddata / f.name
    if f.is_file():
      os.symlink(f.resolve(), target)
    elif f.is_dir():
      os.symlink(f.resolve(), target)
  log(f"Symlinked data/ from {src.name}")


def replace_in_file(path: Path, replacements: list[tuple[str, str]]) -> int:
  if not path.is_file():
    return 0
  try:
    text = path.read_text(encoding="utf-8")
  except Exception:
    return 0
  orig = text
  for a, b in replacements:
    text = text.replace(a, b)
  if text != orig:
    path.write_text(text, encoding="utf-8")
    return 1
  return 0


def specialize(dst: Path, cfg: dict) -> None:
  reps = [
    (cfg["old_instance"], cfg["instance"]),
    (cfg["old_bridge_sim"], cfg["bridge_sim"]),
    (cfg["old_bridge"], cfg["bridge"]),
    (str(cfg["old_magic_live"]), str(cfg["magic_live"])),
    (str(cfg["old_magic_sim"]), str(cfg["magic_sim"])),
  ]
  # Also catch pre-isolation magics if still present in comments
  for old in (20261023, 20261031, 20261033, 20262023, 20262031, 20262033):
    pass

  n = 0
  for path in dst.rglob("*"):
    if path.is_dir():
      continue
    if any(p in path.parts for p in (".git", "__pycache__", "data")):
      continue
    if path.suffix.lower() in {".parquet", ".png", ".jpg", ".ex5", ".ex4"}:
      continue
    n += replace_in_file(path, reps)
  log(f"  text replacements in {n} files")

  # Rename bridge dirs
  mt5 = dst / "mt5"
  for old, new in ((cfg["old_bridge"], cfg["bridge"]), (cfg["old_bridge_sim"], cfg["bridge_sim"])):
    op, np_ = mt5 / old, mt5 / new
    if op.exists() and not np_.exists():
      op.rename(np_)
      log(f"  renamed {old} → {new}")
    elif not np_.exists():
      np_.mkdir(parents=True, exist_ok=True)
      (np_ / "decisions").mkdir(exist_ok=True)
      log(f"  created {new}")

  # Rename EAs
  exp = mt5 / "Experts"
  for old, new in ((cfg["ea_live"], cfg["ea_live_new"]), (cfg["ea_sim"], cfg["ea_sim_new"])):
    op, np_ = exp / old, exp / new
    if op.exists():
      # content already replaced instance strings; rename file
      if np_.exists():
        np_.unlink()
      op.rename(np_)
      # Update class/file header names inside
      t = np_.read_text(encoding="utf-8", errors="replace")
      t = t.replace(old.replace(".mq5", ""), new.replace(".mq5", ""))
      np_.write_text(t, encoding="utf-8")
      log(f"  EA {old} → {new}")

  # Ports
  sh = dst / "scripts" / "run_app_linux.sh"
  if sh.exists():
    t = sh.read_text(encoding="utf-8")
    t = re.sub(r"^PORT=\d+", f"PORT={cfg['app_port']}", t, count=1, flags=re.M)
    sh.write_text(t, encoding="utf-8")
  mon = dst / "mt5_bridge" / "live_monitor_server.py"
  if mon.exists():
    t = mon.read_text(encoding="utf-8")
    t = re.sub(r"DEFAULT_MONITOR_PORT\s*=\s*\d+", f"DEFAULT_MONITOR_PORT = {cfg['bridge_port']}", t)
    t = re.sub(r"SIM_MONITOR_PORT\s*=\s*\d+", f"SIM_MONITOR_PORT = {cfg['sim_port']}", t)
    t = re.sub(r"COMPARE_MONITOR_PORT\s*=\s*\d+", f"COMPARE_MONITOR_PORT = {cfg['compare_port']}", t)
    mon.write_text(t, encoding="utf-8")

  # protocol magics / instance / bridge paths
  proto = dst / "mt5_bridge" / "protocol.py"
  if proto.exists():
    t = proto.read_text(encoding="utf-8")
    t = re.sub(r'DEFAULT_MAGIC\s*=\s*\d+', f'DEFAULT_MAGIC = {cfg["magic_live"]}', t)
    t = re.sub(r'DEFAULT_SIM_MAGIC\s*=\s*\d+', f'DEFAULT_SIM_MAGIC = {cfg["magic_sim"]}', t)
    t = re.sub(r'INSTANCE_ID\s*=\s*"[^"]+"', f'INSTANCE_ID = "{cfg["instance"]}"', t)
    t = re.sub(r'BRIDGE_DIR = ROOT / "mt5" / "[^"]+"', f'BRIDGE_DIR = ROOT / "mt5" / "{cfg["bridge"]}"', t)
    t = re.sub(
      r'BRIDGE_SIM_DIR = ROOT / "mt5" / "[^"]+"',
      f'BRIDGE_SIM_DIR = ROOT / "mt5" / "{cfg["bridge_sim"]}"',
      t,
    )
    proto.write_text(t, encoding="utf-8")

  # Fresh empty bridge models.json
  for bname, base in ((cfg["bridge"], cfg["magic_live"]), (cfg["bridge_sim"], cfg["magic_sim"])):
    bdir = mt5 / bname
    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / "decisions").mkdir(exist_ok=True)
    (bdir / "models.json").write_text(
      json.dumps(
        {"updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
         "risk_pct": 1.0, "base_magic": base, "models": []},
        indent=2,
      )
      + "\n",
      encoding="utf-8",
    )


def write_clean_settings(dst: Path, cfg: dict) -> None:
  results = dst / "results"
  learning = dst / "learning" / "kb_profiles"
  for p in (results, results / "jobs", results / "grid_search", results / "trade_models",
            results / "research", learning):
    p.mkdir(parents=True, exist_ok=True)

  eras = [
    {
      "key": "2025-h2",
      "label": "2025 (6 tháng cuối)",
      "learn_from": "2025-07-01",
      "learn_until": "2025-12-31",
      "kb_profile": "era_2025_h2",
    },
    {
      "key": "5-thang-cuoi-2025",
      "label": "5 thang cuoi 2025",
      "learn_from": "2025-08-01",
      "learn_until": "2025-12-31",
      "kb_profile": "era_5_thang_cuoi_2025",
    },
    {
      "key": "2025-2026-6thang",
      "label": "2025-2026-6thang",
      "learn_from": "2025-10-01",
      "learn_until": "2026-03-31",
      "kb_profile": "era_2025_2026_6thang",
    },
  ]
  if cfg["tf"] == "M5":
    presets = ["elite_or_quality", "elite_m5_balanced", "anti_chase_fixed_70"]
  else:
    presets = ["elite_or_quality", "anti_chase_fixed_70", "elite_55_4"]

  settings = {
    "id": "final_guide",
    "label": f"Final_app GUIDE · {cfg['instance']}",
    "strategy_train_weeks": [3, 6],
    "learning_eras": eras,
    "learning_era_keys": ["2025-h2", "5-thang-cuoi-2025"],
    "learning_loops": 4,
    "backtest_from": OOS_FROM,
    "backtest_to": OOS_TO,
    "spread_pips": cfg["spread"],
    "slippage_pips": 0.3,
    "grid_objective": "quality",
    "mining_presets": presets,
    "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
  }
  (results / "app_settings.json").write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  (results / "trade_models.json").write_text(json.dumps({"models": []}, indent=2) + "\n", encoding="utf-8")
  (results / "active_trade_model.json").write_text("{}\n", encoding="utf-8")
  (results / "active_workspace.json").write_text(
    json.dumps({
      "oos_from": OOS_FROM,
      "oos_to": OOS_TO,
      "spread_pips": cfg["spread"],
      "slippage_pips": 0.3,
      "feature_profile": cfg["feature_profile_default"],
      "use_learning": True,
    }, indent=2)
    + "\n",
    encoding="utf-8",
  )
  (results / "ui_preferences.json").write_text(
    json.dumps({"compare.from": OOS_FROM, "compare.to": OOS_TO}, indent=2) + "\n",
    encoding="utf-8",
  )
  (learning / "index.json").write_text(json.dumps({"profiles": []}, indent=2) + "\n", encoding="utf-8")
  log(f"  clean settings OOS {OOS_FROM}→{OOS_TO} objective=quality eras={settings['learning_era_keys']}")


def main() -> int:
  FINAL.mkdir(parents=True, exist_ok=True)
  catalog = []
  for cfg in DESKS:
    dst = FINAL / cfg["dst_name"]
    log(f"==== {cfg['instance']} ({cfg['tf']} {cfg['symbol']}) ====")
    rsync_clone(cfg["src"], dst)
    symlink_data(cfg["src"], dst)
    specialize(dst, cfg)
    write_clean_settings(dst, cfg)
    catalog.append({
      "folder": cfg["dst_name"],
      "instance": cfg["instance"],
      "tf": cfg["tf"],
      "symbol": cfg["symbol"],
      "app_port": cfg["app_port"],
      "magic_live": cfg["magic_live"],
      "magic_sim": cfg["magic_sim"],
      "bridge": cfg["bridge"],
      "oos": f"{OOS_FROM}→{OOS_TO}",
    })

  (FINAL / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
  log(f"Wrote {FINAL / 'catalog.json'}")
  log("Clone+clean done. Next: ./run_final_train.sh")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
