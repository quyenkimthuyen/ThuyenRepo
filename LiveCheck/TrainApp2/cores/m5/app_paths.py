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


def relocate_under_root(
  raw: str | os.PathLike | None,
  *,
  root: Path,
  default_parent: str = "mt5",
) -> Path | None:
  """Map a stored path onto this app copy.

  Relative paths join ``root``. Absolute paths already under ``root`` are kept.
  Absolute paths from another machine/folder are remapped by leaf name
  (``mt5/bridge_*`` or ``results/simulate_runs/*``).
  """
  if raw is None:
    return None
  text = str(raw).strip()
  if not text:
    return None
  root = Path(root).resolve()
  p = Path(text)
  if not p.is_absolute() and not (len(text) >= 2 and text[1] == ":"):
    return (root / p).resolve()
  if _is_under(p, root):
    try:
      return p.resolve()
    except OSError:
      return root / p.name
  name = p.name
  parts_l = [x.lower() for x in p.parts]
  if "simulate_runs" in parts_l:
    return (root / "results" / "simulate_runs" / name).resolve()
  parent = p.parent.name.lower()
  if name.lower().startswith("bridge") or parent == "mt5":
    return (root / "mt5" / name).resolve()
  if parent == "results":
    return (root / "results" / name).resolve()
  return (root / default_parent / name).resolve()


def get_root() -> Path:
  """Writable desk workspace: data / results / learning / mt5."""
  desk = (os.environ.get("TRAINAPP_DESK") or "").strip().lower()
  app_root = (os.environ.get("TRAINAPP_ROOT") or "").strip()
  runtime = (os.environ.get("TRAINAPP_RUNTIME") or "").strip()
  if app_root:
    root = Path(app_root).resolve()
    if runtime:
      rp = Path(runtime)
      if _is_under(rp, root):
        return rp.resolve()
    if desk:
      return (root / "runtime" / desk).resolve()
    return root
  if runtime:
    return Path(runtime).resolve()
  return Path(__file__).resolve().parent


def get_core_root() -> Path:
  env = (os.environ.get("TRAINAPP_CORE") or "").strip()
  app_root = (os.environ.get("TRAINAPP_ROOT") or "").strip()
  here = Path(__file__).resolve().parent
  if app_root:
    root = Path(app_root).resolve()
    if env:
      p = Path(env)
      if _is_under(p, root):
        return p.resolve()
    if _is_under(here, root):
      return here
  if env:
    return Path(env).resolve()
  return here
