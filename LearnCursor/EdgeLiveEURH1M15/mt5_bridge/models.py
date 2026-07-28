"""Headless trade-model loaders (no Streamlit).

Canonical source for Bridge + Health/backtest run conditions
(train weeks/months, KB, feature profile, mining search space, spread/slip).
MODELS_PATH / ACTIVE_MODEL_PATH resolve under the *active* TF's results dir
(``tf_context.REPORT_DIR`` is a dynamic proxy — see tf_context.py).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS, get_active_tf
from run_backtest import REPORT_DIR
from runtime_profiles import get_tf_defaults

MODELS_PATH = REPORT_DIR / "trade_models.json"
ACTIVE_MODEL_PATH = REPORT_DIR / "active_trade_model.json"
DEFAULT_MODEL_ID = ""

# Fields that must match between MT5 Bridge live remine and Health/backtest.
# train_weeks (M15) / train_months (H1) — see STRATEGY_CONDITION_KEYS_FOR(tf).
STRATEGY_CONDITION_KEYS = (
  "trade_model_id",
  "train_weeks",
  "use_learning",
  "kb_profile",
  "kb_snapshot",
  "feature_profile",
  "spread_pips",
  "slippage_pips",
  "mining_search_space",
)


def _train_unit(tf: str | None = None) -> str:
  return get_tf_defaults(tf or get_active_tf()).train_unit


def _train_key(tf: str | None = None) -> str:
  return "train_months" if _train_unit(tf) == "months" else "train_weeks"


def _read_json(path: Path) -> Any:
  if not path.exists():
    return None
  try:
    with open(path, encoding="utf-8") as f:
      return json.load(f)
  except (OSError, json.JSONDecodeError):
    return None


def _normalize_snapshot(val) -> int | None:
  if val is None or val in ("latest", "Latest", ""):
    return None
  try:
    return int(val)
  except (TypeError, ValueError):
    return None


def list_trade_models() -> list[dict]:
  data = _read_json(MODELS_PATH)
  if not data or not isinstance(data, dict):
    return []
  return list(data.get("models") or [])


def get_model_by_id(model_id: str) -> dict | None:
  for m in list_trade_models():
    if m.get("id") == model_id:
      return m
  return None


def load_active_model_id() -> str | None:
  data = _read_json(ACTIVE_MODEL_PATH)
  if isinstance(data, dict) and data.get("id"):
    return data["id"]
  models = list_trade_models()
  return models[0]["id"] if models else None


def coerce_instance_model_id(model_id: str | None, tf: str | None = None) -> str | None:
  """Prefer the active model for ``tf`` when a foreign-TF id (e.g. tm_h1_* on
  M15, or tm_m15_* on H1) is passed — mirrors EdgeMinerH1's instance guard."""
  t = str(tf or get_active_tf()).upper()
  other = "h1" if t == "M15" else "m15"
  mid = (model_id or "").strip() or None
  active = load_active_model_id()
  if not mid:
    return active
  mid_l = mid.lower()
  if f"tm_{other}" in mid_l or mid_l.startswith(f"{other}_"):
    return active or mid
  m = get_model_by_id(mid)
  if m and str(m.get("data_timeframe") or "").upper() not in ("", t):
    return active or mid
  return mid


def resolve_model(model_id: str | None = None) -> dict | None:
  mid = coerce_instance_model_id(model_id or load_active_model_id())
  return get_model_by_id(mid) if mid else None


def get_model_run_params(model: dict | None = None, model_id: str | None = None) -> dict:
  m = model or resolve_model(model_id)
  tf = str((m or {}).get("data_timeframe") or get_active_tf()).upper()
  key = _train_key(tf)
  default_window = get_tf_defaults(tf).train_length
  if not m:
    return {
      "train_weeks": default_window if key == "train_weeks" else None,
      "train_months": default_window if key == "train_months" else None,
      "train_window": default_window,
      "use_learning": True,
      "use_kb": True,
      "kb_profile": "era_2023_2025",
      "kb_snapshot": 1,
      "oos_from": None,
      "oos_to": None,
      "spread_pips": float(DEFAULT_SPREAD_PIPS),
      "slippage_pips": float(DEFAULT_SLIPPAGE_PIPS),
      "feature_profile": "current",
      "mining_search_space": None,
      "trade_model_id": None,
      "label": None,
    }
  # Accept either unit on the stored model; fall back cross-unit if only the
  # other one is present (rough weeks<->months conversion for old payloads).
  train_weeks = m.get("train_weeks")
  train_months = m.get("train_months")
  if key == "train_months" and train_months is None and train_weeks is not None:
    train_months = max(1, int(round(int(train_weeks) / 4)))
  if key == "train_weeks" and train_weeks is None and train_months is not None:
    train_weeks = max(1, int(round(int(train_months) * 4)))
  train_window = train_months if key == "train_months" else train_weeks
  if train_window is None:
    train_window = default_window
  return {
    "train_weeks": int(train_weeks) if train_weeks is not None else None,
    "train_months": int(train_months) if train_months is not None else None,
    "train_window": int(train_window),
    "use_learning": bool(m.get("use_kb", True)),
    "use_kb": bool(m.get("use_kb", True)),
    "kb_profile": m.get("kb_profile") or "default",
    "kb_snapshot": _normalize_snapshot(m.get("kb_snapshot")),
    "oos_from": m.get("oos_from"),
    "oos_to": m.get("oos_to"),
    "spread_pips": float(m.get("spread_pips", DEFAULT_SPREAD_PIPS)),
    "slippage_pips": float(m.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
    "feature_profile": (
      m.get("feature_profile")
      or ("legacy" if int(m.get("feature_schema") or 0) < 3 else "current")
    ),
    "mining_search_space": m.get("mining_search_space"),
    "trade_model_id": m.get("id"),
    "label": m.get("label"),
  }


def strategy_conditions(params: dict | None) -> dict[str, Any]:
  """Subset of params shared by Bridge remine and Health/backtest."""
  p = params or {}
  ss = p.get("mining_search_space") or None
  key = _train_key()
  train_window = p.get("train_window")
  if train_window is None:
    train_window = p.get(key) or get_tf_defaults(get_active_tf()).train_length
  return {
    "trade_model_id": p.get("trade_model_id"),
    key: int(train_window),
    "use_learning": bool(p.get("use_learning", p.get("use_kb", True))),
    "kb_profile": p.get("kb_profile"),
    "kb_snapshot": p.get("kb_snapshot"),
    "feature_profile": p.get("feature_profile") or "current",
    "spread_pips": round(float(p.get("spread_pips") or DEFAULT_SPREAD_PIPS), 4),
    "slippage_pips": round(float(p.get("slippage_pips") or DEFAULT_SLIPPAGE_PIPS), 4),
    "mining_search_space": ss,
  }


def conditions_fingerprint(params: dict | None) -> str:
  raw = json.dumps(strategy_conditions(params), sort_keys=True, default=str, ensure_ascii=False)
  return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def describe_strategy_conditions(params: dict | None) -> dict[str, Any]:
  """UI-friendly summary (session / spacing / hold)."""
  c = strategy_conditions(params)
  ss = c.get("mining_search_space") or {}
  return {
    **{k: c[k] for k in c if k != "mining_search_space"},
    "session_ranges": ss.get("session_ranges"),
    "min_bars_between": ss.get("min_bars_between"),
    "max_hold_bars": ss.get("max_hold_bars"),
    "conditions_fp": conditions_fingerprint(params),
  }


def conditions_match(a: dict | None, b: dict | None) -> bool:
  return conditions_fingerprint(a) == conditions_fingerprint(b)
