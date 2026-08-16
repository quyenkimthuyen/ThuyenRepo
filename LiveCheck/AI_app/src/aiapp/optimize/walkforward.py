"""AIEdge vs TrainApp — fair walk-forward under identical costs & no era overlap."""
from __future__ import annotations

from typing import Any

import pandas as pd

from aiapp.compare.harness import _robust, decide_winner
from aiapp.config import Desk, load_protocol
from aiapp.optimize.protocol_mine import (
  _load_df,
  _metrics_dict,
  _passes_validate,
  _strategy_brief,
)


def _weekly_bounds(df: pd.DataFrame, start: str, end: str) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
  s = pd.Timestamp(start)
  e = pd.Timestamp(end) + pd.Timedelta(days=1)
  cur = s - pd.Timedelta(days=int(s.weekday()))
  out: list[tuple[pd.Timestamp, pd.Timestamp]] = []
  while cur < e:
    nxt = cur + pd.Timedelta(days=7)
    if nxt > s and cur < e:
      a = max(cur, s)
      b = min(nxt, e)
      if a < b and ((df.index >= a) & (df.index < b)).any():
        out.append((a, b))
    cur = nxt
  return out


def _space_from_preset(name: str | None):
  from mining_presets import get_preset  # type: ignore
  from strategy_miner import MiningSearchSpace, mining_search_space_from_dict  # type: ignore

  if not name:
    return MiningSearchSpace()
  return mining_search_space_from_dict(get_preset(name))


def _apply_cost_gate(fm, sig, *, spread_pips: float, min_atr_spread_mult: float = 3.5):
  """AIEdge-only: block entries when ATR is too small vs spread (cost survival)."""
  import numpy as np

  pip = 0.0001
  atr = np.asarray(fm.atr, dtype=float)
  atr_pips = atr / pip
  out = np.asarray(sig, dtype=int).copy()
  n = min(len(out), len(atr_pips))
  thin = atr_pips[:n] < (float(spread_pips) * float(min_atr_spread_mult))
  out[:n][thin] = 0
  return out


def _run_wf(
  desk: Desk,
  *,
  window_from: str,
  window_to: str,
  train_weeks: int,
  preset: str | None,
  slip: float,
  remine_each_week: bool = True,
  use_learning: bool = True,
  cost_gate: bool = False,
  cost_gate_mult: float = 3.5,
) -> dict[str, Any]:
  from feature_engine import FeatureMatrix  # type: ignore
  from optimizer import get_knowledge_base, optimize_on_window, reset_kb_cache  # type: ignore
  from strategy_miner import backtest_mined, generate_signals_mined  # type: ignore

  reset_kb_cache()
  kb = None
  learning = use_learning
  if learning:
    try:
      kb = get_knowledge_base()
    except Exception:
      learning = False
      kb = None

  space = _space_from_preset(preset)
  df = _load_df(desk)
  fm = FeatureMatrix(df)
  weeks = _weekly_bounds(df, window_from, window_to)
  all_trades = []
  frozen = None
  last_brief = None

  for w0, w1 in weeks:
    train_end = w0
    train_start = train_end - pd.Timedelta(weeks=train_weeks)
    mask = (df.index >= train_start) & (df.index < train_end)
    if int(mask.sum()) < 400:
      continue
    tr_s = int(df.index.get_loc(df.index[mask][0]))
    tr_e = int(df.index.get_loc(df.index[mask][-1])) + 1

    if remine_each_week or frozen is None:
      strat = optimize_on_window(
        fm,
        tr_s,
        tr_e,
        use_learning=learning,
        as_of=w0,
        kb=kb,
        search_space=space,
      )
      if strat is None:
        continue
      frozen = strat
      last_brief = _strategy_brief(strat)
    else:
      strat = frozen

    week_mask = (df.index >= w0) & (df.index < w1)
    if not week_mask.any():
      continue
    te_s = int(df.index.get_loc(df.index[week_mask][0]))
    te_e = int(df.index.get_loc(df.index[week_mask][-1])) + 1
    sig = generate_signals_mined(fm, strat, te_s, te_e)
    if cost_gate:
      sig = _apply_cost_gate(
        fm, sig, spread_pips=desk.spread_pips, min_atr_spread_mult=cost_gate_mult
      )
    trades = backtest_mined(
      fm, strat, sig, te_s, te_e, spread_pips=desk.spread_pips, slippage_pips=slip
    )
    all_trades.extend(trades)

  return {
    "metrics": _metrics_dict(all_trades),
    "n_weeks": len(weeks),
    "last_strategy": last_brief,
    "use_learning": learning,
    "preset": preset,
    "train_weeks": train_weeks,
    "cost_gate": cost_gate,
  }


def _select_grid() -> list[tuple[str | None, int, float | None]]:
  # (preset, train_weeks, cost_gate_mult|None) — compact for overnight proof
  return [
    ("elite_or_quality", 6, None),
    ("anti_chase_fixed_70", 6, None),
    ("elite_or_quality", 6, 3.5),
  ]


