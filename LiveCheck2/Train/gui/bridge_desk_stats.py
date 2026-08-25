"""Shared Live desk stats — today/week PnL, open trade, unrealized R."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any


def fmt_px(value) -> str:
  try:
    return f"{float(value):.5f}"
  except (TypeError, ValueError):
    return "—"


def unrealized_r(trade: dict, connection: dict) -> float | None:
  """Estimate open R from live bid/ask vs entry/SL."""
  try:
    entry = float(
      trade.get("entry_px") if trade.get("entry_px") is not None else trade.get("entry")
    )
    sl = float(trade["sl"])
  except (TypeError, ValueError, KeyError):
    return None
  risk = abs(entry - sl)
  if risk <= 0:
    return None
  direction = str(trade.get("direction") or trade.get("dir") or "").upper()
  bid, ask = connection.get("bid"), connection.get("ask")
  try:
    if direction in ("BUY", "LONG"):
      mark = float(bid)
      return round((mark - entry) / risk, 3)
    if direction in ("SELL", "SHORT"):
      mark = float(ask)
      return round((entry - mark) / risk, 3)
  except (TypeError, ValueError):
    return None
  return None


def open_trades(trades: list[dict], *, mode: str | None = "auto") -> list[dict]:
  from mt5_bridge.trade_journal import trade_mode

  out = []
  for t in trades or []:
    if str(t.get("status") or "").upper() != "OPEN":
      continue
    if mode is None or trade_mode(t) == mode:
      out.append(t)
  return out


def open_trade(trades: list[dict]) -> dict | None:
  opens = open_trades(trades, mode=None)
  return opens[-1] if opens else None


def count_open(trades: list[dict], *, mode: str | None = "auto") -> int:
  return len(open_trades(trades, mode=mode))


def journal_mt5_position_desync(
  *,
  journal_open_n: int,
  ea_positions: int | None,
  ea_online: bool,
  decision_reason: str | None = None,
) -> dict[str, Any] | None:
  """Detect Live journal↔MT5 desync that can freeze a model on HOLD forever.

  Same failure mode as Simulate sticky fill: journal says OPEN → engine
  ``reason=position_open`` → no new entries, even if MT5 is already flat.
  """
  if not ea_online or ea_positions is None:
    return None
  try:
    mt5_n = int(ea_positions)
  except (TypeError, ValueError):
    return None
  jn = int(journal_open_n or 0)
  reason = str(decision_reason or "").strip().lower()
  if jn > 0 and mt5_n == 0:
    return {
      "kind": "journal_ghost_open",
      "severity": True,
      "journal_open": jn,
      "mt5_positions": mt5_n,
      "message": (
        f"App đang nhớ {jn} lệnh mở nhưng trên MT5 không còn lệnh nào. "
        "Model sẽ không vào lệnh mới cho đến khi xóa lệnh treo trên App."
      ),
    }
  if jn == 0 and mt5_n > 0:
    return {
      "kind": "mt5_orphan_position",
      "fixable": False,
      "journal_open": jn,
      "mt5_positions": mt5_n,
      "message": (
        f"Trên MT5 còn {mt5_n} lệnh mở nhưng App không thấy — "
        "kiểm tra magic/roster; Bridge có thể mở thêm lệnh trùng."
      ),
    }
  if jn != mt5_n and jn > 0 and mt5_n > 0:
    return {
      "kind": "count_mismatch",
      "fixable": False,
      "journal_open": jn,
      "mt5_positions": mt5_n,
      "message": (
        f"Số lệnh mở lệch: App={jn} · MT5={mt5_n}. "
        "Mở MT5 Bridge để đối chiếu từng model."
      ),
    }
  if reason == "position_open" and mt5_n == 0:
    return {
      "kind": "hold_without_mt5",
      "fixable": True,
      "journal_open": jn,
      "mt5_positions": mt5_n,
      "message": (
        "App đang giữ trạng thái «đang có lệnh» trong khi MT5 trống — "
        "Bridge tự gỡ khi EA còn online; bấm «Xóa lệnh treo trên App» nếu desk vẫn kẹt."
      ),
    }

  return None


def period_stats(
  trades: list[dict],
  *,
  today: date | None = None,
  model_id: str | None = None,
) -> tuple[dict, dict]:
  """Desk PnL = Auto only (Trade Model). Manual-edited fills stay out."""
  from mt5_bridge.trade_journal import compute_stats, filter_trades

  today = today or date.today()
  week_from = today - timedelta(days=today.weekday())
  today_stats = compute_stats(
    filter_trades(trades, date_from=today, date_to=today, mode="auto", model_id=model_id),
  )
  week_stats = compute_stats(
    filter_trades(trades, date_from=week_from, date_to=today, mode="auto", model_id=model_id),
  )
  return today_stats, week_stats


def read_ea_sync(bridge_dir) -> dict[str, Any]:
  """Per-model EA↔App sync status from ea_sync.json (ForgeBridge v1.25+)."""
  from mt5_bridge.protocol import ea_sync_path, read_json

  bdir = Path(bridge_dir) if bridge_dir else None
  if bdir is None:
    return {}
  data = read_json(ea_sync_path(bdir)) or {}
  return data if isinstance(data, dict) else {}


def _ea_sync_models_by_id(ea_sync: dict) -> dict[str, dict]:
  out: dict[str, dict] = {}
  for row in ea_sync.get("models") or []:
    if isinstance(row, dict) and row.get("id"):
      out[str(row["id"])] = row
  return out


def _mt5_positions_by_model(
  mt5_rows: list[dict],
  *,
  roster_models: list[dict],
) -> dict[str, list[dict]]:
  magic_to_id = {
    int(r.get("magic")): str(r.get("id"))
    for r in roster_models
    if isinstance(r, dict) and r.get("magic") is not None and r.get("id")
  }
  out: dict[str, list[dict]] = {}
  for p in mt5_rows:
    mid = str(p.get("model_id") or "").strip()
    if not mid:
      try:
        mid = magic_to_id.get(int(p.get("magic")), "")
      except (TypeError, ValueError):
        mid = ""
    if not mid:
      mid = "_unknown"
    out.setdefault(mid, []).append(p)
  return out


def build_ea_app_sync_status(
  *,
  bridge_dir,
  connection: dict,
  health: dict,
  trades: list[dict],
  ea_sync: dict,
  model_ids: list[str],
  roster: dict,
  decision: dict | None = None,
  file_status: dict | None = None,
) -> dict[str, Any]:
  """Structured EA↔App sync for Live Trade Now (MT5/EA = source of truth)."""
  from mt5_bridge.trade_journal import read_ea_positions_snapshot, trade_mode

  ea_online = bool(health.get("online"))
  ea_summary = str(ea_sync.get("summary") or "").strip()
  ea_bar = str(ea_sync.get("bar_time") or "").strip()
  sync_timeout = "TIMEOUT" in ea_summary.upper()
  mt5_rows, mt5_n_file = read_ea_positions_snapshot(bridge_dir)
  roster_models = [r for r in (roster.get("models") or []) if isinstance(r, dict)]
  mt5_by_model = _mt5_positions_by_model(mt5_rows, roster_models=roster_models)
  ea_by_id = _ea_sync_models_by_id(ea_sync)

  try:
    ea_pos_n = int(connection.get("positions")) if connection.get("positions") is not None else None
  except (TypeError, ValueError):
    ea_pos_n = None
  if mt5_n_file is not None:
    ea_pos_n = mt5_n_file

  journal_all = open_trades(trades, mode=None)
  journal_auto = open_trades(trades, mode="auto")
  j_all_n = len(journal_all)
  j_auto_n = len(journal_auto)

  decision_reason = str(
    (decision or {}).get("reason") or (file_status or {}).get("reason") or ""
  ).strip().lower()

  issues: list[str] = []
  state = "offline"
  if ea_online:
    state = "ok"
  else:
    issues.append("EA offline — không đọc được heartbeat MT5.")

  if sync_timeout:
    state = "bad"
    issues.append(f"EA chờ App quá lâu: {ea_summary or 'TIMEOUT'}")

  per_model: list[dict[str, Any]] = []
  for mid in model_ids:
    j_opens = [t for t in journal_all if str(t.get("model_id") or "") == mid]
    m_mt5 = mt5_by_model.get(mid, [])
    ea_slot = ea_by_id.get(mid) or {}
    ea_st = str(ea_slot.get("status") or "").strip()
    ea_act = str(ea_slot.get("action") or "").strip()
    row_issues: list[str] = []
    row_state = "ok"
    if ea_st == "TIMEOUT":
      row_state = "bad"
      row_issues.append("TIMEOUT decision")
    elif ea_st and ea_st not in ("OK", "FLAT", "HOLD"):
      if ea_st in ("OPEN", "BUY", "SELL", "ENTERED"):
        row_state = "ok"
      else:
        row_state = "warn"
        row_issues.append(f"EA status {ea_st}")

    if len(j_opens) > 1:
      row_state = "bad"
      row_issues.append(f"App nhớ {len(j_opens)} lệnh mở (max 1/model)")
    if len(m_mt5) > 1:
      row_state = "bad"
      row_issues.append(f"MT5 có {len(m_mt5)} lệnh (max 1/model)")

    if ea_online and ea_pos_n is not None:
      if len(j_opens) == 0 and len(m_mt5) > 0:
        row_state = "warn"
        row_issues.append("MT5 có lệnh · App chưa có (Bridge sẽ import)")
      elif len(j_opens) > 0 and len(m_mt5) == 0:
        row_state = "bad"
        row_issues.append("App nhớ lệnh mở · MT5 trống")
      elif len(j_opens) == 1 and len(m_mt5) == 1:
        jt, mp = j_opens[0], m_mt5[0]
        for label, jkey, mkey in (
          ("entry", "entry_px", "price_open"),
          ("SL", "sl", "sl"),
          ("TP", "tp", "tp"),
        ):
          try:
            jv, mv = float(jt.get(jkey)), float(mp.get(mkey))
            if abs(jv - mv) > 1e-5:
              row_state = "warn" if row_state == "ok" else row_state
              row_issues.append(f"{label} App≠MT5 (MT5 đúng)")
          except (TypeError, ValueError):
            pass

    if row_state == "bad" and state != "bad":
      state = "warn"
    if row_state == "bad":
      state = "bad"

    per_model.append({
      "model_id": mid,
      "journal_open": len(j_opens),
      "mt5_open": len(m_mt5),
      "ea_status": ea_st or "—",
      "ea_action": ea_act or "—",
      "state": row_state,
      "issues": row_issues,
      "mt5_position": m_mt5[0] if len(m_mt5) == 1 else None,
      "journal_trade": j_opens[0] if len(j_opens) == 1 else None,
    })

  awaiting_n = sum(
    1 for t in trades
    if str(t.get("status") or "").upper() == "OPEN"
    and "awaiting_mt5_deal" in (t.get("interventions") or [])
  )
  if awaiting_n > 0:
    issues.append(
      f"{awaiting_n} lệnh OPEN chờ deal MT5 — App không đóng bừa (giống Trade)."
    )
    if state == "ok":
      state = "warn"

  desync = journal_mt5_position_desync(
    journal_open_n=j_all_n,
    ea_positions=ea_pos_n,
    ea_online=ea_online,
    decision_reason=decision_reason,
  )
  if desync:
    kind = str(desync.get("kind") or "")
    if kind in ("journal_ghost_open", "hold_without_mt5"):
      state = "bad" if state != "offline" else state
    elif kind == "mt5_orphan_position":
      state = "warn" if state == "ok" else state
    else:
      state = "warn" if state == "ok" else state
    issues.append(str(desync.get("message") or kind))

  positions_match = (
    ea_online
    and ea_pos_n is not None
    and j_all_n == int(ea_pos_n)
    and not desync
    and not sync_timeout
  )

  if ea_online and state == "ok" and not issues:
    headline = "Đồng bộ OK — App và MT5 khớp"
    if ea_summary:
      headline += f" · {ea_summary}"
  elif state == "offline":
    headline = "EA offline — chưa đồng bộ với MT5"
  elif state == "bad":
    headline = "Lệch đồng bộ — ưu tiên số liệu MT5 (EA)"
  else:
    headline = "Đồng bộ cần chú ý — kiểm tra chi tiết"

  detail_parts = []
  if ea_bar:
    detail_parts.append(f"Bar EA: {ea_bar}")
  if ea_pos_n is not None:
    detail_parts.append(f"MT5: {ea_pos_n} lệnh")
  detail_parts.append(f"App: {j_all_n} mở ({j_auto_n} auto)")
  if ea_summary and ea_summary not in headline:
    detail_parts.append(ea_summary)

  return {
    "state": state,
    "headline": headline,
    "detail": " · ".join(detail_parts),
    "ea_online": ea_online,
    "ea_summary": ea_summary or None,
    "ea_bar_time": ea_bar or None,
    "ea_sync_timeout": sync_timeout,
    "positions_match": positions_match,
    "journal_open_all": j_all_n,
    "journal_open_auto": j_auto_n,
    "mt5_positions": ea_pos_n,
    "mt5_rows": mt5_rows,
    "per_model": per_model,
    "issues": issues,
    "desync": desync,
    "fixable": bool(desync and desync.get("fixable")),
    "awaiting_deal": awaiting_n,
  }


def snapshot_live_desk(
  *,
  bridge_dir=None,
  today: date | None = None,
  model_ids: list[str] | None = None,
) -> dict[str, Any]:
  """One-shot Live desk snapshot for dashboard (no Streamlit)."""
  from mt5_bridge import background as bridge_bg
  from mt5_bridge.protocol import (
    connection_path,
    decision_path,
    normalize_model_ids,
    read_json,
    read_models_roster,
    resolve_live_bridge_dir,
    status_path,
  )
  from mt5_bridge.trade_journal import load_trades, restore_false_manual_edits, trade_mode
  from gui.mt5_live_chart import connection_health

  bdir = bridge_dir or resolve_live_bridge_dir()
  today = today or date.today()
  restore_false_manual_edits(bdir)
  connection = read_json(connection_path(bdir)) or {}
  decision = read_json(decision_path(bdir)) or {}
  file_status = read_json(status_path(bdir)) or {}
  service_status = bridge_bg.get_status()
  trades = load_trades(bdir)
  health = connection_health(connection, stale_after_seconds=10.0, bridge_dir=bdir)
  today_stats, week_stats = period_stats(trades, today=today)

  cfg = bridge_bg.load_config()
  roster = read_models_roster(bdir)
  roster_ids = [
    str(r.get("id"))
    for r in (roster.get("models") or [])
    if isinstance(r, dict) and r.get("id")
  ]
  ids = normalize_model_ids(
    model_ids if model_ids is not None else (cfg.get("model_ids") or roster_ids),
    fallback=cfg.get("model_id") or decision.get("model_id"),
  )
  per_model = []
  for mid in ids:
    t_stats, w_stats = period_stats(trades, today=today, model_id=mid)
    opens = [t for t in open_trades(trades, mode="auto") if str(t.get("model_id") or "") == mid]
    ot = opens[-1] if opens else None
    slot = (file_status.get("per_model") or {}).get(mid) or {}
    per_model.append({
      "model_id": mid,
      "today_stats": t_stats,
      "week_stats": w_stats,
      "open_trade": ot,
      "unrealized_r": unrealized_r(ot, connection) if ot else None,
      "open_count": len(opens),
      "last_action": slot.get("action"),
      "signal_wait": slot.get("signal_wait"),
      "magic": next(
        (r.get("magic") for r in (roster.get("models") or [])
         if isinstance(r, dict) and str(r.get("id")) == mid),
        None,
      ),
    })

  opens_all = open_trades(trades, mode="auto")
  ot = opens_all[-1] if opens_all else open_trade(trades)
  ur = unrealized_r(ot, connection) if ot else None
  open_auto = count_open(trades, mode="auto")
  open_manual = sum(
    1 for t in trades
    if str(t.get("status") or "").upper() == "OPEN" and trade_mode(t) != "auto"
  )
  ea_pos = connection.get("positions")
  try:
    ea_pos_n = int(ea_pos) if ea_pos is not None else None
  except (TypeError, ValueError):
    ea_pos_n = None
  open_all = count_open(trades, mode=None)
  ea_sync = read_ea_sync(bdir)
  sync_status = build_ea_app_sync_status(
    bridge_dir=bdir,
    connection=connection,
    health=health,
    trades=trades,
    ea_sync=ea_sync,
    model_ids=ids,
    roster=roster,
    decision=decision,
    file_status=file_status,
  )
  desync = sync_status.get("desync")
  sync_summary = sync_status.get("ea_summary") or ""
  sync_timeout = bool(sync_status.get("ea_sync_timeout"))
  ea_pos_n = sync_status.get("mt5_positions", ea_pos_n)
  return {
    "connection": connection,
    "decision": decision,
    "file_status": file_status,
    "service_status": service_status,
    "trades": trades,
    "health": health,
    "today_stats": today_stats,
    "week_stats": week_stats,
    "open_trade": ot,
    "open_trades": opens_all,
    "unrealized_r": ur,
    "open_auto": open_auto,
    "open_manual": open_manual,
    "model_ids": ids,
    "per_model": per_model,
    "today": today,
    "ea_positions": ea_pos_n,
    "journal_mt5_desync": desync,
    "ea_sync": ea_sync,
    "ea_sync_summary": sync_summary or None,
    "ea_sync_timeout": sync_timeout,
    "sync_status": sync_status,
  }
