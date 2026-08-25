#!/usr/bin/env python3
"""Render per-desk ForgeBridge EA from mt5/template (ForgeBridgeLive v1.27 base).

  python scripts/render_forgebridge_ea.py
  python scripts/render_forgebridge_ea.py --desk e21
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "mt5" / "template" / "ForgeBridgeDesk.mq5.template"

# Defaults for runtime desks (yaml may override instance_id / magic / bridge_subdir).
DESKS: list[dict] = [
  {
    "desk": "e21",
    "instance_id": "LC2E21",
    "bridge_subdir": "bridge_lc2_e21",
    "magic": 20281021,
    "chart_bars": 1344,
    "desk_line": "EURUSD M15",
  },
  {
    "desk": "g23",
    "instance_id": "LC2G23",
    "bridge_subdir": "bridge_lc2_g23",
    "magic": 20281041,
    "chart_bars": 1344,
    "desk_line": "GBPUSD M15",
  },
]


def _load_yaml_overrides(desk_id: str) -> dict:
  path = ROOT / "desks" / f"{desk_id}.yaml"
  if not path.is_file():
    return {}
  out: dict = {}
  for line in path.read_text(encoding="utf-8").splitlines():
    line = line.split("#", 1)[0].strip()
    if not line or ":" not in line:
      continue
    k, v = line.split(":", 1)
    out[k.strip()] = v.strip().strip('"').strip("'")
  mapped: dict = {}
  if out.get("instance_id"):
    mapped["instance_id"] = out["instance_id"]
  if out.get("bridge_subdir"):
    mapped["bridge_subdir"] = out["bridge_subdir"]
  if out.get("magic"):
    mapped["magic"] = int(out["magic"])
  if out.get("bar_minutes"):
    bm = int(out["bar_minutes"])
    mapped["chart_bars"] = 4032 if bm <= 5 else 1344
  sym = out.get("symbol") or ""
  tf = out.get("tf") or ""
  if sym and tf:
    mapped["desk_line"] = f"{sym} {tf}"
  return mapped


def render_one(cfg: dict, template: str) -> Path:
  desk = cfg["desk"]
  instance_id = str(cfg["instance_id"])
  ea_stem = f"ForgeBridge{instance_id}"
  text = template
  subs = {
    "@@EA_STEM@@": ea_stem,
    "@@INSTANCE_ID@@": instance_id,
    "@@BRIDGE_SUBDIR@@": str(cfg["bridge_subdir"]),
    "@@MAGIC@@": str(int(cfg["magic"])),
    "@@CHART_BARS@@": str(int(cfg["chart_bars"])),
    "@@DESK_LINE@@": str(cfg.get("desk_line") or instance_id),
  }
  for k, v in subs.items():
    text = text.replace(k, v)
  if "@@" in text:
    missing = sorted(set(re.findall(r"@@\w+@@", text)))
    raise RuntimeError(f"{desk}: unresolved placeholders {missing}")
  dest = ROOT / "runtime" / desk / "mt5" / "Experts" / f"{ea_stem}.mq5"
  dest.parent.mkdir(parents=True, exist_ok=True)
  dest.write_text(text, encoding="utf-8")
  return dest


def main(argv: list[str] | None = None) -> int:
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--desk", action="append", help="Only render these desk ids (e21, g23, …)")
  args = ap.parse_args(argv)
  if not TEMPLATE.is_file():
    print(f"Missing template: {TEMPLATE}", file=sys.stderr)
    return 1
  template = TEMPLATE.read_text(encoding="utf-8")
  want = {d.strip().lower() for d in (args.desk or []) if d.strip()}
  rendered: list[Path] = []
  for base in DESKS:
    if want and base["desk"] not in want:
      continue
    cfg = {**base, **_load_yaml_overrides(base["desk"])}
    rendered.append(render_one(cfg, template))
  if not rendered:
    print("No desks rendered.", file=sys.stderr)
    return 1
  for p in rendered:
    print(f"OK {p.relative_to(ROOT)}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