def _trainapp_default() -> tuple[str | None, int]:
  return ("elite_or_quality", 6)


def select_hyperparams(desk: Desk, protocol: dict | None = None) -> dict[str, Any]:
  protocol = protocol or load_protocol()
  proto = protocol.get("protocol") or protocol
  slip = float(proto.get("default_slippage_pips") or 0.3)
  va = proto["validate"]

  ranked: list[tuple[float, dict]] = []
  all_tried: list[tuple[float, dict]] = []
  for preset, train_weeks, gate_mult in _select_grid():
    print(
      f"  select {desk.id}: preset={preset} tw={train_weeks} gate={gate_mult} …",
      flush=True,
    )
    res = _run_wf(
      desk,
      window_from=va["from"],
      window_to=va["to"],
      train_weeks=train_weeks,
      preset=preset,
      slip=slip,
      remine_each_week=True,
      use_learning=True,
      cost_gate=gate_mult is not None,
      cost_gate_mult=float(gate_mult or 3.5),
    )
    m = res["metrics"]
    ok = _passes_validate(m, proto)
    score = float(m.get("robust_score") or -1e9)
    print(f"    {'ok' if ok else 'reject'} score={score} {m}", flush=True)
    cand = {
      "preset": preset,
      "train_weeks": train_weeks,
      "cost_gate_mult": gate_mult,
      "validate": m,
      "use_learning": res.get("use_learning"),
    }
    all_tried.append((score, cand))
    if ok:
      ranked.append((score, cand))

  if ranked:
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1]

  # Soft fallback: reuse already-scored candidates (no second WF pass)
  all_tried.sort(key=lambda x: x[0], reverse=True)
  best = dict(all_tried[0][1])
  best["soft_fallback"] = True
  print(f"  soft_fallback -> {best.get('preset')} tw={best.get('train_weeks')}", flush=True)
  return best


def run_desk_proof_wf(desk: Desk, protocol: dict | None = None) -> dict[str, Any]:
  protocol = protocol or load_protocol()
  proto = protocol.get("protocol") or protocol
  slip = float(proto.get("default_slippage_pips") or 0.3)
  te = proto["test"]

  picked = select_hyperparams(desk, protocol)
  gate = picked.get("cost_gate_mult")
  print(
    f"  AIEdge pick: preset={picked.get('preset')} tw={picked.get('train_weeks')} gate={gate}",
    flush=True,
  )
  ai_test = _run_wf(
    desk,
    window_from=te["from"],
    window_to=te["to"],
    train_weeks=int(picked["train_weeks"]),
    preset=picked.get("preset"),
    slip=slip,
    remine_each_week=True,
    use_learning=True,
    cost_gate=gate is not None,
    cost_gate_mult=float(gate or 3.5),
  )

  ta_preset, ta_tw = _trainapp_default()
  print(
    f"  TrainApp-fair baseline: preset={ta_preset} tw={ta_tw} @ spread={desk.spread_pips}",
    flush=True,
  )
  ta_test = _run_wf(
    desk,
    window_from=te["from"],
    window_to=te["to"],
    train_weeks=ta_tw,
    preset=ta_preset,
    slip=slip,
    remine_each_week=True,
    use_learning=True,
    cost_gate=False,
  )

  aiedge = {
    "desk": desk.id,
    "system": "AIEdge-ValidateSelect-CostGate-WF",
    "space": picked.get("preset"),
    "params": {
      "preset": picked.get("preset"),
      "train_weeks": picked.get("train_weeks"),
      "cost_gate_mult": gate,
      "selection": "validate_wf_robust_score",
      "soft_fallback": bool(picked.get("soft_fallback")),
      "last_strategy": ai_test.get("last_strategy"),
    },
    "param_key": f"wf|{picked.get('preset')}|tw{picked.get('train_weeks')}|gate{gate}",
    "validate": picked.get("validate"),
    "test": ai_test["metrics"],
  }
  baseline = {
    "source": "fair_wf_same_cost",
    "label": f"TrainApp default {ta_preset} tw{ta_tw} @ {desk.spread_pips}pip (no cost-gate)",
    "metrics_raw": ta_test["metrics"],
    "metrics": ta_test["metrics"],
    "note": (
      "Re-simulated under AIEdge protocol costs on the locked TEST window. "
      "Published TrainApp grid rows that train on overlapping 2025-2026 eras are NOT used."
    ),
  }
  decision = decide_winner(aiedge.get("test") or {}, baseline)
  return {
    "desk": desk.id,
    "pair": desk.pair,
    "tf": desk.tf,
    "aiedge_cost_spread_pips": desk.spread_pips,
    "aiedge": aiedge,
    "trainapp_baseline": baseline,
    "decision": decision,
  }
