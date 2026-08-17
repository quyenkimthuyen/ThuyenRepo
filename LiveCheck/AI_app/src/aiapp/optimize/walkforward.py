"""AIEdge vs TrainApp — fair walk-forward under identical costs & no era overlap."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from aiapp.compare.harness import decide_winner, load_trainapp_baseline
from aiapp.config import RESULTS, Desk, load_protocol
from aiapp.optimize.protocol_mine import (
  _load_df,
  _metrics_dict,
  _passes_validate,
  _strategy_brief,
)

CACHE_DIR = RESULTS / "wf_cache"


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


def _apply_cost_gate(fm, sig, *, spread_pips: float, min_atr_spread_mult: float = 2.5):
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


def _select_score(m: dict, *, min_trades: int = 20) -> float:
  """Prefer absolute R survival under cost, not thin lucky samples."""
  n = int(m.get("n_trades") or 0)
  tot = float(m.get("total_r") or 0)
  dd = max(float(m.get("max_drawdown_r") or 0), 1.0)
  wr = float(m.get("win_rate_pct") or 0)
  if n < min_trades:
    return -1e6 + n + 0.01 * tot
  # Primary: total_r with DD penalty; bonus for WR floor
  return (tot / dd) + 0.03 * tot - 0.08 * max(0.0, 38.0 - wr) - 0.15 * max(0.0, dd - 25.0)


def _cache_key(
  desk: Desk,
  *,
  window_from: str,
  window_to: str,
  train_weeks: int,
  preset: str | None,
  cost_gate: bool,
  cost_gate_mult: float,
  remine_each_week: bool,
  remine_stride: int,
) -> str:
  raw = "|".join(
    [
      desk.id,
      f"{desk.spread_pips:.2f}",
      window_from,
      window_to,
      str(train_weeks),
      str(preset),
      str(cost_gate),
      f"{cost_gate_mult:.2f}",
      str(remine_each_week),
      str(remine_stride),
      "v2",
    ]
  )
  return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def _run_wf(
  desk: Desk,
  *,
  window_from: str,
  window_to: str,
  train_weeks: int,
  preset: str | None,
  slip: float,
  remine_each_week: bool = True,
  remine_stride: int = 1,
  use_learning: bool = True,
  cost_gate: bool = False,
  cost_gate_mult: float = 2.5,
  use_cache: bool = True,
) -> dict[str, Any]:
  from feature_engine import FeatureMatrix  # type: ignore
  from optimizer import get_knowledge_base, optimize_on_window, reset_kb_cache  # type: ignore
  from strategy_miner import backtest_mined, generate_signals_mined  # type: ignore

  key = _cache_key(
    desk,
    window_from=window_from,
    window_to=window_to,
    train_weeks=train_weeks,
    preset=preset,
    cost_gate=cost_gate,
    cost_gate_mult=cost_gate_mult,
    remine_each_week=remine_each_week,
    remine_stride=remine_stride,
  )
  cache_path = CACHE_DIR / f"{desk.id}_{key}.json"
  if use_cache and cache_path.exists():
    try:
      cached = json.loads(cache_path.read_text(encoding="utf-8"))
      cached["from_cache"] = True
      return cached
    except Exception:
      pass

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

  for wi, (w0, w1) in enumerate(weeks):
    train_end = w0
    train_start = train_end - pd.Timedelta(weeks=train_weeks)
    mask = (df.index >= train_start) & (df.index < train_end)
    if int(mask.sum()) < 400:
      continue
    tr_s = int(df.index.get_loc(df.index[mask][0]))
    tr_e = int(df.index.get_loc(df.index[mask][-1])) + 1

    need_remine = remine_each_week and (wi % max(int(remine_stride), 1) == 0)
    if need_remine or frozen is None:
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

  out = {
    "metrics": _metrics_dict(all_trades),
    "n_weeks": len(weeks),
    "last_strategy": last_brief,
    "use_learning": learning,
    "preset": preset,
    "train_weeks": train_weeks,
    "cost_gate": cost_gate,
    "remine_stride": remine_stride,
    "from_cache": False,
  }
  try:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
  except Exception:
    pass
  return out


def _select_grid(desk: Desk) -> list[tuple[str | None, int, float | None, int]]:
  """(preset, train_weeks, cost_gate_mult|None, remine_stride)."""
  if desk.tf.upper() == "M5":
    # M5: no aggressive cost-gate (starves fills); biweekly remine for speed/stability
    return [
      ("anti_chase_fixed_70", 6, None, 2),
      ("edge_gentle", 6, None, 2),
      ("anti_chase_fixed_70", 9, None, 2),
      ("baseline", 6, None, 2),
    ]
  # M15: keep the recipe that produced G23 absolute win; mild cost-gate only as option
  return [
    ("anti_chase_fixed_70", 6, None, 1),
    ("anti_chase_fixed_70", 9, None, 1),
    ("edge_gentle", 6, None, 1),
    ("elite_or_quality", 6, None, 1),
    ("anti_chase_fixed_70", 6, 2.5, 1),
  ]


def _trainapp_default(desk: Desk) -> tuple[str | None, int, int]:
  # Fixed TrainApp recommended recipe
  stride = 2 if desk.tf.upper() == "M5" else 1
  return ("elite_or_quality", 6, stride)


def select_hyperparams(desk: Desk, protocol: dict | None = None) -> dict[str, Any]:
  protocol = protocol or load_protocol()
  proto = protocol.get("protocol") or protocol
  slip = float(proto.get("default_slippage_pips") or 0.3)
  min_tr = int(proto.get("min_validate_trades") or 20)
  va = proto["validate"]

  ranked: list[tuple[float, dict]] = []
  viable: list[tuple[float, dict]] = []
  for preset, train_weeks, gate_mult, stride in _select_grid(desk):
    print(
      f"  select {desk.id}: preset={preset} tw={train_weeks} gate={gate_mult} stride={stride} …",
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
      remine_stride=stride,
      use_learning=True,
      cost_gate=gate_mult is not None,
      cost_gate_mult=float(gate_mult or 2.5),
    )
    m = res["metrics"]
    ok = _passes_validate(m, proto)
    score = _select_score(m, min_trades=min_tr)
    print(
      f"    {'ok' if ok else 'reject'} score={score:.3f} cache={res.get('from_cache')} {m}",
      flush=True,
    )
    cand = {
      "preset": preset,
      "train_weeks": train_weeks,
      "cost_gate_mult": gate_mult,
      "remine_stride": stride,
      "validate": m,
      "use_learning": res.get("use_learning"),
      "select_score": score,
    }
    if int(m.get("n_trades") or 0) >= min_tr:
      viable.append((score, cand))
    if ok:
      ranked.append((score, cand))

  if ranked:
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1]

  if viable:
    viable.sort(key=lambda x: x[0], reverse=True)
    best = dict(viable[0][1])
  else:
    # Extremely thin data: take highest raw select_score among attempted (may be < min_tr)
    # Re-score first grid row from cache as last resort
    preset, train_weeks, gate_mult, stride = _select_grid(desk)[0]
    res = _run_wf(
      desk,
      window_from=va["from"],
      window_to=va["to"],
      train_weeks=train_weeks,
      preset=preset,
      slip=slip,
      remine_each_week=True,
      remine_stride=stride,
      use_learning=True,
      cost_gate=gate_mult is not None,
      cost_gate_mult=float(gate_mult or 2.5),
    )
    best = {
      "preset": preset,
      "train_weeks": train_weeks,
      "cost_gate_mult": gate_mult,
      "remine_stride": stride,
      "validate": res["metrics"],
      "select_score": _select_score(res["metrics"], min_trades=min_tr),
    }
  best["soft_fallback"] = True
  print(
    f"  soft_fallback -> {best.get('preset')} tw={best.get('train_weeks')} "
    f"gate={best.get('cost_gate_mult')} n={(best.get('validate') or {}).get('n_trades')}",
    flush=True,
  )
  return best


def run_desk_proof_wf(desk: Desk, protocol: dict | None = None) -> dict[str, Any]:
  protocol = protocol or load_protocol()
  proto = protocol.get("protocol") or protocol
  slip = float(proto.get("default_slippage_pips") or 0.3)
  te = proto["test"]

  picked = select_hyperparams(desk, protocol)
  gate = picked.get("cost_gate_mult")
  stride = int(picked.get("remine_stride") or 1)
  print(
    f"  AIEdge pick: preset={picked.get('preset')} tw={picked.get('train_weeks')} "
    f"gate={gate} stride={stride}",
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
    remine_stride=stride,
    use_learning=True,
    cost_gate=gate is not None,
    cost_gate_mult=float(gate or 2.5),
  )

  ta_preset, ta_tw, ta_stride = _trainapp_default(desk)
  print(
    f"  TrainApp-fair baseline: preset={ta_preset} tw={ta_tw} stride={ta_stride} "
    f"@ spread={desk.spread_pips}",
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
    remine_stride=ta_stride,
    use_learning=True,
    cost_gate=False,
  )

  published = load_trainapp_baseline(desk)

  aiedge = {
    "desk": desk.id,
    "system": "AIEdge-v2-ValidateSelect-WF",
    "space": picked.get("preset"),
    "params": {
      "preset": picked.get("preset"),
      "train_weeks": picked.get("train_weeks"),
      "cost_gate_mult": gate,
      "remine_stride": stride,
      "selection": "validate_select_score_v2",
      "soft_fallback": bool(picked.get("soft_fallback")),
      "select_score": picked.get("select_score"),
      "last_strategy": ai_test.get("last_strategy"),
    },
    "param_key": (
      f"wf|{picked.get('preset')}|tw{picked.get('train_weeks')}|"
      f"gate{gate}|s{stride}"
    ),
    "validate": picked.get("validate"),
    "test": ai_test["metrics"],
  }
  baseline = {
    "source": "fair_wf_same_cost",
    "label": (
      f"TrainApp default {ta_preset} tw{ta_tw} stride{ta_stride} "
      f"@ {desk.spread_pips}pip (no cost-gate)"
    ),
    "metrics_raw": ta_test["metrics"],
    "metrics": ta_test["metrics"],
    "note": (
      "Re-simulated under AIEdge protocol costs on the locked TEST window. "
      "Published TrainApp grid rows that train on overlapping 2025-2026 eras are NOT used "
      "as the primary baseline."
    ),
  }
  decision = decide_winner(aiedge.get("test") or {}, baseline)
  # Absolute profitability flag (beats "app still better" concern)
  ai_r = float((aiedge.get("test") or {}).get("total_r") or 0)
  ta_r = float((baseline.get("metrics") or {}).get("total_r") or 0)
  pub_r = float(((published.get("metrics") or {}).get("total_r") or 0))
  decision["aiedge_profitable"] = ai_r > 0
  decision["beats_fair_total_r"] = ai_r > ta_r
  decision["vs_published_stressed_total_r"] = round(ai_r - pub_r, 3)

  return {
    "desk": desk.id,
    "pair": desk.pair,
    "tf": desk.tf,
    "aiedge_cost_spread_pips": desk.spread_pips,
    "aiedge": aiedge,
    "trainapp_baseline": baseline,
    "trainapp_published_stressed": published,
    "decision": decision,
  }
