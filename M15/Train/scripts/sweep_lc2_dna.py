#!/usr/bin/env python3
"""Remine LiveCheck2 best-model DNA on M15 e21.

Score only OOS 2026-h1 (not LC2's 12-month window). Learn era_2025_full
for the sweep without putting 12-month learn into Settings Reset.
Does not touch the MT5 Bridge or desk g23.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from run_std_recipe import (  # noqa: E402
  _bind, _ensure_kb, _fmt, _log, _passes, _row_nums,
)
from sweep_fill_presets import (  # noqa: E402
  PRIMARY_OOS, _hit_target, _primary_hits, _publish, _run_specs,
)

ERA_2025_FULL = {
  "key": "2025-full",
  "label": "2025 (12 tháng)",
  "learn_from": "2025-01-01",
  "learn_until": "2025-12-31",
  "kb_profile": "era_2025_full",
}
ERA_KEYS = ["2025-h1", "2025-full"]
WEEKS = [8, 12]


def _pin_learn_settings() -> dict:
  from gui.app_settings import default_settings_for_desk, save_settings, _sanitize_settings, get_settings
  from mining_presets import LC2_DNA_PRESETS

  s = default_settings_for_desk()
  catalog = list(s.get("learning_eras") or [])
  if not any(str(e.get("key")) == "2025-full" for e in catalog):
    catalog.append(dict(ERA_2025_FULL))
  s["learning_eras"] = catalog
  s["learning_era_keys"] = list(ERA_KEYS)
  s["oos_window_keys"] = ["2026-h1"]
  s["strategy_train_weeks"] = list(WEEKS)
  s["mining_presets"] = list(LC2_DNA_PRESETS)
  s["learning_loops"] = 3
  save_settings(_sanitize_settings(s))
  return get_settings()


def _restore_settings(winner: dict | None) -> None:
  from gui.app_settings import default_settings_for_desk, save_settings, _sanitize_settings

  s = default_settings_for_desk()
  if winner and not winner.get("error"):
    preset = str(winner.get("mining_preset") or "")
    weeks = int(winner.get("train_weeks") or 8)
    kb = str(winner.get("kb_profile") or "")
    if preset:
      s["mining_presets"] = [preset] + [p for p in s["mining_presets"] if p != preset]
    if weeks in (6, 7, 8, 9, 12):
      s["strategy_train_weeks"] = [weeks]
    era_key = kb.replace("era_", "").replace("_", "-") if kb.startswith("era_") else ""
    if kb == "era_2025_full":
      catalog = list(s.get("learning_eras") or [])
      if not any(str(e.get("key")) == "2025-full" for e in catalog):
        catalog.append(dict(ERA_2025_FULL))
      s["learning_eras"] = catalog
      s["learning_era_keys"] = ["2025-full"]
    elif era_key:
      s["learning_era_keys"] = [era_key]
  save_settings(_sanitize_settings(s))


def _build_specs(settings: dict, weeks: list[int], presets: list[str]):
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
    oos_from=PRIMARY_OOS[0],
    oos_to=PRIMARY_OOS[1],
    oos_windows=[PRIMARY_OOS],
    kb_learn_by_profile=kb_learn,
    skip_kb_oos_overlap=True,
    spread_pips=float(settings.get("spread_pips") or 0),
    slippage_pips=float(settings.get("slippage_pips") or 0),
    max_runs=10_000,
    mining_presets=presets,
  )


def _priority(preset: str) -> int:
  if preset.endswith("_clip"):
    return 0
  if preset.endswith("_bar"):
    return 1
  return 2


def run_desk(*, workers: int) -> dict:
  desk = "e21"
  cfg = _bind(desk)
  from mining_presets import LC2_DNA_PRESETS
  from sweep_fill_presets import _load_known
  settings = _pin_learn_settings()
  _log(
    desk,
    f"lc2 dna start pair={cfg.get('pair')} workers={workers} "
    f"eras={settings.get('learning_era_keys')} weeks={WEEKS} "
    f"presets={list(LC2_DNA_PRESETS)}",
  )
  kb = _ensure_kb(desk, reset=False)
  known = _load_known()
  presets = sorted(LC2_DNA_PRESETS, key=_priority)
  specs = _build_specs(settings, WEEKS, presets)
  rows = _run_specs(desk, specs, workers=workers, wave="lc2_dna_2026h1", known=known)
  lc2_hits = _primary_hits(rows)
  best_lc2 = lc2_hits[0] if lc2_hits else None
  created = _publish(desk, rows, "lc2_dna_2026h1")
  pin = None
  if best_lc2 and _passes(best_lc2):
    _, tot, _, _ = _row_nums(best_lc2)
    if _hit_target(best_lc2) or tot > 31.688:
      pin = best_lc2
  _restore_settings(pin)
  if best_lc2:
    _log(desk, f"lc2 dna best 2026-h1 {_fmt(best_lc2)}")
  best = best_lc2
  out = {
    "desk": desk,
    "kb": kb,
    "n_specs": len(specs),
    "n_hits": len(lc2_hits),
    "target": _hit_target(best),
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
    "created": [{"id": m.get("id"), "label": m.get("label")} for m in created],
  }
  _log(desk, f"LC2 DNA DONE {json.dumps(out, ensure_ascii=False)}")
  return out


def main() -> int:
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--workers", type=int, default=6)
  args = ap.parse_args()
  try:
    out = run_desk(workers=max(1, args.workers))
  except Exception as exc:
    try:
      _bind("e21")
      _log("e21", f"FAILED: {exc}")
    except Exception:
      print(f"FAILED e21: {exc}", flush=True)
    raise
  print(json.dumps(out, indent=2, ensure_ascii=False), flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
