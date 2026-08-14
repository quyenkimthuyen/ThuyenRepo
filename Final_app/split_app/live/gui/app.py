"""EdgeMiner Live — trader desk UI (daily ops first, config second)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import streamlit as st

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))

from bridge_control import start_bridge, status, stop_bridge  # noqa: E402
from desk_snapshot import desk_snapshot  # noqa: E402
from live_config import BRIDGE_DIR, INBOX_DIR  # noqa: E402
from journal_view import (  # noqa: E402
  load_recent_fills,
  load_trades_many,
  journal_summary_many,
  stats_by_model_many,
  PERIOD_LABELS,
  PERIODS,
)
from magic_allocator import assign_magics  # noqa: E402
from package_store import (  # noqa: E402
  default_roster_from_installed,
  delete_installed,
  list_installed,
  load_roster,
  save_roster,
)
from books import bridge_subdir, group_models_by_book  # noqa: E402
from replay_control import (  # noqa: E402
  load_oos_prefs,
  save_oos_prefs,
  start_oos_replay,
  stop_replay,
)
from safety import (  # noqa: E402
  arm_kill_switch,
  disarm_kill_switch,
  is_kill_switch_armed,
  write_flatten_command,
)
from reset_data import reset_live_data  # noqa: E402
from equity_view import render_equity_section  # noqa: E402
from replay_history import (  # noqa: E402
  latest_parity_snapshot,
  list_replay_runs,
  load_replay_run,
  reset_replay_history,
)
from risk_prefs import (  # noqa: E402
  clear_loss_guard_trip,
  load_risk_prefs,
  risk_status_snapshot,
  save_risk_prefs,
)
from shared.constants import LIVE_APP_PORT, LIVE_INSTANCE_ID, LIVE_MAGIC_BASE  # noqa: E402
from theme import (  # noqa: E402
  inject_theme,
  pill,
  r_class,
  signal_badge,
)

st.set_page_config(
  page_title="EdgeMiner Live",
  layout="wide",
  initial_sidebar_state="collapsed",
)
inject_theme()

if "desk_mode" not in st.session_state:
  st.session_state.desk_mode = "Live"


def _model_label_map(models: list[dict]) -> dict[str, str]:
  out: dict[str, str] = {}
  for m in models:
    mid = str(m.get("model_id") or "")
    if mid:
      out[mid] = str(m.get("label") or mid)
  return out


def _render_replay_progress(replay: dict, models: list[dict]) -> None:
  """Show replay status model-first (parity rows or market groups)."""
  books = replay.get("books") or []
  labels = _model_label_map(models)
  if not books:
    return

  # Prefer per-model parity results when present
  model_rows = []
  for b in books:
    for pm in b.get("parity_models") or []:
      mid = str(pm.get("id") or pm.get("model_id") or "")
      model_rows.append({
        "label": labels.get(mid) or mid or "—",
        "market": f"{b.get('symbol')} {b.get('timeframe')}",
        "status": b.get("ea_status") or "done",
        "R": pm.get("R"),
        "lab_R": pm.get("lab_R"),
        "dR": pm.get("dR"),
        "pct": 100.0 if b.get("ea_status") == "completed" or b.get("pct") else (b.get("pct") or 0),
      })
  if model_rows:
    for row in model_rows:
      dr = row.get("dR")
      dr_s = f"ΔR {dr:+.2f}" if isinstance(dr, (int, float)) else ""
      st.progress(
        min(1.0, float(row.get("pct") or 0) / 100.0),
        text=(
          f"{row['label']} · {row['market']} · "
          f"R={row.get('R')} (lab {row.get('lab_R')}) {dr_s} · {row['status']}"
        ),
      )
    return

  for b in books:
    pct = b.get("pct") or 0
    market = f"{b.get('symbol')} {b.get('timeframe')}"
    n = b.get("n_models") or 0
    st.progress(
      min(1.0, float(pct) / 100.0),
      text=(
        f"{n} model(s) on {market} · "
        f"{b.get('bars_done')}/{b.get('bars_total')} ({pct}%) · "
        f"{b.get('ea_status')} · fills={b.get('n_fills')}"
      ),
    )


def render_replay_desk() -> dict:
  """Replay desk — Run → Progress → Results → Past runs (no Live chrome)."""
  from datetime import date as _date

  st.session_state.desk_mode = "Replay"
  if "replay_stats_period" not in st.session_state:
    st.session_state.replay_stats_period = "all"

  snap = desk_snapshot(sim=True)
  tone = snap["health_tone"]
  journal = snap["journal"]
  replay = snap.get("replay") or {}
  today = snap["today"]
  models = snap.get("models") or []
  running = bool(snap.get("bridge_running"))

  st.markdown(
    f"""
    <div class="desk-top">
      <div>
        <p class="desk-brand">EdgeMiner Live</p>
        <p class="desk-sub">Replay OOS · {snap.get('subtitle') or 'models'} · {LIVE_INSTANCE_ID}</p>
      </div>
      <div class="desk-clock">{snap['updated_at']}</div>
    </div>
    """,
    unsafe_allow_html=True,
  )

  n_on = len(models)
  pills = [
    pill(snap["health"], tone),
    pill("Running" if running else "Idle", "ok" if running else "muted"),
    pill(f"{n_on} model{'s' if n_on != 1 else ''} on", "ok" if n_on else "warn"),
    pill("SIM", "ok"),
  ]
  st.markdown(f'<div class="pill-row">{"".join(pills)}</div>', unsafe_allow_html=True)

  # ── 1. Run ──────────────────────────────────────────────────────────
  st.markdown('<div class="panel-label">1 · Run</div>', unsafe_allow_html=True)
  prefs = load_oos_prefs()
  try:
    d_from = _date.fromisoformat(str(prefs.get("from") or "2026-01-01")[:10])
  except ValueError:
    d_from = _date(2026, 1, 1)
  try:
    d_to = _date.fromisoformat(str(prefs.get("to") or "2026-08-07")[:10])
  except ValueError:
    d_to = _date(2026, 8, 7)

  # Seed widget state once from saved prefs (survives refresh / restart).
  if "oos_from_date" not in st.session_state:
    st.session_state.oos_from_date = d_from
  if "oos_to_date" not in st.session_state:
    st.session_state.oos_to_date = d_to

  oc1, oc2 = st.columns(2)
  with oc1:
    oos_from = st.date_input("OOS from", key="oos_from_date")
  with oc2:
    oos_to = st.date_input("OOS to", key="oos_to_date")

  # Auto-save range — no Save button; keep last config in oos_prefs.json
  cur_from, cur_to = str(oos_from), str(oos_to)
  if cur_from != str(prefs.get("from") or "") or cur_to != str(prefs.get("to") or ""):
    save_oos_prefs(date_from=cur_from, date_to=cur_to)
  if not models:
    st.info("Chưa bật model — mở **Models**, bật On, Save.")
  else:
    chips = " · ".join(
      f"{m.get('label') or m.get('model_id')} ({m.get('symbol')} {m.get('timeframe')})"
      for m in models[:8]
    )
    extra = f" · +{len(models) - 8} more" if len(models) > 8 else ""
    st.caption(f"Models on: {chips}{extra}")

  a1, a2, a3 = st.columns([1.4, 1, 2])
  with a1:
    if st.button(
      "Start OOS replay",
      type="primary",
      use_container_width=True,
      disabled=bool(running or not models),
      key="desk_start_replay",
    ):
      try:
        out = start_oos_replay(
          date_from=str(st.session_state.get("oos_from_date") or load_oos_prefs()["from"]),
          date_to=str(st.session_state.get("oos_to_date") or load_oos_prefs()["to"]),
          restart=True,
        )
        st.toast(f"Replay {out.get('from')}→{out.get('to')} · pid {out.get('pid')}")
        st.rerun()
      except Exception as exc:
        st.error(str(exc))
  with a2:
    if st.button(
      "Stop",
      use_container_width=True,
      disabled=not running,
      key="desk_stop_replay",
    ):
      stop_replay()
      st.toast("Replay stopped")
      st.rerun()
  with a3:
    st.caption(f"Window **{oos_from} → {oos_to}** · schedule-parity (lab TotalR/WR).")

  # ── 2. Progress ─────────────────────────────────────────────────────
  books = replay.get("books") or []
  if running or books:
    st.markdown('<div class="panel-label" style="margin-top:0.75rem">2 · Progress</div>', unsafe_allow_html=True)
    if running and not books:
      st.caption("Đang khởi động batch…")
    else:
      _render_replay_progress(replay, models)

  # ── 3. Results ──────────────────────────────────────────────────────
  st.markdown('<div class="panel-label" style="margin-top:0.75rem">3 · Results</div>', unsafe_allow_html=True)
  day_r = today.get("total_r") or 0.0
  tot_r = journal.get("total_r") or 0.0
  wr = journal.get("win_rate_pct")
  c1, c2, c3, c4 = st.columns(4)
  c1.metric("OOS R", f"{day_r:+.2f}")
  c2.metric("Closed", today.get("n") or journal.get("n_closed") or 0)
  c3.metric("Total R", f"{tot_r:+.2f}")
  c4.metric("Win rate", f"{wr}%" if wr is not None else "—")

  bdirs = [Path(p) for p in (snap.get("bridge_dirs") or [])]
  rows = stats_by_model_many(bdirs, period="all") if bdirs else []
  if rows:
    st.dataframe(
      [{
        "Model": r.get("label"),
        "Market": f"{r.get('symbol') or ''} {r.get('timeframe') or ''}".strip() or "—",
        "Closed": r.get("n_closed"),
        "W/L": f"{r.get('wins')}/{r.get('losses')}",
        "WR%": r.get("win_rate_pct"),
        "R": r.get("total_r"),
        "Open": r.get("n_open"),
      } for r in rows],
      use_container_width=True,
      hide_index=True,
    )
  else:
    st.caption("Chưa có kết quả — Start OOS replay.")

  trades = load_trades_many(bdirs) if bdirs else []
  parity_books = books
  eq = render_equity_section(trades, period="all", parity_books=parity_books)
  if eq and eq.get("figure") is not None:
    with st.expander("Equity & drawdown", expanded=True):
      e1, e2, e3 = st.columns(3)
      e1.metric("Curve R", eq.get("total_r") or 0)
      e2.metric("Max DD", f"{eq.get('max_dd_r') or 0}R")
      e3.metric(
        "Source",
        "parity weeks" if eq.get("source") == "parity_weeks" else f"{eq.get('n_points') or 0} trades",
      )
      st.plotly_chart(eq["figure"], use_container_width=True, config={"displayModeBar": False})
      st.caption("Đậm = all · nét đứt = từng model · panel dưới = DD từ đỉnh (R).")

  with st.expander("Trades", expanded=False):
    if trades:
      prefer = [
        "closed_at", "exit_time", "updated_at", "model_id", "action", "direction",
        "entry", "exit", "sl", "r", "result", "status", "mode", "reason", "magic",
      ]
      keys = [k for k in prefer if any(k in t for t in trades)]
      rows_t = [{k: t.get(k) for k in keys} for t in trades[-80:]] if keys else trades[-80:]
      st.dataframe(rows_t, use_container_width=True, hide_index=True)
    else:
      st.caption("Chưa có trade.")

  # ── 4. Past runs ────────────────────────────────────────────────────
  st.markdown('<div class="panel-label" style="margin-top:0.75rem">4 · Past runs</div>', unsafe_allow_html=True)
  runs = list_replay_runs(limit=20)
  cur = latest_parity_snapshot()
  if cur and not runs:
    from replay_history import archive_parity_batch
    if cur.get("books") and st.button("Archive current result into history", key="archive_cur"):
      archive_parity_batch(cur)
      st.rerun()
  if runs:
    options = {
      f"{r.get('created_at', '')[:19]} · {r.get('oos_from')}→{r.get('oos_to')} · "
      f"R={r.get('total_r')} · {r.get('n_ok')}/{r.get('n_models')} ok · {r.get('run_id')}": r
      for r in runs
    }
    pick = st.selectbox("Past runs", list(options.keys()), key="replay_hist_pick")
    chosen = options.get(pick) or runs[0]
    detail = load_replay_run(str(chosen.get("run_id"))) or {}
    hist_models = (detail.get("summary") or {}).get("models") or []
    if not hist_models:
      from replay_history import _summarize_batch
      hist_models = (_summarize_batch(detail).get("models") or [])
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total R", chosen.get("total_r"))
    m2.metric("Models OK", f"{chosen.get('n_ok')}/{chosen.get('n_models')}")
    m3.metric("OOS", f"{chosen.get('oos_from')} → {chosen.get('oos_to')}")
    m4.metric("Status", "OK" if chosen.get("ok") else "FAIL")
    if hist_models:
      st.dataframe(
        [{
          "Model": m.get("label") or m.get("model_id"),
          "Market": f"{m.get('symbol') or ''} {m.get('timeframe') or ''}".strip(),
          "R": m.get("total_r"),
          "Lab R": m.get("lab_total_r"),
          "ΔR": m.get("delta_r"),
          "WR%": m.get("win_rate_pct"),
          "Trades": m.get("n_trades"),
          "OK": m.get("ok"),
        } for m in hist_models],
        use_container_width=True,
        hide_index=True,
      )
    with st.expander("Raw run JSON", expanded=False):
      st.json({
        "run_id": detail.get("run_id"),
        "oos_from": detail.get("oos_from"),
        "oos_to": detail.get("oos_to"),
        "ok": detail.get("ok"),
        "summary": detail.get("summary"),
      })
  else:
    st.caption("Chưa có run lưu — Start OOS replay một lần để tạo history.")

  with st.expander("Reset replay history", expanded=False):
    wipe_archive = st.checkbox("Also delete past runs archive", value=True, key="wipe_replay_arch")
    confirm_rep = st.text_input(
      "Type CLEAR to reset",
      value="",
      key="replay_reset_confirm",
      placeholder="CLEAR",
    )
    if st.button("Reset replay history", type="primary", key="reset_replay_btn"):
      if confirm_rep.strip() != "CLEAR":
        st.error("Gõ đúng CLEAR để xác nhận.")
      else:
        out = reset_replay_history(
          stop_replay_proc=True,
          clear_archive=bool(wipe_archive),
          clear_current=True,
          clear_sim_journals=True,
        )
        st.session_state["last_replay_reset"] = out
        st.toast("Replay history cleared")
        st.rerun()
    last_rr = st.session_state.get("last_replay_reset")
    if last_rr:
      st.caption(
        f"Last reset removed {len(last_rr.get('removed') or [])} files"
        + ("" if last_rr.get("ok") else f" · errors: {last_rr.get('errors')}")
      )

  return snap


def _health_flag_html(level: str, text: str) -> str:
  lv = level if level in ("ok", "warn", "danger", "muted") else "muted"
  return f'<span class="health-flag health-flag-{lv}">{text}</span>'


def _render_health_panel(health: dict, *, sim: bool = False) -> None:
  """Per-book / per-model pipeline freshness — stuck EA/model detector."""
  if not health:
    return
  overall = health.get("overall") or "muted"
  summary = health.get("summary") or "—"
  st.markdown(
    f'<div class="panel-label" style="margin-top:0.75rem">Pipeline health · '
    f'{_health_flag_html(overall, summary)}</div>',
    unsafe_allow_html=True,
  )
  if sim:
    st.caption("Replay mode — health chi tiết dành cho Live (EA ↔ worker từng nến).")
    return

  alerts = health.get("alerts") or []
  if alerts:
    for a in alerts[:8]:
      lv = a.get("level") or "warn"
      msg = a.get("message") or a.get("code") or "—"
      st.markdown(
        f'<div class="health-alert health-alert-{lv}">{msg}</div>',
        unsafe_allow_html=True,
      )

  books = health.get("books") or []
  if not books:
    st.caption("Chưa có book — bật model trong Models.")
    return

  for book in books:
    flags = " · ".join(book.get("flags") or []) or "OK"
    worker = (
      f"pid {book.get('worker_pid')}" if book.get("worker_alive") else "worker down"
    )
    head_meta = (
      f"EA {book.get('ea_state')} {book.get('ea_age')} · "
      f"bar {book.get('bar_time') or '—'} ({book.get('bar_age')}) · "
      f"status {book.get('status_state')} {book.get('status_age')} · {worker}"
    )
    if book.get("ea_sync_summary"):
      head_meta += f" · sync {book.get('ea_sync_summary')} ({book.get('ea_sync_age')})"
    models_html = []
    for m in book.get("models") or []:
      mflags = ",".join(m.get("flags") or []) or ("OK" if m.get("level") == "ok" else "—")
      models_html.append(
        "<div class='health-model'>"
        f"<div><strong>{m.get('label') or m.get('model_id')}</strong>"
        f"<div class='model-meta'>magic {m.get('magic') or '—'} · {m.get('reason') or ''}</div></div>"
        f"<div>{m.get('action') or '—'}</div>"
        f"<div class='model-meta'>dec {m.get('decision_age')} · bar {m.get('bar_time') or '—'}</div>"
        f"{_health_flag_html(m.get('level') or 'muted', mflags)}"
        "</div>"
      )
    st.markdown(
      f"""
      <div class="health-book">
        <div class="health-book-head">
          <div class="health-book-title">{book.get('symbol')} {book.get('timeframe')} · {book.get('n_models')} model(s)
            {_health_flag_html(book.get('level') or 'muted', flags)}</div>
          <div class="health-book-meta">{head_meta}</div>
        </div>
        {''.join(models_html)}
      </div>
      """,
      unsafe_allow_html=True,
    )
  st.caption(
    "TIMEOUT/LAG = decision chưa khớp nến EA · EA_STALE = heartbeat chết · "
    "WORKER_STALE = App không cập nhật status. Bật Auto-refresh để theo dõi."
  )


def render_live_desk() -> dict:
  """Live desk — Control → Now → Pipeline → Session (History gộp vào)."""
  st.session_state.desk_mode = "Live"
  if "live_stats_period" not in st.session_state or st.session_state.live_stats_period not in PERIODS:
    st.session_state.live_stats_period = "all"

  snap = desk_snapshot(sim=False)
  tone = snap["health_tone"]
  dec = snap["decision"]
  today = snap["today"]
  journal = snap["journal"]
  health_detail = snap.get("health_detail") or {}
  models = snap.get("models") or []
  running = bool(snap.get("bridge_running"))

  st.markdown(
    f"""
    <div class="desk-top">
      <div>
        <p class="desk-brand">EdgeMiner Live</p>
        <p class="desk-sub">Live trading · {snap.get('subtitle') or 'models'} · {LIVE_INSTANCE_ID}</p>
      </div>
      <div class="desk-clock">{snap['updated_at']}</div>
    </div>
    """,
    unsafe_allow_html=True,
  )

  n_on = len(models)
  pills = [
    pill(snap["health"], tone),
    pill("Running" if running else "Stopped", "ok" if running else "muted"),
    pill(f"{n_on} model{'s' if n_on != 1 else ''} on", "ok" if n_on else "warn"),
    pill(
      f"EA {snap['ea_age']}" if snap["ea_online"] else "EA offline",
      "ok" if snap["ea_online"] else "warn",
    ),
    pill(f"{snap['n_open']} open", "warn" if snap["n_open"] else "muted"),
  ]
  if snap["kill_switch"]:
    pills.append(pill("KILL ARMED", "danger"))
  if snap.get("loss_guard_tripped"):
    pills.append(pill("RISK TRIP", "danger"))
  if health_detail:
    h_tone = health_detail.get("overall") or "muted"
    if h_tone not in ("ok", "warn", "danger", "muted"):
      h_tone = "warn"
    pills.append(pill(str(health_detail.get("summary") or "HEALTH"), h_tone))
  st.markdown(f'<div class="pill-row">{"".join(pills)}</div>', unsafe_allow_html=True)

  for err in snap.get("chart_errors") or []:
    st.error(err)
  for w in (snap.get("chart_warnings") or [])[:2]:
    st.warning(w)

  # ── 1. Control ──────────────────────────────────────────────────────
  st.markdown('<div class="panel-label">1 · Control</div>', unsafe_allow_html=True)
  if not models:
    st.info("Chưa bật model — mở **Models**, bật On, Save.")
  else:
    chips = " · ".join(
      f"{m.get('label') or m.get('model_id')} ({m.get('symbol')} {m.get('timeframe')})"
      for m in models[:8]
    )
    extra = f" · +{len(models) - 8} more" if len(models) > 8 else ""
    st.caption(f"On: {chips}{extra}")

  a1, a2, a3, a4 = st.columns([1.3, 1, 1, 1.2])
  with a1:
    mt5_up = True
    if os.name == "nt":
      try:
        from deploy_ea import is_mt5_running
        mt5_up = bool(is_mt5_running())
      except Exception:
        mt5_up = True
    # Allow Start when MT5 is down even if workers still "Running".
    start_disabled = bool(snap["kill_switch"] or not models or (running and mt5_up))
    start_why = ""
    if snap["kill_switch"]:
      start_why = "Kill đang armed — bấm Disarm kill trước."
    elif running and not mt5_up:
      start_why = "MT5 đã tắt — bấm Start để mở lại terminal (+ deploy nếu cần)."
    elif running:
      start_why = "Bridge đang Running — bấm Stop rồi Start lại nếu cần."
    elif not models:
      start_why = "Chưa có model On — mở Models, bật On, Save."
    if not mt5_up and os.name == "nt":
      st.warning("XM MT5 không chạy — Start sẽ mở lại terminal64.")
    start_label = "Start trading" if mt5_up or not running else "Mở lại MT5 + Start"
    if st.button(
      start_label,
      type="primary",
      use_container_width=True,
      disabled=start_disabled,
      key="desk_start",
      help=start_why or "Deploy EA (nếu thiếu) rồi start bridge workers.",
    ):
      try:
        with st.spinner("Checking / deploying EA trên MT5 (Windows)…"):
          if running and not mt5_up:
            # Workers still up but terminal closed — reopen MT5 without full stop first.
            from deploy_ea import ensure_live_eas_deployed, ensure_mt5_running
            mt5 = ensure_mt5_running(wait_sec=12.0)
            if not mt5.get("ok"):
              raise RuntimeError(
                "Không mở lại được XM MT5.\n"
                f"{mt5.get('error') or mt5.get('reason') or ''}"
              )
            dep = ensure_live_eas_deployed(
              force=True, wait_online=False, wait_sec=15.0,
            )
            out = {"n_workers": "kept", "deploy": dep, "pid": "—"}
            if mt5.get("started"):
              st.toast("XM MT5 đã mở lại")
          else:
            out = start_bridge(require_chart=False)
            dep = out.get("deploy") or {}
            mt5 = (dep.get("mt5") or {}) if isinstance(dep, dict) else {}
            if mt5.get("started"):
              st.toast("XM MT5 đã khởi động")
        dep = out.get("deploy") or {}
        if dep.get("deployed"):
          n = (dep.get("coverage") or {}).get("n_books") or len(dep.get("books") or [])
          st.toast(f"Deployed EA · {n} book(s) · Started")
        else:
          st.toast(f"Started · {out.get('n_workers') or out.get('pid')} worker(s)")
        st.rerun()
      except Exception as exc:
        st.error(str(exc))
    if start_why:
      st.caption(start_why)
  with a2:
    if st.button("Stop", use_container_width=True, disabled=not running, key="desk_stop"):
      stop_bridge(flatten=False)
      st.toast("Stopped")
      st.rerun()
  with a3:
    if st.button("Flatten", use_container_width=True, key="desk_flat"):
      write_flatten_command(reason="desk_flatten")
      st.toast("Flatten sent")
      st.rerun()
  with a4:
    kill_label = "Disarm kill" if snap["kill_switch"] else "Emergency kill"
    if st.button(kill_label, use_container_width=True, key="desk_kill_toggle"):
      if snap["kill_switch"]:
        disarm_kill_switch()
        st.toast("Kill disarmed")
      else:
        arm_kill_switch(reason="desk_emergency", flatten=True)
        st.toast("Kill armed · flattened")
      st.rerun()

  # ── 2. Now ──────────────────────────────────────────────────────────
  st.markdown('<div class="panel-label" style="margin-top:0.75rem">2 · Now</div>', unsafe_allow_html=True)
  left, right = st.columns([1.35, 1])
  with left:
    act = dec.get("action") or "—"
    sig_tone = dec.get("tone") or "unknown"
    act_cls = f"decision-{sig_tone}"
    panel_cls = f"signal-{sig_tone}"
    reason = dec.get("reason") or "—"
    meta_bits = []
    if dec.get("bar_time"):
      meta_bits.append(f"bar {dec['bar_time']}")
    if snap["bar"].get("close") is not None:
      meta_bits.append(f"last {snap['bar'].get('close')}")
    meta = " · ".join(meta_bits) if meta_bits else "Waiting for first decision…"
    labels = _model_label_map(models)
    mid = dec.get("model_id")
    model_line = labels.get(str(mid), mid) if mid else (
      models[0].get("label") if models else "—"
    )
    badge = signal_badge(sig_tone)
    st.markdown(
      f"""
      <div class="panel signal-panel {panel_cls}">
        <div class="signal-head">
          <div class="panel-label">Signal</div>
          <span class="signal-badge">{badge}</span>
        </div>
        <div class="decision-action {act_cls}">{act}</div>
        <div class="decision-meta">
          <div class="decision-model">{model_line}</div>
          <div class="decision-reason">{reason}</div>
          <div class="decision-wait">{meta}</div>
        </div>
      </div>
      """,
      unsafe_allow_html=True,
    )
  with right:
    day_r = today.get("total_r") or 0.0
    tot_r = journal.get("total_r") or 0.0
    wr = journal.get("win_rate_pct")
    wr_s = f"{wr}%" if wr is not None else "—"
    n_today = today.get("n") or 0
    n_closed = journal.get("n_closed") or 0
    n_open = len(snap.get("open_trades") or [])
    st.markdown(
      f"""
      <div class="panel session-panel">
        <div class="panel-label">Session</div>
        <div class="stat-grid">
          <div class="stat-cell">
            <div class="stat-k">Today R</div>
            <div class="stat-v {r_class(day_r)}">{day_r:+.2f}</div>
          </div>
          <div class="stat-cell">
            <div class="stat-k">Closed</div>
            <div class="stat-v neutral">{n_today if n_today else n_closed}</div>
          </div>
          <div class="stat-cell">
            <div class="stat-k">Total R</div>
            <div class="stat-v {r_class(tot_r)}">{tot_r:+.2f}</div>
          </div>
          <div class="stat-cell">
            <div class="stat-k">Win rate</div>
            <div class="stat-v neutral">{wr_s}</div>
          </div>
        </div>
      </div>
      """,
      unsafe_allow_html=True,
    )
    if n_open:
      st.caption(f"Đang mở {n_open} vị thế.")
    elif n_today == 0 and n_closed == 0:
      st.caption("Chưa có lệnh đóng — thống kê R cập nhật khi EA đóng lệnh.")

  if snap.get("open_trades"):
    st.markdown('<div class="panel-label">Open positions</div>', unsafe_allow_html=True)
    labels = _model_label_map(models)
    for t in snap["open_trades"][:6]:
      side = str(t.get("action") or t.get("direction") or "?").upper()
      mid = str(t.get("model_id") or "")
      name = labels.get(mid) or t.get("label") or mid or "—"
      st.markdown(
        f"""<div class="model-card"><div class="model-title">{side} · {name}</div>
        <div class="model-meta">entry {t.get('entry') or t.get('entry_price') or '—'} · sl {t.get('sl') or '—'} · magic {t.get('magic') or '—'}</div></div>""",
        unsafe_allow_html=True,
      )

  # ── 3. Pipeline health ──────────────────────────────────────────────
  st.markdown('<div class="panel-label" style="margin-top:0.75rem">3 · Pipeline</div>', unsafe_allow_html=True)
  _render_health_panel(health_detail, sim=False)

  # ── 4. Session results (ex-History) ─────────────────────────────────
  st.markdown('<div class="panel-label" style="margin-top:0.75rem">4 · Session</div>', unsafe_allow_html=True)
  period = st.radio(
    "Period",
    options=list(PERIODS),
    format_func=lambda k: PERIOD_LABELS.get(k, k),
    horizontal=True,
    key="live_stats_period",
  )
  from desk_snapshot import _bridge_dirs_for_enabled, book_models
  from journal_view import filter_trades_by_period

  bdirs = _bridge_dirs_for_enabled(book_models(), sim=False)
  if not bdirs:
    bdirs = [Path(p) for p in (snap.get("bridge_dirs") or [])] or [BRIDGE_DIR]
  summary = journal_summary_many(bdirs, period=period)
  rows = [
    r for r in stats_by_model_many(bdirs, period=period)
    if (r.get("n_closed") or 0) or (r.get("n_open") or 0)
  ]
  model_table = [
    {
      "Model": r.get("label"),
      "Market": f"{r.get('symbol') or ''} {r.get('timeframe') or ''}".strip() or "—",
      "Open": r.get("n_open"),
      "Closed": r.get("n_closed"),
      "W": r.get("wins"),
      "L": r.get("losses"),
      "WR%": r.get("win_rate_pct"),
      "Total R": r.get("total_r"),
      "Avg R": r.get("avg_r"),
    }
    for r in rows
  ]
  all_trades = load_trades_many(bdirs)
  trades = filter_trades_by_period(all_trades, period)
  fills = []
  for bdir in bdirs:
    fills.extend(load_recent_fills(bdir, limit=25))
  fills = fills[-25:]

  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Closed", summary.get("n_closed") or 0)
  c2.metric("Total R", f"{float(summary.get('total_r') or 0):+.3f}")
  c3.metric("WR%", summary.get("win_rate_pct") if summary.get("win_rate_pct") is not None else "—")
  c4.metric("W/L", f"{summary.get('wins') or 0}/{summary.get('losses') or 0}")

  if model_table:
    st.dataframe(model_table, use_container_width=True, hide_index=True)
  else:
    st.caption(f"Chưa có lệnh đóng trong {PERIOD_LABELS.get(period, period)}.")

  eq = render_equity_section(trades, period="all", parity_books=None)
  if eq and eq.get("figure") is not None:
    with st.expander("Equity & drawdown", expanded=True):
      e1, e2, e3 = st.columns(3)
      e1.metric("Curve R", eq.get("total_r") or 0)
      e2.metric("Max DD", f"{eq.get('max_dd_r') or 0}R")
      e3.metric("Source", f"{eq.get('n_points') or 0} trades")
      st.plotly_chart(eq["figure"], use_container_width=True, config={"displayModeBar": False})
      st.caption("Đậm = all · nét đứt = từng model · panel dưới = DD từ đỉnh (R).")
      bym = eq.get("by_model") or {}
      if len(bym) > 1:
        st.dataframe(
          [{
            "Model": v.get("label"),
            "Points": v.get("n"),
            "Total R": v.get("total_r"),
            "Max DD": v.get("max_dd_r"),
          } for v in bym.values()],
          use_container_width=True,
          hide_index=True,
        )

  with st.expander("Trades", expanded=False):
    if trades:
      prefer = [
        "closed_at", "exit_time", "updated_at", "model_id", "action", "direction",
        "entry", "exit", "sl", "r", "result", "status", "mode", "reason", "magic",
      ]
      keys = [k for k in prefer if any(k in t for t in trades)]
      rows = [{k: t.get(k) for k in keys} for t in trades[-80:]] if keys else trades[-80:]
      st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
      st.caption("Chưa có trade — đợi EA đóng lệnh.")
    if fills:
      st.caption("Raw fills")
      st.dataframe(fills, use_container_width=True, hide_index=True)

  return snap



def render_setup_page() -> None:
  """Setup — Risk → Safety → Runtime → Windows/EA → Danger zone."""
  st.markdown(
    f"""
    <div class="desk-top">
      <div>
        <p class="desk-brand">EdgeMiner Live</p>
        <p class="desk-sub">Setup · {LIVE_INSTANCE_ID}</p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
  )

  # ── 1. Risk limits ──────────────────────────────────────────────────
  st.markdown('<div class="panel-label">1 · Risk limits</div>', unsafe_allow_html=True)
  st.caption(
    "Chạm ngưỡng → FLAT + dừng service. Áp dụng Live trading. 0 = tắt ngưỡng đó."
  )
  prefs = load_risk_prefs()
  snap_r = risk_status_snapshot()
  if snap_r.get("tripped"):
    st.error(
      f"TRIPPED · {snap_r.get('tripped_reason') or 'risk guard'} "
      f"· {snap_r.get('tripped_at') or ''}"
    )
    if st.button("Clear trip (cho phép Start lại)", key="clear_risk_trip"):
      clear_loss_guard_trip()
      st.toast("Trip cleared — bấm Start trading")
      st.rerun()

  cstat = st.columns(4)
  cstat[0].metric("DD hôm nay", f"{snap_r.get('day_dd_r') if snap_r.get('day_dd_r') is not None else '—'}R")
  cstat[1].metric("DD tuần", f"{snap_r.get('week_dd_r') if snap_r.get('week_dd_r') is not None else '—'}R")
  cstat[2].metric("R hôm nay", snap_r.get("day_total_r") if snap_r.get("day_total_r") is not None else "—")
  cstat[3].metric("Streak thua ngày", snap_r.get("day_streak") if snap_r.get("day_streak") is not None else "—")

  en = st.toggle("Enable risk guard", value=bool(prefs.get("loss_guard_enabled", True)), key="risk_en")
  r1, r2 = st.columns(2)
  with r1:
    day_dd = st.number_input(
      "Max DD ngày (R)", min_value=0.0, max_value=100.0,
      value=float(prefs.get("loss_guard_max_day_dd_r") or 0), step=0.5, key="risk_day_dd",
      help="Peak-to-trough drawdown trong ngày ≥ ngưỡng → stop",
    )
    week_dd = st.number_input(
      "Max DD tuần (R)", min_value=0.0, max_value=200.0,
      value=float(prefs.get("loss_guard_max_week_dd_r") or 0), step=0.5, key="risk_week_dd",
    )
    day_loss = st.number_input(
      "Max lỗ ngày (R)", min_value=0.0, max_value=100.0,
      value=float(prefs.get("loss_guard_max_day_loss_r") or 0), step=0.5, key="risk_day_loss",
      help="Tổng R trong ngày ≤ −ngưỡng → stop (0=tắt)",
    )
  with r2:
    week_loss = st.number_input(
      "Max lỗ tuần (R)", min_value=0.0, max_value=200.0,
      value=float(prefs.get("loss_guard_max_week_loss_r") or 0), step=0.5, key="risk_week_loss",
    )
    day_streak = st.number_input(
      "Max thua liên tiếp / ngày", min_value=0, max_value=50,
      value=int(prefs.get("loss_guard_max_day") or 0), step=1, key="risk_day_streak",
    )
    week_streak = st.number_input(
      "Max thua liên tiếp / tuần", min_value=0, max_value=80,
      value=int(prefs.get("loss_guard_max_week") or 0), step=1, key="risk_week_streak",
    )

  if st.button("Save risk limits", type="primary", key="save_risk_limits"):
    save_risk_prefs(
      loss_guard_enabled=bool(en),
      loss_guard_max_day_dd_r=float(day_dd),
      loss_guard_max_week_dd_r=float(week_dd),
      loss_guard_max_day_loss_r=float(day_loss),
      loss_guard_max_week_loss_r=float(week_loss),
      loss_guard_max_day=int(day_streak),
      loss_guard_max_week=int(week_streak),
    )
    try:
      from bridge_control import save_config
      save_config(
        loss_guard_enabled=bool(en),
        loss_guard_max_day_dd_r=float(day_dd),
        loss_guard_max_week_dd_r=float(week_dd),
        loss_guard_max_day_loss_r=float(day_loss),
        loss_guard_max_week_loss_r=float(week_loss),
        loss_guard_max_day=int(day_streak),
        loss_guard_max_week=int(week_streak),
      )
    except Exception:
      pass
    st.toast("Risk limits saved")
    st.rerun()

  # ── 2. Safety ───────────────────────────────────────────────────────
  st.markdown('<div class="panel-label" style="margin-top:0.75rem">2 · Safety</div>', unsafe_allow_html=True)
  st.caption("Emergency kill dừng mọi model, khóa latch, và Flatten. Dùng khi cần dừng tay.")
  kill_on = is_kill_switch_armed()
  st.markdown(
    f'<div class="pill-row">{pill("KILL ARMED" if kill_on else "Kill off", "danger" if kill_on else "muted")}</div>',
    unsafe_allow_html=True,
  )
  k1, k2 = st.columns(2)
  with k1:
    if st.button("Arm kill-switch", type="primary", key="setup_arm_kill"):
      arm_kill_switch(reason="setup_kill", flatten=True)
      st.rerun()
  with k2:
    if st.button("Disarm kill-switch", key="setup_disarm_kill"):
      disarm_kill_switch()
      st.rerun()

  # ── 3. Runtime ──────────────────────────────────────────────────────
  st.markdown('<div class="panel-label" style="margin-top:0.75rem">3 · Runtime</div>', unsafe_allow_html=True)
  st.caption("Workers / service — hàng ngày Start/Stop trên desk Live; đây là trạng thái kỹ thuật.")
  try:
    from debug_log import support_bundle_hint
    st.caption(f"Debug logs (hỗ trợ): `{support_bundle_hint()}`")
  except Exception:
    pass
  st_stat = status()
  m1, m2, m3 = st.columns(3)
  m1.metric("Workers", st_stat.get("n_workers") or (1 if st_stat["running"] else 0))
  m2.metric("PID", st_stat["pid"] or "—")
  m3.metric("Kill-switch", "ARMED" if kill_on else "off")
  if st_stat.get("workers"):
    for w in st_stat["workers"]:
      mark = "●" if w.get("alive") else "○"
      mids = ", ".join(w.get("model_ids") or []) or "—"
      st.caption(
        f"{mark} models [{mids}] · {w.get('symbol')} {w.get('timeframe')} · pid {w.get('pid')}"
      )
  rt1, rt2 = st.columns(2)
  with rt1:
    if st.button("Start (require EA online)", key="setup_start_bridge"):
      try:
        with st.spinner("Auto-deploy EA (nếu thiếu) rồi Start…"):
          out = start_bridge(require_chart=True)
        dep = out.get("deploy") or {}
        st.success(
          f"workers={out.get('n_workers')} pid={out.get('pid')}"
          + (f" · deployed={dep.get('deployed')}" if dep else "")
        )
        st.rerun()
      except Exception as exc:
        st.error(str(exc))
  with rt2:
    if st.button("Stop + flatten", key="setup_stop_bridge"):
      stop_bridge(flatten=True)
      st.rerun()

  # ── 4. Windows / EA ─────────────────────────────────────────────────
  st.markdown('<div class="panel-label" style="margin-top:0.75rem">4 · Windows / EA</div>', unsafe_allow_html=True)
  with st.expander("Autostart sau reboot", expanded=False):
    from windows_autostart import (
      is_windows as _is_win_as,
      load_prefs as _as_prefs,
      task_status as _as_status,
    )
    st_as = _as_status()
    prefs_as = st_as.get("prefs") or _as_prefs()
    st.markdown(
      "**Theo Start / Stop trading:**\n"
      "- **Start** → gắn Scheduled Task (reboot: MT5 + Live app + bridge)\n"
      "- **Stop / Emergency kill** → gỡ task\n"
    )
    if not _is_win_as():
      st.caption("Task thật chỉ đăng ký trên PC Windows chạy MT5.")
    else:
      installed = bool(st_as.get("task_installed"))
      st.write(
        f"Task: **{'INSTALLED' if installed else 'not installed'}** · "
        f"enabled={prefs_as.get('enabled')} · start_bridge={prefs_as.get('start_bridge')}"
      )
      st.caption(f"Delay logon {prefs_as.get('delay_sec') or 45}s · log: results/debug_logs/boot_*.log")
      if st.button("Refresh status", key="as_refresh"):
        st.rerun()

  with st.expander("EA attach (auto-deploy)", expanded=False):
    enabled = [r for r in (load_roster().get("models") or []) if r.get("enabled")]
    groups = group_models_by_book(enabled)
    if not groups:
      st.info("Bật ít nhất một model rồi Save ở Models.")
    else:
      lines = [
        "Live **Start** trên Windows tự check + deploy EA đủ mọi book đang bật "
        "(`deploy_live_ea.ps1 -FromRoster`).",
        "",
        "Mỗi thị trường (symbol+TF) → 1 chart `ForgeBridgeLive` với `InpBridgeSubdir`:",
        "",
      ]
      for (sym, tf), rows in groups.items():
        sub = bridge_subdir(sym, tf, sim=False)
        labels = ", ".join(r.get("label") or r.get("model_id") for r in rows)
        lines.append(f"- **{labels}** · {sym} {tf}")
        lines.append(f"  → `InpBridgeSubdir={sub}`")
      lines.append("")
      lines.append(f"Magic base `{LIVE_MAGIC_BASE}` · manual: `deploy_live_ea.ps1 -FromRoster`")
      lines.append("Tắt auto-deploy: env `LIVE_SKIP_EA_DEPLOY=1`")
      st.markdown("\n".join(lines))
      if st.button("Deploy EA now (Windows)", key="setup_deploy_ea_now"):
        try:
          from deploy_ea import ensure_live_eas_deployed
          with st.spinner("Deploying all enabled books…"):
            info = ensure_live_eas_deployed(force=True, wait_online=True, wait_sec=60.0)
          st.success(
            f"OK · books={(info.get('coverage') or {}).get('n_books')} "
            f"deployed={info.get('deployed')} skipped={info.get('skipped')}"
          )
        except Exception as exc:
          st.error(str(exc))

  # ── 5. Danger zone ──────────────────────────────────────────────────
  st.markdown('<div class="panel-label" style="margin-top:0.75rem">5 · Danger zone</div>', unsafe_allow_html=True)
  with st.expander("Reset all Live data", expanded=False):
    st.caption(
      "Xóa journal · sim/parity · bridge state · OHLC cache · "
      "(tuỳ chọn) packages + roster. Dừng workers/replay trước khi wipe."
    )
    wipe_packages = st.checkbox(
      "Also remove installed packages & clear roster",
      value=True,
      key="reset_wipe_packages",
    )
    reseed = st.checkbox(
      "Re-seed OHLC from lab after wipe (only if packages kept)",
      value=True,
      key="reset_reseed",
      disabled=wipe_packages,
    )
    confirm = st.text_input(
      "Type RESET to confirm",
      value="",
      key="reset_confirm_txt",
      placeholder="RESET",
    )
    if st.button("Reset all Live data", type="primary", key="reset_all_btn"):
      if confirm.strip() != "RESET":
        st.error("Gõ đúng RESET để xác nhận.")
      else:
        with st.spinner("Resetting…"):
          out = reset_live_data(
            stop_services=True,
            journal=True,
            sim_parity=True,
            runtime=True,
            ohlc_cache=True,
            include_packages=bool(wipe_packages),
            reseed_ohlc=bool(reseed) and not wipe_packages,
            disarm_kill=True,
          )
        st.session_state["last_reset"] = out
        st.rerun()

    last = st.session_state.get("last_reset")
    if last:
      if last.get("ok"):
        st.success(
          "Last reset OK · bridges={n} · packages={p} · roster_cleared={r} · reseed={s}".format(
            n=len(last.get("bridges") or {}),
            p=last.get("packages_removed") or 0,
            r=last.get("roster_cleared"),
            s=len(last.get("reseed") or []),
          )
        )
      else:
        st.warning("Last reset có lỗi: " + "; ".join(last.get("errors") or [])[:400])
      with st.expander("Last reset details", expanded=False):
        st.json(last)


