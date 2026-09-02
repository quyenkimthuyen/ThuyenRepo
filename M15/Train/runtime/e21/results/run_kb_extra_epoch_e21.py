#!/usr/bin/env python3
"""Tiếp 1 vòng KB (không reset) rồi grid 8/12w trên ep mới. Không promote Active."""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/thuyenng/work/ThuyenRepo/M15/Train")
sys.path.insert(0, str(ROOT))
from desk_context import apply_desk_env

LOG = ROOT / "runtime" / "e21" / "results" / "pipeline_kb_grid.log"
PREV_BEST = (56.1, 2.66, 43.3, 3.0, 41, 2.864)


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
  log(f"extra-epoch start pair={cfg.get('pair')} tf={cfg.get('tf')}")
  from data_loader import load_eurusd_m15
  from feature_engine import FeatureMatrix
  from gui.app_settings import get_settings, settings_grid_signature
  from gui.grid_search_engine import GridSpec, run_grid, save_grid_run, _score
  from kb_profiles import profile_path, register_profile, slice_df_for_period
  from knowledge_base import KnowledgeBase
  from run_learning import run_epoch
  from config import DEFAULT_TF

  s = get_settings()
  pid = "era_2025_full"
  learn_from, learn_until = "2025-01-01", "2025-12-31"
  weeks = list(s.get("strategy_train_weeks") or [8, 12])
  preset = (s.get("mining_presets") or ["eur_fill_ss_lab"])[0]
  objective = str(s.get("grid_objective") or "quality")
  oos_from = str(s.get("backtest_from") or "2026-01-01")
  oos_to = str(s.get("backtest_to") or "2026-12-31")
  spread = float(s.get("spread_pips") or 1.9)
  slip = float(s.get("slippage_pips") or 0.3)

  kb = KnowledgeBase(profile_path(pid))
  already = len(kb.epoch_history)
  next_ep = already + 1
  log(
    f"KB continue (no reset) · have={already} → run ep{next_ep} · "
    f"{learn_from}→{learn_until} · genomes={len(kb.genomes)}"
  )
  t0 = time.time()
  df = load_eurusd_m15(learn_from)
  df = slice_df_for_period(df, learn_from, learn_until)
  fm = FeatureMatrix(df)
  out = run_epoch(df, fm, kb, next_ep)
  m = out["epoch_metrics"]
  cumulative = len(kb.epoch_history)
  register_profile(
    pid, "2025 (12 tháng)",
    str(df.index[0].date()), str(df.index[-1].date()),
    cumulative,
    note=f"continue +1 epoch → {cumulative}",
  )
  log(
    f"KB ep{cumulative} WR={m.get('win_rate_pct')} R={m.get('total_r')} "
    f"RR={m.get('avg_rr')} genomes={len(kb.genomes)} rules={len(kb.rule_stats)}"
  )

  specs = [
    GridSpec(
      train_weeks=tm, use_kb=True, kb_profile=pid, kb_snapshot=cumulative,
      oos_from=oos_from, oos_to=oos_to,
      spread_pips=spread, slippage_pips=slip,
      mining_preset=preset,
    )
    for tm in weeks
  ]
  log(f"Grid start {len(specs)} combo · only ep{cumulative} · obj={objective}")

  def on_prog(done, total, label):
    log(f"Grid {done}/{total}: {label}")

  rows = run_grid(specs, objective=objective, on_progress=on_prog, workers=2)
  rid = save_grid_run(
    rows,
    config={
      "train_weeks": weeks,
      "kb_profiles": [pid],
      "include_kb_off": False,
      "epoch_mode": "selected",
      "selected_epochs": {pid: [cumulative]},
      "oos_from": oos_from,
      "oos_to": oos_to,
      "spread_pips": spread,
      "slippage_pips": slip,
      "mining_presets": [preset],
      "timeframe": DEFAULT_TF,
      "source": "kb_extra_epoch_cli",
      "settings_signature": settings_grid_signature(s),
      "promote": False,
      "compare_prev_best": {
        "wr": PREV_BEST[0], "rr": PREV_BEST[1], "r": PREV_BEST[2],
        "dd": PREV_BEST[3], "n": PREV_BEST[4], "pf": PREV_BEST[5],
        "label": "8w · 2025-full · ep1 · eur_fill_ss_lab",
      },
    },
    objective=objective,
  )
  ok = [x for x in rows if not x.get("error")]
  log(f"Grid done {rid}: {len(ok)}/{len(rows)} OK in {time.time()-t0:.0f}s")
  ranked = sorted(ok, key=lambda r: _score(r, objective), reverse=True)
  prev_wr, prev_rr, prev_r, prev_dd, prev_n, prev_pf = PREV_BEST
  log(
    f"prev best WR={prev_wr} RR={prev_rr} R={prev_r} DD={prev_dd} n={prev_n} "
    f"PF={prev_pf} · 8w · ep1 · eur_fill_ss_lab"
  )
  for r in ranked:
    wr = float(r.get("win_rate_pct") or 0)
    tot = float(r.get("total_r") or 0)
    d_wr = wr - prev_wr
    d_r = tot - prev_r
    log(
      f"ep{cumulative} WR={wr:.1f} ({d_wr:+.1f}) RR={float(r.get('avg_rr') or 0):.2f} "
      f"R={tot:.1f} ({d_r:+.1f}) DD={float(r.get('max_drawdown_r') or 0):.1f} "
      f"n={r.get('n_trades')} PF={r.get('profit_factor')} · {r.get('label')}"
    )
  improved = any(
    float(r.get("win_rate_pct") or 0) > prev_wr + 0.05
    or float(r.get("total_r") or 0) > prev_r + 0.5
    for r in ranked
  )
  log(
    "EXTRA EPOCH DONE · "
    + ("improved vs ep1" if improved else "no improvement vs ep1")
    + " (no promote, no Active)"
  )
  print("PIPELINE DONE", flush=True)
  return 0


if __name__ == "__main__":
  try:
    raise SystemExit(main())
  except Exception as exc:
    log(f"FAILED: {exc}")
    print("PIPELINE FAILED", flush=True)
    raise
