"""Manual 'Remine this week' IPC — GUI writes a request; Live worker mines.

Does not wait for Sunday open. Replaces the current broker week's genome in
``live_weeks`` (``forced=True`` so it wins over OOS schedule).
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from mt5_bridge.protocol import atomic_write_json, ensure_bridge_dir, read_json, utc_now_iso

REMINE_REQUEST_NAME = "remine_request.json"
REMINE_STATUS_NAME = "remine_status.json"


def remine_request_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / REMINE_REQUEST_NAME


def remine_status_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / REMINE_STATUS_NAME


def request_live_remine(
  bridge_dir: Path | None = None,
  *,
  model_ids: list[str] | None = None,
  week_start: str | None = None,
  reason: str = "manual_ui",
) -> dict[str, Any]:
  """Ask the Live worker to remine the current (or given) broker week."""
  payload: dict[str, Any] = {
    "requested_at": time.time(),
    "requested_iso": utc_now_iso(),
    "reason": str(reason or "manual_ui"),
  }
  ids = [str(x) for x in (model_ids or []) if x]
  if ids:
    payload["model_ids"] = ids
  if week_start:
    payload["week_start"] = str(week_start)[:10]
  atomic_write_json(remine_request_path(bridge_dir), payload)
  write_remine_status(
    bridge_dir,
    state="queued",
    week_start=payload.get("week_start"),
    model_ids=ids or None,
    message="Chờ Bridge nhận yêu cầu remine.",
  )
  return payload


def consume_live_remine(bridge_dir: Path | None = None) -> dict[str, Any] | None:
  path = remine_request_path(bridge_dir)
  if not path.exists():
    return None
  data = read_json(path)
  try:
    path.unlink()
  except OSError:
    pass
  return data if isinstance(data, dict) else {"reason": "manual_ui"}


def read_remine_status(bridge_dir: Path | None = None) -> dict[str, Any]:
  data = read_json(remine_status_path(bridge_dir))
  return data if isinstance(data, dict) else {}


def write_remine_status(
  bridge_dir: Path | None = None,
  *,
  state: str,
  week_start: str | None = None,
  model_ids: list[str] | None = None,
  current_model: str | None = None,
  results: list[dict[str, Any]] | None = None,
  message: str | None = None,
  error: str | None = None,
) -> None:
  payload: dict[str, Any] = {
    "state": str(state),
    "updated_at": utc_now_iso(),
  }
  if week_start:
    payload["week_start"] = str(week_start)[:10]
  if model_ids:
    payload["model_ids"] = list(model_ids)
  if current_model:
    payload["current_model"] = current_model
  if results is not None:
    payload["results"] = results
  if message:
    payload["message"] = message
  if error:
    payload["error"] = error
  atomic_write_json(remine_status_path(bridge_dir), payload)


def apply_manual_remine_request(engines: dict, bridge_dir: Path | None = None) -> bool:
  """Consume a pending request and remine matching engines. Returns True if ran."""
  req = consume_live_remine(bridge_dir)
  if not req:
    return False

  from mt5_bridge.comm_log import append_event

  ids = [str(x) for x in (req.get("model_ids") or []) if x]
  if not ids:
    ids = [str(k) for k in (engines or {})]
  week_raw = req.get("week_start")
  week_ts = None
  if week_raw:
    import pandas as pd
    week_ts = pd.Timestamp(str(week_raw)[:10])

  write_remine_status(
    bridge_dir,
    state="running",
    week_start=str(week_raw)[:10] if week_raw else None,
    model_ids=ids,
    message=f"Đang remine {len(ids)} model…",
  )
  append_event(
    "system",
    "manual_remine_start",
    bridge_dir=bridge_dir,
    summary=f"n={len(ids)} week={week_raw or 'current'}",
    payload={"model_ids": ids, "week_start": week_raw},
  )

  results: list[dict[str, Any]] = []
  week_used = str(week_raw)[:10] if week_raw else None
  for mid in ids:
    eng = (engines or {}).get(mid)
    if eng is None:
      results.append({"model_id": mid, "ok": False, "error": "not_in_roster"})
      continue
    write_remine_status(
      bridge_dir,
      state="running",
      week_start=week_used,
      model_ids=ids,
      current_model=mid,
      results=results,
      message=f"Đang remine {mid}…",
    )
    try:
      out = eng.force_remine_week(week_ts)
      row = {"model_id": mid, **(out or {})}
      if row.get("week_start"):
        week_used = str(row["week_start"])[:10]
      results.append(row)
    except Exception as exc:
      results.append({"model_id": mid, "ok": False, "error": str(exc)[:300]})

  n_ok = sum(1 for r in results if r.get("ok"))
  failed = [r for r in results if not r.get("ok")]
  state = "done" if n_ok == len(results) else ("error" if n_ok == 0 else "done")
  write_remine_status(
    bridge_dir,
    state=state,
    week_start=week_used,
    model_ids=ids,
    results=results,
    message=f"Xong {n_ok}/{len(results)} model.",
    error=("; ".join(str(r.get("error") or r["model_id"]) for r in failed)[:400] if failed else None),
  )
  append_event(
    "system",
    "manual_remine_done",
    bridge_dir=bridge_dir,
    summary=f"ok={n_ok}/{len(results)} week={week_used}",
    payload={"results": results},
  )
  try:
    from mt5_bridge.trade_journal import request_live_redecide
    request_live_redecide(bridge_dir)
  except Exception:
    pass
  return True
