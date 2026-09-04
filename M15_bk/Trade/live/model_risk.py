"""Per-model risk_pct helpers for Live bridge roster + engines (BUG-01)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def risk_by_id_from_rows(rows: list[dict] | None) -> dict[str, float]:
  out: dict[str, float] = {}
  for r in rows or []:
    mid = str(r.get("model_id") or r.get("id") or "")
    if not mid:
      continue
    try:
      out[mid] = float(r.get("risk_pct") or 1.0)
    except (TypeError, ValueError):
      out[mid] = 1.0
  return out


def risk_by_id_from_live_roster(*, symbol: str | None = None, timeframe: str | None = None) -> dict[str, float]:
  """Read enabled models' risk_pct from live_roster.json (optionally one book)."""
  try:
    from package_store import load_roster
    from runtime_host import normalize_symbol, normalize_timeframe
  except Exception:
    return {}
  rows = [r for r in (load_roster().get("models") or []) if r.get("enabled")]
  if symbol and timeframe:
    sym = normalize_symbol(symbol)
    tf = normalize_timeframe(timeframe)
    rows = [
      r for r in rows
      if normalize_symbol(r.get("symbol")) == sym
      and normalize_timeframe(r.get("timeframe")) == tf
    ]
  return risk_by_id_from_rows(rows)


def apply_per_model_risk_to_bridge(
  bridge_dir: Path | str,
  *,
  risk_by_id: dict[str, float] | None = None,
) -> dict[str, float]:
  """Write per-model risk_pct into models.json; preserve magic/label/id.

  Returns the effective risk map applied (model_id → risk_pct).
  """
  bdir = Path(bridge_dir)
  path = bdir / "models.json"
  if not path.exists():
    return dict(risk_by_id or {})
  try:
    data = json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return dict(risk_by_id or {})
  if not isinstance(data, dict):
    return dict(risk_by_id or {})

  risk_map = dict(risk_by_id or {})
  models_out: list[dict[str, Any]] = []
  applied: dict[str, float] = {}
  for m in data.get("models") or []:
    if not isinstance(m, dict):
      continue
    mid = str(m.get("id") or "")
    if not mid:
      continue
    try:
      fallback = float(m.get("risk_pct") or data.get("risk_pct") or 1.0)
    except (TypeError, ValueError):
      fallback = 1.0
    try:
      rp = float(risk_map.get(mid, fallback) or fallback)
    except (TypeError, ValueError):
      rp = fallback
    if rp <= 0:
      rp = 1.0
    row = dict(m)
    row["risk_pct"] = rp
    models_out.append(row)
    applied[mid] = rp

  top = 1.0
  if models_out:
    try:
      top = float(models_out[0].get("risk_pct") or 1.0)
    except (TypeError, ValueError):
      top = 1.0
  data["models"] = models_out
  data["risk_pct"] = top
  bdir.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + ".tmp")
  tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  tmp.replace(path)
  return applied


def apply_per_model_risk_to_engines(
  engines: dict[str, Any],
  risk_by_id: dict[str, float],
) -> None:
  """Stamp each BridgeEngine.risk_pct from the Live roster map."""
  for mid, eng in (engines or {}).items():
    if mid not in risk_by_id:
      continue
    try:
      rp = float(risk_by_id[mid])
    except (TypeError, ValueError):
      continue
    if rp > 0:
      eng.risk_pct = rp


def build_engines_with_per_model_risk(
  build_engines_fn,
  model_ids: list[str],
  *,
  risk_pct: float,
  bridge_dir: Path,
  base_magic: int,
  existing_engines: dict[str, Any] | None = None,
  risk_by_id: dict[str, float] | None = None,
  symbol: str | None = None,
  timeframe: str | None = None,
) -> dict[str, Any]:
  """Host build_engines then restore per-model risk on engines + models.json."""
  engines = build_engines_fn(
    model_ids,
    risk_pct=float(risk_pct),
    bridge_dir=bridge_dir,
    base_magic=int(base_magic),
    existing_engines=existing_engines,
  )
  risk_map = dict(risk_by_id or {})
  if not risk_map:
    risk_map = risk_by_id_from_live_roster(symbol=symbol, timeframe=timeframe)
  if risk_map:
    apply_per_model_risk_to_engines(engines, risk_map)
    apply_per_model_risk_to_bridge(bridge_dir, risk_by_id=risk_map)
  return engines
