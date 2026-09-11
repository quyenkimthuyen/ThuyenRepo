"""Live Windows autostart: per-clone task names and move rebind."""
from __future__ import annotations

import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(LIVE.parent))


def test_clone_task_suffix_differs_for_different_folders(tmp_path):
  from windows_autostart import clone_task_suffix

  a = tmp_path / "M15_clone1"
  b = tmp_path / "M15_clone2"
  a.mkdir()
  b.mkdir()
  s1 = clone_task_suffix(a)
  s2 = clone_task_suffix(b)
  assert s1 != s2
  assert s1.startswith("M15_clone1-")
  assert s2.startswith("M15_clone2-")
  assert len(s1.split("-")[-1]) == 8


def test_task_name_is_per_clone_not_global():
  from windows_autostart import LEGACY_TASK_NAME, task_name

  name = task_name()
  assert name.startswith("EdgeMinerLive2Boot-")
  assert name != LEGACY_TASK_NAME
  assert "EdgeMinerLive2Boot-" in name


def test_ensure_skips_when_not_enabled(tmp_path, monkeypatch):
  import windows_autostart as auto

  monkeypatch.setattr(auto, "PREFS_PATH", tmp_path / "autostart_prefs.json")
  monkeypatch.setattr(auto, "is_windows", lambda: True)
  (tmp_path / "autostart_prefs.json").write_text(
    '{"enabled": false, "start_mt5": true, "start_app": true}\n',
    encoding="utf-8",
  )
  out = auto.ensure_autostart_after_move()
  assert out.get("skipped") is True
  assert out.get("reason") == "not_enabled"


def test_ensure_skips_off_windows(tmp_path, monkeypatch):
  import windows_autostart as auto

  monkeypatch.setattr(auto, "PREFS_PATH", tmp_path / "autostart_prefs.json")
  monkeypatch.setattr(auto, "is_windows", lambda: False)
  (tmp_path / "autostart_prefs.json").write_text(
    '{"enabled": true}\n',
    encoding="utf-8",
  )
  out = auto.ensure_autostart_after_move()
  assert out.get("skipped") is True
  assert out.get("reason") == "not_windows"


def test_install_script_has_ensure_and_taskname():
  text = (LIVE / "scripts" / "install_autostart_windows.ps1").read_text(encoding="utf-8")
  assert "Ensure" in text
  assert "TaskName" in text
  assert "Get-CloneTaskSuffix" in text
  assert "EdgeMinerLive2Boot-" in text


def test_boot_script_has_no_hardcoded_work_venv():
  text = (LIVE / "scripts" / "boot_autostart_windows.ps1").read_text(encoding="utf-8")
  assert r"C:\Work\ThuyenRepo\EdgeMinerM15B5" not in text
  assert ".venv\\Scripts\\python.exe" in text
