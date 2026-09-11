"""Live Windows logon autostart: Start registers a task, Stop removes it."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


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


def test_launcher_cmd_is_relative_to_cmd_file(tmp_path, monkeypatch):
  import gui.live_autostart as auto

  monkeypatch.setenv("TRAINAPP_ROOT", str(tmp_path))
  monkeypatch.setenv("TRAINAPP_DESK", "e21")
  (tmp_path / "scripts").mkdir()
  (tmp_path / "scripts" / "live_windows_boot.ps1").write_text("# boot\n", encoding="utf-8")
  text = auto.launcher_cmd_text(desk="e21", python_exe=r"C:\Python\python.exe")
  assert "live_windows_boot.ps1" in text
  assert "-Desk e21" in text
  assert "%~dp0" in text
  assert r"C:\Python\python.exe" not in text
  assert "C:\\Work" not in text


def test_task_name_unique_per_clone_folder(tmp_path, monkeypatch):
  import gui.live_autostart as auto

  a = tmp_path / "M15_clone1" / "Train"
  b = tmp_path / "M15_clone2" / "Train"
  a.mkdir(parents=True)
  b.mkdir(parents=True)
  monkeypatch.setenv("TRAINAPP_ROOT", str(a))
  n1 = auto.task_name("e21")
  monkeypatch.setenv("TRAINAPP_ROOT", str(b))
  n2 = auto.task_name("e21")
  assert n1 != n2
  assert n1.startswith("TrainApp-Live-M15_clone1-")
  assert n1.endswith("-e21")
  assert n2.startswith("TrainApp-Live-M15_clone2-")
  assert n2.endswith("-e21")
  assert n1 != "TrainApp-Live-e21"


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
  assert name == auto.task_name("e21")
  assert name.endswith("-e21")
  assert auto.autostart_is_marked("e21")
  cmd = auto.launcher_cmd_path("e21")
  assert cmd.is_file()
  body = cmd.read_text(encoding="ascii")
  assert "-Desk e21" in body
  assert "%~dp0" in body


def test_ensure_rewrites_stale_absolute_cmd(tmp_path, monkeypatch):
  import gui.live_autostart as auto

  monkeypatch.setenv("TRAINAPP_ROOT", str(tmp_path))
  monkeypatch.setenv("TRAINAPP_DESK", "e21")
  results = tmp_path / "runtime" / "e21" / "results"
  results.mkdir(parents=True)
  stale = results / "live_windows_boot.cmd"
  stale.write_text(
    "@echo off\r\n"
    "powershell.exe -File "
    '"C:\\Work\\ThuyenRepo\\M15_clone1\\Train\\scripts\\live_windows_boot.ps1" '
    "-Desk e21\r\n",
    encoding="ascii",
  )
  (tmp_path / "scripts").mkdir()
  (tmp_path / "scripts" / "live_windows_boot.ps1").write_text("# boot\n", encoding="utf-8")
  auto.ensure_live_autostart_after_move("e21")
  text = stale.read_text(encoding="ascii")
  assert "%~dp0" in text
  assert "M15_clone1" not in text
  assert "-Desk e21" in text


def test_heal_autostart_launchers_rewrites_cmd(tmp_path):
  import importlib.util

  heal_py = ROOT.parent / "scripts" / "heal_after_move.py"
  spec = importlib.util.spec_from_file_location("heal_after_move", heal_py)
  mod = importlib.util.module_from_spec(spec)
  assert spec.loader is not None
  spec.loader.exec_module(mod)
  results = tmp_path / "Train" / "runtime" / "g23" / "results"
  results.mkdir(parents=True)
  cmd = results / "live_windows_boot.cmd"
  cmd.write_text(
    'powershell.exe -File "C:\\Work\\ThuyenRepo\\M15_clone1\\Train\\scripts\\live_windows_boot.ps1" -Desk g23\r\n',
    encoding="ascii",
  )
  n = mod.heal_autostart_launchers(tmp_path)
  assert n == 1
  text = cmd.read_text(encoding="ascii")
  assert "%~dp0" in text
  assert "M15_clone1" not in text
  assert "-Desk g23" in text


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
  assert "live_trade_dash.render()" in bridge
