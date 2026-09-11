"""TrainApp2 root deploy script must exist and be desk-aware."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEPLOY = ROOT / "scripts" / "deploy_xm_forgebridge.ps1"


def test_root_deploy_script_exists_and_is_desk_aware():
  assert DEPLOY.is_file(), DEPLOY
  text = DEPLOY.read_text(encoding="utf-8-sig")
  assert "[string]$Desk" in text
  assert "desks\\$Desk.yaml" in text or 'desks\\$Desk.yaml' in text
  assert "TRAINAPP_RUNTIME" in text
  assert "Test-PathUnder" in text
  assert "ForgeBridge$InstanceId" in text
  assert "cores\\$CoreName" in text or "cores\\$CoreName" in text
  assert "scripts\\mt5_bridge_service.py" in text
  assert "function Restart-BridgeService" in text
  assert "Start-Process" in text
  assert "ConvertTo-QuotedArgumentLine" in text
  assert "Invoke-CimMethod" not in text
  assert "pythonw.exe" not in text
  assert '"enabled": true' in text
  restart = text.split("function Restart-BridgeService", 1)[1].split("Write-Step", 1)[0]
  assert "Win32_Process.Create" not in restart
  assert "enabled = $false" not in restart
  assert "--bridge-dir" in restart
