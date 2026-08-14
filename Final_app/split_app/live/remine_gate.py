"""Remine quality gate + alerts for Live / Live-like bridge path.

After ``optimize_on_window`` produces a strategy for an unseen week, score it on
the train window before allowing Live decisions. Fail → FLAT + alert (no trade).

Prefs: ``live/results/remine_gate_prefs.json``
Alerts: ``live/results/remine_gate_alerts.jsonl`` + ``remine_gate_last.json``
Disable: env ``LIVE_REMINE_GATE=0``
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from live_config import RESULTS_DIR

PREFS_PATH = RESULTS_DIR / "remine_gate_prefs.json"
ALERTS_PATH = RESULTS_DIR / "remine_gate_alerts.jsonl"
LAST_PATH = RESULTS_DIR / "remine_gate_last.json"

DEFAULT_PREFS: dict[str, Any] = {
  "enabled": True,
  # Absolute floors on train-window backtest of the remined strategy
  "min_n_trades": 20,
  "min_profit_factor": 1.3,
  "min_total_r": 0.0,
  # If model baseline PF exists: remine PF must be >= ratio * baseline_pf
  "min_pf_vs_baseline": 0.75,
  "compare_baseline": True,
}


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def _write(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + ".tmp")
  tmp.write_text(
    json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n",
    encoding="utf-8",
  )
  tmp.replace(path)


def gate_enabled() -> bool:
  env = os.environ.get("LIVE_REMINE_GATE", "").strip().lower()
  if env in ("0", "false", "no", "off"):
    return False
  if env in ("1", "true", "yes", "on"):
    return True
  prefs = load_prefs()
  return bool(prefs.get("enabled", True))


def load_prefs() -> dict[str, Any]:
  data = _read(PREFS_PATH) or {}
  out = dict(DEFAULT_PREFS)
  if isinstance(data, dict):
    out.update({k: data[k] for k in DEFAULT_PREFS if k in data})
  return out


def save_prefs(updates: dict[str, Any] | None = None) -> dict[str, Any]:
  prefs = load_prefs()
  if updates:
    prefs.update(updates)
  prefs["updated_at"] = _now()
  _write(PREFS_PATH, prefs)
  return prefs


def load_model_baseline(model_id: str) -> dict[str, Any]:
  """Baseline metrics from Live materialized store / package model.json."""
  mid = str(model_id or "")
  candidates = [
    RESULTS_DIR / "trade_models.json",
  ]
  store = None
  for p in candidates:
    store = _read(p)
    if store:
      break
  models = (store or {}).get("models") or []
  row = next((m for m in models if str(m.get("id")) == mid), None)
  if not row:
    # installed package fallback
    inst_root = RESULTS_DIR.parent / "installed_models"
    if inst_root.is_dir():
      for d in inst_root.iterdir():
        if not d.is_dir():
          continue
        man = _read(d / "manifest.json") or {}
        if str(man.get("model_id") or "") != mid and not d.name.endswith(mid):
          continue
        metrics = _read(d / "metrics.json") or {}
        model = _read(d / "model.json") or {}
        row = {**model, **metrics}
        break
  if not row:
    return {}
  def _f(*keys: str) -> float | None:
    for k in keys:
      if row.get(k) is None:
        continue
      try:
        return float(row[k])
      except (TypeError, ValueError):
        continue
    return None
  return {
    "total_r": _f("total_r"),
    "profit_factor": _f("profit_factor", "pf"),
    "win_rate_pct": _f("win_rate_pct", "win_rate"),
    "n_trades": _f("n_trades", "trades"),
    "label": row.get("label"),
  }


def evaluate_strategy_on_train(
  *,
  fm: Any,
  strat: Any,
  train_start_idx: int,
  train_end_idx: int,
  spread_pips: float = 1.0,
  slippage_pips: float = 0.3,
) -> dict[str, Any]:
  """Backtest remined strategy on the train window used for mining."""
  from strategy import compute_metrics
  from strategy_miner import backtest_mined, generate_signals_mined

  ts, te = int(train_start_idx), int(train_end_idx)
  if te - ts < 10:
    return {
      "n_trades": 0,
      "profit_factor": 0.0,
      "total_r": 0.0,
      "win_rate": 0.0,
      "error": "train_window_too_small",
    }
  signals = generate_signals_mined(fm, strat, ts, te)
  trades = backtest_mined(
    fm, strat, signals, ts, te,
    spread_pips=float(spread_pips),
    slippage_pips=float(slippage_pips),
  )
  m = compute_metrics(trades)
  return {
    "n_trades": int(m.get("n_trades") or 0),
    "profit_factor": float(m.get("profit_factor") or 0.0),
    "total_r": float(m.get("total_r") or 0.0),
    "win_rate": float(m.get("win_rate") or 0.0),
    "max_drawdown_r": float(m.get("max_drawdown_r") or 0.0),
  }


def check_remine_gate(
  metrics: dict[str, Any],
  *,
  baseline: dict[str, Any] | None = None,
  prefs: dict[str, Any] | None = None,
) -> dict[str, Any]:
  """Return {ok, reasons, metrics, baseline, prefs_used}."""
  prefs = prefs or load_prefs()
  baseline = baseline or {}
  reasons: list[str] = []
  n = int(metrics.get("n_trades") or 0)
  pf = float(metrics.get("profit_factor") or 0.0)
  if pf == float("inf"):
    pf = 99.0
  tr = float(metrics.get("total_r") or 0.0)

  min_n = int(prefs.get("min_n_trades") or 0)
  min_pf = float(prefs.get("min_profit_factor") or 0.0)
  min_tr = float(prefs.get("min_total_r") or 0.0)

  if n < min_n:
    reasons.append(f"n_trades {n} < {min_n}")
  if pf < min_pf:
    reasons.append(f"profit_factor {pf:.3f} < {min_pf}")
  if tr < min_tr:
    reasons.append(f"total_r {tr:.3f} < {min_tr}")

  if prefs.get("compare_baseline"):
    base_pf = baseline.get("profit_factor")
    ratio = float(prefs.get("min_pf_vs_baseline") or 0.0)
    if base_pf is not None and ratio > 0 and float(base_pf) > 0:
      need = float(base_pf) * ratio
      if pf < need:
        reasons.append(
          f"profit_factor {pf:.3f} < {ratio:.2f}× baseline_pf {float(base_pf):.3f} (need {need:.3f})"
        )

  return {
    "ok": not reasons,
    "reasons": reasons,
    "metrics": {
      "n_trades": n,
      "profit_factor": round(pf, 3),
      "total_r": round(tr, 3),
      "win_rate": round(float(metrics.get("win_rate") or 0.0), 4),
      "max_drawdown_r": metrics.get("max_drawdown_r"),
    },
    "baseline": baseline,
    "prefs": {
      "min_n_trades": min_n,
      "min_profit_factor": min_pf,
      "min_total_r": min_tr,
      "min_pf_vs_baseline": prefs.get("min_pf_vs_baseline"),
      "compare_baseline": prefs.get("compare_baseline"),
    },
  }


def emit_remine_alert(payload: dict[str, Any]) -> dict[str, Any]:
  """Append alert line + update last-alert snapshot for UI/health."""
  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  row = {**payload, "updated_at": _now()}
  try:
    with ALERTS_PATH.open("a", encoding="utf-8") as f:
      f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
  except OSError:
    pass
  _write(LAST_PATH, row)
  level = "ok" if row.get("ok") else "fail"
  print(
    f"[remine_gate] {level} model={row.get('model_id')} week={row.get('week_start')} "
    f"pf={((row.get('metrics') or {}).get('profit_factor'))} "
    f"n={((row.get('metrics') or {}).get('n_trades'))} "
    f"reasons={row.get('reasons') or []}",
    flush=True,
  )
  return row


def load_last_alert() -> dict[str, Any]:
  return _read(LAST_PATH) or {}


def remove_live_week_entry(model_id: str, week_start: Any) -> bool:
  """Drop a live_weeks genome so a failed gate cannot be reused next bar."""
  try:
    import trade_model_schedule as sched
    path = sched.model_live_weeks_path(str(model_id))
    data = _read(path)
    if not data:
      return False
    try:
      ws = str(week_start.date())
    except Exception:
      ws = str(week_start)[:10]
    weekly = [
      e for e in (data.get("weekly") or [])
      if not (isinstance(e, dict) and str(e.get("week_start")) == ws)
    ]
    if len(weekly) == len(data.get("weekly") or []):
      return False
    data["weekly"] = weekly
    data["updated_at"] = _now()
    _write(path, data)
    return True
  except Exception as exc:
    print(f"[remine_gate] remove_live_week failed: {exc}", flush=True)
    return False


def gate_remine_strategy(
  *,
  model_id: str,
  week_start: Any,
  fm: Any,
  strat: Any,
  train_start_idx: int,
  train_end_idx: int,
  spread_pips: float = 1.0,
  slippage_pips: float = 0.3,
) -> dict[str, Any]:
  """Full gate: evaluate → check → alert. Returns check result dict."""
  if not gate_enabled():
    return {"ok": True, "skipped": True, "reasons": [], "metrics": {}}
  metrics = evaluate_strategy_on_train(
    fm=fm,
    strat=strat,
    train_start_idx=train_start_idx,
    train_end_idx=train_end_idx,
    spread_pips=spread_pips,
    slippage_pips=slippage_pips,
  )
  baseline = load_model_baseline(model_id)
  result = check_remine_gate(metrics, baseline=baseline)
  try:
    ws = str(week_start.date())
  except Exception:
    ws = str(week_start)[:10]
  alert = emit_remine_alert({
    "model_id": model_id,
    "week_start": ws,
    "ok": result["ok"],
    "reasons": result["reasons"],
    "metrics": result["metrics"],
    "baseline": {
      k: baseline.get(k) for k in ("total_r", "profit_factor", "win_rate_pct", "n_trades", "label")
    },
    "event": "remine_gate_pass" if result["ok"] else "remine_gate_fail",
  })
  result["alert"] = alert
  result["week_start"] = ws
  return result
