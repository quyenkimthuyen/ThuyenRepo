"""Golden mini walk-forward — reproducibility + KB OFF baseline."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from forexforge.contracts import CostModel, JobKind, RunSpec
from forexforge.data_loader import _normalize_ohlcv
from forexforge.store import Store
from forexforge.wf_runner import run_backtest

FIXTURE = Path(__file__).parent / "fixtures" / "sample_h1.parquet"


@pytest.fixture(scope="module")
def sample_df():
  raw = pd.read_parquet(FIXTURE)
  return _normalize_ohlcv(raw)


def test_golden_one_week_kb_off(sample_df, tmp_path):
  """~1 week OOS on sample fixture — stable shape + no crash."""
  spec = RunSpec(
    kind=JobKind.BACKTEST,
    use_kb=False,
    cost=CostModel(spread_pips=1.0, slippage_pips=0.3),
    train_months=3,
    oos_from=sample_df.index[0].date().replace() if False else None,
    seed=42,
  )
  # Use last ~10 days of fixture as OOS window for speed
  oos_from = (sample_df.index[-1] - pd.Timedelta(days=10)).date()
  spec = spec.model_copy(update={"oos_from": oos_from})

  report = run_backtest(sample_df, spec, verbose=False)
  assert report.overall_oos is not None
  assert report.leakage is not None and report.leakage.ok
  assert report.spec.use_kb is False
  assert "version" in report.raw.get("config", {})
  # Deterministic-ish: same inputs → same trade count on rerun
  report2 = run_backtest(sample_df, spec, verbose=False)
  assert report.overall_oos.n_trades == report2.overall_oos.n_trades
  assert report.overall_oos.total_r == report2.overall_oos.total_r


def test_store_save_and_compare(sample_df, tmp_path):
  db = tmp_path / "t.db"
  store = Store(db)
  oos_from = (sample_df.index[-1] - pd.Timedelta(days=10)).date()
  spec = RunSpec(use_kb=False, oos_from=oos_from, label="golden-a")
  report = run_backtest(sample_df, spec, verbose=False)
  run_id = store.create_run(spec, status="done")
  rid = store.save_report(run_id, report)
  rows = store.compare_reports([rid])
  assert len(rows) == 1
  assert rows[0]["n_trades"] == report.overall_oos.n_trades
