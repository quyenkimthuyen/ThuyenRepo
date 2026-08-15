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
  load_strategy_stats,
  paper_results_summary,
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
    pms = b.get("parity_models") or []
    if not pms and (b.get("ea_status") in ("running", "pending") or replay.get("running")):
      model_rows.append({
        "label": f"{b.get('n_models') or '?'} model(s)",
        "market": f"{b.get('symbol')} {b.get('timeframe')}",
        "status": b.get("ea_status") or "pending",
        "R": None,
        "lab_R": None,
        "dR": None,
        "pct": float(b.get("pct") or 0),
        "err": None,
      })
      continue
    for pm in pms:
      mid = str(pm.get("id") or pm.get("model_id") or "")
      err = pm.get("err") or pm.get("error")
      model_rows.append({
        "label": labels.get(mid) or mid or "—",
        "market": f"{b.get('symbol')} {b.get('timeframe')}",
        "status": ("FAIL" if err else (b.get("ea_status") or "done")),
        "R": pm.get("R"),
        "lab_R": pm.get("lab_R"),
        "dR": pm.get("dR"),
        "pct": 100.0 if (pm.get("R") is not None or err) else float(b.get("pct") or 0),
        "err": err,
      })
  if model_rows:
    for row in model_rows:
      dr = row.get("dR")
      dr_s = f"ΔR {dr:+.2f}" if isinstance(dr, (int, float)) else ""
      err = row.get("err")
      err_s = f" · {err}" if err else ""
      st.progress(
        min(1.0, float(row.get("pct") or 0) / 100.0),
        text=(
          f"{row['label']} · {row['market']} · "
          f"R={row.get('R')} (lab {row.get('lab_R')}) {dr_s} · {row['status']}{err_s}"
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


def _parity_results_from_replay(replay: dict, models: list[dict]) -> dict:
  """Aggregate live parity numbers for Results metrics (not paper journal)."""
  labels = _model_label_map(models)
  rows = []
  for b in replay.get("books") or []:
    for pm in b.get("parity_models") or []:
      mid = str(pm.get("id") or pm.get("model_id") or "")
      err = pm.get("err") or pm.get("error")
      rows.append({
        "Model": labels.get(mid) or mid,
        "Market": f"{b.get('symbol') or ''} {b.get('timeframe') or ''}".strip(),
        "R": pm.get("R"),
        "Lab R": pm.get("lab_R"),
        "ΔR": pm.get("dR"),
        "OK": (err is None) and (pm.get("R") is not None),
        "Error": err,
      })
  n_ok = sum(1 for r in rows if r.get("OK"))
  tot_r = round(sum(float(r.get("R") or 0) for r in rows if r.get("OK")), 3)
  return {
    "rows": rows,
    "n_models": len(rows),
    "n_ok": n_ok,
    "total_r": tot_r,
    "ok": bool(rows) and n_ok == len(rows),
  }


def _render_replay_live_panels() -> dict:
  """Progress + Results + Past runs — safe to poll via st.fragment."""
  snap = desk_snapshot(sim=True)
  replay = snap.get("replay") or {}
  models = snap.get("models") or []
  running = bool(snap.get("bridge_running"))
  books = replay.get("books") or []
  prefs = load_oos_prefs()
  mode = str(prefs.get("mode") or replay.get("mode") or "live_like")
  parity = _parity_results_from_replay(replay, models) if mode == "parity" else {}
  paper = paper_results_summary() if mode == "live_like" else {}
  stats = load_strategy_stats() if mode == "live_like" else (replay.get("strategy_stats") or {})

  st.caption(
    f"Updated {snap.get('updated_at')} · "
    f"{'RUNNING' if running else 'Idle'}"
    + (f" · pid {replay.get('pid')}" if replay.get("pid") else "")
    + f" · mode={mode}"
    + (" · force_remine" if prefs.get("force_remine") else "")
  )

  # ── 2. Progress ─────────────────────────────────────────────────────
  st.markdown('<div class="panel-label" style="margin-top:0.25rem">2 · Progress</div>', unsafe_allow_html=True)
  if mode == "parity":
    if running and not any(b.get("parity_models") for b in books):
      st.caption("Đang chạy Lab parity… chờ model đầu tiên.")
    if running or any(b.get("parity_models") for b in books) or books:
      _render_replay_progress(replay, models)
    else:
      st.caption("Chưa có progress — Start OOS replay.")
  else:
    if running or any(int(b.get("bars_done") or 0) for b in books) or books:
      for b in books:
        done = int(b.get("bars_done") or 0)
        total = int(b.get("bars_total") or 0)
        pct = b.get("pct") or 0
        st.caption(
          f"{b.get('symbol')} {b.get('timeframe')} · {b.get('ea_status')} · "
          f"{done}/{total} bars ({pct}%) · fills={b.get('n_fills')} · signals={b.get('n_signals')}"
        )
        if total:
          st.progress(min(max(float(pct) / 100.0, 0.0), 1.0))
    else:
      st.caption("Chưa có progress — Start Live-like replay.")

  # ── 3. Results ──────────────────────────────────────────────────────
  st.markdown('<div class="panel-label" style="margin-top:0.75rem">3 · Results</div>', unsafe_allow_html=True)
  c1, c2, c3, c4 = st.columns(4)
  if mode == "parity":
    c1.metric("Total R", parity.get("total_r") if parity.get("n_models") else "—")
    c2.metric(
      "Models OK",
      f"{parity.get('n_ok')}/{parity.get('n_models')}" if parity.get("n_models") else "—",
    )
    c3.metric(
      "OOS",
      f"{replay.get('oos_from') or '—'} → {replay.get('oos_to') or '—'}",
    )
    if running:
      status_txt = "RUNNING"
    elif not parity.get("n_models"):
      status_txt = "—"
    else:
      status_txt = "OK" if parity.get("ok") else "FAIL"
    c4.metric("Status", status_txt)
    if parity.get("rows"):
      st.dataframe(parity["rows"], use_container_width=True, hide_index=True)
    else:
      st.caption("Chưa có kết quả Lab parity — Start với mode Lab parity.")
  else:
    c1.metric("Fills", paper.get("n_fills") if paper.get("n_books") else "—")
    c2.metric(
      "Books OK",
      f"{paper.get('n_ok')}/{paper.get('n_books')}" if paper.get("n_books") else "—",
    )
    c3.metric(
      "OOS",
      f"{paper.get('oos_from') or replay.get('oos_from') or '—'} → "
      f"{paper.get('oos_to') or replay.get('oos_to') or '—'}",
    )
    if running:
      status_txt = "RUNNING"
    elif not paper.get("n_books"):
      status_txt = "—"
    else:
      status_txt = "OK" if paper.get("ok") else "FAIL"
    c4.metric("Status", status_txt)
    if paper.get("books"):
      st.dataframe(
        [{
          "Book": f"{b.get('symbol')} {b.get('timeframe')}",
          "Models": b.get("n_models"),
          "Fills": b.get("n_fills"),
          "Signals": b.get("n_signals"),
          "Bars": f"{b.get('bars_done') or '—'}/{b.get('bars_total') or '—'}",
          "Status": b.get("status"),
          "OK": b.get("ok"),
        } for b in paper["books"]],
        use_container_width=True,
        hide_index=True,
      )
    else:
      st.caption("Chưa có kết quả Live-like — Start OOS replay (bridge/paper).")

    if stats:
      s1, s2, s3 = st.columns(3)
      s1.metric("Schedule hits", stats.get("schedule_hits") or 0)
      s2.metric("Remine", stats.get("remine_count") or 0)
      s3.metric("Skip", stats.get("skip_count") or 0)
      bym = stats.get("by_model") or {}
      if bym:
        st.dataframe(
          [{
            "Model": mid,
            "Schedule": v.get("schedule_hits"),
            "Remine": v.get("remine_count"),
            "Skip": v.get("skip_count"),
          } for mid, v in bym.items()],
          use_container_width=True,
          hide_index=True,
        )

  bdirs = [Path(p) for p in (snap.get("bridge_dirs") or [])]
  trades = load_trades_many(bdirs) if bdirs else []
  eq = render_equity_section(
    trades,
    period="all",
    parity_books=books if mode == "parity" else None,
  )
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
      st.caption(
        "Chưa có trade journal"
        + (" (Lab parity dùng weekly genomes)." if mode == "parity" else " (chạy Live-like để có paper fills).")
      )

  # ── 4. Past runs ────────────────────────────────────────────────────
  st.markdown('<div class="panel-label" style="margin-top:0.75rem">4 · Past runs</div>', unsafe_allow_html=True)
  runs = list_replay_runs(limit=20)
  cur = latest_parity_snapshot()
  if mode == "parity" and cur and not runs:
    from replay_history import archive_parity_batch
    if cur.get("books") and st.button("Archive current result into history", key="archive_cur"):
      archive_parity_batch({**cur, "mode": "schedule_parity"})
      st.rerun()
  if mode == "live_like" and paper.get("n_books") and not running:
    from replay_history import archive_live_like_run
    if st.button("Archive current Live-like result", key="archive_live_like"):
      archive_live_like_run(paper)
      st.toast("Archived Live-like run")
      st.rerun()
  if runs:
    options = {
      f"{r.get('created_at', '')[:19]} · {r.get('mode') or 'parity'} · "
      f"{r.get('oos_from')}→{r.get('oos_to')} · "
      f"R={r.get('total_r')} · fills={r.get('n_fills')} · "
      f"{r.get('n_ok')}/{r.get('n_models')} ok · {r.get('run_id')}": r
      for r in runs
    }
    labels = list(options.keys())
    latest_id = str(runs[0].get("run_id") or "")
    prev_latest = str(st.session_state.get("_replay_hist_latest_id") or "")
    if latest_id and latest_id != prev_latest:
      st.session_state["_replay_hist_latest_id"] = latest_id
      st.session_state["replay_hist_pick"] = labels[0]
    elif st.session_state.get("replay_hist_pick") not in options:
      st.session_state["replay_hist_pick"] = labels[0]
    pick = st.selectbox("Past runs", labels, key="replay_hist_pick")
    chosen = options.get(pick) or runs[0]
    detail = load_replay_run(str(chosen.get("run_id"))) or {}
    hist_models = (detail.get("summary") or {}).get("models") or []
    if not hist_models and chosen.get("mode") != "live_like":
      from replay_history import _summarize_batch
      hist_models = (_summarize_batch(detail).get("models") or [])
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total R", chosen.get("total_r") if chosen.get("total_r") is not None else "—")
    m2.metric("Models OK", f"{chosen.get('n_ok')}/{chosen.get('n_models')}")
    m3.metric("OOS", f"{chosen.get('oos_from')} → {chosen.get('oos_to')}")
    m4.metric("Mode", chosen.get("mode") or "—")
    if hist_models:
      st.dataframe(
        [{
          "Model": m.get("label") or m.get("model_id"),
          "Market": f"{m.get('symbol') or ''} {m.get('timeframe') or ''}".strip(),
          "R": m.get("total_r"),
          "Lab R": m.get("lab_total_r"),
          "ΔR": m.get("delta_r"),
          "WR%": m.get("win_rate_pct"),
          "Trades": m.get("n_trades") or m.get("n_fills"),
          "OK": m.get("ok"),
        } for m in hist_models],
        use_container_width=True,
        hide_index=True,
      )
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


def render_replay_desk() -> dict:
  """Replay desk — Run → Progress → Results → Past runs (no Live chrome)."""
  from datetime import date as _date
  from datetime import timedelta

  st.session_state.desk_mode = "Replay"
  if "replay_stats_period" not in st.session_state:
    st.session_state.replay_stats_period = "all"

  snap = desk_snapshot(sim=True)
  tone = snap["health_tone"]
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
  if "replay_mode_radio" not in st.session_state:
    st.session_state.replay_mode_radio = (
      "Live-like (bridge)" if prefs.get("mode") != "parity" else "Lab parity"
    )

  mode_label = st.radio(
    "Replay mode",
    ["Live-like (bridge)", "Lab parity"],
    horizontal=True,
    key="replay_mode_radio",
    help=(
      "Live-like = cùng BridgeEngine với Live (paper fills). "
      "Lab parity = genome đóng băng, khớp TotalR/WR Lab."
    ),
  )
  mode = "live_like" if mode_label.startswith("Live-like") else "parity"
  force_remine = False
  if mode == "live_like":
    force_remine = st.checkbox(
      "Force remine (ignore schedule — stress path tuần mới)",
      value=bool(prefs.get("force_remine")),
      key="replay_force_remine",
      help="Bỏ qua schedule.json, ép optimize_on_window như Live khi gặp tuần chưa freeze.",
    )

  oc1, oc2 = st.columns(2)
  with oc1:
    oos_from = st.date_input("OOS from", key="oos_from_date")
  with oc2:
    oos_to = st.date_input("OOS to", key="oos_to_date")

  # Warn only when selected OOS is outside cache for enabled books.
  try:
    from books import group_models_by_book
    from live_config import RESULTS_DIR
    import json as _json

    def _cache_span(sym: str, tf: str) -> tuple[str | None, str | None]:
      meta_p = RESULTS_DIR / "data" / f"mt5_{sym.lower()}_{tf.lower()}_meta.json"
      if meta_p.exists():
        try:
          meta = _json.loads(meta_p.read_text(encoding="utf-8"))
          start = str(meta.get("start") or "")[:10] or None
          end = str(meta.get("end") or "")[:10] or None
          if start and end:
            return start, end
        except Exception:
          pass
      pq = RESULTS_DIR / "data" / f"mt5_{sym.lower()}_{tf.lower()}.parquet"
      if pq.exists():
        try:
          import pandas as pd
          df = pd.read_parquet(pq)
          if len(df):
            return str(df.index[0])[:10], str(df.index[-1])[:10]
        except Exception:
          return None, None
      return None, None

    warn_bits: list[str] = []
    sel_from = str(oos_from)
    sel_to = str(oos_to)
    for (sym, tf), _rows in group_models_by_book(models).items():
      c0, c1 = _cache_span(str(sym), str(tf))
      label = f"{sym} {tf}"
      if not c0 or not c1:
        warn_bits.append(f"{label}: chưa có OHLC cache — không replay được")
        continue
      eff_from = max(sel_from, c0)
      eff_to = min(sel_to, c1)
      if sel_from < c0:
        warn_bits.append(
          f"{label}: OOS from {sel_from} sớm hơn data ({c0}) — replay bắt đầu {eff_from}"
        )
      if sel_to > c1:
        warn_bits.append(
          f"{label}: OOS to {sel_to} muộn hơn data ({c1}) — replay kết thúc {eff_to}"
        )
      if eff_from > eff_to:
        warn_bits.append(
          f"{label}: khoảng OOS không giao data ({c0}→{c1}) — không có bar để chạy"
        )
    for w in warn_bits:
      st.warning(w)
  except Exception:
    pass

  cur_from, cur_to = str(oos_from), str(oos_to)
  if (
    cur_from != str(prefs.get("from") or "")
    or cur_to != str(prefs.get("to") or "")
    or mode != prefs.get("mode")
    or bool(force_remine) != bool(prefs.get("force_remine"))
  ):
    save_oos_prefs(
      date_from=cur_from,
      date_to=cur_to,
      mode=mode,
      force_remine=force_remine if mode == "live_like" else False,
    )
  if not models:
    st.info("Chưa bật model — mở **Models**, bật On, Save.")

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
          mode=mode,
          force_remine=force_remine if mode == "live_like" else False,
          restart=True,
        )
        st.toast(
          f"Replay {out.get('mode')} {out.get('from')}→{out.get('to')} · pid {out.get('pid')}"
        )
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
    if mode == "live_like":
      hint = "Live-like · bridge decide → paper fill · books song song (1 process/book)"
      if force_remine:
        hint += " · FORCE REMINE"
    else:
      hint = "Lab parity · schedule genomes (TotalR/WR)"
    st.caption(f"Window **{oos_from} → {oos_to}** · {hint}")
  st.caption("Parity OK ≠ Live OK — dùng **Live-like** trước khi Start trading.")

  # Live panels: native fragment poll (streamlit-autorefresh is unreliable on 1.60).
  auto = bool(st.session_state.get("auto_refresh"))
  every = max(1, int(st.session_state.get("auto_refresh_every") or 5))
  if auto:
    @st.fragment(run_every=timedelta(seconds=every))
    def _replay_live_fragment() -> dict:
      return _render_replay_live_panels()

    return _replay_live_fragment() or snap
  return _render_replay_live_panels()


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
    book_lv = book.get("level") or "muted"
    flags = " · ".join(book.get("flags") or [])
    if not flags:
      # Never paint "OK" in warn/danger colors — that mismatch looked broken.
      flags = "OK" if book_lv == "ok" else str(book_lv).upper()
    worker = (
      f"pid {book.get('worker_pid')}" if book.get("worker_alive") else "worker down"
    )
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
          <div class="health-book-title">{book.get('symbol')} {book.get('timeframe')} · {book.get('n_models')} model(s)
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
    "RISK_CAP = vượt trần risk đồng thời · REMINE = remine khi gate đang bật."
  )
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
        with st.spinner(
          "Start Live: check packages/OHLC → MT5/EA → workers "
          "(không remine lúc Start; remine trên nến đầu)…"
        ):
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
              force=False, wait_online=True, wait_sec=45.0,
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
    st.caption(
      "Start chỉ check package + OHLC (nhanh). Remine chạy trên worker khi có nến mới."
    )
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
  """Setup tabs: Risk · Quality · Control · System."""
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
  st.caption("Risk = mất tiền · Quality = remine · Control = kill/workers · System = EA & wipe")

  tab_risk, tab_quality, tab_control, tab_system = st.tabs(
    ["Risk", "Quality", "Control", "System"]
  )

  # ── Risk: loss guard + concurrent cap ───────────────────────────────
  with tab_risk:
    st.markdown('<div class="panel-label">1 · Loss guard</div>', unsafe_allow_html=True)
    st.caption(
      "Sau khi lỗ/DD chạm ngưỡng → FLAT + dừng service. "
      "Khác concurrent cap (chặn trước khi mở lệnh). 0 = tắt ngưỡng đó."
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

    if st.button("Save loss guard", type="primary", key="save_risk_limits"):
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
      st.toast("Loss guard saved")
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

  # ── Quality: remine gate ────────────────────────────────────────────
  with tab_quality:
    st.markdown('<div class="panel-label">1 · Remine quality gate</div>', unsafe_allow_html=True)
    st.caption(
      "Gate chỉ kiểm tra chất lượng sau khi remine (FAIL → FLAT / schedule fallback). "
      "Tắt gate ≠ tắt remine: tuần ngoài schedule vẫn remine bình thường; Live chỉ thôi cảnh báo REMINE_OK. "
      "Cuối tuần (T6 ≥18h / T7 / CN) worker pre-remine tuần tới; Thứ 2 chỉ fallback nếu chưa freeze."
    )
    try:
      from weekend_preremine import (
        in_weekend_preremine_window,
        load_all_preremine_state,
        next_week_start,
        weekend_preremine_target,
      )
      tgt = weekend_preremine_target()
      target_week = str((tgt or next_week_start()).date())
      if tgt is not None:
        st.caption(f"Weekend pre-remine window · target week {target_week}")
      elif in_weekend_preremine_window():
        st.caption(f"Weekend pre-remine · next week {target_week}")
      else:
        st.caption(f"Weekend pre-remine idle · next week will be {target_week}")

      books = (load_all_preremine_state().get("books") or {})
      gate_by_model: dict[str, dict] = {}
      try:
        from remine_gate import load_gate_by_model_week
        gate_by_model = load_gate_by_model_week(target_week)
      except Exception:
        gate_by_model = {}

      def _fmt_num(v: Any, digits: int = 2) -> str:
        if v is None or v == "":
          return "—"
        try:
          x = float(v)
          if x != x:  # NaN
            return "—"
          if abs(x - round(x)) < 1e-9:
            return str(int(round(x)))
          return f"{x:.{digits}f}"
        except (TypeError, ValueError):
          return str(v)

      def _row_from_info(book: str, mid: str, info: dict, pr_status: str) -> dict:
        src = str(info.get("source") or "—")
        gate_row = gate_by_model.get(mid) or {}
        # Prefer persisted weekend state; fall back to alerts for this target week.
        metrics = {}
        if info.get("n_trades") is not None or info.get("profit_factor") is not None:
          metrics = {
            "n_trades": info.get("n_trades"),
            "profit_factor": info.get("profit_factor"),
            "total_r": info.get("total_r"),
          }
        elif isinstance(gate_row.get("metrics"), dict) and str(gate_row.get("week_start") or "") == target_week:
          metrics = gate_row.get("metrics") or {}
        baseline_pf = info.get("baseline_pf")
        if baseline_pf is None and isinstance(gate_row.get("baseline"), dict):
          if str(gate_row.get("week_start") or "") == target_week:
            baseline_pf = (gate_row.get("baseline") or {}).get("profit_factor")
        gate_label = info.get("gate")
        if not gate_label:
          if src in ("schedule_hit", "state_done"):
            gate_label = "—"
          elif isinstance(gate_row, dict) and str(gate_row.get("week_start") or "") == target_week and "ok" in gate_row:
            gate_label = "PASS" if gate_row.get("ok") else "FAIL"
          elif src == "remine":
            gate_label = "PASS"
          elif src == "schedule_fallback":
            gate_label = "FAIL"
          else:
            gate_label = "—"
        reasons = info.get("gate_reasons") or info.get("error")
        if (not reasons or reasons == "—") and gate_row.get("reasons") and str(gate_row.get("week_start") or "") == target_week:
          reasons = "; ".join(str(x) for x in (gate_row.get("reasons") or []))
        if isinstance(reasons, list):
          reasons = "; ".join(str(x) for x in reasons)
        reason_s = str(reasons or "").strip() or "—"
        return {
          "book": book,
          "model": mid,
          "week": str(info.get("week_start") or "—") if info else "—",
          "status": pr_status,
          "source": src,
          "gate": gate_label,
          "n": _fmt_num(metrics.get("n_trades"), 0),
          "PF": _fmt_num(metrics.get("profit_factor"), 2),
          "R": _fmt_num(metrics.get("total_r"), 1),
          "base_PF": _fmt_num(baseline_pf, 2),
          "reason": reason_s[:100],
          "updated": str(info.get("updated_at") or "—")[:19] if info else "—",
        }

      # Roster models → pending if not yet in pre-remine state for target week.
      roster_rows: list[dict] = []
      try:
        from package_store import load_roster
        for m in (load_roster().get("models") or []):
          if not m.get("enabled", True):
            continue
          sym = str(m.get("symbol") or "").upper()
          tf = str(m.get("timeframe") or "").upper()
          mid = str(m.get("model_id") or m.get("id") or "")
          if not (sym and tf and mid):
            continue
          roster_rows.append(
            {
              "book": f"{sym.lower()}_{tf.lower()}",
              "symbol": sym,
              "timeframe": tf,
              "model_id": mid,
            }
          )
      except Exception:
        roster_rows = []

      by_book_model: dict[tuple[str, str], dict] = {}
      for bk, row in books.items():
        for mid, info in (row.get("models") or {}).items():
          by_book_model[(str(bk), str(mid))] = dict(info or {})

      status_rows: list[dict] = []
      seen: set[tuple[str, str]] = set()
      for rr in roster_rows:
        key = (rr["book"], rr["model_id"])
        seen.add(key)
        info = by_book_model.get(key) or {}
        week = str(info.get("week_start") or "")
        if info and week == target_week and info.get("ok"):
          pr_status = "READY"
        elif info and week == target_week and info.get("ok") is False:
          pr_status = "FAIL"
        elif info and week and week != target_week:
          pr_status = "STALE"
        elif info:
          pr_status = "PARTIAL"
        else:
          pr_status = "PENDING"
        status_rows.append(_row_from_info(rr["book"], rr["model_id"], info, pr_status))
      # Orphan state entries (not in roster) still useful to show.
      for (bk, mid), info in sorted(by_book_model.items()):
        if (bk, mid) in seen:
          continue
        week = str(info.get("week_start") or "")
        pr_status = "READY" if (week == target_week and info.get("ok")) else (
          "FAIL" if info.get("ok") is False else "STALE"
        )
        status_rows.append(_row_from_info(bk, mid, info, pr_status))

      if status_rows:
        ready_n = sum(1 for r in status_rows if r["status"] == "READY")
        st.caption(
          f"Pre-remine models · {ready_n}/{len(status_rows)} READY for week {target_week} · "
          "n/PF/R = train metrics sau remine · base_PF = package baseline · gate = PASS/FAIL/—"
        )
        st.dataframe(
          status_rows,
          use_container_width=True,
          hide_index=True,
          height=min(420, 42 + 35 * len(status_rows)),
          column_config={
            "model": st.column_config.TextColumn("model", width="medium"),
            "reason": st.column_config.TextColumn("reason", width="large"),
          },
        )
      elif books:
        bits = []
        for bk, row in sorted(books.items()):
          mods = row.get("models") or {}
          ok_n = sum(1 for m in mods.values() if m.get("ok"))
          bits.append(f"{bk} {ok_n}/{len(mods)}@{row.get('week_start') or '—'}")
        st.caption("Pre-remine state · " + " · ".join(bits))
    except Exception:
      pass
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

  # ── Control: kill + workers ─────────────────────────────────────────
  with tab_control:
    st.markdown('<div class="panel-label">1 · Kill-switch</div>', unsafe_allow_html=True)
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

    st.markdown('<div class="panel-label" style="margin-top:0.75rem">2 · Workers</div>', unsafe_allow_html=True)
    st.caption("Hàng ngày Start/Stop trên desk Live; đây là trạng thái kỹ thuật.")
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

    st.markdown('<div class="panel-label" style="margin-top:0.75rem">2 · Danger zone</div>', unsafe_allow_html=True)
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
        save_roster(default_roster_from_installed())
        st.rerun()

  # ── 2. Import ───────────────────────────────────────────────────────
  st.markdown('<div class="panel-label" style="margin-top:0.75rem">2 · Import</div>', unsafe_allow_html=True)
  st.caption("Nhận package từ Lab (.tmpkg). Bắt buộc có **schedule.json** — thiếu thì import bị từ chối.")
  up = st.file_uploader("Upload .tmpkg", type=["tmpkg"], key="models_upload")
  path_txt = st.text_input("Or path to .tmpkg (file) / packages_out folder", "", key="models_path")
  if st.button("Import package", type="primary", key="import_pkg_btn"):
    try:
      if up is not None:
        INBOX_DIR.mkdir(parents=True, exist_ok=True)
        dest = INBOX_DIR / up.name
        dest.write_bytes(up.getvalue())
        pkg = dest
        cmd = [sys.executable, str(LIVE / "import_trade_package.py"), str(pkg)]
      elif path_txt.strip():
        pkg = Path(path_txt.strip())
        if pkg.is_dir():
          cmd = [sys.executable, str(LIVE / "import_trade_package.py"), "--dir", str(pkg)]
        else:
          cmd = [sys.executable, str(LIVE / "import_trade_package.py"), str(pkg)]
      else:
        st.error("Choose a .tmpkg file, or path to file / packages_out folder")
        cmd = None
      if cmd:
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        r = subprocess.run(
          cmd,
          cwd=str(LIVE),
          capture_output=True,
          text=True,
          encoding="utf-8",
          errors="replace",
          env=env,
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



# ── Sidebar ───────────────────────────────────────────────────────────
with st.sidebar:
  st.markdown("### Desk")
  # Persist Auto-refresh across F5 via results/ui_prefs.json
  from gui.theme import load_ui_prefs, save_ui_prefs
  _ui_prefs = load_ui_prefs()
  # top_nav may be set later in this script run — also read ?nav= here.
  _qp_nav = st.query_params.get("nav") or st.query_params.get("page")
  if isinstance(_qp_nav, (list, tuple)):
    _qp_nav = _qp_nav[0] if _qp_nav else None
  _nav_for_auto = st.session_state.get("top_nav") or str(_qp_nav or "").strip() or None
  if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = bool(_ui_prefs.get("auto_refresh"))
  if "auto_refresh_every" not in st.session_state:
    st.session_state.auto_refresh_every = int(_ui_prefs.get("auto_refresh_every") or 5)
  # Entering Replay: force ON for progress polling (session only — don't overwrite prefs).
  _forced_replay_auto = False
  if _nav_for_auto == "Replay" and st.session_state.get("_auto_refresh_nav_prev") != "Replay":
    st.session_state.auto_refresh = True
    _forced_replay_auto = True
  st.session_state["_auto_refresh_nav_prev"] = _nav_for_auto
  auto = st.toggle("Auto-refresh", key="auto_refresh")
  every = st.select_slider(
    "Every (sec)",
    options=[5, 10, 15, 30],
    key="auto_refresh_every",
  )
  # Save user changes only (skip the automatic Replay force-on write).
  _saved_auto = bool(_ui_prefs.get("auto_refresh"))
  _saved_every = int(_ui_prefs.get("auto_refresh_every") or 5)
  if (not _forced_replay_auto) and (
    bool(auto) != _saved_auto or int(every) != _saved_every
  ):
    save_ui_prefs({
      "auto_refresh": bool(auto),
      "auto_refresh_every": int(every),
    })
  if st.button("Refresh now", use_container_width=True):
    st.rerun()
  st.caption(f"{LIVE_INSTANCE_ID} · :{LIVE_APP_PORT} · magic {LIVE_MAGIC_BASE}")
  if auto:
    if st.session_state.get("top_nav") == "Replay" or _nav_for_auto == "Replay":
      st.caption("Replay panels tự poll (fragment) — không cần F5.")
    else:
      st.caption("Auto-refresh cập nhật số liệu — giữ sau refresh trang.")

# Full-page refresh for Live/Setup. Replay uses st.fragment(run_every) in-desk
# (streamlit-autorefresh custom component is unreliable on Streamlit 1.60).
if auto and st.session_state.get("top_nav") != "Replay":
  try:
    from streamlit_autorefresh import st_autorefresh  # type: ignore

    st_autorefresh(interval=int(every) * 1000, key="desk_refresh")
  except Exception:
    from datetime import timedelta
    import time as _time

    _every_s = max(1, int(every))

    @st.fragment(run_every=timedelta(seconds=_every_s))
    def _desk_auto_refresh_fallback() -> None:
      now = _time.time()
      last = float(st.session_state.get("_desk_refresh_last") or 0.0)
      if last <= 0.0 or (now - last) < (_every_s - 0.5):
        if last <= 0.0:
          st.session_state["_desk_refresh_last"] = now
        return
      st.session_state["_desk_refresh_last"] = now
      st.rerun()

    _desk_auto_refresh_fallback()

# Top-level nav: Live first · Replay desk · Models/Setup pages
# Persist in ?nav= so browser refresh stays on the same page.
_TOP_NAV = ("Live", "Replay", "Models", "Setup")


def _nav_from_query() -> str | None:
  raw = st.query_params.get("nav") or st.query_params.get("page")
  if isinstance(raw, (list, tuple)):
    raw = raw[0] if raw else None
  raw = str(raw or "").strip()
  return raw if raw in _TOP_NAV else None


if "top_nav" not in st.session_state:
  qp_nav = _nav_from_query()
  legacy = st.session_state.get("live_section")
  if qp_nav:
    st.session_state.top_nav = qp_nav
  elif legacy in ("Models", "Setup"):
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
  help="Live = trading · Replay = OOS desk · Models = import/roster · Setup = Risk/Quality/Control/System",
)
# Keep URL in sync so F5 / refresh stays on Live · Replay · Models · Setup
if _nav_from_query() != nav:
  st.query_params["nav"] = nav

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
