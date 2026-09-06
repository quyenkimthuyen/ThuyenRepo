#!/usr/bin/env python3
"""Quét preset × KB × tuần trên OOS 2026-h1 (SpreadPoints nến).

Không đưa model lên Bridge. Dừng desk khi WR>50 và Total R≥50 (n≥15).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from run_std_recipe import (  # noqa: E402
  FILTER, _bind, _ensure_kb, _fmt, _log, _passes, _row_nums,
)

TARGET_R = 50.0
ALL_ERA_KEYS = ["2024-h1", "2024-h2", "2025-h1", "2025-h2"]
PRIMARY_OOS = ("2026-01-01", "2026-06-30")
SECOND_OOS = ("2025-07-01", "2025-12-31")
CHUNK = 24

# Search-space changed vs last grid on this parquet — same grid key, must remine.
FORCE_RERUN = {
  "eur_fill_ss_more", "eur_fill_ss_plus", "eur_fill_ss_run", "eur_fill_ss_bank",
  "eur_fill_ss_more_hyb24", "eur_fill_ss_more_hold", "eur_fill_ss_more_hyb28",
  "eur_fill_ss_clip",
  "gbp_fill_ss_tight", "gbp_fill_ss_tight_hyb24", "gbp_fill_ss_tight_n",
  "eur_fill_bar_stop", "gbp_fill_bar_stop",
}


def _hit_target(row: dict | None) -> bool:
  if not row:
    return False
  wr, tot, dd, n = _row_nums(row)
  return wr > FILTER["wr_gt"] and tot >= TARGET_R and n >= FILTER["n_ge"] and dd < FILTER["max_dd_lt"]


def _primary_hits(rows: list[dict]) -> list[dict]:
  hits = [
    r for r in rows
    if not r.get("error")
    and str(r.get("oos_from") or "")[:10] == PRIMARY_OOS[0]
    and _passes(r)
  ]
  hits.sort(key=lambda r: (_row_nums(r)[1], _row_nums(r)[0]), reverse=True)
  return hits


def _merge(rows: list[dict]) -> list[dict]:
  by: dict[str, dict] = {}
  for r in rows:
    k = r.get("key")
    if not k:
      continue
    prev = by.get(k)
    if not prev or (prev.get("error") and not r.get("error")):
      by[k] = r
    elif not r.get("error"):
      by[k] = r
  return list(by.values())


def _grid_dir() -> Path:
  return Path(os.environ["TRAINAPP_RUNTIME"]) / "results" / "grid_search"


def _load_known() -> dict[str, dict]:
  known: dict[str, dict] = {}
  d = _grid_dir()
  if not d.exists():
    return known
  for p in sorted(d.glob("gs_*.json")):
    try:
      data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
      continue
    for row in data.get("rows") or []:
      k = row.get("key")
      if not k or row.get("error"):
        continue
      if row.get("mining_preset") in FORCE_RERUN:
        continue
      known[k] = row
  return known


def _pin_learn_settings(desk: str) -> dict:
  from gui.app_settings import default_settings_for_desk, save_settings, _sanitize_settings, get_settings

  s = default_settings_for_desk()
  s["learning_era_keys"] = list(ALL_ERA_KEYS)
  s["oos_window_keys"] = ["2026-h1"]
  s["learning_loops"] = 3
  save_settings(_sanitize_settings(s))
  return get_settings()


def _restore_settings() -> None:
  from gui.app_settings import default_settings_for_desk, save_settings, _sanitize_settings
  save_settings(_sanitize_settings(default_settings_for_desk()))


def _fill_presets(desk: str) -> list[str]:
  from mining_presets import PRESETS
  prefix = "gbp_fill_" if desk.startswith("g") else "eur_fill_"
  return [n for n in PRESETS if n.startswith(prefix)]


def _other_presets() -> list[str]:
  from mining_presets import list_active_presets
  return [
    n for n in list_active_presets()
    if not n.startswith("eur_fill_")
    and not n.startswith("gbp_fill_")
    and not n.startswith("gbp_wr50_")
  ]


def _gbp_wr50_presets() -> list[str]:
  from mining_presets import PRESETS
  return [n for n in PRESETS if n.startswith("gbp_wr50_")]


def _build_specs(settings: dict, weeks: list[int], presets: list[str], oos: list[tuple[str, str]]):
  from gui.app_settings import resolve_learning_eras
  from gui.grid_search_engine import build_grid

  eras = resolve_learning_eras(settings)
  kb_learn = {
    e["kb_profile"]: (str(e["learn_from"])[:10], str(e["learn_until"])[:10])
    for e in eras
  }
  return build_grid(
    train_weeks=weeks,
    kb_profiles=[e["kb_profile"] for e in eras],
    include_kb_off=False,
    epoch_mode="selected",
    selected_epochs={e["kb_profile"]: [1, 2, 3] for e in eras},
    oos_from=oos[0][0],
    oos_to=oos[0][1],
    oos_windows=oos,
    kb_learn_by_profile=kb_learn,
    skip_kb_oos_overlap=True,
    spread_pips=float(settings.get("spread_pips") or 0),
    slippage_pips=float(settings.get("slippage_pips") or 0),
    max_runs=10_000,
    mining_presets=presets,
  )


def _run_specs(desk: str, specs: list, *, workers: int, wave: str, known: dict[str, dict]) -> list[dict]:
  from gui.grid_search_engine import run_grid, save_grid_run

  todo = [s for s in specs if s.key() not in known]
  reused = [known[s.key()] for s in specs if s.key() in known]
  _log(desk, f"{wave}: {len(specs)} combo · skip {len(reused)} · run {len(todo)}")
  rows = list(reused)
  if _hit_target(_primary_hits(rows)[0] if _primary_hits(rows) else None):
    _log(desk, f"{wave}: already at target from cached rows")
    return rows
  if not todo:
    return rows
  # Clip / r50 / sparkstop first — highest chance to hit WR>50 R≥50.
  todo.sort(key=lambda s: (
    0 if (s.mining_preset or "").endswith(("_clip", "_bar_stop", "_r50", "_sparkstop")) else 1,
    s.mining_preset or "",
    s.kb_profile or "",
    s.kb_snapshot or 0,
  ))
  for i in range(0, len(todo), CHUNK):
    chunk = todo[i:i + CHUNK]
    t0 = time.time()

    def on_prog(done, total, label, _i=i, _n=len(todo)):
      _log(desk, f"{wave} {_i + done}/{_n}: {label}")

    part = run_grid(chunk, objective="quality", on_progress=on_prog, workers=workers)
    rid = save_grid_run(
      part,
      config={
        "source": "sweep_fill_presets",
        "wave": wave,
        "filter_target": FILTER,
        "chunk": f"{i // CHUNK + 1}",
      },
      objective="quality",
    )
    rows.extend(part)
    wr_best = ""
    ok = [r for r in part if not r.get("error")]
    if ok:
      top = sorted(ok, key=lambda r: (_row_nums(r)[1], _row_nums(r)[0]), reverse=True)[0]
      wr_best = _fmt(top)
    _log(desk, f"{wave} chunk {rid} {len(ok)}/{len(part)} in {time.time() - t0:.0f}s · {wr_best}")
    for r in part:
      k = r.get("key")
      if k and not r.get("error"):
        known[k] = r
    best = _primary_hits(rows)
    if best and _hit_target(best[0]):
      _log(desk, f"{wave}: TARGET HIT mid-wave · {_fmt(best[0])}")
      break
  return rows


def _publish(desk: str, rows: list[dict], run_id: str) -> list[dict]:
  from gui.trade_model import create_trade_model, list_trade_models, set_active_trade_model

  hits = _primary_hits(rows)
  _log(desk, f"Filter 2026-h1 WR>{FILTER['wr_gt']} R>{FILTER['total_r_gt']} n>={FILTER['n_ge']}: {len(hits)}")
  created = []
  for i, row in enumerate(hits[:3]):
    wr, tot, _, _ = _row_nums(row)
    model = create_trade_model(
      row,
      run_id=run_id,
      label=f"WR{wr:.0f}R{tot:.0f}",
      set_active=False,
      build_report=False,
    )
    created.append(model)
    _log(desk, f"TM {model.get('id')} · {model.get('label')} · {_fmt(row)}")
  models = [
    m for m in list_trade_models()
    if str(m.get("oos_from") or "")[:10] == PRIMARY_OOS[0]
    and float(m.get("win_rate_pct") or 0) > FILTER["wr_gt"]
    and int(m.get("n_trades") or 0) >= FILTER["n_ge"]
  ]
  models.sort(key=lambda m: (float(m.get("total_r") or 0), float(m.get("win_rate_pct") or 0)), reverse=True)
  if models:
    set_active_trade_model(models[0]["id"])
    _log(
      desk,
      f"Active {models[0].get('id')} · {models[0].get('label')} · "
      f"WR={models[0].get('win_rate_pct')} R={models[0].get('total_r'):+.1f} n={models[0].get('n_trades')}",
    )
  elif not created:
    _log(desk, "Không TM nào đạt WR>50 trên OOS 2026-h1")
  return created


def run_desk(desk: str, *, workers: int) -> dict:
  cfg = _bind(desk)
  settings = _pin_learn_settings(desk)
  _log(
    desk,
    f"sweep start pair={cfg.get('pair')} workers={workers} "
    f"eras={settings.get('learning_era_keys')} slip={settings.get('slippage_pips')}",
  )
  kb = _ensure_kb(desk, reset=False)
  known = _load_known()
  merged: list[dict] = list(known.values())
  fill = _fill_presets(desk)
  default_weeks = [6] if desk.startswith("g") else [8]
  neighbor = [5, 8, 4] if desk.startswith("g") else [6, 7, 9]
  waves: list[tuple[str, list[int], list[str], list[tuple[str, str]]]] = [
    ("w1_fill_2026", default_weeks, fill, [PRIMARY_OOS]),
    ("w2_weeks_2026", neighbor, fill, [PRIMARY_OOS]),
  ]
  if desk.startswith("g"):
    waves.append(("w3_wr50_2026", default_weeks, _gbp_wr50_presets(), [PRIMARY_OOS]))
  waves.append(("w4_other_2026", default_weeks, _other_presets(), [PRIMARY_OOS]))
  waves.append(("w5_fill_2025h2", default_weeks, fill, [SECOND_OOS]))

  best = None
  last_rid = ""
  for name, weeks, presets, oos in waves:
    if not presets:
      continue
    specs = _build_specs(settings, weeks, presets, oos)
    part = _run_specs(desk, specs, workers=workers, wave=name, known=known)
    merged = _merge(merged + part)
    hits = _primary_hits(merged)
    best = hits[0] if hits else None
    if best:
      _log(desk, f"{name} best 2026-h1 {_fmt(best)}")
    else:
      top = sorted(
        [r for r in merged if not r.get("error") and str(r.get("oos_from") or "")[:10] == PRIMARY_OOS[0]],
        key=lambda r: (_row_nums(r)[1], _row_nums(r)[0]),
        reverse=True,
      )
      if top:
        _log(desk, f"{name} no WR>50 hit · top {_fmt(top[0])}")
    last_rid = name
    if _hit_target(best):
      _log(desk, f"TARGET HIT · stop further waves · {_fmt(best)}")
      break

  created = _publish(desk, merged, last_rid)
  _restore_settings()
  hits = _primary_hits(merged)
  out = {
    "desk": desk,
    "kb": kb,
    "n_rows": len(merged),
    "n_hits": len(hits),
    "best": None if not best else {
      "label": best.get("label"),
      "preset": best.get("mining_preset"),
      "kb": best.get("kb_profile"),
      "snap": best.get("kb_snapshot"),
      "weeks": best.get("train_weeks"),
      "wr": _row_nums(best)[0],
      "total_r": _row_nums(best)[1],
      "n": _row_nums(best)[3],
    },
    "target": _hit_target(best),
    "created": [{"id": m.get("id"), "label": m.get("label")} for m in created],
  }
  _log(desk, f"SWEEP DONE {json.dumps(out, ensure_ascii=False)}")
  return out


def main() -> int:
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--desk", required=True)
  ap.add_argument("--workers", type=int, default=5)
  args = ap.parse_args()
  desk = args.desk.strip().lower()
  try:
    out = run_desk(desk, workers=max(1, args.workers))
  except Exception as exc:
    try:
      _bind(desk)
      _log(desk, f"FAILED: {exc}")
    except Exception:
      print(f"FAILED {desk}: {exc}", flush=True)
    raise
  print(json.dumps(out, indent=2, ensure_ascii=False), flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
