"""Replay / remine FeatureMatrix must not include bars after the as-of cut."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from mt5_bridge.engine import (
  BridgeEngine,
  _frame_before,
  _frame_through,
  _normalize,
)
from mt5_bridge.history_sync import utc_to_broker_time


def _ohlc(idx: pd.DatetimeIndex) -> pd.DataFrame:
  n = len(idx)
  close = 1.10 + pd.Series(range(n), index=idx).astype(float) * 0.00001
  return pd.DataFrame({
    "Open": close,
    "High": close + 0.0002,
    "Low": close - 0.0002,
    "Close": close,
    "Volume": 100.0,
  }, index=idx)


def test_causalize_roc5_matches_clipped_matrix():
  from feature_engine import FeatureMatrix
  from mt5_bridge.engine import _causalize_roc5_through

  idx = pd.date_range("2026-08-01 00:00", periods=800, freq="15min")
  df = _ohlc(idx)
  bar = idx[400]
  fm_full = FeatureMatrix(df)
  fm_clip = FeatureMatrix(df.loc[:bar])
  bar_idx = int(fm_full.index.get_loc(bar))
  leaked = float(fm_full.features["roc_5"][bar_idx])
  _causalize_roc5_through(fm_full, bar_idx)
  got = float(fm_full.features["roc_5"][bar_idx])
  want = float(fm_clip.features["roc_5"][bar_idx])
  assert abs(got - want) < 1e-9
  assert abs(leaked - want) > 1e-9


def test_frame_through_drops_later_bars():
  idx = pd.date_range("2026-08-20 00:00", periods=200, freq="15min")
  df = _ohlc(idx)
  bar = idx[50]
  out = _frame_through(df, bar)
  assert out.index[-1] == bar
  assert bar in out.index
  assert idx[51] not in out.index
  assert len(out) == 51


def test_frame_before_excludes_week_open():
  idx = pd.date_range("2026-08-17 00:00", periods=800, freq="15min")
  df = _ohlc(idx)
  week = pd.Timestamp("2026-08-24")
  out = _frame_before(df, week)
  assert len(out)
  assert out.index[-1] < week
  assert week not in out.index
  assert (out.index >= week).sum() == 0


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


def test_decide_source_uses_live_as_of_projection():
  src = Path(__file__).resolve().parents[1] / "mt5_bridge" / "engine.py"
  text = src.read_text(encoding="utf-8")
  start = text.find("def decide_for_bar")
  end = text.find("def _remember")
  body = text[start:end]
  assert "as_of_closed_bar=True" in body
  assert "_causalize_roc5_through" in body
  assert "scan_end" in body


def test_compare_runner_pins_causal_universe():
  src = Path(__file__).resolve().parents[1] / "mt5_bridge" / "compare_runner.py"
  text = src.read_text(encoding="utf-8")
  assert "set_causal_universe" in text
  assert "causal_replay_universe" in text
  assert "eng._df = full.copy()" not in text


def test_decide_fm_may_keep_cached_future_rows(mt5_frame, tmp_path):
  """Working FM can stay full-length (fast). Causality is scan_end + roc_5 as-of."""
  from feature_engine import FeatureMatrix
  from gui.trade_model import get_model_by_id
  from mt5_bridge.trade_journal import save_trades

  model = get_model_by_id("tm_m15_best_2_49216b56")
  if not model:
    pytest.skip("trade model missing")

  week = pd.Timestamp("2026-07-20")
  week_bars = mt5_frame.index[
    (mt5_frame.index >= week) & (mt5_frame.index < week + pd.Timedelta(days=5))
  ]
  if len(week_bars) < 40:
    pytest.skip("not enough bars in week")
  bar_ts = week_bars[12]
  assert mt5_frame.index[-1] > bar_ts

  cache = tmp_path / "mt5_full.parquet"
  mt5_frame.to_parquet(cache)
  bridge = tmp_path / "bridge"
  bridge.mkdir()
  save_trades([], bridge)

  eng = BridgeEngine(
    model_id="tm_m15_best_2_49216b56",
    mt5_cache=cache,
    bridge_dir=bridge,
  )
  eng.ensure_history()
  decision = eng.decide_for_bar(_bar_payload(mt5_frame, bar_ts))
  assert decision.get("reason") != "error"
  assert eng._fm is not None
  bar_idx = int(eng._fm.index.get_loc(bar_ts))
  clip = FeatureMatrix(mt5_frame.loc[:bar_ts])
  got = float(eng._fm.features["roc_5"][bar_idx])
  want = float(clip.features["roc_5"][int(clip.index.get_loc(bar_ts))])
  assert abs(got - want) < 1e-6


def test_remine_fm_excludes_trading_week(mt5_frame, tmp_path, monkeypatch):
  """Remine FeatureMatrix last bar must be strictly before week_start."""
  from gui.trade_model import get_model_by_id

  model = get_model_by_id("tm_m15_best_2_49216b56")
  if not model:
    pytest.skip("trade model missing")

  week_start = pd.Timestamp("2026-07-20")
  cache = tmp_path / "mt5_full.parquet"
  mt5_frame.to_parquet(cache)
  from mt5_bridge.trade_journal import save_trades
  bridge = tmp_path / "bridge"
  bridge.mkdir()
  save_trades([], bridge)

  seen: list[pd.Timestamp] = []
  orig_fm = BridgeEngine._feature_matrix

  def _spy(self, df, feature_profile):  # noqa: ANN001
    if df is not None and len(df):
      seen.append(df.index[-1])
    return orig_fm(self, df, feature_profile)

  monkeypatch.setattr(BridgeEngine, "_feature_matrix", _spy)
  eng = BridgeEngine(
    model_id="tm_m15_best_2_49216b56",
    mt5_cache=cache,
    bridge_dir=bridge,
  )
  eng.ensure_history()
  key, train_weeks, use_learning, kb_profile, kb_snapshot, feature_profile, search_space = (
    eng._week_cache_key(week_start)
  )
  eng._remine_week_strategy(
    week_start=week_start,
    cache_key=key,
    train_weeks=train_weeks,
    use_learning=use_learning,
    kb_profile=kb_profile,
    kb_snapshot=kb_snapshot,
    feature_profile=feature_profile,
    search_space=search_space,
  )
  assert seen, "remine did not build a FeatureMatrix"
  assert seen[0] < week_start, f"remine FM last={seen[0]} not before {week_start}"


def test_set_causal_universe_remine_still_before_week(mt5_frame, tmp_path, monkeypatch):
  """Compare-style universe includes the trading week — remine must still clip."""
  from gui.trade_model import get_model_by_id
  from mt5_bridge.trade_journal import save_trades

  model = get_model_by_id("tm_m15_best_2_49216b56")
  if not model:
    pytest.skip("trade model missing")

  week_start = pd.Timestamp("2026-07-20")
  cache = tmp_path / "mt5_full.parquet"
  mt5_frame.to_parquet(cache)
  bridge = tmp_path / "bridge"
  bridge.mkdir()
  save_trades([], bridge)

  seen: list[pd.Timestamp] = []
  orig_fm = BridgeEngine._feature_matrix

  def _spy(self, df, feature_profile):  # noqa: ANN001
    if df is not None and len(df):
      seen.append(df.index[-1])
    return orig_fm(self, df, feature_profile)

  monkeypatch.setattr(BridgeEngine, "_feature_matrix", _spy)
  eng = BridgeEngine(
    model_id="tm_m15_best_2_49216b56",
    mt5_cache=cache,
    bridge_dir=bridge,
  )
  eng.set_causal_universe(mt5_frame)
  assert eng._universe is not None
  assert eng._universe.index[-1] >= week_start
  key, train_weeks, use_learning, kb_profile, kb_snapshot, feature_profile, search_space = (
    eng._week_cache_key(week_start)
  )
  eng._remine_week_strategy(
    week_start=week_start,
    cache_key=key,
    train_weeks=train_weeks,
    use_learning=use_learning,
    kb_profile=kb_profile,
    kb_snapshot=kb_snapshot,
    feature_profile=feature_profile,
    search_space=search_space,
  )
  assert seen, "remine did not build a FeatureMatrix"
  assert seen[0] < week_start, f"universe remine FM last={seen[0]} not before {week_start}"


def test_canonical_frame_reads_parquet_not_pinned_tip(tmp_path, monkeypatch):
  """HistoryFeed may pin a short OOS tip — weekly remine still trains on parquet."""
  monkeypatch.setattr("mt5_bridge.engine.resolve_model", lambda *_a, **_k: {})
  monkeypatch.setattr("mt5_bridge.engine.get_model_run_params", lambda *_a, **_k: {})
  week_start = pd.Timestamp("2026-07-20")
  idx = pd.date_range("2026-01-05", periods=12000, freq="15min")
  frame = _normalize(_ohlc(idx))
  cache = tmp_path / "mt5_full.parquet"
  frame.to_parquet(cache)
  bridge = tmp_path / "bridge"
  bridge.mkdir()
  eng = BridgeEngine(
    model_id="tm_m15_best_2_49216b56",
    mt5_cache=cache,
    bridge_dir=bridge,
  )
  tip = frame.iloc[-80:]
  eng.set_causal_universe(tip)
  assert len(eng._universe) == 80
  can = eng._canonical_frame()
  assert len(can) == len(frame)
  mine = _frame_before(can, week_start)
  tip_mine = _frame_before(eng._universe, week_start)
  assert len(mine) > 500
  assert len(mine) > len(tip_mine)
