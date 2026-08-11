"""Live BridgeEngine vs OOS (+ Live vs Sim) for the same window as HistoryFeed sim.

Default window: 2026-01-01 → 2026-07-17 (matches completed Simulate run).

Usage:
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/test_live_oos_2026.py -q -s --assert=plain
  python3 tests/test_live_oos_2026.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import pytest

from analytics import monthly_from_weekly_log
from gui.bridge_model_monitor import compare_live_week_to_oos
from gui.trade_model import get_model_by_id, load_model_report
from mt5_bridge.engine import BridgeEngine, _normalize
from mt5_bridge.history_sync import utc_to_broker_time
from mt5_bridge.trade_journal import save_trades

MODEL_ID = "tm_m15_best_2_49216b56"
DATE_FROM = "2026-01-01"
DATE_TO = "2026-07-17"
ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "results" / "live_oos_2026.json"

_DECISION_KEYS = (
  "action", "signal_id", "strategy_name", "week_start", "conditions_fp",
  "reason", "entry", "sl", "tp", "rr",
)


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


def _tip_bar_ts(frame: pd.DataFrame, week: str):
  week_start = pd.Timestamp(week)
  tip = week_start + pd.Timedelta(days=7) - pd.Timedelta(minutes=5)
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


def _oos_weeks(report: dict, date_from: str, date_to: str):
  d0 = pd.Timestamp(date_from)
  d1 = pd.Timestamp(date_to)
  rows = []
  for w in report.get("weekly_log") or []:
    ws = str(w.get("week_start") or "")[:10]
    if not ws:
      continue
    ts = pd.Timestamp(ws)
    if ts < d0 or ts > d1:
      continue
    if "strategy" not in w:
      continue
    rows.append(w)
  return sorted(rows, key=lambda w: str(w.get("week_start"))[:10])


def _make_engine(tmp: Path, frame: pd.DataFrame, name: str) -> BridgeEngine:
  bridge = tmp / name
  bridge.mkdir(parents=True)
  save_trades([], bridge)
  cache = tmp / f"mt5_{name}.parquet"
  frame.to_parquet(cache)
  eng = BridgeEngine(model_id=MODEL_ID, mt5_cache=cache, bridge_dir=bridge)
  eng.ensure_history()
  return eng


def run_live_window_parity(
  frame: pd.DataFrame,
  model: dict,
  report: dict,
  tmp: Path,
  *,
  date_from: str = DATE_FROM,
  date_to: str = DATE_TO,
  sample_every: int = 8,
) -> dict:
  """Tip remine Live vs OOS + sampled Live vs Sim decision parity."""
  t0 = time.time()
  weeks = _oos_weeks(report, date_from, date_to)
  live = _make_engine(tmp, frame, "bridge_live")
  sim = _make_engine(tmp, frame, "bridge_sim")

  week_rows = []
  for w in weeks:
    week = str(w.get("week_start"))[:10]
    tip = _tip_bar_ts(frame, week)
    if tip is None or tip > pd.Timestamp(date_to) + pd.Timedelta(days=1):
      week_rows.append({
        "week": week,
        "oos_strategy": w.get("strategy"),
        "live_strategy": None,
        "match": False,
        "error": "no tip bar",
        "oos_r": w.get("oos_r"),
      })
      continue
    d = live.decide_for_bar(_bar_payload(frame, tip))
    name = d.get("strategy_name")
    oos_name = w.get("strategy")
    parity = compare_live_week_to_oos(
      model, week_start=week, strategy_name=name, conditions_fp=d.get("conditions_fp"),
    )
    week_rows.append({
      "week": week,
      "bar": utc_to_broker_time(tip).strftime("%Y.%m.%d %H:%M"),
      "oos_strategy": oos_name,
      "live_strategy": name,
      "match": bool(name and oos_name and name == oos_name),
      "parity_status": parity.get("status"),
      "oos_r": w.get("oos_r"),
      "oos_trades": w.get("oos_trades"),
    })

  # Sampled bars Live vs Sim
  d0 = pd.Timestamp(date_from)
  d1 = pd.Timestamp(date_to) + pd.Timedelta(hours=23, minutes=45)
  bars = list(frame.index[(frame.index >= d0) & (frame.index <= d1)])
  sampled = bars[:: max(1, sample_every)]
  live_sim_mismatches = []
  n_signal = n_flat = n_hold = n_other = 0
  for ts in sampled:
    payload = _bar_payload(frame, ts)
    dl = live.decide_for_bar(payload)
    ds = sim.decide_for_bar(payload)
    sl = {k: dl.get(k) for k in _DECISION_KEYS}
    ss = {k: ds.get(k) for k in _DECISION_KEYS}
    act = str(dl.get("action") or "")
    if act in ("BUY", "SELL"):
      n_signal += 1
    elif act == "FLAT":
      n_flat += 1
    elif act == "HOLD":
      n_hold += 1
    else:
      n_other += 1
    if sl != ss:
      live_sim_mismatches.append({
        "bar": payload.get("time"),
        "live": sl,
        "sim": ss,
      })
      if len(live_sim_mismatches) >= 20:
        break

  n_match = sum(1 for r in week_rows if r.get("match"))
  mismatches = [r for r in week_rows if not r.get("match")]
  oos_month = monthly_from_weekly_log(report.get("weekly_log") or [])
  if oos_month is not None and not oos_month.empty:
    oos_month = oos_month[
      (oos_month["month"].astype(str) >= date_from[:7])
      & (oos_month["month"].astype(str) <= date_to[:7])
    ]

  out = {
    "model_id": MODEL_ID,
    "conditions_fp": live.conditions_fp,
    "window_from": date_from,
    "window_to": date_to,
    "elapsed_sec": round(time.time() - t0, 1),
    "n_weeks": len(week_rows),
    "n_strategy_match": n_match,
    "n_strategy_mismatch": len(mismatches),
    "strategy_match_rate": round(n_match / len(week_rows), 3) if week_rows else 0.0,
    "weeks": week_rows,
    "oos_mismatches": [
      {"week": m["week"], "live": m.get("live_strategy"), "oos": m.get("oos_strategy"), "oos_r": m.get("oos_r")}
      for m in mismatches
    ],
    "oos_month_from_weekly_log": (
      oos_month.to_dict(orient="records") if oos_month is not None and not oos_month.empty else []
    ),
    "bars_in_window": len(bars),
    "bars_sampled": len(sampled),
    "sample_every": sample_every,
    "live_sim_mismatches": len(live_sim_mismatches),
    "live_sim_mismatch_samples": live_sim_mismatches[:10],
    "n_signal": n_signal,
    "n_flat": n_flat,
    "n_hold": n_hold,
    "n_other": n_other,
  }
  return out


@pytest.fixture(scope="module")
def mt5_frame() -> pd.DataFrame:
  path = ROOT / "data" / "mt5_eurusd_m5.parquet"
  if not path.exists():
    pytest.skip("mt5 m15 cache missing")
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


@pytest.fixture(scope="module")
def live_2026_parity(mt5_frame, active_model, tmp_path_factory):
  model, report = active_model
  tmp = tmp_path_factory.mktemp("live_oos_2026")
  result = run_live_window_parity(mt5_frame, model, report, tmp)
  RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
  RESULTS_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
  return result


def test_live_2026_report(live_2026_parity):
  r = live_2026_parity
  assert r["n_weeks"] >= 20
  assert RESULTS_PATH.exists()
  print(
    f"\n[Live vs OOS {DATE_FROM}→{DATE_TO}] "
    f"strategy match={r['n_strategy_match']}/{r['n_weeks']} "
    f"· Live≠Sim decisions={r['live_sim_mismatches']} "
    f"· sampled bars={r['bars_sampled']} "
    f"· {RESULTS_PATH}"
  )
  for w in r.get("weeks") or []:
    mark = "OK" if w.get("match") else "DIFF"
    print(
      f"  [{mark}] {w.get('week')}: live=`{w.get('live_strategy')}` "
      f"| oos=`{w.get('oos_strategy')}` | oos_r={w.get('oos_r')}"
    )


def test_live_sim_decisions_identical_on_sample(live_2026_parity):
  """Empty journals ⇒ Live and Simulate decide_for_bar must match."""
  r = live_2026_parity
  assert r["live_sim_mismatches"] == 0, (
    f"Live≠Sim on {r['live_sim_mismatches']} sampled bars — "
    f"samples={r.get('live_sim_mismatch_samples')}"
  )


def test_live_oos_strategy_parity_2026(live_2026_parity):
  """Tip remine Live should match Health OOS weekly strategy (full weeks in window)."""
  r = live_2026_parity
  # Ignore trailing week whose tip bar is past date_to (incomplete HistoryFeed window)
  date_to = pd.Timestamp(DATE_TO)
  hard = []
  for m in r["oos_mismatches"]:
    week = m["week"]
    tip = pd.Timestamp(week) + pd.Timedelta(days=7) - pd.Timedelta(minutes=5)
    if tip.normalize() > date_to.normalize():
      continue
    hard.append(m)
  if hard:
    lines = [
      f"Live ≠ OOS strategy · {DATE_FROM}→{DATE_TO} · "
      f"hard mismatches {len(hard)} "
      f"(raw match {r['n_strategy_match']}/{r['n_weeks']})",
      f"Wrote {RESULTS_PATH}",
    ]
    for m in hard[:15]:
      lines.append(
        f"  {m['week']}: live=`{m['live']}` ≠ oos=`{m['oos']}` (oos_r={m.get('oos_r')})"
      )
    pytest.fail("\n".join(lines))


if __name__ == "__main__":
  frame = _normalize(pd.read_parquet(ROOT / "data" / "mt5_eurusd_m5.parquet"))
  model = get_model_by_id(MODEL_ID)
  report = load_model_report(MODEL_ID)
  import tempfile
  with tempfile.TemporaryDirectory() as td:
    result = run_live_window_parity(frame, model, report, Path(td))
  RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
  RESULTS_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
  print(json.dumps({
    "n_weeks": result["n_weeks"],
    "strategy_match": f"{result['n_strategy_match']}/{result['n_weeks']}",
    "live_sim_mismatches": result["live_sim_mismatches"],
    "elapsed_sec": result["elapsed_sec"],
    "path": str(RESULTS_PATH),
  }, indent=2))
