"""EdgeMiner Live — trader desk UI (daily ops first, config second)."""
from __future__ import annotations

import html
import importlib
import inspect
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import streamlit as st

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))


def _reload_stale_live_modules() -> None:
  """Streamlit re-runs app.py but keeps sibling modules in sys.modules."""

  def _missing_sim(fn) -> bool:
    try:
      return "sim" not in inspect.signature(fn).parameters
    except (TypeError, ValueError):
      return True

  touched = False
  import books as bk
  if _missing_sim(bk.bridge_dir):
    importlib.reload(bk)
    touched = True
  import bridge_control as bc
  if _missing_sim(bc.status) or _missing_sim(bc.is_running):
    importlib.reload(bc)
    touched = True
  import deploy_ea as de
  cov_fn = getattr(de, "roster_ea_coverage", None)
  if not hasattr(de, "ensure_live_eas_deployed") or cov_fn is None or _missing_sim(cov_fn):
    importlib.reload(de)
    touched = True
  import live_health as lh
  bound = getattr(lh, "bridge_status", None)
  try:
    lh_src = inspect.getsource(lh)
  except Exception:
    lh_src = ""
  need_lh = (
    touched
    or not hasattr(lh, "live_quote")
    or (bound is not None and _missing_sim(bound))
    or "strategy_mode" not in lh_src
    or "FROZEN_MISSING" not in lh_src
  )
  if need_lh:
    importlib.reload(lh)
    touched = True
  import desk_snapshot as ds
  bound = getattr(ds, "bridge_status", None)
  if (
    touched
    or (bound is not None and _missing_sim(bound))
    or not hasattr(ds, "now_watch_rows")
    or "buy_lines" not in inspect.getsource(ds.now_watch_rows)
    or "short" not in inspect.getsource(ds.now_watch_rows)
    or "day_slots" not in inspect.getsource(ds.now_watch_rows)
    or "day_full" not in inspect.getsource(ds.now_watch_rows)
    or "wait_code" not in inspect.getsource(ds.now_watch_rows)
    or "day_hits" not in inspect.getsource(ds.now_watch_rows)
    or "score_buy" not in inspect.getsource(ds.now_watch_rows)
    or "score_ok" not in inspect.getsource(ds.now_watch_rows)
    or "pa_ok" not in inspect.getsource(ds.now_watch_rows)
    or not hasattr(ds, "inspect_model_label")
    or "period_n" not in inspect.getsource(ds.inspect_model_label)
    or "selected D/W/M/ALL count" not in inspect.getsource(ds.inspect_model_label)
  ):
    importlib.reload(ds)
  import watch_expect as we
  try:
    we_src = inspect.getsource(we)
  except Exception:
    we_src = ""
  if (
    not hasattr(we, "watch_chart_figures")
    or not hasattr(we, "build_watch_figure")
    or not hasattr(we, "explain_watch")
    or not hasattr(we, "model_watch_figure")
    or "watch_chart_figures" not in we_src
    or "model_watch_figure" not in we_src
    or "n_rules" not in we_src
    or "_CHART_BARS" not in we_src
    or "wait_code" not in we_src
    or "_session_pack" not in we_src
    or "hit_times" not in we_src
    or "_add_hit_vlines" not in we_src
    or "exit_time" not in we_src
    or 'type="rect"' not in we_src
    or "win_fill" not in we_src
    or "broker_wall_to_display" not in we_src
    or "DISPLAY_TZ_LABEL" not in we_src
    or "chart_feature_pack" not in we_src
    or "slice_pack_to_period" not in we_src
    or "extra_gate_lines" not in we_src
    or "the BUY/SELL rules ticked" not in we_src
    or "_fire_side" not in we_src
    or "_gap_pack" not in we_src
    or "pa_ok" not in we_src
    or "frozen_missing" not in we_src
    or "_rsi_chase_caps" not in we_src
    or "carry_forward_week_strategy" not in we_src
    or "_schedule.json" not in we_src
  ):
    importlib.reload(we)
  import replay_control as rc
  need_rc = False
  try:
    if "delay_ms" not in inspect.signature(rc.save_oos_prefs).parameters:
      need_rc = True
  except Exception:
    need_rc = True
  if not hasattr(rc, "live_bridge_dirs") or not hasattr(rc, "_assert_live_feed_bridge"):
    need_rc = True
  start_fn = getattr(rc, "_start_ea_simulate", None)
  if start_fn is not None:
    try:
      src = inspect.getsource(start_fn)
      if "ensure_sim_eas_deployed" in src:
        need_rc = True
      if "roster_ea_coverage(sim=" in src:
        need_rc = True
      if "live_ea_needs_history_feed_binary" not in src:
        need_rc = True
      wi = src.find("write_history_feed_control")
      di = src.find("ensure_live_eas_deployed")
      if di >= 0 and wi > di:
        need_rc = True
    except Exception:
      need_rc = True
  hf = getattr(rc, "history_feed_active", None)
  if hf is not None:
    try:
      if "pending" not in inspect.getsource(hf):
        need_rc = True
    except Exception:
      need_rc = True
  if getattr(rc, "HISTORY_FEED_EA_VERSION", (0,)) < (1, 25):
    need_rc = True
  try:
    if '["LIVE_REPLAY_FORCE_REMINE"] = "1" if force else "0"' in inspect.getsource(rc.start_oos_replay):
      need_rc = True
  except Exception:
    need_rc = True
  if need_rc:
    importlib.reload(rc)
  import package_store as ps
  if not hasattr(ps, "rebuild_roster_preserving_sticky"):
    importlib.reload(ps)
  import weekend_preremine as wpr
  if (
    not hasattr(wpr, "build_quality_status_table")
    or not hasattr(wpr, "quality_status_week")
    or "frozen_mode" not in inspect.getsource(wpr.maybe_preremine_engines)
  ):
    importlib.reload(wpr)
  import strategy_mode as sm_mod
  if (
    not hasattr(sm_mod, "frozen_enabled")
    or not hasattr(sm_mod, "carry_forward_week_strategy")
  ):
    importlib.reload(sm_mod)
  import risk_prefs as rp
  need_rp = not hasattr(rp, "journal_risk_metrics")
  if not need_rp:
    try:
      need_rp = "desk_day_total_r" not in inspect.getsource(rp.journal_risk_metrics)
    except Exception:
      need_rp = True
  if need_rp:
    importlib.reload(rp)
    touched = True
  lg_mod = sys.modules.get("loss_guard_ext")
  if lg_mod is not None and not hasattr(lg_mod, "desk_closed_trades"):
    importlib.reload(lg_mod)
  import theme as th
  if (
    not hasattr(th, "progress_bar_html")
    or "import-flash" not in getattr(th, "_SHARED", "")
    or "now-watch" not in getattr(th, "_SHARED", "")
    or "now-rule" not in getattr(th, "_SHARED", "")
    or "now-inspect" not in getattr(th, "_SHARED", "")
    or "now-levels" not in getattr(th, "_SHARED", "")
    or "no-rerun-fade" not in getattr(th, "_SHARED", "")
    or "white-space: normal" not in getattr(th, "_SHARED", "")
    or "now-chip" not in getattr(th, "_SHARED", "")
    or "st-key-now_xf_" not in getattr(th, "_SHARED", "")
    or "0.72rem !important" not in getattr(th, "_SHARED", "")
    or not hasattr(th, "save_now_chart_checks")
    or not hasattr(th, "now_chart_check_id")
    or not hasattr(th, "restore_widget_choice")
  ):
    importlib.reload(th)
  import journal_view as jv
  try:
    jv_src = inspect.getsource(jv)
  except Exception:
    jv_src = ""
  if "_profit_looks_like_r" not in jv_src:
    importlib.reload(jv)


_reload_stale_live_modules()

from bridge_control import is_running as bridge_is_running  # noqa: E402
from bridge_control import start_bridge, status, stop_bridge  # noqa: E402
from desk_snapshot import desk_snapshot, inspect_model_label  # noqa: E402
from live_config import BRIDGE_DIR, INBOX_DIR  # noqa: E402
from journal_view import (  # noqa: E402
  load_recent_fills,
  load_trades_many,
  journal_summary_many,
  stats_by_model_many,
  _trade_r,
  _trade_result,
  PERIOD_LABELS,
  PERIOD_TITLES,
  PERIODS,
)
from magic_allocator import assign_magics  # noqa: E402
from package_store import (  # noqa: E402
  default_roster_from_installed,
  delete_installed,
  list_installed,
  load_roster,
  rebuild_roster_preserving_sticky,
  save_roster,
)
from books import bridge_subdir, group_models_by_book  # noqa: E402
from replay_control import (  # noqa: E402
  load_oos_prefs,
  save_oos_prefs,
  start_oos_replay,
  stop_replay,
)
from safety import disarm_kill_switch  # noqa: E402
from reset_data import reset_live_data  # noqa: E402
from equity_view import render_equity_section  # noqa: E402
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
  progress_bar_html,
  r_class,
)

st.set_page_config(
  page_title="EdgeMiner Live",
  layout="wide",
  initial_sidebar_state="collapsed",
)
inject_theme()

