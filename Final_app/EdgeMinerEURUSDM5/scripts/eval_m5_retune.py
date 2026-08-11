#!/usr/bin/env python3
"""Remine-eval after M5 hybrid retune — compare new search spaces vs saved models.

Runs walk-forward OOS with existing KB (no retrain) so the delta is mainly
fitness/preset/genome defaults from the retune.

Usage:
  /path/to/.venv/bin/python scripts/eval_m5_retune.py
  /path/to/.venv/bin/python scripts/eval_m5_retune.py --workers 4
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "results" / "research" / "m5_retune_eval"
RESULT_PATH = OUT_DIR / "latest.json"

# Mirror previous BestTotalR / elite windows.
OOS_FROM = "2026-01-01"
OOS_TO = "2026-08-07"
FEATURE = "m5_parity"


def _baseline_old_models() -> list[dict]:
  path = ROOT / "results" / "trade_models.json"
  if not path.exists():
    return []
  data = json.loads(path.read_text(encoding="utf-8"))
  models = data.get("models") if isinstance(data, dict) else data
  out = []
  for m in models or []:
    if not isinstance(m, dict):
      continue
    out.append({
      "label": m.get("label") or m.get("name") or m.get("id"),
      "id": m.get("id"),
      "total_r": m.get("total_r"),
      "n_trades": m.get("n_trades"),
      "profit_factor": m.get("profit_factor"),
      "max_drawdown_r": m.get("max_drawdown_r"),
      "win_rate_pct": m.get("win_rate_pct"),
      "train_weeks": m.get("train_weeks"),
      "kb_profile": m.get("kb_profile"),
      "mining_preset_hint": (
        "baseline" if (m.get("mining_search_space") or {}).get("selection_mode") == "legacy"
        and not (m.get("mining_search_space") or {}).get("anti_chase")
        else "curated/other"
      ),
      "target_tpw": (m.get("mining_search_space") or {}).get("target_trades_per_week"),
    })
  return out


def _jobs() -> list[dict]:
  """Focused matrix: same KB/OOS as prior BestTotalR, new retune presets."""
  return [
    {
      "name": "baseline_tw3_era5",
      "preset": "baseline",
      "train_weeks": 3,
      "kb_profile": "era_5_thang_cuoi_2025",
      "use_kb": True,
    },
    {
      "name": "elite_or_quality_tw3_era5",
      "preset": "elite_or_quality",
      "train_weeks": 3,
      "kb_profile": "era_5_thang_cuoi_2025",
      "use_kb": True,
    },
    {
      "name": "elite_or_quality_tw6_era5",
      "preset": "elite_or_quality",
      "train_weeks": 6,
      "kb_profile": "era_5_thang_cuoi_2025",
      "use_kb": True,
    },
    {
      "name": "baseline_tw6_era5",
      "preset": "baseline",
      "train_weeks": 6,
      "kb_profile": "era_5_thang_cuoi_2025",
      "use_kb": True,
    },
    {
      "name": "elite_or_quality_tw3_era3",
      "preset": "elite_or_quality",
      "train_weeks": 3,
      "kb_profile": "era_3_thang_cuoi_2025",
      "use_kb": True,
    },
    # Isolate old elite TPW=8 under NEW fitness (genome hybrid still applied).
    {
      "name": "elite_or_legacy_tpw8_tw3_era5",
      "preset": "elite_or_quality",
      "train_weeks": 3,
      "kb_profile": "era_5_thang_cuoi_2025",
      "use_kb": True,
      "override_tpw": 8.0,
    },
  ]


def _run_one(job: dict) -> dict:
  started = time.time()
  try:
    from data_loader import load_eurusd_m15
    from mining_presets import get_preset
    from optimizer import reset_kb_cache
    from run_backtest import run_walk_forward
    from strategy_miner import mining_search_space_from_dict

    space_dict = dict(get_preset(job["preset"]) or {})
    if job.get("override_tpw") is not None:
      space_dict["target_trades_per_week"] = float(job["override_tpw"])
    space = mining_search_space_from_dict(space_dict)
    reset_kb_cache()
    df = load_eurusd_m15("2025-01-01")
    report = run_walk_forward(
      df,
      use_learning=bool(job.get("use_kb", True)),
      train_weeks=int(job["train_weeks"]),
      spread_pips=1.0,
      slippage_pips=0.3,
      holdout_months=0,
      kb_profile=job.get("kb_profile"),
      oos_from=OOS_FROM,
      oos_to=OOS_TO,
      feature_profile=FEATURE,
      search_space=space,
      verbose=False,
    )
    oos = report.get("overall_oos") or {}
    return {
      "name": job["name"],
      "preset": job["preset"],
      "train_weeks": job["train_weeks"],
      "kb_profile": job.get("kb_profile"),
      "override_tpw": job.get("override_tpw"),
      "target_tpw": space_dict.get("target_trades_per_week"),
      "hold": space_dict.get("max_hold_bars"),
      "spacing": space_dict.get("min_bars_between"),
      "n_trades": oos.get("n_trades"),
      "win_rate_pct": oos.get("win_rate_pct"),
      "avg_rr": oos.get("avg_rr"),
      "total_r": oos.get("total_r"),
      "max_drawdown_r": oos.get("max_drawdown_r"),
      "profit_factor": oos.get("profit_factor"),
      "trades_per_week": oos.get("trades_per_week"),
      "error": None,
      "elapsed_sec": round(time.time() - started, 1),
    }
  except Exception as exc:
    return {
      "name": job["name"],
      "preset": job.get("preset"),
      "error": f"{type(exc).__name__}: {exc}",
      "traceback": traceback.format_exc(),
      "elapsed_sec": round(time.time() - started, 1),
    }


def _r_per_trade(row: dict) -> float | None:
  n = row.get("n_trades")
  r = row.get("total_r")
  if not n or r is None:
    return None
  try:
    return float(r) / float(n)
  except Exception:
    return None


def _r_dd(row: dict) -> float | None:
  r = row.get("total_r")
  dd = row.get("max_drawdown_r")
  if r is None or not dd:
    return None
  try:
    return float(r) / max(float(dd), 0.5)
  except Exception:
    return None


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--workers", type=int, default=4)
  ap.add_argument("--only", nargs="*", default=None, help="Run only these job names")
  args = ap.parse_args()

  jobs = _jobs()
  if args.only:
    want = set(args.only)
    jobs = [j for j in jobs if j["name"] in want]
  if not jobs:
    print("No jobs", flush=True)
    return 1

  OUT_DIR.mkdir(parents=True, exist_ok=True)
  print(f"Desk={ROOT.name} jobs={len(jobs)} workers={args.workers}", flush=True)
  print(f"OOS {OOS_FROM} → {OOS_TO} · feature={FEATURE}", flush=True)

  rows: list[dict] = []
  # Process pool: each worker re-imports and loads data (safer with numpy/sklearn).
  with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
    futs = {pool.submit(_run_one, job): job["name"] for job in jobs}
    for fut in as_completed(futs):
      name = futs[fut]
      row = fut.result()
      rows.append(row)
      if row.get("error"):
        print(f"FAIL {name}: {row['error']}", flush=True)
      else:
        print(
          f"OK   {name}: R={row.get('total_r')} n={row.get('n_trades')} "
          f"PF={row.get('profit_factor')} WR={row.get('win_rate_pct')} "
          f"DD={row.get('max_drawdown_r')} tpw={row.get('trades_per_week')} "
          f"({row.get('elapsed_sec')}s)",
          flush=True,
        )

  for row in rows:
    row["r_per_trade"] = _r_per_trade(row)
    row["r_over_dd"] = _r_dd(row)

  rows.sort(key=lambda r: float(r.get("total_r") or -1e18), reverse=True)
  payload = {
    "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "desk": ROOT.name,
    "oos_from": OOS_FROM,
    "oos_to": OOS_TO,
    "feature_profile": FEATURE,
    "previous_models": _baseline_old_models(),
    "runs": rows,
  }
  RESULT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
  stamp = OUT_DIR / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
  stamp.write_text(RESULT_PATH.read_text(encoding="utf-8"), encoding="utf-8")
  print(f"Wrote {RESULT_PATH}", flush=True)

  print("\n=== vs previous trade_models ===", flush=True)
  for m in payload["previous_models"]:
    print(
      f"  OLD {m.get('label')}: R={m.get('total_r')} n={m.get('n_trades')} "
      f"PF={m.get('profit_factor')} WR={m.get('win_rate_pct')} DD={m.get('max_drawdown_r')}",
      flush=True,
    )
  print("=== new runs (by Total R) ===", flush=True)
  for r in rows:
    if r.get("error"):
      print(f"  NEW {r['name']}: ERROR {r['error']}", flush=True)
    else:
      print(
        f"  NEW {r['name']}: R={r.get('total_r')} n={r.get('n_trades')} "
        f"PF={r.get('profit_factor')} WR={r.get('win_rate_pct')} DD={r.get('max_drawdown_r')} "
        f"tpw={r.get('trades_per_week')} R/trade={r.get('r_per_trade')} R/DD={r.get('r_over_dd')}",
        flush=True,
      )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
