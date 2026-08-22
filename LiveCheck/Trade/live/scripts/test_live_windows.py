#!/usr/bin/env python3
"""Windows Live-mode E2E checks — plumbing through desk/UI readiness.

Default run is non-destructive for an already-running Live session:
  - does NOT start/stop bridge workers
  - does NOT attach/restart MT5 (use --with-deploy for that)
  - flatten / kill-switch are exercised then restored

Usage (from split_app or live):
  python live/scripts/test_live_windows.py
  python live/scripts/test_live_windows.py --with-deploy
  python live/scripts/test_live_windows.py --with-bridge-once
  powershell -File live/scripts/test_live_windows.ps1
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import platform
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))
sys.path.insert(0, str(LIVE / "gui"))  # theme.py lives beside app.py

PASSED = 0
FAILED = 0
SKIPPED = 0
RESULTS: list[tuple[str, str, str]] = []


def _record(name: str, status: str, detail: str = "") -> None:
  global PASSED, FAILED, SKIPPED
  RESULTS.append((name, status, detail))
  if status == "OK":
    PASSED += 1
    print(f"  OK   {name}" + (f" — {detail}" if detail else ""))
  elif status == "SKIP":
    SKIPPED += 1
    print(f"  SKIP {name}" + (f" — {detail}" if detail else ""))
  else:
    FAILED += 1
    print(f"  FAIL {name}: {detail}")


def check(name: str, fn: Callable[[], str | None]) -> None:
  """Run check; fn returns optional detail on success, raises on failure."""
  try:
    detail = fn() or ""
    _record(name, "OK", detail)
  except Exception as exc:  # noqa: BLE001 — collect all failures
    _record(name, "FAIL", str(exc))


def skip(name: str, reason: str) -> None:
  _record(name, "SKIP", reason)


# ── checks ──────────────────────────────────────────────────────────────────


def check_windows() -> str:
  if not platform.system().lower().startswith("win"):
    raise AssertionError(f"not Windows ({platform.system()})")
  return platform.platform()


def check_constants() -> str:
  from shared.constants import (
    LIVE_APP_PORT,
    LIVE_BRIDGE_PORT,
    LIVE_INSTANCE_ID,
    LIVE_MAGIC_BASE,
    LIVE_SIM_MAGIC_BASE,
  )
  assert LIVE_APP_PORT == 8601, LIVE_APP_PORT
  assert LIVE_BRIDGE_PORT == 9601, LIVE_BRIDGE_PORT
  assert LIVE_MAGIC_BASE == 20263001, LIVE_MAGIC_BASE
  assert LIVE_SIM_MAGIC_BASE == 20264001, LIVE_SIM_MAGIC_BASE
  assert LIVE_INSTANCE_ID == "LIVE1"
  return f"port={LIVE_APP_PORT} magic={LIVE_MAGIC_BASE}"


def check_paths() -> str:
  from live_config import BRIDGE_DIR, LIVE_ROOT, MT5_ROOT, RESULTS_DIR, ROSTER_PATH
  assert LIVE_ROOT == LIVE, LIVE_ROOT
  assert MT5_ROOT.is_dir(), MT5_ROOT
  assert (MT5_ROOT / "Experts" / "ForgeBridgeLive.mq5").is_file()
  assert (LIVE / "gui" / "app.py").is_file()
  assert (LIVE / "gui" / "theme.py").is_file()
  assert (LIVE / "scripts" / "deploy_live_ea.ps1").is_file()
  assert (LIVE / "scripts" / "run_app_windows.ps1").is_file()
  assert (LIVE / ".streamlit" / "config.toml").is_file()
  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  return f"roster={ROSTER_PATH.name} bridge={BRIDGE_DIR.name}"


def check_streamlit_theme_config() -> str:
  cfg = (LIVE / ".streamlit" / "config.toml").read_text(encoding="utf-8")
  assert 'base = "light"' in cfg or "base = 'light'" in cfg
  assert "backgroundColor" in cfg
  assert "primaryColor" in cfg
  return "light base"


def check_theme_helpers() -> str:
  from theme import pill, r_class, signal_badge
  assert "pill-ok" in pill("Running", "ok")
  assert r_class(1.2) == "pos"
  assert r_class(-0.5) == "neg"
  assert r_class(0) == "neutral"
  assert signal_badge("flat") == "FLAT"
  assert signal_badge("long") == "LONG"
  assert signal_badge("short") == "SHORT"
  css = Path(LIVE / "gui" / "theme.py").read_text(encoding="utf-8")
  for needle in (
    "signal-panel", "session-panel", "stat-cell", "decision-flat", "--desk-text",
    "replay-prog", "replay-prog-fill",
  ):
    assert needle in css, needle
  assert "stProgressBarTrack" not in css
  from theme import progress_bar_html
  html = progress_bar_html(24.4)
  assert "width:24.4%" in html
  assert "replay-prog-fill" in html
  return "signal/session CSS present"


def check_app_ast() -> str:
  src = (LIVE / "gui" / "app.py").read_text(encoding="utf-8")
  ast.parse(src)
  assert "render_live_desk" in src
  assert "EA Simulate (MT5)" in src
  assert "Live-like (app)" not in src
  assert "Lab parity" not in src
  assert "signal-panel" in src
  assert "session-panel" in src
  assert "inject_theme" in src
  assert "st.progress" not in src
  assert "progress_bar_html" in src
  assert "st_autorefresh" not in src
  assert "desk_refresh_now" in src
  assert "_run_live_now_tick" in src
  assert "LIVE_SECTIONS" in src
  assert "_render_live_control" in src
  assert "format_func=_period_label" in src
  assert "_live_stats_period_seeded" not in src
  assert "_live_desk_section_seeded" not in src
  assert "restore_widget_choice" in src
  return "app.py parse + Live desk markup"


def check_deploy_ps1_parse() -> str:
  """Regression: UTF-8 fancy quotes/dashes must not break PS 5.1 parse."""
  script = LIVE / "scripts" / "deploy_live_ea.ps1"
  raw = script.read_bytes()
  if not raw.startswith(b"\xef\xbb\xbf"):
    # Allow if file is pure ASCII; otherwise require BOM for WinPS
    try:
      raw.decode("ascii")
    except UnicodeDecodeError as exc:
      raise AssertionError("deploy_live_ea.ps1 should be UTF-8 with BOM on Windows") from exc
  helper = Path(tempfile.gettempdir()) / "live_e2e_parse_deploy.ps1"
  helper.write_text(
    "\n".join([
      "$e = $null; $t = $null",
      f"$p = '{script}'",
      "[void][System.Management.Automation.Language.Parser]::ParseFile($p, [ref]$t, [ref]$e)",
      "if ($e -and $e.Count -gt 0) {",
      "  Write-Output ('PARSE_FAIL:' + $e[0].Message + '@' + $e[0].Extent.StartLineNumber)",
      "  exit 2",
      "}",
      "Write-Output 'PARSE_OK'",
      "exit 0",
    ]) + "\n",
    encoding="utf-8",
  )
  r = subprocess.run(
    ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(helper)],
    capture_output=True,
    text=True,
    timeout=60,
  )
  out = (r.stdout or "").strip()
  if r.returncode != 0 or "PARSE_OK" not in out:
    raise AssertionError(out or r.stderr or f"exit={r.returncode}")
  # Spot-check identity needles
  txt = script.read_text(encoding="utf-8-sig")
  for needle in ("ForgeBridgeLive", "FromRoster", "20263001", "SkipBridgeService"):
    assert needle in txt, needle
  return "PARSE_OK"


def check_roster_and_books() -> str:
  from deploy_ea import enabled_books
  from package_store import list_installed, load_roster

  installed = list_installed()
  roster = load_roster()
  models = roster.get("models") or []
  enabled = [m for m in models if m.get("enabled")]
  books = enabled_books()
  if not installed:
    raise AssertionError("no installed packages — import a .tmpkg first")
  if not enabled:
    raise AssertionError("no enabled roster models — turn On in Models UI")
  assert books, "enabled_books() empty despite enabled models"
  for b in books:
    assert b.get("symbol") and b.get("timeframe"), b
    assert b.get("bridge_subdir", "").startswith("bridge_live_"), b
  return f"installed={len(installed)} enabled={len(enabled)} books={len(books)}"


def check_sync_roster() -> str:
  r = subprocess.run(
    [sys.executable, str(LIVE / "sync_bridge_roster.py")],
    cwd=str(LIVE),
    capture_output=True,
    text=True,
    timeout=120,
  )
  if r.returncode != 0:
    raise AssertionError((r.stderr or r.stdout or f"exit={r.returncode}")[-500:])
  from deploy_ea import enabled_books
  books = enabled_books()
  written = 0
  for b in books:
    p = Path(b["bridge_dir"]) / "models.json"
    if p.is_file():
      written += 1
      data = json.loads(p.read_text(encoding="utf-8"))
      assert isinstance(data.get("models"), list), data
  assert written >= 1, "no models.json written"
  return f"models.json books={written}"


def check_replay_modes() -> str:
  from replay_control import normalize_replay_mode

  assert normalize_replay_mode("ea") == "ea"
  assert normalize_replay_mode("history_feed") == "ea"
  assert normalize_replay_mode("live_like") == "live_like"
  assert normalize_replay_mode("paper") == "live_like"
  assert normalize_replay_mode("inline") == "live_like"
  assert normalize_replay_mode("parity") == "parity"
  from replay_control import _assert_live_feed_bridge
  from pathlib import Path
  try:
    _assert_live_feed_bridge(Path("bridge_sim_live_eurusd_m15"))
    raise AssertionError("sim dir should be refused")
  except RuntimeError:
    pass
  p = _assert_live_feed_bridge(Path("C:/x/bridge_live_eurusd_m15"))
  assert p.name.startswith("bridge_live")
  from replay_control import history_feed_active
  idle_dir = Path(tempfile.mkdtemp(prefix="bridge_live_idle_"))
  try:
    (idle_dir / "sim_control.json").write_text(
      json.dumps({"enabled": True, "ea_status": "idle", "bars_done": 0, "bars_total": 0}),
      encoding="utf-8",
    )
    assert history_feed_active(idle_dir) is False, "idle leftover must not lock Start"
    (idle_dir / "sim_control.json").write_text(
      json.dumps({"enabled": True, "ea_status": "pending"}),
      encoding="utf-8",
    )
    assert history_feed_active(idle_dir) is True
  finally:
    import shutil
    shutil.rmtree(idle_dir, ignore_errors=True)
  mq5 = (SPLIT / "mt5" / "Experts" / "ForgeBridgeLive.mq5").read_text(encoding="utf-8")
  assert '#property version   "1.25"' in mq5
  assert "WaitHistoryDecisionsForBar" in mq5
  assert "g_sim_delay_ms + 6000" not in mq5
  assert "left open like Live" in mq5
  assert "ReadSimControlFile() && g_sim_enabled" in mq5
  from replay_control import live_ea_needs_history_feed_binary
  assert callable(live_ea_needs_history_feed_binary)
  return "ea history-feed on live bridge"


def check_desk_snapshot() -> str:
  from desk_snapshot import desk_snapshot

  snap = desk_snapshot(sim=False)
  required = [
    "health", "health_tone", "decision", "today", "journal",
    "bridge_running", "ea_online", "n_open", "kill_switch",
    "models", "updated_at", "subtitle",
  ]
  missing = [k for k in required if k not in snap]
  if missing:
    raise AssertionError(f"missing keys: {missing}")
  dec = snap["decision"] or {}
  assert "action" in dec and "tone" in dec, dec
  assert dec["tone"] in ("long", "short", "flat", "unknown"), dec["tone"]
  today = snap["today"] or {}
  assert "total_r" in today and "n" in today, today
  journal = snap["journal"] or {}
  assert "total_r" in journal, journal
  return (
    f"action={dec.get('action')} tone={dec.get('tone')} "
    f"running={snap['bridge_running']} models={len(snap.get('models') or [])}"
  )


def check_live_health() -> str:
  from live_health import build_live_health

  detail = build_live_health(sim=False)
  assert isinstance(detail, dict), detail
  assert "overall" in detail, detail.keys()
  assert "books" in detail, detail.keys()
  return f"overall={detail.get('overall')} books={len(detail.get('books') or [])}"


def check_journal() -> str:
  from journal_view import journal_summary, load_trades

  summary = journal_summary(period="today")
  trades = load_trades()
  assert isinstance(summary, dict)
  assert "total_r" in summary or "n_closed" in summary or "n" in summary, summary
  return f"summary_keys={sorted(summary)[:6]} trades={len(trades)}"


def check_bridge_status() -> str:
  from bridge_control import status

  st = status()
  assert "running" in st, st
  return f"running={st.get('running')} workers={st.get('n_workers') or len(st.get('workers') or [])}"


def check_ea_coverage() -> str:
  from deploy_ea import roster_ea_coverage

  cov = roster_ea_coverage(stale_after=180.0)
  assert "n_books" in cov and "books" in cov, cov
  return (
    f"books={cov['n_books']} online={cov['n_online']} "
    f"all_online={cov['all_online']}"
  )


def check_safety_roundtrip() -> str:
  from live_config import BRIDGE_DIR
  from safety import (
    arm_kill_switch,
    disarm_kill_switch,
    is_kill_switch_armed,
    write_flatten_command,
  )

  was_armed = is_kill_switch_armed()
  try:
    flat = write_flatten_command(reason="e2e_windows_flatten")
    cmd_path = BRIDGE_DIR / "command.json"
    assert cmd_path.is_file(), cmd_path
    assert flat.get("action") == "FLAT", flat
    data = json.loads(cmd_path.read_text(encoding="utf-8"))
    assert str(data.get("action") or "").upper() == "FLAT", data

    arm_kill_switch(reason="e2e_windows_kill", flatten=True)
    assert is_kill_switch_armed()
    from bridge_control import prepare_runtime
    blocked = False
    try:
      prepare_runtime(require_chart=False)
    except RuntimeError:
      blocked = True
    assert blocked, "prepare_runtime should refuse when kill armed"
  finally:
    if was_armed:
      arm_kill_switch(reason="e2e_restore", flatten=False)
    else:
      disarm_kill_switch()
    assert is_kill_switch_armed() == was_armed
  return f"restored_armed={was_armed}"


def check_prepare_runtime() -> str:
  from safety import is_kill_switch_armed
  if is_kill_switch_armed():
    raise AssertionError("kill switch armed — disarm in Setup first")
  from bridge_control import prepare_runtime
  # require_chart=False so missing EA heartbeat does not fail the E2E
  prep = prepare_runtime(require_chart=False)
  assert isinstance(prep, dict), prep
  mat = prep.get("materialize") or {}
  assert int(mat.get("n") or 0) >= 1, prep
  return f"materialize_n={mat.get('n')} groups={len(prep.get('groups') or [])}"


def check_app_http() -> str:
  from shared.constants import LIVE_APP_PORT
  url = f"http://127.0.0.1:{LIVE_APP_PORT}/"
  try:
    with urllib.request.urlopen(url, timeout=5) as resp:
      code = resp.getcode()
      body = resp.read(4000).decode("utf-8", errors="replace")
  except urllib.error.URLError as exc:
    raise AssertionError(f"app not reachable at {url}: {exc}") from exc
  assert code == 200, code
  # Streamlit root usually returns HTML shell
  assert "<html" in body.lower() or "streamlit" in body.lower() or len(body) > 50
  return f"{url} HTTP {code}"


def check_run_app_status_ps1() -> str:
  ps1 = LIVE / "scripts" / "run_app_windows.ps1"
  r = subprocess.run(
    ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1), "Status"],
    capture_output=True,
    text=True,
    timeout=60,
    cwd=str(LIVE),
  )
  out = ((r.stdout or "") + (r.stderr or "")).strip()
  if r.returncode != 0 and "RUNNING" not in out.upper():
    raise AssertionError(out or f"exit={r.returncode}")
  if "RUNNING" not in out.upper():
    raise AssertionError(out or "Status did not report RUNNING")
  return out.splitlines()[-1] if out else "RUNNING"


def check_deploy_dry_noattach() -> str:
  """Compile/link path without attaching EA — still needs XM MT5 install."""
  script = LIVE / "scripts" / "deploy_live_ea.ps1"
  r = subprocess.run(
    [
      "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
      "-File", str(script),
      "-Mode", "Live",
      "-FromRoster",
      "-SkipBridgeService",
      "-NoAttach",
      "-NoEnableTrading",
      "-NoRestartTerminal",
    ],
    capture_output=True,
    text=True,
    timeout=300,
    cwd=str(LIVE),
    env={**os.environ, "LIVE_SKIP_EA_DEPLOY": "1"},  # unused by ps1; harmless
  )
  out = (r.stdout or "")[-1200:]
  err = (r.stderr or "")[-800:]
  # ParserError must never happen
  blob = (r.stdout or "") + (r.stderr or "")
  if "ParserError" in blob or "RedirectionNotSupported" in blob:
    raise AssertionError(f"PowerShell parse error\n{blob[-1000:]}")
  if r.returncode != 0:
    # XM missing is an environment skip, not a code failure for --with-deploy soft mode
    if "XM Global MT5 not found" in blob or "MetaQuotes Terminal data not found" in blob:
      raise AssertionError(f"MT5 environment: {blob[-500:]}")
    raise AssertionError(f"exit={r.returncode}\n{out}\n{err}")
  if "Live DeployEA" not in (r.stdout or ""):
    raise AssertionError(f"unexpected output:\n{out}")
  return "deploy -NoAttach exit 0"


def check_bridge_once() -> str:
  from bridge_control import prepare_runtime, status, stop_bridge
  from deploy_ea import enabled_books
  from safety import is_kill_switch_armed

  if is_kill_switch_armed():
    raise AssertionError("kill switch armed")
  books = enabled_books()
  if not books:
    raise AssertionError("no enabled books")
  book = books[0]
  prep = prepare_runtime(require_chart=False)
  mat = prep.get("materialize") or {}
  mids = mat.get("model_ids") or book.get("model_ids") or []
  if not mids:
    raise AssertionError("no model ids after prepare_runtime")
  mid = mids[0]
  svc = LIVE / "scripts" / "mt5_bridge_service_live.py"
  was_running = bool(status().get("running"))
  r = subprocess.run(
    [
      sys.executable, str(svc),
      "--symbol", book["symbol"],
      "--timeframe", book["timeframe"],
      "--model-ids", str(mid),
      "--bridge-dir", str(book["bridge_dir"]),
      "--once",
    ],
    cwd=str(LIVE),
    capture_output=True,
    text=True,
    timeout=180,
  )
  if r.returncode != 0:
    raise AssertionError((r.stderr or r.stdout or f"exit={r.returncode}")[-800:])
  if not was_running:
    stop_bridge(flatten=False)
  return f"once {book['symbol']} {book['timeframe']} model={mid}"


def check_gui_nav_labels() -> str:
  src = (LIVE / "gui" / "app.py").read_text(encoding="utf-8")
  for label in ("Live", "Models", "Setup", "Start trading", "Stop"):
    assert label in src, label
  assert "Flatten" not in src
  assert "Emergency kill" not in src
  assert "tab_control" not in src
  return "nav/actions present"


# ── runner ──────────────────────────────────────────────────────────────────


def main() -> int:
  ap = argparse.ArgumentParser(description="Windows Live-mode E2E checks")
  ap.add_argument("--with-deploy", action="store_true",
                  help="Run deploy_live_ea.ps1 -FromRoster -NoAttach (needs XM MT5)")
  ap.add_argument("--with-bridge-once", action="store_true",
                  help="Run mt5_bridge_service_live.py --once for first enabled book")
  ap.add_argument("--allow-non-windows", action="store_true",
                  help="Do not fail when not on Windows (skips Win-only checks)")
  args = ap.parse_args()

  print("=== Live Windows E2E ===")
  print(f"LIVE={LIVE}")

  # Platform gate
  if platform.system().lower().startswith("win"):
    check("windows platform", check_windows)
  elif args.allow_non_windows:
    skip("windows platform", f"running on {platform.system()}")
  else:
    check("windows platform", check_windows)
    print("=== FAILED (not Windows) ===")
    return 2

  print("\n-- Core --")
  check("constants", check_constants)
  check("paths + scripts", check_paths)
  check("streamlit config.toml", check_streamlit_theme_config)
  check("theme helpers / CSS", check_theme_helpers)
  check("gui app AST + markup", check_app_ast)
  check("gui nav labels", check_gui_nav_labels)
  check("replay modes", check_replay_modes)
  if platform.system().lower().startswith("win"):
    check("deploy_live_ea.ps1 PARSE", check_deploy_ps1_parse)
  else:
    skip("deploy_live_ea.ps1 PARSE", "Windows only")

  print("\n-- Live data path --")
  check("roster + enabled books", check_roster_and_books)
  check("sync_bridge_roster", check_sync_roster)
  check("desk_snapshot shape", check_desk_snapshot)
  check("live_health", check_live_health)
  check("journal_summary", check_journal)
  check("bridge status()", check_bridge_status)
  check("EA coverage report", check_ea_coverage)

  print("\n-- Safety / prepare --")
  check("flatten + kill roundtrip", check_safety_roundtrip)
  check("prepare_runtime", check_prepare_runtime)

  print("\n-- App process --")
  check("HTTP Live UI", check_app_http)
  if platform.system().lower().startswith("win"):
    check("run_app_windows.ps1 Status", check_run_app_status_ps1)
  else:
    skip("run_app_windows.ps1 Status", "Windows only")

  if args.with_deploy:
    print("\n-- Deploy (optional) --")
    if platform.system().lower().startswith("win"):
      check("deploy -NoAttach", check_deploy_dry_noattach)
    else:
      skip("deploy -NoAttach", "Windows only")
  else:
    skip("deploy -NoAttach", "pass --with-deploy to enable")

  if args.with_bridge_once:
    print("\n-- Bridge once (optional) --")
    check("service --once", check_bridge_once)
  else:
    skip("service --once", "pass --with-bridge-once to enable")

  print("\n=== SUMMARY ===")
  print(f"OK={PASSED}  FAIL={FAILED}  SKIP={SKIPPED}")
  if FAILED:
    print("Failed checks:")
    for name, status, detail in RESULTS:
      if status == "FAIL":
        print(f"  - {name}: {detail}")
    print("=== LIVE WINDOWS E2E FAILED ===")
    return 1
  print("=== LIVE WINDOWS E2E PASSED ===")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
