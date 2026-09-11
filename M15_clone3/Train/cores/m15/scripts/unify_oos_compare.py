#!/usr/bin/env python3
"""Unify all Trade Model comparisons on canonical OOS: 2026-01-01 → 2026-08-07 (M15 desks).

- Patches app_settings / active_workspace / ui compare dates
- Re-runs walk-forward for every live Trade Model on that window
- Updates registry KPIs + per-model OOS reports
- Writes ranked comparison under results/research/m15_oos_unified/

Usage:
  EdgeMinerM15B5/.venv/bin/python scripts/unify_oos_compare.py
  ... --reuse
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

OOS_FROM = "2026-01-01"
OOS_TO = "2026-08-07"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "results" / "research" / "m15_oos_unified"


def log(msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
  print(line, flush=True)
  OUT.mkdir(parents=True, exist_ok=True)
  with open(OUT / "unify.log", "a", encoding="utf-8") as f:
    f.write(line + "\n")


def _read(path: Path):
  if not path.exists():
    return None
  return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(".tmp")
  tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
  tmp.replace(path)


def _pick_active(models: list[dict]) -> dict | None:
  by_label = {(m.get("label") or "").strip(): m for m in models}
  for lab in ("BestQuality", "BestBalance", "BestPF", "BestTotalR", "BestWinRate", "bestWinrate", "Balance"):
    if lab in by_label:
      return by_label[lab]
  for m in models:
    lab = (m.get("label") or "")
    if "RiskAdj" in lab or lab.startswith("GBPUSD BestR") or lab.startswith("Best"):
      return m
  return models[0] if models else None


def patch_settings() -> None:
  from gui.ui_preferences import set_preference
  from gui.trade_model import list_trade_models, set_active_trade_model

  settings_path = ROOT / "results" / "app_settings.json"
  settings = _read(settings_path) or {}
  settings["backtest_from"] = OOS_FROM
  settings["backtest_to"] = OOS_TO
  settings["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
  _write(settings_path, settings)
  log(f"app_settings backtest={OOS_FROM}→{OOS_TO}")

  models = list_trade_models()
  preferred = _pick_active(models)

  ws_path = ROOT / "results" / "active_workspace.json"
  ws = _read(ws_path) or {}
  ws["oos_from"] = OOS_FROM
  ws["oos_to"] = OOS_TO
  if preferred:
    ws["label"] = preferred.get("label")
    ws["trade_model_id"] = preferred.get("id")
    for k in ("kb_profile", "kb_snapshot", "train_weeks", "spread_pips", "slippage_pips",
              "feature_profile", "mining_search_space"):
      if preferred.get(k) is not None:
        ws[k] = preferred.get(k)
    try:
      set_active_trade_model(preferred.get("id"))
    except Exception as exc:
      log(f"set_active skip: {exc}")
    log(f"active → {preferred.get('label')} ({preferred.get('id')})")
  _write(ws_path, ws)

  try:
    set_preference("compare.from", OOS_FROM)
    set_preference("compare.to", OOS_TO)
    labels = [m.get("label") for m in models if m.get("label")]
    best = [x for x in labels if str(x).startswith("Best") or str(x).startswith("best") or "RiskAdj" in str(x)]
    set_preference("compare.model_labels", best[:6] or labels[:6])
    log(f"ui compare={OOS_FROM}→{OOS_TO} labels={best[:6] or labels[:6]}")
  except Exception as exc:
    log(f"ui_preferences skip: {exc}")


def report_window_ok(report: dict | None) -> bool:
  if not report:
    return False
  cfg = report.get("config") or {}
  of = str(cfg.get("oos_from") or report.get("oos_from") or "")[:10]
  ot = str(cfg.get("oos_to") or report.get("oos_to") or "")[:10]
  return of == OOS_FROM and ot == OOS_TO


def load_cached_report(model_id: str) -> dict | None:
  candidates = [
    OUT / f"{model_id}_oos_report.json",
    ROOT / "results" / "trade_models" / f"{model_id}.json",
  ]
  for p in candidates:
    rep = _read(p)
    if report_window_ok(rep):
      return rep
  return None


def run_oos(model: dict) -> dict:
  from data_loader import load_eurusd_m15
  from mining_presets import get_preset
  from optimizer import reset_kb_cache
  from run_backtest import run_walk_forward
  from strategy_miner import mining_search_space_from_dict

  space_dict = model.get("mining_search_space") or get_preset("elite_or_quality")
  space = mining_search_space_from_dict(space_dict)
  reset_kb_cache()
  df = load_eurusd_m15("2025-01-01")
  return run_walk_forward(
    df,
    use_learning=bool(model.get("use_kb", True)),
    train_weeks=int(model.get("train_weeks") or 3),
    spread_pips=float(model.get("spread_pips") or 1.0),
    slippage_pips=float(model["slippage_pips"]) if model.get("slippage_pips") is not None else 0.0,
    holdout_months=0,
    kb_profile=model.get("kb_profile"),
    kb_snapshot=model.get("kb_snapshot"),
    oos_from=OOS_FROM,
    oos_to=OOS_TO,
    feature_profile=model.get("feature_profile") or "current",
    search_space=space,
    verbose=False,
  )


def apply_metrics(model: dict, report: dict) -> dict:
  oos = report.get("overall_oos") or {}
  model = dict(model)
  model["oos_from"] = OOS_FROM
  model["oos_to"] = OOS_TO
  model["total_r"] = oos.get("total_r")
  model["win_rate_pct"] = oos.get("win_rate_pct")
  model["max_drawdown_r"] = oos.get("max_drawdown_r")
  model["profit_factor"] = oos.get("profit_factor")
  model["n_trades"] = oos.get("n_trades")
  model["trades_per_week"] = oos.get("trades_per_week")
  model["oos_unified_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
  model["oos_window_canonical"] = True
  return model


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--reuse", action="store_true")
  ap.add_argument(
    "--delete-noncanonical",
    action="store_true",
    help="Xóa model có OOS window khác canonical trước khi rescore",
  )
  args = ap.parse_args()

  OUT.mkdir(parents=True, exist_ok=True)
  log(f"Desk={ROOT.name} unify OOS {OOS_FROM}→{OOS_TO}")

  from gui.trade_model import (
    delete_trade_model,
    list_trade_models,
    load_models_store,
    save_model_report,
    save_models_store,
  )

  models = list_trade_models()
  if args.delete_noncanonical:
    for m in list(models):
      of = str(m.get("oos_from") or "")[:10]
      ot = str(m.get("oos_to") or "")[:10]
      if of != OOS_FROM or ot != OOS_TO:
        log(f"Delete non-canonical before rescore: {m.get('label')} ({of}→{ot})")
        delete_trade_model(m.get("id"))
    models = list_trade_models()

  store = load_models_store()
  by_id = {m.get("id"): m for m in (store.get("models") or [])}
  rows = []

  for m in models:
    mid = m.get("id")
    lab = m.get("label")
    report = None
    if args.reuse:
      report = load_cached_report(mid)
      if report:
        log(f"Reuse OOS {lab} ({mid})")
    if report is None:
      log(f"Re-run OOS {lab} ({mid}) …")
      report = run_oos(m)
    _write(OUT / f"{mid}_oos_report.json", report)
    try:
      save_model_report(mid, report)
    except Exception as exc:
      log(f"  save_model_report skip: {exc}")

    updated = apply_metrics(m, report)
    if mid in by_id:
      by_id[mid].update({k: updated[k] for k in updated if k != "id"})
    oos = report.get("overall_oos") or {}
    st = {
      "label": lab,
      "id": mid,
      "oos_from": OOS_FROM,
      "oos_to": OOS_TO,
      "total_r": oos.get("total_r"),
      "profit_factor": oos.get("profit_factor"),
      "win_rate_pct": oos.get("win_rate_pct"),
      "max_drawdown_r": oos.get("max_drawdown_r"),
      "n_trades": oos.get("n_trades"),
      "trades_per_week": oos.get("trades_per_week"),
    }
    rows.append(st)
    log(
      f"  {lab}: R={st['total_r']} PF={st['profit_factor']} WR={st['win_rate_pct']} "
      f"DD={st['max_drawdown_r']} n={st['n_trades']}"
    )

  store["models"] = list(by_id.values())
  save_models_store(store)
  patch_settings()

  rows.sort(key=lambda r: float(r.get("total_r") or -1e9), reverse=True)
  payload = {
    "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "desk": ROOT.name,
    "oos_from": OOS_FROM,
    "oos_to": OOS_TO,
    "models": rows,
  }
  _write(OUT / "latest.json", payload)
  _write(OUT / f"compare_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", payload)

  lines = [
    f"# Trade Model compare — {ROOT.name}",
    "",
    f"OOS **only**: `{OOS_FROM}` → `{OOS_TO}`",
    "",
    "| Rank | Label | Total R | PF | WR% | MaxDD R | Trades | TPW |",
    "|------|-------|---------|-----|-----|---------|--------|-----|",
  ]
  for i, r in enumerate(rows, 1):
    lines.append(
      f"| {i} | {r['label']} | {r['total_r']} | {r['profit_factor']} | {r['win_rate_pct']} | "
      f"{r['max_drawdown_r']} | {r['n_trades']} | {r['trades_per_week']} |"
    )
  (OUT / "compare.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
  log(f"Wrote {OUT / 'latest.json'} and compare.md ({len(rows)} models)")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