if "desk_mode" not in st.session_state:
  st.session_state.desk_mode = "Live"

# Top-level nav — defined early so sidebar / auto-refresh cannot race ahead of it.
_TOP_NAV = ("Live", "Replay", "Models", "Setup")
LIVE_SECTIONS = ("now", "pipeline", "session")
LIVE_SECTION_LABELS = {
  "now": "Now",
  "pipeline": "Health",
  "session": "Trades",
}


def _wl_text(wins, losses, be=0) -> str:
  s = f"{int(wins or 0)}/{int(losses or 0)}"
  n_be = int(be or 0)
  if n_be:
    s += f" · {n_be} BE"
  return s


def _live_workers_running() -> bool:
  try:
    return bool(bridge_is_running(sim=False))
  except TypeError:
    return bool(bridge_is_running())


def _nav_from_query() -> str | None:
  raw = st.query_params.get("nav") or st.query_params.get("page")
  if isinstance(raw, (list, tuple)):
    raw = raw[0] if raw else None
  raw = str(raw or "").strip()
  return raw if raw in _TOP_NAV else None


def _mark_ui_interact() -> None:
  import time as _time
  st.session_state["_ui_interact_at"] = _time.time()


def _on_top_nav_change() -> None:
  nav = st.session_state.get("top_nav")
  if nav in _TOP_NAV:
    cur = st.query_params.get("nav")
    if isinstance(cur, (list, tuple)):
      cur = cur[0] if cur else None
    if str(cur or "") != nav:
      st.query_params["nav"] = nav
  _mark_ui_interact()


def _seed_top_nav() -> None:
  if "top_nav" in st.session_state and st.session_state.top_nav in _TOP_NAV:
    return
  qp = _nav_from_query()
  legacy = st.session_state.get("live_section")
  if qp:
    st.session_state.top_nav = qp
  elif legacy in ("Models", "Setup"):
    st.session_state.top_nav = legacy
  elif st.session_state.get("desk_mode") in _TOP_NAV:
    st.session_state.top_nav = st.session_state.desk_mode
  else:
    st.session_state.top_nav = "Live"


def _on_live_stats_period_change() -> None:
  from gui.theme import save_ui_prefs

  period = st.session_state.get("live_stats_period")
  if period in PERIODS:
    save_ui_prefs({"live_stats_period": period})
  _mark_ui_interact()


def _seed_live_stats_period() -> None:
  """Restore D/W/M/ALL before the radio mounts.

  Do not skip after the first visit: Streamlit drops ``live_stats_period``
  whenever the radio is off-page (Replay / Models / Setup, or Health).
  Prefs on disk already survive F5; this re-applies them after tab hops.
  """
  from gui.theme import load_ui_prefs, restore_widget_choice

  st.session_state.live_stats_period = restore_widget_choice(
    st.session_state.get("live_stats_period"),
    load_ui_prefs().get("live_stats_period"),
    PERIODS,
    "today",
  )


def _on_live_desk_section_change() -> None:
  from gui.theme import save_ui_prefs

  section = st.session_state.get("live_desk_section")
  if section in LIVE_SECTIONS:
    save_ui_prefs({"live_desk_section": section})
  _mark_ui_interact()


def _seed_live_desk_section() -> None:
  """Restore Now/Health/Trades the same way as D/W/M/ALL after tab hops."""
  from gui.theme import load_ui_prefs, restore_widget_choice

  saved = str(load_ui_prefs().get("live_desk_section") or "now")
  if saved == "control":
    saved = "now"
  st.session_state.live_desk_section = restore_widget_choice(
    st.session_state.get("live_desk_section"),
    saved,
    LIVE_SECTIONS,
    "now",
  )


def _model_label_map(models: list[dict]) -> dict[str, str]:
  out: dict[str, str] = {}
  for m in models:
    mid = str(m.get("model_id") or "")
    if mid:
      out[mid] = str(m.get("label") or mid)
  return out


def _render_replay_live_panels(snap: dict | None = None) -> dict:
  """OOS HistoryFeed progress — results show on the Live desk."""
  snap = snap or desk_snapshot(sim=False)
  replay = snap.get("replay") or {}
  running = bool(replay.get("running"))
  books = replay.get("books") or []

  st.caption(
    f"Updated {snap.get('updated_at')} · "
    f"{'RUNNING' if running else 'Idle'}"
    + (f" · pid {replay.get('pid')}" if replay.get("pid") else "")
  )

  st.markdown(
    '<div class="panel-label" style="margin-top:0.25rem">2 · Progress</div>',
    unsafe_allow_html=True,
  )
  stuck = [
    b for b in books
    if str(b.get("ea_status") or "") in ("pending", "idle")
    and int(b.get("bars_total") or 0) == 0
    and running
  ]
  if stuck:
    st.error(
      "Feed đang kẹt: Python đã ghi sim_control.json nhưng EA trên chart chưa đọc "
      "(ForgeBridgeLive < 1.25 chưa chờ quyết định song song như Live). "
      "Bấm **Restart feed** — app sẽ compile/gắn ForgeBridgeLive 1.25."
    )
  if running or any(int(b.get("bars_done") or 0) for b in books) or books:
    for b in books:
      done = int(b.get("bars_done") or 0)
      total = int(b.get("bars_total") or 0)
      err = str(b.get("error") or "")
      status = str(b.get("ea_status") or "")
      last = str(b.get("last_bar") or "")
      if total > 0:
        pct_i = int(round(100.0 * done / total))
        pct_i = min(max(pct_i, 0), 100)
        if done < total and status not in ("completed", "error", "failed"):
          pct_i = min(pct_i, 99)
      else:
        pct_i = 0
      st.caption(
        f"{b.get('symbol')} {b.get('timeframe')} · {status} · "
        f"{done}/{total} bars ({pct_i}%)"
        + (f" · {last}" if last else "")
        + (f" · {err}" if err else "")
      )
      if total:
        st.html(progress_bar_html(pct_i), width="stretch")
  else:
    st.caption("Chưa có progress — Start feed.")

  st.caption(
    "Replay chỉ bơm nến OOS vào **ForgeBridgeLive** (cùng bridge/worker với Live). "
    "Tab Live nhận tín hiệu và xử lý như thật — không có mode sim riêng. "
    "Khác duy nhất: giá quá khứ + paper fill Bid/Ask (spread từng nến, như Live). "
    "Lệnh còn mở cuối tuần giữ OPEN (không đóng end_range)."
  )
  return snap


def _replay_progress_tick_body() -> None:
  _render_replay_live_panels()


def _run_replay_progress_tick() -> None:
  auto = bool(st.session_state.get("auto_refresh"))
  try:
    every = int(st.session_state.get("auto_refresh_every") or 5)
  except (TypeError, ValueError):
    every = 5
  run_every = float(every) if auto else None
  st.fragment(run_every=run_every)(_replay_progress_tick_body)()


