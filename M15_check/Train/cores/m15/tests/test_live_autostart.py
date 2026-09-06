"""Live Windows logon autostart: Start registers a task, Stop removes it."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_boot_script_starts_mt5_app_and_worker():
  boot = (ROOT / "scripts" / "live_windows_boot.ps1").read_text(encoding="utf-8")
  assert "terminal64.exe" in boot
  assert "XM Global MT5" in boot
  assert "manage.ps1" in boot
  assert "Start $Desk" in boot
  assert "resume_live_worker.py" in boot
  assert "--desk $Desk" in boot


def test_resume_worker_skips_when_disabled():
  text = (ROOT / "scripts" / "resume_live_worker.py").read_text(encoding="utf-8")
  assert "apply_desk_env" in text
  assert "start_worker" in text
  assert 'enabled' in text
  assert "is_running" in text


def test_launcher_cmd_points_at_boot_script(tmp_path, monkeypatch):
  import gui.live_autostart as auto

  monkeypatch.setenv("TRAINAPP_ROOT", str(tmp_path))
  monkeypatch.setenv("TRAINAPP_DESK", "e21")
  (tmp_path / "scripts").mkdir()
  (tmp_path / "scripts" / "live_windows_boot.ps1").write_text("# boot\n", encoding="utf-8")
  text = auto.launcher_cmd_text(desk="e21", python_exe=r"C:\Python\python.exe")
  assert "live_windows_boot.ps1" in text
  assert "-Desk e21" in text
  assert r"C:\Python\python.exe" in text


def test_enable_writes_marker_when_task_register_ok(tmp_path, monkeypatch):
  import gui.live_autostart as auto

  monkeypatch.setenv("TRAINAPP_ROOT", str(tmp_path))
  monkeypatch.setenv("TRAINAPP_DESK", "e21")
  monkeypatch.setattr(auto.sys, "platform", "win32")
  (tmp_path / "scripts").mkdir()
  (tmp_path / "scripts" / "live_windows_boot.ps1").write_text("# boot\n", encoding="utf-8")
  monkeypatch.setattr(auto, "_run_powershell", lambda *_a, **_k: (0, "OK\n", ""))
  ok, name = auto.enable_live_autostart("e21")
  assert ok is True
  assert name == "TrainApp-Live-e21"
  assert auto.autostart_is_marked("e21")
  cmd = auto.launcher_cmd_path("e21")
  assert cmd.is_file()
  assert "-Desk e21" in cmd.read_text(encoding="ascii")


def test_disable_clears_marker(tmp_path, monkeypatch):
  import gui.live_autostart as auto

  monkeypatch.setenv("TRAINAPP_ROOT", str(tmp_path))
  monkeypatch.setenv("TRAINAPP_DESK", "e21")
  monkeypatch.setattr(auto.sys, "platform", "win32")
  auto.marker_path("e21").parent.mkdir(parents=True, exist_ok=True)
  auto.marker_path("e21").write_text("{}", encoding="utf-8")
  monkeypatch.setattr(auto, "_run_powershell", lambda *_a, **_k: (0, "OK\n", ""))
  ok, _name = auto.disable_live_autostart("e21")
  assert ok is True
  assert not auto.autostart_is_marked("e21")


def test_live_trade_and_bridge_hook_autostart():
  live = (ROOT / "gui" / "views" / "live_trade_dash.py").read_text(encoding="utf-8")
  bridge = (ROOT / "gui" / "views" / "mt5_bridge.py").read_text(encoding="utf-8")
  assert "enable_live_autostart" in live
  assert "disable_live_autostart" in live
  assert "enable_live_autostart" in bridge
  assert "disable_live_autostart" in bridge
