"""Resolve TrainApp runtime root (state) vs core root (code).

Paths follow this copy of the app (TRAINAPP_ROOT / this file). Stale env vars
or JSON from another folder/machine are ignored or remapped.
"""
from __future__ import annotations

import os
from pathlib import Path


def _is_under(path: Path, root: Path) -> bool:
  try:
    path.resolve().relative_to(root.resolve())
    return True
  except (ValueError, OSError):
    return False


def _normalized_parts(raw: str) -> list[str]:
  text = str(raw).strip().replace("\\", "/")
  if text.lower().startswith("mt5/") and ":/" in text[4:]:
    text = text[4:]
  return [p for p in text.split("/") if p and p != "."]


def _bridge_folder_from_parts(parts: list[str]) -> str | None:
  for i, part in enumerate(parts):
    if part.lower() == "mt5" and i + 1 < len(parts):
      nxt = parts[i + 1]
      if nxt.lower().startswith("bridge"):
        return nxt
  for part in reversed(parts):
    if part.lower().startswith("bridge"):
      return part
  return None


def _is_windows_abs(text: str) -> bool:
  return len(text) >= 2 and text[1] == ":"


def this_train_root() -> Path:
  """Train folder that contains this copy of cores/m15 (not a sibling clone)."""
  return Path(__file__).resolve().parents[2]


def relocate_under_root(
  raw: str | os.PathLike | None,
  *,
  root: Path,
  default_parent: str = "mt5",
) -> Path | None:
  """Map a stored path onto this app copy.

  Relative paths join ``root``. Absolute paths already under ``root`` or this
  Train tree are kept. Paths from a sibling clone (M15, LiveCheck2, …) are
  remapped even if that folder still exists on disk.
  """
  if raw is None:
    return None
  text = str(raw).strip()
  if not text:
    return None
  root = Path(root).resolve()
  train = this_train_root()
  norm = text.replace("\\", "/")
  p = Path(text)
  if not p.is_absolute() and not _is_windows_abs(norm):
    return (root / p).resolve()
  if _is_under(p, root):
    try:
      return p.resolve()
    except OSError:
      return root / p.name
  try:
    if p.exists() and _is_under(p, train):
      return p.resolve()
  except OSError:
    pass
  parts = _normalized_parts(text)
  parts_l = [x.lower() for x in parts]
  bridge = _bridge_folder_from_parts(parts)
  if bridge:
    return (root / "mt5" / bridge).resolve()
  if "simulate_runs" in parts_l:
    return (root / "results" / "simulate_runs" / parts[-1]).resolve()
  name = parts[-1] if parts else p.name
  parent = parts[-2].lower() if len(parts) >= 2 else p.parent.name.lower()
  if name.lower().startswith("bridge") or parent == "mt5":
    return (root / "mt5" / name).resolve()
  if parent == "results":
    return (root / "results" / name).resolve()
  return (root / default_parent / name).resolve()


def _trusted_train_root() -> Path:
  here = this_train_root()
  app_root = (os.environ.get("TRAINAPP_ROOT") or "").strip()
  if app_root:
    cand = Path(app_root).resolve()
    if cand == here or _is_under(cand, here):
      return cand
  return here


def get_root() -> Path:
  """Writable desk workspace: data / results / learning / mt5."""
  desk = (os.environ.get("TRAINAPP_DESK") or "").strip().lower()
  runtime = (os.environ.get("TRAINAPP_RUNTIME") or "").strip()
  root = _trusted_train_root()
  here = Path(__file__).resolve().parent
  if runtime:
    try:
      rp = Path(runtime).resolve()
    except OSError:
      rp = Path(runtime)
    if _is_under(rp, root):
      return rp
  if desk:
    return (root / "runtime" / desk).resolve()
  return here


def get_core_root() -> Path:
  here = Path(__file__).resolve().parent
  train = this_train_root()
  env = (os.environ.get("TRAINAPP_CORE") or "").strip()
  if env:
    try:
      p = Path(env).resolve()
    except OSError:
      p = Path(env)
    if p == here or _is_under(p, train):
      return p
  return here
