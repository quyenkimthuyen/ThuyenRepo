"""Replay remine must be as-of the bar's week, not wall-clock now."""
from __future__ import annotations

import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
if str(LIVE) not in sys.path:
  sys.path.insert(0, str(LIVE))

from runtime_host import resolve_host_desk  # noqa: E402


def test_host_remine_clips_bars_before_week_start():
  for symbol in ("EURUSD", "GBPUSD"):
    desk = resolve_host_desk(symbol, "M15")
    src = (desk / "mt5_bridge" / "engine.py").read_text(encoding="utf-8")
    assert "df_mine.index < week_start" in src, desk
    assert "fm_asof = FeatureMatrix" in src, desk
    assert "as_of=week_start" in src, desk
    assert "datetime.now" not in src[src.find("def _remine_week_strategy") : src.find("def _save_mt5_cache")]
