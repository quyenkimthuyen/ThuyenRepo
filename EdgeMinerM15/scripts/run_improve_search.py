#!/usr/bin/env python3
"""Multi-pass improve: Live↔OOS feedback → (optional KB) → grid variants → promote best."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LOG = ROOT / "results" / "improve_search.log"
SUMMARY = ROOT / "results" / "improve_search_summary.json"


def log(msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
  print(line, flush=True)
  LOG.parent.mkdir(parents=True, exist_ok=True)
  with open(LOG, "a", encoding="utf-8") as f:
    f.write(line + "\n")


def _interrupt_gui_job() -> None:
  job_path = ROOT / "results" / "jobs" / "long_task_state.json"
  if not job_path.exists():
    return
  try:
    data = json.loads(job_path.read_text(encoding="utf-8"))
    if data.get("status") == "running":
      data["status"] = "interrupted"
      data["error"] = "Thay bằng improve_search CLI"
      job_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
      log("Đã đánh dấu job GUI cũ là interrupted")
  except Exception:
    pass


def run_learning_continue(
  profile_id: str, name: str, from_date: str, until_date: str, epochs: int,
) -> None:
  """Continue KB without --reset (extra epochs for later grid snapshots)."""
  log(f"=== Học KB thêm: {profile_id} (+{epochs} vòng, không reset) ===")
  cmd = [
    sys.executable, str(ROOT / "run_learning.py"),
    "--epochs", str(epochs),
    "--kb-profile", profile_id,
    "--kb-name", name,
    "--from-date", from_date,
  ]
  if until_date:
    cmd.extend(["--until-date", until_date])
  subprocess.run(cmd, cwd=str(ROOT), check=True)


def run_grid_pass(space_name: str, search_space, *, objective: str, specs, config: dict) -> dict:
  from gui.grid_search_engine import run_grid, save_grid_run
  from strategy_miner import mining_search_space_to_dict

  log(f"=== Grid pass `{space_name}`: {len(specs)} combo · {objective} ===")

  def on_prog(done, total, label):
    log(f"[{space_name}] {done}/{total}: {label}")

  rows = run_grid(
    specs, objective=objective, on_progress=on_prog, search_space=search_space,
  )
  rid = save_grid_run(
    rows,
    config={
      **config,
      "timeframe": "M15",
      "search_space_name": space_name,
      "mining_search_space": mining_search_space_to_dict(search_space),
      "improve_pass": True,
    },
    objective=objective,
    run_id=f"gs_improve_{space_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
  )
  ok = [x for x in rows if not x.get("error")]
  best = ok[0] if ok else None
  log(
    f"Pass `{space_name}` xong: {rid} · "
    f"{len(ok)}/{len(rows)} OK · best={None if not best else best.get('total_r')}R"
  )
  return {
    "space_name": space_name,
    "run_id": rid,
    "best": best,
    "n_ok": len(ok),
    "n_rows": len(rows),
  }


def _score_row(row: dict | None, objective: str) -> float:
  from gui.grid_search_engine import _score
  if not row or row.get("error"):
    return -1e18
  return float(_score(row, objective))


def _point_latest_to(run_id: str) -> None:
  from gui.grid_search_engine import LATEST_PATH, RUNS_DIR
  best_path = RUNS_DIR / f"{run_id}.json"
  if best_path.exists():
    LATEST_PATH.write_text(best_path.read_text(encoding="utf-8"), encoding="utf-8")


def main() -> int:
  from gui.app_settings import get_settings, grid_build_kwargs, resolve_learning_eras
  from gui.edge_improve import (
    alternate_mining_search_spaces,
    build_live_oos_feedback,
    health_gate_active_model,
    maybe_promote_grid_best,
  )
  from gui.grid_search_engine import build_grid, build_grid_from_settings, grid_readiness
  from gui.trade_model import get_active_trade_model, load_model_report
  from kb_profiles import get_profile

  _interrupt_gui_job()
  s = get_settings()
  objective = s.get("grid_objective") or "risk_adjusted"
  eras = resolve_learning_eras(s)
  active0 = get_active_trade_model()
  active0_id = (active0 or {}).get("id")
  active0_r = ((load_model_report(active0_id) or {}).get("overall_oos") or {}).get("total_r")
  if active0_r is None:
    active0_r = (active0 or {}).get("total_r")

  log(
    f"Start improve_search · active={active0_id} · {active0_r}R · "
    f"eras={[e['kb_profile'] for e in eras]} · objective={objective}"
  )

  try:
    fb = build_live_oos_feedback(source="live")
    log(
      f"Live↔OOS feedback: weeks={fb.get('n_weeks_compared')} "
      f"mean_edge={fb.get('mean_edge_r')} tips={fb.get('suggestions')}"
    )
  except Exception as e:
    log(f"Feedback skip: {e}")

  readiness = grid_readiness()
  log(
    f"KB readiness: {readiness.get('ready_combos')}/{readiness.get('expected_combos')} "
    f"complete={readiness.get('kb_complete')}"
  )

  if not readiness.get("kb_complete"):
    from scripts.run_kb_then_grid import run_learning
    loops = int(s.get("learning_loops") or 4)
    for era in eras:
      run_learning(
        era["kb_profile"], era["label"], era["learn_from"], era["learn_until"], loops,
      )
  else:
    log("KB đã đủ — bỏ qua reset; chạy multi-pass grid với search space mới.")

  specs, config = build_grid_from_settings()
  passes: list[dict] = []
  spaces = alternate_mining_search_spaces()

  for name, space in spaces:
    passes.append(run_grid_pass(name, space, objective=objective, specs=specs, config=config))

  best_pass = max(passes, key=lambda p: _score_row(p.get("best"), objective))
  best_row = best_pass.get("best")
  log(
    f"Global best pass=`{best_pass.get('space_name')}` · "
    f"{None if not best_row else best_row.get('total_r')}R · "
    f"key={None if not best_row else best_row.get('key')}"
  )
  _point_latest_to(best_pass["run_id"])

  promo = maybe_promote_grid_best(objective=objective, require_better_than_active=True)
  log(f"Promote (strict): ok={promo.get('ok')} reason={promo.get('reason')}")

  if not promo.get("ok"):
    log("Chưa promote — học thêm 2 vòng KB rồi grid lại space tốt nhất.")
    for era in eras:
      try:
        run_learning_continue(
          era["kb_profile"], era["label"], era["learn_from"], era["learn_until"], 2,
        )
      except Exception as e:
        log(f"Continue learn fail {era['kb_profile']}: {e}")

    kw = grid_build_kwargs(s)
    selected: dict[str, list[int]] = {}
    for era in eras:
      pid = era["kb_profile"]
      snaps = [
        int(x.get("cumulative"))
        for x in ((get_profile(pid) or {}).get("snapshots") or [])
        if x.get("cumulative") is not None
      ]
      have = max(snaps) if snaps else int((get_profile(pid) or {}).get("epochs") or 0)
      selected[pid] = list(range(1, max(1, have) + 1))
    kw["selected_epochs"] = selected
    kw["epoch_mode"] = "selected"
    allowed = {
      "train_weeks", "kb_profiles", "include_kb_off", "epoch_mode",
      "selected_epochs", "oos_from", "oos_to", "spread_pips", "slippage_pips",
      "max_runs",
    }
    specs2 = build_grid(**{k: v for k, v in kw.items() if k in allowed})
    if len(specs2) > 40:
      # Prefer higher epochs + keep all train_weeks
      specs2 = sorted(
        specs2,
        key=lambda sp: (sp.kb_snapshot or 0, sp.train_weeks or 0),
        reverse=True,
      )[:40]
      log(f"Cắt specs2 còn {len(specs2)} combo (ưu tiên epoch cao)")

    space_map = dict(spaces)
    space_name = best_pass.get("space_name") or spaces[0][0]
    space = space_map.get(space_name) or spaces[0][1]
    extra = run_grid_pass(
      f"{space_name}_kb_extra",
      space,
      objective=objective,
      specs=specs2,
      config={**config, "selected_epochs": selected, "kb_extra": True},
    )
    passes.append(extra)
    best_pass = max(passes, key=lambda p: _score_row(p.get("best"), objective))
    best_row = best_pass.get("best")
    _point_latest_to(best_pass["run_id"])
    promo = maybe_promote_grid_best(objective=objective, require_better_than_active=True)
    log(f"Promote after KB extra: ok={promo.get('ok')} reason={promo.get('reason')}")

  gate = health_gate_active_model()
  log(
    f"Health gate: verdict={gate.get('health', {}).get('verdict')} "
    f"promoted={None if not gate.get('promoted') else gate['promoted'].get('ok')}"
  )

  active1 = get_active_trade_model()
  active1_id = (active1 or {}).get("id")
  active1_r = ((load_model_report(active1_id) or {}).get("overall_oos") or {}).get("total_r")
  if active1_r is None:
    active1_r = (active1 or {}).get("total_r")

  summary = {
    "updated_at": datetime.now().isoformat(timespec="seconds"),
    "objective": objective,
    "active_before": {"id": active0_id, "total_r": active0_r},
    "active_after": {"id": active1_id, "total_r": active1_r},
    "best_pass": best_pass.get("space_name"),
    "best_row": {
      k: (best_row or {}).get(k)
      for k in (
        "key", "label", "total_r", "win_rate_pct", "n_trades",
        "max_drawdown_r", "risk_adjusted", "kb_profile", "kb_snapshot", "train_weeks",
      )
    } if best_row else None,
    "passes": [
      {
        "space_name": p["space_name"],
        "run_id": p["run_id"],
        "best_r": None if not p.get("best") else p["best"].get("total_r"),
        "best_key": None if not p.get("best") else p["best"].get("key"),
        "n_ok": p["n_ok"],
      }
      for p in passes
    ],
    "promote": {
      "ok": promo.get("ok"),
      "reason": promo.get("reason"),
      "model_id": None if not promo.get("model") else promo["model"].get("id"),
    },
    "health_gate": {
      "verdict": gate.get("health", {}).get("verdict"),
      "promoted_ok": None if not gate.get("promoted") else gate["promoted"].get("ok"),
    },
  }
  SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  log(f"Summary → {SUMMARY}")
  log(
    f"=== HOÀN TẤT · active {active0_id} ({active0_r}R) → "
    f"{active1_id} ({active1_r}R) · best_pass={best_pass.get('space_name')} ==="
  )
  return 0


if __name__ == "__main__":
  sys.exit(main())
