"""Per-book bridge paths — internal only; users think in models, not books."""
from __future__ import annotations

from pathlib import Path

from live_config import LIVE_BRIDGE_SIM_SUBDIR, LIVE_BRIDGE_SUBDIR, MT5_ROOT
from runtime_host import normalize_symbol, normalize_timeframe

_LEGACY_LIVE = "bridge_live"
_LEGACY_SIM = "bridge_sim_live"


def live_bridge_prefix(*, sim: bool = False) -> str:
  return LIVE_BRIDGE_SIM_SUBDIR if sim else LIVE_BRIDGE_SUBDIR


def is_bridge_dir_name(name: str, *, sim: bool | None = None) -> bool:
  """Match this clone's live/sim folders, plus legacy bridge_live_* names."""
  n = str(name or "")

  def match(prefix: str) -> bool:
    return bool(prefix) and (n == prefix or n.startswith(f"{prefix}_"))

  sim_ok = match(LIVE_BRIDGE_SIM_SUBDIR) or match(_LEGACY_SIM)
  live_ok = (match(LIVE_BRIDGE_SUBDIR) or match(_LEGACY_LIVE)) and not sim_ok
  if sim is True:
    return sim_ok
  if sim is False:
    return live_ok
  return live_ok or sim_ok


def book_key(symbol: str | None, timeframe: str | None) -> str:
  sym = normalize_symbol(symbol)
  tf = normalize_timeframe(timeframe)
  return f"{sym}_{tf}".lower()


def bridge_subdir(symbol: str | None, timeframe: str | None, *, sim: bool = False) -> str:
  """EA InpBridgeSubdir value, e.g. bridge_rr1_eurusd_m15."""
  return f"{live_bridge_prefix(sim=sim)}_{book_key(symbol, timeframe)}"


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
