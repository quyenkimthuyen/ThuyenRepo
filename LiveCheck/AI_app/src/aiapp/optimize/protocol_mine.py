"""AIEdge protocol miner — TrainApp genomes under locked train/validate/test + realistic costs."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from aiapp.compare.harness import _robust, decide_winner, load_trainapp_baseline
from aiapp.config import RESULTS, Desk, load_protocol


def _core_paths(desk: Desk) -> tuple[Path, Path]:
  root = Path(r"C:\Work\ThuyenRepo\LiveCheck\TrainApp")
  core_name = "m5" if desk.tf.upper() == "M5" else "m15"
  return root, root / "cores" / core_name


_TRAINAPP_MOD_PREFIXES = (
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
)


def _purge_trainapp_modules() -> None:
  doomed = [
    name
    for name in list(sys.modules)
    if name == "gui"
    or name.startswith("gui.")
    or any(name == p or name.startswith(p + ".") for p in _TRAINAPP_MOD_PREFIXES)
  ]
  for name in doomed:
    sys.modules.pop(name, None)


def _activate_trainapp(desk: Desk) -> Path:
  root, core = _core_paths(desk)
  runtime = desk.trainapp_runtime
  os.environ["TRAINAPP_ROOT"] = str(root)
  os.environ["TRAINAPP_RUNTIME"] = str(runtime)
  os.environ["TRAINAPP_DESK"] = desk.id
  os.environ["TRAINAPP_CORE"] = core.name
  _purge_trainapp_modules()
  # Core must win import resolution for this desk
  for p in (str(core), str(root / "gui"), str(root)):
    while p in sys.path:
      sys.path.remove(p)
  sys.path[:0] = [str(core), str(root / "gui"), str(root)]
  return core


def _load_df(desk: Desk):
  """Load OHLC from the desk runtime MT5 cache (loader name is legacy)."""
  _activate_trainapp(desk)
  from data_loader import load_eurusd_m15  # type: ignore

  return load_eurusd_m15()


def _idx_range(df: pd.DataFrame, start: str, end: str) -> tuple[int, int]:
  sl = df.loc[start:end]
  if sl.empty:
    raise ValueError(f"Empty slice {start}..{end}")
  return int(df.index.get_loc(sl.index[0])), int(df.index.get_loc(sl.index[-1])) + 1


def _metrics_dict(trades) -> dict[str, Any]:
  from strategy import compute_metrics  # type: ignore

  m = compute_metrics(trades)
  wr = float(m.get("win_rate") or 0) * 100.0
  tot = float(m.get("total_r") or 0)
  dd = float(m.get("max_drawdown_r") or 0)
  return {
    "n_trades": int(m.get("n_trades") or 0),
    "total_r": round(tot, 3),
    "win_rate_pct": round(wr, 2),
    "avg_rr": round(float(m.get("avg_rr") or 0), 3),
    "max_drawdown_r": round(dd, 3),
    "profit_factor": round(float(m.get("profit_factor") or 0), 3)
    if (m.get("profit_factor") or 0) != float("inf")
    else 999.0,
    "robust_score": round(_robust(tot, dd, wr), 3),
  }


def _strategy_brief(strat) -> dict[str, Any]:
  return {
    "name": getattr(strat, "name", None),
    "rr": getattr(strat, "rr_ratio", None),
    "atr_mult": getattr(strat, "atr_mult_sl", None),
    "ml_prob_min": getattr(strat, "ml_prob_min", None),
    "score_threshold": getattr(strat, "score_threshold", None),
    "max_hold_bars": getattr(strat, "max_hold_bars", None),
    "min_bars_between": getattr(strat, "min_bars_between", None),
    "n_long_rules": len(getattr(strat, "long_rules", []) or []),
    "n_short_rules": len(getattr(strat, "short_rules", []) or []),
    "anti_chase": getattr(strat, "anti_chase", None),
    "exit_mode": getattr(strat, "exit_mode", None),
  }


def _candidate_spaces():
  from strategy_miner import MiningSearchSpace  # type: ignore

  # Compact spaces designed for cost survival + locked protocol (no test peek).
  return [
    (
      "elite_fixed_chase",
      MiningSearchSpace(
        rr_ratios=(2.5, 3.0),
        atr_multipliers=(0.9, 1.05),
        score_thresholds=(1.0, 1.6, 2.2),
        min_rules_matches=(1, 2),
        ml_probability_thresholds=(0.0, 0.36, 0.40),
        selection_mode="elite_frontier",
        anti_chase=True,
        anti_chase_mode="fixed",
        exit_modes_full_only=True,
      ),
    ),
    (
      "quality_trail",
      MiningSearchSpace(
        rr_ratios=(2.5,),
        atr_multipliers=(0.9, 1.05),
        score_thresholds=(0.6, 1.0, 1.6),
        min_rules_matches=(1, 2),
        ml_probability_thresholds=(0.0, 0.40),
        selection_mode="expectancy_frontier",
        anti_chase=True,
        anti_chase_mode="fixed",
        exit_modes_full_only=False,
      ),
    ),
    (
      "baseline_full",
      MiningSearchSpace(
        rr_ratios=(2.5, 3.0),
        atr_multipliers=(0.9,),
        score_thresholds=(1.0, 1.6),
        min_rules_matches=(2,),
        ml_probability_thresholds=(0.0, 0.40),
        selection_mode="legacy",
        exit_modes_full_only=True,
      ),
    ),
  ]


def _passes_validate(m: dict, proto: dict) -> bool:
  return (
    int(m.get("n_trades") or 0) >= int(proto.get("min_validate_trades") or 20)
    and float(m.get("win_rate_pct") or 0) >= float(proto.get("min_validate_wr") or 42)
    and float(m.get("max_drawdown_r") or 999) <= float(proto.get("max_validate_dd") or 14)
    and float(m.get("total_r") or 0) > 0
  )


def optimize_desk_protocol(desk: Desk, protocol: dict | None = None) -> dict[str, Any]:
  """Mine on train only; select on validate only; return model (test not yet run)."""
  protocol = protocol or load_protocol()
  proto = protocol.get("protocol") or protocol
  slip = float(proto.get("default_slippage_pips") or 0.3)

  from feature_engine import FeatureMatrix  # type: ignore
  from strategy_miner import (  # type: ignore
    backtest_mined,
    generate_signals_mined,
    mine_strategy,
  )

  df = _load_df(desk)
  fm = FeatureMatrix(df)
  tr_s, tr_e = _idx_range(df, proto["train"]["from"], proto["train"]["to"])
  va_s, va_e = _idx_range(df, proto["validate"]["from"], proto["validate"]["to"])

  candidates: list[tuple[float, Any, dict, dict, str]] = []
  for space_name, space in _candidate_spaces():
    strat = mine_strategy(fm, tr_s, tr_e, search_space=space)
    if strat is None:
      continue
    # Soft train sanity
    sig_tr = generate_signals_mined(fm, strat, tr_s, tr_e)
    tr_m = _metrics_dict(
      backtest_mined(
        fm, strat, sig_tr, tr_s, tr_e, spread_pips=desk.spread_pips, slippage_pips=slip
      )
    )
    if float(tr_m.get("total_r") or 0) < -30:
      continue
    sig_va = generate_signals_mined(fm, strat, va_s, va_e)
    va_m = _metrics_dict(
      backtest_mined(
        fm, strat, sig_va, va_s, va_e, spread_pips=desk.spread_pips, slippage_pips=slip
      )
    )
    if not _passes_validate(va_m, proto):
      continue
    score = float(va_m.get("robust_score") or -1e9)
    candidates.append((score, strat, tr_m, va_m, space_name))

  if not candidates:
    raise RuntimeError(f"{desk.id}: no mined candidate passed validate gates")

  candidates.sort(key=lambda x: x[0], reverse=True)
  score, best, tr_m, va_m, space_name = candidates[0]
  return {
    "desk": desk.id,
    "system": "AIEdge-ProtocolMine",
    "space": space_name,
    "params": _strategy_brief(best),
    "param_key": f"{space_name}|{best.name}",
    "train": tr_m,
    "validate": va_m,
    "test": None,
    "_strat": best,
    "_fm_ready": True,
  }


def evaluate_test(desk: Desk, model: dict, protocol: dict | None = None) -> dict[str, Any]:
  protocol = protocol or load_protocol()
  proto = protocol.get("protocol") or protocol
  slip = float(proto.get("default_slippage_pips") or 0.3)
  strat = model.get("_strat")
  if strat is None:
    raise RuntimeError("model missing strategy object")

  from feature_engine import FeatureMatrix  # type: ignore
  from strategy_miner import backtest_mined, generate_signals_mined  # type: ignore

  df = _load_df(desk)
  fm = FeatureMatrix(df)
  te_s, te_e = _idx_range(df, proto["test"]["from"], proto["test"]["to"])
  sig = generate_signals_mined(fm, strat, te_s, te_e)
  trades = backtest_mined(
    fm, strat, sig, te_s, te_e, spread_pips=desk.spread_pips, slippage_pips=slip
  )
  model["test"] = _metrics_dict(trades)
  # strip non-json
  clean = {k: v for k, v in model.items() if not k.startswith("_")}
  return clean


def run_desk_proof(desk: Desk, protocol: dict | None = None) -> dict[str, Any]:
  protocol = protocol or load_protocol()
  model = optimize_desk_protocol(desk, protocol)
  clean = evaluate_test(desk, model, protocol)
  baseline = load_trainapp_baseline(desk)
  decision = decide_winner(clean.get("test") or {}, baseline)
  return {
    "desk": desk.id,
    "pair": desk.pair,
    "tf": desk.tf,
    "aiedge_cost_spread_pips": desk.spread_pips,
    "aiedge": clean,
    "trainapp_baseline": baseline,
    "decision": decision,
  }
