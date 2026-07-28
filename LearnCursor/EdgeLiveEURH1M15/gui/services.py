"""GUI data services — load reports, run jobs."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from data_loader import META_PATH, download_eurusd, load_eurusd
from config import (
  DEFAULT_HOLDOUT_MONTHS, DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS,
  DEFAULT_START_DATE, DEFAULT_RISK_PCT_PER_TRADE, get_active_tf,
)
from runtime_profiles import get_tf_defaults
from kb_profiles import (
  DEFAULT_PROFILE_ID, create_profile, delete_profile, kb_valid_for_backtest,
  list_profiles, load_kb as load_kb_from_profiles, register_profile, slice_df_for_period,
  suggest_profiles_for_oos,
)
from optimizer import set_kb_profile, reset_kb_cache
from run_backtest import run_walk_forward, save_backtest_report, REPORT_DIR
from run_learning import run_epoch
from feature_engine import FeatureMatrix
from knowledge_base import KnowledgeBase

BACKTEST_REPORT = REPORT_DIR / "backtest_report.json"
LEARNING_REPORT = REPORT_DIR / "learning_report.json"


def load_json(path: Path) -> dict | None:
  if not path.exists():
    return None
  with open(path, encoding="utf-8") as f:
    return json.load(f)


def load_backtest_report(workspace_aware: bool = True) -> dict | None:
  if workspace_aware:
    try:
      from gui.workspace import load_report_for_workspace
      return load_report_for_workspace()
    except Exception:
      pass
  return load_json(BACKTEST_REPORT)


def load_learning_report() -> dict | None:
  return load_json(LEARNING_REPORT)


def load_data_meta() -> dict:
  from mt5_bridge.history_sync import cache_meta_for
  from mt5_bridge.protocol import read_json
  return read_json(cache_meta_for(get_active_tf())) or {}


def load_kb(profile_id: str = DEFAULT_PROFILE_ID) -> KnowledgeBase:
  return load_kb_from_profiles(profile_id)


def get_ohlc_df(start: str | None = None) -> pd.DataFrame:
  d = get_tf_defaults(get_active_tf())
  return load_eurusd(start or d.start_date, tf=d.tf)


@st.cache_data(ttl=300, show_spinner=False)
def get_ohlc_df_cached(start: str = DEFAULT_START_DATE, tf: str = "M15") -> pd.DataFrame:
  """Cached OHLC — tránh đọc parquet lại mỗi lần chuyển tab."""
  return load_eurusd(start, tf=tf)


@st.cache_data(ttl=300, show_spinner=False)
def get_ohlc_window_cached(
  chart_from: str, chart_to: str, start: str = DEFAULT_START_DATE, tf: str = "M15",
) -> pd.DataFrame:
  """Chỉ load slice OHLC cho chart (tuần hiện tại + padding)."""
  ohlc = get_ohlc_df_cached(start, tf=tf)
  window = ohlc.loc[pd.Timestamp(chart_from):pd.Timestamp(chart_to)]
  if window.empty:
    window = ohlc.tail(672)
  return window.copy()


def refresh_market_data(start: str | None = None) -> pd.DataFrame:
  _clear_ohlc_streamlit_cache()
  d = get_tf_defaults(get_active_tf())
  return download_eurusd(start or d.start_date, force_refresh=True, tf=d.tf)


def _clear_ohlc_streamlit_cache() -> None:
  try:
    get_ohlc_df_cached.clear()
    get_ohlc_window_cached.clear()
  except Exception:
    pass


def execute_backtest(
  use_learning: bool = False,
  train_weeks: int | None = None,
  train_months: int | None = None,
  train_unit: str | None = None,
  train_length: int | None = None,
  start_date: str | None = None,
  spread_pips: float = DEFAULT_SPREAD_PIPS,
  slippage_pips: float = DEFAULT_SLIPPAGE_PIPS,
  holdout_months: int = DEFAULT_HOLDOUT_MONTHS,
  risk_pct: float = DEFAULT_RISK_PCT_PER_TRADE,
  kb_profile: str = DEFAULT_PROFILE_ID,
  kb_snapshot: int | str | None = None,
  oos_from: str | None = None,
  oos_to: str | None = None,
  feature_profile: str | None = None,
  mining_search_space: dict | None = None,
  on_progress=None,
  archive: bool = False,
  archive_label: str | None = None,
  sync_workspace: bool = True,
) -> dict:
  from strategy_miner import mining_search_space_from_dict

  # Prefer explicit args; else pull from active Trade Model so health/analysis
  # re-runs match session/spacing/hold of the saved model (not miner defaults).
  if feature_profile is None or mining_search_space is None:
    try:
      from mt5_bridge.models import get_model_run_params, resolve_model
      from gui.trade_model import get_active_trade_model
      active = get_active_trade_model() or resolve_model()
      mp = get_model_run_params(active, (active or {}).get("id"))
      if feature_profile is None:
        feature_profile = mp.get("feature_profile") or "current"
      if mining_search_space is None:
        mining_search_space = mp.get("mining_search_space")
      if train_weeks is None and train_months is None and train_length is None:
        train_weeks = mp.get("train_weeks")
        train_months = mp.get("train_months")
    except Exception:
      feature_profile = feature_profile or "current"

  search_space = (
    mining_search_space_from_dict(mining_search_space)
    if mining_search_space else None
  )

  d = get_tf_defaults(get_active_tf())
  df = load_eurusd(start_date or d.start_date, tf=d.tf)
  reset_kb_cache()
  if use_learning:
    set_kb_profile(kb_profile, kb_snapshot)
  result = run_walk_forward(
    df,
    use_learning=use_learning,
    train_weeks=train_weeks,
    train_months=train_months,
    train_unit=train_unit,
    train_length=train_length,
    spread_pips=spread_pips,
    slippage_pips=slippage_pips,
    holdout_months=holdout_months,
    risk_pct_per_trade=risk_pct,
    kb_profile=kb_profile if use_learning else None,
    kb_snapshot=kb_snapshot if use_learning else None,
    oos_from=oos_from or None,
    oos_to=oos_to or None,
    feature_profile=feature_profile or "current",
    search_space=search_space,
    on_progress=on_progress,
    verbose=False,
  )
  save_backtest_report(result)
  if sync_workspace:
    try:
      from gui.trade_model import get_active_trade_model
      from gui.workspace import save_workspace_report, sync_workspace_from_backtest
      tm = get_active_trade_model()
      if tm and tm.get("id"):
        result.setdefault("config", {})["trade_model_id"] = tm["id"]
      sync_workspace_from_backtest(result)
      save_workspace_report(result)
    except Exception:
      pass
  if archive:
    from gui.report_store import save_report
    save_report(result, label=archive_label)
  return result


def execute_learning(
  epochs: int = 2,
  reset_kb: bool = False,
  kb_profile: str = DEFAULT_PROFILE_ID,
  kb_name: str | None = None,
  from_date: str | None = None,
  until_date: str | None = None,
  on_epoch_done=None,
) -> dict:
  from kb_profiles import profile_path as kb_path_fn

  if kb_profile != DEFAULT_PROFILE_ID and not kb_path_fn(kb_profile).exists():
    create_profile(kb_profile, kb_name or kb_profile)

  path = kb_path_fn(kb_profile)
  if reset_kb and path.exists():
    path.unlink()

  kb = KnowledgeBase(path)
  d = get_tf_defaults(get_active_tf())
  df = load_eurusd(from_date or d.start_date, tf=d.tf)
  df = slice_df_for_period(df, from_date or d.start_date, until_date)
  fm = FeatureMatrix(df)

  all_epoch_results = []
  last_result = None
  for epoch in range(1, epochs + 1):
    if on_epoch_done:
      on_epoch_done(epoch, epochs, "running")
    last_result = run_epoch(df, fm, kb, epoch)
    all_epoch_results.append(last_result["epoch_metrics"])
    if on_epoch_done:
      on_epoch_done(epoch, epochs, "done")

  register_profile(
    kb_profile, kb_name or kb_profile,
    str(df.index[0].date()), str(df.index[-1].date()), epochs,
  )

  report = {
    "epochs": epochs,
    "kb_profile": kb_profile,
    "trained_from": str(df.index[0].date()),
    "trained_to": str(df.index[-1].date()),
    "epoch_history": all_epoch_results,
    "kb_summary": {
      "genomes": len(kb.genomes),
      "rules": len(kb.rule_stats),
      "ml_samples": len(kb.ml_experience),
      "best_fitness": kb.best_fitness_ever,
    },
    "last_epoch_trades": last_result["trades"] if last_result else [],
  }
  REPORT_DIR.mkdir(exist_ok=True)
  with open(LEARNING_REPORT, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
  try:
    from gui.components import suggested_oos_range
    from gui.workspace import set_active_workspace, sync_workspace_from_learning
    sync_workspace_from_learning(report)
    oos_from, oos_to = suggested_oos_range(kb_profile)
    set_active_workspace(
      kb_profile=kb_profile,
      learn_from=report["trained_from"],
      learn_until=report["trained_to"],
      oos_from=oos_from,
      oos_to=oos_to,
    )
  except Exception:
    pass
  return report

