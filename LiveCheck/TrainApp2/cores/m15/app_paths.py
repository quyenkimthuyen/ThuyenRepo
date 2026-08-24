"""Resolve TrainApp runtime root (state) vs core root (code)."""
from __future__ import annotations

import os
from pathlib import Path


def get_root() -> Path:
  """Writable desk workspace: data / results / learning / mt5."""
  env = (os.environ.get("TRAINAPP_RUNTIME") or "").strip()
  if env:
    return Path(env).resolve()
  # Fallback: running as legacy flat desk (code dir == state dir).
  return Path(__file__).resolve().parent


def get_core_root() -> Path:
  env = (os.environ.get("TRAINAPP_CORE") or "").strip()
  if env:
    return Path(env).resolve()
  return Path(__file__).resolve().parent
