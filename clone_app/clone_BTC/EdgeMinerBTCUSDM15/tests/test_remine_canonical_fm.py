"""Remine must not lock a weaker strategy from a truncated HistoryFeed tip."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from gui.trade_model import get_model_by_id
from mt5_bridge.engine import BridgeEngine, _normalize
from mt5_bridge.history_sync import utc_to_broker_time
from mt5_bridge.trade_journal import save_trades

MODEL_ID = "tm_m15_best_2_49216b56"
WEEK = "2026-03-16"
ROOT = Path(__file__).resolve().parents[1]


def _bar_payload(frame: pd.DataFrame, bar_ts: pd.Timestamp) -> dict:
  row = frame.loc[bar_ts]
  return {
    "time": utc_to_broker_time(bar_ts).strftime("%Y.%m.%d %H:%M"),
    "open": float(row.Open),
    "high": float(row.High),
    "low": float(row.Low),
    "close": float(row.Close),
    "tick_volume": float(row.Volume),
  }


@pytest.fixture(scope="module")
def mt5_frame() -> pd.DataFrame:
  path = ROOT / "data" / "mt5_btcusd_m15.parquet"
  if not path.exists():
    pytest.skip("mt5 m15 cache missing")
  return _normalize(pd.read_parquet(path))


def test_remine_truncated_monday_matches_full_tip(mt5_frame, tmp_path):
  """Working series truncated at Monday remine must still match full-tip strategy.

  Uses canonical parquet on disk for ``_remine_week_strategy`` while in-memory
  ``_df`` starts short — mimics HistoryFeed before the week tip is fed.
  """
  model = get_model_by_id(MODEL_ID)
  if not model:
    pytest.skip("trade model missing")

  week_start = pd.Timestamp(WEEK)
  monday = week_start
  # First M15 bar of the week
  week_bars = mt5_frame.index[
    (mt5_frame.index >= week_start) & (mt5_frame.index < week_start + pd.Timedelta(days=7))
  ]
  if len(week_bars) < 10:
    pytest.skip("not enough bars in week")
  monday_bar = week_bars[0]
  tip_bar = week_bars[-1]

  # Canonical cache = FULL history (as production mt5 parquet)
  full_cache = tmp_path / "mt5_full.parquet"
  mt5_frame.to_parquet(full_cache)

  bridge = tmp_path / "bridge"
  bridge.mkdir()
  save_trades([], bridge)

  eng = BridgeEngine(model_id=MODEL_ID, mt5_cache=full_cache, bridge_dir=bridge)
  # Truncate working memory to Monday-only (bad old path) but leave canonical file full
  eng._df = mt5_frame.loc[:monday_bar].copy()
  eng._fm = None
  eng._fm_key = None

  d_mon = eng.decide_for_bar(_bar_payload(mt5_frame, monday_bar))
  name_mon = d_mon.get("strategy_name")
  assert name_mon, f"expected remine on Monday, got {d_mon}"

  # Fresh engine, full working series through tip
  eng2 = BridgeEngine(model_id=MODEL_ID, mt5_cache=full_cache, bridge_dir=bridge)
  eng2.ensure_history()
  d_tip = eng2.decide_for_bar(_bar_payload(mt5_frame, tip_bar))
  name_tip = d_tip.get("strategy_name")
  assert name_tip, f"expected remine on tip, got {d_tip}"

  assert name_mon == name_tip, (
    f"truncated Monday remine `{name_mon}` != full tip `{name_tip}` "
    f"(week={WEEK})"
  )
  assert str(d_mon.get("week_start") or "")[:10] == WEEK
  assert str(d_tip.get("week_start") or "")[:10] == WEEK
