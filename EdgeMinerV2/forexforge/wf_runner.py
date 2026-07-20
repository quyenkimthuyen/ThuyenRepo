"""Unified walk-forward runner — shared by backtest and learning."""
from __future__ import annotations

from typing import Callable, Optional

import pandas as pd
from tqdm import tqdm

from .config import MIN_TRAIN_BARS, TRAIN_MONTHS
from .contracts import JobKind, LeakageCheck, MetricsPack, Report, RunSpec, TradeRecord
from .data_loader import get_train_window_indices, get_week_indices
from .feature_engine import FeatureMatrix
from .kb_profiles import (
  DEFAULT_PROFILE_ID,
  create_profile,
  profile_path,
  register_profile,
  save_epoch_snapshot,
  slice_df_for_period,
)
from .knowledge_base import KnowledgeBase
from .leakage import LeakageError, assert_no_leakage
from .meta_learner import mine_strategy_learning, record_trade_learning
from .optimizer import (
  TARGET_TRADES_PER_WEEK,
  get_knowledge_base,
  optimize_on_window,
  reset_kb_cache,
  set_kb_profile,
)
from .strategy import compute_metrics
from .strategy_miner import MinedStrategy, Rule, backtest_mined, generate_signals_mined

ProgressCallback = Callable[[int, int, object], None]


def generate_weekly_schedule(df: pd.DataFrame, first_trade_date, end_date=None):
  weeks, current = [], first_trade_date
  end = end_date if end_date is not None else df.index[-1]
  while current < end:
    weeks.append((current, current + pd.Timedelta(days=7)))
    current += pd.Timedelta(days=7)
  return weeks


def strategy_to_dict(s: MinedStrategy) -> dict:
  def rules_to_list(rules: list[Rule]):
    return [
      {"feat": r.feature, "op": r.op, "thr": round(r.threshold, 4), "w": round(r.weight, 3)}
      for r in rules
    ]
  return {
    "name": s.name,
    "exit_mode": s.exit_mode,
    "ml_prob_min": s.ml_prob_min,
    "rr": s.rr_ratio,
    "atr_mult": s.atr_mult_sl,
    "long_rules": rules_to_list(s.long_rules),
    "short_rules": rules_to_list(s.short_rules),
  }


def trades_to_records(trades) -> list[TradeRecord]:
  return [
    TradeRecord(
      entry=str(t.entry_time),
      exit=str(t.exit_time),
      direction="LONG" if t.direction == 1 else "SHORT",
      entry_px=round(t.entry_price, 5),
      exit_px=round(t.exit_price, 5),
      sl=round(t.sl, 5),
      tp=round(t.tp, 5),
      pnl_pips=round(t.pnl_pips, 1),
      r=round(t.r_multiple, 2),
      reason=t.exit_reason,
    )
    for t in trades
  ]


def _pack_metrics(m: dict, trades_per_week: float) -> MetricsPack:
  return MetricsPack(
    n_trades=m["n_trades"],
    trades_per_week=round(trades_per_week, 2),
    win_rate_pct=round(m["win_rate"] * 100, 2),
    avg_rr=round(m["avg_rr"], 3),
    profit_factor=round(m["profit_factor"], 3),
    total_pips=round(m["total_pips"], 2),
    total_r=round(m["total_r"], 3),
    max_drawdown_r=round(m["max_drawdown_r"], 2),
    max_win_streak=m.get("max_win_streak", 0),
    max_loss_streak=m.get("max_loss_streak", 0),
    risk_of_ruin_pct=m.get("risk_of_ruin_pct", 0),
  )


