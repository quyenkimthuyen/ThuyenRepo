"""TrainApp desk loader — config-driven runtime for unified Train cores."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
  import yaml  # type: ignore
except ImportError:  # pragma: no cover
  yaml = None

TRAINAPP_ROOT = Path(__file__).resolve().parent
DESKS_DIR = TRAINAPP_ROOT / "desks"
CORES_DIR = TRAINAPP_ROOT / "cores"
RUNTIME_DIR = TRAINAPP_ROOT / "runtime"

_CACHE: dict[str, Any] = {}


def _parse_simple_yaml(text: str) -> dict[str, Any]:
  """Minimal YAML subset (key: value) — avoids PyYAML dependency if missing."""
  out: dict[str, Any] = {}
  for raw in text.splitlines():
    line = raw.strip()
    if not line or line.startswith("#"):
      continue
    if ":" not in line:
      continue
    key, val = line.split(":", 1)
    key = key.strip()
    val = val.strip().strip('"').strip("'")
    if val.lower() in ("true", "false"):
      out[key] = val.lower() == "true"
      continue
    try:
      if "." in val:
        out[key] = float(val)
      else:
        out[key] = int(val)
      continue
    except ValueError:
      out[key] = val
  return out


def load_desk(desk_id: str | None = None) -> dict[str, Any]:
  desk_id = (desk_id or os.environ.get("TRAINAPP_DESK") or "").strip().lower()
  if not desk_id:
    raise ValueError("TRAINAPP_DESK is not set")
  if _CACHE.get("id") == desk_id and "cfg" in _CACHE:
    return dict(_CACHE["cfg"])

  path = DESKS_DIR / f"{desk_id}.yaml"
  if not path.exists():
    raise FileNotFoundError(f"Desk config missing: {path}")
  text = path.read_text(encoding="utf-8")
  if yaml is not None:
    cfg = yaml.safe_load(text) or {}
  else:
    cfg = _parse_simple_yaml(text)
  if not isinstance(cfg, dict):
    raise ValueError(f"Invalid desk yaml: {path}")
  cfg["id"] = str(cfg.get("id") or desk_id).lower()
  runtime = RUNTIME_DIR / cfg["id"]
  cfg["runtime_root"] = str(runtime.resolve())
  cfg["core_root"] = str((CORES_DIR / str(cfg.get("core") or "m15")).resolve())
  _CACHE.clear()
  _CACHE["id"] = cfg["id"]
  _CACHE["cfg"] = dict(cfg)
  return dict(cfg)


def apply_desk_env(desk_id: str) -> dict[str, Any]:
  cfg = load_desk(desk_id)
  os.environ["TRAINAPP_DESK"] = cfg["id"]
  os.environ["TRAINAPP_RUNTIME"] = cfg["runtime_root"]
  os.environ["TRAINAPP_CORE"] = cfg["core_root"]
  os.environ["TRAINAPP_ROOT"] = str(TRAINAPP_ROOT)
  return cfg


def list_desks() -> list[str]:
  return sorted(p.stem for p in DESKS_DIR.glob("*.yaml"))
