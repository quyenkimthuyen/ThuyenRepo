#!/usr/bin/env python3
"""Export Best 3m (or any trade model) last_strategy → frozen JSON snapshot."""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "results" / "trade_models.json"
ACTIVE_MODEL = ROOT / "results" / "active_trade_model.json"
MODELS_DIR = ROOT / "results" / "trade_models"
OUT_DIR = ROOT / "mt5" / "frozen"


def _load(path: Path):
  with open(path, encoding="utf-8") as f:
    return json.load(f)


def main():
  ap = argparse.ArgumentParser(description="Freeze trade model last_strategy for MT5 EA")
  ap.add_argument("--model-id", default=None)
  ap.add_argument("--out", type=Path, default=OUT_DIR / "best_3m_frozen.json")
  args = ap.parse_args()
  if not args.model_id and ACTIVE_MODEL.exists():
    args.model_id = (_load(ACTIVE_MODEL) or {}).get("id")
  if not args.model_id:
    raise SystemExit("No active Trade Model.")

  store = _load(MODELS) if MODELS.exists() else {"models": []}
  meta = next((m for m in store.get("models", []) if m.get("id") == args.model_id), None)
  report_path = MODELS_DIR / f"{args.model_id}.json"
  if not report_path.exists():
    raise SystemExit(f"Missing report: {report_path}")

  report = _load(report_path)
  strat = report.get("last_strategy")
  if not strat:
    raise SystemExit("Report has no last_strategy")

  weekly = report.get("weekly_log") or []
  last_week = weekly[-1] if weekly else {}
  score_thr = float(last_week.get("score_thr") or 0.83)

  payload = {
    "source_trade_model_id": args.model_id,
    "source_label": (meta or {}).get("label") or args.model_id,
    "frozen_at": str(date.today()),
    "warning": (
      "Static freeze of last_strategy only. Does NOT re-mine weekly or use ML/KB. "
      "MT5 results will differ from app walk-forward."
    ),
    "symbol": "EURUSD",
    "timeframe": "H1",
    "strategy": {
      "name": strat.get("name"),
      "exit_mode": strat.get("exit_mode", "hybrid"),
      "ml_prob_min": strat.get("ml_prob_min", 0.4),
      "ml_enabled": False,
      "score_threshold": score_thr,
      "rr": strat.get("rr", 3.0),
      "atr_mult_sl": strat.get("atr_mult", 0.9),
      "min_rules_match": 2,
      "max_trades_per_week": 2,
      "min_bars_between": 4,
      "max_hold_bars": 36,
      "session_filter": True,
      "session_hour_from": 7,
      "session_hour_to": 20,
      "trail_activate_r": 1.8,
      "trail_distance_r": 0.6,
      "risk_pct": 1.0,
      "long_rules": strat.get("long_rules") or [],
      "short_rules": strat.get("short_rules") or [],
    },
  }

  args.out.parent.mkdir(parents=True, exist_ok=True)
  with open(args.out, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2, ensure_ascii=False)
  print(f"Wrote {args.out}")
  print(f"Strategy: {payload['strategy']['name']}")
  print(f"Long rules: {len(payload['strategy']['long_rules'])}  Short: {len(payload['strategy']['short_rules'])}")


if __name__ == "__main__":
  main()
