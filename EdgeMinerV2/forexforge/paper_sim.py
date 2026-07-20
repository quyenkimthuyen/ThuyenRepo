"""Paper trading simulation — signals + cost-model fills + durable journal."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS, DEFAULT_START_DATE
from .logging_util import get_logger
from .paper_monitor import get_monitor_state
from .paths import RESULTS_DIR, ensure_dirs
from .data_loader import load_eurusd_h1

log = get_logger("forexforge.paper")

JOURNAL_PATH = RESULTS_DIR / "paper_journal.jsonl"
STATE_PATH = RESULTS_DIR / "paper_state.json"


def _utc() -> str:
  return datetime.now(timezone.utc).isoformat()


def _append_journal(event: dict[str, Any]) -> None:
  ensure_dirs()
  with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
    f.write(json.dumps(event, ensure_ascii=False) + "\n")


def load_journal(limit: int = 200) -> list[dict]:
  if not JOURNAL_PATH.exists():
    return []
  rows = []
  with open(JOURNAL_PATH, encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if line:
        rows.append(json.loads(line))
  return rows[-limit:]


def load_paper_state() -> dict:
  if not STATE_PATH.exists():
    return {"enabled": False, "sessions": []}
  with open(STATE_PATH, encoding="utf-8") as f:
    return json.load(f)


def save_paper_state(state: dict) -> None:
  ensure_dirs()
  with open(STATE_PATH, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=2, ensure_ascii=False)


def run_paper_tick(
  *,
  use_kb: bool = False,
  kb_profile: str | None = None,
  kb_epoch: int | str | None = None,
  spread_pips: float = DEFAULT_SPREAD_PIPS,
  slippage_pips: float = DEFAULT_SLIPPAGE_PIPS,
) -> dict:
  """
  One paper tick: mine current-week strategy, project signals,
  simulate fills with the same cost model as backtest, journal everything.
  """
  df = load_eurusd_h1(DEFAULT_START_DATE)
  monitor = get_monitor_state(
    df,
    use_learning=use_kb,
    kb_profile=kb_profile,
    kb_snapshot=kb_epoch,
    spread_pips=spread_pips,
    slippage_pips=slippage_pips,
  )
  if monitor.get("error"):
    log.warning("Paper tick error: %s", monitor["error"])
    _append_journal({"ts": _utc(), "type": "error", "message": monitor["error"]})
    return monitor

  tick_id = uuid.uuid4().hex[:10]
  event = {
    "ts": _utc(),
    "type": "tick",
    "tick_id": tick_id,
    "week_start": monitor.get("week_start"),
    "kb_profile": kb_profile,
    "use_kb": use_kb,
    "spread_pips": spread_pips,
    "slippage_pips": slippage_pips,
    "signals": monitor.get("signals_this_week", []),
    "trades": monitor.get("recent_trades", []),
    "week_total_r": monitor.get("week_total_r"),
    "week_wr": monitor.get("week_wr"),
    "strategy": monitor.get("strategy"),
  }
  _append_journal(event)

  state = load_paper_state()
  state["enabled"] = True
  state["last_tick"] = event["ts"]
  state["last_tick_id"] = tick_id
  state["last_monitor"] = {
    "week_start": monitor.get("week_start"),
    "week_total_r": monitor.get("week_total_r"),
    "week_wr": monitor.get("week_wr"),
    "signals": len(monitor.get("signals_this_week") or []),
    "trades": monitor.get("week_trades_taken"),
  }
  sessions = state.setdefault("sessions", [])
  sessions.append({"tick_id": tick_id, "ts": event["ts"]})
  state["sessions"] = sessions[-500:]
  save_paper_state(state)
  log.info(
    "Paper tick %s week=%s trades=%s R=%s",
    tick_id, monitor.get("week_start"), monitor.get("week_trades_taken"), monitor.get("week_total_r"),
  )
  monitor["tick_id"] = tick_id
  monitor["journal_path"] = str(JOURNAL_PATH)
  return monitor
