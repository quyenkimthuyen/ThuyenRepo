"""Read Live trade journal / fills from bridge_live."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from live_config import BRIDGE_DIR


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def load_trades(bridge_dir: Path | None = None) -> list[dict]:
  bdir = Path(bridge_dir or BRIDGE_DIR)
  data = _read(bdir / "trades.json")
  if isinstance(data, dict):
    return list(data.get("trades") or [])
  if isinstance(data, list):
    return data
  return []


def load_recent_fills(bridge_dir: Path | None = None, limit: int = 50) -> list[dict]:
  bdir = Path(bridge_dir or BRIDGE_DIR)
  path = bdir / "fills.jsonl"
  if not path.exists():
    return []
  rows: list[dict] = []
  with open(path, encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if not line:
        continue
      try:
        rows.append(json.loads(line))
      except json.JSONDecodeError:
        continue
  return rows[-limit:]


def journal_summary(bridge_dir: Path | None = None) -> dict[str, Any]:
  trades = load_trades(bridge_dir)
  closed = [t for t in trades if t.get("exit") is not None or t.get("status") == "closed"]
  r_vals = []
  for t in closed:
    try:
      if t.get("r") is not None:
        r_vals.append(float(t["r"]))
    except (TypeError, ValueError):
      pass
  wins = sum(1 for r in r_vals if r > 0)
  losses = sum(1 for r in r_vals if r < 0)
  return {
    "n_trades": len(trades),
    "n_closed": len(closed),
    "total_r": round(sum(r_vals), 3) if r_vals else 0.0,
    "wins": wins,
    "losses": losses,
    "win_rate_pct": round(100.0 * wins / len(r_vals), 1) if r_vals else None,
    "recent_fills": len(load_recent_fills(bridge_dir, limit=500)),
  }
