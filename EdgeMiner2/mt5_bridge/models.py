"""Headless trade-model loaders (no Streamlit)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS
from run_backtest import REPORT_DIR

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
      "spread_pips": float(DEFAULT_SPREAD_PIPS),
      "slippage_pips": float(DEFAULT_SLIPPAGE_PIPS),
      "trade_model_id": None,
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
    "trade_model_id": m.get("id"),
    "label": m.get("label"),
  }
