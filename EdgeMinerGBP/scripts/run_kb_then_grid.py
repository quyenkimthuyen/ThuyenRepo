#!/usr/bin/env python3
"""Huấn luyện KB theo Cài đặt → chạy Grid Search."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LOG = ROOT / "results" / "pipeline_run.log"


def log(msg: str):
  line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
  print(line, flush=True)
  LOG.parent.mkdir(parents=True, exist_ok=True)
  with open(LOG, "a", encoding="utf-8") as f:
    f.write(line + "\n")


def run_learning(
  profile_id: str,
  name: str,
  from_date: str,
  until_date: str,
  epochs: int,
  *,
  reset: bool = False,
):
  mode = "reset + học" if reset else "học tiếp (giữ KB)"
  log(f"=== Học KB: {profile_id} ({epochs} vòng · {mode}) ===")
  cmd = [
    sys.executable, str(ROOT / "run_learning.py"),
    "--epochs", str(epochs),
    "--kb-profile", profile_id,
    "--kb-name", name,
    "--from-date", from_date,
    "--until-date", until_date,
  ]
  if reset:
    cmd.append("--reset")
  subprocess.run(cmd, cwd=str(ROOT), check=True)


def run_grid():
  from gui.app_settings import get_settings
  from gui.grid_search_engine import (
    build_grid_from_settings,
    grid_readiness,
    run_grid,
    save_grid_run,
  )

  r = grid_readiness()
  log(f"Grid readiness: {r['ready_combos']}/{r['expected_combos']} kb_complete={r['kb_complete']}")
  if not r["kb_complete"]:
    raise RuntimeError(f"KB chưa đủ: {r}")

  specs, config = build_grid_from_settings()
  objective = get_settings().get("grid_objective", "total_r")
  log(f"=== Grid Search: {len(specs)} combo · mục tiêu {objective} ===")

  def on_prog(done, total, label):
    log(f"Grid {done}/{total}: {label}")

  rows = run_grid(
    specs,
    objective=objective,
    reopt_period=config.get("reopt_period", "week"),
    on_progress=on_prog,
  )
  rid = save_grid_run(rows, config=config, objective=objective)
  ok = [x for x in rows if not x.get("error")]
  log(f"Grid xong: {rid} · {len(ok)}/{len(rows)} combo OK")
  if ok:
    best = ok[0]
    log(f"Best: {best.get('label')} · {best.get('total_r')}R")
  return rid


def setup_gui_reports(*, reset_models: bool = True):
  """Tạo Trade Model + báo cáo đầy đủ cho tab Phân tích trên GUI."""
  from gui.app_settings import get_settings
  from gui.grid_search_engine import load_latest_grid_run
  from gui.services import execute_backtest
  from gui.trade_model import (
    create_trade_model,
    save_active_model_id,
    save_model_report,
    save_models_store,
  )

  latest = load_latest_grid_run()
  rows = [r for r in (latest or {}).get("rows", []) if not r.get("error")]
  if not rows:
    raise RuntimeError("Grid không có kết quả hợp lệ")

  best = rows[0]
  run_id = latest.get("run_id")
  log(f"=== Tạo Trade Model từ grid best: {best.get('label')} ===")

  if reset_models:
    save_models_store({"models": []})

  model = create_trade_model(
    best,
    run_id=run_id,
    set_active=False,
    build_report=False,
  )

  s = get_settings()
  log("=== Backtest đầy đủ cho báo cáo Phân tích ===")
  report = execute_backtest(
    use_learning=bool(best.get("use_kb", True)),
    train_months=int(best["train_months"]),
    kb_profile=best.get("kb_profile"),
    kb_snapshot=best.get("kb_snapshot"),
    oos_from=best.get("oos_from") or s.get("backtest_from"),
    oos_to=best.get("oos_to") or s.get("backtest_to"),
    spread_pips=float(best.get("spread_pips", s.get("spread_pips", 1.0))),
    slippage_pips=float(best.get("slippage_pips", s.get("slippage_pips", 0.3))),
    sync_workspace=True,
  )
  report.setdefault("config", {})["trade_model_id"] = model["id"]
  save_model_report(model["id"], report)
  save_active_model_id(model["id"])

  oos = report.get("overall_oos") or {}
  log(
    f"Trade model: {model['id']} · "
    f"{oos.get('total_r')}R · {oos.get('n_trades')} lệnh · "
    f"báo cáo → results/trade_models/{model['id']}.json"
  )
  return model["id"]


def main():
  import argparse
  parser = argparse.ArgumentParser(description="Huấn luyện KB → Grid Search → báo cáo GUI")
  parser.add_argument("--reset", action="store_true", help="Xóa KB trước khi học (mặc định: học tiếp)")
  parser.add_argument("--skip-learning", action="store_true", help="Chỉ chạy grid + báo cáo")
  args = parser.parse_args()

  from gui.app_settings import get_settings, resolve_learning_eras

  # Dọn job GUI kẹt
  job_path = ROOT / "results" / "jobs" / "long_task_state.json"
  if job_path.exists():
    try:
      data = json.loads(job_path.read_text(encoding="utf-8"))
      if data.get("status") == "running":
        data["status"] = "interrupted"
        data["error"] = "Thay bằng pipeline CLI"
        job_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        log("Đã đánh dấu job GUI cũ là interrupted")
    except Exception:
      pass

  s = get_settings()
  loops = int(s.get("learning_loops") or 4)
  eras = resolve_learning_eras(s)
  reset_note = "reset KB" if args.reset else "giữ KB"
  log(
    f"Settings: {[e['kb_profile'] for e in eras]} · {loops} vòng · "
    f"OOS {s.get('backtest_from')}–{s.get('backtest_to')} · {reset_note}"
  )

  if not args.skip_learning:
    for era in eras:
      run_learning(
        era["kb_profile"],
        era["label"],
        era["learn_from"],
        era["learn_until"],
        loops,
        reset=args.reset,
      )
  else:
    log("Bỏ qua học KB (--skip-learning)")

  run_grid()
  setup_gui_reports(reset_models=True)
  log("=== HOÀN TẤT — mở GUI (python3 run_gui.py) để xem Phân tích ===")
  return 0


if __name__ == "__main__":
  sys.exit(main())
