"""TrainApp desk loader — config-driven runtime for unified Train cores."""
from __future__ import annotations

import json
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


def _is_under(path: Path, root: Path) -> bool:
  try:
    path.resolve().relative_to(root.resolve())
    return True
  except (ValueError, OSError):
    return False


def _relocate_under_root(raw: str, *, root: Path) -> str | None:
  text = (raw or "").strip()
  if not text:
    return None
  root = root.resolve()
  p = Path(text)
  if not p.is_absolute() and not (len(text) >= 2 and text[1] == ":"):
    abs_p = (root / p).resolve()
  elif _is_under(p, root):
    try:
      abs_p = p.resolve()
    except OSError:
      abs_p = root / p.name
  else:
    name = p.name
    parts_l = [x.lower() for x in p.parts]
    if "simulate_runs" in parts_l:
      abs_p = (root / "results" / "simulate_runs" / name).resolve()
    else:
      parent = p.parent.name.lower()
      if name.lower().startswith("bridge") or parent == "mt5":
        abs_p = (root / "mt5" / name).resolve()
      elif parent == "results":
        abs_p = (root / "results" / name).resolve()
      else:
        return None
  try:
    return abs_p.resolve().relative_to(root).as_posix()
  except ValueError:
    return str(abs_p)


def _heal_json_paths(path: Path, *, root: Path) -> bool:
  if not path.is_file():
    return False
  try:
    data = json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return False
  if not isinstance(data, dict):
    return False

  changed = False

  def walk(node: Any) -> None:
    nonlocal changed
    if isinstance(node, dict):
      for k, v in list(node.items()):
        if isinstance(v, str) and k in ("bridge_dir", "archive_path"):
          relocated = _relocate_under_root(v, root=root)
          if relocated and relocated != v:
            node[k] = relocated
            changed = True
        else:
          walk(v)
    elif isinstance(node, list):
      for item in node:
        walk(item)

  walk(data)
  if not changed:
    return False
  path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
  return True


def heal_runtime_paths(runtime_root: str | Path | None = None) -> int:
  """Rewrite stale absolute paths in runtime JSON so a copied folder still works."""
  root = Path(runtime_root or os.environ.get("TRAINAPP_RUNTIME") or "").resolve()
  if not root.is_dir():
    return 0
  n = 0
  results = root / "results"
  for name in ("mt5_bridge_config.json", "mt5_bridge_sim_state.json"):
    if _heal_json_paths(results / name, root=root):
      n += 1
  return n


def apply_desk_env(desk_id: str) -> dict[str, Any]:
  cfg = load_desk(desk_id)
  os.environ["TRAINAPP_DESK"] = cfg["id"]
  os.environ["TRAINAPP_RUNTIME"] = cfg["runtime_root"]
  os.environ["TRAINAPP_CORE"] = cfg["core_root"]
  os.environ["TRAINAPP_ROOT"] = str(TRAINAPP_ROOT)
  heal_runtime_paths(cfg["runtime_root"])
  return cfg


def list_desks() -> list[str]:
  return sorted(p.stem for p in DESKS_DIR.glob("*.yaml"))
