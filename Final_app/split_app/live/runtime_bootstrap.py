"""Bootstrap Final_app host desk imports + patch paths to Live results/bridge."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from live_config import BRIDGE_DIR, BRIDGE_SIM_DIR, LIVE_ROOT, RESULTS_DIR
from runtime_host import normalize_symbol, normalize_timeframe, resolve_host_desk
from shared.constants import LIVE_INSTANCE_ID, LIVE_MAGIC_BASE, LIVE_SIM_MAGIC_BASE

_BOOTSTRAPPED: dict[str, Any] = {}


def _purge_host_modules() -> None:
  """Drop previously imported desk modules so a different host can load cleanly."""
  drop_prefixes = (
    "mt5_bridge",
    "trade_model_kb_pin",
    "trade_model_schedule",
    "run_backtest",
    "optimizer",
    "strategy_miner",
    "knowledge_base",
    "kb_profiles",
    "config",
    "features",
    "data_loader",
  )
  # Keep live_config — only purge if it came from a desk
  for name in list(sys.modules):
    if name in ("live_config",):
      continue
    if name in drop_prefixes or any(name.startswith(p + ".") for p in drop_prefixes):
      del sys.modules[name]


def bootstrap_host(symbol: str, timeframe: str, *, force: bool = False) -> Path:
  """Insert host desk on sys.path and redirect REPORT/BRIDGE/MAGIC to Live."""
  symbol = normalize_symbol(symbol)
  timeframe = normalize_timeframe(timeframe)
  key = f"{symbol}|{timeframe}"
  if not force and _BOOTSTRAPPED.get("key") == key:
    return Path(_BOOTSTRAPPED["desk"])

  desk = resolve_host_desk(symbol, timeframe)
  if _BOOTSTRAPPED.get("key") and _BOOTSTRAPPED.get("key") != key:
    _purge_host_modules()

  # Live paths first for our thin modules; desk next for engine stack
  live_str = str(LIVE_ROOT)
  split_str = str(LIVE_ROOT.parent)
  desk_str = str(desk)
  for p in (desk_str, split_str, live_str):
    if p in sys.path:
      sys.path.remove(p)
  # Desk MUST be first so `import config` / mt5_bridge resolve to host desk.
  # Live modules are already imported before bootstrap (live_config, etc.).
  sys.path.insert(0, split_str)
  sys.path.insert(0, desk_str)

  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  (RESULTS_DIR / "trade_models").mkdir(parents=True, exist_ok=True)
  data_dir = RESULTS_DIR / "data"
  data_dir.mkdir(parents=True, exist_ok=True)

  import run_backtest  # noqa: WPS433

  run_backtest.REPORT_DIR = RESULTS_DIR

  import trade_model_kb_pin as kb_pin  # noqa: WPS433

  kb_pin.REPORT_DIR = RESULTS_DIR
  kb_pin.MODELS_DIR = RESULTS_DIR / "trade_models"

  import trade_model_schedule as sched  # noqa: WPS433

  sched.REPORT_DIR = RESULTS_DIR
  sched.MODELS_DIR = RESULTS_DIR / "trade_models"

  import mt5_bridge.models as models  # noqa: WPS433

  models.MODELS_PATH = RESULTS_DIR / "trade_models.json"
  models.ACTIVE_MODEL_PATH = RESULTS_DIR / "active_trade_model.json"

  import mt5_bridge.protocol as protocol  # noqa: WPS433

  protocol.ROOT = LIVE_ROOT
  protocol.BRIDGE_DIR = BRIDGE_DIR
  protocol.BRIDGE_SIM_DIR = BRIDGE_SIM_DIR
  protocol.CONFIG_PATH = RESULTS_DIR / "mt5_bridge_config.json"
  protocol.DEFAULT_MAGIC = int(LIVE_MAGIC_BASE)
  protocol.DEFAULT_SIM_MAGIC = int(LIVE_SIM_MAGIC_BASE)
  protocol.DEFAULT_TIMEFRAME = timeframe
  protocol.INSTANCE_ID = LIVE_INSTANCE_ID

  # Patch history_sync BEFORE importing engine/background (they snapshot MT5_CACHE_PATH).
  import mt5_bridge.history_sync as history_sync  # noqa: WPS433

  cache_path = data_dir / f"mt5_{symbol.lower()}_{timeframe.lower()}.parquet"
  history_sync.ROOT = LIVE_ROOT
  history_sync.DATA_DIR = data_dir
  history_sync.MT5_CACHE_PATH = cache_path
  history_sync.MT5_META_PATH = data_dir / f"mt5_{symbol.lower()}_{timeframe.lower()}_meta.json"
  history_sync.DATA_START_CONFIG_PATH = data_dir / "data_start.json"
  history_sync.BRIDGE_DIR = BRIDGE_DIR

  import mt5_bridge.engine as engine  # noqa: WPS433

  engine.MT5_CACHE_PATH = cache_path
  engine.MT5_CACHE = cache_path

  import mt5_bridge.background as background  # noqa: WPS433

  background.ROOT = LIVE_ROOT
  background.CONFIG_PATH = RESULTS_DIR / "mt5_bridge_config.json"
  background.PID_PATH = RESULTS_DIR / "mt5_bridge_service.pid"
  background.SERVICE_LOG = RESULTS_DIR / "mt5_bridge_service.log"
  background.SERVICE_SCRIPT = LIVE_ROOT / "scripts" / "mt5_bridge_service_live.py"
  background.BRIDGE_DIR = BRIDGE_DIR
  background.MT5_CACHE_PATH = cache_path


  _BOOTSTRAPPED.clear()
  _BOOTSTRAPPED.update({"key": key, "desk": str(desk), "symbol": symbol, "timeframe": timeframe})
  return desk


def bootstrap_info() -> dict[str, Any]:
  return dict(_BOOTSTRAPPED)
