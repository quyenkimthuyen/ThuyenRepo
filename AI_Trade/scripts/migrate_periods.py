#!/usr/bin/env python3
"""Migrate legacy period ids (train, validation, test) to new year-based ids."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.periods import normalize_setup_period  # noqa: E402

LEGACY_MAP = {
    "train": "train_2022",
    "validation": "bt_2023",
    "test": "bt_2024",
}


def migrate_period(value: str | None) -> str:
    if not value:
        return "train_2022"
    return LEGACY_MAP.get(value, value)


def migrate_setups(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for setup in payload.get("setups", []):
        old = setup.get("period", "train")
        new = migrate_period(old)
        if old != new:
            setup["period"] = new
            changed += 1
        elif normalize_setup_period(old) != old:
            setup["period"] = normalize_setup_period(old)
            changed += 1
    if changed:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return changed


def migrate_annotations(path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for ann in payload.get("annotations", []):
        old = ann.get("period", "train")
        new = migrate_period(old)
        if old != new:
            ann["period"] = new
            changed += 1
    if changed:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return changed


def migrate_backtests(path: Path) -> int:
    if not path.exists():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for run in payload.get("runs", []):
        old = run.get("period")
        if not old:
            continue
        if old in LEGACY_MAP:
            run["period"] = LEGACY_MAP[old]
            changed += 1
    if changed:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return changed


def main() -> None:
    labels = ROOT / "data" / "labels"
    n_setups = migrate_setups(labels / "setups.json")
    n_ann = migrate_annotations(labels / "bar_annotations.json")
    n_bt = migrate_backtests(ROOT / "data" / "backtests" / "runs.json")
    print(f"Migrated setups: {n_setups}, annotations: {n_ann}, backtests: {n_bt}")


if __name__ == "__main__":
    main()
