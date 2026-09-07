"""Identity for this Train folder copy so sibling clones do not share ports/bridges.

YAML desks stay the M15 template (8911, bridge_lc2_e21, …). Runtime overlays a
slug from the parent folder name (M15_check → check, M15_bk → bk). Canonical
folders ``M15`` and ``LiveCheck2`` keep the template identity.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_CANONICAL = frozenset({"m15", "livecheck2"})


def train_root() -> Path:
  return Path(__file__).resolve().parent


def clone_folder_name(root: Path | None = None) -> str:
  return (root or train_root()).resolve().parent.name


def clone_slug(folder: str | None = None) -> str:
  n = (folder if folder is not None else clone_folder_name()).strip().lower()
  n = n.replace("-", "_").replace(" ", "_")
  if n in _CANONICAL:
    return ""
  if n.startswith("m15_"):
    return n[4:]
  if n.startswith("livecheck"):
    rest = n[len("livecheck"):].lstrip("_")
    return f"lc{rest}" if rest else "lc"
  return "".join(ch for ch in n if ch.isalnum() or ch == "_").strip("_")[:16]


def clone_port_offset(slug: str | None = None) -> int:
  s = slug if slug is not None else clone_slug()
  if not s:
    return 0
  h = 0
  for b in s.encode("utf-8"):
    h = (h * 33 + b) & 0xFFFFFFFF
  return 100 * (1 + (h % 5))


def _alnum_tag(slug: str) -> str:
  return "".join(ch for ch in slug if ch.isalnum())[:12]


def overlay_desk_identity(
  cfg: dict[str, Any],
  *,
  train_root: Path | None = None,
) -> dict[str, Any]:
  """Return a copy of desk yaml with clone-unique ports / bridge / magic."""
  out = dict(cfg)
  slug = clone_slug(clone_folder_name(train_root))
  off = clone_port_offset(slug)
  if slug and out.get("clone_slug") == slug and int(out.get("clone_port_offset") or 0) == off:
    return out
  out["clone_slug"] = slug
  out["clone_port_offset"] = off
  if not slug:
    out.setdefault("sim_chart_port", 10086)
    out.setdefault("compare_chart_port", 10196)
    return out

  tag = _alnum_tag(slug)
  suffix = f"_{slug}"
  tag_u = tag.upper()

  if out.get("port") is not None:
    out["port"] = int(out["port"]) + off
  if out.get("chart_port") is not None:
    out["chart_port"] = int(out["chart_port"]) + off
  if out.get("magic") is not None:
    out["magic"] = int(out["magic"]) + off
  if out.get("sim_magic") is not None:
    out["sim_magic"] = int(out["sim_magic"]) + off

  b = str(out.get("bridge_subdir") or "")
  if b and not b.endswith(suffix):
    out["bridge_subdir"] = f"{b}{suffix}"
  bs = str(out.get("bridge_sim_subdir") or "")
  if bs and not bs.endswith(suffix):
    out["bridge_sim_subdir"] = f"{bs}{suffix}"

  inst = str(out.get("instance_id") or "")
  if inst and tag_u and not inst.upper().endswith(tag_u):
    out["instance_id"] = f"{inst}{tag_u}"

  out["sim_chart_port"] = 10086 + off
  out["compare_chart_port"] = 10196 + off
  return out
