#!/usr/bin/env python3
"""Học KB 2024-h1/h2 + 2025-h1/h2/q4 (giữ 2025-full), grid ss_lab/ss_more trên OOS 2026. Không promote."""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/thuyenng/work/ThuyenRepo/M15/Train")
sys.path.insert(0, str(ROOT))
from desk_context import apply_desk_env

LOG = ROOT / "runtime" / "e21" / "results" / "pipeline_kb_grid.log"

LEARN_ERAS = [
  {
    "kb_profile": "era_2024_h1",
    "kb_name": "2024 (6 tháng đầu)",
    "learn_from": "2024-01-01",
    "learn_until": "2024-06-30",
  },
  {
    "kb_profile": "era_2024_h2",
    "kb_name": "2024 (6 tháng cuối)",
    "learn_from": "2024-07-01",
    "learn_until": "2024-12-31",
  },
  {
    "kb_profile": "era_2025_h1",
    "kb_name": "2025 (6 tháng đầu)",
    "learn_from": "2025-01-01",
    "learn_until": "2025-06-30",
  },
  {
    "kb_profile": "era_2025_h2",
    "kb_name": "2025 (6 tháng cuối)",
    "learn_from": "2025-07-01",
    "learn_until": "2025-12-31",
  },
  {
    "kb_profile": "era_2025_q4",
    "kb_name": "2025 (3 tháng cuối)",
    "learn_from": "2025-10-01",
    "learn_until": "2025-12-31",
  },
]
KEEP_GRID = ["era_2025_full"]
PREV = "ss_lab 8w full ep1 WR56.1 +43.3R n=41 PF2.86"


def log(msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] [e21] {msg}"
  print(line, flush=True)
  LOG.parent.mkdir(parents=True, exist_ok=True)
  with open(LOG, "a", encoding="utf-8") as f:
    f.write(line + "\n")


def bind():
  cfg = apply_desk_env("e21")
  for name in list(sys.modules):
    if name in (
      "run_backtest", "knowledge_base", "config", "app_paths",
      "data_loader", "kb_profiles", "optimizer",
    ) or name.startswith("gui.") or name.startswith("mt5_bridge"):
      sys.modules.pop(name, None)
  for p in (str(ROOT), str(cfg["core_root"])):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)
  return cfg


def main() -> int:
  cfg = bind()
  log(f"extra-era start pair={cfg.get('pair')} · keep era_2025_full · {PREV}")
  from gui.app_settings import merge_learning_eras_into_catalog
  from gui.era_compare import ensure_profile_learned
  from gui.grid_search_engine import build_grid, run_grid, save_grid_run, _score
  from config import DEFAULT_TF

  merge_learning_eras_into_catalog(
    [
      {
        "key": "2025-q4",
        "label": "2025 (3 tháng cuối)",
        "learn_from": "2025-10-01",
        "learn_until": "2025-12-31",
        "kb_profile": "era_2025_q4",
      },
    ],
  )

  loops = 3
  t0 = time.time()
  for era in LEARN_ERAS:
    log(
      f"KB learn RESET · {era['kb_name']} · {loops} vòng · "
      f"{era['learn_from']}→{era['learn_until']}"
    )
    out = ensure_profile_learned(era, epochs=loops, reset=True)
    if out.get("skipped"):
      log(f"KB skip {era['kb_profile']}")
    else:
      summ = (out.get("kb_summary") or {})
      log(
        f"KB done {era['kb_profile']} genomes={summ.get('genomes')} "
        f"rules={summ.get('rules')} fitness={summ.get('best_fitness')}"
      )

  weeks = [8, 12]
  presets = ["eur_fill_ss_lab", "eur_fill_ss_more"]
  pids = KEEP_GRID + [e["kb_profile"] for e in LEARN_ERAS]
  selected = {pid: [1, 2, 3] for pid in pids}
  specs = build_grid(
    train_weeks=weeks,
    kb_profiles=pids,
    include_kb_off=False,
    epoch_mode="selected",
    selected_epochs=selected,
    oos_from="2026-01-01",
    oos_to="2026-12-31",
    oos_by_profile=None,
    spread_pips=1.9,
    slippage_pips=0.3,
    max_runs=200,
    mining_presets=presets,
  )
  log(
    f"Grid start {len(specs)} combo · 2026 OOS forced · "
    f"eras={pids} · presets={presets}"
  )

  def on_prog(done, total, label):
    log(f"Grid {done}/{total}: {label}")

  rows = run_grid(specs, objective="quality", on_progress=on_prog, workers=2)
  rid = save_grid_run(
    rows,
    config={
      "train_weeks": weeks,
      "kb_profiles": pids,
      "include_kb_off": False,
      "mining_presets": presets,
      "oos_from": "2026-01-01",
      "oos_to": "2026-12-31",
      "spread_pips": 1.9,
      "slippage_pips": 0.3,
      "timeframe": DEFAULT_TF,
      "source": "eur_extra_era_cli",
      "promote": False,
      "compare_prev": PREV,
    },
    objective="quality",
  )
  ok = [x for x in rows if not x.get("error")]
  log(f"Grid done {rid}: {len(ok)}/{len(rows)} OK in {time.time()-t0:.0f}s")
  ranked = sorted(ok, key=lambda r: _score(r, "quality"), reverse=True)

  def key_n(r):
    return int(r.get("n_trades") or 0)

  def key_r(r):
    return float(r.get("total_r") or 0)

  def key_wr(r):
    return float(r.get("win_rate_pct") or 0)

  log("by quality:")
  for r in ranked[:10]:
    log(
      f"top WR={key_wr(r):.1f} RR={float(r.get('avg_rr') or 0):.2f} "
      f"R={key_r(r):.1f} DD={float(r.get('max_drawdown_r') or 0):.1f} "
      f"n={key_n(r)} PF={r.get('profit_factor')} · {r.get('label')}"
    )
  by_n = sorted(ok, key=key_n, reverse=True)[:4]
  log("by n:")
  for r in by_n:
    log(f"n={key_n(r)} WR={key_wr(r):.1f} R={key_r(r):.1f} · {r.get('label')}")
  by_r = sorted(ok, key=key_r, reverse=True)[:4]
  log("by R:")
  for r in by_r:
    log(f"R={key_r(r):.1f} WR={key_wr(r):.1f} n={key_n(r)} · {r.get('label')}")
  quality = [
    r for r in ok
    if key_r(r) > 0 and float(r.get("profit_factor") or 0) >= 1.2 and key_n(r) >= 40
  ]
  log(f"quality-gate hits={len(quality)} / {len(ok)}")
  log("EXTRA ERA DONE (no promote, no Active, 2025-full untouched)")
  print("PIPELINE DONE", flush=True)
  return 0


if __name__ == "__main__":
  try:
    raise SystemExit(main())
  except Exception as exc:
    log(f"FAILED: {exc}")
    print("PIPELINE FAILED", flush=True)
    raise
