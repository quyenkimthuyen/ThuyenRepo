#!/usr/bin/env python3
"""Pin 10 unique E21 Trade Models from latest grid, named WR<wr>R<r>."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from desk_context import apply_desk_env  # noqa: E402

N_MODELS = 10
FAMILY_CAP = 8


def bind():
  cfg = apply_desk_env("e21")
  for name in list(sys.modules):
    if name in (
      "run_backtest", "knowledge_base", "config", "app_paths",
      "data_loader", "kb_profiles", "optimizer",
    ) or name.startswith("gui.") or name.startswith("mt5_bridge"):
      sys.modules.pop(name, None)
  for p in (str(ROOT), str(cfg["core_root"])):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)
  return cfg


def _q(row: dict) -> float:
  from gui.grid_search_engine import _score
  return _score(row, "quality")


def _family(row: dict) -> tuple:
  return (
    str(row.get("mining_preset") or ""),
    str(row.get("kb_profile") or ""),
    int(row.get("train_weeks") or 0),
  )


def _wr_r_label(row: dict, used: set[str]) -> str:
  wr = int(float(row.get("win_rate_pct") or 0))
  tot = int(float(row.get("total_r") or 0))
  lab = f"WR{wr}R{tot}"
  if lab.lower() in used:
    dd = int(float(row.get("max_drawdown_r") or 0))
    lab = f"WR{wr}R{tot}DD{dd}"
  n = 2
  base = lab
  while lab.lower() in used:
    lab = f"{base}_{n}"
    n += 1
  used.add(lab.lower())
  return lab


def _pick(rows: list[dict]) -> list[dict]:
  ok = [r for r in rows if not r.get("error")]
  quality = [r for r in ok if _q(r) > -1e11]
  quality.sort(key=lambda r: (_q(r), float(r.get("total_r") or 0), float(r.get("win_rate_pct") or 0)), reverse=True)
  picked: list[dict] = []
  seen_fam: set[tuple] = set()
  seen_key: set[str] = set()
  for row in quality:
    fam = _family(row)
    key = str(row.get("key") or "")
    if fam in seen_fam or key in seen_key:
      continue
    seen_fam.add(fam)
    seen_key.add(key)
    picked.append(row)
    if len(picked) >= FAMILY_CAP:
      break
  for row in quality:
    key = str(row.get("key") or "")
    if key in seen_key:
      continue
    seen_key.add(key)
    picked.append(row)
    if len(picked) >= N_MODELS:
      break
  return picked[:N_MODELS]


def _sync_row(model: dict, row: dict, run_id: str | None, label: str) -> dict:
  model["label"] = label
  model["label_custom"] = True
  model["grid_run_id"] = run_id
  model["grid_key"] = row.get("key")
  model["train_weeks"] = row.get("train_weeks")
  model["use_kb"] = bool(row.get("use_kb", True))
  model["kb_profile"] = row.get("kb_profile")
  model["kb_snapshot"] = row.get("kb_snapshot")
  model["oos_from"] = row.get("oos_from")
  model["oos_to"] = row.get("oos_to")
  model["total_r"] = row.get("total_r")
  model["win_rate_pct"] = row.get("win_rate_pct")
  model["max_drawdown_r"] = row.get("max_drawdown_r")
  model["profit_factor"] = row.get("profit_factor")
  model["n_trades"] = row.get("n_trades")
  model["mining_search_space"] = row.get("mining_search_space")
  model["mining_preset"] = row.get("mining_preset")
  return model


def main() -> int:
  cfg = bind()
  from gui.grid_search_engine import load_latest_grid_run
  from gui.trade_model import (
    create_trade_model,
    load_models_store,
    save_models_store,
    set_active_trade_model,
  )
  try:
    from trade_model_kb_pin import ensure_model_kb_pin
  except Exception:
    ensure_model_kb_pin = None  # type: ignore

  run = load_latest_grid_run() or {}
  run_id = run.get("run_id")
  picked = _pick(run.get("rows") or [])
  print(f"desk={cfg.get('id')} grid={run_id} picked={len(picked)}", flush=True)
  if len(picked) < N_MODELS:
    print(f"WARN only {len(picked)} unique quality combos", flush=True)

  used_labels: set[str] = set()
  created: list[dict] = []
  winner_id = None
  for i, row in enumerate(picked):
    label = _wr_r_label(row, used_labels)
    model = create_trade_model(
      row,
      run_id=run_id,
      label=label,
      set_active=(i == 0),
      build_report=False,
    )
    store = load_models_store()
    for m in store["models"]:
      if m.get("id") != model.get("id"):
        continue
      _sync_row(m, row, run_id, label)
      if ensure_model_kb_pin:
        try:
          ensure_model_kb_pin(m)
        except Exception as exc:
          print(f"kb_pin skip {m.get('id')}: {exc}", flush=True)
      model = m
      break
    save_models_store(store)
    if i == 0:
      winner_id = model.get("id")
    wr = float(row.get("win_rate_pct") or 0)
    tot = float(row.get("total_r") or 0)
    print(
      f"{i+1:2} {label:12} {model.get('id')} WR={wr:.1f} R={tot:.1f} "
      f"n={row.get('n_trades')} PF={row.get('profit_factor')} "
      f"ep{row.get('kb_snapshot')} {_family(row)}",
      flush=True,
    )
    created.append(model)

  if winner_id:
    set_active_trade_model(winner_id)
    print(f"active={winner_id}", flush=True)
  print("DONE", flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
