"""BUG-10/11: EA source contracts for orphan magics + per-slot live manage."""
from __future__ import annotations

from pathlib import Path

TRADE = Path(__file__).resolve().parents[2]
LIVE_EA = TRADE / "mt5" / "Experts" / "ForgeBridgeLive.mq5"
SIM_EA = TRADE / "mt5" / "Experts" / "ForgeBridgeLiveSim.mq5"


def _magic_is_ours_body(src: str) -> str:
  i = src.find("bool MagicIsOurs(")
  assert i >= 0, "MagicIsOurs missing"
  return src[i : i + 450]


def test_magic_is_ours_includes_live_magic_span():
  for path in (LIVE_EA, SIM_EA):
    src = path.read_text(encoding="utf-8", errors="replace")
    body = _magic_is_ours_body(src)
    assert "LIVE_MAGIC_SPAN" in body or "base + " in body or "g_roster_base_magic" in body, path.name
    assert "15" in body, f"{path.name}: span size 15 expected"


def test_write_positions_uses_magic_is_ours():
  src = LIVE_EA.read_text(encoding="utf-8", errors="replace")
  i = src.find("bool WritePositionsJson()")
  chunk = src[i : i + 1200]
  assert "MagicIsOurs" in chunk, "WritePositionsJson must use MagicIsOurs (orphan visibility)"


def test_open_from_decision_saves_per_slot_exit_params():
  src = LIVE_EA.read_text(encoding="utf-8", errors="replace")
  i = src.find("bool OpenFromDecision(")
  chunk = src[i : i + 9000]
  assert "g_slot_max_hold[save_slot]" in chunk or "g_slot_max_hold[slot]" in chunk
  assert "g_slot_exit_mode" in chunk
  assert "g_slot_trail_act" in chunk
  assert "g_slot_risk" in chunk


def test_manage_open_restores_per_slot_params():
  src = LIVE_EA.read_text(encoding="utf-8", errors="replace")
  i = src.find("void ManageOpen()")
  chunk = src[i : i + 4000]
  assert "g_exit_mode = g_slot_exit_mode[s]" in chunk
  assert "Always restore this model's exit params" in chunk


def test_exit_mode_defaults_to_full_not_trail():
  for path in (LIVE_EA, SIM_EA):
    src = path.read_text(encoding="utf-8", errors="replace")
    assert "int ParseExitMode(" in src, path.name
    assert 'return 0;' in src[src.find("int ParseExitMode(") : src.find("int ParseExitMode(") + 900]
    assert "else g_exit_mode = 2" not in src, path.name
    assert 'string pat = "\\"" + key + "\\":"' in src, path.name