def render_replay_desk() -> dict:
  """Replay desk — EA Simulate (MT5) only: Run + Progress."""
  from datetime import date as _date

  st.session_state.desk_mode = "Replay"
  mode = "ea"

  snap = desk_snapshot(sim=False)
  tone = snap["health_tone"]
  models = snap.get("models") or []
  running = bool((snap.get("replay") or {}).get("running"))

  st.markdown(
    f"""
    <div class="desk-top">
      <div>
        <p class="desk-brand">EdgeMiner Live</p>
        <p class="desk-sub">Replay OOS → Live · {snap.get('subtitle') or 'models'} · {LIVE_INSTANCE_ID}</p>
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
    pill("EA SIM", "ok"),
  ]
  st.markdown(f'<div class="pill-row">{"".join(pills)}</div>', unsafe_allow_html=True)

  st.markdown('<div class="panel-label">1 · Run</div>', unsafe_allow_html=True)
  prefs = load_oos_prefs()
  try:
    d_from = _date.fromisoformat(str(prefs.get("from") or "2023-01-01")[:10])
  except ValueError:
    d_from = _date(2026, 1, 1)
  try:
    d_to = _date.fromisoformat(str(prefs.get("to") or "2026-08-07")[:10])
  except ValueError:
    d_to = _date(2026, 8, 7)

  if "oos_from_date" not in st.session_state:
    st.session_state.oos_from_date = d_from
  if "oos_to_date" not in st.session_state:
    st.session_state.oos_to_date = d_to

  delay_ms = int(prefs.get("delay_ms") or 100)
  if "replay_ea_delay" not in st.session_state:
    st.session_state.replay_ea_delay = delay_ms
  delay_ms = int(st.number_input(
    "EA bar delay (ms)",
    min_value=1,
    max_value=2000,
    step=10,
    key="replay_ea_delay",
    help="Pacing nến HistoryFeed. 100 = 0.1s/bar.",
  ))

  oc1, oc2 = st.columns(2)
  with oc1:
    oos_from = st.date_input("OOS from", key="oos_from_date")
  with oc2:
    oos_to = st.date_input("OOS to", key="oos_to_date")

  ea_ready = True
  ea_online = False
  import platform as _plat
  if not _plat.system().lower().startswith("win"):
    ea_ready = False
    st.warning("OOS HistoryFeed chỉ chạy trên Windows + MT5.")
  else:
    try:
      from deploy_ea import roster_ea_coverage
      import time as _cov_time

      now = _cov_time.time()
      cached = st.session_state.get("_sim_ea_cov")
      if (
        isinstance(cached, tuple)
        and len(cached) == 2
        and now - float(cached[0]) < 8.0
        and isinstance(cached[1], dict)
      ):
        cov = cached[1]
      else:
        cov = roster_ea_coverage(stale_after=180.0)
        st.session_state["_sim_ea_cov"] = (now, cov)
      ea_online = bool(cov.get("all_online"))
      if not ea_online:
        miss = ", ".join(
          f"{m.get('symbol')} {m.get('timeframe')}" for m in (cov.get("missing") or [])
        ) or "—"
        st.info(
          f"Live EA chưa online ({cov.get('n_online') or 0}/{cov.get('n_books') or 0}). "
          f"Start sẽ Deploy ForgeBridgeLive. Missing: {miss}"
        )
    except Exception as _cov_exc:
      st.caption(f"Live EA coverage: {_cov_exc}")

  cur_from, cur_to = str(oos_from), str(oos_to)
  if (
    cur_from != str(prefs.get("from") or "")
    or cur_to != str(prefs.get("to") or "")
    or mode != prefs.get("mode")
    or int(delay_ms) != int(prefs.get("delay_ms") or 100)
  ):
    save_oos_prefs(
      date_from=cur_from,
      date_to=cur_to,
      mode=mode,
      delay_ms=delay_ms,
    )
  if not models:
    st.info("Chưa bật model — mở **Models**, bật On, Save.")

  if running:
    start_label = "Restart feed"
  elif ea_online:
    start_label = "Start feed"
  else:
    start_label = "Deploy Live EA + Start feed"
  start_disabled = bool(not models or not ea_ready)
  start_why = ""
  if not models:
    start_why = "Chưa có model On — mở Models, bật On, Save."
  elif not ea_ready:
    start_why = "OOS HistoryFeed chỉ chạy trên Windows + MT5."
  a1, a2, a3 = st.columns([1.4, 1, 2])
  with a1:
    if st.button(
      start_label,
      type="primary",
      use_container_width=True,
      disabled=start_disabled,
      key="desk_start_replay",
      help=start_why or "Ghi sim_control.json rồi deploy ForgeBridgeLive nếu chart chưa online.",
    ):
      try:
        with st.spinner("Writing HistoryFeed + deploying Live EA if needed…"):
          out = start_oos_replay(
            date_from=str(st.session_state.get("oos_from_date") or load_oos_prefs()["from"]),
            date_to=str(st.session_state.get("oos_to_date") or load_oos_prefs()["to"]),
            mode=mode,
            delay_ms=delay_ms,
            restart=True,
          )
        st.session_state.pop("_sim_ea_cov", None)
        st.toast(
          f"EA Simulate {out.get('from')}→{out.get('to')} · pid {out.get('pid')}"
        )
        st.rerun()
      except Exception as exc:
        import traceback
        st.error(str(exc))
        with st.expander("Traceback"):
          st.code(traceback.format_exc())
    if start_why:
      st.caption(start_why)
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
    hint = "OOS → ForgeBridgeLive → worker Live · kết quả trên tab Live"
    st.caption(f"Window **{oos_from} → {oos_to}** · {hint}")
  try:
    from strategy_mode import strategy_mode as _sm
    sm_now = _sm()
  except Exception:
    sm_now = "weekly"
  st.caption(
    "Replay bơm nến OOS vào đúng EA/worker/journal Live. "
    "Tab Live không phân biệt replay — paper fill chỉ vì giá quá khứ. "
    f"Remine theo **Setup → Quality** (đang **{sm_now}**), giống Live."
  )

  _run_replay_progress_tick()
  return snap


def _render_remine_status_table() -> None:
  """Current-week remine freeze for enabled models (Setup Quality + Live)."""
  try:
    from weekend_preremine import build_quality_status_table
    data = build_quality_status_table()
  except Exception as exc:
    st.warning(f"Remine status unavailable: {exc}")
    return
  rows = data.get("rows") or []
  week = data.get("week") or "—"
  mode = data.get("mode") or "trading"
  if mode == "preremine":
    st.caption(
      f"Weekend pre-remine · bảng = tuần tới **{week}** "
      f"(tuần đang trade {data.get('trade_week')})"
    )
  else:
    st.caption(
      f"Tuần đang trade · **{week}**  ·  "
      f"pre-remine tuần tới {data.get('next_week')} (T6 ≥18h / T7 / CN)"
    )
  try:
    from strategy_mode import frozen_enabled
    if frozen_enabled():
      st.caption("Strategy mode **frozen** — không remine / không weekend pre-remine.")
  except Exception:
    pass
  if not rows:
    st.caption("Chưa có model On — bật ở Models.")
    return
  ready_n = int(data.get("ready_n") or 0)
  title = "Tuần hiện tại" if mode == "trading" else "Pre-remine tuần tới"
  st.caption(
    f"{title} · {ready_n}/{len(rows)} READY for week {week} · "
    "n/PF/R = train metrics sau remine · base_PF = package baseline · gate = PASS/FAIL/—"
  )
  st.dataframe(
    rows,
    use_container_width=True,
    hide_index=True,
    height=min(420, 42 + 35 * len(rows)),
    column_config={
      "model": st.column_config.TextColumn("model", width="medium"),
      "reason": st.column_config.TextColumn("reason", width="large"),
    },
  )


def _health_flag_html(level: str, text: str) -> str:
  lv = level if level in ("ok", "warn", "danger", "muted") else "muted"
  return f'<span class="health-flag health-flag-{lv}">{text}</span>'


def _json_file(path: Path) -> dict:
  if not path.is_file():
    return {}
  try:
    data = json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return {}
  return data if isinstance(data, dict) else {}


def _book_live_quote(book: dict) -> dict:
  """Tick bid/spread for health titles — read EA files, not snapshot fields."""
  from live_health import live_quote

  bdir = Path(str(book.get("bridge_dir") or ""))
  conn = _json_file(bdir / "connection.json") if bdir.is_dir() else {}
  bar = _json_file(bdir / "bar.json") if bdir.is_dir() else {}
  q = live_quote(conn, bar)
  if q.get("spread_text") and q.get("spread_text") != "—":
    return q
  snap = live_quote(
    {"bid": book.get("bid"), "ask": book.get("ask"), "spread_points": book.get("spread_points")},
    {"digits": book.get("digits"), "point": book.get("point")},
  )
  if snap.get("spread_text") and snap.get("spread_text") != "—":
    return snap
  return q


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
    st.caption("EA Simulate / Replay — worker sim + HistoryFeed (không đụng lệnh Live).")

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
    book_lv = book.get("level") or "muted"
    flags = " · ".join(book.get("flags") or [])
    if not flags:
      # Never paint "OK" in warn/danger colors — that mismatch looked broken.
      flags = "OK" if book_lv == "ok" else str(book_lv).upper()
    worker = (
      f"pid {book.get('worker_pid')}" if book.get("worker_alive") else "worker down"
    )
    quote = _book_live_quote(book)
    spr = quote.get("spread_text") or book.get("spread_text") or "—"
    bid = quote.get("bid")
    if bid is None:
      bid = book.get("bid")
    bid_s = f"{float(bid):.5f}".rstrip("0").rstrip(".") if bid is not None else ""
    title_bits = f"{book.get('symbol')} {book.get('timeframe')} · spr {spr}"
    if bid_s:
      title_bits = f"{book.get('symbol')} {book.get('timeframe')} · {bid_s} spr {spr}"
    head_meta = (
      f"EA {book.get('ea_state')} {book.get('ea_age')} · "
      f"tick {book.get('tick_age') or '—'} · "
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
        f"<div class='model-meta'>magic {m.get('magic') or '—'} · {m.get('reason') or ''}"
        f"{(' · src=' + str(m.get('strategy_source'))) if m.get('strategy_source') else ''}"
        f"</div></div>"
        f"<div>{m.get('action') or '—'}</div>"
        f"<div class='model-meta'>dec {m.get('decision_age')} · bar {m.get('bar_time') or '—'}</div>"
        f"{_health_flag_html(m.get('level') or 'muted', mflags)}"
        "</div>"
      )
    st.markdown(
      f"""
      <div class="health-book">
        <div class="health-book-head">
          <div class="health-book-title">{title_bits} · {book.get('n_models')} model(s)
            {_health_flag_html(book_lv, flags)}</div>
          <div class="health-book-meta">{head_meta}</div>
        </div>
        {''.join(models_html)}
      </div>
      """,
      unsafe_allow_html=True,
    )
  st.caption(
    "TIMEOUT/LAG = decision chưa khớp nến EA · EA_STALE = connection.json không ghi (EA/chart tắt) · "
    "MARKET_QUIET/TICK_STALE = EA online nhưng broker không có tick mới (cuối tuần) · "
    "WORKER_STALE = App không cập nhật status · GATE_FAIL = remine bị chặn · "
    "RISK_CAP = vượt trần risk đồng thời · REMINE = remine khi gate đang bật · "
    "FROZEN = Setup giữ genome, không remine tuần · FROZEN_MISS = chưa có freeze."
  )
  if health.get("strategy_mode") == "frozen":
    st.caption("Strategy mode: **frozen** — không remine theo tuần (Setup → Quality).")
  rg = health.get("remine_gate_last") or {}
  if rg:
    ok = rg.get("ok")
    st.caption(
      f"Remine gate last: {'PASS' if ok else 'FAIL'} · "
      f"{rg.get('model_id')} · week {rg.get('week_start')} · "
      f"PF={(rg.get('metrics') or {}).get('profit_factor')} · "
      f"n={(rg.get('metrics') or {}).get('n_trades')}"
      + (f" · {'; '.join(rg.get('reasons') or [])}" if rg.get('reasons') else "")
    )
  rc = health.get("risk_cap_last") or {}
  if rc:
    st.caption(
      f"Risk cap last: {'OK' if rc.get('ok') else 'BLOCK'} · "
      f"{rc.get('model_id')} · proj={rc.get('projected_risk_pct')}% · "
      f"{'; '.join(rc.get('reasons') or []) or '—'}"
    )


def _period_label(key: str) -> str:
  return PERIOD_LABELS.get(key, key)


def _now_chip_cls(ok) -> str:
  return "now-hit" if ok else "now-miss"


def _now_watch_badge(rows: list[dict]) -> str:
  n_fire = sum(1 for r in rows if str(r.get("action") or "").upper() in ("BUY", "SELL", "LONG", "SHORT"))
  n_hold = sum(1 for r in rows if str(r.get("action") or "").upper() == "HOLD")
  if n_fire:
    return f"{n_fire} LIVE"
  if n_hold:
    return f"{n_hold} HOLD"
  if rows:
    return "ALL FLAT"
  return "WAIT"


def _now_rules_cell(lines: list, gate: str, ready: bool) -> str:
  gate_cls = "now-hit" if ready else "now-miss"
  parts = [f'<div class="now-gate {gate_cls}">{html.escape(str(gate or "—"))}</div>']
  if not lines:
    parts.append('<span class="now-rule now-miss">—</span>')
    return "".join(parts)
  for line in lines:
    cls = "now-hit" if line.get("hit") else "now-miss"
    parts.append(
      f'<span class="now-rule {cls}">{html.escape(str(line.get("text") or "—"))}</span>'
    )
  return "".join(parts)


def _render_now_side_rules(
  lines: list,
  *,
  side: str,
  gate: str,
  ready: bool,
  key_prefix: str,
  saved: dict[str, bool] | None = None,
) -> tuple[list[tuple], dict[str, bool]]:
  """BUY/SELL rule list with checkboxes; ticked rules go on the chart."""
  from gui.theme import now_chart_check_id

  saved = saved or {}
  gate_cls = "now-hit" if ready else "now-miss"
  title = "BUY" if side == "B" else "SELL"
  st.markdown(
    f'<div class="now-inspect-k">{title}</div>'
    f'<div class="now-gate {gate_cls}">{html.escape(str(gate or "—"))}</div>',
    unsafe_allow_html=True,
  )
  picked: list[tuple] = []
  checks: dict[str, bool] = {}
  if not lines:
    st.markdown('<span class="now-rule now-miss">—</span>', unsafe_allow_html=True)
    return picked, checks
  for i, line in enumerate(lines):
    feat = str(line.get("feat_key") or "")
    try:
      thr = float(line.get("thr")) if line.get("thr") is not None else 0.0
    except (TypeError, ValueError):
      thr = 0.0
    ckey = f"{key_prefix}_{side}_{i}_{feat}"
    cid = now_chart_check_id(side, feat, thr)
    if ckey not in st.session_state:
      st.session_state[ckey] = bool(saved[cid]) if cid in saved else (i == 0)
    text = str(line.get("text") or "—")
    mark = "hit" if line.get("hit") else "miss"
    on = bool(st.checkbox(f"{mark}  {text}", key=ckey))
    checks[cid] = on
    if on and feat:
      picked.append((feat, side, thr))
  return picked, checks


def _watch_book_groups(rows: list[dict]) -> list[tuple[str, list[dict]]]:
  groups: dict[str, list[dict]] = {}
  order: list[str] = []
  live = {"BUY", "SELL", "LONG", "SHORT", "HOLD"}
  for r in rows:
    key = f"{r.get('symbol') or '—'} {r.get('timeframe') or ''}".strip()
    if key not in groups:
      groups[key] = []
      order.append(key)
    groups[key].append(r)
  order.sort(key=lambda k: (
    0 if any(str(x.get("action") or "").upper() in live for x in groups[k]) else 1,
    k,
  ))
  return [(k, groups[k]) for k in order]


def _watch_model_label(row: dict) -> str:
  return str(row.get("model") or row.get("short") or row.get("model_id") or "—")


def _watch_radio_label(row: dict, *, period: str | None = None) -> str:
  name = inspect_model_label(row, period=period)
  act = str(row.get("action") or "").upper()
  if act in ("BUY", "SELL", "HOLD"):
    return f"{name} · {act}"
  return name


def _render_now_watch(rows: list[dict]) -> None:
  badge = _now_watch_badge(rows)
  live_n = sum(1 for r in rows if str(r.get("action") or "").upper() in ("BUY", "SELL", "LONG", "SHORT"))
  tone = "long" if live_n else ("flat" if rows else "unknown")
  if any(str(r.get("action") or "").upper() in ("SELL", "SHORT") for r in rows) and live_n:
    if not any(str(r.get("action") or "").upper() in ("BUY", "LONG") for r in rows):
      tone = "short"
  body = []
  for r in rows:
    act = html.escape(str(r.get("action") or "—"))
    model = html.escape(_watch_model_label(r))
    row_tone = html.escape(str(r.get("tone") or "unknown"))
    buy_cls = "now-hit" if r.get("buy_ready") else "now-miss"
    sell_cls = "now-hit" if r.get("sell_ready") else "now-miss"
    buy = html.escape(str(r.get("buy_gate") or "—"))
    sell = html.escape(str(r.get("sell_gate") or "—"))
    wait_cls = "now-hit" if r.get("wait_ok") else "now-miss"
    wait = html.escape(str(r.get("wait") or "—"))
    slots_cls = "now-miss" if r.get("day_full") else "now-hit"
    slots = html.escape(str(r.get("day_slots") or "—"))
    body.append(
      f'<tr class="now-row now-row-{row_tone}">'
      f'<td class="now-act">{act}</td>'
      f'<td class="now-model">{model}</td>'
      f'<td class="now-gate-cell"><span class="{buy_cls}">{buy}</span></td>'
      f'<td class="now-gate-cell"><span class="{sell_cls}">{sell}</span></td>'
      f'<td class="now-wait-cell"><span class="{wait_cls}">{wait}</span></td>'
      f'<td class="now-gate-cell"><span class="{slots_cls}">{slots}</span></td>'
      f"</tr>"
    )
  table = (
    '<table class="now-watch now-watch-compact"><thead><tr>'
    "<th>Act</th><th>Model</th><th>BUY</th><th>SELL</th><th>Wait</th><th>Day</th>"
    "</tr></thead><tbody>"
    + ("".join(body) or '<tr><td colspan="6" class="now-expect">Waiting for first decision…</td></tr>')
    + "</tbody></table>"
  )
  st.markdown(
    f"""
    <div class="panel signal-panel now-watch-panel signal-{tone}">
      <div class="signal-head">
        <div class="panel-label">Watch</div>
        <span class="signal-badge">{html.escape(badge)}</span>
      </div>
      {table}
    </div>
    """,
    unsafe_allow_html=True,
  )


def _render_now_inspect(rows: list[dict], health_detail: dict, *, period: str = "today") -> None:
  groups = _watch_book_groups(rows)
  if not groups:
    return
  book_map = {}
  for book in (health_detail or {}).get("books") or []:
    key = f"{book.get('symbol') or ''} {book.get('timeframe') or ''}".strip()
    if key:
      book_map[key] = book
  st.markdown(
    '<div class="panel-label" style="margin-top:0.2rem">Model</div>',
    unsafe_allow_html=True,
  )
  tabs = st.tabs([g[0] for g in groups])
  live = {"BUY", "SELL", "LONG", "SHORT", "HOLD"}
  for tab, (book_key, book_rows) in zip(tabs, groups):
    with tab:
      ids = [str(r.get("model_id") or "") for r in book_rows if r.get("model_id")]
      by_id = {str(r.get("model_id") or ""): r for r in book_rows}
      if not ids:
        st.caption("No models.")
        continue
      book = book_map.get(book_key)
      trades: list[dict] = []
      bdir = Path(str((book or {}).get("bridge_dir") or "")) if (book or {}).get("bridge_dir") else None
      if bdir is not None:
        try:
          from journal_view import load_trades
          trades = list(load_trades(bdir))
        except Exception:
          trades = []
      from watch_expect import period_fill_marks
      labeled: dict[str, dict] = {}
      labels: dict[str, str] = {}
      for mid in ids:
        counts: dict[str, int] = {}
        hits_by: dict[str, list] = {}
        for p in ("today", "week", "month", "all"):
          hits_p = period_fill_marks(trades, model_id=mid, period=p)
          hits_by[p] = hits_p
          counts[p] = len(hits_p)
        labeled[mid] = {
          **(by_id.get(mid) or {}),
          "period": period,
          "period_n": counts.get(str(period).lower(), 0),
          "period_counts": counts,
          "period_hits": hits_by.get(str(period).lower(), []),
        }
        labels[mid] = _watch_radio_label(labeled[mid], period=period)
      default = ids[0]
      for mid in ids:
        if str((by_id[mid] or {}).get("action") or "").upper() in live:
          default = mid
          break
      slug = re.sub(r"[^A-Za-z0-9_]+", "_", book_key)
      wkey = f"now_model_{slug}"
      from gui.theme import (
        load_now_chart_checks,
        load_now_picked_model,
        save_now_chart_checks,
        save_now_picked_model,
      )
      saved_mid = load_now_picked_model(book_key)
      if st.session_state.get(wkey) not in ids:
        st.session_state[wkey] = saved_mid if saved_mid in ids else default
      picked = st.radio(
        "Model",
        ids,
        format_func=lambda i, _l=labels: _l.get(i, i),
        horizontal=True,
        key=wkey,
        label_visibility="collapsed",
      )
      if str(picked) != saved_mid:
        save_now_picked_model(book_key, picked)
      row = labeled.get(str(picked)) or by_id.get(str(picked)) or book_rows[0]
      why = html.escape(str(row.get("why") or row.get("reason") or "—"))
      act = html.escape(str(row.get("action") or "—"))
      name = html.escape(inspect_model_label(row, period=period))
      sess_cls = "now-hit" if row.get("session_ok") else "now-miss"
      sess = html.escape(str(row.get("session_gate") or "—"))
      chase_on = bool(row.get("chase_on"))
      chase_cls = "now-miss" if row.get("chase_block") else "now-hit"
      chase_lab = "Chase" if row.get("chase_block") else "Chase ok"
      score_cls = _now_chip_cls(bool(row.get("score_ok")))
      ml_cls = _now_chip_cls(bool(row.get("ml_ok")))
      gap_cls = _now_chip_cls(bool(row.get("gap_ok")) if row.get("gap_on") else True)
      rsi_cls = _now_chip_cls(bool(row.get("rsi_ok")))
      htf_cls = _now_chip_cls(bool(row.get("htf_ok")))
      pa_cls = _now_chip_cls(bool(row.get("pa_ok")))
      chase_chip = f'<span class="now-chip {chase_cls}">{chase_lab}</span>' if chase_on else ""
      score_chip = (
        f'<span class="now-chip {score_cls}">Score {html.escape(str(row.get("score_buy") or "—"))}'
        f' · {html.escape(str(row.get("score_sell") or "—"))}</span>'
      )
      ml_chip = (
        f'<span class="now-chip {ml_cls}">ML {html.escape(str(row.get("ml_buy") or "—"))}'
        f' · {html.escape(str(row.get("ml_sell") or "—"))}</span>'
      )
      gap_chip = (
        f'<span class="now-chip {gap_cls}">Gap {html.escape(str(row.get("gap") or "—"))}</span>'
        if row.get("gap_on") else ""
      )
      rsi_chip = f'<span class="now-chip {rsi_cls}">{html.escape(str(row.get("rsi_text") or "RSI —"))}</span>'
      htf_chip = f'<span class="now-chip {htf_cls}">{html.escape(str(row.get("htf_text") or "HTF —"))}</span>'
      pa_chip = (
        f'<span class="now-chip {pa_cls}">{html.escape(str(row.get("pa_buy") or "PA↑ —"))}'
        f' · {html.escape(str(row.get("pa_sell") or "PA↓ —"))}</span>'
      )
      st.markdown(
        f"""
        <div class="now-inspect">
          <div class="now-inspect-head">
            <span class="now-act now-row-{html.escape(str(row.get('tone') or 'flat'))}">{act}</span>
            <span class="now-model">{name}</span>
            <span class="now-inspect-why">{why}</span>
          </div>
          <div class="now-extra">
            <span class="now-chip {sess_cls}">Sess {sess}</span>
            {chase_chip}
            {rsi_chip}
            {score_chip}
            {ml_chip}
            {gap_chip}
            {htf_chip}
            {pa_chip}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
      )
      rule_prefix = f"now_xf_{slug}_{picked}"
      saved_checks = load_now_chart_checks(str(picked))
      buy_col, sell_col = st.columns(2)
      with buy_col:
        buy_sel, buy_map = _render_now_side_rules(
          list(row.get("buy_lines") or []),
          side="B",
          gate=str(row.get("buy_gate") or "—"),
          ready=bool(row.get("buy_ready")),
          key_prefix=rule_prefix,
          saved=saved_checks,
        )
      with sell_col:
        sell_sel, sell_map = _render_now_side_rules(
          list(row.get("sell_lines") or []),
          side="S",
          gate=str(row.get("sell_gate") or "—"),
          ready=bool(row.get("sell_ready")),
          key_prefix=rule_prefix,
          saved=saved_checks,
        )
      chart_selected = list(buy_sel) + list(sell_sel)
      merged_checks = {**buy_map, **sell_map}
      if merged_checks != saved_checks:
        save_now_chart_checks(str(picked), merged_checks)
      chart_err = ""
      try:
        from watch_expect import model_watch_figure
        fig = model_watch_figure(
          model_id=str(row.get("model_id") or ""),
          book=book_map.get(book_key),
          title="",
          period=period,
          hit_times=list(row.get("period_hits") or []),
          selected=chart_selected,
        )
      except Exception as exc:
        fig = None
        chart_err = str(exc)
      if fig is not None:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption(
          f"Chấm = mở · nét đứt = đóng · xanh = thắng · đỏ = thua. "
          f"Giờ VN (UTC+7) · {PERIOD_LABELS.get(period, period)}. Session 7–20 theo broker."
        )
      else:
        st.caption(
          chart_err
          or "Chưa vẽ được chỉ số — cần genome (schedule / live_weeks) và bars.json từ worker."
        )


