#!/usr/bin/env python3
"""Chạy recipe đã chuẩn hóa: học KB theo Settings → Grid OOS 2026-h1 → tạo TM.

Không đổi weeks / preset / OOS (khác pipeline_kb_grid cũ).
Không đưa model lên Bridge.
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

from desk_context import apply_desk_env  # noqa: E402

# 6 tháng OOS: n mỏng hơn 12 tháng — không đòi n>=40 như quality score.
# tpw_gt is optional (hunt: >5 lệnh/tuần).
FILTER = {"wr_gt": 50.0, "total_r_gt": 15.0, "n_ge": 15, "max_dd_lt": 14.0}
PROMOTE_ON_BAR = False
MAX_MODELS = 3


def _purge() -> None:
  for name in list(sys.modules):
    if name in (
      "run_backtest", "knowledge_base", "config", "app_paths",
      "data_loader", "kb_profiles", "optimizer",
    ) or name.startswith("gui.") or name.startswith("mt5_bridge"):
      sys.modules.pop(name, None)


def _bind(desk: str) -> dict:
  cfg = apply_desk_env(desk)
  _purge()
  for p in (str(ROOT), str(cfg["core_root"])):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)
  # Streamlit session_state survives module purge; e21 settings must not leak to g23.
  try:
    import streamlit as st
    st.session_state.pop("app_settings", None)
    st.session_state.pop("settings_grid_signature", None)
  except Exception:
    pass
  return cfg


def _log(desk: str, msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] [{desk}] {msg}"
  try:
    print(line, flush=True)
  except UnicodeEncodeError:
    print(line.encode("ascii", "replace").decode("ascii"), flush=True)
  log_dir = Path(os.environ["TRAINAPP_RUNTIME"]) / "results"
  log_dir.mkdir(parents=True, exist_ok=True)
  with open(log_dir / "std_recipe.log", "a", encoding="utf-8") as f:
    f.write(line + "\n")


def _row_nums(row: dict) -> tuple[float, float, float, int]:
  return (
    float(row.get("win_rate_pct") or 0),
    float(row.get("total_r") or 0),
    float(row.get("max_drawdown_r") or 999),
    int(row.get("n_trades") or 0),
  )


def _passes(row: dict) -> bool:
  if row.get("error"):
    return False
  wr, tot, dd, n = _row_nums(row)
  if not (wr > FILTER["wr_gt"] and tot > FILTER["total_r_gt"] and n >= FILTER["n_ge"] and dd < FILTER["max_dd_lt"]):
    return False
  tpw_gt = FILTER.get("tpw_gt")
  if tpw_gt is not None:
    tpw = float(row.get("trades_per_week") or 0)
    if tpw <= float(tpw_gt):
      return False
  return True


def _fmt(row: dict) -> str:
  wr, tot, dd, n = _row_nums(row)
  rr = float(row.get("avg_rr") or 0)
  tpw = float(row.get("trades_per_week") or 0)
  return (
    f"WR={wr:.1f} RR={rr:.2f} R={tot:+.1f} DD={dd:.1f} n={n} tpw={tpw:.2f} · {row.get('label')}"
  )


def _ensure_kb(desk: str, *, reset: bool) -> dict:
  from gui.app_settings import get_settings, resolve_learning_eras
  from gui.era_compare import ensure_profile_learned

  s = get_settings()
  eras = resolve_learning_eras(s)
  loops = int(s.get("learning_loops") or 3)
  learned, skipped = [], []
  for era in eras:
    label = era.get("label") or era["kb_profile"]
    _log(desk, f"KB {'RESET' if reset else 'ensure'} · {label} · {loops} epoch · {era['learn_from']}→{era['learn_until']}")
    spec = {
      "kb_profile": era["kb_profile"],
      "kb_name": era.get("label") or era["kb_profile"],
      "learn_from": era["learn_from"],
      "learn_until": era["learn_until"],
    }
    t0 = time.time()
    out = ensure_profile_learned(spec, epochs=loops, reset=reset)
    if out.get("protected"):
      skipped.append(era["kb_profile"])
      _log(desk, f"KB locked skip · {era['kb_profile']} epochs={out.get('epochs')}")
    elif out.get("skipped"):
      skipped.append(era["kb_profile"])
      _log(desk, f"KB skip · {era['kb_profile']} epochs={out.get('epochs')}")
    else:
      learned.append(era["kb_profile"])
      _log(desk, f"KB done · {era['kb_profile']} in {time.time() - t0:.0f}s")
  return {"learned": learned, "skipped": skipped, "loops": loops}


def _run_grid(
  desk: str,
  *,
  workers: int,
  mining_presets: list[str] | None = None,
  era_keys: list[str] | None = None,
  train_weeks: list[int] | None = None,
) -> dict:
  from gui.app_settings import get_settings
  from gui.grid_search_engine import (
    build_grid_from_settings, grid_readiness, run_grid, save_grid_run, _score,
  )
  from config import DEFAULT_TF

  s = get_settings()
  if mining_presets or era_keys or train_weeks:
    s = dict(s)
    if mining_presets:
      s["mining_presets"] = list(mining_presets)
    if era_keys:
      s["learning_era_keys"] = list(era_keys)
    if train_weeks:
      s["strategy_train_weeks"] = [int(w) for w in train_weeks]
  ready = grid_readiness(s)
  _log(
    desk,
    f"KB readiness complete={ready.get('kb_complete')} "
    f"ready={ready.get('ready_combos')}/{ready.get('expected_combos')}",
  )
  if not ready.get("kb_complete"):
    raise RuntimeError(f"{desk}: KB chưa đủ — {ready}")

  specs, config = build_grid_from_settings(s)
  objective = str(s.get("grid_objective") or "quality")
  _log(desk, f"Grid start {len(specs)} combo · obj={objective} · workers={workers}")
  t0 = time.time()

  def on_prog(done, total, label):
    _log(desk, f"Grid {done}/{total}: {label}")

  rows = run_grid(specs, objective=objective, on_progress=on_prog, workers=workers)
  rid = save_grid_run(
    rows,
    config={
      **config,
      "timeframe": DEFAULT_TF,
      "filter_target": FILTER,
      "source": "std_recipe",
    },
    objective=objective,
  )
  ok = [x for x in rows if not x.get("error")]
  _log(desk, f"Grid done {rid}: {len(ok)}/{len(rows)} OK in {time.time() - t0:.0f}s")
  ranked = sorted(ok, key=lambda r: (_row_nums(r)[1], _row_nums(r)[0]), reverse=True)
  for r in ranked[:8]:
    _log(desk, f"top {_fmt(r)}")
  return {"run_id": rid, "rows": rows, "objective": objective}


def _create_models(desk: str, run: dict) -> list[dict]:
  from gui.trade_model import create_trade_model, get_active_trade_model

  rows = [r for r in (run.get("rows") or []) if not r.get("error")]
  hits = [r for r in rows if _passes(r)]
  hits.sort(key=lambda r: (_row_nums(r)[1], _row_nums(r)[0]), reverse=True)
  tpw_bit = f" tpw>{FILTER['tpw_gt']}" if FILTER.get("tpw_gt") is not None else ""
  _log(
    desk,
    f"Filter WR>{FILTER['wr_gt']} R>{FILTER['total_r_gt']} "
    f"n>={FILTER['n_ge']}{tpw_bit}: {len(hits)}",
  )
  current = get_active_trade_model(force_reload=True)
  cur_key = None
  if current:
    cur_key = (
      float(current.get("total_r") or 0),
      float(current.get("win_rate_pct") or 0),
    )
  created = []
  for i, row in enumerate(hits[:MAX_MODELS]):
    wr, tot, dd, n = _row_nums(row)
    label = f"WR{wr:.0f}R{tot:.0f}"
    promote = False
    if i == 0:
      if PROMOTE_ON_BAR or cur_key is None:
        promote = True
      else:
        promote = (tot, wr) > cur_key
        if not promote:
          _log(
            desk,
            f"Giữ Active hiện tại R={cur_key[0]:+.1f} WR={cur_key[1]:.1f} "
            f"(grid mới top R={tot:+.1f} WR={wr:.1f})",
          )
    model = create_trade_model(
      row,
      run_id=run.get("run_id"),
      label=label,
      set_active=promote,
      build_report=False,
    )
    created.append(model)
    _log(
      desk,
      f"TM {model.get('id')} · {model.get('label')} · {_fmt(row)} · active={promote}",
    )
  if not created:
    _log(desk, "Không TM nào đạt WR>50 trên OOS 6 tháng — không tạo model")
  return created


def _wipe_learn_artifacts(desk: str) -> None:
  """Xóa grid / TM / compare cũ. KB đã khóa (pin Trade Model) được giữ."""
  import shutil

  rt = Path(os.environ["TRAINAPP_RUNTIME"])
  removed: list[str] = []
  try:
    from kb_profiles import protect_from_trade_models, wipe_unprotected_profiles

    locked = protect_from_trade_models()
    kb_out = wipe_unprotected_profiles()
    if kb_out.get("deleted"):
      removed.append("kb:" + ",".join(kb_out["deleted"]))
    if locked or kb_out.get("kept"):
      _log(
        desk,
        "KB locked kept "
        + ", ".join(kb_out.get("kept") or locked or []),
      )
  except Exception as exc:
    _log(desk, f"KB protect wipe skipped: {exc}")
  know = rt / "learning" / "knowledge.json"
  # default knowledge.json: wipe_unprotected already unlinks unless locked
  if know.exists():
    try:
      from kb_profiles import DEFAULT_PROFILE_ID, is_profile_protected
      if not is_profile_protected(DEFAULT_PROFILE_ID):
        know.unlink()
        removed.append("knowledge.json")
    except Exception:
      pass
  for rel in (
    "results/grid_search",
    "results/trade_models",
    "results/compare_trade",
    "results/simulate_runs",
  ):
    p = rt / rel
    if p.exists():
      shutil.rmtree(p)
      removed.append(rel)
  for name in ("trade_models.json", "active_trade_model.json", "learning_report.json"):
    p = rt / "results" / name
    if p.exists():
      p.unlink()
      removed.append(name)
  (rt / "results").mkdir(parents=True, exist_ok=True)
  (rt / "results" / "trade_models.json").write_text(
    json.dumps({"models": []}, indent=2) + "\n", encoding="utf-8",
  )
  _log(desk, f"wiped {', '.join(removed) or 'nothing'}")


def _replay_created(desk: str, created: list[dict]) -> dict | None:
  ids = [str(m.get("id") or "") for m in created if m.get("id")]
  if len(ids) < 2:
    _log(desk, f"Replay skip: cần ≥2 TM (có {len(ids)}) — OOS đã nằm trong grid")
    return None
  from gui.app_settings import get_settings
  from mt5_bridge.compare_runner import run_compare

  s = get_settings()
  date_from = str(s.get("backtest_from") or "2026-01-01")[:10]
  date_to = str(s.get("backtest_to") or "2026-06-30")[:10]
  _log(desk, f"Compare replay {date_from}→{date_to} models={ids[:5]}")
  t0 = time.time()

  def on_prog(p: dict):
    done = int(p.get("bars_done") or 0)
    total = int(p.get("bars_total") or 1)
    if done in (1, total) or done % 500 == 0:
      _log(desk, f"Replay {done}/{total}")

  run = run_compare(
    model_ids=ids[:5],
    date_from=date_from,
    date_to=date_to,
    on_progress=on_prog,
  )
  per = run.get("per_model") or {}
  for mid, info in per.items():
    stats = (info or {}).get("stats") or {}
    _log(
      desk,
      f"Replay {mid} WR={stats.get('win_rate_pct')} R={stats.get('total_r')} "
      f"n={stats.get('n_trades')} DD={stats.get('max_drawdown_r')}",
    )
  _log(desk, f"Replay done {run.get('run_id')} in {time.time() - t0:.0f}s")
  return {
    "run_id": run.get("run_id"),
    "per_model": {k: (v or {}).get("stats") for k, v in per.items()},
  }


def run_desk(
  desk: str,
  *,
  reset_kb: bool,
  workers: int,
  keep_settings: bool = False,
  wipe: bool = False,
  replay: bool = False,
  mining_presets: list[str] | None = None,
  era_keys: list[str] | None = None,
  train_weeks: list[int] | None = None,
) -> dict:
  cfg = _bind(desk)
  from gui.app_settings import default_settings_for_desk, save_settings, _sanitize_settings, get_settings
  from gui.trade_model import get_active_trade_model

  if wipe:
    _wipe_learn_artifacts(desk)
  if not keep_settings:
    pinned = _sanitize_settings(default_settings_for_desk())
    save_settings(pinned)
  s = get_settings()
  grid_presets = list(mining_presets) if mining_presets else None
  _log(
    desk,
    f"start pair={cfg.get('pair')} tf={cfg.get('tf')} "
    f"weeks={train_weeks or s.get('strategy_train_weeks')} "
    f"eras={era_keys or s.get('learning_era_keys')} "
    f"loops={s.get('learning_loops')} presets={grid_presets or s.get('mining_presets')} "
    f"oos={s.get('oos_window_keys')} {s.get('backtest_from')}→{s.get('backtest_to')} "
    f"spread={s.get('spread_pips')}/{s.get('slippage_pips')}",
  )
  kb = _ensure_kb(desk, reset=reset_kb)
  run = _run_grid(
    desk, workers=workers, mining_presets=grid_presets,
    era_keys=era_keys, train_weeks=train_weeks,
  )
  created = _create_models(desk, run)
  replay_out = None
  if replay:
    try:
      replay_out = _replay_created(desk, created)
    except Exception as exc:
      _log(desk, f"Replay FAILED (TM vẫn giữ): {exc}")
      replay_out = {"error": str(exc)}
  active_id = (get_active_trade_model(force_reload=True) or {}).get("id")
  out = {
    "desk": desk,
    "kb": kb,
    "run_id": run.get("run_id"),
    "n_combos": len(run.get("rows") or []),
    "created": [
      {
        "id": m.get("id"),
        "label": m.get("label"),
        "active": m.get("id") == active_id,
      }
      for m in created
    ],
    "replay": replay_out,
  }
  _log(desk, f"RECIPE DONE {json.dumps(out, ensure_ascii=False)}")
  return out


def replay_existing_desk(desk: str) -> dict:
  _bind(desk)
  from gui.trade_model import list_trade_models

  created = list_trade_models()[:5]
  _log(desk, f"Replay-only {len(created)} TM")
  replay_out = None
  try:
    replay_out = _replay_created(desk, created)
  except Exception as exc:
    _log(desk, f"Replay FAILED (TM vẫn giữ): {exc}")
    replay_out = {"error": str(exc)}
  out = {
    "desk": desk,
    "created": [{"id": m.get("id"), "label": m.get("label")} for m in created],
    "replay": replay_out,
  }
  _log(desk, f"REPLAY DONE {json.dumps(out, ensure_ascii=False)}")
  return out


def main() -> int:
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--desks", default="e21,g23")
  ap.add_argument("--reset-kb", action="store_true", default=True)
  ap.add_argument("--no-reset-kb", action="store_true")
  ap.add_argument(
    "--keep-settings", action="store_true",
    help="Giữ app_settings hiện tại (không pin 1 era / preset desk default)",
  )
  ap.add_argument(
    "--wipe", action="store_true",
    help="Xóa KB, grid_search, trade model, compare/simulate cũ trước khi học",
  )
  ap.add_argument(
    "--replay", action="store_true",
    help="Sau khi tạo TM: Compare Trade paper replay trên cửa sổ OOS",
  )
  ap.add_argument(
    "--replay-only", action="store_true",
    help="Chỉ Compare Trade các TM hiện có (không học KB/grid)",
  )
  ap.add_argument("--workers", type=int, default=2)
  ap.add_argument(
    "--presets", default="",
    help="Override mining presets cho grid lần này (csv). Không ghi đè Settings.",
  )
  ap.add_argument("--wr-gt", type=float, default=None, help="Filter WR%% > this (default 50).")
  ap.add_argument("--n-ge", type=int, default=None, help="Filter n_trades >= this (default 15).")
  ap.add_argument(
    "--tpw-gt", type=float, default=None,
    help="Filter trades_per_week > this (hunt: 5). Off by default.",
  )
  ap.add_argument(
    "--promote-bar", action="store_true",
    help="Promote first filter hit to Active even if Total R < live.",
  )
  ap.add_argument(
    "--era-keys", default="",
    help="Override learning_era_keys cho grid lần này (csv). Không ghi đè Settings.",
  )
  ap.add_argument(
    "--weeks", default="",
    help="Override strategy_train_weeks cho grid lần này (csv). Không ghi đè Settings.",
  )
  args = ap.parse_args()
  if args.wr_gt is not None:
    FILTER["wr_gt"] = float(args.wr_gt)
  if args.n_ge is not None:
    FILTER["n_ge"] = int(args.n_ge)
  if args.tpw_gt is not None:
    FILTER["tpw_gt"] = float(args.tpw_gt)
  global PROMOTE_ON_BAR
  PROMOTE_ON_BAR = bool(args.promote_bar)
  desks = [d.strip().lower() for d in args.desks.split(",") if d.strip()]
  reset = bool(args.reset_kb) and not args.no_reset_kb
  preset_override = [p.strip() for p in args.presets.split(",") if p.strip()] or None
  era_override = [k.strip() for k in args.era_keys.split(",") if k.strip()] or None
  week_override = [int(w) for w in args.weeks.split(",") if w.strip()] or None
  summary = []
  rc = 0
  for desk in desks:
    try:
      if args.replay_only:
        summary.append(replay_existing_desk(desk))
      else:
        summary.append(run_desk(
          desk,
          reset_kb=reset,
          workers=max(1, args.workers),
          keep_settings=bool(args.keep_settings),
          wipe=bool(args.wipe),
          replay=bool(args.replay),
          mining_presets=preset_override,
          era_keys=era_override,
          train_weeks=week_override,
        ))
    except Exception as exc:
      rc = 1
      try:
        _bind(desk)
        _log(desk, f"FAILED: {exc}")
      except Exception:
        print(f"FAILED {desk}: {exc}", flush=True)
      summary.append({"desk": desk, "error": str(exc)})
  print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
  return rc


if __name__ == "__main__":
  raise SystemExit(main())
