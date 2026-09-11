#!/usr/bin/env python3
"""Create 3 live-ok Train TMs per desk, then promote_top3_to_live --spawn."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/thuyenng/work/ThuyenRepo/M15_clone2_1/Train")
PICKS = {
  "e21": [
    {
      "run": "gs_20260910_150931",
      "key": "9be2aafa4817",
      "label": "WR45R24",
      "kb": "era_2024_h1",
      "ep": 8,
    },
    {
      "run": "gs_20260910_132124",
      "key": "d27bc2b91acb",
      "label": "WR41R28",
      "kb": "era_2025_h1",
      "ep": 6,
    },
    {
      "run": "gs_20260910_132124",
      "key": "bcc415c8fb0b",
      "label": "WR40R25",
      "kb": "era_2025_h1",
      "ep": 7,
    },
  ],
  "g23": [
    {
      "run": "gs_20260910_172219",
      "key": "922eac5bdebc",
      "label": "WR48R27",
      "kb": "era_2025_h2",
      "ep": 4,
    },
    {
      "run": "gs_20260910_172219",
      "key": "c003b4a75f83",
      "label": "WR47R34",
      "kb": "era_2025_h2",
      "ep": 1,
    },
    {
      "run": "gs_20260910_114048",
      "key": "9e42a5700f94",
      "label": "WR45R36",
      "kb": "era_2025_h2",
      "ep": 4,
    },
  ],
}


def _create_desk(desk: str) -> None:
  sys.path.insert(0, str(ROOT))
  sys.path.insert(0, str(ROOT / "scripts"))
  from run_std_recipe import _bind

  _bind(desk)
  from gui.trade_model import (
    create_trade_model,
    delete_trade_model,
    list_trade_models,
    load_models_store,
    save_models_store,
    set_active_trade_model,
  )
  from mt5_bridge.background import save_config, sync_bridge_roster
  from trade_model_kb_pin import ensure_model_kb_pin

  gdir = ROOT / "runtime" / desk / "results" / "grid_search"
  keep_ids: list[str] = []
  for spec in PICKS[desk]:
    data = json.loads((gdir / f"{spec['run']}.json").read_text(encoding="utf-8"))
    row = next(r for r in data["rows"] if r.get("key") == spec["key"])
    row["kb_profile"] = spec["kb"]
    row["kb_snapshot"] = spec["ep"]
    model = create_trade_model(
      row,
      run_id=spec["run"],
      label=spec["label"],
      set_active=False,
      build_report=False,
    )
    store = load_models_store()
    for m in store["models"]:
      if m.get("id") != model["id"]:
        continue
      m["kb_profile"] = spec["kb"]
      m["kb_snapshot"] = spec["ep"]
      m.pop("kb_fingerprint", None)
      ensure_model_kb_pin(m)
      model = m
      break
    save_models_store(store)
    keep_ids.append(model["id"])
    print(
      f"{desk} KEEP {model['id']} {model.get('label')} "
      f"WR={model.get('win_rate_pct')} R={model.get('total_r')} "
      f"kb={model.get('kb_profile')}@{model.get('kb_snapshot')} "
      f"pin={model.get('kb_pin_source')}",
      flush=True,
    )

  for m in list(list_trade_models()):
    mid = str(m.get("id") or "")
    if mid and mid not in keep_ids:
      delete_trade_model(mid)
      print(f"{desk} DELETE {mid} {m.get('label')}", flush=True)

  set_active_trade_model(keep_ids[0])
  save_config(
    enabled=True,
    model_id=keep_ids[0],
    model_ids=keep_ids,
    max_trades_per_day_by_model={mid: 2 for mid in keep_ids},
  )
  sync_bridge_roster(model_ids=keep_ids)
  print(f"{desk} BRIDGE {keep_ids}", flush=True)


def main() -> int:
  os.chdir(ROOT)
  if len(sys.argv) == 2 and sys.argv[1] in PICKS:
    _create_desk(sys.argv[1])
    return 0

  for desk in ("e21", "g23"):
    rc = subprocess.call([sys.executable, "-u", str(Path(__file__).resolve()), desk])
    if rc != 0:
      return rc

  out = Path("/tmp/m15_clone2_1_top3_pkg")
  cmd = [
    sys.executable, "-u", str(ROOT / "scripts" / "promote_top3_to_live.py"),
    "--spawn", "--force-schedule", "--out", str(out),
  ]
  print("PROMOTE", " ".join(cmd), flush=True)
  return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
  raise SystemExit(main())
