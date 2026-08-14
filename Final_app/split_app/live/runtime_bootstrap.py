"""Bootstrap Final_app host desk imports + patch paths to Live results/bridge."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from live_config import BRIDGE_DIR, BRIDGE_SIM_DIR, LIVE_ROOT, RESULTS_DIR
from runtime_host import normalize_symbol, normalize_timeframe, resolve_host_desk
from shared.constants import LIVE_INSTANCE_ID, LIVE_MAGIC_BASE, LIVE_SIM_MAGIC_BASE

_BOOTSTRAPPED: dict[str, Any] = {}
_ENGINE_PATCHED = False
STATS_PATH = RESULTS_DIR / "replay_strategy_stats.json"


def _purge_host_modules() -> None:
  """Drop previously imported desk modules so a different host can load cleanly."""
  global _ENGINE_PATCHED
  drop_prefixes = (
    "mt5_bridge",
    "trade_model_kb_pin",
    "trade_model_schedule",
    "run_backtest",
    "optimizer",
    "strategy_miner",
    "knowledge_base",
    "kb_profiles",
    "config",
    "features",
    "feature_engine",
    "data_loader",
    "gui",
    "analytics",
  )
  # Keep live package modules (live_config, etc.) — only purge desk-side imports.
  keep = {"live_config", "books", "package_store", "materialize_models", "runtime_host"}
  for name in list(sys.modules):
    if name in keep or name.startswith("live_"):
      continue
    if name in drop_prefixes or any(name.startswith(p + ".") for p in drop_prefixes):
      del sys.modules[name]
  _ENGINE_PATCHED = False


def _force_remine_enabled() -> bool:
  return os.environ.get("LIVE_REPLAY_FORCE_REMINE", "").strip().lower() in (
    "1", "true", "yes", "on",
  )


def _bump_strategy_stat(model_id: str, source: str, week_start: Any) -> None:
  """Increment schedule/remine counters for Replay Results (best-effort)."""
  try:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = STATS_PATH.with_suffix(".lock")
    with open(lock_path, "a+", encoding="utf-8") as lockf:
      try:
        import fcntl
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
      except Exception:
        pass
      data: dict[str, Any]
      if STATS_PATH.exists():
        try:
          data = json.loads(STATS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
          data = {}
      else:
        data = {}
      by = dict(data.get("by_model") or {})
      row = dict(by.get(str(model_id)) or {"schedule_hits": 0, "remine_count": 0, "skip_count": 0})
      key = {
        "schedule": "schedule_hits",
        "remine": "remine_count",
        "none": "skip_count",
      }.get(source, "skip_count")
      row[key] = int(row.get(key) or 0) + 1
      by[str(model_id)] = row
      data["by_model"] = by
      data["schedule_hits"] = sum(int(v.get("schedule_hits") or 0) for v in by.values())
      data["remine_count"] = sum(int(v.get("remine_count") or 0) for v in by.values())
      data["skip_count"] = sum(int(v.get("skip_count") or 0) for v in by.values())
      data["updated_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
      events = list(data.get("events") or [])
      ws = week_start
      try:
        ws = str(week_start.date())
      except Exception:
        ws = str(week_start)
      events.append({
        "at": data["updated_at"],
        "model_id": str(model_id),
        "source": source,
        "week_start": ws,
      })
      data["events"] = events[-200:]
      tmp = STATS_PATH.with_suffix(".json.tmp")
      tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
      tmp.replace(STATS_PATH)
      try:
        import fcntl
        fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
      except Exception:
        pass
  except Exception:
    pass


def _patch_schedule_and_engine(sched: Any, engine: Any) -> None:
  """Force-remine env + remine quality gate + strategy_source on decisions."""
  global _ENGINE_PATCHED
  if _ENGINE_PATCHED:
    return

  orig_lookup = sched.lookup_week_strategy

  def lookup_week_strategy(model_id, week_start):  # noqa: ANN001
    if _force_remine_enabled():
      return None
    return orig_lookup(model_id, week_start)

  sched.lookup_week_strategy = lookup_week_strategy

  BridgeEngine = engine.BridgeEngine
  orig_remine = BridgeEngine._remine_week_strategy
  orig_decide = BridgeEngine.decide_for_bar

  def _remine_week_strategy(self, *args, **kwargs):  # noqa: ANN001
    week_start = kwargs.get("week_start")
    if week_start is None and args:
      week_start = args[0]
    cache_key = kwargs.get("cache_key")
    train_weeks = int(kwargs.get("train_weeks") or 6)
    feature_profile = str(kwargs.get("feature_profile") or "current")
    already_cached = bool(cache_key) and cache_key in getattr(self, "_strat_cache", {})
    force = _force_remine_enabled()
    had_frozen = False
    if not force and week_start is not None:
      try:
        entry = orig_lookup(self.model_id, week_start)
        had_frozen = bool(entry and isinstance(entry.get("strategy"), dict))
      except Exception:
        had_frozen = False

    strat = orig_remine(self, *args, **kwargs)

    if already_cached:
      src = getattr(self, "_last_strategy_source", None) or (
        "schedule" if had_frozen and not force else "remine"
      )
      self._last_strategy_source = src
      return strat

    if strat is None:
      self._last_strategy_source = "none"
      _bump_strategy_stat(self.model_id, "none", week_start)
      return None

    # Frozen genome (package schedule or prior live_weeks) — no gate
    if had_frozen and not force:
      self._last_strategy_source = "schedule"
      _bump_strategy_stat(self.model_id, "schedule", week_start)
      return strat

    # Fresh remine — quality gate before allowing Live/Replay to trade it
    self._last_strategy_source = "remine"
    try:
      from remine_gate import (
        gate_enabled,
        gate_remine_strategy,
        remove_live_week_entry,
      )
      if gate_enabled():
        from data_loader import get_train_window_indices
        df_mine = self.load()
        ts, te = get_train_window_indices(df_mine, week_start, train_weeks)
        if ts is None:
          raise RuntimeError("remine_gate: missing train window")
        fm = self._feature_matrix(df_mine, feature_profile)
        params = self._params or {}
        result = gate_remine_strategy(
          model_id=str(self.model_id),
          week_start=week_start,
          fm=fm,
          strat=strat,
          train_start_idx=int(ts),
          train_end_idx=int(te),
          spread_pips=float(params.get("spread_pips") or 1.0),
          slippage_pips=float(params.get("slippage_pips") or 0.3),
        )
        self._last_remine_gate = result
        if not result.get("ok"):
          if cache_key:
            self._strat_cache.pop(cache_key, None)
          remove_live_week_entry(self.model_id, week_start)
          self._last_strategy_source = "remine_gate_fail"
          self._last_flat_reason = "remine_gate_fail"
          _bump_strategy_stat(self.model_id, "none", week_start)
          return None
    except Exception as exc:
      # Fail closed: do not trade unvalidated remine if gate itself errors
      print(f"[remine_gate] error (fail-closed): {exc}", flush=True)
      if cache_key:
        self._strat_cache.pop(cache_key, None)
      try:
        from remine_gate import remove_live_week_entry
        remove_live_week_entry(self.model_id, week_start)
      except Exception:
        pass
      self._last_strategy_source = "remine_gate_fail"
      self._last_flat_reason = "remine_gate_error"
      self._last_remine_gate = {"ok": False, "reasons": [str(exc)]}
      _bump_strategy_stat(self.model_id, "none", week_start)
      return None

    _bump_strategy_stat(self.model_id, "remine", week_start)
    return strat

  def decide_for_bar(self, bar):  # noqa: ANN001
    decision = orig_decide(self, bar)
    if isinstance(decision, dict):
      src = getattr(self, "_last_strategy_source", None)
      if src:
        decision["strategy_source"] = src
      gate = getattr(self, "_last_remine_gate", None)
      if isinstance(gate, dict) and gate:
        decision["remine_gate_ok"] = gate.get("ok")
        if gate.get("reasons"):
          decision["remine_gate_reasons"] = gate.get("reasons")
        if gate.get("metrics"):
          decision["remine_gate_metrics"] = gate.get("metrics")
      flat_reason = getattr(self, "_last_flat_reason", None)
      if (
        src in ("remine_gate_fail",)
        and str(decision.get("action") or "").upper() == "FLAT"
        and flat_reason
      ):
        decision["reason"] = flat_reason
      # Concurrent portfolio risk cap (all books)
      try:
        from risk_cap import apply_risk_cap_to_decision
        bdir = getattr(self, "bridge_dir", None)
        sim = bool(bdir and "bridge_sim" in str(bdir))
        risk = float(getattr(self, "risk_pct", None) or decision.get("risk_pct") or 1.0)
        decision.setdefault("risk_pct", risk)
        decision.setdefault("model_id", getattr(self, "model_id", None))
        decision = apply_risk_cap_to_decision(decision, sim=sim, risk_pct=risk)
      except Exception as exc:
        print(f"[risk_cap] error (fail-closed): {exc}", flush=True)
        if str(decision.get("action") or "").upper() in ("BUY", "SELL"):
          decision = dict(decision)
          decision["action"] = "FLAT"
          decision["reason"] = "risk_cap_error"
          decision["risk_cap_ok"] = False
          decision["risk_cap_reasons"] = [str(exc)]
    return decision

  BridgeEngine._remine_week_strategy = _remine_week_strategy
  BridgeEngine.decide_for_bar = decide_for_bar
  if hasattr(engine, "lookup_week_strategy"):
    engine.lookup_week_strategy = lookup_week_strategy

  _ENGINE_PATCHED = True


def bootstrap_host(symbol: str, timeframe: str, *, force: bool = False) -> Path:
  """Insert host desk on sys.path and redirect REPORT/BRIDGE/MAGIC to Live."""
  symbol = normalize_symbol(symbol)
  timeframe = normalize_timeframe(timeframe)
  key = f"{symbol}|{timeframe}"
  if not force and _BOOTSTRAPPED.get("key") == key:
    return Path(_BOOTSTRAPPED["desk"])

  desk = resolve_host_desk(symbol, timeframe)
  if _BOOTSTRAPPED.get("key") and _BOOTSTRAPPED.get("key") != key:
    _purge_host_modules()

  live_str = str(LIVE_ROOT)
  split_str = str(LIVE_ROOT.parent)
  desk_str = str(desk)
  for p in (desk_str, split_str, live_str):
    if p in sys.path:
      sys.path.remove(p)
  sys.path.insert(0, split_str)
  sys.path.insert(0, desk_str)

  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  (RESULTS_DIR / "trade_models").mkdir(parents=True, exist_ok=True)
  data_dir = RESULTS_DIR / "data"
  data_dir.mkdir(parents=True, exist_ok=True)

  import run_backtest  # noqa: WPS433

  run_backtest.REPORT_DIR = RESULTS_DIR

  import trade_model_kb_pin as kb_pin  # noqa: WPS433

  kb_pin.REPORT_DIR = RESULTS_DIR
  kb_pin.MODELS_DIR = RESULTS_DIR / "trade_models"

  import trade_model_schedule as sched  # noqa: WPS433

  sched.REPORT_DIR = RESULTS_DIR
  sched.MODELS_DIR = RESULTS_DIR / "trade_models"

  import mt5_bridge.models as models  # noqa: WPS433

  models.MODELS_PATH = RESULTS_DIR / "trade_models.json"
  models.ACTIVE_MODEL_PATH = RESULTS_DIR / "active_trade_model.json"

  import mt5_bridge.protocol as protocol  # noqa: WPS433

  protocol.ROOT = LIVE_ROOT
  protocol.BRIDGE_DIR = BRIDGE_DIR
  protocol.BRIDGE_SIM_DIR = BRIDGE_SIM_DIR
  protocol.CONFIG_PATH = RESULTS_DIR / "mt5_bridge_config.json"
  protocol.DEFAULT_MAGIC = int(LIVE_MAGIC_BASE)
  protocol.DEFAULT_SIM_MAGIC = int(LIVE_SIM_MAGIC_BASE)
  protocol.DEFAULT_TIMEFRAME = timeframe
  protocol.INSTANCE_ID = LIVE_INSTANCE_ID

  import mt5_bridge.history_sync as history_sync  # noqa: WPS433

  cache_path = data_dir / f"mt5_{symbol.lower()}_{timeframe.lower()}.parquet"
  history_sync.ROOT = LIVE_ROOT
  history_sync.DATA_DIR = data_dir
  history_sync.MT5_CACHE_PATH = cache_path
  history_sync.MT5_META_PATH = data_dir / f"mt5_{symbol.lower()}_{timeframe.lower()}_meta.json"
  history_sync.DATA_START_CONFIG_PATH = data_dir / "data_start.json"
  history_sync.BRIDGE_DIR = BRIDGE_DIR

  import mt5_bridge.engine as engine  # noqa: WPS433

  engine.MT5_CACHE_PATH = cache_path
  engine.MT5_CACHE = cache_path

  import mt5_bridge.background as background  # noqa: WPS433

  background.ROOT = LIVE_ROOT
  background.CONFIG_PATH = RESULTS_DIR / "mt5_bridge_config.json"
  background.PID_PATH = RESULTS_DIR / "mt5_bridge_service.pid"
  background.SERVICE_LOG = RESULTS_DIR / "mt5_bridge_service.log"
  background.SERVICE_SCRIPT = LIVE_ROOT / "scripts" / "mt5_bridge_service_live.py"
  background.BRIDGE_DIR = BRIDGE_DIR
  background.MT5_CACHE_PATH = cache_path

  _patch_schedule_and_engine(sched, engine)

  _BOOTSTRAPPED.clear()
  _BOOTSTRAPPED.update({"key": key, "desk": str(desk), "symbol": symbol, "timeframe": timeframe})
  return desk


def bootstrap_info() -> dict[str, Any]:
  return dict(_BOOTSTRAPPED)
