"""Replay remine must be as-of the bar's week, not wall-clock now."""
from __future__ import annotations

import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
if str(LIVE) not in sys.path:
  sys.path.insert(0, str(LIVE))

from runtime_host import resolve_host_desk  # noqa: E402


def test_host_atr_stop_adds_one_spread():
  desk = resolve_host_desk("EURUSD", "M15")
  src = (desk / "execution.py").read_text(encoding="utf-8")
  fn = src[src.find("def atr_stop_distance") :]
  assert "spread_from_quote" in fn or "spread_price(spread_pips)" in fn
  assert "float(atr_mult) * float(atr)" in fn


def test_host_remine_clips_bars_before_week_start():
  for symbol in ("EURUSD", "GBPUSD"):
    desk = resolve_host_desk(symbol, "M15")
    src = (desk / "mt5_bridge" / "engine.py").read_text(encoding="utf-8")
    start = src.find("def _remine_week_strategy")
    end = src.find("def _week_cache_key")
    remine = src[start:end]
    assert remine, desk
    assert "as_of=week_start" in remine, desk
    assert "get_train_window_indices" in remine, desk
    assert "datetime.now" not in remine
