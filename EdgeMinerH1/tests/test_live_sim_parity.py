"""Live and Simulate must share BridgeEngine decisions for the same bars.

Both modes call ``BridgeEngine.decide_for_bar`` with the same Trade Model /
FeatureMatrix path — only ``bridge_dir`` (journal) differs. Empty journals
⇒ identical decisions for identical bar payloads.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from gui.trade_model import get_model_by_id, load_model_report
from mt5_bridge.engine import BridgeEngine, _normalize
from mt5_bridge.history_sync import utc_to_broker_time
from mt5_bridge.trade_journal import save_trades

MODEL_ID = "tm_m15_best_2_49216b56"
WEEK = "2026-01-26"

# Fields that must match for Live vs Simulate (wall-clock stamp excluded)
_DECISION_COMPARE_KEYS = (
  "action",
  "signal_id",
  "strategy_name",
  "week_start",
  "conditions_fp",
  "reason",
  "model_id",
  "bar_time",
  "entry",
  "sl",
  "tp",
  "entry_time",
  "rr",
  "atr_mult_sl",
  "max_hold_bars",
  "slots_remaining",
  "exit_mode",
)


@pytest.fixture(scope="module")
def mt5_frame() -> pd.DataFrame:
  path = Path(__file__).resolve().parents[1] / "data" / "mt5_eurusd_h1.parquet"
  if not path.exists():
    pytest.skip("mt5 h1 cache missing")
  return _normalize(pd.read_parquet(path))


@pytest.fixture(scope="module")
def active_model():
  model = get_model_by_id(MODEL_ID)
  if not model:
    pytest.skip(f"trade model `{MODEL_ID}` missing")
  report = load_model_report(MODEL_ID)
  if not report:
    pytest.skip("model health report missing")
  return model, report


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


def _week_bar_timestamps(frame: pd.DataFrame, week: str, *, limit: int = 48) -> list[pd.Timestamp]:
  week_start = pd.Timestamp(week)
  week_end = week_start + pd.Timedelta(days=7)
  idx = frame.index[(frame.index >= week_start) & (frame.index < week_end)]
  if len(idx) == 0:
    return []
  # Sample across the week (not only tip) — keep runtime bounded
  step = max(1, len(idx) // limit)
  return list(idx[::step][:limit])


def _decision_slice(decision: dict) -> dict:
  return {k: decision.get(k) for k in _DECISION_COMPARE_KEYS}


def _make_pair_engines(tmp_path: Path, frame: pd.DataFrame) -> tuple[BridgeEngine, BridgeEngine]:
  """Live + Simulate engines: same model/cache content, empty journals, isolated dirs."""
  live_dir = tmp_path / "bridge_live"
  sim_dir = tmp_path / "bridge_sim"
  live_dir.mkdir(parents=True)
  sim_dir.mkdir(parents=True)
  save_trades([], live_dir)
  save_trades([], sim_dir)

  cache_live = tmp_path / "mt5_live.parquet"
  cache_sim = tmp_path / "mt5_sim.parquet"
  frame.to_parquet(cache_live)
  frame.to_parquet(cache_sim)

  live = BridgeEngine(
    model_id=MODEL_ID,
    mt5_cache=cache_live,
    bridge_dir=live_dir,
  )
  sim = BridgeEngine(
    model_id=MODEL_ID,
    mt5_cache=cache_sim,
    bridge_dir=sim_dir,
  )
  live.ensure_history()
  sim.ensure_history()
  return live, sim


def test_live_sim_share_conditions_fp(mt5_frame, active_model, tmp_path):
  live, sim = _make_pair_engines(tmp_path, mt5_frame)
  assert live.conditions_fp
  assert live.conditions_fp == sim.conditions_fp
  assert live.params.get("trade_model_id") == MODEL_ID
  assert sim.params.get("trade_model_id") == MODEL_ID


def test_live_sim_same_decision_on_same_bars(mt5_frame, active_model, tmp_path):
  _, report = active_model
  row = next(
    (w for w in (report.get("weekly_log") or []) if str(w.get("week_start"))[:10] == WEEK),
    None,
  )
  if not row:
    pytest.skip(f"week {WEEK} not in weekly_log")

  bars = _week_bar_timestamps(mt5_frame, WEEK, limit=24)
  if not bars:
    pytest.skip(f"no H1 bars for week {WEEK}")

  live, sim = _make_pair_engines(tmp_path, mt5_frame)
  assert live.conditions_fp == sim.conditions_fp

  matched_signal = False
  for ts in bars:
    payload = _bar_payload(mt5_frame, ts)
    d_live = live.decide_for_bar(payload)
    d_sim = sim.decide_for_bar(payload)
    assert _decision_slice(d_live) == _decision_slice(d_sim), (
      f"Live≠Sim at {payload.get('time')}: "
      f"live={_decision_slice(d_live)} sim={_decision_slice(d_sim)}"
    )
    assert str(d_live.get("week_start") or "")[:10] == WEEK
    if d_live.get("action") in ("BUY", "SELL"):
      matched_signal = True
      assert d_live.get("strategy_name") == row.get("strategy")
      assert d_live.get("strategy_name") == d_sim.get("strategy_name")
      assert d_live.get("conditions_fp") == live.conditions_fp

  # At least remine produced a named strategy on FLAT bars too
  tip = live.decide_for_bar(_bar_payload(mt5_frame, bars[-1]))
  assert tip.get("strategy_name") == row.get("strategy") or tip.get("strategy_name")
  # Soft: if week has no signal in sampled bars, still OK if strategy remine matched
  if not matched_signal:
    assert tip.get("strategy_name") == row.get("strategy")


def test_live_sim_hold_flat_contract_identical(mt5_frame, active_model, tmp_path):
  """With empty journals, HOLD/FLAT reasons must match (no divergent open-position logic)."""
  bars = _week_bar_timestamps(mt5_frame, WEEK, limit=12)
  if len(bars) < 2:
    pytest.skip("need ≥2 bars in week")

  live, sim = _make_pair_engines(tmp_path, mt5_frame)
  reasons = []
  for ts in bars:
    payload = _bar_payload(mt5_frame, ts)
    d_live = live.decide_for_bar(payload)
    d_sim = sim.decide_for_bar(payload)
    assert d_live.get("action") == d_sim.get("action")
    assert d_live.get("reason") == d_sim.get("reason")
    reasons.append(d_live.get("reason"))
  # Sanity: engine actually decided something known
  assert any(r in ("no_signal", "signal", "no_slots", "position_open", "levels_unavailable") for r in reasons)


def test_live_sim_signal_id_stable_across_modes(mt5_frame, active_model, tmp_path):
  """Same bar + action ⇒ same signal_id (EA/App handshake key)."""
  week_start = pd.Timestamp(WEEK)
  week_end = week_start + pd.Timedelta(days=7)
  bars = list(mt5_frame.index[(mt5_frame.index >= week_start) & (mt5_frame.index < week_end)])
  if not bars:
    pytest.skip("no bars")

  live, sim = _make_pair_engines(tmp_path, mt5_frame)
  # Warm remine once, then scan for a real signal bar
  live.decide_for_bar(_bar_payload(mt5_frame, bars[0]))
  sim.decide_for_bar(_bar_payload(mt5_frame, bars[0]))

  for ts in bars:
    payload = _bar_payload(mt5_frame, ts)
    d_live = live.decide_for_bar(payload)
    d_sim = sim.decide_for_bar(payload)
    assert d_live.get("signal_id") == d_sim.get("signal_id")
    if d_live.get("action") in ("BUY", "SELL"):
      assert d_live.get("signal_id")
      assert d_live.get("entry") == d_sim.get("entry")
      assert d_live.get("sl") == d_sim.get("sl")
      assert d_live.get("tp") == d_sim.get("tp")
      return
  pytest.skip("no BUY/SELL in week — remine ran but week had no open signals under empty journal")
