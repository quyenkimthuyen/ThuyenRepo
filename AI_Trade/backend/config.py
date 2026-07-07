from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
LABELS_PATH = DATA_DIR / "labels" / "setups.json"
CANDLES_PATH = DATA_DIR / "eurusd_h1.csv"
SPLITS_PATH = ROOT / "config" / "splits.json"
STRATEGY_PATH = DATA_DIR / "strategies" / "latest.json"

PIP = 0.0001
