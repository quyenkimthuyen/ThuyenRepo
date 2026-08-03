#!/usr/bin/env python3
"""A/B compare breakthrough mining presets vs active Trade Model baseline.

Uses the *existing* KB (no retrain) — same spirit as KB→Grid, but only the
new opt-in mining-space dimension. Does not mutate app settings, defaults,
or the active model unless ``--promote`` and the winner beats baseline on
both win-rate and avg RR.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_loader import load_eurusd_m15
from gui.trade_model import (
  create_trade_model,
  get_model_by_id,
  load_active_model_id,
  load_model_report,
)
from mining_presets import PRESETS, get_preset, list_presets
from optimizer import reset_kb_cache
from run_backtest import run_walk_forward
from strategy_miner import mining_search_space_from_dict

OUT_DIR = ROOT / "results" / "research" / "wr_rr_breakthrough"
RESULT_PATH = OUT_DIR / "latest.json"


def _model_cfg(model_id: str | None = None) -> tuple[str, dict, dict]:
  mid = model_id or load_active_model_id()
  if not mid:
    raise RuntimeError("No active trade model.")
  meta = get_model_by_id(mid) or {}
  report = load_model_report(mid) or {}
  cfg = report.get("config") or {}
  return mid, meta, {
    "train_weeks": int(meta.get("train_weeks") or cfg.get("train_weeks") or 6),
    "use_kb": bool(meta.get("use_kb", cfg.get("use_learning_kb", True))),
    "kb_profile": meta.get("kb_profile") or cfg.get("kb_profile"),
    "kb_snapshot": meta.get("kb_snapshot", cfg.get("kb_snapshot")),
    "oos_from": meta.get("oos_from") or cfg.get("oos_from") or "2026-01-01",
    "oos_to": meta.get("oos_to") or cfg.get("oos_to") or "2026-12-31",
    "spread_pips": float(meta.get("spread_pips") or cfg.get("spread_pips") or 1.0),
    "slippage_pips": float(meta.get("slippage_pips") or cfg.get("slippage_pips") or 0.3),
    "feature_profile": meta.get("feature_profile") or cfg.get("feature_profile") or "current",
  }


def _run_one(payload: tuple) -> dict:
  name, space_dict, df, model = payload
  try:
    reset_kb_cache()
    space = mining_search_space_from_dict(space_dict)
    report = run_walk_forward(
      df,
      use_learning=bool(model["use_kb"]),
      train_weeks=int(model["train_weeks"]),
      spread_pips=float(model["spread_pips"]),
      slippage_pips=float(model["slippage_pips"]),
      holdout_months=0,
      kb_profile=model.get("kb_profile"),
      kb_snapshot=model.get("kb_snapshot"),
      oos_from=model.get("oos_from"),
      oos_to=model.get("oos_to"),
      feature_profile=model.get("feature_profile") or "current",
      search_space=space,
      verbose=False,
    )
    oos = report.get("overall_oos") or {}
    return {
      "name": name,
      "mining_search_space": space_dict,
      "feature_profile": model.get("feature_profile") or "current",
      "overall_oos": oos,
      "n_trades": oos.get("n_trades"),
      "win_rate_pct": oos.get("win_rate_pct"),
      "avg_rr": oos.get("avg_rr"),
      "total_r": oos.get("total_r"),
      "max_drawdown_r": oos.get("max_drawdown_r"),
      "profit_factor": oos.get("profit_factor"),
      "trades_per_week": oos.get("trades_per_week"),
      "error": None,
      "report": report,
    }
  except Exception as exc:
    return {
      "name": name,
      "mining_search_space": space_dict,
      "error": f"{type(exc).__name__}: {exc}",
      "traceback": traceback.format_exc(),
    }


def _delta(candidate: dict, baseline: dict) -> dict:
  keys = ("win_rate_pct", "avg_rr", "total_r", "max_drawdown_r", "profit_factor", "n_trades")
  out = {}
  for key in keys:
    c, b = candidate.get(key), baseline.get(key)
    if c is None or b is None:
      out[key] = None
    else:
      out[key] = round(float(c) - float(b), 4)
  return out


def _beats_wr_and_rr(candidate: dict, baseline: dict) -> bool:
  return (
    float(candidate.get("win_rate_pct") or 0) > float(baseline.get("win_rate_pct") or 0)
    and float(candidate.get("avg_rr") or 0) >= float(baseline.get("avg_rr") or 0)
    and float(candidate.get("total_r") or 0) > 0
  )


def _beats_balanced(candidate: dict, baseline: dict) -> bool:
  """WR↑ and RR≥ and Total R not worse than -5% of baseline."""
  if not _beats_wr_and_rr(candidate, baseline):
    return False
  base_r = float(baseline.get("total_r") or 0)
  cand_r = float(candidate.get("total_r") or 0)
  return cand_r >= base_r * 0.95


def _joint_score(row: dict) -> float:
  if row.get("error"):
    return -1e12
  wr = float(row.get("win_rate_pct") or 0) / 100
  rr = float(row.get("avg_rr") or 0)
  tr = float(row.get("total_r") or 0)
  dd = max(float(row.get("max_drawdown_r") or 1), 0.5)
  tpw = float(row.get("trades_per_week") or 0)
  if tr <= 0 or not 4.0 <= tpw <= 12.0:
    return -1e9
  expectancy = wr * rr - (1.0 - wr)
  # Prefer WR×RR lifts that also preserve total R / frequency near 7–9.
  return (
    expectancy * 120
    + (tr / dd)
    + wr * 80
    + min(rr, 3.5) * 20
    + min(tpw, 8) * 3
    + min(tr, 250) * 0.15
  )


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--model-id", default=None, help="Baseline trade model id")
  parser.add_argument(
    "--presets",
    default="baseline,wr_rr_sniper,wr_rr_frontier,wr_rr_lock",
    help="Comma-separated preset names",
  )
  parser.add_argument("--workers", type=int, default=2)
  parser.add_argument("--train-weeks", type=int, default=None)
  parser.add_argument("--kb-profile", default=None)
  parser.add_argument("--kb-snapshot", default=None, help="Epoch int or 'latest'")
  parser.add_argument("--oos-from", default=None)
  parser.add_argument("--oos-to", default=None)
  parser.add_argument(
    "--out",
    default=None,
    help="Output JSON path (default: results/research/wr_rr_breakthrough/latest.json)",
  )
  parser.add_argument(
    "--promote",
    action="store_true",
    help="Create a NEW trade model if winner beats baseline on WR and RR",
  )
  parser.add_argument("--set-active", action="store_true", help="With --promote, set active")
  args = parser.parse_args()

  mid, meta, model = _model_cfg(args.model_id)
  if args.train_weeks is not None:
    model["train_weeks"] = int(args.train_weeks)
  if args.kb_profile is not None:
    model["kb_profile"] = args.kb_profile
    model["use_kb"] = True
  if args.kb_snapshot is not None:
    snap = str(args.kb_snapshot).strip().lower()
    model["kb_snapshot"] = None if snap in ("", "latest", "none") else int(snap)
  if args.oos_from is not None:
    model["oos_from"] = args.oos_from
  if args.oos_to is not None:
    model["oos_to"] = args.oos_to

  names = [n.strip() for n in args.presets.split(",") if n.strip()]
  unknown = [n for n in names if n not in PRESETS]
  if unknown:
    raise SystemExit(f"Unknown presets {unknown}. Known: {list_presets()}")

  out_path = Path(args.out) if args.out else RESULT_PATH
  if not out_path.is_absolute():
    out_path = ROOT / out_path

  df = load_eurusd_m15("2025-01-01").copy()
  fingerprint = hashlib.sha256(
    __import__("pandas").util.hash_pandas_object(df, index=True).values.tobytes(),
  ).hexdigest()

  frozen = (load_model_report(mid) or {}).get("overall_oos") or {
    "win_rate_pct": meta.get("win_rate_pct"),
    "avg_rr": None,
    "total_r": meta.get("total_r"),
  }

  jobs = [(name, get_preset(name), df, model) for name in names]
  rows: list[dict] = []
  workers = max(1, min(args.workers, len(jobs)))
  print(
    f"Breakthrough A/B | model={mid} | presets={names} | workers={workers}",
    flush=True,
  )
  print(
    f"  cfg train={model['train_weeks']}w kb={model.get('kb_profile')} "
    f"ep={model.get('kb_snapshot')} OOS={model.get('oos_from')}→{model.get('oos_to')}",
    flush=True,
  )
  if workers == 1:
    for job in jobs:
      row = _run_one(job)
      rows.append(row)
      print(f"  {row['name']}: {row.get('overall_oos') or row.get('error')}", flush=True)
  else:
    with ProcessPoolExecutor(max_workers=workers) as pool:
      pending = {pool.submit(_run_one, job): job[0] for job in jobs}
      for fut in as_completed(pending):
        row = fut.result()
        rows.append(row)
        print(f"  {row['name']}: {row.get('overall_oos') or row.get('error')}", flush=True)

  ok = [r for r in rows if not r.get("error")]
  baseline = next((r for r in ok if r["name"] == "baseline"), None)
  if baseline is None and ok:
    # Fall back to frozen metrics as baseline reference
    baseline = {
      "name": "frozen_active",
      "win_rate_pct": frozen.get("win_rate_pct"),
      "avg_rr": frozen.get("avg_rr"),
      "total_r": frozen.get("total_r"),
      "max_drawdown_r": frozen.get("max_drawdown_r"),
      "profit_factor": frozen.get("profit_factor"),
      "n_trades": frozen.get("n_trades"),
      "overall_oos": frozen,
    }
  ranked = sorted(ok, key=_joint_score, reverse=True)
  winner = ranked[0] if ranked else None
  # Prefer a candidate that actually beats WR+RR (joint winner may sacrifice RR).
  wr_rr_winners = [
    r for r in ranked
    if baseline is not None
    and r.get("name") != baseline.get("name")
    and _beats_wr_and_rr(r, baseline)
  ]
  balanced = [r for r in wr_rr_winners if _beats_balanced(r, baseline)]
  promote_candidate = (balanced[0] if balanced else None) or (
    wr_rr_winners[0] if wr_rr_winners else None
  )
  deltas = {
    r["name"]: _delta(r, baseline)
    for r in ok
    if baseline is not None and r["name"] != baseline.get("name")
  }

  promoted = None
  if args.promote and promote_candidate and baseline:
    winner = promote_candidate
    row = {
      "key": f"breakthrough_{winner['name']}_{mid[-8:]}",
      "train_weeks": model["train_weeks"],
      "use_kb": model["use_kb"],
      "kb_profile": model["kb_profile"],
      "kb_snapshot": model["kb_snapshot"],
      "oos_from": model["oos_from"],
      "oos_to": model["oos_to"],
      "spread_pips": model["spread_pips"],
      "slippage_pips": model["slippage_pips"],
      "feature_profile": winner.get("feature_profile") or "current",
      "mining_search_space": winner.get("mining_search_space"),
      "total_r": winner.get("total_r"),
      "win_rate_pct": winner.get("win_rate_pct"),
      "max_drawdown_r": winner.get("max_drawdown_r"),
      "profit_factor": winner.get("profit_factor"),
      "n_trades": winner.get("n_trades"),
    }
    report = winner.get("report")
    promoted = create_trade_model(
      row,
      run_id="breakthrough_wr_rr",
      label=f"Breakthrough {winner['name']} · vs {mid[-8:]}",
      report=report,
      set_active=bool(args.set_active),
      allow_duplicate_combo=True,
    )
    print(f"Promoted NEW model: {promoted.get('id')} (active={args.set_active})", flush=True)

  payload = {
    "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "baseline_model_id": mid,
    "model_config": model,
    "data_end": str(df.index[-1]),
    "data_fingerprint": fingerprint,
    "frozen_active_oos": frozen,
    "ranked": [
      {k: v for k, v in r.items() if k != "report"} for r in ranked
    ],
    "deltas_vs_baseline": deltas,
    "winner": None if not winner else {
      k: v for k, v in winner.items() if k != "report"
    },
    "beats_wr_and_rr": bool(
      winner and baseline and _beats_wr_and_rr(winner, baseline)
      and winner["name"] != baseline.get("name")
    ),
    "promoted_model_id": None if not promoted else promoted.get("id"),
  }
  out_path.parent.mkdir(parents=True, exist_ok=True)
  out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
  print(json.dumps({
    "winner": payload["winner"]["name"] if payload["winner"] else None,
    "beats_wr_and_rr": payload["beats_wr_and_rr"],
    "deltas_vs_baseline": deltas,
    "path": str(out_path),
  }, indent=2, ensure_ascii=False), flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