def _render_live_live_panels(*, period: str, section: str = "now") -> dict:
  """Selected Live tab — ticked by fragment; radio stays outside."""
  from desk_snapshot import _bridge_dirs_for_enabled, book_models, now_watch_rows

  if period not in PERIODS:
    period = "today"
  if section not in LIVE_SECTIONS:
    section = "now"
  snap = desk_snapshot(sim=False)
  health_detail = snap.get("health_detail") or {}
  models = snap.get("models") or []
  bdirs = _bridge_dirs_for_enabled(book_models(), sim=False)
  if not bdirs:
    bdirs = [Path(p) for p in (snap.get("bridge_dirs") or [])] or [BRIDGE_DIR]

  st.caption(f"Updated {snap.get('updated_at')}")
  if section == "pipeline":
    _render_health_panel(health_detail, sim=False)
    return snap
  session = journal_summary_many(bdirs, period=period)
  if section == "session":
    _render_live_session_body(
      snap, period=period, bdirs=bdirs, session=session,
    )
    return snap

  watch_rows = now_watch_rows(snap)
  left, right = st.columns([2.2, 1])
  with left:
    _render_now_watch(watch_rows)
  with right:
    period_r = float(session.get("total_r") or 0.0)
    wr = session.get("win_rate_pct")
    wr_s = f"{wr}%" if wr is not None else "—"
    n_closed = int(session.get("n_closed") or 0)
    n_open = len(snap.get("open_trades") or [])
    wins = int(session.get("wins") or 0)
    losses = int(session.get("losses") or 0)
    period_title = PERIOD_TITLES.get(period, PERIOD_LABELS.get(period, period))
    st.markdown(
      f"""
      <div class="panel session-panel">
        <div class="panel-label">Session · {period_title}</div>
        <div class="stat-grid">
          <div class="stat-cell">
            <div class="stat-k">Closed</div>
            <div class="stat-v neutral">{n_closed}</div>
          </div>
          <div class="stat-cell">
            <div class="stat-k">Total R</div>
            <div class="stat-v {r_class(period_r)}">{period_r:+.2f}</div>
          </div>
          <div class="stat-cell">
            <div class="stat-k">Win rate</div>
            <div class="stat-v neutral">{wr_s}</div>
          </div>
          <div class="stat-cell">
            <div class="stat-k">W/L</div>
            <div class="stat-v neutral">{_wl_text(wins, losses, session.get("be"))}</div>
          </div>
        </div>
      </div>
      """,
      unsafe_allow_html=True,
    )
    if n_open:
      st.caption(f"Đang mở {n_open} vị thế.")

  _render_now_inspect(watch_rows, health_detail, period=period)

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

  return snap


