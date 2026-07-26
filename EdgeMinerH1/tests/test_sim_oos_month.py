"""Simulate (BridgeEngine HistoryFeed path) vs Health OOS by calendar month.

Remine each OOS week via the same ``decide_for_bar`` path as Simulate, then
compare ``strategy_name`` (+ monthly R baseline from weekly_log).

Usage:
  pytest tests/test_sim_oos_month.py -q -s --assert=plain
  pytest tests/test_sim_oos_month.py -q -s --assert=plain -k 2026-03
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from analytics import monthly_breakdown, monthly_from_weekly_log, trades_json_to_df
from gui.bridge_model_monitor import compare_live_week_to_oos
from gui.trade_model import get_model_by_id, load_model_report
from mt5_bridge.engine import BridgeEngine, _normalize
from mt5_bridge.history_sync import utc_to_broker_time
from mt5_bridge.trade_journal import save_trades

MODEL_ID = "tm_m15_best_2_49216b56"
MONTHS = ("2026-03", "2026-04")
ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"


def _results_path(month: str) -> Path:
  return RESULTS_DIR / f"sim_oos_{month.replace('-', '_')}.json"


@pytest.fixture(scope="module")
def mt5_frame() -> pd.DataFrame:
  path = ROOT / "data" / "mt5_eurusd_h1.parquet"
  if not path.exists():
    pytest.skip("mt5 h1 cache missing")
  return _normalize(pd.read_parquet(path))


@pytest.fixture(scope="module")
def active_model():
  model = get_model_by_id(MODEL_ID)
  if not model:
    pytest.skip(f"trade model `{MODEL_ID}` missing")
  report = load_model_report(MODEL_ID)
  if not report:
    pytest.skip("model health report missing")
  return model, report


def _oos_weeks_in_month(report: dict, month: str):
  rows = []
  for w in report.get("weekly_log") or []:
    ws = str(w.get("week_start") or "")[:10]
    if not ws.startswith(month):
      continue
    if "strategy" not in w and "oos_r" not in w:
      continue
    rows.append(w)
  return sorted(rows, key=lambda w: str(w.get("week_start"))[:10])


def _tip_bar_ts(frame: pd.DataFrame, week: str):
  week_start = pd.Timestamp(week)
  tip = week_start + pd.Timedelta(days=7) - pd.Timedelta(hours=1)
  if tip in frame.index:
    return tip
  idx = frame.index.get_indexer([tip], method="pad")[0]
  if idx < 0:
    return None
  ts = frame.index[idx]
  if ts < week_start or ts >= week_start + pd.Timedelta(days=7):
    week_bars = frame.index[
      (frame.index >= week_start) & (frame.index < week_start + pd.Timedelta(days=7))
    ]
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


def _make_sim_engine(tmp_path: Path, frame: pd.DataFrame) -> BridgeEngine:
  sim_dir = tmp_path / "bridge_sim"
  sim_dir.mkdir(parents=True)
  save_trades([], sim_dir)
  cache = tmp_path / "mt5_sim.parquet"
  frame.to_parquet(cache)
  eng = BridgeEngine(model_id=MODEL_ID, mt5_cache=cache, bridge_dir=sim_dir)
  eng.ensure_history()
  return eng


def _oos_month_stats(report: dict, month: str) -> dict:
  weekly = _oos_weeks_in_month(report, month)
  monthly = monthly_from_weekly_log(report.get("weekly_log") or [])
  row = None
  if monthly is not None and not monthly.empty:
    hit = monthly[monthly["month"].astype(str) == month]
    if not hit.empty:
      row = hit.iloc[0].to_dict()

  trades_df = trades_json_to_df(report.get("trades") or [])
  trades_month = None
  if trades_df is not None and not trades_df.empty:
    bd = monthly_breakdown(trades_df)
    hit = bd[bd["month"].astype(str) == month] if bd is not None and not bd.empty else None
    if hit is not None and not hit.empty:
      trades_month = hit.iloc[0].to_dict()

  return {
    "weeks": [
      {
        "week_start": str(w.get("week_start"))[:10],
        "strategy": w.get("strategy"),
        "oos_r": w.get("oos_r"),
        "oos_trades": w.get("oos_trades"),
      }
      for w in weekly
    ],
    "from_weekly_log": {
      "total_r": None if row is None else row.get("total_r"),
      "n_trades": None if row is None else row.get("n_trades"),
    },
    "from_trades": {
      "total_r": None if trades_month is None else trades_month.get("total_r"),
      "n_trades": None if trades_month is None else trades_month.get("n_trades"),
      "win_rate_pct": None if trades_month is None else trades_month.get("win_rate_pct"),
    },
  }


def run_sim_month_vs_oos(
  frame: pd.DataFrame,
  model: dict,
  report: dict,
  tmp_path: Path,
  *,
  month: str,
) -> dict:
  """Simulate remine each OOS week in ``month``; compare strategy to Health OOS."""
  weeks = _oos_weeks_in_month(report, month)
  if not weeks:
    return {"error": f"no OOS weeks in {month}", "month": month}

  eng = _make_sim_engine(tmp_path, frame)
  comparisons = []
  for w in weeks:
    week = str(w.get("week_start"))[:10]
    tip = _tip_bar_ts(frame, week)
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
    "model_id": MODEL_ID,
    "month": month,
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
      }
      for c in mismatches
    ],
  }


@pytest.fixture(scope="module", params=list(MONTHS), ids=list(MONTHS))
def month_parity(request, mt5_frame, active_model, tmp_path_factory):
  month = request.param
  model, report = active_model
  tmp = tmp_path_factory.mktemp(f"sim_oos_{month}")
  result = run_sim_month_vs_oos(mt5_frame, model, report, tmp, month=month)
  out = _results_path(month)
  out.parent.mkdir(parents=True, exist_ok=True)
  out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
  return result


@pytest.mark.parametrize("month", list(MONTHS), ids=list(MONTHS))
def test_oos_month_baseline(active_model, month):
  """Health OOS has weeks; weekly_log R sums to monthly bucket."""
  _, report = active_model
  weeks = _oos_weeks_in_month(report, month)
  assert weeks, f"no weekly_log rows for {month}"
  assert len(weeks) >= 4, f"expected ≥4 weeks in {month}, got {len(weeks)}"

  stats = _oos_month_stats(report, month)
  weekly_r = sum(float(w.get("oos_r") or 0) for w in weeks)
  monthly_r = stats["from_weekly_log"]["total_r"]
  assert monthly_r is not None
  assert abs(float(monthly_r) - weekly_r) < 1e-6


def test_sim_month_report_written(month_parity):
  """Artifact JSON for manual review / CI upload."""
  month = month_parity["month"]
  path = _results_path(month)
  assert path.exists()
  loaded = json.loads(path.read_text())
  assert loaded["month"] == month
  assert loaded["model_id"] == MODEL_ID
  assert loaded.get("n_weeks", 0) >= 4
  oos = loaded["oos_month"]["from_weekly_log"]
  print(
    f"\n[sim vs OOS {month}] match={loaded['n_strategy_match']}/{loaded['n_weeks']} "
    f"· OOS R={oos['total_r']} · trades={oos['n_trades']} → {path}"
  )
  for w in loaded.get("weeks") or []:
    mark = "OK" if w.get("match") else "DIFF"
    print(
      f"  [{mark}] {w.get('week')}: sim=`{w.get('sim_strategy')}` "
      f"| oos=`{w.get('oos_strategy')}` | oos_r={w.get('oos_r')}"
    )


def test_sim_month_vs_oos_strategies(month_parity):
  """Simulate remine mỗi tuần trong tháng → strategy phải khớp Health OOS."""
  result = month_parity
  month = result["month"]
  assert not result.get("error"), result.get("error")
  assert result["n_weeks"] >= 4

  oos = result["oos_month"]["from_weekly_log"]
  assert oos["total_r"] is not None
  assert oos["n_trades"] is not None

  if result["mismatches"]:
    lines = [
      f"Simulate ≠ OOS strategy · {month} · "
      f"match {result['n_strategy_match']}/{result['n_weeks']} · "
      f"OOS month R={oos['total_r']} · n={oos['n_trades']}",
      f"Wrote {_results_path(month)}",
    ]
    for m in result["mismatches"]:
      lines.append(
        f"  {m['week']}: sim=`{m['sim']}` ≠ oos=`{m['oos']}` (oos_r={m.get('oos_r')})"
      )
    pytest.fail("\n".join(lines))