def _resolve_schedule(df_wf: pd.DataFrame, train_months: int, oos_from, oos_to, holdout_cutoff):
  train_end_date = df_wf.index[0] + pd.DateOffset(months=train_months)
  oos_mask = df_wf.index >= train_end_date
  if not oos_mask.any():
    return [], train_end_date
  first_trade_date = df_wf.index[oos_mask][0]
  first_trade_date -= pd.Timedelta(days=first_trade_date.weekday())
  if first_trade_date < train_end_date:
    first_trade_date += pd.Timedelta(days=7)

  if oos_from:
    oos_from_ts = pd.Timestamp(oos_from)
    if oos_from_ts > first_trade_date:
      first_trade_date = oos_from_ts - pd.Timedelta(days=oos_from_ts.weekday())

  wf_end = holdout_cutoff if holdout_cutoff is not None else df_wf.index[-1]
  if oos_to:
    wf_end = min(wf_end, pd.Timestamp(oos_to))

  weeks = generate_weekly_schedule(df_wf, first_trade_date, wf_end)
  if oos_from:
    weeks = [w for w in weeks if w[0] >= pd.Timestamp(oos_from)]
  if oos_to:
    weeks = [w for w in weeks if w[0] <= pd.Timestamp(oos_to)]
  return weeks, first_trade_date


def _run_holdout_forward(
  df, fm, holdout_cutoff, use_learning, train_months, spread_pips, slippage_pips, kb,
):
  train_start_idx, train_end_idx = get_train_window_indices(df, holdout_cutoff, train_months)
  if train_start_idx is None:
    return [], None
  strat = optimize_on_window(
    fm, train_start_idx, train_end_idx,
    use_learning=use_learning, as_of=holdout_cutoff, kb=kb,
  )
  if strat is None:
    return [], None
  holdout_mask = df.index >= holdout_cutoff
  if not holdout_mask.any():
    return [], strategy_to_dict(strat)
  start_i = df.index.get_loc(df.index[holdout_mask][0])
  sig = generate_signals_mined(fm, strat, start_i, fm.n)
  trades = backtest_mined(
    fm, strat, sig, start_i, fm.n,
    spread_pips=spread_pips, slippage_pips=slippage_pips,
  )
  return trades, strategy_to_dict(strat)


def run_walk_forward_weeks(
  df: pd.DataFrame,
  fm: FeatureMatrix,
  *,
  weeks: list,
  use_learning: bool,
  train_months: int,
  spread_pips: float,
  slippage_pips: float,
  risk_pct_per_trade: float = 1.0,
  kb: KnowledgeBase | None = None,
  record_learning: bool = False,
  on_progress: Optional[ProgressCallback] = None,
  verbose: bool = False,
  desc: str = "Walk-forward",
) -> tuple[list, list[dict], MinedStrategy | None]:
  """One epoch of weekly WF. Shared by backtest and learning."""
  all_oos_trades = []
  weekly_log: list[dict] = []
  last_strat: MinedStrategy | None = None
  prev_strat: MinedStrategy | None = None

  week_iter = tqdm(weeks, desc=desc, disable=not verbose or on_progress is not None)
  for wi, (week_start, week_end) in enumerate(week_iter):
    if on_progress:
      on_progress(wi + 1, len(weeks), week_start)

    train_start_idx, train_end_idx = get_train_window_indices(df, week_start, train_months)
    if train_start_idx is None or (train_end_idx - train_start_idx) < MIN_TRAIN_BARS:
      weekly_log.append({"week_start": str(week_start.date()), "status": "skip_train"})
      continue

    if use_learning and kb is not None:
      strat = mine_strategy_learning(fm, train_start_idx, train_end_idx, kb, as_of=week_start)
    else:
      strat = optimize_on_window(
        fm, train_start_idx, train_end_idx,
        use_learning=False, as_of=week_start, kb=None,
      )

    if strat is None:
      strat = prev_strat
    if strat is None:
      weekly_log.append({"week_start": str(week_start.date()), "status": "skip_no_strategy"})
      continue

    last_strat, prev_strat = strat, strat
    oos_start, oos_end = get_week_indices(df, week_start, week_end)
    if oos_start is None:
      continue

    signals = generate_signals_mined(fm, strat, oos_start, oos_end)
    week_trades = backtest_mined(
      fm, strat, signals, oos_start, oos_end,
      spread_pips=spread_pips, slippage_pips=slippage_pips,
    )

    if record_learning and kb is not None:
      for t in week_trades:
        try:
          entry_idx = fm.index.get_loc(t.entry_time)
          signal_idx = max(entry_idx - 1, 0)
          record_trade_learning(kb, fm, strat, signal_idx, t.direction, t.r_multiple)
        except (KeyError, ValueError, TypeError) as exc:
          # keep learning robust but never silent-swallow everything
          weekly_log.append({
            "week_start": str(week_start.date()),
            "status": "learn_record_error",
            "error": str(exc),
          })

    all_oos_trades.extend(week_trades)
    week_m = compute_metrics(week_trades, risk_pct_per_trade)
    weekly_log.append({
      "week_start": str(week_start.date()),
      "strategy": strat.name,
      "score_thr": strat.score_threshold,
      "long_rules": len(strat.long_rules),
      "short_rules": len(strat.short_rules),
      "oos_trades": week_m["n_trades"],
      "oos_wr": round(week_m["win_rate"], 3),
      "oos_pips": round(week_m["total_pips"], 1),
      "oos_r": round(week_m["total_r"], 2),
    })

  return all_oos_trades, weekly_log, last_strat


