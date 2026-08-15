"""Concurrent risk cap — limit total open risk across all Live models.

Per-model already allows only one open trade. This caps *portfolio* exposure:
sum(risk_pct of OPEN + pending SIGNAL) must stay under prefs.

Prefs: ``live/results/risk_cap_prefs.json``
Alerts: ``live/results/risk_cap_alerts.jsonl`` + ``risk_cap_last.json``
Disable: env ``LIVE_RISK_CAP=0``
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from live_config import MT5_ROOT, RESULTS_DIR

PREFS_PATH = RESULTS_DIR / "risk_cap_prefs.json"
ALERTS_PATH = RESULTS_DIR / "risk_cap_alerts.jsonl"
LAST_PATH = RESULTS_DIR / "risk_cap_last.json"
LOCK_PATH = RESULTS_DIR / "risk_cap.lock"
RESERVE_DIR = RESULTS_DIR / "risk_cap_reservations"

DEFAULT_PREFS: dict[str, Any] = {
  "enabled": True,
  # Total risk_pct of open + pending signals across all books
  "max_open_risk_pct": 3.0,
  # Max concurrent OPEN positions (all models)
  "max_open_positions": 4,
  # Count fresh BUY/SELL decisions without OPEN yet as reserved risk
  "include_pending_signals": True,
  # Ignore pending decisions older than this many seconds
  "pending_max_age_sec": 900,
  # Cross-worker reservation TTL (closes race before decision.json is written)
  "reservation_ttl_sec": 120,
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


def cap_enabled() -> bool:
  env = os.environ.get("LIVE_RISK_CAP", "").strip().lower()
  if env in ("0", "false", "no", "off"):
    return False
  if env in ("1", "true", "yes", "on"):
    return True
  return bool(load_prefs().get("enabled", True))


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


def _roster_risk_map() -> dict[str, float]:
  try:
    from package_store import load_roster
    roster = load_roster()
  except Exception:
    return {}
  out: dict[str, float] = {}
  for r in roster.get("models") or []:
    mid = str(r.get("model_id") or "")
    if not mid:
      continue
    try:
      out[mid] = float(r.get("risk_pct") or 1.0)
    except (TypeError, ValueError):
      out[mid] = 1.0
  return out


def _iter_bridge_dirs(*, sim: bool) -> list[Path]:
  dirs: list[Path] = []
  seen: set[str] = set()
  try:
    from books import bridge_dir, group_models_by_book
    from package_store import load_roster
    enabled = [r for r in (load_roster().get("models") or []) if r.get("enabled")]
    for (sym, tf), _ in group_models_by_book(enabled).items():
      p = bridge_dir(sym, tf, sim=sim)
      key = str(p)
      if key not in seen:
        dirs.append(p)
        seen.add(key)
  except Exception:
    pass
  # Also scan on-disk bridge folders (workers may exist beyond roster parse)
  prefix = "bridge_sim_live_" if sim else "bridge_live_"
  try:
    if MT5_ROOT.is_dir():
      for p in MT5_ROOT.iterdir():
        if p.is_dir() and p.name.startswith(prefix) and str(p) not in seen:
          dirs.append(p)
          seen.add(str(p))
  except OSError:
    pass
  return dirs


def _parse_age_sec(updated_at: Any) -> float | None:
  if not updated_at:
    return None
  try:
    ts = datetime.fromisoformat(str(updated_at).replace("Z", "+00:00"))
    if ts.tzinfo is None:
      ts = ts.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - ts.astimezone(timezone.utc)).total_seconds())
  except Exception:
    return None


def _load_decisions(bdir: Path) -> list[dict]:
  rows: list[dict] = []
  primary = _read(bdir / "decision.json")
  if isinstance(primary, dict):
    rows.append(primary)
  dec_dir = bdir / "decisions"
  if dec_dir.is_dir():
    for p in dec_dir.glob("*.json"):
      d = _read(p)
      if isinstance(d, dict):
        rows.append(d)
  # de-dupe by model_id (prefer decisions/ over primary mirror)
  by_mid: dict[str, dict] = {}
  for d in rows:
    mid = str(d.get("model_id") or "")
    if not mid:
      continue
    by_mid[mid] = d
  return list(by_mid.values())


def _load_reservations(prefs: dict[str, Any]) -> list[dict]:
  """Active cross-worker SIGNAL reservations (sim + live share one dir; filtered by sim tag)."""
  out: list[dict] = []
  if not RESERVE_DIR.is_dir():
    return out
  ttl = float(prefs.get("reservation_ttl_sec") or 120)
  for p in RESERVE_DIR.glob("*.json"):
    d = _read(p)
    if not isinstance(d, dict):
      continue
    age = _parse_age_sec(d.get("updated_at"))
    if age is not None and age > ttl:
      try:
        p.unlink(missing_ok=True)  # type: ignore[call-arg]
      except TypeError:
        try:
          if p.exists():
            p.unlink()
        except OSError:
          pass
      except OSError:
        pass
      continue
    out.append(d)
  return out


def _reserve_signal(*, model_id: str, risk_pct: float, sim: bool, action: str) -> None:
  mid = str(model_id or "").strip() or "_unknown"
  RESERVE_DIR.mkdir(parents=True, exist_ok=True)
  safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in mid)[:80]
  tag = "sim" if sim else "live"
  _write(RESERVE_DIR / f"{tag}_{safe}.json", {
    "model_id": mid,
    "risk_pct": float(risk_pct),
    "action": action,
    "sim": bool(sim),
    "updated_at": _now(),
  })


def collect_exposure(*, sim: bool = False, prefs: dict[str, Any] | None = None) -> dict[str, Any]:
  """Sum open + pending risk across all books."""
  prefs = prefs or load_prefs()
  risk_map = _roster_risk_map()
  opens: list[dict] = []
  pending: list[dict] = []
  open_mids: set[str] = set()
  pending_mids: set[str] = set()

  for bdir in _iter_bridge_dirs(sim=sim):
    trades_path = bdir / "trades.json"
    trades = _read(trades_path)
    if isinstance(trades, dict):
      trade_rows = trades.get("trades") or trades.get("rows") or []
    elif isinstance(trades, list):
      trade_rows = trades
    else:
      trade_rows = []
    # Also try desk journal loader if available
    if not trade_rows:
      try:
        from mt5_bridge.trade_journal import load_trades
        trade_rows = load_trades(bdir) or []
      except Exception:
        trade_rows = []

    for t in trade_rows:
      st = str(t.get("status") or "").upper()
      if st == "CLOSED" or t.get("exit") is not None:
        continue
      if st and st not in ("OPEN", ""):
        # unknown status — skip unless looks open
        if st not in ("OPEN", "PENDING"):
          continue
      mid = str(t.get("model_id") or "")
      risk = risk_map.get(mid)
      if risk is None:
        try:
          risk = float(t.get("risk_pct") or 1.0)
        except (TypeError, ValueError):
          risk = 1.0
      opens.append({
        "model_id": mid,
        "risk_pct": float(risk),
        "bridge_dir": str(bdir),
        "magic": t.get("magic"),
      })
      if mid:
        open_mids.add(mid)

    if not prefs.get("include_pending_signals", True):
      continue
    max_age = float(prefs.get("pending_max_age_sec") or 900)
    for d in _load_decisions(bdir):
      action = str(d.get("action") or "").upper()
      if action not in ("BUY", "SELL"):
        continue
      mid = str(d.get("model_id") or "")
      if mid and mid in open_mids:
        continue  # already counted as open
      age = _parse_age_sec(d.get("updated_at"))
      if age is not None and age > max_age:
        continue
      risk = risk_map.get(mid)
      if risk is None:
        try:
          risk = float(d.get("risk_pct") or 1.0)
        except (TypeError, ValueError):
          risk = 1.0
      pending.append({
        "model_id": mid,
        "risk_pct": float(risk),
        "action": action,
        "bridge_dir": str(bdir),
        "age_sec": age,
        "source": "decision",
      })
      if mid:
        pending_mids.add(mid)

  # Cross-worker reservations (before decision.json lands)
  if prefs.get("include_pending_signals", True):
    for d in _load_reservations(prefs):
      if bool(d.get("sim")) != bool(sim):
        continue
      mid = str(d.get("model_id") or "")
      if mid and (mid in open_mids or mid in pending_mids):
        continue
      try:
        risk = float(d.get("risk_pct") or risk_map.get(mid) or 1.0)
      except (TypeError, ValueError):
        risk = 1.0
      pending.append({
        "model_id": mid,
        "risk_pct": float(risk),
        "action": str(d.get("action") or "BUY").upper(),
        "bridge_dir": "reservation",
        "age_sec": _parse_age_sec(d.get("updated_at")),
        "source": "reservation",
      })
      if mid:
        pending_mids.add(mid)

  open_risk = sum(float(x["risk_pct"]) for x in opens)
  pending_risk = sum(float(x["risk_pct"]) for x in pending)
  return {
    "open": opens,
    "pending": pending,
    "n_open": len(opens),
    "n_pending": len(pending),
    "open_risk_pct": round(open_risk, 3),
    "pending_risk_pct": round(pending_risk, 3),
    "total_risk_pct": round(open_risk + pending_risk, 3),
    "open_model_ids": sorted(open_mids),
  }


def check_signal_allowed(
  *,
  model_id: str,
  risk_pct: float,
  sim: bool = False,
  prefs: dict[str, Any] | None = None,
  exposure: dict[str, Any] | None = None,
) -> dict[str, Any]:
  """Would adding this model's new SIGNAL breach the cap?"""
  prefs = prefs or load_prefs()
  exp = exposure if exposure is not None else collect_exposure(sim=sim, prefs=prefs)
  mid = str(model_id or "")
  add = float(risk_pct or 1.0)
  reasons: list[str] = []

  # If this model already has an open, engine should HOLD — still safe-check
  if mid and mid in set(exp.get("open_model_ids") or []):
    return {
      "ok": True,
      "skipped": True,
      "reasons": [],
      "exposure": exp,
      "projected_risk_pct": exp.get("total_risk_pct"),
      "add_risk_pct": 0.0,
    }

  # Exclude this model's own pending signal from baseline (we're replacing it)
  base_risk = float(exp.get("total_risk_pct") or 0.0)
  for p in exp.get("pending") or []:
    if str(p.get("model_id") or "") == mid:
      base_risk = max(0.0, base_risk - float(p.get("risk_pct") or 0.0))

  projected = base_risk + add
  max_risk = float(prefs.get("max_open_risk_pct") or 0.0)
  max_pos = int(prefs.get("max_open_positions") or 0)

  if max_risk > 0 and projected > max_risk + 1e-9:
    reasons.append(
      f"projected_risk {projected:.2f}% > max_open_risk_pct {max_risk:.2f}% "
      f"(open={exp.get('open_risk_pct')} pending={exp.get('pending_risk_pct')} +{add})"
    )
  # positions: opens + other pending + this new signal
  other_pending = sum(
    1 for p in (exp.get("pending") or []) if str(p.get("model_id") or "") != mid
  )
  projected_pos = int(exp.get("n_open") or 0) + other_pending + 1
  if max_pos > 0 and projected_pos > max_pos:
    reasons.append(
      f"projected_positions {projected_pos} > max_open_positions {max_pos} "
      f"(open={exp.get('n_open')} pending_others={other_pending})"
    )

  return {
    "ok": not reasons,
    "reasons": reasons,
    "exposure": exp,
    "projected_risk_pct": round(projected, 3),
    "projected_positions": projected_pos,
    "add_risk_pct": add,
    "prefs": {
      "max_open_risk_pct": max_risk,
      "max_open_positions": max_pos,
    },
  }


