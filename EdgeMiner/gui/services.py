"""GUI data services — load reports, run jobs."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from config import (
  DEFAULT_HOLDOUT_MONTHS, DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS,
  DEFAULT_START_DATE, DEFAULT_RISK_PCT_PER_TRADE,
)
from data_loader import META_PATH, load_eurusd_h1, download_eurusd_h1
from knowledge_base import KnowledgeBase, KNOWLEDGE_PATH
from paper_monitor import get_monitor_state
from run_backtest import run_walk_forward, save_backtest_report, REPORT_DIR
from run_learning import run_epoch

BACKTEST_REPORT = REPORT_DIR / "backtest_report.json"
LEARNING_REPORT = REPORT_DIR / "learning_report.json"


def load_json(path: Path) -> dict | None:
  if not path.exists():
    return None
  with open(path, encoding="utf-8") as f:
    return json.load(f)


def load_backtest_report() -> dict | None:
  return load_json(BACKTEST_REPORT)


def load_learning_report() -> dict | None:
  return load_json(LEARNING_REPORT)


def load_data_meta() -> dict:
  return load_json(META_PATH) or {}


def load_kb() -> KnowledgeBase:
  return KnowledgeBase()


def get_ohlc_df(start: str = DEFAULT_START_DATE) -> pd.DataFrame:
  return load_eurusd_h1(start)


def refresh_market_data(start: str = DEFAULT_START_DATE) -> pd.DataFrame:
  return download_eurusd_h1(start, force_refresh=True)


def execute_backtest(
  use_learning: bool = False,
  train_months: int = 3,
  start_date: str = DEFAULT_START_DATE,
  spread_pips: float = DEFAULT_SPREAD_PIPS,
  slippage_pips: float = DEFAULT_SLIPPAGE_PIPS,
  holdout_months: int = DEFAULT_HOLDOUT_MONTHS,
  risk_pct: float = DEFAULT_RISK_PCT_PER_TRADE,
  on_progress=None,
) -> dict:
  df = load_eurusd_h1(start_date)
  result = run_walk_forward(
    df,
    use_learning=use_learning,
    train_months=train_months,
    spread_pips=spread_pips,
    slippage_pips=slippage_pips,
    holdout_months=holdout_months,
    risk_pct_per_trade=risk_pct,
    on_progress=on_progress,
    verbose=False,
  )
  save_backtest_report(result)
  return result


def execute_learning(
  epochs: int = 2,
  reset_kb: bool = False,
  start_date: str = DEFAULT_START_DATE,
  on_epoch_done=None,
) -> dict:
  from feature_engine import FeatureMatrix

  if reset_kb and KNOWLEDGE_PATH.exists():
    KNOWLEDGE_PATH.unlink()

  kb = KnowledgeBase()
  df = load_eurusd_h1(start_date)
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

  report = {
    "epochs": epochs,
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
  return report


def get_paper_monitor(use_learning: bool = False, spread_pips: float = DEFAULT_SPREAD_PIPS,
                      slippage_pips: float = DEFAULT_SLIPPAGE_PIPS) -> dict:
  df = load_eurusd_h1(DEFAULT_START_DATE)
  return get_monitor_state(df, use_learning=use_learning,
                           spread_pips=spread_pips, slippage_pips=slippage_pips)
