#!/usr/bin/env python3
"""Re-rank all improve grid runs with current scoring and promote best if better."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
  from gui.edge_improve import maybe_promote_grid_best
  from gui.grid_search_engine import LATEST_PATH, RUNS_DIR, _score
  from gui.trade_model import get_active_trade_model, load_model_report

  objective = "risk_adjusted"
  runs = sorted(RUNS_DIR.glob("gs_improve_*.json"))
  if not runs:
    print("No improve runs found")
    return 1

  candidates: list[tuple[float, float, dict, Path]] = []
  for path in runs:
    try:
      data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
      continue
    rows = [r for r in (data.get("rows") or []) if not r.get("error")]
    if not rows:
      continue
    for r in rows:
      r["risk_adjusted"] = round(_score(r, objective), 3)
    rows.sort(key=lambda r: (_score(r, objective), float(r.get("total_r") or 0)), reverse=True)
    data["rows"] = rows
    data["best"] = rows[0]
    data["objective"] = objective
    data["re_ranked_at"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
      f"{path.name}: best={rows[0].get('total_r')}R RA={rows[0].get('risk_adjusted')} "
      f"tw/w={rows[0].get('trades_per_week')} · {rows[0].get('label')}"
    )
    for r in rows:
      sc = float(_score(r, objective))
      if sc <= -1e11:
        continue
      candidates.append((sc, float(r.get("total_r") or 0), r, path))

  if not candidates:
    print("No usable rows")
    return 1

  # Global: near-best RA (±5%), then highest total_r
  candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
  top_ra = candidates[0][0]
  near = [t for t in candidates if t[0] >= top_ra * 0.95]
  near.sort(key=lambda t: t[1], reverse=True)
  best_sc, best_r, best_row, best_path = near[0]

  payload = json.loads(best_path.read_text(encoding="utf-8"))
  payload["best"] = best_row
  payload["rows"] = sorted(
    payload.get("rows") or [],
    key=lambda r: (_score(r, objective), float(r.get("total_r") or 0)),
    reverse=True,
  )
  payload["global_pick"] = {
    "total_r": best_row.get("total_r"),
    "risk_adjusted": best_row.get("risk_adjusted"),
    "key": best_row.get("key"),
    "from_run": best_path.name,
  }
  LATEST_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  print(
    f"Global pick → {best_path.name} · {best_r}R RA={best_sc:.3f} · {best_row.get('label')}"
  )

  active = get_active_trade_model()
  aid = (active or {}).get("id")
  ar = ((load_model_report(aid) or {}).get("overall_oos") or {}).get("total_r")
  print(f"Active before: {aid} · {ar}R")

  promo = maybe_promote_grid_best(objective=objective, require_better_than_active=True)
  if not promo.get("ok") and ar is not None and best_r > float(ar) + 5:
    promo = maybe_promote_grid_best(objective=objective, require_better_than_active=False)
    print(
      f"Force promote by total_r: ok={promo.get('ok')} "
      f"id={None if not promo.get('model') else promo['model'].get('id')}"
    )
  elif promo.get("ok"):
    print(f"Promoted: {promo.get('model', {}).get('id')} · {promo.get('best', {}).get('total_r')}R")
  else:
    print(f"No promote: {promo}")

  active2 = get_active_trade_model()
  print(
    f"Active after: {(active2 or {}).get('id')} · {(active2 or {}).get('total_r')}R "
    f"label={(active2 or {}).get('label')}"
  )
  return 0


if __name__ == "__main__":
  sys.exit(main())
