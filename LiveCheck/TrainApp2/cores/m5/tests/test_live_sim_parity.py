"""Live and Simulate must share BridgeEngine decisions for the same bars.

Guarantee for traders: switching Live ↔ Simulate does not change remine /
signal logic — only ``bridge_dir`` (journal) and ``magic`` differ. Empty
journals + identical bar OHLC ⇒ identical decisions (action, levels, fp).

Execution (OrderSend vs paper OHLC) is out of scope — that path intentionally
diverges. These tests lock the *decision* contract.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from gui.trade_model import list_trade_models, load_model_report
from mt5_bridge.engine import BridgeEngine, _normalize
from mt5_bridge.history_sync import utc_to_broker_time
from mt5_bridge.protocol import DEFAULT_MAGIC, DEFAULT_SIM_MAGIC
from mt5_bridge.trade_journal import save_trades

# Fields that must match for Live vs Simulate (wall-clock / magic excluded)
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
  path = Path(__file__).resolve().parents[1] / "data" / "mt5_eurusd_m5.parquet"
  if not path.exists():
    pytest.skip("mt5 m15 cache missing")
  return _normalize(pd.read_parquet(path))


@pytest.fixture(scope="module")
def resolved_model(mt5_frame):
  """Pick any Trade Model that has a health report + bars in cache."""
  for model in list_trade_models():
    mid = model.get("id")
    if not mid:
      continue
    report = load_model_report(mid)
    if not report:
      continue
    weeks = [
      str(w.get("week_start") or "")[:10]
      for w in (report.get("weekly_log") or [])
      if w.get("week_start")
    ]
    for week in weeks:
      if _week_bar_timestamps(mt5_frame, week, limit=4):
        return model, report, week, mid
  pytest.skip("no Trade Model with report + matching bars in MT5 cache")


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
  step = max(1, len(idx) // limit)
  return list(idx[::step][:limit])


def _all_week_bars(frame: pd.DataFrame, week: str) -> list[pd.Timestamp]:
  week_start = pd.Timestamp(week)
  week_end = week_start + pd.Timedelta(days=7)
  return list(frame.index[(frame.index >= week_start) & (frame.index < week_end)])


def _decision_slice(decision: dict) -> dict:
  return {k: decision.get(k) for k in _DECISION_COMPARE_KEYS}


def _make_pair_engines(
  tmp_path: Path,
  frame: pd.DataFrame,
  model_id: str,
) -> tuple[BridgeEngine, BridgeEngine]:
  """Live + Simulate engines: same model/cache, empty journals, real magics."""
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
    model_id=model_id,
    mt5_cache=cache_live,
    bridge_dir=live_dir,
    magic=DEFAULT_MAGIC,
  )
  sim = BridgeEngine(
    model_id=model_id,
    mt5_cache=cache_sim,
    bridge_dir=sim_dir,
    magic=DEFAULT_SIM_MAGIC,
  )
  live.ensure_history()
  sim.ensure_history()
  return live, sim


def test_live_sim_share_conditions_fp(mt5_frame, resolved_model, tmp_path):
  model, _report, _week, mid = resolved_model
  live, sim = _make_pair_engines(tmp_path, mt5_frame, mid)
  assert live.conditions_fp
  assert live.conditions_fp == sim.conditions_fp
  assert live.params.get("trade_model_id") == mid
  assert sim.params.get("trade_model_id") == mid
  # Magics differ like real EA Live vs Sim — must not affect remine fp
  assert live.magic == DEFAULT_MAGIC
  assert sim.magic == DEFAULT_SIM_MAGIC
  assert live.magic != sim.magic
  assert live.params == sim.params


def test_live_sim_same_decision_on_same_bars(mt5_frame, resolved_model, tmp_path):
  _model, report, week, mid = resolved_model
  row = next(
    (w for w in (report.get("weekly_log") or []) if str(w.get("week_start"))[:10] == week),
    None,
  )
  if not row:
    pytest.skip(f"week {week} not in weekly_log")

  bars = _week_bar_timestamps(mt5_frame, week, limit=24)
  if not bars:
    pytest.skip(f"no M15 bars for week {week}")

  live, sim = _make_pair_engines(tmp_path, mt5_frame, mid)
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
    assert str(d_live.get("week_start") or "")[:10] == week
    if d_live.get("action") in ("BUY", "SELL"):
      matched_signal = True
      assert d_live.get("strategy_name") == row.get("strategy")
      assert d_live.get("strategy_name") == d_sim.get("strategy_name")
      assert d_live.get("conditions_fp") == live.conditions_fp

  tip_live = live.decide_for_bar(_bar_payload(mt5_frame, bars[-1]))
  tip_sim = sim.decide_for_bar(_bar_payload(mt5_frame, bars[-1]))
  assert _decision_slice(tip_live) == _decision_slice(tip_sim)
  assert tip_live.get("strategy_name")
  # OOS weekly_log may drift vs fresh remine; Live↔Sim identity is the contract here.
  if matched_signal:
    assert tip_live.get("strategy_name") == row.get("strategy")
    assert tip_sim.get("strategy_name") == row.get("strategy")


def test_live_sim_hold_flat_contract_identical(mt5_frame, resolved_model, tmp_path):
  """With empty journals, HOLD/FLAT reasons must match (no divergent open-position logic)."""
  _model, _report, week, mid = resolved_model
  bars = _week_bar_timestamps(mt5_frame, week, limit=12)
  if len(bars) < 2:
    pytest.skip("need ≥2 bars in week")

  live, sim = _make_pair_engines(tmp_path, mt5_frame, mid)
  reasons = []
  for ts in bars:
    payload = _bar_payload(mt5_frame, ts)
    d_live = live.decide_for_bar(payload)
    d_sim = sim.decide_for_bar(payload)
    assert d_live.get("action") == d_sim.get("action")
    assert d_live.get("reason") == d_sim.get("reason")
    reasons.append(d_live.get("reason"))
  assert any(
    r in ("no_signal", "signal", "no_slots", "position_open", "levels_unavailable")
    for r in reasons
  )


def test_live_sim_signal_id_stable_across_modes(mt5_frame, resolved_model, tmp_path):
  """Same bar + action ⇒ same signal_id (EA/App handshake key)."""
  _model, _report, week, mid = resolved_model
  bars = _all_week_bars(mt5_frame, week)
  if not bars:
    pytest.skip("no bars")

  live, sim = _make_pair_engines(tmp_path, mt5_frame, mid)
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


def test_live_sim_parity_across_oos_weeks(mt5_frame, resolved_model, tmp_path):
  """Sample several OOS weeks — Live/Sim decisions stay identical."""
  _model, report, _week, mid = resolved_model
  weeks: list[str] = []
  for w in report.get("weekly_log") or []:
    week = str(w.get("week_start") or "")[:10]
    if week and _week_bar_timestamps(mt5_frame, week, limit=2):
      weeks.append(week)
    if len(weeks) >= 3:
      break
  if len(weeks) < 2:
    pytest.skip("need ≥2 OOS weeks with bars")

  live, sim = _make_pair_engines(tmp_path, mt5_frame, mid)
  mismatches = []
  for week in weeks:
    for ts in _week_bar_timestamps(mt5_frame, week, limit=8):
      payload = _bar_payload(mt5_frame, ts)
      d_live = live.decide_for_bar(payload)
      d_sim = sim.decide_for_bar(payload)
      if _decision_slice(d_live) != _decision_slice(d_sim):
        mismatches.append({
          "time": payload.get("time"),
          "live": _decision_slice(d_live),
          "sim": _decision_slice(d_sim),
        })
  assert not mismatches, f"Live≠Sim on {len(mismatches)} bars: {mismatches[:3]}"


def test_live_only_open_journal_diverges_then_clears(mt5_frame, resolved_model, tmp_path):
  """Journal is the *only* Live/Sim decision fork: open Live position → HOLD; clear → match again."""
  _model, _report, week, mid = resolved_model
  bars = _all_week_bars(mt5_frame, week)
  if len(bars) < 4:
    pytest.skip("need several bars in week")

  live, sim = _make_pair_engines(tmp_path, mt5_frame, mid)
  live_dir = tmp_path / "bridge_live"
  sim_dir = tmp_path / "bridge_sim"

  signal_ts = None
  signal_payload = None
  for ts in bars:
    payload = _bar_payload(mt5_frame, ts)
    d = live.decide_for_bar(payload)
    sim.decide_for_bar(payload)
    if d.get("action") in ("BUY", "SELL"):
      signal_ts = ts
      signal_payload = payload
      break
  if signal_ts is None:
    pytest.skip("no BUY/SELL bar to demonstrate journal gate")

  # Reset engine caches so re-decide is fresh after journal change
  live._last_bar_key = None
  live._last_decision = None
  sim._last_bar_key = None
  sim._last_decision = None

  broker_t = utc_to_broker_time(signal_ts).strftime("%Y.%m.%d %H:%M")
  save_trades(
    [{
      "id": "parity_open",
      "status": "OPEN",
      "mode": "auto",
      "direction": "BUY",
      "entry_time": broker_t,
      "bar_time": broker_t,
      "entry_px": 1.1,
      "sl": 1.09,
      "tp": 1.12,
      "model_id": mid,
    }],
    live_dir,
  )
  save_trades([], sim_dir)

  d_live = live.decide_for_bar(signal_payload)
  d_sim = sim.decide_for_bar(signal_payload)
  assert d_live.get("reason") == "position_open"
  assert d_live.get("action") in ("HOLD", "FLAT") or d_live.get("reason") == "position_open"
  assert d_sim.get("action") in ("BUY", "SELL")
  assert _decision_slice(d_live) != _decision_slice(d_sim)

  # Clear Live journal → decisions converge again
  save_trades([], live_dir)
  live._last_bar_key = None
  live._last_decision = None
  sim._last_bar_key = None
  sim._last_decision = None
  d_live2 = live.decide_for_bar(signal_payload)
  d_sim2 = sim.decide_for_bar(signal_payload)
  assert _decision_slice(d_live2) == _decision_slice(d_sim2)
  assert d_live2.get("action") in ("BUY", "SELL")


def test_active_model_params_identical_for_live_and_sim_dirs(mt5_frame, resolved_model, tmp_path):
  """Same Trade Model id ⇒ identical run params / fp regardless of bridge folder."""
  from mt5_bridge.models import conditions_fingerprint, get_model_run_params

  model, _report, _week, mid = resolved_model
  p_live = get_model_run_params(model, mid)
  p_sim = get_model_run_params(model, mid)
  assert conditions_fingerprint(p_live) == conditions_fingerprint(p_sim)
  assert p_live.get("trade_model_id") == mid

  live, sim = _make_pair_engines(tmp_path, mt5_frame, mid)
  assert live.conditions_fp == sim.conditions_fp == conditions_fingerprint(p_live)
  assert live.bridge_dir != sim.bridge_dir
