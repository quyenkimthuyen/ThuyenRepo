"""GUI data services — load reports, run jobs."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from config import (
  DEFAULT_HOLDOUT_MONTHS, DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS,
  DEFAULT_START_DATE, DEFAULT_RISK_PCT_PER_TRADE,
)
from data_loader import META_PATH, load_eurusd_h1, download_eurusd_h1
from kb_profiles import (
  DEFAULT_PROFILE_ID, create_profile, delete_profile, kb_valid_for_backtest,
  list_profiles, load_kb as load_kb_from_profiles, register_profile, slice_df_for_period,
  suggest_profiles_for_oos,
)
from optimizer import set_kb_profile, reset_kb_cache
from paper_monitor import get_monitor_state
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
  return load_json(META_PATH) or {}


def load_kb(profile_id: str = DEFAULT_PROFILE_ID) -> KnowledgeBase:
  return load_kb_from_profiles(profile_id)


def get_ohlc_df(start: str = DEFAULT_START_DATE) -> pd.DataFrame:
  return load_eurusd_h1(start)


@st.cache_data(ttl=300, show_spinner=False)
def get_ohlc_df_cached(start: str = DEFAULT_START_DATE) -> pd.DataFrame:
  """Cached OHLC — tránh đọc parquet lại mỗi lần chuyển tab."""
  return load_eurusd_h1(start)


@st.cache_data(ttl=300, show_spinner=False)
def get_ohlc_window_cached(chart_from: str, chart_to: str, start: str = DEFAULT_START_DATE) -> pd.DataFrame:
  """Chỉ load slice OHLC cho chart (tuần hiện tại + padding)."""
  ohlc = get_ohlc_df_cached(start)
  window = ohlc.loc[pd.Timestamp(chart_from):pd.Timestamp(chart_to)]
  if window.empty:
    window = ohlc.tail(168)
  return window.copy()


def refresh_market_data(start: str = DEFAULT_START_DATE) -> pd.DataFrame:
  _clear_ohlc_streamlit_cache()
  return download_eurusd_h1(start, force_refresh=True)


def _clear_ohlc_streamlit_cache() -> None:
  try:
    get_ohlc_df_cached.clear()
    get_ohlc_window_cached.clear()
  except Exception:
    pass


def execute_backtest(
  use_learning: bool = False,
  train_months: int = 3,
  start_date: str = DEFAULT_START_DATE,
  spread_pips: float = DEFAULT_SPREAD_PIPS,
  slippage_pips: float = DEFAULT_SLIPPAGE_PIPS,
  holdout_months: int = DEFAULT_HOLDOUT_MONTHS,
  risk_pct: float = DEFAULT_RISK_PCT_PER_TRADE,
  kb_profile: str = DEFAULT_PROFILE_ID,
  kb_snapshot: int | str | None = None,
  oos_from: str | None = None,
  oos_to: str | None = None,
  on_progress=None,
  archive: bool = False,
  archive_label: str | None = None,
  sync_workspace: bool = True,
) -> dict:
  df = load_eurusd_h1(start_date)
  reset_kb_cache()
  if use_learning:
    set_kb_profile(kb_profile, kb_snapshot)
  result = run_walk_forward(
    df,
    use_learning=use_learning,
    train_months=train_months,
    spread_pips=spread_pips,
    slippage_pips=slippage_pips,
    holdout_months=holdout_months,
    risk_pct_per_trade=risk_pct,
    kb_profile=kb_profile if use_learning else None,
    kb_snapshot=kb_snapshot if use_learning else None,
    oos_from=oos_from or None,
    oos_to=oos_to or None,
    on_progress=on_progress,
    verbose=False,
  )
  save_backtest_report(result)
  if sync_workspace:
    try:
      from gui.trade_profile import get_active_trade_profile
      from gui.workspace import save_workspace_report, sync_workspace_from_backtest
      tp_id = get_active_trade_profile().get("id")
      if tp_id:
        result.setdefault("config", {})["trade_profile_id"] = tp_id
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
  from_date: str = DEFAULT_START_DATE,
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
  df = load_eurusd_h1(from_date)
  df = slice_df_for_period(df, from_date, until_date)
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


def get_paper_monitor(
  use_learning: bool = False,
  kb_profile: str = DEFAULT_PROFILE_ID,
  kb_snapshot: int | str | None = None,
  spread_pips: float = DEFAULT_SPREAD_PIPS,
  slippage_pips: float = DEFAULT_SLIPPAGE_PIPS,
) -> dict:
  reset_kb_cache()
  if use_learning:
    set_kb_profile(kb_profile, kb_snapshot)
  df = load_eurusd_h1(DEFAULT_START_DATE)
  return get_monitor_state(
    df, use_learning=use_learning,
    spread_pips=spread_pips, slippage_pips=slippage_pips,
    kb_profile=kb_profile if use_learning else None,
    kb_snapshot=kb_snapshot if use_learning else None,
  )
