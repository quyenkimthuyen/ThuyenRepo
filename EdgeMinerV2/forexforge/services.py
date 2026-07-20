"""Service layer for CLI/UI — no Streamlit dependency."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

from .config import (
  DEFAULT_HOLDOUT_MONTHS,
  DEFAULT_RISK_PCT_PER_TRADE,
  DEFAULT_SLIPPAGE_PIPS,
  DEFAULT_SPREAD_PIPS,
  DEFAULT_START_DATE,
)
from .contracts import CostModel, InstrumentSpec, JobKind, Report, RunSpec
from .data_loader import META_PATH, download_eurusd_h1, load_eurusd_h1
from .guardrails import check_epoch_limit
from .jobs import submit_job
from .kb_profiles import (
  DEFAULT_PROFILE_ID,
  create_profile,
  delete_profile,
  list_profiles,
  list_snapshots,
  load_kb,
  suggest_profiles_for_oos,
)
from .leakage import LeakageError, assert_no_leakage, check_kb_leakage
from .logging_util import get_logger
from .optimizer import reset_kb_cache
from .paper_monitor import get_monitor_state
from .paths import RESULTS_DIR, ensure_dirs
from .store import Store
from .wf_runner import execute_run

log = get_logger("forexforge.services")
ProgressCb = Optional[Callable[[int, int, object], None]]


def load_data_meta() -> dict:
  if not META_PATH.exists():
    return {}
  with open(META_PATH, encoding="utf-8") as f:
    return json.load(f)


def refresh_market_data(start: str = DEFAULT_START_DATE) -> pd.DataFrame:
  log.info("Refreshing market data from %s", start)
  return download_eurusd_h1(start, force_refresh=True)


def get_ohlc(start: str = DEFAULT_START_DATE, end: str | None = None) -> pd.DataFrame:
  return load_eurusd_h1(start, end)


def run_backtest_sync(
  *,
  use_kb: bool = False,
  train_months: int = 3,
  start_date: str = DEFAULT_START_DATE,
  spread_pips: float = DEFAULT_SPREAD_PIPS,
  slippage_pips: float = DEFAULT_SLIPPAGE_PIPS,
  holdout_months: int = DEFAULT_HOLDOUT_MONTHS,
  risk_pct: float = DEFAULT_RISK_PCT_PER_TRADE,
  kb_profile: str = DEFAULT_PROFILE_ID,
  kb_epoch: int | str | None = None,
  oos_from: str | None = None,
  oos_to: str | None = None,
  label: str | None = None,
  on_progress: ProgressCb = None,
  archive: bool = True,
) -> tuple[Report, str | None]:
  ensure_dirs()
  if use_kb:
    assert_no_leakage(kb_profile, oos_from or start_date)
  spec = RunSpec(
    kind=JobKind.BACKTEST,
    instrument=InstrumentSpec(),
    cost=CostModel(spread_pips=spread_pips, slippage_pips=slippage_pips),
    train_months=train_months,
    use_kb=use_kb,
    kb_profile=kb_profile if use_kb else None,
    kb_epoch=kb_epoch if use_kb else None,
    oos_from=oos_from,
    oos_to=oos_to,
    data_from=start_date,
    holdout_months=holdout_months,
    risk_pct_per_trade=risk_pct,
    label=label,
  )
  reset_kb_cache()
  df = load_eurusd_h1(start_date)
  report = execute_run(df, spec, on_progress=on_progress, verbose=False)
  report_id = None
  if archive:
    store = Store()
    run_id = store.create_run(spec, status="done")
    report_id = store.save_report(run_id, report)
    path = RESULTS_DIR / f"report_{report_id}.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    log.info("Archived report_id=%s path=%s", report_id, path)
  return report, report_id


def submit_backtest_job(**kwargs) -> str:
  use_kb = kwargs.get("use_kb", False)
  spec = RunSpec(
    kind=JobKind.BACKTEST,
    instrument=InstrumentSpec(),
    cost=CostModel(
      spread_pips=kwargs.get("spread_pips", DEFAULT_SPREAD_PIPS),
      slippage_pips=kwargs.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS),
    ),
    train_months=kwargs.get("train_months", 3),
    use_kb=use_kb,
    kb_profile=kwargs.get("kb_profile") if use_kb else None,
    kb_epoch=kwargs.get("kb_epoch") if use_kb else None,
    oos_from=kwargs.get("oos_from"),
    oos_to=kwargs.get("oos_to"),
    data_from=kwargs.get("start_date", DEFAULT_START_DATE),
    holdout_months=kwargs.get("holdout_months", 0),
    risk_pct_per_trade=kwargs.get("risk_pct", 1.0),
    label=kwargs.get("label"),
  )
  if use_kb:
    assert_no_leakage(spec.kb_profile, spec.oos_from_str() or spec.data_from)
  handle = submit_job(spec, background=True)
  return handle.job_id


def run_learn_sync(
  *,
  kb_profile: str,
  epochs: int = 3,
  from_date: str = DEFAULT_START_DATE,
  until_date: str | None = None,
  kb_name: str | None = None,
  spread_pips: float = DEFAULT_SPREAD_PIPS,
  slippage_pips: float = DEFAULT_SLIPPAGE_PIPS,
  on_progress: ProgressCb = None,
) -> Report:
  verdict = check_epoch_limit(kb_profile, additional=epochs)
  if not verdict.ok:
    raise ValueError(verdict.reasons[0])
  if kb_profile != DEFAULT_PROFILE_ID:
    create_profile(kb_profile, kb_name or kb_profile)
  spec = RunSpec(
    kind=JobKind.LEARN,
    cost=CostModel(spread_pips=spread_pips, slippage_pips=slippage_pips),
    use_kb=True,
    kb_profile=kb_profile,
    data_from=from_date,
    data_to=until_date,
    epochs=epochs,
    label=kb_name or kb_profile,
  )
  df = load_eurusd_h1(from_date, until_date)
  report = execute_run(df, spec, on_progress=on_progress, verbose=False)
  store = Store()
  run_id = store.create_run(spec, status="done")
  store.save_report(run_id, report)
  return report


def submit_learn_job(**kwargs) -> str:
  profile = kwargs["kb_profile"]
  epochs = int(kwargs.get("epochs", 3))
  verdict = check_epoch_limit(profile, additional=epochs)
  if not verdict.ok:
    raise ValueError(verdict.reasons[0])
  spec = RunSpec(
    kind=JobKind.LEARN,
    cost=CostModel(
      spread_pips=kwargs.get("spread_pips", DEFAULT_SPREAD_PIPS),
      slippage_pips=kwargs.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS),
    ),
    use_kb=True,
    kb_profile=profile,
    data_from=kwargs.get("from_date", DEFAULT_START_DATE),
    data_to=kwargs.get("until_date"),
    epochs=epochs,
    label=kwargs.get("kb_name") or profile,
  )
  return submit_job(spec, background=True).job_id


def paper_state(
  *,
  use_kb: bool = False,
  kb_profile: str | None = None,
  kb_epoch: int | str | None = None,
  spread_pips: float = DEFAULT_SPREAD_PIPS,
  slippage_pips: float = DEFAULT_SLIPPAGE_PIPS,
) -> dict[str, Any]:
  df = load_eurusd_h1(DEFAULT_START_DATE)
  return get_monitor_state(
    df,
    use_learning=use_kb,
    kb_profile=kb_profile,
    kb_snapshot=kb_epoch,
    spread_pips=spread_pips,
    slippage_pips=slippage_pips,
  )


def profiles() -> list[dict]:
  return list_profiles()


def snapshots(profile_id: str) -> list[dict]:
  return list_snapshots(profile_id)


def kb(profile_id: str = DEFAULT_PROFILE_ID):
  return load_kb(profile_id)


def leakage_status(profile_id: str, oos_from: str):
  return check_kb_leakage(profile_id, oos_from)


__all__ = [
  "LeakageError",
  "DEFAULT_PROFILE_ID",
  "Store",
  "create_profile",
  "delete_profile",
  "get_ohlc",
  "kb",
  "leakage_status",
  "load_data_meta",
  "paper_state",
  "profiles",
  "refresh_market_data",
  "run_backtest_sync",
  "run_learn_sync",
  "snapshots",
  "submit_backtest_job",
  "submit_learn_job",
  "suggest_profiles_for_oos",
]
