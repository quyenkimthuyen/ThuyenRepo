#!/usr/bin/env python3
"""Watch e21 r8 64-combo grid. On miss, kill stale-memory pipeline and start disk r9.

ASCII stdout tokens: BAR_MET | STARTED_R9 | DEAD | FAILED
Does not touch g23. Does not wipe KB. Does not start a second grid while r8 runs.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

TRAIN = Path(__file__).resolve().parent.parent
RESULTS = TRAIN / "runtime" / "e21" / "results"
PIPE_LOG = RESULTS / "pipeline_m15_tune.log"
MODELS = RESULTS / "trade_models.json"
WD_LOG = RESULTS / "e21_r8_watchdog.log"
SPAWN_LOG = RESULTS / "e21_watchdog_spawn.log"
LOCK = RESULTS / "e21_r8_watchdog.lock"

POLL_SEC = 40
DEAD_NEED = 3
BAR_WR = 55.0
BAR_R = 90.0
BAR_RR = 2.5

CREATE_NEW_PROCESS_GROUP = 0x00000200
DETACHED_PROCESS = 0x00000008

RE_R8 = re.compile(r"e21 wr50 r8\b")
RE_GRID_DONE_64 = re.compile(r"Grid done \S+: (\d+)/64 OK")
RE_GRID_PROG = re.compile(r"Grid (\d+)/64:")
RE_HITS_R8 = re.compile(r"wr50 round 8 hits=(\d+)")
RE_PROMOTED = re.compile(
    r"Promoted\[[^\]]+\].*?WR(\d+(?:\.\d+)?)\s+RR(\d+(?:\.\d+)?)\s+\+(\d+(?:\.\d+)?)R",
    re.IGNORECASE,
)
RE_TOPQ = re.compile(
    r"topQ WR=(\d+(?:\.\d+)?)\s+RR=(\d+(?:\.\d+)?)\s+R=(\d+(?:\.\d+)?)",
)
RE_NEXT_ROUND = re.compile(r"e21 wr50 r(\d+)\b")
RE_LABEL_RR = re.compile(r"RR\s*(\d+(?:\.\d+)?)", re.IGNORECASE)


def _now() -> str:
  return datetime.now().isoformat(timespec="seconds")


def wlog(msg: str) -> None:
  line = f"[{_now()}] {msg}"
  RESULTS.mkdir(parents=True, exist_ok=True)
  with open(WD_LOG, "a", encoding="ascii", errors="replace") as f:
    f.write(line + "\n")
  try:
    print(line, flush=True)
  except UnicodeEncodeError:
    print(line.encode("ascii", "replace").decode("ascii"), flush=True)


def emit(token: str, extra: str = "") -> None:
  wlog(token if not extra else f"{token} {extra}")
  print(token, flush=True)


def tasklist_alive(pid: int) -> bool:
  if pid <= 0:
    return False
  try:
    r = subprocess.run(
      ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
      capture_output=True, text=True, timeout=20,
    )
  except Exception as exc:
    wlog(f"tasklist err pid={pid}: {exc}")
    return True  # unknown -> do NOT treat as dead
  out = (r.stdout or "").strip()
  if not out or out.upper().startswith("INFO:"):
    return False
  return f",{pid}," in out.replace(" ", "") or f'"{pid}"' in out


def pid_cmd(pid: int) -> str:
  try:
    r = subprocess.run(
      [
        "powershell", "-NoProfile", "-Command",
        f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine",
      ],
      capture_output=True, text=True, timeout=25, cwd=str(TRAIN),
    )
    return (r.stdout or "").strip()
  except Exception:
    return ""


def is_e21_pipeline(cmd: str) -> bool:
  c = (cmd or "").lower()
  if "e21_r8_watchdog" in c:
    return False
  if "pipeline_m15_tune" not in c:
    return False
  if "g23" in c and "--desks e21" not in c:
    return False
  return True


def find_e21_pipeline_pids() -> list[int]:
  try:
    r = subprocess.run(
      [
        "powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" |"
        " Where-Object { $_.CommandLine -match 'pipeline_m15_tune.py'"
        " -and $_.CommandLine -match '--desks e21'"
        " -and $_.CommandLine -notmatch 'e21_r8_watchdog' } |"
        " Select-Object -ExpandProperty ProcessId",
      ],
      capture_output=True, text=True, timeout=30, cwd=str(TRAIN),
    )
  except Exception as exc:
    wlog(f"find e21 err: {exc}")
    return []
  pids = []
  for tok in (r.stdout or "").split():
    try:
      pids.append(int(tok))
    except ValueError:
      pass
  return pids


def models_meet_bar() -> str | None:
  if not MODELS.is_file():
    return None
  try:
    data = json.loads(MODELS.read_text(encoding="utf-8"))
  except Exception:
    return None
  models = data.get("models") if isinstance(data, dict) else data
  if not isinstance(models, list):
    return None
  for m in models:
    if not isinstance(m, dict):
      continue
    try:
      wr = float(m.get("win_rate_pct") or 0)
      tot = float(m.get("total_r") or 0)
    except (TypeError, ValueError):
      continue
    rr = m.get("avg_rr")
    try:
      rr_f = float(rr) if rr is not None else 0.0
    except (TypeError, ValueError):
      rr_f = 0.0
    if rr_f <= 0:
      lab = str(m.get("label") or "")
      mm = RE_LABEL_RR.search(lab)
      if mm:
        rr_f = float(mm.group(1))
    if wr > BAR_WR and tot > BAR_R and rr_f > BAR_RR:
      return f"id={m.get('id')} WR={wr} R={tot} RR={rr_f}"
  return None


def parse_r8(text: str) -> dict:
  lines = text.splitlines()
  start = -1
  for i, ln in enumerate(lines):
    if RE_R8.search(ln):
      start = i
  if start < 0:
    return {"has_r8": False}
  body = lines[start:]
  done_m = None
  done_idx = -1
  for i, ln in enumerate(body):
    m = RE_GRID_DONE_64.search(ln)
    if m:
      done_m = m
      done_idx = i
  prog_n = None
  for ln in body:
    if "Grid done" in ln:
      continue
    pm = RE_GRID_PROG.search(ln)
    if pm:
      prog_n = int(pm.group(1))
  hits = None
  for ln in body:
    hm = RE_HITS_R8.search(ln)
    if hm:
      hits = int(hm.group(1))
  chua = False
  for ln in body:
    ascii_ln = ln.encode("ascii", "replace").decode("ascii").lower()
    if "chưa đạt" in ln or "chua dat" in ascii_ln:
      chua = True
    if "wr>" in ascii_ln and "sau" in ascii_ln and "round" in ascii_ln:
      chua = True
    if "no hits" in ascii_ln and "promote" in ascii_ln:
      chua = True
  promoted_ok = False
  promoted_any = False
  after = body[done_idx:] if done_idx >= 0 else []
  for ln in after:
    if "Promoted[" in ln:
      promoted_any = True
      pm = RE_PROMOTED.search(ln)
      if pm:
        wr, rr, tot = float(pm.group(1)), float(pm.group(2)), float(pm.group(3))
        if wr >= 55.0 and tot > BAR_R and rr > BAR_RR:
          promoted_ok = True
    tm = RE_TOPQ.search(ln)
    if tm:
      wr, rr, tot = float(tm.group(1)), float(tm.group(2)), float(tm.group(3))
      if wr > BAR_WR and tot > BAR_R and rr > BAR_RR:
        promoted_ok = True
  stale_next = False
  if done_idx >= 0:
    for ln in body[done_idx + 1:]:
      nm = RE_NEXT_ROUND.search(ln)
      if nm and int(nm.group(1)) >= 9:
        stale_next = True
  in_progress = done_m is None and prog_n is not None and prog_n < 64
  return {
    "has_r8": True,
    "grid_done": done_m is not None,
    "ok_n": int(done_m.group(1)) if done_m else None,
    "prog_n": prog_n,
    "in_progress": in_progress,
    "hits": hits,
    "chua": chua,
    "promoted_ok": promoted_ok,
    "promoted_any": promoted_any,
    "stale_next": stale_next,
  }


def kill_pid_tree(pid: int) -> bool:
  cmd = pid_cmd(pid)
  if cmd and not is_e21_pipeline(cmd):
    wlog(f"REFUSE_KILL pid={pid} not e21 pipeline")
    return False
  if not tasklist_alive(pid):
    wlog(f"kill skip: {pid} already dead")
    return True
  wlog(f"taskkill /PID {pid} /T /F")
  r = subprocess.run(
    ["taskkill", "/PID", str(pid), "/T", "/F"],
    capture_output=True, text=True, timeout=30,
  )
  wlog(f"taskkill rc={r.returncode}")
  for _ in range(12):
    if not tasklist_alive(pid):
      return True
    time.sleep(0.5)
  return not tasklist_alive(pid)


def start_pipeline(round_no: int) -> int | None:
  existing = find_e21_pipeline_pids()
  if existing:
    wlog(f"REFUSE_SPAWN r{round_no}: e21 already running pids={existing}")
    return None
  env = os.environ.copy()
  env["FILLBOOK_START_ROUND"] = str(round_no)
  env["PYTHONUNBUFFERED"] = "1"
  SPAWN_LOG.parent.mkdir(parents=True, exist_ok=True)
  sl = open(SPAWN_LOG, "a", encoding="utf-8", errors="replace")
  sl.write(f"\n===== spawn r{round_no} {_now()} =====\n")
  sl.flush()
  try:
    p = subprocess.Popen(
      [
        sys.executable, "-u",
        str(TRAIN / "scripts" / "pipeline_m15_tune.py"),
        "--desks", "e21", "--mode", "wr50", "--workers", "5", "--no-salvage",
      ],
      cwd=str(TRAIN),
      env=env,
      stdout=sl,
      stderr=subprocess.STDOUT,
      stdin=subprocess.DEVNULL,
      creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
      close_fds=False,
    )
  except Exception as exc:
    sl.write(f"spawn error: {exc}\n")
    sl.close()
    wlog(f"FAILED spawn r{round_no}: {exc}")
    return None
  wlog(f"spawned r{round_no} pid={p.pid}")
  return p.pid


def read_log() -> tuple[str, int, float]:
  if not PIPE_LOG.is_file():
    return "", 0, 0.0
  st = PIPE_LOG.stat()
  text = PIPE_LOG.read_text(encoding="utf-8", errors="replace")
  return text, st.st_size, st.st_mtime


def write_lock() -> None:
  LOCK.write_text(f"{os.getpid()}\n{_now()}\n", encoding="ascii")


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--pid", type=int, default=28552,
                  help="e21 r8 python PID to watch")
  args = ap.parse_args()
  RESULTS.mkdir(parents=True, exist_ok=True)
  write_lock()

  target = int(args.pid)
  alive = tasklist_alive(target)
  others = find_e21_pipeline_pids()
  if not alive and others:
    target = others[0]
    alive = True
    wlog(f"retarget pid={target} from live e21 list {others}")
  cmd = pid_cmd(target) if alive else ""
  wlog(
    f"WATCH start target={target} alive={alive} others={others} "
    f"cmd={(cmd[:160] if cmd else 'none')}"
  )
  if alive and cmd and not is_e21_pipeline(cmd):
    emit("FAILED", "target pid is not e21 pipeline")
    return 1
  if not alive:
    wlog("target not visible yet; will require repeated misses before DEAD")

  last_size = -1
  last_mtime = -1.0
  dead_streak = 0
  while True:
    met = models_meet_bar()
    if met:
      emit("BAR_MET", met)
      return 0

    alive = tasklist_alive(target)
    if not alive:
      found = find_e21_pipeline_pids()
      if found:
        wlog(f"target {target} gone but e21 live {found}; retarget")
        target = found[0]
        alive = True
        dead_streak = 0
      else:
        dead_streak += 1
    else:
      dead_streak = 0

    try:
      text, size, mtime = read_log()
    except Exception as exc:
      wlog(f"log read err: {exc}")
      time.sleep(POLL_SEC)
      continue

    st = parse_r8(text) if text else {}
    changed = size != last_size or mtime != last_mtime
    last_size, last_mtime = size, mtime
    wlog(
      f"{'log' if changed else 'hb'} r8 done={st.get('grid_done')} "
      f"prog={st.get('prog_n')} hits={st.get('hits')} chua={st.get('chua')} "
      f"promo={st.get('promoted_ok')} inprog={st.get('in_progress')} "
      f"stale_next={st.get('stale_next')} pid={target} alive={alive} "
      f"dead_streak={dead_streak}"
    )

    if st.get("promoted_ok") or (st.get("hits") is not None and st["hits"] > 0):
      emit("BAR_MET", f"hits={st.get('hits')} promo={st.get('promoted_ok')}")
      return 0
    if st.get("promoted_any") and st.get("grid_done"):
      emit("BAR_MET", "Promoted")
      return 0

    miss = bool(st.get("grid_done")) and (
      st.get("hits") == 0 or st.get("chua") or st.get("stale_next")
    )
    if miss and st.get("in_progress"):
      wlog("skip r9: grid still in progress")
      miss = False
    if miss:
      wlog("r8 miss after 64-combo Grid done -> kill target, start disk r9")
      if alive:
        if not kill_pid_tree(target):
          emit("FAILED", f"taskkill {target}")
          return 1
      new_pid = start_pipeline(9)
      if not new_pid:
        emit("FAILED", "start r9")
        return 1
      emit("STARTED_R9", f"pid={new_pid}")
      return 0

    if dead_streak >= DEAD_NEED and not st.get("grid_done"):
      if st.get("in_progress"):
        wlog("DEAD streak but grid in progress in log; wait, do not spawn")
      else:
        emit("DEAD", f"{target} gone before Grid done; restart r8")
        new_pid = start_pipeline(8)
        if not new_pid:
          emit("FAILED", "restart r8")
          return 1
        wlog(f"restarted r8 pid={new_pid}")
        return 0

    if dead_streak >= DEAD_NEED and st.get("grid_done") and (
      st.get("hits") == 0 or st.get("chua") or st.get("stale_next")
    ):
      wlog("r8 done+miss and pid dead -> start disk r9")
      new_pid = start_pipeline(9)
      if not new_pid:
        emit("FAILED", "start r9")
        return 1
      emit("STARTED_R9", f"pid={new_pid}")
      return 0

    time.sleep(POLL_SEC)


if __name__ == "__main__":
  try:
    raise SystemExit(main())
  except Exception as exc:
    try:
      emit("FAILED", str(exc))
    except Exception:
      print("FAILED", flush=True)
    raise
