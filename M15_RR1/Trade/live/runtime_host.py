"""Map Live package symbol/TF → lab desk (code host for remine)."""
from __future__ import annotations

from pathlib import Path

# LiveCheck/Trade/live → LiveCheck; Final_app/split_app/live → Final_app
APP_ROOT = Path(__file__).resolve().parents[2]
# Backward-compatible alias (older scripts import FINAL_APP).
FINAL_APP = APP_ROOT

# Live remine reuses lab desk Python stack (optimizer, BridgeEngine, features).
# Bridge files + trade_models stay under Trade/live — only code is hosted.
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


def _candidate_desk_paths(name: str) -> list[Path]:
  """Support both flat Final_app layout and LiveCheck Train/M5|M15 layout."""
  tf_folder = "M5" if name.endswith("M5") and not name.endswith("M15") else (
    "M15" if name.endswith("M15") else None
  )
  candidates = [
    APP_ROOT / name,
    APP_ROOT / "Train" / "M5" / name,
    APP_ROOT / "Train" / "M15" / name,
    APP_ROOT / "Train" / "cores" / "m15",
    APP_ROOT / "Train" / "cores" / "m5",
  ]
  if tf_folder:
    candidates.insert(0, APP_ROOT / "Train" / tf_folder / name)
  seen: set[str] = set()
  out: list[Path] = []
  for path in candidates:
    key = str(path)
    if key in seen:
      continue
    seen.add(key)
    out.append(path)
  return out


def resolve_host_desk(symbol: str, timeframe: str) -> Path:
  key = (normalize_symbol(symbol), normalize_timeframe(timeframe))
  name = HOST_DESKS.get(key)
  if not name:
    raise ValueError(
      f"No host desk for {key[0]} {key[1]}. "
      f"Supported: {sorted(HOST_DESKS)}"
    )
  tried: list[str] = []
  for desk in _candidate_desk_paths(name):
    tried.append(str(desk))
    if desk.is_dir() and (desk / "mt5_bridge" / "engine.py").exists():
      return desk
  raise FileNotFoundError(
    f"Host desk missing for {name}. Tried: {tried}"
  )


def host_desk_name(symbol: str, timeframe: str) -> str:
  return resolve_host_desk(symbol, timeframe).name
