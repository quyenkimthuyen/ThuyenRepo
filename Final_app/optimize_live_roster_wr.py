#!/usr/bin/env python3
"""Optimize Live roster slots: WR↑ with TotalR not down.

Pass1: scan existing desk trade_models for dominate candidates.
Pass2: focused remine (WR-oriented presets) for slots still missing a winner.
Pass3: freeze schedule, export .tmpkg, import Live, update roster.

Usage:
  python optimize_live_roster_wr.py --pass1
  python optimize_live_roster_wr.py --pass2 --workers 4
  python optimize_live_roster_wr.py --promote
  python optimize_live_roster_wr.py --all --workers 4
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FINAL = Path(__file__).resolve().parent
SPLIT = FINAL / "split_app"
LIVE = SPLIT / "live"
PY = Path("/home/thuyenng/work/ThuyenRepo/EdgeMinerM15B5/.venv/bin/python")
OOS_FROM, OOS_TO = "2026-01-01", "2026-08-07"
MIN_PF = 1.3
MIN_TRADES = 40
REPORT_JSON = FINAL / "results_live_roster_wr_opt.json"
REPORT_MD = FINAL / "results_live_roster_wr_opt.md"
LOG = FINAL / "live_roster_wr_opt.log"

DESK_BY_BOOK = {
  ("EURUSD", "M15"): "EdgeMinerEURUSDM15",
  ("EURUSD", "M5"): "EdgeMinerEURUSDM5",
  ("GBPUSD", "M15"): "EdgeMinerGBPUSDM15",
  ("GBPUSD", "M5"): "EdgeMinerGBPUSDM5",
}

# Role inferred from Live label suffix.
ROLE_PRESETS_M15_EUR = ["eur_m15_wr", "eur_m15_stretch_wr", "eur_m15_balance_v2", "elite_or_quality"]
ROLE_PRESETS_M15_GBP = ["elite_or_quality", "anti_chase_fixed_70", "edge_gentle", "baseline"]
ROLE_PRESETS_M5 = ["elite_or_quality", "elite_m5_balanced", "anti_chase_fixed_70", "baseline"]


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def log(msg: str) -> None:
  line = f"[{_now()}] {msg}"
  print(line, flush=True)
  with open(LOG, "a", encoding="utf-8") as f:
    f.write(line + "\n")


def _f(v: Any, default: float = 0.0) -> float:
  try:
    if v is None:
      return default
    return float(v)
  except Exception:
    return default


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def infer_role(label: str) -> str:
  lab = str(label or "")
  if "· WR" in lab or lab.endswith(" WR"):
    return "WR"
  if "Balance" in lab:
    return "Balance"
  if "· R" in lab or lab.endswith(" · R"):
    return "R"
  return "?"


def load_roster_slots() -> list[dict]:
  roster = _read(LIVE / "results" / "live_roster.json") or {}
  slots = []
  for row in roster.get("models") or []:
    sym = str(row.get("symbol") or "").upper()
    tf = str(row.get("timeframe") or "").upper()
    desk = DESK_BY_BOOK.get((sym, tf))
    if not desk:
      continue
    store = _read(FINAL / desk / "results" / "trade_models.json") or {}
    mid = str(row.get("model_id") or "")
    model = next((m for m in (store.get("models") or []) if str(m.get("id")) == mid), None) or {}
    slots.append({
      "install_id": row.get("install_id"),
      "model_id": mid,
      "live_label": row.get("label"),
      "role": infer_role(str(row.get("label") or "")),
      "symbol": sym,
      "timeframe": tf,
      "desk": desk,
      "enabled": bool(row.get("enabled")),
      "baseline": {
        "label": model.get("label") or row.get("label"),
        "total_r": _f(model.get("total_r")),
        "win_rate_pct": _f(model.get("win_rate_pct")),
        "profit_factor": _f(model.get("profit_factor")),
        "n_trades": int(_f(model.get("n_trades"))),
        "max_drawdown_r": _f(model.get("max_drawdown_r")),
        "train_weeks": model.get("train_weeks"),
        "kb_profile": model.get("kb_profile"),
        "feature_profile": model.get("feature_profile"),
        "spread_pips": model.get("spread_pips"),
        "slippage_pips": model.get("slippage_pips"),
      },
    })
  return slots


def passes_gate(cand: dict, baseline: dict) -> bool:
  wr = _f(cand.get("win_rate_pct"))
  r = _f(cand.get("total_r"))
  pf = _f(cand.get("profit_factor"))
  n = int(_f(cand.get("n_trades")))
  b_wr = _f(baseline.get("win_rate_pct"))
  b_r = _f(baseline.get("total_r"))
  if wr <= b_wr:
    return False
  if r < b_r:
    return False
  if pf < MIN_PF:
    return False
  if n < MIN_TRADES:
    return False
  return True


def rank_key(cand: dict, baseline: dict) -> tuple:
  return (
    _f(cand.get("win_rate_pct")) - _f(baseline.get("win_rate_pct")),
    _f(cand.get("total_r")),
    _f(cand.get("profit_factor")),
  )


def scan_desk_candidates(slot: dict) -> dict | None:
  desk = slot["desk"]
  store = _read(FINAL / desk / "results" / "trade_models.json") or {}
  baseline = slot["baseline"]
  base_id = slot["model_id"]
  best = None
  best_key = None
  for m in store.get("models") or []:
    if m.get("archived"):
      continue
    mid = str(m.get("id") or "")
    if mid == base_id:
      continue
    if not passes_gate(m, baseline):
      continue
    key = rank_key(m, baseline)
    if best is None or key > best_key:
      best = m
      best_key = key
  if not best:
    return None
  return {
    "model_id": best.get("id"),
    "label": best.get("label"),
    "total_r": _f(best.get("total_r")),
    "win_rate_pct": _f(best.get("win_rate_pct")),
    "profit_factor": _f(best.get("profit_factor")),
    "n_trades": int(_f(best.get("n_trades"))),
    "max_drawdown_r": _f(best.get("max_drawdown_r")),
    "train_weeks": best.get("train_weeks"),
    "kb_profile": best.get("kb_profile"),
    "feature_profile": best.get("feature_profile"),
    "spread_pips": best.get("spread_pips"),
    "slippage_pips": best.get("slippage_pips"),
    "source": "pass1_existing",
    "delta_wr": round(_f(best.get("win_rate_pct")) - _f(baseline.get("win_rate_pct")), 3),
    "delta_r": round(_f(best.get("total_r")) - _f(baseline.get("total_r")), 3),
  }


def pass1(slots: list[dict]) -> dict:
  results = []
  for slot in slots:
    cand = scan_desk_candidates(slot)
    action = "replace" if cand else "need_pass2"
    results.append({
      **{k: slot[k] for k in (
        "install_id", "model_id", "live_label", "role", "symbol", "timeframe",
        "desk", "enabled", "baseline",
      )},
      "action": action,
      "candidate": cand,
    })
    b = slot["baseline"]
    if cand:
      log(
        f"PASS1 {slot['symbol']} {slot['timeframe']} {slot['role']}: "
        f"REPLACE {b.get('label')} → {cand['label']} "
        f"WR {b.get('win_rate_pct')}→{cand['win_rate_pct']} "
        f"R {b.get('total_r')}→{cand['total_r']}"
      )
    else:
      log(
        f"PASS1 {slot['symbol']} {slot['timeframe']} {slot['role']}: "
        f"KEEP {b.get('label')} (no dominate candidate) → pass2"
      )
  payload = {
    "updated_at": _now(),
    "oos_from": OOS_FROM,
    "oos_to": OOS_TO,
    "gate": {"wr_gt": True, "r_gte": True, "min_pf": MIN_PF, "min_trades": MIN_TRADES},
    "slots": results,
  }
  _write(REPORT_JSON, payload)
  write_report_md(payload)
  return payload


def write_report_md(payload: dict) -> None:
  lines = [
    "# Live roster WR optimize",
    "",
    f"OOS `{payload.get('oos_from')}` → `{payload.get('oos_to')}` · {_now()}",
    "",
    "| Book | Role | Action | Baseline | Candidate | ΔWR | ΔR |",
    "|------|------|--------|----------|-----------|-----|----|",
  ]
  for s in payload.get("slots") or []:
    b = s.get("baseline") or {}
    c = s.get("candidate") or {}
    base_s = f"{b.get('label')} R={b.get('total_r')} WR={b.get('win_rate_pct')}"
    if c:
      cand_s = f"{c.get('label')} R={c.get('total_r')} WR={c.get('win_rate_pct')}"
      dwr, dr = c.get("delta_wr"), c.get("delta_r")
    else:
      cand_s = "—"
      dwr = dr = "—"
    lines.append(
      f"| {s.get('symbol')} {s.get('timeframe')} | {s.get('role')} | `{s.get('action')}` | "
      f"{base_s} | {cand_s} | {dwr} | {dr} |"
    )
  REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def presets_for_slot(slot: dict) -> list[str]:
  sym, tf = slot["symbol"], slot["timeframe"]
  if tf == "M15" and sym == "EURUSD":
    return list(ROLE_PRESETS_M15_EUR)
  if tf == "M15":
    return list(ROLE_PRESETS_M15_GBP)
  return list(ROLE_PRESETS_M5)


def train_weeks_for_slot(slot: dict) -> list[int]:
  tf = slot["timeframe"]
  base_tw = int(slot.get("baseline", {}).get("train_weeks") or (6 if tf == "M15" else 3))
  if tf == "M15":
    opts = [6, 9]
  else:
    opts = [3, 6]
  if base_tw not in opts:
    opts.append(base_tw)
  return sorted(set(opts))


def _pass2_job_worker(job: dict) -> dict:
  """Run one walk-forward job (importable worker for ProcessPool)."""
  from _wr_opt_pass2_worker import run_job

  return run_job(job)


def build_pass2_jobs(slots_need: list[dict]) -> list[dict]:
  jobs = []
  for slot in slots_need:
    desk = FINAL / slot["desk"]
    kb = slot["baseline"].get("kb_profile")
    feature = slot["baseline"].get("feature_profile") or (
      "m5_parity" if slot["timeframe"] == "M5" else "current"
    )
    spread = slot["baseline"].get("spread_pips") or (1.5 if slot["timeframe"] == "M15" else 1.0)
    slip = slot["baseline"].get("slippage_pips") or 0.3
    for preset in presets_for_slot(slot):
      # skip unknown presets for this desk
      try:
        sys.path.insert(0, str(desk))
        from mining_presets import PRESETS  # type: ignore
        if preset not in PRESETS:
          continue
      finally:
        if str(desk) in sys.path:
          sys.path.remove(str(desk))
      for tw in train_weeks_for_slot(slot):
        jobs.append({
          "slot_key": f"{slot['symbol']}_{slot['timeframe']}_{slot['role']}",
          "desk": slot["desk"],
          "desk_path": str(desk),
          "symbol": slot["symbol"],
          "timeframe": slot["timeframe"],
          "role": slot["role"],
          "baseline": slot["baseline"],
          "baseline_model_id": slot["model_id"],
          "preset": preset,
          "train_weeks": tw,
          "kb_profile": kb,
          "feature_profile": feature,
          "spread_pips": spread,
          "slippage_pips": slip,
          "name": f"{slot['symbol']}_{slot['timeframe']}_{slot['role']}_{preset}_tw{tw}",
        })
  return jobs


def promote_pass2_winner(job_result: dict) -> dict | None:
  """Create trade model + save report/schedule on desk from a winning WF job."""
  desk = Path(job_result["desk_path"])
  worker = FINAL / f"_wr_opt_promote_{desk.name}.py"
  payload_path = FINAL / f"_wr_opt_promote_{desk.name}.json"
  _write(payload_path, job_result)
  worker.write_text(
    r'''
import json, sys
from pathlib import Path
desk = Path(sys.argv[1]).resolve()
payload = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
sys.path.insert(0, str(desk))
from gui.trade_model import create_trade_model, save_model_report, load_models_store, save_models_store
from mining_presets import get_preset

oos = payload.get("overall_oos") or {}
space = get_preset(payload["preset"]) or {}
row = {
  "key": f"wr_opt|{payload.get('preset')}|tw{payload.get('train_weeks')}|{payload.get('kb_profile')}",
  "train_weeks": payload.get("train_weeks"),
  "use_kb": True,
  "kb_profile": payload.get("kb_profile"),
  "kb_snapshot": None,
  "oos_from": "2026-01-01",
  "oos_to": "2026-08-07",
  "spread_pips": payload.get("spread_pips"),
  "slippage_pips": payload.get("slippage_pips"),
  "total_r": oos.get("total_r") or payload.get("total_r"),
  "win_rate_pct": oos.get("win_rate_pct") or payload.get("win_rate_pct"),
  "max_drawdown_r": oos.get("max_drawdown_r") or payload.get("max_drawdown_r"),
  "profit_factor": oos.get("profit_factor") or payload.get("profit_factor"),
  "n_trades": oos.get("n_trades") or payload.get("n_trades"),
  "feature_profile": payload.get("feature_profile"),
  "mining_search_space": space,
  "mining_preset": payload.get("preset"),
  "preset": payload.get("preset"),
}
label = f"WROpt_{payload.get('role')}_{payload.get('preset')}_tw{payload.get('train_weeks')}"
report = {
  "overall_oos": oos,
  "config": payload.get("report_config") or {
    "train_weeks": payload.get("train_weeks"),
    "use_learning_kb": True,
    "kb_profile": payload.get("kb_profile"),
    "oos_from": "2026-01-01",
    "oos_to": "2026-08-07",
    "feature_profile": payload.get("feature_profile"),
    "mining_search_space": space,
  },
  "schedule_weekly": payload.get("schedule_weekly"),
  "data_source": payload.get("data_source") or {},
}
m = create_trade_model(
  row, run_id="wr_opt", label=label, report=report,
  set_active=False, build_report=False, allow_duplicate_combo=True,
)
save_model_report(m["id"], report)
store = load_models_store()
for x in store["models"]:
  if x.get("id") == m.get("id"):
    x["oos_from"] = "2026-01-01"
    x["oos_to"] = "2026-08-07"
    x["total_r"] = row["total_r"]
    x["win_rate_pct"] = row["win_rate_pct"]
    x["profit_factor"] = row["profit_factor"]
    x["n_trades"] = row["n_trades"]
    x["max_drawdown_r"] = row["max_drawdown_r"]
    m = x
    break
save_models_store(store)
print(json.dumps({"model_id": m.get("id"), "label": m.get("label"), **{k: m.get(k) for k in ["total_r","win_rate_pct","profit_factor","n_trades","max_drawdown_r"]}}))
''',
    encoding="utf-8",
  )
  try:
    r = subprocess.run(
      [str(PY), str(worker), str(desk), str(payload_path)],
      cwd=str(desk),
      capture_output=True,
      text=True,
    )
    if r.returncode != 0:
      log(f"promote fail {desk.name}: {r.stderr or r.stdout}")
      return None
    line = (r.stdout or "").strip().splitlines()[-1]
    return json.loads(line)
  finally:
    for p in (worker, payload_path):
      try:
        p.unlink()
      except OSError:
        pass


def pass2(payload: dict, *, workers: int = 4) -> dict:
  need = [s for s in (payload.get("slots") or []) if s.get("action") == "need_pass2"]
  if not need:
    log("PASS2: nothing to remine")
    return payload
  jobs = build_pass2_jobs(need)
  log(f"PASS2: {len(need)} slots · {len(jobs)} jobs · workers={workers}")
  if not jobs:
    return payload

  by_desk: dict[str, list[dict]] = {}
  for j in jobs:
    by_desk.setdefault(j["desk"], []).append(j)

  all_results: list[dict] = []
  runner = FINAL / "_wr_opt_pass2_desk_runner.py"
  runner.write_text(
    '''#!/usr/bin/env python3
"""Run Pass2 jobs for one desk in an isolated process."""
from __future__ import annotations
import json, sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

FINAL = Path(__file__).resolve().parent
sys.path.insert(0, str(FINAL))
from _wr_opt_pass2_worker import run_job

def main() -> int:
  jobs_path = Path(sys.argv[1])
  workers = int(sys.argv[2])
  out_path = Path(sys.argv[3])
  jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
  rows = []
  with ProcessPoolExecutor(max_workers=max(1, workers)) as pool:
    futs = {pool.submit(run_job, j): j.get("name") for j in jobs}
    for fut in as_completed(futs):
      rows.append(fut.result())
  # Drop schedule_weekly from file if huge? Keep — needed for promote.
  out_path.write_text(json.dumps(rows, ensure_ascii=False, default=str) + "\\n", encoding="utf-8")
  print(f"DONE n={len(rows)} ok={sum(1 for r in rows if not r.get('error'))}", flush=True)
  return 0

if __name__ == "__main__":
  raise SystemExit(main())
''',
    encoding="utf-8",
  )

  for desk_name, desk_jobs in by_desk.items():
    log(f"PASS2 desk {desk_name}: {len(desk_jobs)} jobs (isolated)")
    jobs_path = FINAL / f"_wr_opt_jobs_{desk_name}.json"
    out_path = FINAL / f"_wr_opt_out_{desk_name}.json"
    # Strip nothing yet — write jobs without prior results
    _write(jobs_path, desk_jobs)
    r = subprocess.run(
      [str(PY), str(runner), str(jobs_path), str(workers), str(out_path)],
      cwd=str(FINAL),
    )
    if r.returncode != 0 or not out_path.exists():
      log(f"PASS2 desk {desk_name}: runner FAILED rc={r.returncode}")
      continue
    rows = _read(out_path) or []
    for row in rows:
      all_results.append(row)
      if row.get("error"):
        log(f"  FAIL {row.get('name')}: {row.get('error')}")
      else:
        log(
          f"  OK {row.get('name')}: R={row.get('total_r')} WR={row.get('win_rate_pct')} "
          f"PF={row.get('profit_factor')} n={row.get('n_trades')} ({row.get('elapsed_sec')}s)"
        )
    try:
      jobs_path.unlink()
    except OSError:
      pass

  # Pick best winner per slot_key
  best_by_slot: dict[str, dict] = {}
  for row in all_results:
    if row.get("error"):
      continue
    baseline = row.get("baseline") or {}
    if not passes_gate(row, baseline):
      continue
    sk = row["slot_key"]
    prev = best_by_slot.get(sk)
    if prev is None or rank_key(row, baseline) > rank_key(prev, baseline):
      best_by_slot[sk] = row

  for s in payload["slots"]:
    if s.get("action") != "need_pass2":
      continue
    sk = f"{s['symbol']}_{s['timeframe']}_{s['role']}"
    winner = best_by_slot.get(sk)
    if not winner:
      s["action"] = "keep"
      s["candidate"] = None
      s["pass2"] = "no_winner"
      log(f"PASS2 {sk}: no winner — KEEP baseline")
      continue
    created = promote_pass2_winner(winner)
    if not created:
      s["action"] = "keep"
      s["pass2"] = "promote_failed"
      continue
    s["action"] = "replace"
    s["candidate"] = {
      "model_id": created.get("model_id"),
      "label": created.get("label"),
      "total_r": _f(created.get("total_r")),
      "win_rate_pct": _f(created.get("win_rate_pct")),
      "profit_factor": _f(created.get("profit_factor")),
      "n_trades": int(_f(created.get("n_trades"))),
      "max_drawdown_r": _f(created.get("max_drawdown_r")),
      "train_weeks": winner.get("train_weeks"),
      "kb_profile": winner.get("kb_profile"),
      "feature_profile": winner.get("feature_profile"),
      "spread_pips": winner.get("spread_pips"),
      "slippage_pips": winner.get("slippage_pips"),
      "source": f"pass2:{winner.get('preset')}",
      "delta_wr": round(_f(created.get("win_rate_pct")) - _f(s["baseline"].get("win_rate_pct")), 3),
      "delta_r": round(_f(created.get("total_r")) - _f(s["baseline"].get("total_r")), 3),
    }
    s["pass2"] = winner.get("name")
    log(
      f"PASS2 {sk}: REPLACE → {created.get('label')} "
      f"WRΔ={s['candidate']['delta_wr']} RΔ={s['candidate']['delta_r']}"
    )

  payload["updated_at"] = _now()
  payload["pass2_jobs"] = len(jobs)
  payload["pass2_results_n"] = len(all_results)
  _write(REPORT_JSON, payload)
  write_report_md(payload)
  return payload


def ensure_schedule_and_package(desk: str, model_id: str) -> Path | None:
  desk_path = FINAL / desk
  sched = desk_path / "results" / "trade_models" / f"{model_id}_schedule.json"
  if not sched.exists() or not (_read(sched) or {}).get("weekly"):
    log(f"Export schedule {desk}/{model_id}")
    r = subprocess.run(
      [str(PY), str(desk_path / "scripts" / "export_model_schedule.py"),
       "--model-id", model_id, "--quiet"],
      cwd=str(desk_path),
    )
    if r.returncode != 0:
      log(f"  schedule export FAILED rc={r.returncode}")
      return None
  out_dir = SPLIT / "packages_out" / "wr_opt"
  out_dir.mkdir(parents=True, exist_ok=True)
  r = subprocess.run(
    [
      str(PY), str(SPLIT / "lab" / "export_trade_package.py"),
      "--desk", desk, "--model-id", model_id, "--out", str(out_dir),
    ],
    cwd=str(SPLIT),
    capture_output=True,
    text=True,
  )
  if r.returncode != 0:
    log(f"  package export FAILED: {r.stderr or r.stdout}")
    return None
  # find newest matching tmpkg
  cands = sorted(out_dir.glob(f"*{model_id[-8:]}.tmpkg"), key=lambda p: p.stat().st_mtime, reverse=True)
  if not cands:
    cands = sorted(out_dir.glob("*.tmpkg"), key=lambda p: p.stat().st_mtime, reverse=True)
  if not cands:
    return None
  pkg = cands[0]
  log(f"  package {pkg.name}")
  r2 = subprocess.run(
    [str(PY), str(LIVE / "import_trade_package.py"), str(pkg)],
    cwd=str(LIVE),
    capture_output=True,
    text=True,
  )
  if r2.returncode != 0:
    log(f"  import FAILED: {r2.stderr or r2.stdout}")
    return None
  log(f"  {(r2.stdout or '').strip()}")
  return pkg


def live_role_label(symbol: str, timeframe: str, role: str) -> str:
  suffix = {"WR": "WR", "R": "R", "Balance": "Balance"}.get(role, role)
  return f"{symbol} {timeframe} · {suffix}"


def promote_to_live(payload: dict) -> dict:
  """For replace slots (and keep slots missing schedule if enabled intended): package + roster."""
  sys.path.insert(0, str(LIVE))
  from package_store import list_installed, load_roster, save_roster, package_ready

  roster = load_roster()
  models = list(roster.get("models") or [])
  by_old: dict[str, dict] = {str(m.get("install_id")): m for m in models}
  installed = {row["model_id"]: row for row in list_installed()}

  summary = []
  for s in payload.get("slots") or []:
    action = s.get("action")
    cand = s.get("candidate")
    target_id = (cand or {}).get("model_id") if action == "replace" else s.get("model_id")
    desk = s["desk"]
    if not target_id:
      summary.append({**s, "promote": "skip_no_id"})
      continue

    # Always ensure schedule for models we want on Live
    pkg = ensure_schedule_and_package(desk, str(target_id))
    if pkg is None:
      # keep old if replace failed
      s["promote"] = "package_failed"
      if action == "replace":
        s["action"] = "keep"
        s["candidate"] = None
      summary.append({**s, "promote": "package_failed"})
      continue

    # refresh installed map
    installed = {row["model_id"]: row for row in list_installed()}
    inst = installed.get(str(target_id))
    if not inst or not inst.get("ready"):
      ready = package_ready(inst["install_id"]) if inst else {"ready": False, "error": "missing"}
      log(f"  not ready after import: {ready}")
      s["promote"] = "not_ready"
      summary.append({**s, "promote": "not_ready"})
      continue

    new_label = live_role_label(s["symbol"], s["timeframe"], s["role"])
    old_iid = str(s.get("install_id") or "")
    # Prefer book+role match (install_id can collide when multiple roles share a model).
    updated = False
    role_matches = [
      m for m in models
      if m.get("symbol") == s["symbol"]
      and m.get("timeframe") == s["timeframe"]
      and infer_role(str(m.get("label") or "")) == s["role"]
    ]
    iid_matches = [
      m for m in models
      if str(m.get("install_id")) == old_iid
      and m.get("symbol") == s["symbol"]
      and m.get("timeframe") == s["timeframe"]
      and not any(
        infer_role(str(x.get("label") or "")) == s["role"] for x in role_matches
      )
    ]
    target_row = role_matches[0] if role_matches else (iid_matches[0] if iid_matches else None)
    if target_row is not None:
      m = target_row
      m["install_id"] = inst["install_id"]
      m["model_id"] = target_id
      m["label"] = new_label
      m["symbol"] = s["symbol"]
      m["timeframe"] = s["timeframe"]
      m["enabled"] = True  # winners with schedule go On
      m["ready"] = True
      m["has_schedule"] = True
      updated = True
    if not updated:
      models.append({
        "install_id": inst["install_id"],
        "model_id": target_id,
        "label": new_label,
        "symbol": s["symbol"],
        "timeframe": s["timeframe"],
        "enabled": True,
        "risk_pct": 1.0,
        "magic": None,
      })
    s["promote"] = "ok"
    s["new_install_id"] = inst["install_id"]
    s["new_model_id"] = target_id
    s["new_live_label"] = new_label
    summary.append(s)
    log(f"PROMOTE {s['symbol']} {s['timeframe']} {s['role']} → {new_label} ({target_id})")

  # Disable incomplete leftovers
  from package_store import sanitize_roster_models
  cleaned, warns = sanitize_roster_models(models)
  for w in warns:
    log(f"roster sanitize: {w}")
  save_roster(cleaned, active_book=roster.get("active_book"))
  payload["promote_summary"] = [
    {
      "symbol": s.get("symbol"),
      "timeframe": s.get("timeframe"),
      "role": s.get("role"),
      "action": s.get("action"),
      "promote": s.get("promote"),
      "new_model_id": s.get("new_model_id"),
      "candidate": s.get("candidate"),
      "baseline": s.get("baseline"),
    }
    for s in payload.get("slots") or []
  ]
  payload["updated_at"] = _now()
  _write(REPORT_JSON, payload)
  write_report_md(payload)
  return payload


def main() -> int:
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--pass1", action="store_true")
  ap.add_argument("--pass2", action="store_true")
  ap.add_argument("--promote", action="store_true")
  ap.add_argument("--all", action="store_true", help="pass1+pass2+promote")
  ap.add_argument("--workers", type=int, default=4)
  args = ap.parse_args()
  if args.all:
    args.pass1 = args.pass2 = args.promote = True
  if not (args.pass1 or args.pass2 or args.promote):
    args.pass1 = True

  slots = load_roster_slots()
  log(f"Loaded {len(slots)} Live roster slots")
  payload = _read(REPORT_JSON) or {}

  if args.pass1:
    payload = pass1(slots)

  if args.pass2:
    if not payload.get("slots"):
      payload = pass1(slots)
    payload = pass2(payload, workers=args.workers)

  if args.promote:
    if not payload.get("slots"):
      payload = pass1(slots)
    # If pass1 found replaces, promote those; also package keep baselines that lack schedule
    # For keep slots that were Off due to missing schedule, still try schedule export of baseline.
    for s in payload.get("slots") or []:
      if s.get("action") == "keep":
        # still try to make baseline Live-ready if schedule missing
        s["_also_package_baseline"] = True
    payload = promote_to_live(payload)
    # Package keep baselines missing schedule so they can be re-enabled
    for s in payload.get("slots") or []:
      if s.get("action") != "keep":
        continue
      desk, mid = s["desk"], s["model_id"]
      sched = FINAL / desk / "results" / "trade_models" / f"{mid}_schedule.json"
      weekly = (_read(sched) or {}).get("weekly") if sched.exists() else None
      if weekly:
        # re-import to ensure Live has schedule copy
        ensure_schedule_and_package(desk, mid)
      else:
        log(f"KEEP {s['symbol']} {s['timeframe']} {s['role']}: exporting baseline schedule…")
        ensure_schedule_and_package(desk, mid)

    # Re-enable keep slots that are now ready
    sys.path.insert(0, str(LIVE))
    from package_store import list_installed, load_roster, save_roster, sanitize_roster_models
    installed_by_mid = {r["model_id"]: r for r in list_installed()}
    roster = load_roster()
    models = list(roster.get("models") or [])
    for s in payload.get("slots") or []:
      if s.get("action") != "keep":
        continue
      inst = installed_by_mid.get(s["model_id"])
      if not inst or not inst.get("ready"):
        continue
      for m in models:
        if (
          m.get("symbol") == s["symbol"]
          and m.get("timeframe") == s["timeframe"]
          and infer_role(str(m.get("label") or "")) == s["role"]
        ):
          m["install_id"] = inst["install_id"]
          m["model_id"] = s["model_id"]
          m["label"] = live_role_label(s["symbol"], s["timeframe"], s["role"])
          m["enabled"] = True
          break
    cleaned, warns = sanitize_roster_models(models)
    save_roster(cleaned, active_book=roster.get("active_book"))
    for w in warns:
      log(f"final sanitize: {w}")

  log(f"Done. Report: {REPORT_MD}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