def run_backtest(df: pd.DataFrame, spec: RunSpec, *, on_progress=None, verbose: bool = True) -> Report:
  """KB OFF/ON backtest via unified WF. Hard-blocks leakage when KB ON."""
  reset_kb_cache()
  profile_id = spec.kb_profile or DEFAULT_PROFILE_ID
  leakage = LeakageCheck(ok=True, message="KB OFF")
  kb_instance: KnowledgeBase | None = None

  if spec.use_kb:
    check_start = spec.oos_from_str() or str(df.index[0].date())
    leakage = assert_no_leakage(profile_id, check_start)
    snap = spec.kb_epoch
    set_kb_profile(profile_id, snap)
    kb_instance = get_knowledge_base(profile_id, snap)

  holdout_cutoff = None
  if spec.holdout_months > 0:
    holdout_cutoff = df.index[-1] - pd.DateOffset(months=spec.holdout_months)

  df_wf = df[df.index < holdout_cutoff] if holdout_cutoff is not None else df
  fm = FeatureMatrix(df)
  weeks, first_trade_date = _resolve_schedule(
    df_wf, spec.train_months, spec.oos_from, spec.oos_to, holdout_cutoff,
  )

  if verbose:
    print(
      f"Walk-forward | bars={len(df)} | KB={'ON' if spec.use_kb else 'OFF'} "
      f"| profile={profile_id if spec.use_kb else '-'} | weeks={len(weeks)}"
    )
    if spec.use_kb:
      print(f"  KB check: {leakage.message}")

  all_oos_trades, weekly_log, last_strat = run_walk_forward_weeks(
    df, fm,
    weeks=weeks,
    use_learning=spec.use_kb,
    train_months=spec.train_months,
    spread_pips=spec.cost.spread_pips,
    slippage_pips=spec.cost.slippage_pips,
    risk_pct_per_trade=spec.risk_pct_per_trade,
    kb=kb_instance,
    record_learning=False,
    on_progress=on_progress,
    verbose=verbose,
  )

  holdout_trades, holdout_strat = [], None
  if holdout_cutoff is not None:
    holdout_trades, holdout_strat = _run_holdout_forward(
      df, fm, holdout_cutoff, spec.use_kb, spec.train_months,
      spec.cost.spread_pips, spec.cost.slippage_pips, kb_instance,
    )

  overall = compute_metrics(all_oos_trades, spec.risk_pct_per_trade)
  one_year_ago = df.index[-1] - pd.DateOffset(years=1)
  year_trades = [t for t in all_oos_trades if t.entry_time >= one_year_ago]
  year_m = compute_metrics(year_trades, spec.risk_pct_per_trade)
  traded_weeks = max(len([w for w in weekly_log if w.get("oos_trades", 0) > 0]), 1)
  avg_tpw = overall["n_trades"] / traded_weeks

  holdout_m = compute_metrics(holdout_trades, spec.risk_pct_per_trade) if holdout_trades else None
  overall_pack = _pack_metrics(overall, avg_tpw)
  year_pack = _pack_metrics(year_m, avg_tpw)

  constraints = {
    "win_rate_above_60": year_m["win_rate"] >= 0.60,
    "rr_above_2": year_m["avg_rr"] >= 2.0,
    "profitable": year_m["total_r"] > 0,
    "trades_per_week_near_2": 1.2 <= avg_tpw <= 3.0,
  }

  raw = {
    "data_range": {
      "start": str(df.index[0].date()),
      "end": str(df.index[-1].date()),
      "bars": len(df),
    },
    "oos_start": str(pd.Timestamp(first_trade_date).date()),
    "config": {
      "version": "forexforge_v2",
      "train_months": spec.train_months,
      "target_trades_per_week": TARGET_TRADES_PER_WEEK,
      "pair": spec.instrument.pair,
      "tf": spec.instrument.timeframe,
      "use_learning_kb": spec.use_kb,
      "kb_profile": profile_id if spec.use_kb else None,
      "kb_snapshot": (spec.kb_epoch if spec.kb_epoch not in (None, "latest") else "latest") if spec.use_kb else None,
      "kb_validation": leakage.model_dump(mode="json"),
      "oos_from": spec.oos_from_str(),
      "oos_to": spec.oos_to_str(),
      "spread_pips": spec.cost.spread_pips,
      "slippage_pips": spec.cost.slippage_pips,
      "holdout_months": spec.holdout_months,
      "risk_pct_per_trade": spec.risk_pct_per_trade,
    },
    "overall_oos": overall_pack.model_dump(),
    "last_1_year": year_pack.model_dump(),
    "constraints_met": constraints,
    "last_strategy": strategy_to_dict(last_strat) if last_strat else None,
    "weekly_log": weekly_log,
    "trades": [t.model_dump() for t in trades_to_records(all_oos_trades)],
  }
  if holdout_m:
    raw["holdout_forward"] = {
      "cutoff": str(holdout_cutoff.date()),
      "months": spec.holdout_months,
      "metrics": _pack_metrics(
        holdout_m,
        holdout_m["n_trades"] / max(spec.holdout_months * 4.33, 1),
      ).model_dump(),
      "strategy": holdout_strat,
      "trades": [t.model_dump() for t in trades_to_records(holdout_trades)],
    }

  return Report(
    spec=spec,
    leakage=leakage,
    data_range=raw["data_range"],
    oos_start=raw["oos_start"],
    overall_oos=overall_pack,
    last_1_year=year_pack,
    constraints_met=constraints,
    weekly_log=weekly_log,
    trades=trades_to_records(all_oos_trades),
    holdout_forward=raw.get("holdout_forward"),
    last_strategy=raw["last_strategy"],
    raw=raw,
  )


