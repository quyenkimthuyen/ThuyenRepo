"""Runtime risk limits for Live bridge (slots / max trades per day)."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from config import MAX_TRADES_PER_DAY
from mt5_bridge.history_sync import parse_broker_time, utc_to_broker_time
from mt5_bridge.trade_journal import load_trades, trade_mode

import pandas as pd


def _cfg_int_map(raw: Any) -> dict[str, int]:
  if not isinstance(raw, dict):
    return {}
  out: dict[str, int] = {}
  for k, v in raw.items():
    mid = str(k or "").strip()
    if not mid:
      continue
    try:
      out[mid] = max(0, int(v))
    except (TypeError, ValueError):
      continue
  return out


def model_default_max_trades(model: dict | None) -> int:
  if not model:
    return int(MAX_TRADES_PER_DAY)
  raw = model.get("max_trades_per_day")
  if raw is None:
    return int(MAX_TRADES_PER_DAY)
  try:
    return max(0, int(raw))
  except (TypeError, ValueError):
    return int(MAX_TRADES_PER_DAY)


def resolve_max_trades_per_day(
  model_id: str,
  strat_max: int,
  *,
  model: dict | None = None,
  cfg: dict | None = None,
) -> int:
  """Effective daily slot cap: bridge override → Trade Model → remined strategy."""
  mid = str(model_id or "").strip()
  if cfg is None:
    try:
      from mt5_bridge.background import load_config
      cfg = load_config()
    except Exception:
      cfg = {}
  by_model = _cfg_int_map((cfg or {}).get("max_trades_per_day_by_model"))
  if mid and mid in by_model:
    return by_model[mid]
  if model is None and mid:
    try:
      from mt5_bridge.models import resolve_model
      model = resolve_model(mid)
    except Exception:
      model = None
  if model is not None:
    raw = model.get("max_trades_per_day")
    if raw is not None:
      try:
        return max(0, int(raw))
      except (TypeError, ValueError):
        pass
  try:
    return max(0, int(strat_max))
  except (TypeError, ValueError):
    return int(MAX_TRADES_PER_DAY)


def journal_day_trade_count(
  bridge_dir: Path,
  broker_day: date,
  *,
  model_id: str | None = None,
) -> int:
  """Count auto OPEN/CLOSED journal rows for one broker day (and optional model)."""
  day_n = 0
  mid = str(model_id) if model_id else None
  for trade in load_trades(bridge_dir):
    if trade_mode(trade) != "auto":
      continue
    if mid and str(trade.get("model_id") or "") != mid:
      continue
    status = str(trade.get("status") or "").upper()
    if status not in ("OPEN", "CLOSED"):
      continue
    entry_raw = trade.get("entry_time") or trade.get("bar_time") or trade.get("updated_at")
    if not entry_raw:
      continue
    try:
      raw = str(entry_raw).strip().replace(".", "-")
      if "T" in raw:
        et = utc_to_broker_time(pd.Timestamp(raw))
      else:
        et = utc_to_broker_time(parse_broker_time(raw[:16]))
      if et.date() == broker_day:
        day_n += 1
    except Exception:
      continue
  return day_n