def _render_live_session_body(snap: dict, *, period: str, bdirs: list, session: dict) -> None:
  from journal_view import filter_trades_by_period

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
  c1.metric("Closed", session.get("n_closed") or 0)
  c2.metric("Total R", f"{float(session.get('total_r') or 0):+.3f}")
  c3.metric("WR%", session.get("win_rate_pct") if session.get("win_rate_pct") is not None else "—")
  c4.metric("W/L", _wl_text(session.get("wins"), session.get("losses"), session.get("be")))

  if model_table:
    st.dataframe(model_table, use_container_width=True, hide_index=True)

  eq = render_equity_section(trades, period=period, parity_books=None)
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
      rows_t = []
      for t in (trades[-80:] if keys else []):
        row = {k: t.get(k) for k in keys}
        if "r" in row:
          row["r"] = _trade_r(t)
        if "result" in row:
          row["result"] = _trade_result(t)
        rows_t.append(row)
      if not keys:
        rows_t = trades[-80:]
      st.dataframe(rows_t, use_container_width=True, hide_index=True)
    else:
      st.caption("Chưa có trade — đợi EA đóng lệnh.")
    if fills:
      st.caption("Raw fills")
      st.dataframe(fills, use_container_width=True, hide_index=True)


def _live_now_tick_body() -> None:
  period = st.session_state.get("live_stats_period") or "today"
  section = st.session_state.get("live_desk_section") or "now"
  _render_live_live_panels(period=str(period), section=str(section))


