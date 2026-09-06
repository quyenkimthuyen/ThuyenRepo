#!/usr/bin/env python3
"""Nâng Total R > 50, giữ WR > 50 trên OOS 6 tháng 2026-h1.

Không nới confirm, không kéo dài OOS, không 3 lệnh/ngày.
  EUR: late hybrid overlay (cùng entry ss_more) + weeks 7/9 cùng confirm.
  GBP: cùng confirm ss_tight, densify gap/hold + 8w; đo overlay riêng.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from desk_context import apply_desk_env  # noqa: E402

TARGET = {"wr_gt": 50.0, "total_r_gt": 50.0, "n_ge": 15, "max_dd_lt": 16.0}
OOS = ("2026-01-01", "2026-06-30")
FOLD = ("2025-07-01", "2025-12-31")  # extra fold, không dùng để promote


def _purge() -> None:
  for name in list(sys.modules):
    if name in (
      "run_backtest", "knowledge_base", "config", "app_paths",
      "data_loader", "kb_profiles", "optimizer",
    ) or name.startswith("gui.") or name.startswith("mt5_bridge"):
      sys.modules.pop(name, None)


def _bind(desk: str) -> dict:
  cfg = apply_desk_env(desk)
  _purge()
  for p in (str(ROOT), str(cfg["core_root"])):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)
  return cfg


def _log(desk: str, msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] [{desk}] {msg}"
  try:
    print(line, flush=True)
  except UnicodeEncodeError:
    print(line.encode("ascii", "replace").decode("ascii"), flush=True)
  log_dir = Path(os.environ["TRAINAPP_RUNTIME"]) / "results"
  log_dir.mkdir(parents=True, exist_ok=True)
  with open(log_dir / "r50_lift.log", "a", encoding="utf-8") as f:
    f.write(line + "\n")


def _nums(row: dict) -> tuple[float, float, float, int]:
  return (
    float(row.get("win_rate_pct") or 0),
    float(row.get("total_r") or 0),
    float(row.get("max_drawdown_r") or 999),
    int(row.get("n_trades") or 0),
  )


def _fmt(row: dict) -> str:
  wr, tot, dd, n = _nums(row)
  rr = float(row.get("avg_rr") or 0)
  return (
    f"WR={wr:.1f} RR={rr:.2f} R={tot:+.1f} DD={dd:.1f} n={n} "
    f"w={row.get('train_weeks')} ep={row.get('kb_snapshot')} {row.get('mining_preset')}"
  )


def _hit(row: dict) -> bool:
  if row.get("error"):
    return False
  wr, tot, dd, n = _nums(row)
  oos_ok = (str(row.get("oos_from") or "")[:10], str(row.get("oos_to") or "")[:10]) == OOS
  return oos_ok and wr > TARGET["wr_gt"] and tot > TARGET["total_r_gt"] and n >= TARGET["n_ge"] and dd < TARGET["max_dd_lt"]


def _run(desk: str, specs, *, workers: int, tag: str, save: bool = True) -> list[dict]:
  from gui.grid_search_engine import run_grid, save_grid_run
  from config import DEFAULT_TF

  _log(desk, f"{tag} start {len(specs)} combo · workers={workers}")
  t0 = time.time()

  def on_prog(done, total, label):
    _log(desk, f"{tag} {done}/{total}: {label}")

  rows = run_grid(specs, objective="total_r", on_progress=on_prog, workers=workers)
  if save:
    rid = save_grid_run(
      rows,
      config={"source": "r50_lift", "tag": tag, "timeframe": DEFAULT_TF, "target": TARGET},
      objective="total_r",
    )
    _log(desk, f"{tag} saved {rid}: {sum(1 for r in rows if not r.get('error'))}/{len(rows)} OK in {time.time() - t0:.0f}s")
  else:
    _log(desk, f"{tag} done (no save): {sum(1 for r in rows if not r.get('error'))}/{len(rows)} OK in {time.time() - t0:.0f}s")
  ranked = sorted([r for r in rows if not r.get("error")], key=lambda r: (_nums(r)[1], _nums(r)[0]), reverse=True)
  for r in ranked[:10]:
    mark = " HIT" if _hit(r) else ""
    _log(desk, f"{tag} top {_fmt(r)}{mark}")
  return rows


def _register_wave2_presets() -> None:
  return


def _specs(desk: str, *, wave: int):
  from gui.grid_search_engine import build_grid
  from config import DEFAULT_SPREAD_PIPS, DEFAULT_SLIPPAGE_PIPS

  common = dict(
    include_kb_off=False,
    epoch_mode="selected",
    oos_from=OOS[0],
    oos_to=OOS[1],
    skip_kb_oos_overlap=True,
    spread_pips=float(DEFAULT_SPREAD_PIPS),
    slippage_pips=float(DEFAULT_SLIPPAGE_PIPS),
    max_runs=80,
  )
  if desk.startswith("g"):
    if wave == 2:
      return build_grid(
        train_weeks=[6, 8],
        kb_profiles=["era_2025_h2", "era_2025_h1"],
        selected_epochs={"era_2025_h2": [1, 2, 3], "era_2025_h1": [1, 2, 3]},
        kb_learn_by_profile={
          "era_2025_h2": ("2025-07-01", "2025-12-31"),
          "era_2025_h1": ("2025-01-01", "2025-06-30"),
        },
        mining_presets=["gbp_fill_ss_vol"],
        **common,
      )
    return build_grid(
      train_weeks=[6, 8],
      kb_profiles=["era_2025_h2"],
      selected_epochs={"era_2025_h2": [1, 2, 3]},
      kb_learn_by_profile={"era_2025_h2": ("2025-07-01", "2025-12-31")},
      mining_presets=["gbp_fill_ss_tight_n", "gbp_fill_ss_tight_hyb24"],
      **common,
    )
  if wave == 2:
    _register_wave2_presets()
    return build_grid(
      train_weeks=[8],
      kb_profiles=["era_2025_h1"],
      selected_epochs={"era_2025_h1": [1, 2, 3]},
      kb_learn_by_profile={"era_2025_h1": ("2025-01-01", "2025-06-30")},
      mining_presets=["eur_fill_ss_plus", "eur_fill_ss_more_hold", "eur_fill_ss_more_hyb28"],
      **common,
    )
  return build_grid(
    train_weeks=[8, 7, 9],
    kb_profiles=["era_2025_h1"],
    selected_epochs={"era_2025_h1": [1, 2, 3]},
    kb_learn_by_profile={"era_2025_h1": ("2025-01-01", "2025-06-30")},
    mining_presets=["eur_fill_ss_more_hyb24"],
    **common,
  )


def _fold_specs():
  from gui.grid_search_engine import build_grid
  from config import DEFAULT_SPREAD_PIPS, DEFAULT_SLIPPAGE_PIPS

  return build_grid(
    train_weeks=[8],
    kb_profiles=["era_2025_h1"],
    include_kb_off=False,
    epoch_mode="selected",
    selected_epochs={"era_2025_h1": [1, 2, 3]},
    oos_from=FOLD[0],
    oos_to=FOLD[1],
    kb_learn_by_profile={"era_2025_h1": ("2025-01-01", "2025-06-30")},
    skip_kb_oos_overlap=True,
    spread_pips=float(DEFAULT_SPREAD_PIPS),
    slippage_pips=float(DEFAULT_SLIPPAGE_PIPS),
    max_runs=20,
    mining_presets=["eur_fill_ss_more_hyb24"],
  )


def _promote(desk: str, rows: list[dict], run_id: str) -> list[dict]:
  from gui.trade_model import create_trade_model

  hits = [r for r in rows if _hit(r)]
  hits.sort(key=lambda r: (_nums(r)[1], _nums(r)[0]), reverse=True)
  created = []
  for i, row in enumerate(hits[:3]):
    wr, tot, dd, n = _nums(row)
    label = f"WR{wr:.0f}R{tot:.0f}"
    model = create_trade_model(
      row,
      run_id=run_id,
      label=label,
      set_active=(i == 0),
      build_report=False,
      allow_duplicate_combo=False,
    )
    created.append(model)
    _log(desk, f"TM {model.get('id')} · {model.get('label')} · {_fmt(row)} · active={i == 0}")
  if not created:
    _log(desk, "Không combo nào WR>50 và R>50 trên 2026-h1")
  return created


def run_desk(desk: str, *, workers: int, wave: int) -> dict:
  cfg = _bind(desk)
  _log(desk, f"R50 lift pair={cfg.get('pair')} spread={cfg.get('spread_pips')} wave={wave}")
  if wave == 2 and desk.startswith("g"):
    from gui.era_compare import ensure_profile_learned
    _log(desk, "KB ensure era_2025_h1 · 3 epoch")
    t0 = time.time()
    ensure_profile_learned(
      {
        "kb_profile": "era_2025_h1",
        "kb_name": "2025 (6 tháng đầu)",
        "learn_from": "2025-01-01",
        "learn_until": "2025-06-30",
      },
      epochs=3,
      reset=True,
    )
    _log(desk, f"KB era_2025_h1 done in {time.time() - t0:.0f}s")
  specs = _specs(desk, wave=wave)
  rows = _run(desk, specs, workers=workers, tag=f"lift{wave}")
  fold_rows = []
  if wave == 1 and not desk.startswith("g"):
    fold_rows = _run(desk, _fold_specs(), workers=workers, tag="fold", save=False)
  created = _promote(desk, rows, run_id="r50_lift")
  out = {
    "desk": desk,
    "n_combos": len(rows),
    "hits": [
      {
        "preset": r.get("mining_preset"),
        "weeks": r.get("train_weeks"),
        "ep": r.get("kb_snapshot"),
        "wr": _nums(r)[0],
        "r": _nums(r)[1],
        "n": _nums(r)[3],
        "dd": _nums(r)[2],
      }
      for r in rows if _hit(r)
    ],
    "fold": [
      {
        "ep": r.get("kb_snapshot"),
        "wr": _nums(r)[0],
        "r": _nums(r)[1],
        "n": _nums(r)[3],
      }
      for r in fold_rows if not r.get("error")
    ],
    "models": [{"id": m.get("id"), "label": m.get("label")} for m in created],
  }
  _log(desk, f"R50 DONE {json.dumps(out, ensure_ascii=False)}")
  return out


def main() -> int:
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--desks", default="e21,g23")
  ap.add_argument("--workers", type=int, default=3)
  ap.add_argument("--wave", type=int, default=1, choices=(1, 2))
  args = ap.parse_args()
  desks = [d.strip().lower() for d in args.desks.split(",") if d.strip()]
  summary, rc = [], 0
  for desk in desks:
    try:
      summary.append(run_desk(desk, workers=max(1, args.workers), wave=args.wave))
    except Exception as exc:
      rc = 1
      try:
        _bind(desk)
        _log(desk, f"FAILED: {exc}")
      except Exception:
        print(f"FAILED {desk}: {exc}", flush=True)
      summary.append({"desk": desk, "error": str(exc)})
  print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
  return rc


if __name__ == "__main__":
  raise SystemExit(main())
