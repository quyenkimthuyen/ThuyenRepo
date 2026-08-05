"""Mining-space freshness assessor tests."""
from __future__ import annotations

from gui.mining_space_health import assess_mining_space_freshness


def _report_from_months(
  rows: list[dict], *, wr: float, rr: float, total_r: float,
) -> dict:
  weekly = []
  for row in rows:
    weekly.append({
      "week_start": f"{row['month']}-08",
      "oos_r": row["total_r"],
      "oos_trades": row.get("n", 4),
    })
  return {
    "overall_oos": {
      "win_rate_pct": wr,
      "avg_rr": rr,
      "total_r": total_r,
      "max_drawdown_r": 5.0,
      "profit_factor": 2.0,
      "trades_per_week": 3.0,
      "n_trades": sum(r.get("n", 4) for r in rows),
    },
    "weekly_log": weekly,
    "trades": [],
  }


def test_mining_space_fresh_when_active_beats_baseline():
  months = [
    {"month": "2026-01", "total_r": 10.0},
    {"month": "2026-02", "total_r": 12.0},
    {"month": "2026-03", "total_r": 8.0},
    {"month": "2026-04", "total_r": 9.0},
  ]
  base_months = [
    {"month": "2026-01", "total_r": 6.0},
    {"month": "2026-02", "total_r": 5.0},
    {"month": "2026-03", "total_r": 4.0},
    {"month": "2026-04", "total_r": 3.0},
  ]
  active = _report_from_months(months, wr=65.0, rr=2.8, total_r=39.0)
  baseline = _report_from_months(base_months, wr=48.0, rr=2.4, total_r=18.0)
  out = assess_mining_space_freshness(
    active, baseline, preset_name="elite_or_quality",
  )
  assert out["verdict"] == "fresh"
  assert out["late_edge_r"] is not None and out["late_edge_r"] > 0
  assert out["delta"]["win_rate_pct"] > 0


def test_mining_space_stale_when_quality_and_late_edge_lost():
  active_rows = [
    {"month": "2026-01", "total_r": 8.0},
    {"month": "2026-02", "total_r": 6.0},
    {"month": "2026-03", "total_r": -4.0},
    {"month": "2026-04", "total_r": -6.0},
  ]
  base_rows = [
    {"month": "2026-01", "total_r": 5.0},
    {"month": "2026-02", "total_r": 5.0},
    {"month": "2026-03", "total_r": 6.0},
    {"month": "2026-04", "total_r": 7.0},
  ]
  active = _report_from_months(active_rows, wr=42.0, rr=2.0, total_r=4.0)
  baseline = _report_from_months(base_rows, wr=50.0, rr=2.5, total_r=23.0)
  out = assess_mining_space_freshness(
    active, baseline, preset_name="elite_or_quality",
  )
  assert out["verdict"] == "stale"
  assert "lỗi thời" in out["message"]


def test_mining_space_insufficient_without_reports():
  out = assess_mining_space_freshness(None, None)
  assert out["verdict"] == "insufficient"
