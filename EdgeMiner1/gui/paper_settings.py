"""Paper Monitor UI settings — persist across tabs / reload."""
from __future__ import annotations

import json
from pathlib import Path

from run_backtest import REPORT_DIR

CONFIG_PATH = REPORT_DIR / "paper_monitor_config.json"


def load_pm_config() -> dict:
  if not CONFIG_PATH.exists():
    return {
      "enabled": False,
      "interval_minutes": 0,
      "use_learning": False,
      "kb_profile": "default",
      "kb_snapshot": None,
      "spread_pips": 1.0,
      "slippage_pips": 0.3,
    }
  try:
    with open(CONFIG_PATH, encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return {
      "enabled": False,
      "interval_minutes": 0,
      "use_learning": False,
      "kb_profile": "default",
      "kb_snapshot": None,
      "spread_pips": 1.0,
      "slippage_pips": 0.3,
    }


def save_ui_settings(
  *,
  use_learning: bool,
  kb_profile: str,
  kb_snapshot: int | str | None,
  spread_pips: float,
  slippage_pips: float,
  interval_minutes: int,
) -> None:
  """Lưu setting Paper Monitor — giữ khi chuyển tab / reload trang."""
  cfg = load_pm_config()
  cfg.update({
    "use_learning": use_learning,
    "kb_profile": kb_profile,
    "kb_snapshot": kb_snapshot,
    "spread_pips": spread_pips,
    "slippage_pips": slippage_pips,
    "interval_minutes": interval_minutes,
    "enabled": interval_minutes > 0,
  })
  REPORT_DIR.mkdir(parents=True, exist_ok=True)
  tmp = CONFIG_PATH.with_suffix(".tmp")
  with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
  tmp.replace(CONFIG_PATH)
