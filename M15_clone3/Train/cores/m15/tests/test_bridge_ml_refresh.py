"""Regression: mid-week bar append must not IndexError; live last bar can signal."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from mt5_bridge.engine import BridgeEngine, _normalize
from mt5_bridge.history_sync import utc_to_broker_time


def _bar_payload(frame: pd.DataFrame, ts: pd.Timestamp) -> dict:
  row = frame.loc[ts]
  return {
    "time": utc_to_broker_time(ts).strftime("%Y.%m.%d %H:%M"),
    "open": float(row.Open),
    "high": float(row.High),
    "low": float(row.Low),
    "close": float(row.Close),
    "tick_volume": float(row.Volume),
  }


@pytest.fixture(scope="module")
def mt5_frame() -> pd.DataFrame:
  path = Path(__file__).resolve().parents[1] / "data" / "mt5_eurusd_m15.parquet"
  if not path.exists():
    pytest.skip("mt5 m15 cache missing")
  return _normalize(pd.read_parquet(path))


def test_decide_survives_in_session_append_with_cached_strat(mt5_frame, tmp_path):
  # Broker 08:00 on 2026-07-23 — inside session, after weekly strat is cached.
  target = pd.Timestamp("2026-07-23 05:00:00")
  assert target in mt5_frame.index
  cut = int(mt5_frame.index.get_loc(target))
  cache = tmp_path / "mt5.parquet"
  mt5_frame.iloc[:cut].to_parquet(cache)

  eng = BridgeEngine(model_id="tm_m15_best_2_49216b56", mt5_cache=cache)
  eng.load()
  warmup = eng.decide_for_bar(_bar_payload(eng._df, eng._df.index[-1]))
  assert warmup.get("action") in {"FLAT", "BUY", "SELL", "HOLD"}
  assert eng._strat_cache, "expected weekly strategy cache"

  strat = next(iter(eng._strat_cache.values()))
  ml = strat.ml_scorer
  assert ml is not None and ml._prob_long is not None
  probs_before = len(ml._prob_long)

  # First in-session append is the known paper SHORT signal bar (last bar live).
  first = mt5_frame.index[cut]
  decision = eng.decide_for_bar(_bar_payload(mt5_frame, first))
  assert decision.get("action") in {"FLAT", "BUY", "SELL", "HOLD"}
  assert decision.get("reason") != "error"
  assert len(ml._prob_long) == len(eng._df)
  assert len(ml._prob_long) >= probs_before
  # Live last-bar path should be able to emit SELL for this known signal.
  assert decision.get("action") == "SELL"
  assert decision.get("reason") == "signal"

  # Further appends must not IndexError on stale ML probs.
  for ts in mt5_frame.index[cut + 1:cut + 3]:
    decision = eng.decide_for_bar(_bar_payload(mt5_frame, ts))
    assert decision.get("action") in {"FLAT", "BUY", "SELL", "HOLD"}
    assert len(ml._prob_long) == len(eng._df)
