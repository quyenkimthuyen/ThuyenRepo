"""One-shot: học lại KB e21 (reset) rồi grid theo Cài đặt. Không đụng g23."""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from desk_context import apply_desk_env

cfg = apply_desk_env("e21")
core = Path(cfg["core_root"])
for p in (str(ROOT), str(core)):
  if p in sys.path:
    sys.path.remove(p)
  sys.path.insert(0, p)
os.environ["PYTHONUNBUFFERED"] = "1"


def log(msg: str) -> None:
  print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def main() -> int:
  from gui.app_settings import get_settings, resolve_learning_eras, settings_grid_signature
  from gui.era_compare import ensure_profile_learned
  from gui.grid_search_engine import build_grid_from_settings, run_grid, save_grid_run
  from config import DEFAULT_TF

  settings = get_settings()
  eras = resolve_learning_eras(settings)
  loops = int(settings.get("learning_loops") or 2)
  log(
    f"e21 relearn fill-contract · eras={[e['kb_profile'] for e in eras]} "
    f"loops={loops} weeks={settings.get('strategy_train_weeks')} "
    f"presets={settings.get('mining_presets')} "
    f"oos={settings.get('backtest_from')}→{settings.get('backtest_to')}"
  )
  if not eras:
    raise SystemExit("Cài đặt e21 chưa chọn era nào")

  for era in eras:
    log(f"KB learn {era['kb_profile']} reset=True")
    out = ensure_profile_learned(
      {
        "kb_profile": era["kb_profile"],
        "kb_name": era.get("label") or era["kb_profile"],
        "learn_from": era["learn_from"],
        "learn_until": era["learn_until"],
      },
      epochs=loops,
      reset=True,
    )
    log(f"KB done {era['kb_profile']} skipped={bool(out.get('skipped'))}")

  specs, config = build_grid_from_settings(settings)
  log(f"Grid start {len(specs)} combo")

  def on_prog(i, total, label):
    log(f"Grid {i}/{total}: {label}")

  objective = str(settings.get("grid_objective") or "quality")
  rows = run_grid(specs, objective=objective, on_progress=on_prog, workers=1)
  rid = save_grid_run(
    rows,
    config={
      **config,
      "timeframe": DEFAULT_TF,
      "source": "fill_contract_relearn",
      "settings_signature": settings_grid_signature(settings),
    },
    objective=objective,
  )
  ok = [x for x in rows if not x.get("error")]
  log(f"Grid done {rid} · {len(ok)}/{len(rows)} OK")
  if ok:
    best = ok[0]
    log(
      f"Best {best.get('label')} · R={best.get('total_r')} "
      f"WR={best.get('win_rate_pct')} n={best.get('n_trades')}"
    )
  log("HOAN TAT")
  return 0


if __name__ == "__main__":
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass
  raise SystemExit(main())
