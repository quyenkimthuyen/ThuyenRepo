from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
  import yaml  # type: ignore
except ImportError:  # pragma: no cover
  yaml = None

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "protocol.yaml"
RESULTS = ROOT / "results"


def _parse_simple_yaml(text: str) -> dict[str, Any]:
  """Minimal nested YAML subset for protocol.yaml without PyYAML."""
  root: dict[str, Any] = {}
  stack: list[tuple[int, dict[str, Any] | list]] = [(0, root)]
  pending_key: str | None = None

  def parse_val(raw: str):
    raw = raw.strip().strip('"').strip("'")
    if raw.lower() in ("true", "false"):
      return raw.lower() == "true"
    try:
      if "." in raw:
        return float(raw)
      return int(raw)
    except ValueError:
      return raw

  for line in text.splitlines():
    if not line.strip() or line.strip().startswith("#"):
      continue
    indent = len(line) - len(line.lstrip(" "))
    stripped = line.strip()
    while stack and indent < stack[-1][0]:
      stack.pop()
    parent = stack[-1][1]
    if stripped.endswith(":") and ":" == stripped[-1] and stripped.count(":") == 1:
      key = stripped[:-1].strip()
      new_map: dict[str, Any] = {}
      if isinstance(parent, dict):
        parent[key] = new_map
      stack.append((indent + 2, new_map))
      continue
    if ":" in stripped:
      key, val = stripped.split(":", 1)
      key = key.strip()
      val = val.strip()
      if val == "":
        new_map = {}
        if isinstance(parent, dict):
          parent[key] = new_map
        stack.append((indent + 2, new_map))
      else:
        if isinstance(parent, dict):
          parent[key] = parse_val(val)
  return root


def load_protocol(path: Path | None = None) -> dict[str, Any]:
  path = path or CONFIG_PATH
  text = path.read_text(encoding="utf-8")
  if yaml is not None:
    data = yaml.safe_load(text)
  else:
    data = _parse_simple_yaml(text)
  if not isinstance(data, dict):
    raise ValueError(f"Invalid protocol: {path}")
  return data


@dataclass(frozen=True)
class Desk:
  id: str
  label: str
  pair: str
  tf: str
  spread_pips: float
  data_parquet: Path
  trainapp_runtime: Path


def list_desks(protocol: dict[str, Any] | None = None) -> list[Desk]:
  protocol = protocol or load_protocol()
  out: list[Desk] = []
  for desk_id, cfg in (protocol.get("desks") or {}).items():
    out.append(
      Desk(
        id=str(desk_id),
        label=str(cfg.get("label") or desk_id).upper(),
        pair=str(cfg.get("pair") or ""),
        tf=str(cfg.get("tf") or ""),
        spread_pips=float(cfg.get("spread_pips") or 2.0),
        data_parquet=Path(str(cfg.get("data_parquet"))),
        trainapp_runtime=Path(str(cfg.get("trainapp_runtime"))),
      )
    )
  return out


def get_desk(desk_id: str, protocol: dict[str, Any] | None = None) -> Desk:
  protocol = protocol or load_protocol()
  for d in list_desks(protocol):
    if d.id == desk_id:
      return d
  raise KeyError(desk_id)
