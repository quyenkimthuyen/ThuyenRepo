#!/usr/bin/env python3
"""Round 3 — ensemble BestQuality+BestBalance + monthly walk-forward stability.

EUR default pair: BestQuality + BestBalance
GBP default pair: BestQuality + BestPF (no BestBalance on that desk)

Modes:
  capital_split  50/50 equity (half R each month, summed)
  union_dedupe   all trades; drop duplicate entry-hour+side keeping first
  agree_month    only count months where BOTH books are positive

Also writes Bridge roster preference for the pair (does not start Bridge).

Usage:
  EdgeMinerM15B5/.venv/bin/python scripts/round3_ensemble_monthly.py
  EdgeMinerM15B5/.venv/bin/python scripts/round3_ensemble_monthly.py --labels BestQuality BestBalance
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "results" / "research" / "m5_round3_ensemble"


def log(msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
  print(line, flush=True)
  OUT.mkdir(parents=True, exist_ok=True)
  with open(OUT / "round3.log", "a", encoding="utf-8") as f:
    f.write(line + "\n")


def _desk_side() -> str:
  return "GBP" if "GBP" in ROOT.name.upper() else "EUR"


def default_labels(side: str) -> list[str]:
  if side == "GBP":
    return ["BestQuality", "BestPF"]
  return ["BestQuality", "BestBalance"]


def find_models(labels: list[str]) -> list[dict]:
  from gui.trade_model import list_trade_models
  models = list_trade_models()
  by_label = {(m.get("label") or "").strip(): m for m in models}
  out = []
  for lab in labels:
    m = by_label.get(lab)
    if not m:
      # fuzzy: startswith
      hits = [x for x in models if (x.get("label") or "").startswith(lab)]
      if not hits:
        raise RuntimeError(f"Model label not found: {lab}")
      m = hits[0]
    out.append(m)
  return out


def run_model_oos(model: dict) -> dict:
  from data_loader import load_eurusd_m15
  from mining_presets import get_preset
  from optimizer import reset_kb_cache
  from run_backtest import run_walk_forward, save_backtest_report
  from strategy_miner import mining_search_space_from_dict

  space_dict = model.get("mining_search_space")
  if not space_dict:
    # fall back to elite_or_quality
    space_dict = get_preset("elite_or_quality")
  space = mining_search_space_from_dict(space_dict)
  reset_kb_cache()
  df = load_eurusd_m15("2025-01-01")
  report = run_walk_forward(
    df,
    use_learning=bool(model.get("use_kb", True)),
    train_weeks=int(model.get("train_weeks") or 3),
    spread_pips=float(model.get("spread_pips") or 1.0),
    slippage_pips=float(model.get("slippage_pips") or 0.3),
    holdout_months=0,
    kb_profile=model.get("kb_profile"),
    kb_snapshot=model.get("kb_snapshot"),
    oos_from=model.get("oos_from") or "2026-01-01",
    oos_to=model.get("oos_to") or "2026-08-07",
    feature_profile=model.get("feature_profile") or "m5_parity",
    search_space=space,
    verbose=False,
  )
  # persist report beside model for later UI
  mid = model.get("id")
  if mid:
    path = OUT / f"{mid}_oos_report.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    try:
      save_backtest_report(report)  # also updates results/backtest_report.json
    except Exception:
      pass
  return report


def trades_from_report(report: dict) -> pd.DataFrame:
  from analytics import trades_json_to_df
  raw = report.get("trades") or []
  if isinstance(raw, list) and raw and isinstance(raw[0], dict):
    return trades_json_to_df(raw)
  # weekly_log-only fallback — monthly_from_weekly_log still works
  return pd.DataFrame(columns=["entry", "dir", "r"])


def monthly_stats(report: dict, trades: pd.DataFrame) -> pd.DataFrame:
  from analytics import monthly_breakdown, monthly_from_weekly_log
  mo = monthly_breakdown(trades)
  if mo is None or mo.empty:
    mo = monthly_from_weekly_log(report.get("weekly_log") or [])
  return mo if mo is not None else pd.DataFrame()


def stability(mo: pd.DataFrame) -> dict:
  if mo is None or mo.empty or "total_r" not in mo.columns:
    return {
      "n_months": 0, "positive_months": 0, "positive_pct": 0.0,
      "mean_r": 0.0, "std_r": 0.0, "worst_month_r": 0.0,
      "best_month_r": 0.0, "monthly_sharpe": 0.0, "total_r": 0.0,
    }
  s = mo["total_r"].astype(float)
  pos = int((s > 0).sum())
  std = float(s.std(ddof=0) or 0.0)
  mean = float(s.mean())
  return {
    "n_months": int(len(s)),
    "positive_months": pos,
    "positive_pct": round(100.0 * pos / max(len(s), 1), 1),
    "mean_r": round(mean, 3),
    "std_r": round(std, 3),
    "worst_month_r": round(float(s.min()), 3),
    "best_month_r": round(float(s.max()), 3),
    "monthly_sharpe": round(mean / std, 3) if std > 1e-9 else None,
    "total_r": round(float(s.sum()), 3),
  }


def ensemble_capital_split(mo_a: pd.DataFrame, mo_b: pd.DataFrame, w: float = 0.5) -> pd.DataFrame:
  a = mo_a.set_index("month")["total_r"].astype(float) if not mo_a.empty else pd.Series(dtype=float)
  b = mo_b.set_index("month")["total_r"].astype(float) if not mo_b.empty else pd.Series(dtype=float)
  idx = sorted(set(a.index) | set(b.index))
  rows = []
  cum = 0.0
  for m in idx:
    ra = float(a.get(m, 0.0)) * w
    rb = float(b.get(m, 0.0)) * (1.0 - w)
    tot = ra + rb
    cum += tot
    rows.append({"month": m, "total_r": round(tot, 3), "from_a": round(ra, 3), "from_b": round(rb, 3), "cum_r": round(cum, 3)})
  return pd.DataFrame(rows)


def ensemble_union_dedupe(tr_a: pd.DataFrame, tr_b: pd.DataFrame) -> pd.DataFrame:
  frames = []
  for src, tr in (("A", tr_a), ("B", tr_b)):
    if tr is None or tr.empty:
      continue
    t = tr.copy()
    t["entry"] = pd.to_datetime(t["entry"], errors="coerce")
    t = t.dropna(subset=["entry", "r"])
    side = t["dir"] if "dir" in t.columns else (t["side"] if "side" in t.columns else "?")
    t["side"] = side.astype(str) if hasattr(side, "astype") else str(side)
    t["src"] = src
    t["bucket"] = t["entry"].dt.floor("h").astype(str) + "|" + t["side"]
    frames.append(t)
  if not frames:
    return pd.DataFrame(columns=["entry", "side", "r"])
  all_t = pd.concat(frames, ignore_index=True).sort_values("entry")
  # keep first trade per hour+side bucket
  dedup = all_t.drop_duplicates(subset=["bucket"], keep="first")
  return dedup[["entry", "side", "r"]].reset_index(drop=True)


def ensemble_agree_month(mo_a: pd.DataFrame, mo_b: pd.DataFrame) -> pd.DataFrame:
  a = mo_a.set_index("month")["total_r"].astype(float) if not mo_a.empty else pd.Series(dtype=float)
  b = mo_b.set_index("month")["total_r"].astype(float) if not mo_b.empty else pd.Series(dtype=float)
  idx = sorted(set(a.index) & set(b.index))
  rows = []
  cum = 0.0
  for m in idx:
    ra, rb = float(a.get(m, 0.0)), float(b.get(m, 0.0))
    if ra > 0 and rb > 0:
      tot = 0.5 * ra + 0.5 * rb
    else:
      tot = 0.0  # sit out disagree / losing months
    cum += tot
    rows.append({
      "month": m, "total_r": round(tot, 3),
      "a_r": round(ra, 3), "b_r": round(rb, 3),
      "agree": bool(ra > 0 and rb > 0), "cum_r": round(cum, 3),
    })
  return pd.DataFrame(rows)


def set_bridge_roster(model_ids: list[str], labels: dict[str, str]) -> None:
  try:
    from gui.ui_preferences import set_preference
    labs = [labels.get(i, i) for i in model_ids]
    set_preference("mt5.bridge_model_labels", labs)
  except Exception as exc:
    log(f"ui_preferences skip: {exc}")
  try:
    from mt5_bridge.protocol import BRIDGE_DIR, BRIDGE_SIM_DIR, write_models_roster
    for bdir in (BRIDGE_DIR, BRIDGE_SIM_DIR):
      write_models_roster(model_ids, bridge_dir=bdir, labels=labels, risk_pct=0.5)
    log(f"Bridge roster set: {labels}")
  except Exception as exc:
    log(f"bridge roster skip: {exc}")


def pack_model(label: str, model: dict, report: dict, mo: pd.DataFrame) -> dict:
  oos = report.get("overall_oos") or {}
  return {
    "label": label,
    "id": model.get("id"),
    "overall": {
      "total_r": oos.get("total_r"),
      "n_trades": oos.get("n_trades"),
      "profit_factor": oos.get("profit_factor"),
      "win_rate_pct": oos.get("win_rate_pct"),
      "max_drawdown_r": oos.get("max_drawdown_r"),
      "trades_per_week": oos.get("trades_per_week"),
    },
    "monthly": mo.to_dict(orient="records") if mo is not None and not mo.empty else [],
    "stability": stability(mo),
  }


def main() -> int:
  side = _desk_side()
  ap = argparse.ArgumentParser()
  ap.add_argument("--labels", nargs=2, default=None)
  ap.add_argument("--skip-roster", action="store_true")
  ap.add_argument("--reuse", action="store_true", help="Reuse cached OOS reports under OUT if present")
  args = ap.parse_args()
  labels = args.labels or default_labels(side)

  OUT.mkdir(parents=True, exist_ok=True)
  log(f"Desk={ROOT.name} side={side} labels={labels}")

  models = find_models(labels)
  packs = []
  mos = []
  trades = []
  for lab, model in zip(labels, models):
    mid = model.get("id") or ""
    cached = OUT / f"{mid}_oos_report.json"
    report = None
    if args.reuse and cached.is_file():
      log(f"Reuse OOS for {lab} ({mid}) …")
      report = json.loads(cached.read_text(encoding="utf-8"))
    else:
      log(f"Re-run OOS for {lab} ({mid}) …")
      report = run_model_oos(model)
    tr = trades_from_report(report)
    mo = monthly_stats(report, tr)
    packs.append(pack_model(lab, model, report, mo))
    mos.append(mo)
    trades.append(tr)
    st = packs[-1]["stability"]
    log(
      f"  {lab}: R={packs[-1]['overall'].get('total_r')} "
      f"PF={packs[-1]['overall'].get('profit_factor')} "
      f"months+={st['positive_pct']}% worst={st['worst_month_r']} sharpe={st['monthly_sharpe']}"
    )

  # Ensembles
  split = ensemble_capital_split(mos[0], mos[1], 0.5)
  union_tr = ensemble_union_dedupe(trades[0], trades[1])
  from analytics import monthly_breakdown
  union_mo = monthly_breakdown(union_tr) if not union_tr.empty else pd.DataFrame()
  agree = ensemble_agree_month(mos[0], mos[1])

  ensembles = {
    "capital_split_50_50": {
      "monthly": split.to_dict(orient="records"),
      "stability": stability(split),
    },
    "union_dedupe": {
      "monthly": union_mo.to_dict(orient="records") if not union_mo.empty else [],
      "stability": stability(union_mo),
      "n_trades": int(len(union_tr)),
    },
    "agree_month": {
      "monthly": agree.to_dict(orient="records"),
      "stability": stability(agree),
      "agree_months": int(agree["agree"].sum()) if not agree.empty and "agree" in agree.columns else 0,
    },
  }
  for name, block in ensembles.items():
    st = block["stability"]
    log(
      f"Ensemble {name}: total_r={st['total_r']} +months={st['positive_pct']}% "
      f"worst={st['worst_month_r']} sharpe={st['monthly_sharpe']}"
    )

  # Pick recommended ensemble: highest monthly_sharpe among those with total_r>0
  best_name, best_st = None, None
  for name, block in ensembles.items():
    st = block["stability"]
    if st["total_r"] <= 0:
      continue
    score = (st.get("monthly_sharpe") or 0) * 10 + st["positive_pct"] * 0.2 + st["total_r"] * 0.01
    if best_st is None or score > best_st[0]:
      best_st = (score, st)
      best_name = name
  log(f"Recommended ensemble: {best_name}")

  if not args.skip_roster:
    ids = [m.get("id") for m in models]
    lab_map = {m.get("id"): lab for lab, m in zip(labels, models)}
    set_bridge_roster(ids, lab_map)

  payload = {
    "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "desk": ROOT.name,
    "side": side,
    "labels": labels,
    "models": packs,
    "ensembles": ensembles,
    "recommended_ensemble": best_name,
  }
  (OUT / "latest.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
  stamp = OUT / f"round3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
  stamp.write_text((OUT / "latest.json").read_text(encoding="utf-8"), encoding="utf-8")
  log(f"Wrote {OUT / 'latest.json'}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
