"""Live BridgeEngine path must remine the same strategy as Health OOS weekly_log."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from gui.bridge_model_monitor import compare_live_week_to_oos
from gui.trade_model import get_model_by_id, load_model_report
from mt5_bridge.engine import BridgeEngine, _normalize
from mt5_bridge.history_sync import utc_to_broker_time
from mt5_bridge.protocol import BRIDGE_DIR

MODEL_ID = "tm_m15_best_2_49216b56"
WEEK = "2026-01-26"


@pytest.fixture(scope="module")
def mt5_frame() -> pd.DataFrame:
  path = Path(__file__).resolve().parents[1] / "data" / "mt5_eurusd_h1.parquet"
  if not path.exists():
    pytest.skip("mt5 h1 cache missing")
  return _normalize(pd.read_parquet(path))


def test_compare_helper_finds_oos_week():
  model = get_model_by_id(MODEL_ID)
  if not model:
    pytest.skip("trade model missing")
  report = load_model_report(MODEL_ID)
  if not report:
    pytest.skip("model health report missing")
  row = next(
    (w for w in (report.get("weekly_log") or []) if str(w.get("week_start"))[:10] == WEEK),
    None,
  )
  if not row:
    pytest.skip(f"week {WEEK} not in report")
  parity = compare_live_week_to_oos(
    model,
    week_start=WEEK,
    strategy_name=row.get("strategy"),
    conditions_fp=None,
  )
  assert parity["status"] == "match"
  assert parity["strategy_match"] is True
  assert parity["oos_strategy"] == row.get("strategy")


def test_live_decide_strategy_matches_oos_week(mt5_frame, tmp_path):
  model = get_model_by_id(MODEL_ID)
  report = load_model_report(MODEL_ID)
  if not model or not report:
    pytest.skip("model/report missing")
  row = next(
    (w for w in (report.get("weekly_log") or []) if str(w.get("week_start"))[:10] == WEEK),
    None,
  )
  if not row:
    pytest.skip(f"week {WEEK} not in report")

  week_start = pd.Timestamp(WEEK)
  bar_ts = week_start + pd.Timedelta(days=7) - pd.Timedelta(hours=1)
  if bar_ts not in mt5_frame.index:
    # pad to nearest available bar at/before target
    idx = mt5_frame.index.get_indexer([bar_ts], method="pad")[0]
    if idx < 0:
      pytest.skip("bar not in cache")
    bar_ts = mt5_frame.index[idx]

  cache = tmp_path / "mt5.parquet"
  # Full history through tip — Live path uses full FeatureMatrix like OOS
  mt5_frame.to_parquet(cache)
  eng = BridgeEngine(
    model_id=MODEL_ID,
    mt5_cache=cache,
    bridge_dir=BRIDGE_DIR,
  )
  eng.ensure_history()
  row_px = mt5_frame.loc[bar_ts]
  bar = {
    "time": utc_to_broker_time(bar_ts).strftime("%Y.%m.%d %H:%M"),
    "open": float(row_px.Open),
    "high": float(row_px.High),
    "low": float(row_px.Low),
    "close": float(row_px.Close),
    "tick_volume": float(row_px.Volume),
  }
  decision = eng.decide_for_bar(bar)
  assert decision.get("strategy_name") == row.get("strategy")
  assert str(decision.get("week_start") or "")[:10] == WEEK

  parity = compare_live_week_to_oos(
    model,
    week_start=decision.get("week_start"),
    strategy_name=decision.get("strategy_name"),
    conditions_fp=decision.get("conditions_fp"),
  )
  assert parity["strategy_match"] is True
  assert parity["status"] == "match"
