from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from systemtrain.live.paper_account import PaperSessionState, PaperTrade

PAPER_DIR = Path("data/paper")
STATE_PATH = PAPER_DIR / "state.json"
JOURNAL_PATH = PAPER_DIR / "journal.jsonl"


def load_session(path: Path = STATE_PATH) -> PaperSessionState:
    if not path.exists():
        return PaperSessionState()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return PaperSessionState.from_dict(raw)


def save_session(session: PaperSessionState, path: Path = STATE_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def append_journal(event: dict[str, Any], path: Path = JOURNAL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")


def load_journal(limit: int = 200, path: Path = JOURNAL_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    events: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        if line.strip():
            events.append(json.loads(line))
    return events


def reset_session(strategy: str | None = None, path: Path = STATE_PATH) -> PaperSessionState:
    if strategy is None:
        session = PaperSessionState()
    else:
        session = load_session(path)
        session.strategies.pop(strategy, None)
    save_session(session, path)
    return session


def trade_event(event_type: str, trade: PaperTrade, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "event": event_type,
        "strategy": trade.strategy,
        "trade": trade.to_dict(),
        **(extra or {}),
    }