def _run_live_now_tick() -> None:
  """Native Streamlit fragment tick — streamlit_autorefresh is not installed."""
  auto = bool(st.session_state.get("auto_refresh"))
  try:
    every = int(st.session_state.get("auto_refresh_every") or 5)
  except (TypeError, ValueError):
    every = 5
  run_every = float(every) if auto else None
  st.fragment(run_every=run_every)(_live_now_tick_body)()


def render_live_desk() -> dict:
  """Live desk — tabs: Now · Health · Trades."""
  st.session_state.desk_mode = "Live"
  _seed_live_stats_period()
  _seed_live_desk_section()

  snap = desk_snapshot(sim=False)
  tone = snap["health_tone"]
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

  if st.session_state.get("live_desk_section") not in LIVE_SECTIONS:
    st.session_state.live_desk_section = "now"
  st.radio(
    "Live section",
    options=list(LIVE_SECTIONS),
    format_func=lambda s: LIVE_SECTION_LABELS.get(s, s),
    horizontal=True,
    key="live_desk_section",
    label_visibility="collapsed",
    on_change=_on_live_desk_section_change,
  )
  section = st.session_state.get("live_desk_section") or "now"
  if section not in LIVE_SECTIONS:
    section = "now"

  if section == "now":
    _render_live_control(snap)
  if section in ("now", "session"):
    st.radio(
      "Session period",
      options=list(PERIODS),
      format_func=_period_label,
      horizontal=True,
      key="live_stats_period",
      label_visibility="collapsed",
      on_change=_on_live_stats_period_change,
    )
  _run_live_now_tick()
  return snap


def _render_live_control(snap: dict) -> None:
  models = snap.get("models") or []
  running = bool(snap.get("bridge_running"))
  if not models:
    st.info("Chưa bật model — mở **Models**, bật On, Save.")

  a1, a2 = st.columns([1.3, 1])
  with a1:
    mt5_up = True
    ea_fresh = True
    if os.name == "nt":
      try:
        from deploy_ea import is_mt5_running, roster_ea_coverage
        mt5_up = bool(is_mt5_running())
        ea_fresh = bool(roster_ea_coverage(stale_after=45.0).get("all_online"))
      except Exception:
        mt5_up = True
        ea_fresh = True
    need_ea_deploy = bool(os.name == "nt" and not ea_fresh)
    # Allow Start when MT5 is down, or Deploy EA when workers are up but heartbeat is stale.
    start_disabled = bool(
      not models or (running and mt5_up and not need_ea_deploy)
    )
    start_why = ""
    if running and not mt5_up:
      start_why = "MT5 đã tắt — bấm Start để mở lại terminal (+ deploy nếu cần)."
    elif running and need_ea_deploy:
      start_why = "Worker đang chạy nhưng EA không heartbeat — bấm để attach lại ForgeBridgeLive."
    elif not models:
      start_why = "Chưa có model On — mở Models, bật On, Save."
    if not mt5_up and os.name == "nt":
      st.warning("XM MT5 không chạy — Start sẽ mở lại terminal64.")
    elif running and need_ea_deploy:
      st.warning("EA chưa online trên chart — Start bị skip deploy vì heartbeat cũ. Bấm Deploy EA.")
    if running and mt5_up and need_ea_deploy:
      start_label = "Deploy EA"
    elif mt5_up or not running:
      start_label = "Start trading"
    else:
      start_label = "Mở lại MT5 + Start"
    if st.button(
      start_label,
      type="primary",
      use_container_width=True,
      disabled=start_disabled,
      key="desk_start",
      help=start_why or "Deploy EA (nếu thiếu) rồi start bridge workers.",
    ):
      try:
        with st.spinner(
          "Start Live: check packages/OHLC → MT5/EA → workers "
          "(không remine lúc Start; remine trên nến đầu)…"
        ):
          if running and mt5_up and need_ea_deploy:
            from deploy_ea import ensure_live_eas_deployed
            dep = ensure_live_eas_deployed(
              force=True, wait_online=True, wait_sec=60.0, stale_after=45.0,
            )
            out = {"n_workers": "kept", "deploy": dep, "pid": "—"}
          elif running and not mt5_up:
            # Workers still up but terminal closed — reopen MT5 without full stop first.
            from deploy_ea import ensure_live_eas_deployed, ensure_mt5_running
            mt5 = ensure_mt5_running(wait_sec=12.0)
            if not mt5.get("ok"):
              raise RuntimeError(
                "Không mở lại được XM MT5.\n"
                f"{mt5.get('error') or mt5.get('reason') or ''}"
              )
            dep = ensure_live_eas_deployed(
              force=False, wait_online=True, wait_sec=45.0, stale_after=45.0,
            )
            out = {"n_workers": "kept", "deploy": dep, "pid": "—"}
            if mt5.get("started"):
              st.toast("XM MT5 đã mở lại")
          else:
            try:
              disarm_kill_switch()
            except Exception:
              pass
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
  st.caption("Đóng lệnh: dùng MT5. Stop chỉ tắt worker, không flatten.")


