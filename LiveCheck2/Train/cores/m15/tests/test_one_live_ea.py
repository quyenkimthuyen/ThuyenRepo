"""One Live EA: history test shares the Live bridge folder and pipeline."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "runtime"


def _live_eas() -> list[Path]:
  return [
    RUNTIME / "e21" / "mt5" / "Experts" / "ForgeBridgeM15E21.mq5",
    RUNTIME / "g23" / "mt5" / "Experts" / "ForgeBridgeM15G23.mq5",
  ]


def test_live_ea_v125_reliability_contract():
  """ForgeBridge desk EA v1.25 — parallel wait, late recovery, ea_sync."""
  for path in _live_eas():
    text = path.read_text(encoding="utf-8")
    assert '#property version   "1.25"' in text, path
    assert "InpDecisionWaitMs = 60000" in text, path
    assert "InpShowComment" in text, path
    assert "g_late_pending" in text, path
    assert "TryRecoverLateDecisions()" in text, path
    assert "TryReadDecisionForBar(" in text, path
    assert 'BridgePath("ea_sync.json")' in text, path
    assert "WaitHistoryDecisionsForBar(" in text, path
    assert "g_model_risk_pct" in text, path
    assert "int live_wait = (int)MathMax(InpDecisionWaitMs" in text, path
    assert "PublishBarSyncBegin(" in text, path


def test_live_ea_retries_late_decisions_on_same_bar():
  """App remine can land after wait budget; EA keeps polling via late_pending."""
  for path in _live_eas():
    text = path.read_text(encoding="utf-8")
    on_tick = text[text.find("void OnTick()") :]
    assert "TryRecoverLateDecisions();" in on_tick, path
    assert "g_late_pending = true" in text, path
    assert "g_late_pending = false" in text, path


def test_cycle_uses_loss_guard_on_history_replay():
  text = (ROOT / "cores" / "m15" / "mt5_bridge" / "background.py").read_text(encoding="utf-8")
  start = text.find("def _cycle(")
  nxt = text.find("\ndef _worker(")
  body = text[start:nxt]
  assert "check_and_apply_loss_guard" in body
  assert "if not is_sim:\n    trip = check_and_apply_loss_guard" not in body.replace("\r", "")
  assert "load_config() if not is_sim else {}" not in body
  assert "eng.decide_for_bar(bar)" in body


def test_decide_for_bar_has_no_sim_branch():
  text = (ROOT / "cores" / "m15" / "mt5_bridge" / "engine.py").read_text(encoding="utf-8")
  start = text.find("  def decide_for_bar(")
  nxt = text.find("\n  def ", start + 10)
  body = text[start:nxt]
  assert "is_sim" not in body
  assert "history_replay" not in body
  assert "simulate" not in body.lower() or "share this path" in body.lower()


def test_protocol_aliases_sim_dir_to_live():
  text = (ROOT / "cores" / "m15" / "mt5_bridge" / "protocol.py").read_text(encoding="utf-8")
  assert "BRIDGE_SIM_DIR = BRIDGE_DIR" in text
  assert "def history_replay_active" in text
  assert "return resolve_live_bridge_dir()" in text


def test_deploy_script_is_live_only():
  text = (ROOT / "scripts" / "deploy_xm_forgebridge.ps1").read_text(encoding="utf-8-sig")
  assert "One Live EA" in text
  assert "$Mode = \"Live\"" in text
  assert "history test uses sim_control.json" in text
  assert "$EaNameSim" not in text
  assert "ForgeBridge*Sim" not in text


def test_sim_ea_sources_removed():
  for desk in ("e21", "g23"):
    experts = RUNTIME / desk / "mt5" / "Experts"
    sim_files = list(experts.glob("*Sim.mq5"))
    assert sim_files == [], f"Sim EA still present under {experts}: {sim_files}"


def test_start_sim_worker_uses_live_worker_not_sim_service():
  text = (ROOT / "cores" / "m15" / "mt5_bridge" / "background.py").read_text(encoding="utf-8")
  start = text.find("def start_sim_worker")
  nxt = text.find("\ndef pause_sim_worker")
  assert start >= 0 and nxt > start
  body = text[start:nxt]
  assert "Popen" not in body
  assert "SIM_SERVICE_SCRIPT" not in body
  assert "run_history_feed_control" in body
  assert "BRIDGE_DIR" in body
  assert "DEFAULT_MAGIC" in body


def test_only_m15_desks_are_registered():
  desks = sorted(p.stem for p in (ROOT / "desks").glob("*.yaml"))
  assert desks == ["e21", "g23"]


def test_render_forgebridge_template_exists():
  tpl = ROOT / "mt5" / "template" / "ForgeBridgeDesk.mq5.template"
  assert tpl.is_file()
  assert "@@EA_STEM@@" in tpl.read_text(encoding="utf-8")
