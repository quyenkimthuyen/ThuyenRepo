"""Per-book bridge paths — internal only; users think in models, not books."""
from __future__ import annotations

from pathlib import Path

from live_config import MT5_ROOT
from runtime_host import normalize_symbol, normalize_timeframe


def book_key(symbol: str | None, timeframe: str | None) -> str:
  sym = normalize_symbol(symbol)
  tf = normalize_timeframe(timeframe)
  return f"{sym}_{tf}".lower()


def bridge_subdir(symbol: str | None, timeframe: str | None, *, sim: bool = False) -> str:
  """EA InpBridgeSubdir value, e.g. bridge_live_eurusd_m5."""
  prefix = "bridge_sim_live" if sim else "bridge_live"
  return f"{prefix}_{book_key(symbol, timeframe)}"


def bridge_dir(symbol: str | None, timeframe: str | None, *, sim: bool = False) -> Path:
  return MT5_ROOT / bridge_subdir(symbol, timeframe, sim=sim)


def group_models_by_book(rows: list[dict]) -> dict[tuple[str, str], list[dict]]:
  """Group roster rows by (symbol, timeframe)."""
  groups: dict[tuple[str, str], list[dict]] = {}
  for r in rows:
    sym = normalize_symbol(r.get("symbol"))
    tf = normalize_timeframe(r.get("timeframe"))
    if not sym or not tf:
      continue
    groups.setdefault((sym, tf), []).append(r)
  return dict(sorted(groups.items()))
