#!/usr/bin/env python3
"""Independent AIEdge vs TrainApp-quality evaluation (see PROTOCOL.md)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
LIVECHECK = ROOT.parent
TRAINAPP = LIVECHECK / "TrainApp"
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

PROTOCOL = {
  "name": "IndependentEval-v1",
  "validate": {"from": "2025-07-01", "to": "2025-12-31"},
  "test": {"from": "2026-01-01", "to": "2026-08-07"},
  "slippage_pips": 0.3,
  "search_space": [
    {"preset": "elite_or_quality", "train_weeks": 6, "cost_gate_mult": None},
    {"preset": "anti_chase_fixed_70", "train_weeks": 6, "cost_gate_mult": None},
    {"preset": "elite_or_quality", "train_weeks": 6, "cost_gate_mult": 3.5},
    {"preset": "elite_or_quality", "train_weeks": 3, "cost_gate_mult": None},
  ],
  "cost_regimes": {
    "yaml": {"EURUSD": 1.0, "GBPUSD": 1.5},
    "realistic": {"EURUSD": 1.6, "GBPUSD": 2.0},
  },
  "desks": {
    "e21": {"pair": "EURUSD", "tf": "M15"},
    "g23": {"pair": "GBPUSD", "tf": "M15"},
    "e31": {"pair": "EURUSD", "tf": "M5"},
    "g33": {"pair": "GBPUSD", "tf": "M5"},
  },
}

_MOD_PREFIXES = (
  "config",
  "data_loader",
  "feature_engine",
  "strategy",
  "strategy_miner",
  "optimizer",
  "knowledge_base",
  "kb_profiles",
  "meta_learner",
  "ml_scorer",
  "app_paths",
  "mining_presets",
  "mt5_bridge",
  "trade_model",
  "trade_model_schedule",
  "trade_model_kb_pin",
  "evolution",
  "execution",
)


def _purge() -> None:
  doomed = [
    n
    for n in list(sys.modules)
    if n == "gui"
    or n.startswith("gui.")
    or any(n == p or n.startswith(p + ".") for p in _MOD_PREFIXES)
  ]
  for n in doomed:
    sys.modules.pop(n, None)


def _activate(desk_id: str) -> dict[str, Any]:
  sys.path.insert(0, str(TRAINAPP))
  from desk_context import apply_desk_env  # type: ignore

  cfg = apply_desk_env(desk_id)
  core = Path(cfg["core_root"])
  _purge()
  for p in (str(core), str(TRAINAPP / "gui"), str(TRAINAPP)):
    while p in sys.path:
      sys.path.remove(p)
  sys.path[:0] = [str(core), str(TRAINAPP / "gui"), str(TRAINAPP)]
  os.environ["TRAINAPP_ROOT"] = str(TRAINAPP)
  os.environ["TRAINAPP_RUNTIME"] = cfg["runtime_root"]
  os.environ["TRAINAPP_DESK"] = cfg["id"]
  os.environ["TRAINAPP_CORE"] = core.name
  return cfg


def _robust(total_r: float, dd: float, wr: float) -> float:
  return (total_r / max(dd, 1.0)) - 0.05 * max(0.0, 55.0 - wr)


def _quality(total_r: float, dd: float, wr: float, pf: float) -> float:
  return (total_r / max(dd, 0.5)) * 2.0 + pf * 25.0 + wr * 0.8 + total_r * 0.04


def _metrics_dict(trades) -> dict[str, Any]:
  from strategy import compute_metrics  # type: ignore

  m = compute_metrics(trades)
  wr = float(m.get("win_rate") or 0) * 100.0
  tot = float(m.get("total_r") or 0)
  dd = float(m.get("max_drawdown_r") or 0)
  pf = float(m.get("profit_factor") or 0)
  if pf == float("inf"):
    pf = 999.0
  return {
    "n_trades": int(m.get("n_trades") or 0),
    "total_r": round(tot, 3),
    "win_rate_pct": round(wr, 2),
    "avg_rr": round(float(m.get("avg_rr") or 0), 3),
    "max_drawdown_r": round(dd, 3),
    "profit_factor": round(pf, 3),
    "robust_score": round(_robust(tot, dd, wr), 3),
    "quality_score": round(_quality(tot, dd, wr, pf), 3),
  }


def _weekly_bounds(df, start: str, end: str):
  import pandas as pd

  s = pd.Timestamp(start)
  e = pd.Timestamp(end) + pd.Timedelta(days=1)
  cur = s - pd.Timedelta(days=int(s.weekday()))
  out = []
  while cur < e:
    nxt = cur + pd.Timedelta(days=7)
    if nxt > s and cur < e:
      a = max(cur, s)
      b = min(nxt, e)
      if a < b and ((df.index >= a) & (df.index < b)).any():
        out.append((a, b))
    cur = nxt
  return out


def _apply_cost_gate(fm, sig, *, spread_pips: float, mult: float):
  import numpy as np

  atr = np.asarray(fm.atr, dtype=float)
  atr_pips = atr / 0.0001
  out = np.asarray(sig, dtype=int).copy()
  n = min(len(out), len(atr_pips))
  thin = atr_pips[:n] < (float(spread_pips) * float(mult))
  out[:n][thin] = 0
  return out


def _cell_key(cell: dict) -> str:
  g = cell.get("cost_gate_mult")
  return f"{cell['preset']}|tw{cell['train_weeks']}|gate{g}"


def run_wf(
  desk_id: str,
  *,
  window_from: str,
  window_to: str,
  train_weeks: int,
  preset: str,
  spread_pips: float,
  slip: float,
  cost_gate_mult: float | None,
) -> dict[str, Any]:
  _activate(desk_id)
  from data_loader import load_eurusd_m15, get_train_window_indices  # type: ignore
  from feature_engine import FeatureMatrix  # type: ignore
  from mining_presets import get_preset  # type: ignore
  from optimizer import get_knowledge_base, optimize_on_window, reset_kb_cache  # type: ignore
  from strategy_miner import (  # type: ignore
    backtest_mined,
    generate_signals_mined,
    mining_search_space_from_dict,
  )

  df = load_eurusd_m15()
  fm = FeatureMatrix(df)
  reset_kb_cache()
  kb = get_knowledge_base()
  space = mining_search_space_from_dict(get_preset(preset))
  weeks = _weekly_bounds(df, window_from, window_to)
  all_trades = []
  last_name = None
  for w0, w1 in weeks:
    tr_s, tr_e = get_train_window_indices(df, w0, train_weeks)
    if tr_s is None:
      continue
    strat = optimize_on_window(
      fm, tr_s, tr_e, use_learning=True, as_of=w0, kb=kb, search_space=space
    )
    if strat is None:
      continue
    last_name = getattr(strat, "name", None)
    week_mask = (df.index >= w0) & (df.index < w1)
    if not week_mask.any():
      continue
    te_s = int(df.index.get_loc(df.index[week_mask][0]))
    te_e = int(df.index.get_loc(df.index[week_mask][-1])) + 1
    sig = generate_signals_mined(fm, strat, te_s, te_e)
    if cost_gate_mult is not None:
      sig = _apply_cost_gate(fm, sig, spread_pips=spread_pips, mult=float(cost_gate_mult))
    trades = backtest_mined(
      fm, strat, sig, te_s, te_e, spread_pips=spread_pips, slippage_pips=slip
    )
    all_trades.extend(trades)

  return {
    "metrics": _metrics_dict(all_trades),
    "n_weeks": len(weeks),
    "last_strategy_name": last_name,
    "preset": preset,
    "train_weeks": train_weeks,
    "cost_gate_mult": cost_gate_mult,
    "spread_pips": spread_pips,
  }


def select_aiedge(candidates: list[dict]) -> dict[str, Any]:
  gated = []
  for c in candidates:
    m = c["validate"]
    if (
      m["n_trades"] >= 20
      and m["win_rate_pct"] >= 42.0
      and m["max_drawdown_r"] <= 14.0
      and m["total_r"] > 0
    ):
      gated.append(c)
  pool = gated if gated else candidates
  best = max(pool, key=lambda c: float(c["validate"]["robust_score"]))
  return {
    "policy": "aiedge",
    "cell": best["cell"],
    "key": best["key"],
    "validate": best["validate"],
    "soft_fallback": not bool(gated),
  }


def select_trainapp_quality(candidates: list[dict]) -> dict[str, Any]:
  gated = []
  for c in candidates:
    m = c["validate"]
    if m["total_r"] > 0 and m["profit_factor"] >= 1.2:
      gated.append(c)
  pool = gated if gated else candidates
  best = max(pool, key=lambda c: float(c["validate"]["quality_score"]))
  return {
    "policy": "trainapp_quality",
    "cell": best["cell"],
    "key": best["key"],
    "validate": best["validate"],
    "soft_fallback": not bool(gated),
  }


def decide_test(a: dict, b: dict) -> dict[str, Any]:
  """PROTOCOL.md winner rules — registered before runs."""
  ar, br = float(a["total_r"]), float(b["total_r"])
  add, bdd = float(a["max_drawdown_r"]), float(b["max_drawdown_r"])
  a_profit, b_profit = ar > 0, br > 0

  def pack(winner: str, reason: str) -> dict[str, Any]:
    return {
      "winner": winner,
      "reason": reason,
      "aiedge_total_r": ar,
      "trainapp_total_r": br,
      "aiedge_dd": add,
      "trainapp_dd": bdd,
      "aiedge_profit": a_profit,
      "trainapp_profit": b_profit,
      "both_nonpositive": (not a_profit) and (not b_profit),
    }

  # Rule 1
  if ar > br and add <= bdd + 5:
    return pack("aiedge", "higher total_r and DD <= other+5")
  if br > ar and bdd <= add + 5:
    return pack("trainapp_quality", "higher total_r and DD <= other+5")
  # Rule 2
  if ar >= br + 10 and add <= bdd + 10:
    return pack("aiedge", "total_r lead >=10R and DD within +10")
  if br >= ar + 10 and bdd <= add + 10:
    return pack("trainapp_quality", "total_r lead >=10R and DD within +10")
  # Rule 3
  if abs(ar - br) < 5 and abs(add - bdd) < 5:
    return pack("tie", "|ΔR|<5 and |ΔDD|<5")
  # Rule 4
  less = "aiedge" if ar > br else "trainapp_quality" if br > ar else "tie"
  return pack(
    "inconclusive",
    f"no clear win under rules; less_negative_or_higher={less}",
  )


def _ckpt_path(desk_id: str, regime: str) -> Path:
  return RESULTS / f"ckpt_{desk_id}_{regime}.json"


def evaluate_desk(desk_id: str, regime: str, *, cells: list[dict] | None = None) -> dict[str, Any]:
  meta = PROTOCOL["desks"][desk_id]
  pair = meta["pair"]
  spread = float(PROTOCOL["cost_regimes"][regime][pair])
  slip = float(PROTOCOL["slippage_pips"])
  cells = cells or PROTOCOL["search_space"]
  va, te = PROTOCOL["validate"], PROTOCOL["test"]

  ckpt = _ckpt_path(desk_id, regime)
  state: dict[str, Any] = {"desk": desk_id, "regime": regime, "spread_pips": spread}
  if ckpt.exists():
    state = json.loads(ckpt.read_text(encoding="utf-8"))
    print(f"  resume {ckpt.name}", flush=True)

  # Shared VALIDATE grid (both policies select from same runs)
  grid: dict[str, Any] = state.get("validate_grid") or {}
  candidates: list[dict] = []
  for cell in cells:
    key = _cell_key(cell)
    if key not in grid:
      print(f"  VALIDATE {desk_id} {key} @ {spread}pip …", flush=True)
      t0 = time.time()
      res = run_wf(
        desk_id,
        window_from=va["from"],
        window_to=va["to"],
        train_weeks=int(cell["train_weeks"]),
        preset=str(cell["preset"]),
        spread_pips=spread,
        slip=slip,
        cost_gate_mult=cell.get("cost_gate_mult"),
      )
      grid[key] = {
        "cell": cell,
        "key": key,
        "validate": res["metrics"],
        "elapsed_s": round(time.time() - t0, 1),
        "n_weeks": res["n_weeks"],
      }
      state["validate_grid"] = grid
      ckpt.write_text(json.dumps(state, indent=2), encoding="utf-8")
      print(f"    -> {res['metrics']} ({grid[key]['elapsed_s']}s)", flush=True)
    candidates.append(grid[key])

  pick_a = select_aiedge(candidates)
  pick_b = select_trainapp_quality(candidates)
  state["picks"] = {"aiedge": pick_a, "trainapp_quality": pick_b}
  ckpt.write_text(json.dumps(state, indent=2), encoding="utf-8")
  print(
    f"  picks: aiedge={pick_a['key']} soft={pick_a['soft_fallback']} | "
    f"trainapp={pick_b['key']} soft={pick_b['soft_fallback']}",
    flush=True,
  )

  # TEST once per distinct pick
  tests: dict[str, Any] = state.get("tests") or {}
  for label, pick in (("aiedge", pick_a), ("trainapp_quality", pick_b)):
    key = pick["key"]
    tkey = f"{label}::{key}"
    if tkey in tests:
      continue
    # Reuse if other policy already tested same cell
    reuse = next((v for k, v in tests.items() if k.endswith(f"::{key}")), None)
    if reuse is not None:
      tests[tkey] = dict(reuse)
      tests[tkey]["reused_from_same_cell"] = True
      continue
    cell = pick["cell"]
    print(f"  TEST {desk_id} {label} {key} @ {spread}pip …", flush=True)
    t0 = time.time()
    res = run_wf(
      desk_id,
      window_from=te["from"],
      window_to=te["to"],
      train_weeks=int(cell["train_weeks"]),
      preset=str(cell["preset"]),
      spread_pips=spread,
      slip=slip,
      cost_gate_mult=cell.get("cost_gate_mult"),
    )
    tests[tkey] = {
      "policy": label,
      "key": key,
      "cell": cell,
      "test": res["metrics"],
      "elapsed_s": round(time.time() - t0, 1),
    }
    state["tests"] = tests
    ckpt.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"    -> {res['metrics']} ({tests[tkey]['elapsed_s']}s)", flush=True)

  state["tests"] = tests

  def _test_for(label: str, pick: dict) -> dict:
    tkey = f"{label}::{pick['key']}"
    if tkey not in tests:
      raise RuntimeError(f"missing TEST artifact {tkey}")
    return tests[tkey]["test"]

  a_test = _test_for("aiedge", pick_a)
  b_test = _test_for("trainapp_quality", pick_b)
  decision = decide_test(a_test, b_test)
  out = {
    "desk": desk_id,
    "pair": pair,
    "tf": meta["tf"],
    "regime": regime,
    "spread_pips": spread,
    "picks": state["picks"],
    "validate_grid": {k: {"key": v["key"], "validate": v["validate"]} for k, v in grid.items()},
    "test": {"aiedge": a_test, "trainapp_quality": b_test},
    "decision": decision,
  }
  state["result"] = out
  ckpt.write_text(json.dumps(state, indent=2), encoding="utf-8")
  return out


def _md(report: dict) -> str:
  lines = [
    "# IndependentEval Report",
    "",
    f"Generated: `{report['generated_at']}`",
    "",
    "Protocol: see `PROTOCOL.md` (locked before run).",
    "",
    f"**Primary regime:** `{report['primary_regime']}`",
    "",
    "## Verdict (measured)",
    "",
  ]
  s = report["summary"]
  lines += [
    f"- Desk wins: AIEdge **{s['aiedge_wins']}** · TrainApp-quality **{s['trainapp_wins']}** · "
    f"tie **{s['ties']}** · inconclusive **{s['inconclusive']}**",
    f"- Profitable desks (TEST R>0): AIEdge **{s['aiedge_profit_desks']}** · "
    f"TrainApp-quality **{s['trainapp_profit_desks']}**",
    f"- Claim: **{s['claim']}**",
    "",
    "## Per desk",
    "",
  ]
  for d in report["desks"]:
    dec = d["decision"]
    lines += [
      f"### {d['desk'].upper()} · {d['pair']} {d['tf']} @ {d['spread_pips']}pip ({d['regime']})",
      "",
      f"- Winner: **{dec['winner']}** — {dec['reason']}",
      f"- AIEdge pick `{d['picks']['aiedge']['key']}` soft={d['picks']['aiedge']['soft_fallback']} "
      f"→ TEST R={d['test']['aiedge']['total_r']} WR={d['test']['aiedge']['win_rate_pct']} "
      f"DD={d['test']['aiedge']['max_drawdown_r']} n={d['test']['aiedge']['n_trades']}",
      f"- TrainApp-quality pick `{d['picks']['trainapp_quality']['key']}` "
      f"soft={d['picks']['trainapp_quality']['soft_fallback']} "
      f"→ TEST R={d['test']['trainapp_quality']['total_r']} "
      f"WR={d['test']['trainapp_quality']['win_rate_pct']} "
      f"DD={d['test']['trainapp_quality']['max_drawdown_r']} "
      f"n={d['test']['trainapp_quality']['n_trades']}",
      "",
    ]
  lines += [
    "## Caveats",
    "",
    "- Mining is stochastic; single seed/run — not a multi-seed distribution.",
    "- Compares **selection policies** on a shared WF search space, not full TrainApp GUI promote stack.",
    "- Does not evaluate TrainApp models that were ranked on the TEST window itself.",
    "",
  ]
  return "\n".join(lines)


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--desks", default="e21,g23,e31,g33")
  ap.add_argument("--regime", default="realistic", choices=["realistic", "yaml", "both"])
  ap.add_argument("--quick", action="store_true", help="2-cell search space only")
  args = ap.parse_args()

  desks = [d.strip().lower() for d in args.desks.split(",") if d.strip()]
  regimes = ["realistic", "yaml"] if args.regime == "both" else [args.regime]
  cells = PROTOCOL["search_space"]
  if args.quick:
    cells = cells[:2]

  primary = regimes[0]
  all_results: list[dict] = []
  for regime in regimes:
    for desk_id in desks:
      print(f"=== {desk_id} / {regime} ===", flush=True)
      all_results.append(evaluate_desk(desk_id, regime, cells=cells))

  primary_rows = [r for r in all_results if r["regime"] == primary]
  aw = sum(1 for r in primary_rows if r["decision"]["winner"] == "aiedge")
  tw = sum(1 for r in primary_rows if r["decision"]["winner"] == "trainapp_quality")
  ties = sum(1 for r in primary_rows if r["decision"]["winner"] == "tie")
  inc = sum(1 for r in primary_rows if r["decision"]["winner"] == "inconclusive")
  ap_ = sum(1 for r in primary_rows if r["decision"]["aiedge_profit"])
  tp_ = sum(1 for r in primary_rows if r["decision"]["trainapp_profit"])

  if aw > tw and ap_ >= tp_:
    claim = "AIEdge selection policy wins under IndependentEval-v1"
  elif tw > aw and tp_ >= ap_:
    claim = "TrainApp-quality selection policy wins under IndependentEval-v1"
  elif ap_ > tp_:
    claim = "No clear desk-win lead; AIEdge more often profitable on TEST"
  elif tp_ > ap_:
    claim = "No clear desk-win lead; TrainApp-quality more often profitable on TEST"
  else:
    claim = "No decisive winner under IndependentEval-v1"

  report = {
    "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "protocol": PROTOCOL["name"],
    "primary_regime": primary,
    "desks_requested": desks,
    "regimes": regimes,
    "quick": bool(args.quick),
    "summary": {
      "aiedge_wins": aw,
      "trainapp_wins": tw,
      "ties": ties,
      "inconclusive": inc,
      "aiedge_profit_desks": ap_,
      "trainapp_profit_desks": tp_,
      "claim": claim,
    },
    "desks": primary_rows,
    "all_runs": all_results,
  }
  (RESULTS / "indep_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
  (RESULTS / "INDEP_REPORT.md").write_text(_md(report), encoding="utf-8")
  print("\n" + claim, flush=True)
  print(f"Wrote {RESULTS / 'INDEP_REPORT.md'}", flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
