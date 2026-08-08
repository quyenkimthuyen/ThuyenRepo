"""GBPUSD: maximize Total R with hard floor WR > 60%.

2-phase WR-oriented sweep + merge prior WR60 hits. Always set PYTHONPATH to app root.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import DEFAULT_START_DATE
from data_loader import load_gbpusd_m15
from gui.grid_search_engine import GridSpec, run_grid, save_grid_run, _score
from gui.model_health import assess_monthly_degradation, monthly_oos_from_report
from gui.trade_model import (
  create_trade_model,
  list_trade_models,
  load_models_store,
  save_model_report,
  save_models_store,
  set_active_trade_model,
)
from mining_presets import get_preset
from optimizer import reset_kb_cache, set_kb_profile
from run_backtest import run_walk_forward, save_backtest_report
from strategy_miner import mining_search_space_from_dict

WR_FLOOR = 60.0
OOS_FROM = "2026-04-01"
OOS_TO = "2026-12-31"
SPREAD = 1.5
SLIP = 0.3
KB6 = "era_2025_2026_6thang"
KB_H2 = "era_2025_h2"

WR_PRESETS = [
  "anti_chase_fixed_62",
  "anti_chase_fixed_65",
  "anti_chase_fixed_68",
  "anti_chase_fixed_70",
  "anti_chase_and_65_2",
  "anti_chase_and_68_2",
  "anti_chase_and_70_15",
  "anti_chase_strict",
  "nova_fixed",
  "elite_60_3",
  "elite_60_35",
  "elite_60_3_vwap",
  "elite_or_quality",
  "wr_rr_lock",
  "wr_rr_sniper",
  "wr_rr_frontier",
]


def _metrics(row: dict) -> tuple[float, float, int, float]:
  return (
    float(row.get("total_r") or 0.0),
    float(row.get("win_rate_pct") or 0.0),
    int(row.get("n_trades") or 0),
    float(row.get("max_drawdown_r") or 0.0),
  )


def _ok_wr(row: dict) -> bool:
  return (
    float(row.get("win_rate_pct") or 0.0) > WR_FLOOR
    and int(row.get("n_trades") or 0) >= 30
    and not row.get("error")
  )


def _champ_key(row: dict) -> tuple:
  tot, wr, n, dd = _metrics(row)
  return (tot, wr, -dd, n)


def _spec(kb: str, tw: int, ep: int, preset: str) -> GridSpec:
  return GridSpec(
    train_weeks=tw,
    use_kb=True,
    kb_profile=kb,
    kb_snapshot=ep,
    oos_from=OOS_FROM,
    oos_to=OOS_TO,
    spread_pips=SPREAD,
    slippage_pips=SLIP,
    mining_preset=preset,
  )


def _known_keys() -> set[tuple]:
  known: set[tuple] = set()
  for gs in (ROOT / "results" / "grid_search").glob("gs_*.json"):
    try:
      d = json.loads(gs.read_text(encoding="utf-8"))
    except Exception:
      continue
    for r in d.get("rows") or []:
      if r.get("error"):
        continue
      kb = r.get("kb_profile")
      tw = r.get("train_weeks")
      ep = r.get("kb_snapshot")
      p = r.get("mining_preset")
      if kb and tw and ep and p:
        known.add((str(kb), int(tw), int(ep), str(p)))
  return known


def _load_prior_wr60() -> list[dict]:
  out: list[dict] = []
  for gs in (ROOT / "results" / "grid_search").glob("gs_*.json"):
    try:
      d = json.loads(gs.read_text(encoding="utf-8"))
    except Exception:
      continue
    for r in d.get("rows") or []:
      if _ok_wr(r):
        out.append(r)
  return out


def _run(specs: list[GridSpec], tag: str) -> list[dict]:
  print(f"{tag}: {len(specs)} combos", flush=True)

  def on_progress(i: int, total: int, label: str) -> None:
    print(f"[{tag} {i}/{total}] {label}", flush=True)

  return run_grid(specs, objective="total_r", on_progress=on_progress) if specs else []


def _report(row: dict, model_id: str) -> dict:
  df = load_gbpusd_m15(DEFAULT_START_DATE)
  reset_kb_cache()
  set_kb_profile(row.get("kb_profile"), row.get("kb_snapshot"))
  space = row.get("mining_search_space") or get_preset(row.get("mining_preset"))
  search_space = mining_search_space_from_dict(space) if space else None
  report = run_walk_forward(
    df,
    use_learning=True,
    train_weeks=int(row["train_weeks"]),
    spread_pips=float(row.get("spread_pips") or SPREAD),
    slippage_pips=float(row.get("slippage_pips") or SLIP),
    kb_profile=row.get("kb_profile"),
    kb_snapshot=row.get("kb_snapshot"),
    oos_from=str(row["oos_from"]),
    oos_to=str(row["oos_to"]),
    search_space=search_space,
    verbose=False,
  )
  report.setdefault("config", {})["trade_model_id"] = model_id
  save_model_report(model_id, report)
  save_backtest_report(report)
  return report


def main() -> None:
  known = _known_keys()
  print(f"known_combos={len(known)}", flush=True)
  seen: set[tuple] = set()
  phase_a: list[GridSpec] = []

  def add(bucket: list[GridSpec], kb: str, tw: int, ep: int, preset: str) -> None:
    key = (kb, tw, ep, preset)
    if key in seen or key in known:
      return
    seen.add(key)
    bucket.append(_spec(kb, tw, ep, preset))

  # A: WR presets on tw=6,9 × ep 3-6 (skip already measured)
  for preset in WR_PRESETS:
    for tw in (6, 9):
      for ep in (3, 4, 5, 6):
        add(phase_a, KB6, tw, ep, preset)

  rows_a = _run(phase_a, "A")
  # seed expand from this run + prior near/pass WR
  seed_rows = rows_a + _load_prior_wr60()
  seed_rows = sorted(
    [r for r in seed_rows if not r.get("error")],
    key=lambda r: (
      1 if _ok_wr(r) else 0,
      float(r.get("total_r") or -999),
      float(r.get("win_rate_pct") or 0),
    ),
    reverse=True,
  )
  top_presets: list[str] = []
  for r in seed_rows:
    p = r.get("mining_preset")
    wr = float(r.get("win_rate_pct") or 0)
    if not p or wr < 55:
      continue
    if p not in top_presets:
      top_presets.append(p)
    if len(top_presets) >= 8:
      break
  for p in ("anti_chase_fixed_62", "anti_chase_fixed_65", "anti_chase_fixed_68", "nova_fixed"):
    if p not in top_presets:
      top_presets.append(p)
  print("EXPAND_PRESETS", top_presets, flush=True)

  phase_b: list[GridSpec] = []
  for preset in top_presets:
    for tw in (3, 12):
      for ep in (3, 4, 5, 6):
        add(phase_b, KB6, tw, ep, preset)
  for preset in top_presets[:6]:
    for tw in (6, 9, 12):
      for ep in (3, 4):
        add(phase_b, KB_H2, tw, ep, preset)

  rows_b = _run(phase_b, "B")
  all_rows = rows_a + rows_b
  rid = save_grid_run(
    sorted(all_rows, key=lambda r: _score(r, "total_r"), reverse=True),
    config={
      "source": "gbpusd_wr60_rmax",
      "pair": "GBPUSD",
      "wr_floor_gt": WR_FLOOR,
      "presets": WR_PRESETS,
      "expand_presets": top_presets,
      "spread_pips": SPREAD,
      "slippage_pips": SLIP,
    },
    objective="total_r",
  )
  print(f"saved {rid} n={len(all_rows)}", flush=True)

  pool = [r for r in all_rows if _ok_wr(r)] + _load_prior_wr60()
  by_key: dict[str, dict] = {}
  for r in pool:
    k = str(r.get("key") or "")
    if not k:
      continue
    prev = by_key.get(k)
    if prev is None or _champ_key(r) > _champ_key(prev):
      by_key[k] = r
  cands = sorted(by_key.values(), key=_champ_key, reverse=True)
  print(f"WR60_PASS n={len(cands)}", flush=True)
  for r in cands[:15]:
    tot, wr, n, dd = _metrics(r)
    print(
      f"  R={tot:+.1f} WR={wr:.1f}% n={n} dd={dd:.2f} "
      f"kb={r.get('kb_profile')} tw={r.get('train_weeks')} ep={r.get('kb_snapshot')} "
      f"preset={r.get('mining_preset')}",
      flush=True,
    )

  if not cands:
    print("NO_CANDIDATE", flush=True)
    raise SystemExit(2)

  best = cands[0]
  tot, wr, _, dd = _metrics(best)
  print(
    f"CHAMPION R={tot:+.1f} WR={wr:.1f}% dd={dd:.2f} "
    f"kb={best.get('kb_profile')} tw={best.get('train_weeks')} "
    f"ep={best.get('kb_snapshot')} preset={best.get('mining_preset')}",
    flush=True,
  )

  model = create_trade_model(
    best,
    run_id=rid,
    label=f"GBPUSD BestR@WR60 {tot:+.1f}R WR{wr:.0f}",
    set_active=True,
    build_report=False,
  )
  report = _report(best, model["id"])
  oos = report.get("overall_oos") or {}
  print(
    "VALIDATED",
    f"R={oos.get('total_r')} WR={oos.get('win_rate_pct')} n={oos.get('n_trades')} "
    f"dd={oos.get('max_drawdown_r')} ror={oos.get('risk_of_ruin_pct')}",
    flush=True,
  )
  vwr = float(oos.get("win_rate_pct") or 0)
  if vwr <= WR_FLOOR:
    print(f"WARN validated WR {vwr} not > {WR_FLOOR}", flush=True)
  deg = assess_monthly_degradation(monthly_oos_from_report(report))
  print("HEALTH", deg.get("verdict"), deg.get("message"), flush=True)

  store = load_models_store()
  for m in store.get("models") or []:
    if m.get("id") != model["id"]:
      continue
    m["total_r"] = oos.get("total_r", tot)
    m["win_rate_pct"] = oos.get("win_rate_pct", wr)
    m["n_trades"] = oos.get("n_trades")
    m["max_drawdown_r"] = oos.get("max_drawdown_r")
    m["profit_factor"] = oos.get("profit_factor")
    m["spread_pips"] = SPREAD
    m["slippage_pips"] = SLIP
    vr = float(m["total_r"] or 0)
    vwr2 = float(m["win_rate_pct"] or 0)
    m["label"] = f"GBPUSD BestR@WR60 {vr:+.1f}R WR{vwr2:.0f}"
    m["label_custom"] = True
  save_models_store(store)
  set_active_trade_model(model["id"])

  if len(cands) > 1 and cands[1].get("key") != best.get("key"):
    t2, w2, _, _ = _metrics(cands[1])
    create_trade_model(
      cands[1],
      run_id=rid,
      label=f"GBPUSD WR60+ alt {t2:+.1f}R WR{w2:.0f}",
      set_active=False,
      build_report=False,
    )

  print("ACTIVE", model["id"], flush=True)
  for m in list_trade_models():
    mark = " *" if float(m.get("win_rate_pct") or 0) > WR_FLOOR else ""
    print(
      f" - {m.get('label')} R={m.get('total_r')} WR={m.get('win_rate_pct')} "
      f"dd={m.get('max_drawdown_r')} tw={m.get('train_weeks')} ep={m.get('kb_snapshot')}{mark}",
      flush=True,
    )
  print("DONE", flush=True)


if __name__ == "__main__":
  main()
