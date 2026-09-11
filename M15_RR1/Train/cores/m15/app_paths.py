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
  norm = text.replace("\\", "/")
  p = Path(text)
  if not p.is_absolute() and not _is_windows_abs(norm):
    return (root / p).resolve()
  if _is_under(p, root):
    try:
      return p.resolve()
    except OSError:
      return root / p.name
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


def get_root() -> Path:
  """Writable desk workspace: data / results / learning / mt5."""
  desk = (os.environ.get("TRAINAPP_DESK") or "").strip().lower()
  app_root = (os.environ.get("TRAINAPP_ROOT") or "").strip()
  runtime = (os.environ.get("TRAINAPP_RUNTIME") or "").strip()
  if app_root:
    root = Path(app_root).resolve()
    if runtime:
      rt = runtime.replace("\\", "/")
      if not _is_windows_abs(rt):
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
      ev = env.replace("\\", "/")
      if not _is_windows_abs(ev):
        p = Path(env)
        if _is_under(p, root):
          return p.resolve()
    if _is_under(here, root):
      return here
  if env:
    return Path(env).resolve()
  return here
