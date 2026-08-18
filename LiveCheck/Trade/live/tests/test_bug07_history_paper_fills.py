"""BUG-07: Live EA HistoryFeed must never OrderSend (force paper fills like Sim)."""
from __future__ import annotations

from pathlib import Path

TRADE = Path(__file__).resolve().parents[2]
LIVE_EA = TRADE / "mt5" / "Experts" / "ForgeBridgeLive.mq5"
SIM_EA = TRADE / "mt5" / "Experts" / "ForgeBridgeLiveSim.mq5"


def test_live_ea_has_usepaperfills_forcing_history_feed():
  src = LIVE_EA.read_text(encoding="utf-8", errors="replace")
  assert "bool UsePaperFills()" in src, "Live EA missing UsePaperFills()"
  # HistoryFeed branch must force paper (never live OrderSend on historical bars)
  assert "BRIDGE_HISTORY_FEED" in src
  idx = src.find("bool UsePaperFills()")
  body = src[idx : idx + 250]
  assert "BRIDGE_HISTORY_FEED" in body
  assert "return true" in body


def test_live_history_paths_call_usepaperfills_not_raw_input():
  """Execution paths must gate on UsePaperFills(), not raw InpHistoryPaperFills."""
  src = LIVE_EA.read_text(encoding="utf-8", errors="replace")
  lines = src.splitlines()
  raw_uses = []
  in_usepaper = False
  for i, line in enumerate(lines, 1):
    if "bool UsePaperFills()" in line:
      in_usepaper = True
    if in_usepaper and line.strip() == "}":
      in_usepaper = False
      continue
    if in_usepaper:
      continue
    if "InpHistoryPaperFills" not in line:
      continue
    if "input bool" in line:
      continue
    if "UsePaperFills" in line:
      continue
    if "paper=" in line or "Comment" in line:
      continue
    raw_uses.append((i, line.strip()))
  assert raw_uses == [], f"HistoryFeed paths still use raw InpHistoryPaperFills: {raw_uses}"


def test_sim_ea_still_forces_history_paper():
  src = SIM_EA.read_text(encoding="utf-8", errors="replace")
  assert "bool UsePaperFills()" in src
  idx = src.find("bool UsePaperFills()")
  body = src[idx : idx + 250]
  assert "return true" in body