def emit_risk_cap_alert(payload: dict[str, Any]) -> dict[str, Any]:
  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  row = {**payload, "updated_at": _now()}
  try:
    with ALERTS_PATH.open("a", encoding="utf-8") as f:
      f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
  except OSError:
    pass
  _write(LAST_PATH, row)
  print(
    f"[risk_cap] {'PASS' if row.get('ok') else 'BLOCK'} model={row.get('model_id')} "
    f"proj={row.get('projected_risk_pct')} reasons={row.get('reasons') or []}",
    flush=True,
  )
  return row


def load_last_alert() -> dict[str, Any]:
  return _read(LAST_PATH) or {}


def apply_risk_cap_to_decision(
  decision: dict[str, Any],
  *,
  sim: bool = False,
  risk_pct: float | None = None,
) -> dict[str, Any]:
  """If decision is BUY/SELL and would breach cap → convert to FLAT risk_cap."""
  if not isinstance(decision, dict):
    return decision
  if not cap_enabled():
    return decision
  action = str(decision.get("action") or "").upper()
  if action not in ("BUY", "SELL"):
    return decision

  mid = str(decision.get("model_id") or "")
  if risk_pct is None:
    try:
      risk_pct = float(decision.get("risk_pct") or _roster_risk_map().get(mid) or 1.0)
    except (TypeError, ValueError):
      risk_pct = 1.0

  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  from file_lock import interprocess_lock

  with interprocess_lock(LOCK_PATH, timeout_sec=10.0):
    check = check_signal_allowed(
      model_id=mid, risk_pct=float(risk_pct), sim=sim,
    )
    if check.get("ok"):
      if not check.get("skipped"):
        _reserve_signal(
          model_id=mid, risk_pct=float(risk_pct), sim=sim, action=action,
        )
      out = dict(decision)
      out["risk_cap_ok"] = True
      out["risk_cap_projected_risk_pct"] = check.get("projected_risk_pct")
      return out
    emit_risk_cap_alert({
      "ok": False,
      "event": "risk_cap_block",
      "model_id": mid,
      "action": action,
      "reasons": check.get("reasons"),
      "projected_risk_pct": check.get("projected_risk_pct"),
      "projected_positions": check.get("projected_positions"),
      "exposure": {
        "n_open": (check.get("exposure") or {}).get("n_open"),
        "n_pending": (check.get("exposure") or {}).get("n_pending"),
        "open_risk_pct": (check.get("exposure") or {}).get("open_risk_pct"),
        "pending_risk_pct": (check.get("exposure") or {}).get("pending_risk_pct"),
        "total_risk_pct": (check.get("exposure") or {}).get("total_risk_pct"),
      },
      "prefs": check.get("prefs"),
    })
    blocked = dict(decision)
    blocked["action"] = "FLAT"
    blocked["reason"] = "risk_cap"
    blocked["risk_cap_ok"] = False
    blocked["risk_cap_reasons"] = check.get("reasons")
    blocked["risk_cap_projected_risk_pct"] = check.get("projected_risk_pct")
    blocked.pop("entry", None)
    blocked.pop("sl", None)
    blocked.pop("tp", None)
    return blocked