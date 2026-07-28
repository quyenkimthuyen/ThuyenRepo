"""Headless trade-model loaders (no Streamlit).

Canonical source for Bridge + Health/backtest run conditions
(train weeks, KB, feature profile, mining search space, spread/slip).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS
from run_backtest import REPORT_DIR

MODELS_PATH = REPORT_DIR / "trade_models.json"
ACTIVE_MODEL_PATH = REPORT_DIR / "active_trade_model.json"
DEFAULT_MODEL_ID = ""

# Fields that must match between MT5 Bridge live remine and Health/backtest.
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


def resolve_model(model_id: str | None = None) -> dict | None:
  mid = model_id or load_active_model_id()
  return get_model_by_id(mid) if mid else None


def get_model_run_params(model: dict | None = None, model_id: str | None = None) -> dict:
  m = model or resolve_model(model_id)
  if not m:
    return {
      "train_weeks": 3,
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
  return {
    "train_weeks": int(m.get("train_weeks", 3)),
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
  return {
    "trade_model_id": p.get("trade_model_id"),
    "train_weeks": int(p.get("train_weeks") or 3),
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
