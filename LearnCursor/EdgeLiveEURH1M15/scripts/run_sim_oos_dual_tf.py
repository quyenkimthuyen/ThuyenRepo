#!/usr/bin/env python3
"""Run Simulate (BridgeEngine HistoryFeed path) vs Health OOS for H1 and M15.

For each TF's active trade model, remine each OOS week tip bar via
``decide_for_bar`` (same path as Simulate) and compare strategy_name to OOS.

Usage:
  python scripts/run_sim_oos_dual_tf.py
  python scripts/run_sim_oos_dual_tf.py --months 2026-03,2026-04 --tf M15,H1
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from analytics import monthly_from_weekly_log
from config import set_active_tf
from gui.bridge_model_monitor import compare_live_week_to_oos
from gui.trade_model import get_model_by_id, load_active_model_id, load_model_report
from mt5_bridge.engine import BridgeEngine, _normalize
from mt5_bridge.history_sync import cache_path_for, utc_to_broker_time
from mt5_bridge.trade_journal import save_trades
from runtime_profiles import get_tf_defaults


DEFAULT_MONTHS = ("2026-03", "2026-04")


def _oos_weeks_in_month(report: dict, month: str) -> list[dict]:
  rows = []
  for w in report.get("weekly_log") or []:
    ws = str(w.get("week_start") or "")[:10]
    if not ws.startswith(month):
      continue
    if "strategy" not in w and "oos_r" not in w:
      continue
    rows.append(w)
  return sorted(rows, key=lambda w: str(w.get("week_start"))[:10])


def _oos_month_stats(report: dict, month: str) -> dict:
  weeks = _oos_weeks_in_month(report, month)
  monthly = monthly_from_weekly_log(report.get("weekly_log") or [])
  row = None
  if monthly is not None and not monthly.empty:
    hit = monthly[monthly["month"].astype(str) == month]
    if not hit.empty:
      row = hit.iloc[0].to_dict()
  return {
    "n_weeks": len(weeks),
    "weekly_r_sum": round(sum(float(w.get("oos_r") or 0) for w in weeks), 4),
    "from_weekly_log": {
      "total_r": None if row is None else row.get("total_r"),
      "n_trades": None if row is None else row.get("n_trades"),
    },
  }


def _tip_bar_ts(frame: pd.DataFrame, week: str, *, bar_minutes: int) -> pd.Timestamp | None:
  week_start = pd.Timestamp(week)
  tip = week_start + pd.Timedelta(days=7) - pd.Timedelta(minutes=int(bar_minutes))
  if tip in frame.index:
    return tip
  idx = frame.index.get_indexer([tip], method="pad")[0]
  if idx < 0:
    return None
  ts = frame.index[idx]
  week_end = week_start + pd.Timedelta(days=7)
  if ts < week_start or ts >= week_end:
    week_bars = frame.index[(frame.index >= week_start) & (frame.index < week_end)]
    return week_bars[-1] if len(week_bars) else None
  return ts


def _bar_payload(frame: pd.DataFrame, bar_ts: pd.Timestamp) -> dict:
  row = frame.loc[bar_ts]
  return {
    "time": utc_to_broker_time(bar_ts).strftime("%Y.%m.%d %H:%M"),
    "open": float(row.Open),
    "high": float(row.High),
    "low": float(row.Low),
    "close": float(row.Close),
    "tick_volume": float(row.Volume),
  }


def _make_sim_engine(
  tmp_path: Path,
  frame: pd.DataFrame,
  *,
  model_id: str,
  tf: str,
) -> BridgeEngine:
  sim_dir = tmp_path / f"bridge_sim_{tf.lower()}"
  sim_dir.mkdir(parents=True)
  save_trades([], sim_dir)
  cache = tmp_path / f"mt5_sim_{tf.lower()}.parquet"
  frame.to_parquet(cache)
  eng = BridgeEngine(
    model_id=model_id,
    mt5_cache=cache,
    bridge_dir=sim_dir,
    tf=tf,
  )
  eng.ensure_history()
  return eng


def run_sim_month_vs_oos(
  *,
  tf: str,
  model_id: str,
  frame: pd.DataFrame,
  model: dict,
  report: dict,
  month: str,
  tmp_path: Path,
) -> dict:
  defaults = get_tf_defaults(tf)
  weeks = _oos_weeks_in_month(report, month)
  if not weeks:
    return {"error": f"no OOS weeks in {month}", "tf": tf, "month": month, "model_id": model_id}

  eng = _make_sim_engine(tmp_path, frame, model_id=model_id, tf=tf)
  comparisons = []
  for w in weeks:
    week = str(w.get("week_start"))[:10]
    tip = _tip_bar_ts(frame, week, bar_minutes=defaults.bar_minutes)
    if tip is None:
      comparisons.append({
        "week": week,
        "oos_strategy": w.get("strategy"),
        "sim_strategy": None,
        "match": False,
        "error": "no bar in cache",
        "oos_r": w.get("oos_r"),
        "oos_trades": w.get("oos_trades"),
      })
      continue
    decision = eng.decide_for_bar(_bar_payload(frame, tip))
    sim_name = decision.get("strategy_name")
    oos_name = w.get("strategy")
    parity = compare_live_week_to_oos(
      model,
      week_start=week,
      strategy_name=sim_name,
      conditions_fp=decision.get("conditions_fp"),
    )
    comparisons.append({
      "week": week,
      "bar": utc_to_broker_time(tip).strftime("%Y.%m.%d %H:%M"),
      "oos_strategy": oos_name,
      "sim_strategy": sim_name,
      "sim_week_start": str(decision.get("week_start") or "")[:10],
      "sim_action": decision.get("action"),
      "sim_reason": decision.get("reason"),
      "conditions_fp": decision.get("conditions_fp"),
      "match": bool(sim_name and oos_name and sim_name == oos_name),
      "parity_status": parity.get("status"),
      "oos_r": w.get("oos_r"),
      "oos_trades": w.get("oos_trades"),
    })

  n_match = sum(1 for c in comparisons if c.get("match"))
  mismatches = [c for c in comparisons if not c.get("match")]
  oos_month = _oos_month_stats(report, month)
  return {
    "tf": tf,
    "model_id": model_id,
    "month": month,
    "bar_minutes": defaults.bar_minutes,
    "conditions_fp": eng.conditions_fp,
    "n_weeks": len(comparisons),
    "n_strategy_match": n_match,
    "n_strategy_mismatch": len(mismatches),
    "strategy_match_rate": round(n_match / len(comparisons), 3) if comparisons else 0.0,
    "oos_month": oos_month,
    "weeks": comparisons,
    "mismatches": [
      {
        "week": c["week"],
        "sim": c.get("sim_strategy"),
        "oos": c.get("oos_strategy"),
        "oos_r": c.get("oos_r"),
        "sim_reason": c.get("sim_reason"),
        "error": c.get("error"),
      }
      for c in mismatches
    ],
  }


def run_tf(tf: str, months: list[str]) -> list[dict]:
  set_active_tf(tf)
  model_id = load_active_model_id()
  if not model_id:
    return [{"tf": tf, "error": "no active trade model"}]
  model = get_model_by_id(model_id)
  report = load_model_report(model_id)
  if not model or not report:
    return [{"tf": tf, "model_id": model_id, "error": "model or health report missing"}]

  cache = cache_path_for(tf)
  if not cache.exists():
    return [{"tf": tf, "model_id": model_id, "error": f"cache missing: {cache}"}]
  frame = _normalize(pd.read_parquet(cache))

  out_dir = ROOT / "results" / tf.lower()
  out_dir.mkdir(parents=True, exist_ok=True)
  results = []
  with tempfile.TemporaryDirectory(prefix=f"sim_oos_{tf}_") as tmp:
    tmp_path = Path(tmp)
    for month in months:
      print(f"\n=== {tf} Simulate vs OOS · {month} · model={model_id} ===", flush=True)
      result = run_sim_month_vs_oos(
        tf=tf,
        model_id=model_id,
        frame=frame,
        model=model,
        report=report,
        month=month,
        tmp_path=tmp_path / month,
      )
      out = out_dir / f"sim_oos_{month.replace('-', '_')}.json"
      out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
      result["artifact"] = str(out)
      results.append(result)

      if result.get("error"):
        print(f"  ERROR: {result['error']}", flush=True)
        continue
      oos = result["oos_month"]["from_weekly_log"]
      print(
        f"  match={result['n_strategy_match']}/{result['n_weeks']} "
        f"({result['strategy_match_rate']:.0%}) · "
        f"OOS R={oos.get('total_r')} · trades={oos.get('n_trades')} · "
        f"fp={result.get('conditions_fp')}",
        flush=True,
      )
      for w in result.get("weeks") or []:
        mark = "OK" if w.get("match") else "DIFF"
        print(
          f"  [{mark}] {w.get('week')}: sim=`{w.get('sim_strategy')}` "
          f"| oos=`{w.get('oos_strategy')}` | action={w.get('sim_action')} "
          f"| oos_r={w.get('oos_r')}",
          flush=True,
        )
      print(f"  wrote {out}", flush=True)
  return results


def main() -> int:
  ap = argparse.ArgumentParser(description="Dual-TF Simulate vs OOS report")
  ap.add_argument("--tf", default="M15,H1", help="Comma-separated TFs")
  ap.add_argument(
    "--months",
    default=",".join(DEFAULT_MONTHS),
    help="Comma-separated YYYY-MM months",
  )
  args = ap.parse_args()
  tfs = [t.strip().upper() for t in args.tf.split(",") if t.strip()]
  months = [m.strip() for m in args.months.split(",") if m.strip()]

  all_results: list[dict] = []
  for tf in tfs:
    all_results.extend(run_tf(tf, months))

  summary_path = ROOT / "results" / "sim_oos_dual_tf_summary.json"
  summary = {
    "tfs": tfs,
    "months": months,
    "results": [
      {
        "tf": r.get("tf"),
        "month": r.get("month"),
        "model_id": r.get("model_id"),
        "n_weeks": r.get("n_weeks"),
        "n_strategy_match": r.get("n_strategy_match"),
        "strategy_match_rate": r.get("strategy_match_rate"),
        "oos_r": (r.get("oos_month") or {}).get("from_weekly_log", {}).get("total_r"),
        "oos_trades": (r.get("oos_month") or {}).get("from_weekly_log", {}).get("n_trades"),
        "error": r.get("error"),
        "artifact": r.get("artifact"),
        "n_mismatch": r.get("n_strategy_mismatch"),
      }
      for r in all_results
    ],
  }
  summary_path.parent.mkdir(parents=True, exist_ok=True)
  summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

  print("\n======== SUMMARY ========", flush=True)
  ok = True
  for row in summary["results"]:
    if row.get("error"):
      ok = False
      print(f"FAIL {row['tf']} {row.get('month')}: {row['error']}", flush=True)
      continue
    rate = float(row.get("strategy_match_rate") or 0)
    status = "PASS" if rate >= 1.0 else ("WARN" if rate >= 0.75 else "FAIL")
    if status == "FAIL":
      ok = False
    print(
      f"{status} {row['tf']} {row['month']}: "
      f"match={row['n_strategy_match']}/{row['n_weeks']} ({rate:.0%}) · "
      f"OOS R={row['oos_r']} · trades={row['oos_trades']}",
      flush=True,
    )
  print(f"Summary → {summary_path}", flush=True)
  return 0 if ok else 1


if __name__ == "__main__":
  raise SystemExit(main())
