from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
MARKET_DIR = DATA_DIR / "market"
LABELS_DIR = DATA_DIR / "labels"
FRONTEND_DIR = ROOT / "frontend"

CANDLES_PATH = MARKET_DIR / "eurusd_h1.csv"
PERIODS_PATH = CONFIG_DIR / "periods.json"
STRATEGY_PATH = CONFIG_DIR / "strategy_rsi_ema_v1.json"
COSTS_PATH = CONFIG_DIR / "costs.json"
SETUPS_PATH = LABELS_DIR / "setups.json"

PIP = 0.0001


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
