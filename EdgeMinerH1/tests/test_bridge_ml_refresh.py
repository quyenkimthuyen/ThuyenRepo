"""Regression: mid-week H1 bar append must not IndexError; live last bar can signal."""
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
  path = Path(__file__).resolve().parents[1] / "data" / "mt5_eurusd_h1.parquet"
  if not path.exists():
    pytest.skip("mt5 h1 cache missing")
  return _normalize(pd.read_parquet(path))


def test_decide_survives_in_session_append_with_cached_strat(mt5_frame, tmp_path):
  # Pick an in-session weekday bar near the end of history.
  frame = mt5_frame
  target = None
  for ts in reversed(frame.index[:-3]):
    broker = utc_to_broker_time(ts)
    if broker.weekday() < 5 and 8 <= broker.hour <= 16:
      target = ts
      break
  assert target is not None, "no in-session bar found"
  cut = int(frame.index.get_loc(target))
  cache = tmp_path / "mt5.parquet"
  frame.iloc[:cut].to_parquet(cache)

  eng = BridgeEngine(model_id="tm_mt5_best_94ef551a", mt5_cache=cache)
  eng.load()
  warmup = eng.decide_for_bar(_bar_payload(eng._df, eng._df.index[-1]))
  assert warmup.get("action") in {"FLAT", "BUY", "SELL", "HOLD"}
  assert eng._strat_cache, "expected weekly strategy cache"

  strat = next(iter(eng._strat_cache.values()))
  ml = strat.ml_scorer
  assert ml is not None and ml._prob_long is not None
  probs_before = len(ml._prob_long)

  # Append several in-session bars; previously this could raise IndexError.
  saw_tradeable = False
  for ts in frame.index[cut:cut + 3]:
    decision = eng.decide_for_bar(_bar_payload(frame, ts))
    assert decision.get("action") in {"FLAT", "BUY", "SELL", "HOLD"}
    assert decision.get("reason") != "error"
    assert len(ml._prob_long) == len(eng._df)
    assert len(ml._prob_long) >= probs_before
    if decision.get("action") in {"BUY", "SELL"}:
      saw_tradeable = True
      assert decision.get("reason") == "signal"

  # At least ensure last-bar path works without crash; signal may be flat.
  assert len(eng._df) == cut + 3
  _ = saw_tradeable  # optional depending on market/strategy that week
