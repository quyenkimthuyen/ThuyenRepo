"""Human-readable codes for bar annotations and setups."""

from __future__ import annotations

import re

import pandas as pd

_BAR_CODE_RE = re.compile(r"^NB-\d{8}-H\d{2}(-\d+)?$")
_SETUP_CODE_RE = re.compile(r"^ST-[LS]-\d{8}-H\d{2}(-\d+)?$")


def bar_code(bar_time: pd.Timestamp | str) -> str:
    ts = pd.Timestamp(bar_time)
    if ts.tz is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return f"NB-{ts.strftime('%Y%m%d')}-H{ts.hour:02d}"


def setup_code(direction: str, entry_time: pd.Timestamp | str) -> str:
    ts = pd.Timestamp(entry_time)
    if ts.tz is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    letter = "L" if direction == "long" else "S"
    return f"ST-{letter}-{ts.strftime('%Y%m%d')}-H{ts.hour:02d}"


def unique_code(base: str, used: set[str]) -> str:
    if base not in used:
        return base
    n = 2
    while f"{base}-{n}" in used:
        n += 1
    return f"{base}-{n}"


def display_bar_code(record: dict) -> str:
    code = record.get("code")
    if code and _BAR_CODE_RE.match(code):
        return code
    bar_time = record.get("bar_time")
    if bar_time:
        return bar_code(bar_time)
    return str(record.get("id", "—"))


def display_setup_code(record: dict) -> str:
    code = record.get("code")
    if code and _SETUP_CODE_RE.match(code):
        return code
    entry_time = record.get("entry_time")
    direction = record.get("direction", "long")
    if entry_time:
        return setup_code(direction, entry_time)
    return str(record.get("id", "—"))


def assign_bar_code(payload: dict, existing: list[dict]) -> str:
    used = {a.get("code") or a.get("id", "") for a in existing}
    used |= {a.get("id", "") for a in existing}
    base = bar_code(payload["bar_time"])
    return unique_code(base, used)


def assign_setup_code(payload: dict, existing: list[dict]) -> str:
    used = {s.get("code") or s.get("id", "") for s in existing}
    used |= {s.get("id", "") for s in existing}
    base = setup_code(payload["direction"], payload["entry_time"])
    return unique_code(base, used)
