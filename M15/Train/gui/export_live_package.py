"""Export a TrainApp Trade Model to a Live `.tmpkg` package.

Writes the same v1 layout Trade imports at http://127.0.0.1:8801/?nav=Models
(`manifest.json` + `model.json` + `kb_pin.json` + `schedule.json`).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

_TRAINAPP = Path(__file__).resolve().parents[1]
if str(_TRAINAPP) not in sys.path:
  sys.path.insert(0, str(_TRAINAPP))

from desk_context import TRAINAPP_ROOT, load_desk  # noqa: E402
from gui.navigation import LABEL_TAB_OOS  # noqa: E402


def trade_app_root() -> Path:
  return TRAINAPP_ROOT.parent / "Trade"


def default_export_dir() -> Path:
  inbox = trade_app_root() / "live" / "packages_inbox"
  return inbox


def _slug(s: str) -> str:
  return re.sub(r"[^a-zA-Z0-9_-]+", "_", (s or "model").strip())[:40]


def _import_package_format():
  root = trade_app_root()
  if not (root / "shared" / "package_format.py").is_file():
    raise RuntimeError(f"Không thấy Trade package format: {root / 'shared' / 'package_format.py'}")
  if str(root) not in sys.path:
    sys.path.insert(0, str(root))
  from shared.package_format import (  # noqa: E402
    build_manifest,
    schedule_weekly_count,
    validate_schedule_payload,
    write_package,
  )
  return build_manifest, schedule_weekly_count, validate_schedule_payload, write_package


def _read_json(path: Path) -> Any:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def runtime_results_dir() -> Path:
  cfg = load_desk()
  return Path(cfg["runtime_root"]) / "results"


def load_schedule(model_id: str) -> dict | None:
  p = runtime_results_dir() / "trade_models" / f"{model_id}_schedule.json"
  data = _read_json(p)
  return data if isinstance(data, dict) else None


def resolve_kb_pin(model: dict) -> Path | None:
  if not model.get("use_kb", True):
    return None
  pin = model.get("kb_pin_path")
  results = runtime_results_dir()
  if pin:
    p = Path(pin)
    if not p.is_absolute():
      p = results / pin
    if p.exists():
      return p
  mid = model.get("id")
  if mid:
    cand = results / "trade_models" / f"{mid}_kb_pin.json"
    if cand.exists():
      return cand
  try:
    from trade_model_kb_pin import ensure_model_kb_pin, resolve_pin_absolute
    ensure_model_kb_pin(model)
    return resolve_pin_absolute(model.get("kb_pin_path"))
  except Exception:
    return None


def metrics_from_model(m: dict) -> dict:
  keys = (
    "total_r", "profit_factor", "win_rate_pct", "max_drawdown_r",
    "n_trades", "trades_per_week", "oos_from", "oos_to",
  )
  return {k: m.get(k) for k in keys if m.get(k) is not None}


def resolve_mining_search_space(model: dict) -> dict | None:
  space = model.get("mining_search_space")
  if isinstance(space, dict) and space:
    return space
  mid = model.get("id")
  if not mid:
    return None
  try:
    from gui.trade_model import load_model_report
    report = load_model_report(str(mid))
  except Exception:
    report = None
  cfg = (report or {}).get("config") or {}
  space = cfg.get("mining_search_space")
  return space if isinstance(space, dict) and space else None


def export_readiness(model: dict) -> dict[str, Any]:
  """UI helper: schedule weeks + whether Export .tmpkg can succeed."""
  mid = str(model.get("id") or "")
  try:
    _, schedule_weekly_count, validate_schedule_payload, _ = _import_package_format()
  except RuntimeError as exc:
    return {"ok": False, "weeks": 0, "kb_ok": False, "error": str(exc)}
  schedule = load_schedule(mid)
  sched_errs = validate_schedule_payload(schedule)
  weeks = 0 if sched_errs else schedule_weekly_count(schedule)
  use_kb = bool(model.get("use_kb", True))
  kb_ok = (not use_kb) or (resolve_kb_pin(model) is not None)
  space_ok = bool(resolve_mining_search_space(model))
  reasons: list[str] = []
  if sched_errs:
    reasons.append(f"thiếu schedule.json — chạy tab {LABEL_TAB_OOS} (OOS remine)")
  if use_kb and not kb_ok:
    reasons.append("thiếu kb_pin.json")
  if not space_ok:
    reasons.append("thiếu mining_search_space")
  return {
    "ok": not reasons,
    "weeks": weeks,
    "kb_ok": kb_ok,
    "error": "; ".join(reasons),
  }


def export_model_tmpkg(
  model: dict,
  *,
  out_dir: Path | None = None,
  label_override: str | None = None,
) -> dict[str, Any]:
  """Pack one live/archived model. Raises RuntimeError if schedule/KB missing."""
  build_manifest, schedule_weekly_count, validate_schedule_payload, write_package = (
    _import_package_format()
  )
  cfg = load_desk()
  symbol = str(cfg.get("symbol") or "EURUSD").upper()
  timeframe = str(cfg.get("tf") or "M15").upper()
  instance = str(cfg.get("instance_id") or cfg.get("id") or "desk")
  desk_id = str(cfg.get("id") or "")
  mid = str(model.get("id") or "unknown")
  raw_label = (label_override or model.get("label") or mid)
  label = f"{symbol} {timeframe} · {raw_label}"
  if str(raw_label).startswith(f"{symbol} {timeframe}"):
    label = str(raw_label)

  use_kb = bool(model.get("use_kb", True))
  kb_pin = resolve_kb_pin(model) if use_kb else None
  if use_kb and kb_pin is None:
    raise RuntimeError(
      f"{mid}: use_kb nhưng thiếu kb_pin.json — mở tab {LABEL_TAB_OOS} / tạo lại pin rồi export."
    )

  schedule = load_schedule(mid)
  sched_errs = validate_schedule_payload(schedule)
  if sched_errs:
    raise RuntimeError(
      f"{mid}: chưa có schedule.json (OOS weekly genomes).\n"
      f"{'; '.join(sched_errs)}\n"
      f"Chạy tab **{LABEL_TAB_OOS}** (OOS remine) cho model này rồi Export lại."
    )

  feature_profile = model.get("feature_profile") or (
    "m5_parity" if timeframe == "M5" else "current"
  )
  payload = {
    "id": mid,
    "label": label,
    "mining_search_space": resolve_mining_search_space(model),
    "train_weeks": model.get("train_weeks") or cfg.get("train_weeks") or 3,
    "use_kb": use_kb,
    "kb_profile": model.get("kb_profile"),
    "kb_snapshot": model.get("kb_snapshot"),
    "spread_pips": model.get("spread_pips") or cfg.get("spread_pips"),
    "slippage_pips": model.get("slippage_pips") or cfg.get("slippage_pips"),
    "max_trades_per_day": model.get("max_trades_per_day") or cfg.get("max_trades_per_day"),
    "feature_profile": feature_profile,
    "feature_schema": int(model.get("feature_schema") or 3),
    "data_source": model.get("data_source") or "mt5_ea",
    "data_timeframe": timeframe,
    "oos_from": model.get("oos_from"),
    "oos_to": model.get("oos_to"),
    "total_r": model.get("total_r"),
    "profit_factor": model.get("profit_factor"),
    "win_rate_pct": model.get("win_rate_pct"),
    "max_drawdown_r": model.get("max_drawdown_r"),
    "n_trades": model.get("n_trades"),
    "symbol": symbol,
    "timeframe": timeframe,
  }
  if not payload.get("mining_search_space"):
    raise RuntimeError(
      f"{mid}: thiếu mining_search_space — model chưa gắn không gian miner. "
      f"Chạy tab {LABEL_TAB_OOS} / remine rồi Export lại."
    )
  lab = {
    "desk": desk_id,
    "instance": instance,
    "repo_relative": f"TrainApp/runtime/{desk_id}",
    "train_app": True,
  }
  files = ["manifest.json", "model.json"]
  manifest = build_manifest(
    model=payload,
    lab=lab,
    symbol=symbol,
    timeframe=timeframe,
    files=files,
  )
  dest = Path(out_dir) if out_dir is not None else default_export_dir()
  dest.mkdir(parents=True, exist_ok=True)
  out_name = f"{instance}_{_slug(raw_label)}_{mid[-8:]}.tmpkg"
  try:
    path = write_package(
      dest / out_name,
      manifest=manifest,
      model=payload,
      metrics=metrics_from_model(model),
      kb_pin_src=kb_pin,
      schedule=schedule,
    )
  except ValueError as exc:
    raise RuntimeError(str(exc)) from exc
  return {
    "path": path,
    "weeks": schedule_weekly_count(schedule),
    "label": label,
    "model_id": mid,
    "inbox": dest,
  }
