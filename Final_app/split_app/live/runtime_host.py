"""Map Live package symbol/TF → Final_app lab desk (code host for remine)."""
from __future__ import annotations

from pathlib import Path

FINAL_APP = Path(__file__).resolve().parents[2]

# Live remine reuses lab desk Python stack (optimizer, BridgeEngine, features).
# Bridge files + trade_models stay under split_app/live — only code is hosted.
HOST_DESKS: dict[tuple[str, str], str] = {
  ("EURUSD", "M5"): "EdgeMinerEURUSDM5",
  ("GBPUSD", "M5"): "EdgeMinerGBPUSDM5",
  ("EURUSD", "M15"): "EdgeMinerEURUSDM15",
  ("GBPUSD", "M15"): "EdgeMinerGBPUSDM15",
}


def normalize_symbol(symbol: str | None) -> str:
  s = (symbol or "").strip().upper().replace(".", "")
  # Strip common broker suffixes (EURUSDm, EURUSD.r, …)
  for base in ("EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "XAUUSD"):
    if s.startswith(base):
      return base
  return s


def normalize_timeframe(tf: str | None) -> str:
  t = (tf or "").strip().upper()
  if t in ("5", "PERIOD_M5"):
    return "M5"
  if t in ("15", "PERIOD_M15"):
    return "M15"
  if t.startswith("M") and t[1:].isdigit():
    return t
  return t


def resolve_host_desk(symbol: str, timeframe: str) -> Path:
  key = (normalize_symbol(symbol), normalize_timeframe(timeframe))
  name = HOST_DESKS.get(key)
  if not name:
    raise ValueError(
      f"No Final_app host desk for {key[0]} {key[1]}. "
      f"Supported: {sorted(HOST_DESKS)}"
    )
  desk = FINAL_APP / name
  if not desk.is_dir():
    raise FileNotFoundError(f"Host desk missing: {desk}")
  if not (desk / "mt5_bridge" / "engine.py").exists():
    raise FileNotFoundError(f"Host desk incomplete (no mt5_bridge/engine.py): {desk}")
  return desk


def host_desk_name(symbol: str, timeframe: str) -> str:
  return resolve_host_desk(symbol, timeframe).name
