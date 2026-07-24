"""Lưu & tải báo cáo backtest để so sánh."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent.parent / "results" / "reports"
INDEX_PATH = REPORTS_DIR / "index.json"


def _load_index() -> dict:
  if not INDEX_PATH.exists():
    return {"reports": []}
  with open(INDEX_PATH, encoding="utf-8") as f:
    return json.load(f)


def _save_index(data: dict):
  REPORTS_DIR.mkdir(parents=True, exist_ok=True)
  with open(INDEX_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)


def report_label(result: dict) -> str:
  cfg = result.get("config", {})
  kb = "KB ON" if cfg.get("use_learning_kb") else "KB OFF"
  prof = cfg.get("kb_profile") or "-"
  oos = f"{cfg.get('oos_from') or 'auto'} → {cfg.get('oos_to') or 'auto'}"
  spread = cfg.get("spread_pips", "?")
  return f"{kb} · {prof} · OOS {oos} · spread {spread}"


def report_summary(result: dict) -> dict:
  cfg = result.get("config", {})
  o = result.get("overall_oos", {})
  return {
    "label": report_label(result),
    "kb_on": bool(cfg.get("use_learning_kb")),
    "kb_profile": cfg.get("kb_profile"),
    "oos_from": cfg.get("oos_from"),
    "oos_to": cfg.get("oos_to"),
    "spread_pips": cfg.get("spread_pips"),
    "n_trades": o.get("n_trades"),
    "win_rate_pct": o.get("win_rate_pct"),
    "avg_rr": o.get("avg_rr"),
    "total_r": o.get("total_r"),
    "max_drawdown_r": o.get("max_drawdown_r"),
    "profit_factor": o.get("profit_factor"),
    "trades_per_week": o.get("trades_per_week"),
    "data_source": (result.get("data_source") or {}).get("source"),
    "data_fingerprint": (result.get("data_source") or {}).get("fingerprint"),
  }


def save_report(result: dict, label: str | None = None, report_id: str | None = None) -> str:
  REPORTS_DIR.mkdir(parents=True, exist_ok=True)
  ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
  rid = report_id or f"rpt_{ts}"
  path = REPORTS_DIR / f"{rid}.json"
  with open(path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

  entry = {
    "id": rid,
    "label": label or report_label(result),
    "saved_at": datetime.now(timezone.utc).isoformat(),
    "summary": report_summary(result),
  }
  idx = _load_index()
  reports = [r for r in idx.get("reports", []) if r["id"] != rid]
  reports.insert(0, entry)
  idx["reports"] = reports[:100]
  _save_index(idx)
  return rid


def list_reports() -> list[dict]:
  return [
    report for report in _load_index().get("reports", [])
    if (report.get("summary") or {}).get("data_source") == "mt5_ea"
  ]


def load_report(report_id: str) -> dict | None:
  path = REPORTS_DIR / f"{report_id}.json"
  if not path.exists():
    return None
  with open(path, encoding="utf-8") as f:
    report = json.load(f)
  if (report.get("data_source") or {}).get("source") != "mt5_ea":
    return None
  return report


def delete_report(report_id: str) -> bool:
  path = REPORTS_DIR / f"{report_id}.json"
  if path.exists():
    path.unlink()
  idx = _load_index()
  before = len(idx.get("reports", []))
  idx["reports"] = [r for r in idx.get("reports", []) if r["id"] != report_id]
  _save_index(idx)
  return len(idx["reports"]) < before


def import_current_backtest(path: Path) -> str | None:
  """Import results/backtest_report.json vào kho so sánh."""
  if not path.exists():
    return None
  with open(path, encoding="utf-8") as f:
    result = json.load(f)
  return save_report(result)


def summaries_table(reports: list[dict]):
  import pandas as pd
  rows = []
  for r in reports:
    s = r.get("summary", {})
    rows.append({
      "id": r["id"],
      "label": r.get("label", ""),
      "saved_at": (r.get("saved_at") or "")[:16],
      "KB": "ON" if s.get("kb_on") else "OFF",
      "Profile": s.get("kb_profile") or "-",
      "OOS": f"{s.get('oos_from') or '?'} → {s.get('oos_to') or '?'}",
      "Lệnh": s.get("n_trades"),
      "WR%": s.get("win_rate_pct"),
      "RR": s.get("avg_rr"),
      "Total R": s.get("total_r"),
      "DD": s.get("max_drawdown_r"),
      "PF": s.get("profit_factor"),
    })
  return pd.DataFrame(rows)
