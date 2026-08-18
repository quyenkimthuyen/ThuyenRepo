"""Pin KB snapshot files next to Trade Models for Bridge independence.

Trade Models store ``kb_pin_path`` + ``kb_fingerprint`` pointing at
``results/trade_models/<model_id>_kb_pin.json`` — a frozen copy of the
KB profile/epoch used when the model was created. Live remine reads the
pin (``update_kb=False``) so deleting Settings / Grid / even the original
KB profile does not break MT5 Bridge for that model.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from kb_profiles import resolve_kb_path
from knowledge_base import KnowledgeBase
from run_backtest import REPORT_DIR

MODELS_DIR = REPORT_DIR / "trade_models"
PIN_SUFFIX = "_kb_pin.json"


def model_kb_pin_path(model_id: str) -> Path:
  return MODELS_DIR / f"{model_id}{PIN_SUFFIX}"


def _file_sha256(path: Path) -> str:
  h = hashlib.sha256()
  with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
      h.update(chunk)
  return h.hexdigest()


def pin_kb_for_model(
  model_id: str,
  kb_profile: str | None,
  kb_snapshot: int | str | None,
  *,
  use_kb: bool = True,
) -> dict | None:
  """Copy resolved KB snapshot beside the Trade Model. Returns pin metadata."""
  if not use_kb or not model_id or not kb_profile:
    return None
  try:
    src = resolve_kb_path(str(kb_profile), kb_snapshot)
  except Exception:
    return None
  if not src.exists():
    return None

  MODELS_DIR.mkdir(parents=True, exist_ok=True)
  dest = model_kb_pin_path(model_id)
  shutil.copy2(src, dest)
  fp = _file_sha256(dest)
  # Store path relative to REPORT_DIR for portability within the repo.
  try:
    rel = str(dest.relative_to(REPORT_DIR))
  except ValueError:
    rel = str(dest)
  return {
    "kb_pin_path": rel,
    "kb_fingerprint": fp[:16],
    "kb_pin_bytes": dest.stat().st_size,
    "kb_pin_source": str(src),
  }


def resolve_pin_absolute(kb_pin_path: str | None) -> Path | None:
  if not kb_pin_path:
    return None
  p = Path(kb_pin_path)
  if not p.is_absolute():
    p = REPORT_DIR / p
  return p if p.exists() else None


def load_kb_for_run(
  *,
  use_learning: bool,
  kb_profile: str | None = None,
  kb_snapshot: int | str | None = None,
  kb_pin_path: str | None = None,
) -> KnowledgeBase | None:
  """Prefer pinned KB file; fall back to profile/snapshot catalog."""
  if not use_learning:
    return None
  pinned = resolve_pin_absolute(kb_pin_path)
  if pinned is not None:
    return KnowledgeBase(pinned)
  if not kb_profile:
    return None
  from kb_profiles import load_kb
  return load_kb(kb_profile, kb_snapshot)


def ensure_model_kb_pin(model: dict) -> dict:
  """Attach pin metadata onto ``model`` (mutates + returns). No-op if KB off."""
  if not model.get("use_kb", True):
    model.pop("kb_pin_path", None)
    model.pop("kb_fingerprint", None)
    model.pop("kb_pin_bytes", None)
    return model
  # Reuse existing pin only when file is present AND fingerprint still matches.
  existing = resolve_pin_absolute(model.get("kb_pin_path"))
  expected_fp = str(model.get("kb_fingerprint") or "")
  if existing is not None and expected_fp:
    actual_fp = _file_sha256(existing)[:16]
    if actual_fp == expected_fp:
      return model
    # Corrupt / replaced pin → fall through and re-pin from catalog.
  mid = model.get("id")
  if not mid:
    return model
  meta = pin_kb_for_model(
    mid,
    model.get("kb_profile"),
    model.get("kb_snapshot"),
    use_kb=True,
  )
  if meta:
    model.update(meta)
  return model


def backfill_kb_pins(models: list[dict]) -> list[dict]:
  """Ensure every KB-on model has a pin file; returns models that gained a pin."""
  updated: list[dict] = []
  for m in models:
    before = m.get("kb_fingerprint")
    ensure_model_kb_pin(m)
    if m.get("kb_fingerprint") and m.get("kb_fingerprint") != before:
      updated.append(m)
  return updated
