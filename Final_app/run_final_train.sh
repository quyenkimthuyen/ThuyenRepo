#!/usr/bin/env bash
# Train all Final_app desks from scratch (GUIDE playbook): KB → Grid → Promote.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PY:-/home/thuyenng/work/ThuyenRepo/EdgeMinerM15B5/.venv/bin/python}"
LOG="$ROOT/final_train.log"

desks=(
  EdgeMinerEURUSDM15
  EdgeMinerGBPUSDM15
  EdgeMinerEURUSDM5
  EdgeMinerGBPUSDM5
)

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

promote() {
  local desk="$1"
  "$PY" - <<PY
import sys
from pathlib import Path
ROOT = Path("$ROOT/$desk")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
try:
  from bootstrap_m5_pipeline import promote_top
except ImportError:
  # M15 desks may lack bootstrap — inline minimal promote
  from gui.grid_search_engine import load_latest_grid_run, _score
  from gui.trade_model import model_from_grid_row, save_models_store, load_models_store, set_active_trade_model
  run = load_latest_grid_run()
  rows = [r for r in (run or {}).get("rows") or [] if not r.get("error")]
  rows = sorted(rows, key=lambda r: _score(r, "quality"), reverse=True)[:5]
  store = load_models_store()
  models = list(store.get("models") or [])
  labels = ["BestQuality", "BestBalance", "BestTotalR", "BestWinRate", "BestPF"]
  promoted = []
  for i, row in enumerate(rows):
    lab = labels[i] if i < len(labels) else f"Top{i+1}"
    m = model_from_grid_row(row, run_id=(run or {}).get("id"), label=lab)
    # ensure oos window
    m["oos_from"] = "2026-01-01"
    m["oos_to"] = "2026-08-07"
    m["label"] = lab
    m["label_custom"] = True
    from gui.trade_model import _new_id
    m["id"] = _new_id(lab)
    models.append(m)
    promoted.append(lab)
  store["models"] = models
  save_models_store(store)
  if models:
    set_active_trade_model(models[0].get("id"))
  print("promoted", promoted)
else:
  out = promote_top(5)
  print("promoted", [x.get("label") for x in out])
PY
}

log "==== Final_app train start ===="
for desk in "${desks[@]}"; do
  d="$ROOT/$desk"
  if [[ ! -d "$d" ]]; then
    log "MISSING $desk — run bootstrap_clone_clean.py first"
    exit 1
  fi
  log "==== KB+Grid $desk ===="
  (cd "$d" && "$PY" scripts/run_kb_then_grid.py) 2>&1 | tee -a "$LOG"
  log "==== Promote $desk ===="
  promote "$desk" 2>&1 | tee -a "$LOG"
  log "==== Unify OOS $desk ===="
  if [[ -f "$d/scripts/unify_oos_compare.py" ]]; then
    (cd "$d" && "$PY" scripts/unify_oos_compare.py) 2>&1 | tee -a "$LOG" || log "unify skip/fail $desk"
  else
    log "no unify script on $desk — copy from source if needed"
  fi
done

log "==== Cross Pareto Final_app ===="
"$PY" "$ROOT/build_final_pareto.py" 2>&1 | tee -a "$LOG"
log "==== Final_app train DONE ===="
log "See $ROOT/results_final_guide_validation.md"
