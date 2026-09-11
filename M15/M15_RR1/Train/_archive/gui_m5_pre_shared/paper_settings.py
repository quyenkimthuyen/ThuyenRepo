"""Compatibility helpers for persisted Paper service settings."""
from __future__ import annotations

from paper_service import load_config, save_config


def load_pm_config() -> dict:
  return load_config()


def save_ui_settings(
  *,
  use_learning: bool,
  kb_profile: str,
  kb_snapshot: int | str | None,
  spread_pips: float,
  slippage_pips: float,
  risk_pct: float = 1.0,
  poll_sec: float = 2.0,
  enabled: bool = True,
) -> None:
  """Persist Paper settings without coupling them to Streamlit session state."""
  save_config(
    enabled=enabled,
    use_learning=use_learning,
    kb_profile=kb_profile,
    kb_snapshot=kb_snapshot,
    spread_pips=spread_pips,
    slippage_pips=slippage_pips,
    risk_pct=risk_pct,
    poll_sec=poll_sec,
  )