def render_setup_page() -> None:
  """Setup tabs: Risk · Quality · System."""
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
  st.caption("Risk = mất tiền · Quality = strategy/remine · System = EA & wipe")

  tab_risk, tab_quality, tab_system = st.tabs(
    ["Risk", "Quality", "System"]
  )

  # ── Risk: loss guard + concurrent cap ───────────────────────────────
  with tab_risk:
    st.markdown('<div class="panel-label">1 · Loss guard</div>', unsafe_allow_html=True)
    st.caption(
      "Max DD ngày/tuần tính từng model (chạm → FLAT đúng model đó). "
      "Max −R/ngày = tổng R hôm nay mọi model trên desk (chạm → FLAT tất cả). "
      "0 = tắt ngưỡng đó. Clear trip gỡ halt."
    )
    prefs = load_risk_prefs()
    snap_r = risk_status_snapshot()
    if snap_r.get("tripped"):
      book_bit = f"{str(snap_r.get('tripped_book') or '').replace('_', ' ').upper()} · " if snap_r.get("tripped_book") else ""
      halted_bit = ""
      halted = snap_r.get("halted_models") or []
      if halted:
        halted_bit = f"models {', '.join(str(x) for x in halted[:4])} · "
      st.error(
        f"TRIPPED · {book_bit}{halted_bit}{snap_r.get('tripped_reason') or 'risk guard'} "
        f"· {snap_r.get('tripped_at') or ''}"
      )
      if st.button("Clear trip (gỡ halt, worker tiếp tục)", key="clear_risk_trip"):
        clear_loss_guard_trip()
        st.toast("Đã gỡ halt trên worker — refresh nếu Pipeline còn ISSUES")
        st.rerun()

    en = st.toggle("Enable risk guard", value=bool(prefs.get("loss_guard_enabled", True)), key="risk_en")
    r1, r2, r3 = st.columns(3)
    with r1:
      day_dd = st.number_input(
        "Max DD ngày / model (R)", min_value=0.0, max_value=100.0,
        value=float(prefs.get("loss_guard_max_day_dd_r") or 0), step=0.5, key="risk_day_dd",
        help="Peak-to-trough DD trong ngày của từng model ≥ ngưỡng → FLAT model đó",
      )
    with r2:
      week_dd = st.number_input(
        "Max DD tuần / model (R)", min_value=0.0, max_value=200.0,
        value=float(prefs.get("loss_guard_max_week_dd_r") or 0), step=0.5, key="risk_week_dd",
        help="Peak-to-trough DD trong tuần của từng model ≥ ngưỡng → FLAT model đó",
      )
    with r3:
      day_loss = st.number_input(
        "Max −R / ngày (tổng model)", min_value=0.0, max_value=100.0,
        value=float(prefs.get("loss_guard_max_day_loss_r") or 0), step=0.5, key="risk_day_loss",
        help="Tổng R hôm nay mọi model ≤ −ngưỡng → FLAT tất cả (0=tắt)",
      )

    if st.button("Save loss guard", type="primary", key="save_risk_limits"):
      save_risk_prefs(
        loss_guard_enabled=bool(en),
        loss_guard_max_day_dd_r=float(day_dd),
        loss_guard_max_week_dd_r=float(week_dd),
        loss_guard_max_day_loss_r=float(day_loss),
        loss_guard_max_week_loss_r=0.0,
        loss_guard_max_day=0,
        loss_guard_max_week=0,
      )
      try:
        from bridge_control import save_config
        save_config(
          loss_guard_enabled=bool(en),
          loss_guard_max_day_dd_r=float(day_dd),
          loss_guard_max_week_dd_r=float(week_dd),
          loss_guard_max_day_loss_r=float(day_loss),
          loss_guard_max_week_loss_r=0.0,
          loss_guard_max_day=0,
          loss_guard_max_week=0,
        )
      except Exception:
        pass
      st.toast("Loss guard saved — đã đẩy xuống worker")
      st.rerun()

    st.markdown('<div class="panel-label" style="margin-top:0.75rem">2 · Concurrent risk cap</div>', unsafe_allow_html=True)
    st.caption(
      "Giới hạn tổng risk đang mở + SIGNAL chờ fill trên toàn portfolio "
      "(mỗi model vẫn chỉ 1 lệnh). Vượt trần → FLAT reason=risk_cap. "
      "Tắt: env LIVE_RISK_CAP=0."
    )
    try:
      from risk_cap import (
        collect_exposure,
        load_last_alert as load_rc_last,
        load_prefs as load_rc_prefs,
        save_prefs as save_rc_prefs,
      )
      rc = load_rc_prefs()
      last_rc = load_rc_last()
      rc_en = st.toggle("Enable concurrent risk cap", value=bool(rc.get("enabled", True)), key="rc_en")
      c1, c2, c3 = st.columns(3)
      with c1:
        rc_max_r = st.number_input(
          "Max open risk % (sum)", min_value=0.0, max_value=50.0,
          value=float(rc.get("max_open_risk_pct") or 3.0), step=0.5, key="rc_max_r",
        )
      with c2:
        rc_max_n = st.number_input(
          "Max open positions", min_value=0, max_value=50,
          value=int(rc.get("max_open_positions") or 4), key="rc_max_n",
        )
      with c3:
        rc_age = st.number_input(
          "Pending signal max age (s)", min_value=60, max_value=7200,
          value=int(rc.get("pending_max_age_sec") or 900), step=60, key="rc_age",
        )
      rc_pend = st.checkbox(
        "Count pending BUY/SELL as reserved risk",
        value=bool(rc.get("include_pending_signals", True)),
        key="rc_pend",
      )
      if st.button("Save risk cap", key="rc_save"):
        save_rc_prefs({
          "enabled": bool(rc_en),
          "max_open_risk_pct": float(rc_max_r),
          "max_open_positions": int(rc_max_n),
          "pending_max_age_sec": int(rc_age),
          "include_pending_signals": bool(rc_pend),
        })
        st.toast("Risk cap saved")
        st.rerun()
      try:
        exp = collect_exposure(sim=False)
        st.caption(
          f"Now (live bridges): open={exp.get('n_open')} "
          f"({exp.get('open_risk_pct')}%) · pending={exp.get('n_pending')} "
          f"({exp.get('pending_risk_pct')}%) · total={exp.get('total_risk_pct')}%"
        )
      except Exception as exp_exc:
        st.caption(f"Exposure snapshot unavailable: {exp_exc}")
      if last_rc:
        st.caption(
          f"Last: {'OK' if last_rc.get('ok') else 'BLOCK'} · {last_rc.get('model_id')} · "
          f"proj={last_rc.get('projected_risk_pct')}% · {last_rc.get('reasons') or '—'}"
        )
    except Exception as exc:
      st.caption(f"Risk cap UI unavailable: {exc}")

  # ── Quality: strategy mode + remine gate ────────────────────────────
  with tab_quality:
    st.markdown('<div class="panel-label">1 · Strategy mode</div>', unsafe_allow_html=True)
    st.caption(
      "**Weekly remine** = mỗi tuần mới mine genome (mặc định). "
      "**Frozen genome** = giữ strategy đã có trong schedule.json / *_live_weeks.json, "
      "không remine thứ Hai và không weekend pre-remine. "
      "Tuần chưa có freeze → FLAT. **Live và Replay dùng chung.** "
      "Đổi option tự lưu; F5 không mất. Đang trade: áp dụng từ **nến kế**, không cần restart."
    )
    try:
      from gui.theme import restore_widget_choice
      from strategy_mode import load_prefs as load_sm_prefs, save_prefs as save_sm_prefs
      sm = load_sm_prefs()
      saved_mode = str(sm.get("mode") or "weekly")
      if saved_mode not in ("weekly", "frozen"):
        saved_mode = "weekly"
      st.session_state.strategy_mode_radio = restore_widget_choice(
        st.session_state.get("strategy_mode_radio"),
        saved_mode,
        ("weekly", "frozen"),
        saved_mode,
      )
      sm_mode = st.radio(
        "Trade model strategy",
        options=("weekly", "frozen"),
        format_func=lambda m: (
          "Weekly remine (mặc định)" if m == "weekly"
          else "Frozen genome (không remine theo tuần)"
        ),
        horizontal=True,
        key="strategy_mode_radio",
        label_visibility="collapsed",
      )
      if sm_mode != saved_mode:
        sm = save_sm_prefs({"mode": sm_mode})
        st.toast(
          "Frozen — next bar" if sm_mode == "frozen" else "Weekly remine — next bar"
        )
      st.caption(
        f"Đã lưu: **{'frozen' if sm_mode == 'frozen' else 'weekly remine'}**"
        + (f" · {sm.get('updated_at')}" if sm.get("updated_at") else "")
      )
    except Exception as exc:
      st.caption(f"Strategy mode UI unavailable: {exc}")

    st.markdown('<div class="panel-label" style="margin-top:0.75rem">2 · Remine quality gate</div>', unsafe_allow_html=True)
    st.caption(
      "Gate chỉ kiểm tra chất lượng sau khi remine (FAIL → FLAT / schedule fallback). "
      "Tắt gate ≠ tắt remine: tuần ngoài schedule vẫn remine bình thường; Live chỉ thôi cảnh báo REMINE_OK. "
      "Cuối tuần (T6 ≥18h / T7 / CN) worker pre-remine tuần tới; Thứ 2 chỉ fallback nếu chưa freeze. "
      "Frozen mode bỏ qua bước này."
    )
    _render_remine_status_table()
    try:
      from remine_gate import load_last_alert, load_prefs as load_rg_prefs, save_prefs as save_rg_prefs
      rg = load_rg_prefs()
      last_rg = load_last_alert()
      rg_en = st.toggle("Enable remine gate", value=bool(rg.get("enabled", True)), key="rg_en")
      g1, g2, g3 = st.columns(3)
      with g1:
        rg_n = st.number_input("Min n_trades (train)", min_value=0, max_value=500, value=int(rg.get("min_n_trades") or 20), key="rg_n")
      with g2:
        rg_pf = st.number_input("Min profit_factor", min_value=0.0, max_value=10.0, value=float(rg.get("min_profit_factor") or 1.3), step=0.1, key="rg_pf")
      with g3:
        rg_tr = st.number_input("Min total_r", min_value=-50.0, max_value=50.0, value=float(rg.get("min_total_r") or 0.0), step=0.5, key="rg_tr")
      rg_cmp = st.checkbox("So với baseline PF model (≥ ratio × baseline)", value=bool(rg.get("compare_baseline", True)), key="rg_cmp")
      rg_ratio = st.number_input(
        "Min PF vs baseline ratio", min_value=0.0, max_value=1.5,
        value=float(rg.get("min_pf_vs_baseline") or 0.75), step=0.05, key="rg_ratio",
        disabled=not rg_cmp,
      )
      if st.button("Save remine gate", key="rg_save"):
        save_rg_prefs({
          "enabled": bool(rg_en),
          "min_n_trades": int(rg_n),
          "min_profit_factor": float(rg_pf),
          "min_total_r": float(rg_tr),
          "compare_baseline": bool(rg_cmp),
          "min_pf_vs_baseline": float(rg_ratio),
        })
        st.toast("Remine gate saved")
        st.rerun()
      if last_rg:
        st.caption(
          f"Last: {'PASS' if last_rg.get('ok') else 'FAIL'} · {last_rg.get('model_id')} · "
          f"week {last_rg.get('week_start')} · {last_rg.get('reasons') or '—'}"
        )
    except Exception as exc:
      st.caption(f"Remine gate UI unavailable: {exc}")

  # ── System: Windows/EA + danger ─────────────────────────────────────
  with tab_system:
    st.markdown('<div class="panel-label">1 · Windows / EA</div>', unsafe_allow_html=True)
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
        "- **Stop** → gỡ task\n"
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

    st.markdown('<div class="panel-label" style="margin-top:0.75rem">2 · Danger zone</div>', unsafe_allow_html=True)
    with st.expander("Reset all Live data", expanded=False):
      st.caption(
        "Xóa journal · sim/parity · bridge state · OHLC cache · "
        "(tuỳ chọn) packages + roster. Mặc định **giữ** `*_live_weeks.json` "
        "(remine tuần Live đã freeze — Replay dùng lại cho khớp). "
        "Dừng workers/replay trước khi wipe."
      )
      keep_live_weeks = st.checkbox(
        "Keep frozen live_weeks (đừng remine lại tuần Live)",
        value=True,
        key="reset_keep_live_weeks",
        help="File results/trade_models/*_live_weeks.json. Tắt chỉ khi muốn xóa genome tuần hiện tại.",
      )
      wipe_packages = st.checkbox(
        "Also remove installed packages & clear roster",
        value=False,
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
              keep_live_weeks=bool(keep_live_weeks),
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


def _install_flash_text(dest: Path) -> str:
  label = dest.name
  weeks = 0
  try:
    meta = json.loads((dest / "install_meta.json").read_text(encoding="utf-8"))
    label = str(meta.get("label") or label)
    weeks = int(meta.get("schedule_weeks") or 0)
  except Exception:
    try:
      man = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
      label = str(man.get("label") or label)
      weeks = int(man.get("schedule_weeks") or 0)
    except Exception:
      pass
  extra = f" · {weeks} tuần OOS" if weeks else ""
  return f"{label}{extra} · `{dest.name}`"


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
  st.caption(
    "Bật/tắt và risk theo **model**. Chỉ package **READY** (có schedule.json + checksum OK) mới On được. "
    "Save rồi Start ở Live. Nếu sau `git pull` trên Windows thấy checksum mismatch / toggle xám — "
    "bấm **Rebuild from installed** (app tự sửa CRLF)."
  )

  from package_store import package_ready, sanitize_roster_models

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
        "enabled": bool(inst.get("ready")),
        "ready": inst.get("ready"),
        "has_schedule": inst.get("has_schedule"),
        "schedule_weeks": inst.get("schedule_weeks"),
        "risk_pct": 1.0,
        "magic": None,
      })

  if not models:
    st.info("Chưa có model — Import package (.tmpkg) ở mục 2.")
  else:
    edited = []
    for i, row in enumerate(models):
      iid = str(row.get("install_id") or "")
      info = package_ready(iid) if iid else {"ready": False, "error": "no install_id", "schedule_weeks": 0}
      ready = bool(info.get("ready"))
      c1, c2, c3, c4 = st.columns([3.2, 0.8, 1.1, 1])
      with c1:
        badge = "READY" if ready else "NO SCHEDULE"
        st.markdown(f"**{row.get('label') or row.get('model_id')}** · `{badge}`")
        st.caption(
          f"{row.get('symbol')} {row.get('timeframe')} · {row.get('model_id')} · "
          f"weeks={info.get('schedule_weeks') or 0}"
          + (f" · {info.get('error')}" if not ready and info.get("error") else "")
        )
      with c2:
        en = st.toggle(
          "On",
          value=bool(row.get("enabled", True)) and ready,
          key=f"en_{i}",
          disabled=not ready,
          help=None if ready else (
            (info.get("error") or "Package incomplete")
            + " — bấm Rebuild from installed nếu lỗi checksum trên Windows"
          ),
        )
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
      edited.append({
        **row,
        "enabled": bool(en) and ready,
        "ready": ready,
        "has_schedule": info.get("has_schedule"),
        "schedule_weeks": info.get("schedule_weeks"),
        "risk_pct": risk,
      })

    s1, s2, s3 = st.columns([1.4, 1, 1])
    with s1:
      if st.button("Save roster", type="primary", use_container_width=True, key="save_roster_btn"):
        cleaned, warns = sanitize_roster_models(edited)
        assigned = assign_magics(cleaned, sim=False)
        save_roster(assigned)
        for w in warns:
          st.warning(w)
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
        # BUG-12: keep sticky magics / risk / enabled from prior roster
        save_roster(rebuild_roster_preserving_sticky())
        st.rerun()

  # ── 2. Import ───────────────────────────────────────────────────────
  if st.session_state.pop("_models_clear_path", False):
    st.session_state["models_path"] = ""

  st.markdown('<div class="panel-label" style="margin-top:0.75rem">2 · Import</div>', unsafe_allow_html=True)
  st.caption("Nhận package từ Lab (.tmpkg). Bắt buộc có **schedule.json** — thiếu thì import bị từ chối.")

  flash = st.session_state.get("models_import_flash") or {}
  if flash.get("text"):
    kind = "ok" if flash.get("ok") else "fail"
    title = "Import thành công" if flash.get("ok") else "Import thất bại"
    st.markdown(
      f'<div class="import-flash import-flash-{kind}">'
      f"<strong>{html.escape(title)}</strong>"
      f"{html.escape(str(flash.get('text') or ''))}"
      f"</div>",
      unsafe_allow_html=True,
    )
    if st.button("Đóng thông báo", key="models_import_flash_dismiss"):
      st.session_state.pop("models_import_flash", None)
      st.rerun()

  upload_n = int(st.session_state.get("models_upload_n") or 0)
  up = st.file_uploader(
    "Upload .tmpkg",
    type=["tmpkg"],
    key=f"models_upload_{upload_n}",
  )
  path_txt = st.text_input(
    "Or path to .tmpkg (file) / packages_out folder",
    key="models_path",
  )
  if st.button("Import package", type="primary", key="import_pkg_btn"):
    from import_trade_package import import_dir, import_one

    ok = False
    msg = "Chọn file .tmpkg, hoặc dán đường dẫn file / thư mục packages_out."
    try:
      with st.spinner("Đang import .tmpkg…"):
        if up is not None:
          INBOX_DIR.mkdir(parents=True, exist_ok=True)
          dest = INBOX_DIR / Path(str(up.name)).name
          dest.write_bytes(up.getvalue())
          installed = import_one(dest)
          ok, msg = True, _install_flash_text(installed)
        elif str(path_txt or "").strip():
          pkg = Path(str(path_txt).strip())
          if not pkg.is_absolute():
            pkg = (LIVE / pkg).resolve()
          if pkg.is_dir():
            dests = import_dir(pkg)
            ok, msg = True, " · ".join(_install_flash_text(d) for d in dests)
          else:
            installed = import_one(pkg)
            ok, msg = True, _install_flash_text(installed)
    except Exception as exc:
      ok, msg = False, str(exc)

    st.session_state["models_import_flash"] = {"ok": ok, "text": msg}
    if ok:
      st.session_state["models_upload_n"] = upload_n + 1
      st.session_state["_models_clear_path"] = True
      st.toast("Import thành công")
    else:
      st.toast("Import thất bại")
    st.rerun()

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
      ready = bool(row.get("ready"))
      c_a, c_b = st.columns([4, 1])
      with c_a:
        st.markdown(
          f"**{row.get('label')}** · `{'READY' if ready else 'INCOMPLETE'}`  \n"
          f"<span style='color:var(--desk-muted);font-size:0.85rem'>"
          f"{row.get('symbol')} {row.get('timeframe')} · {row.get('model_id')}"
          f" · weeks={row.get('schedule_weeks') or 0}"
          f"{' · On' if on else ''}"
          f"{'' if ready else ' · ' + str(row.get('ready_error') or 'missing schedule')}"
          f"</span>",
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



# ── Top nav FIRST (before sidebar / auto-refresh) so clicks are not raced ─
import time as _time

_seed_top_nav()
nav = st.radio(
  "Nav",
  _TOP_NAV,
  horizontal=True,
  key="top_nav",
  label_visibility="collapsed",
  help="Live = trading · Replay = OOS desk · Models = import/roster · Setup = Risk/Quality/System",
  on_change=_on_top_nav_change,
)
# Fill ?nav= only when missing (F5 with bare URL). User clicks sync via on_change.
if _nav_from_query() is None:
  st.query_params["nav"] = nav

# ── Sidebar ───────────────────────────────────────────────────────────
with st.sidebar:
  st.markdown("### Desk")
  # Persist Auto-refresh across F5 via results/ui_prefs.json
  from gui.theme import load_ui_prefs, save_ui_prefs
  _ui_prefs = load_ui_prefs()
  if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = bool(_ui_prefs.get("auto_refresh"))
  if "auto_refresh_every" not in st.session_state:
    st.session_state.auto_refresh_every = int(_ui_prefs.get("auto_refresh_every") or 5)
  auto = st.toggle("Auto-refresh", key="auto_refresh")
  every = st.select_slider(
    "Every (sec)",
    options=[5, 10, 15, 30],
    key="auto_refresh_every",
  )
  _saved_auto = bool(_ui_prefs.get("auto_refresh"))
  _saved_every = int(_ui_prefs.get("auto_refresh_every") or 5)
  if bool(auto) != _saved_auto or int(every) != _saved_every:
    save_ui_prefs({
      "auto_refresh": bool(auto),
      "auto_refresh_every": int(every),
    })
  if st.button("Refresh now", use_container_width=True, key="desk_refresh_now"):
    st.session_state["_desk_tick"] = _time.time()
  st.caption(f"{LIVE_INSTANCE_ID} · :{LIVE_APP_PORT} · magic {LIVE_MAGIC_BASE}")
  if auto:
    st.caption(f"Live numbers refresh every {int(every)}s — D/W/M/ALL stays put.")

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
