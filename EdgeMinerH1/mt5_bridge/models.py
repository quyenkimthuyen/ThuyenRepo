"""Headless trade-model loaders (no Streamlit)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS, DEFAULT_TF, TRAIN_MONTHS
from run_backtest import REPORT_DIR
from mt5_bridge.protocol import INSTANCE_ID, DEFAULT_TIMEFRAME

MODELS_PATH = REPORT_DIR / "trade_models.json"
ACTIVE_MODEL_PATH = REPORT_DIR / "active_trade_model.json"
DEFAULT_MODEL_ID = ""


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


def coerce_instance_model_id(model_id: str | None) -> str | None:
  """Prefer active H1 model when a foreign TF id (e.g. tm_m15_*) is passed."""
  mid = (model_id or "").strip() or None
  active = load_active_model_id()
  tf = (DEFAULT_TIMEFRAME or DEFAULT_TF or INSTANCE_ID or "").upper()
  if not mid:
    return active
  mid_l = mid.lower()
  if tf == "H1" and ("m15" in mid_l or mid_l.startswith("tm_m15")):
    return active or mid
  m = get_model_by_id(mid)
  if m and tf and str(m.get("data_timeframe") or "").upper() not in ("", tf):
    return active or mid
  return mid


def resolve_model(model_id: str | None = None) -> dict | None:
  mid = coerce_instance_model_id(model_id or load_active_model_id())
  return get_model_by_id(mid) if mid else None


def get_model_run_params(model: dict | None = None, model_id: str | None = None) -> dict:
  m = model or resolve_model(model_id)
  if not m:
    return {
      "train_months": int(TRAIN_MONTHS),
      "use_learning": True,
      "use_kb": True,
      "kb_profile": "era_2023_2025",
      "kb_snapshot": 1,
      "spread_pips": float(DEFAULT_SPREAD_PIPS),
      "slippage_pips": float(DEFAULT_SLIPPAGE_PIPS),
      "trade_model_id": None,
    }
  return {
    "train_months": int(m.get("train_months", TRAIN_MONTHS)),
    "use_learning": bool(m.get("use_kb", True)),
    "use_kb": bool(m.get("use_kb", True)),
    "kb_profile": m.get("kb_profile") or "default",
    "kb_snapshot": _normalize_snapshot(m.get("kb_snapshot")),
    "oos_from": m.get("oos_from"),
    "oos_to": m.get("oos_to"),
    "spread_pips": float(m.get("spread_pips", DEFAULT_SPREAD_PIPS)),
    "slippage_pips": float(m.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
    "trade_model_id": m.get("id"),
    "label": m.get("label"),
  }


def strategy_conditions(params: dict | None) -> dict[str, Any]:
  """Subset of params shared by Bridge remine and Health/backtest (H1)."""
  p = params or {}
  return {
    "trade_model_id": p.get("trade_model_id"),
    "train_months": int(p.get("train_months") or TRAIN_MONTHS),
    "use_learning": bool(p.get("use_learning", p.get("use_kb", True))),
    "kb_profile": p.get("kb_profile"),
    "kb_snapshot": p.get("kb_snapshot"),
    "spread_pips": round(float(p.get("spread_pips") or DEFAULT_SPREAD_PIPS), 4),
    "slippage_pips": round(float(p.get("slippage_pips") or DEFAULT_SLIPPAGE_PIPS), 4),
  }


def conditions_fingerprint(params: dict | None) -> str:
  import hashlib
  raw = json.dumps(strategy_conditions(params), sort_keys=True, default=str, ensure_ascii=False)
  return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def describe_strategy_conditions(params: dict | None) -> dict[str, Any]:
  c = strategy_conditions(params)
  return {**c, "conditions_fp": conditions_fingerprint(params)}
