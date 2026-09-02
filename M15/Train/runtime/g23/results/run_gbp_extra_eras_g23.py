#!/usr/bin/env python3
"""Học KB 2025-h1 + 2025-h2 (không đụng 2025-full), grid DNA thắng trên OOS 2026. Không promote."""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/thuyenng/work/ThuyenRepo/M15/Train")
sys.path.insert(0, str(ROOT))
from desk_context import apply_desk_env

LOG = ROOT / "runtime" / "g23" / "results" / "pipeline_kb_grid.log"

ERAS = [
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
]
PREV = "ss_more 8w full ep2 WR56 +16R n=16 · ss_vol 6w full ep2 WR44 +16.2R n=25"


def log(msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] [g23] {msg}"
  print(line, flush=True)
  LOG.parent.mkdir(parents=True, exist_ok=True)
  with open(LOG, "a", encoding="utf-8") as f:
    f.write(line + "\n")


def bind():
  cfg = apply_desk_env("g23")
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
  from gui.era_compare import ensure_profile_learned
  from gui.grid_search_engine import build_grid, run_grid, save_grid_run, _score
  from config import DEFAULT_TF

  loops = 3
  t0 = time.time()
  for era in ERAS:
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

  weeks = [6, 8]
  presets = ["gbp_fill_ss_more", "gbp_fill_ss_vol"]
  pids = [e["kb_profile"] for e in ERAS]
  specs = build_grid(
    train_weeks=weeks,
    kb_profiles=pids,
    include_kb_off=False,
    epoch_mode="selected",
    selected_epochs={pid: [1, 2, 3] for pid in pids},
    oos_from="2026-01-01",
    oos_to="2026-12-31",
    oos_by_profile=None,
    spread_pips=2.3,
    slippage_pips=0.3,
    max_runs=200,
    mining_presets=presets,
  )
  log(f"Grid start {len(specs)} combo · 2026 OOS · no 2025-full re-run")

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
      "spread_pips": 2.3,
      "slippage_pips": 0.3,
      "timeframe": DEFAULT_TF,
      "source": "gbp_extra_era_cli",
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
  for r in ranked[:8]:
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