def run_learning(df: pd.DataFrame, spec: RunSpec, *, on_progress=None, verbose: bool = True) -> Report:
  """Multi-epoch learning using the same weekly WF loop."""
  profile_id = spec.kb_profile or DEFAULT_PROFILE_ID
  if profile_id != DEFAULT_PROFILE_ID and not profile_path(profile_id).exists():
    create_profile(profile_id, spec.label or profile_id)

  kb = KnowledgeBase(profile_path(profile_id))
  data_from = spec.data_from.isoformat() if spec.data_from else str(df.index[0].date())
  data_to = spec.data_to.isoformat() if spec.data_to else None
  df = slice_df_for_period(df, data_from, data_to)
  if len(df) < MIN_TRAIN_BARS + 100:
    raise ValueError("Not enough data for the selected learning period.")

  fm = FeatureMatrix(df)
  weeks, first_trade_date = _resolve_schedule(df, spec.train_months, None, None, None)
  history = []
  last_trades = []

  for epoch in range(1, spec.epochs + 1):
    def _epoch_progress(cur, total, week_start, _epoch=epoch):
      if on_progress:
        # flatten multi-epoch progress
        on_progress((_epoch - 1) * total + cur, spec.epochs * total, week_start)

    all_oos_trades, weekly_log, _ = run_walk_forward_weeks(
      df, fm,
      weeks=weeks,
      use_learning=True,
      train_months=spec.train_months,
      spread_pips=spec.cost.spread_pips,
      slippage_pips=spec.cost.slippage_pips,
      kb=kb,
      record_learning=True,
      on_progress=_epoch_progress if on_progress else None,
      verbose=verbose,
      desc=f"Epoch {epoch}",
    )
    overall = compute_metrics(all_oos_trades)
    traded_weeks = max(len([w for w in weekly_log if w.get("oos_trades", 0) > 0]), 1)
    avg_tpw = overall["n_trades"] / traded_weeks
    epoch_metrics = {
      "epoch": epoch,
      "n_trades": overall["n_trades"],
      "trades_per_week": round(avg_tpw, 2),
      "win_rate_pct": round(overall["win_rate"] * 100, 2),
      "avg_rr": round(overall["avg_rr"], 3),
      "profit_factor": round(overall["profit_factor"], 3),
      "total_pips": round(overall["total_pips"], 2),
      "total_r": round(overall["total_r"], 3),
      "genomes_in_kb": len(kb.genomes),
      "rules_tracked": len(kb.rule_stats),
      "ml_samples": len(kb.ml_experience),
    }
    kb.record_epoch(epoch, epoch_metrics)
    kb.save()
    save_epoch_snapshot(kb, profile_id, epoch_metrics)
    history.append(epoch_metrics)
    last_trades = all_oos_trades
    if verbose:
      print(
        f"Epoch {epoch}: WR={epoch_metrics['win_rate_pct']}% "
        f"R={epoch_metrics['total_r']} genomes={epoch_metrics['genomes_in_kb']}"
      )

  register_profile(
    profile_id,
    spec.label or profile_id,
    str(df.index[0].date()),
    str(df.index[-1].date()),
    spec.epochs,
    note=f"learning {spec.epochs} epoch(s)",
  )

  overall = compute_metrics(last_trades)
  traded_weeks = max(1, len(weeks))
  pack = _pack_metrics(overall, overall["n_trades"] / traded_weeks)
  learn_spec = spec.model_copy(update={"kind": JobKind.LEARN, "use_kb": True, "kb_profile": profile_id})
  return Report(
    spec=learn_spec,
    leakage=LeakageCheck(ok=True, message="learning run — no OOS leakage check"),
    data_range={
      "start": str(df.index[0].date()),
      "end": str(df.index[-1].date()),
      "bars": len(df),
    },
    oos_start=str(pd.Timestamp(first_trade_date).date()),
    overall_oos=pack,
    epoch_history=history,
    trades=trades_to_records(last_trades),
    raw={
      "epochs": spec.epochs,
      "kb_profile": profile_id,
      "trained_from": str(df.index[0].date()),
      "trained_to": str(df.index[-1].date()),
      "epoch_history": history,
      "kb_summary": {
        "genomes": len(kb.genomes),
        "rules": len(kb.rule_stats),
        "ml_samples": len(kb.ml_experience),
        "best_fitness": kb.best_fitness_ever,
      },
    },
  )


def execute_run(df: pd.DataFrame, spec: RunSpec, *, on_progress=None, verbose: bool = True) -> Report:
  if spec.kind == JobKind.LEARN:
    return run_learning(df, spec, on_progress=on_progress, verbose=verbose)
  return run_backtest(df, spec, on_progress=on_progress, verbose=verbose)


__all__ = [
  "LeakageError",
  "execute_run",
  "generate_weekly_schedule",
  "run_backtest",
  "run_learning",
  "run_walk_forward_weeks",
  "strategy_to_dict",
  "trades_to_records",
]
