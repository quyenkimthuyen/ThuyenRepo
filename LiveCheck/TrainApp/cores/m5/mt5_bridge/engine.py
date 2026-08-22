"""Bridge decision engine — merge MT5 M15 bars + weekly remine."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd

from config import BAR_MINUTES, DEFAULT_RISK_PCT_PER_TRADE, MIN_TRAIN_BARS, TRAIN_WEEKS, DEFAULT_FEATURE_PROFILE
from data_loader import get_train_window_indices, get_week_indices
from feature_engine import FeatureMatrix
from mt5_bridge.history_sync import (
  MT5_CACHE_PATH,
  merge_history_bars,
  parse_broker_time,
  start_history_sync,
  utc_to_broker_time,
)
from mt5_bridge.models import (
  conditions_fingerprint,
  describe_strategy_conditions,
  get_model_run_params,
  resolve_model,
  strategy_conditions,
)
from mt5_bridge.protocol import DEFAULT_MAGIC, DEFAULT_MODEL_ID, utc_now_iso
from mt5_bridge.trade_journal import load_trades
from optimizer import get_knowledge_base, optimize_on_window, set_kb_profile
from paper_monitor import _project_signal_levels, _week_bounds_for_ts
from strategy_miner import (
  backtest_mined, ensure_label_cache_for_df, generate_signals_mined,
  mining_search_space_from_dict,
)
from trade_model_schedule import (
  append_live_week,
  attach_ml_scorer,
  lookup_week_strategy,
  strategy_from_dict,
  week_entry_from_strategy,
)

MT5_CACHE = MT5_CACHE_PATH


def _journal_open_and_day_count(
  bridge_dir: Path,
  broker_day,
  *,
  model_id: str | None = None,
) -> tuple[bool, int]:
  """Real EA/paper fills — source of truth for open + day slots (not theoretical backtest).

  When ``model_id`` is set, only that model's journal rows count (Compare Trade
  isolation; single-model dirs already scope by path).

  Strategy fills still count after ``user_sl_tp`` / trail retag them as
  ``mode=manual`` — otherwise max_trades_per_day is skipped.
  """
  has_open = False
  day_n = 0
  mid = str(model_id) if model_id else None
  for trade in load_trades(bridge_dir):
    if not _is_strategy_journal_fill(trade):
      continue
    if mid and str(trade.get("model_id") or "") != mid:
      continue
    status = str(trade.get("status") or "").upper()
    if status == "OPEN":
      has_open = True
    if status not in ("OPEN", "CLOSED"):
      continue
    entry_raw = trade.get("entry_time") or trade.get("bar_time") or trade.get("updated_at")
    if not entry_raw:
      continue
    try:
      raw = str(entry_raw).strip().replace(".", "-")
      # broker wall "2026-01-02 08:15" or ISO
      if "T" in raw:
        et = utc_to_broker_time(pd.Timestamp(raw))
      else:
        et = utc_to_broker_time(parse_broker_time(raw[:16]))
      if et.date() == broker_day:
        day_n += 1
    except Exception:
      continue
  return has_open, day_n


_MANUAL_FILL_ORIGINS = frozenset({
  "manual_test", "manual", "user", "manual_bridge", "manual_close",
})
_MANUAL_SIGNAL_PREFIXES = ("manual_test", "manual_close", "manual_bridge")


def _is_strategy_journal_fill(trade: dict) -> bool:
  """True for strategy opens even if later tagged manual (user_sl_tp)."""
  sid = str(trade.get("signal_id") or "")
  if any(sid.startswith(p) for p in _MANUAL_SIGNAL_PREFIXES):
    return False
  origin = str(trade.get("origin") or "strategy").lower()
  return origin not in _MANUAL_FILL_ORIGINS


def _journal_fill_bar_utc(trade: dict) -> pd.Timestamp | None:
  """Signal/entry bar as UTC-naive (same clock as fm.index). Prefer bar_time."""
  raw = trade.get("bar_time") or trade.get("entry_time")
  if not raw:
    return None
  try:
    text = str(raw).strip()
    if "T" in text:
      ts = pd.Timestamp(text)
      if ts.tzinfo is not None:
        return ts.tz_convert("UTC").tz_localize(None)
      return parse_broker_time(ts)
    if len(text) >= 16 and text[4] == ".":
      text = text.replace(".", "-", 2)
    return parse_broker_time(text[:16] if len(text) >= 16 else text)
  except Exception:
    return None


def _bar_gap(fm, bar_idx: int, bar_ts: pd.Timestamp, prior_utc: pd.Timestamp) -> int:
  """Integer bar gap: FM index when possible, else wall-clock / BAR_MINUTES."""
  index = getattr(fm, "index", None) if fm is not None else None
  if index is not None:
    try:
      loc = index.get_loc(prior_utc)
      if isinstance(loc, slice):
        loc = loc.start
      return abs(int(bar_idx) - int(loc))
    except (KeyError, TypeError, ValueError):
      try:
        indexer = index.get_indexer([prior_utc], method="nearest")
        loc = int(indexer[0]) if len(indexer) else -1
        if loc >= 0:
          nearest = index[loc]
          if abs((nearest - prior_utc).total_seconds()) <= float(BAR_MINUTES) * 60:
            return abs(int(bar_idx) - loc)
      except Exception:
        pass
    except Exception:
      pass
  minutes = abs((pd.Timestamp(bar_ts) - pd.Timestamp(prior_utc)).total_seconds()) / 60.0
  return int(round(minutes / float(BAR_MINUTES)))


def journal_violates_min_bars_between(
  bridge_dir: Path,
  broker_day,
  *,
  model_id: str | None,
  fm,
  bar_idx: int,
  bar_ts: pd.Timestamp,
  min_bars: int,
) -> bool:
  """True if a same-day strategy fill is closer than min_bars to the current bar.

  Miner spacing is per broker day, between signal bars. Live must use the journal
  because generate_signals_mined only sees the current resim set, not filled trades.
  """
  if int(min_bars) <= 0:
    return False
  mid = str(model_id) if model_id else None
  for trade in load_trades(bridge_dir):
    if not _is_strategy_journal_fill(trade):
      continue
    if mid and str(trade.get("model_id") or "") != mid:
      continue
    status = str(trade.get("status") or "").upper()
    if status not in ("OPEN", "CLOSED"):
      continue
    prior = _journal_fill_bar_utc(trade)
    if prior is None:
      continue
    try:
      if utc_to_broker_time(prior).date() != broker_day:
        continue
    except Exception:
      continue
    if _bar_gap(fm, bar_idx, bar_ts, prior) < int(min_bars):
      return True
  return False


class BridgeEngine:
  """Stateful engine: append broker bars, remine once per week, emit decisions."""

  def __init__(
    self,
    *,
    model_id: str = DEFAULT_MODEL_ID,
    risk_pct: float = DEFAULT_RISK_PCT_PER_TRADE,
    magic: int = DEFAULT_MAGIC,
    mt5_cache: Path | None = None,
    bridge_dir: Path | None = None,
  ):
    self.model_id = model_id
    self.risk_pct = float(risk_pct)
    self.magic = int(magic)
    self.mt5_cache = mt5_cache or MT5_CACHE
    self.bridge_dir = bridge_dir
    self._df: pd.DataFrame | None = None
    self._strat_cache: dict[str, Any] = {}
    self._fm: FeatureMatrix | None = None
    self._fm_key: tuple | None = None
    self._last_bar_key: str | None = None
    self._last_decision: dict | None = None
    self._model = resolve_model(model_id)
    self._params = get_model_run_params(self._model, model_id)

  @property
  def params(self) -> dict:
    return self._params

  @property
  def conditions_fp(self) -> str:
    return conditions_fingerprint(self._params)

  def describe_conditions(self) -> dict:
    return describe_strategy_conditions(self._params)

  def refresh_model(self) -> bool:
    """Re-read Trade Model from disk. Clear remine cache if conditions changed."""
    new_model = resolve_model(self.model_id)
    new_params = get_model_run_params(new_model, self.model_id)
    changed = conditions_fingerprint(new_params) != self.conditions_fp
    self._model = new_model
    self._params = new_params
    if changed:
      self._strat_cache.clear()
      self._fm = None
      self._fm_key = None
    return changed

  def _feature_matrix(self, df: pd.DataFrame, feature_profile: str) -> FeatureMatrix:
    """Build FeatureMatrix like OOS walk-forward (full series, cached).

    Do not clip lookback before features: ``htf_trend`` (H4 EMA200) and
    ``roc_5`` (global std) change under short windows and diverge from Health KB ON.
    """
    if df.empty:
      raise ValueError("empty history for FeatureMatrix")
    key = (
      feature_profile,
      len(df),
      str(df.index[0]),
      str(df.index[-1]),
    )
    if self._fm is None or self._fm_key != key:
      ensure_label_cache_for_df(len(df))
      self._fm = FeatureMatrix(df, profile=feature_profile)
      self._fm_key = key
    return self._fm

  def ensure_history(self, force: bool = False) -> pd.DataFrame:
    """Load canonical broker history and request EA synchronization when needed."""
    if force:
      start_history_sync(force=True)
    if self.mt5_cache.exists():
      df = pd.read_parquet(self.mt5_cache)
      self._df = _normalize(df)
      self._fm = None
      self._fm_key = None
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

  def _canonical_frame(self) -> pd.DataFrame:
    """Full parquet history for weekly remine (matches Health OOS / tip tests).

    HistoryFeed must not remine on a truncated in-memory tip — that locks a
    weaker strategy for the whole week in ``_strat_cache``.
    """
    if self.mt5_cache.exists():
      return _normalize(pd.read_parquet(self.mt5_cache))
    return self.load()

  def _sync_working_frame_from_canonical(self, canonical: pd.DataFrame) -> pd.DataFrame:
    """Prefer longer canonical series as working ``_df`` when safe."""
    if canonical is None or canonical.empty:
      return self.load()
    cur = self._df
    if cur is None or len(canonical) >= len(cur):
      if cur is None or len(canonical) != len(cur) or (
        len(canonical) and (
          canonical.index[0] != cur.index[0] or canonical.index[-1] != cur.index[-1]
        )
      ):
        self._df = canonical
        self._fm = None
        self._fm_key = None
    return self.load()

  def _remine_week_strategy(
    self,
    *,
    week_start: pd.Timestamp,
    cache_key: str,
    train_weeks: int,
    use_learning: bool,
    kb_profile,
    kb_snapshot,
    feature_profile: str,
    search_space,
  ):
    """Prefer frozen Trade Model schedule; remine only for unseen weeks."""
    cached = self._strat_cache.get(cache_key)
    if cached is not None:
      return cached

    canonical = self._canonical_frame()
    df_mine = self._sync_working_frame_from_canonical(canonical)
    fm_mine = self._feature_matrix(df_mine, feature_profile)

    kb = None
    if use_learning:
      from trade_model_kb_pin import load_kb_for_run
      pin = (self._params or {}).get("kb_pin_path")
      kb = load_kb_for_run(
        use_learning=True,
        kb_profile=kb_profile,
        kb_snapshot=kb_snapshot,
        kb_pin_path=pin,
      )
      if kb is None and kb_profile:
        set_kb_profile(kb_profile, kb_snapshot)
        kb = get_knowledge_base(kb_profile, kb_snapshot)

    # 1) Frozen OOS / previously live-frozen week — before train-window gate
    scheduled = lookup_week_strategy(self.model_id, week_start)
    if scheduled and isinstance(scheduled.get("strategy"), dict):
      strat = strategy_from_dict(scheduled["strategy"])
      ts_use = int(scheduled.get("train_start_idx", -1))
      te_use = int(scheduled.get("train_end_idx", -1))
      if ts_use < 0 or te_use <= ts_use or te_use > fm_mine.n:
        ts_fb, te_fb = get_train_window_indices(df_mine, week_start, train_weeks)
        if ts_fb is None or (te_fb - ts_fb) < MIN_TRAIN_BARS:
          return None
        ts_use, te_use = ts_fb, te_fb
      attach_ml_scorer(
        strat, fm_mine, ts_use, te_use, kb=kb, as_of=week_start,
        search_space=search_space,
      )
      self._strat_cache[cache_key] = strat
      name = getattr(strat, "name", None) or "?"
      print(
        f"[bridge] schedule week={week_start.date()} strategy={name} "
        f"fm_len={len(df_mine)} train_bars={te_use - ts_use} fp={self.conditions_fp}",
        flush=True,
      )
      return strat

    # 2) Unseen future week — remine once, then freeze into live_weeks
    ts, te = get_train_window_indices(df_mine, week_start, train_weeks)
    if ts is None or (te - ts) < MIN_TRAIN_BARS:
      return None

    strat = optimize_on_window(
      fm_mine, ts, te, use_learning=use_learning, as_of=week_start, kb=kb,
      search_space=search_space,
    )
    if strat is None:
      return None
    self._strat_cache[cache_key] = strat
    try:
      append_live_week(
        self.model_id,
        week_entry_from_strategy(
          week_start=week_start,
          strat=strat,
          train_start_idx=ts,
          train_end_idx=te,
        ),
      )
    except Exception as exc:
      print(f"[bridge] live_weeks append failed: {exc}", flush=True)
    try:
      name = getattr(strat, "name", None) or str(strat)
    except Exception:
      name = "?"
    print(
      f"[bridge] remine week={week_start.date()} strategy={name} "
      f"fm_len={len(df_mine)} train_bars={te - ts} fp={self.conditions_fp}",
      flush=True,
    )
    return strat

  def _save_mt5_cache(self) -> None:
    if self._df is None or self._df.empty:
      return
    self.mt5_cache.parent.mkdir(parents=True, exist_ok=True)
    self._df.to_parquet(self.mt5_cache)

  def merge_bar(self, bar: dict) -> pd.Timestamp:
    """Ensure bar is in the in-memory series. Avoid rewriting parquet on HistoryFeed replay.

    HistoryFeed re-sends bars already in ``mt5_eurusd_m5.parquet``. Rewriting the
    full cache (+ invalidating FeatureMatrix) every bar pegs disk/CPU and freezes the GUI.
    """
    ts = _parse_bar_time(bar)
    df = self.load()
    if ts in df.index:
      return ts

    row = {
      "Open": float(bar["open"]),
      "High": float(bar["high"]),
      "Low": float(bar["low"]),
      "Close": float(bar["close"]),
      "Volume": float(bar.get("volume") or bar.get("tick_volume") or 0),
    }
    if self.mt5_cache.resolve() == MT5_CACHE_PATH.resolve():
      self._df = merge_history_bars([bar], {
        "server": bar.get("server"),
        "account": bar.get("account"),
        "symbol": bar.get("symbol"),
      })
    else:
      add = pd.DataFrame([row], index=[ts])
      df = pd.concat([df, add]).sort_index()
      df = df[~df.index.duplicated(keep="last")]
      self._df = df
      self._save_mt5_cache()
    # New tip only — remine/features must refresh
    self._fm = None
    self._fm_key = None
    return ts

  def prewarm_week(self, bar_ts: pd.Timestamp) -> None:
    """Load/remine strategy for ``bar_ts`` week before HistoryFeed asks for decisions."""
    params = self._params or {}
    train_weeks = int(params.get("train_weeks") or TRAIN_WEEKS)
    use_learning = bool(params.get("use_learning", True))
    kb_profile = params.get("kb_profile")
    kb_snapshot = params.get("kb_snapshot")
    feature_profile = params.get("feature_profile") or DEFAULT_FEATURE_PROFILE
    search_payload = params.get("mining_search_space")
    search_space = (
      mining_search_space_from_dict(search_payload) if search_payload else None
    )
    week_start, _week_end = _week_bounds_for_ts(bar_ts)
    model_id = params.get("trade_model_id") or self.model_id
    cache_key = (
      f"{week_start.date()}|{model_id}|{kb_profile}@{kb_snapshot}|{train_weeks}w|"
      f"{feature_profile}|{search_space!r}"
    )
    self._remine_week_strategy(
      week_start=week_start,
      cache_key=cache_key,
      train_weeks=train_weeks,
      use_learning=use_learning,
      kb_profile=kb_profile,
      kb_snapshot=kb_snapshot,
      feature_profile=feature_profile,
      search_space=search_space,
    )

  def decide_for_bar(self, bar: dict) -> dict:
    """Produce decision.json for the closed M15 bar (Live + HistoryFeed + OOS-parity).

    Live and Simulate share this path: same Trade Model conditions, KB snapshot,
    full-history FeatureMatrix, and weekly ``optimize_on_window`` as Health OOS.
    Only execution differs (real fills vs paper HistoryFeed).
    """
    bar_ts = self.merge_bar(bar)
    bar_key = bar_ts.isoformat(sep=" ")
    if bar_key == self._last_bar_key and self._last_decision is not None:
      return self._last_decision

    params = self._params
    train_weeks = int(params.get("train_weeks") or TRAIN_WEEKS)
    use_learning = bool(params.get("use_learning", True))
    kb_profile = params.get("kb_profile")
    kb_snapshot = params.get("kb_snapshot")
    spread = float(params.get("spread_pips", 1.0))
    slip = float(params.get("slippage_pips", 0.3))
    model_id = params.get("trade_model_id") or self.model_id
    if (
      not self._model
      or self._model.get("data_source") != "mt5_ea"
      or self._model.get("data_timeframe") != "M5"
      or int(self._model.get("feature_schema") or 0) < 2
    ):
      decision = self._flat(
        bar_ts, model_id, reason="legacy_data_source_blocked",
      )
      return self._remember(bar_key, decision)

    df = self.load()
    if df.empty or bar_ts not in df.index:
      # Heal: bar may exist only on canonical cache while working series truncated
      try:
        canonical = self._canonical_frame()
        if bar_ts in canonical.index:
          df = self._sync_working_frame_from_canonical(canonical)
      except Exception:
        pass
    if df.empty or bar_ts not in df.index:
      decision = self._flat(
        bar_ts, model_id, reason="bar_not_in_series",
      )
      return self._remember(bar_key, decision)

    week_start, week_end = _week_bounds_for_ts(bar_ts)

    feature_profile = params.get("feature_profile") or DEFAULT_FEATURE_PROFILE
    search_payload = params.get("mining_search_space")
    search_space = (
      mining_search_space_from_dict(search_payload) if search_payload else None
    )
    cache_key = (
      f"{week_start.date()}|{model_id}|{kb_profile}@{kb_snapshot}|{train_weeks}w|"
      f"{feature_profile}|{search_space!r}"
    )
    # Eager remine on first decision of the week (FLAT or SIGNAL) using full-history FM
    strat = self._remine_week_strategy(
      week_start=week_start,
      cache_key=cache_key,
      train_weeks=train_weeks,
      use_learning=use_learning,
      kb_profile=kb_profile,
      kb_snapshot=kb_snapshot,
      feature_profile=feature_profile,
      search_space=search_space,
    )
    if strat is None:
      # Distinguish train vs mine failure
      df_chk = self.load()
      ts, te = get_train_window_indices(df_chk, week_start, train_weeks)
      reason = (
        "insufficient_train_data"
        if ts is None or (te - ts) < MIN_TRAIN_BARS
        else "no_strategy"
      )
      decision = self._flat(
        bar_ts, model_id, reason=reason, week_start=week_start,
      )
      return self._remember(bar_key, decision)

    # Signal scan FM: working series (synced to canonical when remine ran)
    df = self.load()
    fm = self._feature_matrix(df, feature_profile)

    # Cached weekly strat keeps ML probs sized to the fm at mine-time.
    # Live bars append mid-week → refresh probs before scanning signals.
    ml = getattr(strat, "ml_scorer", None)
    if ml is not None and hasattr(ml, "refresh_for_fm"):
      ml.refresh_for_fm(fm)

    oos_s, oos_e = get_week_indices(df, week_start, week_end)
    if oos_s is None:
      decision = self._flat(
        bar_ts, model_id, reason="no_oos_week", week_start=week_start,
      )
      return self._remember(bar_key, decision)

    signals = generate_signals_mined(
      fm, strat, oos_s, oos_e, include_last_bar=True,
    )
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
    broker_day = utc_to_broker_time(bar_ts).date()
    if self.bridge_dir is not None:
      # Journal = EA/paper truth. Do not block on theoretical backtest open
      # (HistoryFeed timeout miss would otherwise freeze the whole week).
      real_open, day_n = _journal_open_and_day_count(
        self.bridge_dir, broker_day, model_id=model_id,
      )
      slots_left = max(int(strat.max_trades_per_day) - day_n, 0)
      if real_open:
        decision = self._hold(
          bar_ts, model_id, reason="position_open", week_start=week_start, strat=strat,
        )
        return self._remember(bar_key, decision)
    else:
      day_trades = [
        trade for trade in week_trades
        if utc_to_broker_time(trade.entry_time).date() == broker_day
      ]
      slots_left = max(int(strat.max_trades_per_day) - len(day_trades), 0)
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

    min_gap = int(getattr(strat, "min_bars_between", 0) or 0)
    if self.bridge_dir is not None and min_gap > 0:
      if journal_violates_min_bars_between(
        self.bridge_dir, broker_day,
        model_id=model_id, fm=fm, bar_idx=bar_idx, bar_ts=bar_ts, min_bars=min_gap,
      ):
        decision = self._flat(
          bar_ts, model_id, reason="min_bars_between",
          week_start=week_start, strat=strat, slots_remaining=slots_left,
        )
        return self._remember(bar_key, decision)

    proj = _project_signal_levels(fm, strat, bar_idx, direction, spread, slip)
    if not proj:
      decision = self._flat(
        bar_ts, model_id, reason="levels_unavailable", week_start=week_start, strat=strat,
        slots_remaining=slots_left,
      )
      return self._remember(bar_key, decision)

    action = "BUY" if direction == 1 else "SELL"
    sig_id = _signal_id(model_id, bar_ts, action)
    expires = bar_ts + pd.Timedelta(minutes=5)
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
      "conditions_fp": self.conditions_fp,
      "run_conditions": strategy_conditions(self._params),
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
      "expires_bar_time": _fmt_bar(bar_ts + pd.Timedelta(minutes=5)),
      "week_start": str(week_start.date()) if week_start is not None else None,
      "strategy_name": getattr(strat, "name", None),
      "slots_remaining": slots_remaining,
      "updated_at": utc_now_iso(),
      "reason": reason,
      "conditions_fp": self.conditions_fp,
      "run_conditions": strategy_conditions(self._params),
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
