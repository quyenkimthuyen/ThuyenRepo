"""Bridge decision engine — merge MT5 bars + Best 3m weekly remine."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd

from config import DEFAULT_RISK_PCT_PER_TRADE, MIN_TRAIN_BARS, TRAIN_MONTHS
from data_loader import get_train_window_indices, get_week_indices
from feature_engine import FeatureMatrix
from mt5_bridge.history_sync import (
  MT5_CACHE_PATH,
  merge_history_bars,
  parse_broker_time,
  start_history_sync,
  utc_to_broker_time,
)
from mt5_bridge.models import get_model_run_params, resolve_model
from mt5_bridge.protocol import DEFAULT_MAGIC, DEFAULT_MODEL_ID, utc_now_iso
from optimizer import get_knowledge_base, optimize_on_window, set_kb_profile
from paper_monitor import _current_week_bounds, _project_signal_levels
from strategy_miner import backtest_mined, ensure_label_cache_for_df, generate_signals_mined

MT5_CACHE = MT5_CACHE_PATH


class BridgeEngine:
  """Stateful engine: append broker bars, remine once per week, emit decisions."""

  def __init__(
    self,
    *,
    model_id: str = DEFAULT_MODEL_ID,
    risk_pct: float = DEFAULT_RISK_PCT_PER_TRADE,
    magic: int = DEFAULT_MAGIC,
    mt5_cache: Path | None = None,
  ):
    self.model_id = model_id
    self.risk_pct = float(risk_pct)
    self.magic = int(magic)
    self.mt5_cache = mt5_cache or MT5_CACHE
    self._df: pd.DataFrame | None = None
    self._strat_cache: dict[str, Any] = {}
    self._last_bar_key: str | None = None
    self._last_decision: dict | None = None
    self._model = resolve_model(model_id)
    self._params = get_model_run_params(self._model, model_id)

  @property
  def params(self) -> dict:
    return self._params

  def ensure_history(self, force: bool = False) -> pd.DataFrame:
    """Load canonical broker history and request EA synchronization when needed."""
    if force:
      start_history_sync(force=True)
    if self.mt5_cache.exists():
      df = pd.read_parquet(self.mt5_cache)
      self._df = _normalize(df)
      return self._df
    start_history_sync()
    raise RuntimeError("MT5 history is not ready")

  def load(self) -> pd.DataFrame:
    if self._df is not None:
      return self._df
    if self.mt5_cache.exists():
      self._df = _normalize(pd.read_parquet(self.mt5_cache))
      return self._df
    return self.ensure_history()

  def _save_mt5_cache(self) -> None:
    if self._df is None or self._df.empty:
      return
    self.mt5_cache.parent.mkdir(parents=True, exist_ok=True)
    self._df.to_parquet(self.mt5_cache)

  def merge_bar(self, bar: dict) -> pd.Timestamp:
    """Append/overwrite one H1 bar from EA. Returns bar timestamp."""
    if self.mt5_cache.resolve() == MT5_CACHE_PATH.resolve():
      self._df = merge_history_bars([bar], {
        "server": bar.get("server"),
        "account": bar.get("account"),
        "symbol": bar.get("symbol"),
      })
      return _parse_bar_time(bar)
    df = self.load()
    ts = _parse_bar_time(bar)
    row = pd.DataFrame(
      {
        "Open": [float(bar["open"])],
        "High": [float(bar["high"])],
        "Low": [float(bar["low"])],
        "Close": [float(bar["close"])],
        "Volume": [float(bar.get("volume") or bar.get("tick_volume") or 0)],
      },
      index=[ts],
    )
    if ts in df.index:
      df.loc[ts] = row.iloc[0]
    else:
      df = pd.concat([df, row]).sort_index()
      df = df[~df.index.duplicated(keep="last")]
    self._df = df
    self._save_mt5_cache()
    return ts

  def decide_for_bar(self, bar: dict) -> dict:
    """Produce decision.json payload for the closed H1 bar from EA."""
    bar_ts = self.merge_bar(bar)
    bar_key = bar_ts.isoformat(sep=" ")
    if bar_key == self._last_bar_key and self._last_decision is not None:
      return self._last_decision

    params = self._params
    train_months = int(params.get("train_months") or TRAIN_MONTHS)
    use_learning = bool(params.get("use_learning", True))
    kb_profile = params.get("kb_profile")
    kb_snapshot = params.get("kb_snapshot")
    spread = float(params.get("spread_pips", 1.0))
    slip = float(params.get("slippage_pips", 0.3))
    model_id = params.get("trade_model_id") or self.model_id
    if not self._model or self._model.get("data_source") != "mt5_ea":
      decision = self._flat(
        bar_ts, model_id, reason="legacy_data_source_blocked",
      )
      return self._remember(bar_key, decision)

    df = self.load()
    ensure_label_cache_for_df(len(df))
    fm = FeatureMatrix(df)
    week_start, week_end = _current_week_bounds(df)

    cache_key = (
      f"{week_start.date()}|{model_id}|{kb_profile}@{kb_snapshot}|{train_months}"
    )
    strat = self._strat_cache.get(cache_key)
    if strat is None:
      kb = None
      if use_learning:
        if kb_profile:
          set_kb_profile(kb_profile, kb_snapshot)
        kb = get_knowledge_base(kb_profile, kb_snapshot)
      ts, te = get_train_window_indices(df, week_start, train_months)
      if ts is None or (te - ts) < MIN_TRAIN_BARS:
        decision = self._flat(
          bar_ts, model_id, reason="insufficient_train_data", week_start=week_start,
        )
        return self._remember(bar_key, decision)
      strat = optimize_on_window(
        fm, ts, te, use_learning=use_learning, as_of=week_start, kb=kb,
      )
      if strat is None:
        decision = self._flat(
          bar_ts, model_id, reason="no_strategy", week_start=week_start,
        )
        return self._remember(bar_key, decision)
      self._strat_cache[cache_key] = strat

    oos_s, oos_e = get_week_indices(df, week_start, week_end)
    if oos_s is None:
      decision = self._flat(
        bar_ts, model_id, reason="no_oos_week", week_start=week_start,
      )
      return self._remember(bar_key, decision)

    signals = generate_signals_mined(fm, strat, oos_s, oos_e)
    week_trades, open_position = backtest_mined(
      fm, strat, signals, oos_s, oos_e,
      spread_pips=spread, slippage_pips=slip, return_open=True,
    )

    # Decision keyed to closed bar (= signal bar). Entry is next open (handled by EA).
    if bar_ts not in fm.index:
      decision = self._flat(
        bar_ts, model_id, reason="bar_not_in_series", week_start=week_start,
      )
      return self._remember(bar_key, decision)

    bar_idx = int(fm.index.get_loc(bar_ts))
    if isinstance(bar_idx, slice):
      bar_idx = bar_idx.start

    direction = int(signals[bar_idx]) if 0 <= bar_idx < len(signals) else 0
    slots_left = max(int(strat.max_trades_per_week) - len(week_trades), 0)
    if open_position:
      decision = self._hold(
        bar_ts, model_id, reason="position_open", week_start=week_start, strat=strat,
      )
      return self._remember(bar_key, decision)

    if direction == 0 or slots_left <= 0:
      decision = self._flat(
        bar_ts, model_id,
        reason="no_signal" if direction == 0 else "no_slots",
        week_start=week_start, strat=strat, slots_remaining=slots_left,
      )
      return self._remember(bar_key, decision)

    proj = _project_signal_levels(fm, strat, bar_idx, direction, spread, slip)
    if not proj:
      decision = self._flat(
        bar_ts, model_id, reason="cannot_project_levels", week_start=week_start, strat=strat,
      )
      return self._remember(bar_key, decision)

    action = "BUY" if direction == 1 else "SELL"
    sig_id = _signal_id(model_id, bar_ts, action)
    expires = bar_ts + pd.Timedelta(hours=2)
    decision = {
      "signal_id": sig_id,
      "action": action,
      "entry": proj["entry_px"],
      "sl": proj["sl"],
      "tp": proj["tp"],
      "risk_pct": self.risk_pct,
      "magic": self.magic,
      "bar_time": _fmt_bar(bar_ts),
      "entry_time": proj["entry_time"],
      "model_id": model_id,
      "expires_bar_time": _fmt_bar(expires),
      "atr_mult_sl": float(strat.atr_mult_sl),
      "rr": float(strat.rr_ratio),
      "exit_mode": strat.exit_mode,
      "trail_activate_r": float(strat.trail_activate_r),
      "trail_distance_r": float(strat.trail_distance_r),
      "max_hold_bars": int(strat.max_hold_bars),
      "slots_remaining": slots_left - 1,
      "week_start": str(week_start.date()),
      "strategy_name": strat.name,
      "updated_at": utc_now_iso(),
      "reason": "signal",
    }
    return self._remember(bar_key, decision)

  def _remember(self, bar_key: str, decision: dict) -> dict:
    self._last_bar_key = bar_key
    self._last_decision = decision
    return decision

  def _flat(
    self, bar_ts: pd.Timestamp, model_id: str, *, reason: str,
    week_start: pd.Timestamp | None = None, strat=None, slots_remaining: int | None = None,
  ) -> dict:
    return {
      "signal_id": _signal_id(model_id, bar_ts, "FLAT"),
      "action": "FLAT",
      "entry": None,
      "sl": None,
      "tp": None,
      "risk_pct": self.risk_pct,
      "magic": self.magic,
      "bar_time": _fmt_bar(bar_ts),
      "model_id": model_id,
      "expires_bar_time": _fmt_bar(bar_ts + pd.Timedelta(hours=2)),
      "week_start": str(week_start.date()) if week_start is not None else None,
      "strategy_name": getattr(strat, "name", None),
      "slots_remaining": slots_remaining,
      "updated_at": utc_now_iso(),
      "reason": reason,
    }

  def _hold(
    self, bar_ts: pd.Timestamp, model_id: str, *, reason: str,
    week_start: pd.Timestamp | None = None, strat=None,
  ) -> dict:
    d = self._flat(bar_ts, model_id, reason=reason, week_start=week_start, strat=strat)
    d["action"] = "HOLD"
    return d


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
  rename = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
  out = df.rename(columns={c: rename.get(c.lower(), c) for c in df.columns})
  need = ["Open", "High", "Low", "Close"]
  for c in need:
    if c not in out.columns:
      raise ValueError(f"OHLC missing column {c}")
  if "Volume" not in out.columns:
    out["Volume"] = 0.0
  out = out[["Open", "High", "Low", "Close", "Volume"]].copy()
  out.index = pd.to_datetime(out.index, utc=True).tz_convert(None)
  out = out.sort_index()
  return out[~out.index.duplicated(keep="last")].dropna()


def _parse_bar_time(bar: dict) -> pd.Timestamp:
  if bar.get("time"):
    return parse_broker_time(bar["time"])
  if bar.get("bar_time"):
    return parse_broker_time(bar["bar_time"])
  if bar.get("time_msc"):
    return pd.Timestamp(int(bar["time_msc"]), unit="ms")
  raise ValueError("bar missing time / time_msc")


def _fmt_bar(ts: pd.Timestamp) -> str:
  t = utc_to_broker_time(ts)
  return t.strftime("%Y.%m.%d %H:%M")


def _signal_id(model_id: str, bar_ts: pd.Timestamp, action: str) -> str:
  raw = f"{model_id}|{_fmt_bar(bar_ts)}|{action}"
  return hashlib.sha1(raw.encode()).hexdigest()[:16]
