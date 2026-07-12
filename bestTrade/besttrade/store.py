"""BestTrade paper / journal persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from besttrade.paths import BESTTRADE_ROOT

PAPER_DIR = BESTTRADE_ROOT / "data" / "paper"
STATE_PATH = PAPER_DIR / "state.json"
JOURNAL_PATH = PAPER_DIR / "journal.jsonl"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def load_paper_state() -> dict[str, Any]:
    return load_json(STATE_PATH, {})


def save_paper_state(state: dict[str, Any]) -> Path:
    return save_json(STATE_PATH, state)


def append_journal(event: dict[str, Any]) -> None:
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    with JOURNAL_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")


def load_journal(limit: int = 500) -> list[dict[str, Any]]:
    if not JOURNAL_PATH.exists():
        return []
    lines = JOURNAL_PATH.read_text(encoding="utf-8").splitlines()
    events: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        if line.strip():
            events.append(json.loads(line))
    return events


def reset_paper() -> None:
    save_paper_state({})
    if JOURNAL_PATH.exists():
        JOURNAL_PATH.unlink()
