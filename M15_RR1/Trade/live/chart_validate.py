"""Validate MT5 chart (connection/bar) vs enabled package symbol+TF."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from live_config import BRIDGE_DIR, BRIDGE_SIM_DIR
from materialize_models import assert_homogeneous_roster, enabled_roster_rows
from runtime_host import normalize_symbol, normalize_timeframe


def _read_json(path: Path) -> Any:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def period_from_ea(raw: str | None) -> str | None:
  if raw is None:
    return None
  s = str(raw).strip().upper()
  if s.startswith("PERIOD_"):
    s = s.replace("PERIOD_", "")
  return normalize_timeframe(s)


def read_chart_identity(bridge_dir: Path | None = None) -> dict[str, Any]:
  """Best-effort symbol/period from connection.json or bar.json."""
  bdir = Path(bridge_dir or BRIDGE_DIR)
  out: dict[str, Any] = {
    "bridge_dir": str(bdir),
    "symbol": None,
    "timeframe": None,
    "source": None,
    "connected": False,
    "raw": None,
  }
  for name in ("connection.json", "bar.json", "heartbeat.json"):
    data = _read_json(bdir / name)
    if not isinstance(data, dict):
      continue
    sym = data.get("symbol")
    period = data.get("period") or data.get("timeframe") or data.get("tf")
    if sym or period:
      out["symbol"] = normalize_symbol(sym) if sym else out["symbol"]
      out["timeframe"] = period_from_ea(period) if period else out["timeframe"]
      out["source"] = name
      out["raw"] = {k: data.get(k) for k in ("symbol", "period", "timeframe", "server", "account") if k in data}
    if name == "connection.json":
      out["connected"] = bool(data.get("connected", True))
      if data.get("ok") is False:
        out["connected"] = False
  return out


def validate_chart_vs_roster(
  *,
  bridge_dir: Path | None = None,
  roster_rows: list[dict] | None = None,
  require_ea_online: bool = False,
) -> dict[str, Any]:
  """Return {ok, errors, warnings, expected, chart}."""
  rows = roster_rows if roster_rows is not None else enabled_roster_rows()
  errors: list[str] = []
  warnings: list[str] = []
  expected = None
  try:
    symbol, timeframe = assert_homogeneous_roster(rows)
    expected = {"symbol": symbol, "timeframe": timeframe}
  except ValueError as exc:
    errors.append(str(exc))

  chart = read_chart_identity(bridge_dir)
  if expected and chart.get("symbol") and chart["symbol"] != expected["symbol"]:
    errors.append(
      f"Chart symbol {chart['symbol']} ≠ package {expected['symbol']} "
      f"(from {chart.get('source')})"
    )
  if expected and chart.get("timeframe") and chart["timeframe"] != expected["timeframe"]:
    errors.append(
      f"Chart TF {chart['timeframe']} ≠ package {expected['timeframe']} "
      f"(from {chart.get('source')})"
    )
  if not chart.get("symbol") and not chart.get("timeframe"):
    msg = (
      f"No connection/bar yet under {chart.get('bridge_dir')} — "
      "attach ForgeBridgeLive to the package chart before live trading."
    )
    if require_ea_online:
      errors.append(msg)
    else:
      warnings.append(msg)
  elif require_ea_online and not chart.get("connected") and chart.get("source") == "connection.json":
    warnings.append("connection.json present but connected=false")

  return {
    "ok": not errors,
    "errors": errors,
    "warnings": warnings,
    "expected": expected,
    "chart": chart,
  }


def validate_both_bridges(**kwargs) -> dict[str, Any]:
  live = validate_chart_vs_roster(bridge_dir=BRIDGE_DIR, **kwargs)
  sim = validate_chart_vs_roster(bridge_dir=BRIDGE_SIM_DIR, **kwargs)
  return {"live": live, "sim": sim}