def render_models_page() -> None:
  """Models — Roster → Import → Installed."""
  st.markdown(
    f"""
    <div class="desk-top">
      <div>
        <p class="desk-brand">EdgeMiner Live</p>
        <p class="desk-sub">Models · {LIVE_INSTANCE_ID}</p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
  )

  # ── 1. Roster ───────────────────────────────────────────────────────
  st.markdown('<div class="panel-label">1 · Roster</div>', unsafe_allow_html=True)
  st.caption("Bật/tắt và risk theo **model**. Symbol·TF = thị trường của model đó. Save rồi Start ở Live.")

  roster = load_roster()
  models = roster.get("models") or default_roster_from_installed()
  have = {m.get("install_id") for m in models}
  for inst in list_installed():
    if inst["install_id"] not in have:
      models.append({
        "install_id": inst["install_id"],
        "model_id": inst["model_id"],
        "label": inst["label"],
        "symbol": inst["symbol"],
        "timeframe": inst["timeframe"],
        "enabled": True,
        "risk_pct": 1.0,
        "magic": None,
      })

  if not models:
    st.info("Chưa có model — Import package (.tmpkg) ở mục 2.")
  else:
    edited = []
    for i, row in enumerate(models):
      c1, c2, c3, c4 = st.columns([3.2, 0.8, 1.1, 1])
      with c1:
        st.markdown(f"**{row.get('label') or row.get('model_id')}**")
        st.caption(f"{row.get('symbol')} {row.get('timeframe')} · {row.get('model_id')}")
      with c2:
        en = st.toggle("On", value=bool(row.get("enabled", True)), key=f"en_{i}")
      with c3:
        risk = st.number_input(
          "Risk %",
          min_value=0.1,
          max_value=5.0,
          value=float(row.get("risk_pct") or 1.0),
          step=0.1,
          key=f"risk_{i}",
        )
      with c4:
        st.markdown(
          f"<div style='padding-top:1.6rem;color:var(--desk-muted);font-family:IBM Plex Mono,monospace;font-size:0.85rem'>"
          f"{row.get('magic') or '—'}</div>",
          unsafe_allow_html=True,
        )
      edited.append({**row, "enabled": en, "risk_pct": risk})

    s1, s2, s3 = st.columns([1.4, 1, 1])
    with s1:
      if st.button("Save roster", type="primary", use_container_width=True, key="save_roster_btn"):
        assigned = assign_magics(edited, sim=False)
        save_roster(assigned)
        subprocess.run(
          [sys.executable, str(LIVE / "sync_bridge_roster.py")],
          cwd=str(LIVE),
          capture_output=True,
          text=True,
          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0,
        )
        st.toast("Saved · synced to EA")
        st.rerun()
    with s2:
      if st.button("Sync to EA", use_container_width=True, key="sync_ea_btn"):
        r = subprocess.run(
          [sys.executable, str(LIVE / "sync_bridge_roster.py")],
          cwd=str(LIVE),
          capture_output=True,
          text=True,
          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0,
        )
        if r.returncode == 0:
          st.success((r.stdout or "Synced").strip().split("\n")[0])
        else:
          st.error(r.stderr or "sync failed")
    with s3:
      if st.button("Rebuild from installed", use_container_width=True, key="rebuild_roster_btn"):
        save_roster(default_roster_from_installed())
        st.rerun()

  # ── 2. Import ───────────────────────────────────────────────────────
  st.markdown('<div class="panel-label" style="margin-top:0.75rem">2 · Import</div>', unsafe_allow_html=True)
  st.caption("Nhận package từ Lab (.tmpkg) rồi thêm vào roster.")
  up = st.file_uploader("Upload .tmpkg", type=["tmpkg"], key="models_upload")
  path_txt = st.text_input("Or path to .tmpkg", "", key="models_path")
  if st.button("Import package", type="primary", key="import_pkg_btn"):
    try:
      if up is not None:
        INBOX_DIR.mkdir(parents=True, exist_ok=True)
        dest = INBOX_DIR / up.name
        dest.write_bytes(up.getvalue())
        pkg = dest
      elif path_txt.strip():
        pkg = Path(path_txt.strip())
      else:
        st.error("Choose a file or path")
        pkg = None
      if pkg:
        r = subprocess.run(
          [sys.executable, str(LIVE / "import_trade_package.py"), str(pkg)],
          cwd=str(LIVE),
          capture_output=True,
          text=True,
          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0,
        )
        if r.returncode == 0:
          st.success((r.stdout or "Imported").strip())
          st.rerun()
        else:
          st.error(r.stderr or r.stdout or f"exit {r.returncode}")
    except Exception as exc:
      st.exception(exc)

  # ── 3. Installed ────────────────────────────────────────────────────
  st.markdown('<div class="panel-label" style="margin-top:0.75rem">3 · Installed</div>', unsafe_allow_html=True)
  installed = list_installed()
  if not installed:
    st.caption("Empty — export package từ Lab trước.")
  else:
    roster_now = load_roster().get("models") or []
    enabled_ids = {
      str(m.get("install_id"))
      for m in roster_now
      if m.get("enabled") and m.get("install_id")
    }
    running = bool(status().get("running"))
    for row in installed:
      iid = str(row.get("install_id") or "")
      on = iid in enabled_ids
      c_a, c_b = st.columns([4, 1])
      with c_a:
        st.markdown(
          f"**{row.get('label')}**  \n"
          f"<span style='color:var(--desk-muted);font-size:0.85rem'>"
          f"{row.get('symbol')} {row.get('timeframe')} · {row.get('model_id')}"
          f"{' · On' if on else ''}</span>",
          unsafe_allow_html=True,
        )
      with c_b:
        if st.button("Delete", key=f"del_ask_{iid}", use_container_width=True):
          st.session_state["pending_delete_install_id"] = iid

    pending = st.session_state.get("pending_delete_install_id")
    if pending:
      victim = next((r for r in installed if r.get("install_id") == pending), None)
      if victim is None:
        st.session_state.pop("pending_delete_install_id", None)
      else:
        st.warning(
          f"Xóa package **{victim.get('label') or pending}**? "
          "Gỡ khỏi disk + roster. Không hoàn tác."
        )
        if pending in enabled_ids and running:
          st.error("Model đang On và bridge đang chạy — nên **Stop** trước khi xóa.")
        d1, d2 = st.columns(2)
        with d1:
          if st.button("Confirm delete", type="primary", key="del_confirm"):
            try:
              out = delete_installed(pending)
              st.session_state.pop("pending_delete_install_id", None)
              try:
                subprocess.run(
                  [sys.executable, str(LIVE / "sync_bridge_roster.py")],
                  cwd=str(LIVE),
                  capture_output=True,
                  text=True,
                  check=False,
                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0,
                )
              except Exception:
                pass
              st.toast(f"Deleted {out.get('label') or out.get('install_id')}")
              st.rerun()
            except Exception as exc:
              st.error(str(exc))
        with d2:
          if st.button("Cancel", key="del_cancel"):
            st.session_state.pop("pending_delete_install_id", None)
            st.rerun()



# ── Sidebar ───────────────────────────────────────────────────────────
with st.sidebar:
  st.markdown("### Desk")
  auto = st.toggle("Auto-refresh", value=True if st.session_state.desk_mode == "Replay" else False, key="auto_refresh")
  every = st.select_slider("Every (sec)", options=[5, 10, 15, 30], value=5)
  if st.button("Refresh now", use_container_width=True):
    st.rerun()
  st.caption(f"{LIVE_INSTANCE_ID} · :{LIVE_APP_PORT} · magic {LIVE_MAGIC_BASE}")
  if auto:
    st.caption("Auto-refresh cập nhật số liệu — không đổi layout.")

# Full-page refresh only (no fragment): fragments remount cockpit vs tabs and feel like a UI change.
if auto:
  try:
    from streamlit_autorefresh import st_autorefresh  # type: ignore

    st_autorefresh(interval=int(every) * 1000, key="desk_refresh")
  except Exception:
    # Soft fallback: timed full rerun via meta is jarring — skip; user can Refresh now.
    pass

# Top-level nav: Live first · Replay desk · Models/Setup pages
_TOP_NAV = ("Live", "Replay", "Models", "Setup")
if "top_nav" not in st.session_state:
  # migrate old History/Models/Setup section if present
  legacy = st.session_state.get("live_section")
  if legacy in ("Models", "Setup"):
    st.session_state.top_nav = legacy
  elif st.session_state.get("desk_mode") in _TOP_NAV:
    st.session_state.top_nav = st.session_state.desk_mode
  else:
    st.session_state.top_nav = "Live"

nav = st.radio(
  "Nav",
  _TOP_NAV,
  horizontal=True,
  key="top_nav",
  label_visibility="collapsed",
  help="Live = trading · Replay = OOS desk · Models = import/roster · Setup = risk & kỹ thuật",
)

snap: dict = {"journal": {}, "bridge_dirs": []}
journal = {}

if nav == "Live":
  st.session_state.desk_mode = "Live"
  snap = render_live_desk()
  journal = snap.get("journal") or {}
elif nav == "Replay":
  st.session_state.desk_mode = "Replay"
  snap = render_replay_desk()
  journal = snap.get("journal") or {}
elif nav == "Models":
  render_models_page()
else:
  render_setup_page()
