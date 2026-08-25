"""Live Trade — Now pulse + Bridge desk (roster, chart, parity, history test)."""
from __future__ import annotations

from datetime import timedelta
from html import escape

import streamlit as st

from gui.bridge_desk_stats import fmt_px, snapshot_live_desk
from gui.navigation import ALL_ITEMS, LABEL_TAB_REWARD
from gui.page_chrome import render_page_header
from gui.trade_model import format_model_label, get_active_trade_model, get_model_by_id
from mt5_bridge import background as bridge_bg
from mt5_bridge.loss_guard import loss_guard_status
from mt5_bridge.live_monitor_server import DEFAULT_MONITOR_PORT, ensure_chart_server
from mt5_bridge.protocol import normalize_model_ids, resolve_live_bridge_dir
from gui.live_autostart import (
  autostart_is_marked,
  disable_live_autostart,
  enable_live_autostart,
)
from gui.views.mt5_bridge import (
  render_tab_chart,
  render_tab_health,
  render_tab_history,
  render_tab_models,
  render_tab_risk_control,
  render_tab_stats,
  render_tab_tech,
)

_CSS_KEY = "_live_trade_dash_css_v5"  # bump when CSS changes (debug/cache only)

_SCOPED_CSS = """
<style>
.ltd-wrap { font-family: "IBM Plex Sans", "Segoe UI", sans-serif; color: #1a1d23; }
.ltd-title { font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase;
  color: #6b7280; margin: 0 0 0.15rem 0; }
.ltd-model { font-size: 1.05rem; font-weight: 600; margin: 0 0 0.65rem 0; line-height: 1.3; }
.ltd-ready { font-size: 0.82rem; margin: 0 0 0.85rem 0; padding: 0.35rem 0.55rem;
  border-radius: 4px; display: inline-block; }
.ltd-ready.ok { background: #e8f5f1; color: #0d6b56; }
.ltd-ready.warn { background: #fff6e5; color: #9a5b00; }
.ltd-ready.bad { background: #fdecea; color: #b42318; }
.ltd-pulse { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0 0 1rem 0; }
.ltd-chip { font-size: 0.78rem; font-weight: 600; letter-spacing: 0.02em;
  padding: 0.28rem 0.55rem; border-radius: 999px; border: 1px solid #e5e7eb;
  background: #f8fafc; color: #374151; }
.ltd-chip.on { border-color: #a7f3d0; background: #ecfdf5; color: #047857; }
.ltd-chip.off { border-color: #fecaca; background: #fef2f2; color: #b91c1c; }
.ltd-chip.warn { border-color: #fde68a; background: #fffbeb; color: #92400e; }
.ltd-chip.muted { color: #6b7280; font-weight: 500; }
.ltd-hero { border: 1px solid #e5e7eb; border-radius: 10px; padding: 1rem 1.15rem;
  margin: 0 0 1rem 0; background: #fafbfc; }
.ltd-hero.open-long { border-color: #99f6e4; background: linear-gradient(180deg,#f0fdfa 0%,#fafbfc 70%); }
.ltd-hero.open-short { border-color: #fecaca; background: linear-gradient(180deg,#fef2f2 0%,#fafbfc 70%); }
.ltd-hero.flat { border-color: #e5e7eb; }
.ltd-hero-kicker { font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase;
  color: #6b7280; margin: 0 0 0.25rem 0; }
.ltd-hero-dir { font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em;
  margin: 0 0 0.35rem 0; line-height: 1.1; }
.ltd-hero-dir.buy { color: #0f766e; }
.ltd-hero-dir.sell { color: #b91c1c; }
.ltd-hero-dir.flat { color: #374151; }
.ltd-hero-ur { font-size: 2.1rem; font-weight: 700; letter-spacing: -0.03em;
  margin: 0.15rem 0 0.5rem 0; line-height: 1; }
.ltd-hero-ur.pos { color: #0f766e; }
.ltd-hero-ur.neg { color: #b91c1c; }
.ltd-hero-ur.zero { color: #6b7280; }
.ltd-hero-meta { font-size: 0.9rem; color: #374151; margin: 0; line-height: 1.45; }
.ltd-hero-sub { font-size: 0.8rem; color: #6b7280; margin: 0.35rem 0 0 0; }
.ltd-ctx { font-size: 0.82rem; color: #4b5563; margin: -0.35rem 0 0.85rem 0; line-height: 1.35; }
.ltd-ctx b { color: #1f2937; font-weight: 600; }
.ltd-trust { margin: 0.25rem 0 1rem 0; padding: 0.55rem 0.7rem;
  border-radius: 8px; border: 1px solid #e5e7eb; background: #f8fafc; }
.ltd-trust.ok { border-color: #99f6e4; background: #f0fdfa; }
.ltd-trust.bad { border-color: #fecaca; background: #fef2f2; }
.ltd-trust.warn { border-color: #fde68a; background: #fffbeb; }
.ltd-trust-row { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; margin: 0; }
.ltd-trust-label { font-size: 0.68rem; letter-spacing: 0.08em; text-transform: uppercase;
  color: #6b7280; margin: 0 0.25rem 0 0; font-weight: 600; }
.ltd-trust-detail { font-size: 0.8rem; color: #4b5563; margin: 0.4rem 0 0 0; line-height: 1.35; }
.ltd-trust-detail b { color: #1f2937; font-weight: 600; }
</style>
"""


def _inject_css() -> None:
  # Must re-inject every fragment tick. Streamlit fragment reruns replace the
  # fragment DOM (including prior <style>); a one-shot session_state gate then
  # leaves custom HTML as plain unstyled text.
  st.markdown(_SCOPED_CSS, unsafe_allow_html=True)
  st.session_state[_CSS_KEY] = True


def _live_dir():
  return resolve_live_bridge_dir()


def _start_live_bridge(model_ids: list[str]) -> bool:
  """Start Live Bridge from desk using roster đã chọn ở Trade Models."""
  ids = normalize_model_ids(model_ids)
  if not ids:
    st.error("Chưa chọn Trade Model — mở tab **Trade Models**.")
    return False
  cfg = bridge_bg.load_config()
  risk = float(cfg.get("risk_pct") or 1.0)
  poll = float(cfg.get("poll_sec") or 2.0)
  primary = ids[0]
  bdir = _live_dir()
  # Do not wipe trades — but drop sticky fill.json so Stop→Start cannot
  # re-open a ghost journal row (same class of bug as Simulate BestWinRate).
  try:
    from mt5_bridge.trade_journal import clear_sticky_fill_files
    clear_sticky_fill_files(bdir)
  except Exception:
    pass
  bridge_bg.save_config(
    model_id=primary,
    model_ids=ids,
    risk_pct=risk,
    poll_sec=poll,
    bridge_dir=str(bdir),
    enabled=True,
    loss_guard_tripped=False,
    loss_guard_tripped_at=None,
    loss_guard_tripped_reason=None,
    last_error=None,
  )
  bridge_bg.sync_bridge_roster(
    bridge_dir=bdir,
    model_ids=ids,
    risk_pct=risk,
  )
  ok = bridge_bg.start_worker(detached=True)
  if ok:
    ensure_chart_server(bdir, DEFAULT_MONITOR_PORT)
    as_ok, as_msg = enable_live_autostart()
    if as_ok:
      st.toast("Windows logon: tự chạy App + MT5 + Bridge")
    else:
      st.warning(as_msg)
  return ok


def _chip(label: str, *, kind: str = "muted") -> str:
  return f'<span class="ltd-chip {kind}">{escape(label)}</span>'


def _pulse_html(
  *,
  ea_online: bool,
  age_txt: str,
  bridge_running: bool,
  algo_on: bool | None,
  quote_txt: str,
  risk_txt: str | None = None,
) -> str:
  chips = [
    _chip(
      f"EA {'ONLINE' if ea_online else 'OFFLINE'} · {age_txt}",
      kind="on" if ea_online else "off",
    ),
    _chip(
      f"BRIDGE {'RUN' if bridge_running else 'STOP'}",
      kind="on" if bridge_running else "off",
    ),
    _chip(
      f"ALGO {'ON' if algo_on else 'OFF'}",
      kind="on" if algo_on else "off",
    ),
  ]
  if risk_txt:
    chips.append(_chip(risk_txt, kind="muted"))
  chips.append(_chip(quote_txt, kind="muted"))
  return f'<div class="ltd-pulse">{"".join(chips)}</div>'


def _risk_pips(trade: dict) -> str | None:
  try:
    entry = float(trade.get("entry_px") if trade.get("entry_px") is not None else trade.get("entry"))
    sl = float(trade["sl"])
  except (TypeError, ValueError, KeyError):
    return None
  dist = abs(entry - sl)
  if dist <= 0:
    return None
  # Pip size for major FX desks (EURUSD / GBPUSD / …)
  return f"{dist / 0.0001:.1f} pip"


def _hero_open_html(trade: dict, ur: float | None) -> str:
  direction = str(trade.get("direction") or trade.get("dir") or "?").upper()
  is_long = direction in ("BUY", "LONG")
  dir_cls = "buy" if is_long else "sell"
  hero_cls = "open-long" if is_long else "open-short"
  entry = fmt_px(trade.get("entry_px") or trade.get("entry"))
  sl = fmt_px(trade.get("sl"))
  tp = fmt_px(trade.get("tp"))
  if ur is None:
    ur_html = '<div class="ltd-hero-ur zero">uR —</div>'
  else:
    ur_cls = "pos" if ur > 0 else ("neg" if ur < 0 else "zero")
    ur_html = f'<div class="ltd-hero-ur {ur_cls}">{ur:+.2f}R</div>'
  risk = _risk_pips(trade)
  risk_bit = f" · risk {escape(risk)}" if risk else ""
  return f"""
<div class="ltd-hero {hero_cls}">
  <p class="ltd-hero-kicker">Vị thế đang mở</p>
  <p class="ltd-hero-dir {dir_cls}">{escape(direction)}</p>
  {ur_html}
  <p class="ltd-hero-meta">Entry <b>{escape(entry)}</b> · SL <b>{escape(sl)}</b> · TP <b>{escape(tp)}</b>{risk_bit}</p>
</div>
"""


def _context_html(*, week: str, strategy: str) -> str:
  """Single place for week + strategy (not repeated in hero/trust)."""
  week_s = escape(str(week)[:10] if week and week != "—" else "—")
  strat = escape(_short_strat(strategy, max_len=52))
  return (
    f'<p class="ltd-ctx">Tuần <b>{week_s}</b> · {strat}</p>'
  )


def _hero_flat_html(*, action: str, reason: str) -> str:
  act = (action or "FLAT").upper()
  if act in ("BUY", "LONG"):
    dir_cls = "buy"
  elif act in ("SELL", "SHORT"):
    dir_cls = "sell"
  else:
    dir_cls = "flat"
  reason_s = escape((reason or "")[:140])
  reason_html = f'<p class="ltd-hero-sub">{reason_s}</p>' if reason_s else ""
  return f"""
<div class="ltd-hero flat">
  <p class="ltd-hero-kicker">Không có lệnh mở · Decision</p>
  <p class="ltd-hero-dir {dir_cls}">{escape(act)}</p>
  {reason_html}
</div>
"""


def _short_strat(name: str | None, *, max_len: int = 42) -> str:
  """Human-scannable strategy label (drop chase suffix / truncate)."""
  s = str(name or "").strip()
  if not s or s == "—":
    return "—"
  if "|" in s:
    s = s.split("|", 1)[0].strip()
  if len(s) > max_len:
    return s[: max_len - 1] + "…"
  return s


def _sync_html(sync: dict) -> str:
  """EA↔App position sync strip — MT5 values are source of truth."""
  if not sync:
    return ""
  state = str(sync.get("state") or "offline")
  box_kind = {"ok": "ok", "warn": "warn", "bad": "bad"}.get(state, "warn")
  chips = ['<span class="ltd-trust-label">Đồng bộ lệnh</span>']
  headline = str(sync.get("headline") or "—")
  chip_kind = "on" if state == "ok" else ("off" if state == "bad" else "warn")
  chips.append(_chip(headline, kind=chip_kind))

  mt5_n = sync.get("mt5_positions")
  j_n = sync.get("journal_open_all")
  if mt5_n is not None and j_n is not None:
    match_kind = "on" if sync.get("positions_match") else "warn"
    chips.append(_chip(f"MT5 {mt5_n} · App {j_n}", kind=match_kind))

  if sync.get("ea_sync_timeout"):
    chips.append(_chip("TIMEOUT", kind="off"))

  ea_summary = str(sync.get("ea_summary") or "").strip()
  if ea_summary and ea_summary not in headline:
    chips.append(_chip(ea_summary[:48], kind="muted"))

  per_model = sync.get("per_model") or []
  if len(per_model) > 1:
    for pm in per_model:
      mid = str(pm.get("model_id") or "?")
      short = mid[:14] + "…" if len(mid) > 15 else mid
      st_pm = pm.get("state") or "ok"
      pk = "on" if st_pm == "ok" else ("off" if st_pm == "bad" else "warn")
      chips.append(_chip(
        f"{short} EA {pm.get('ea_status', '—')} · M{pm.get('mt5_open', 0)}/A{pm.get('journal_open', 0)}",
        kind=pk,
      ))

  detail = str(sync.get("detail") or "").strip()
  issues = [str(x) for x in (sync.get("issues") or []) if x]
  detail_html = ""
  if issues:
    detail_html = f'<p class="ltd-trust-detail"><b>MT5 (EA) là chuẩn:</b> {escape(issues[0])}</p>'
  elif detail:
    detail_html = f'<p class="ltd-trust-detail">{escape(detail)}</p>'

  return (
    f'<div class="ltd-trust {box_kind}">'
    f'<div class="ltd-trust-row">{"".join(chips)}</div>'
    f"{detail_html}"
    f"</div>"
  )


def _guard_html(
  *,
  guard_day: str,
  guard_week: str,
  guard_tripped: bool,
  guard_off: bool,
) -> str:
  """Loss guard strip only — Live là giai đoạn sau OOS, không hiện Parity."""
  kind = "bad" if guard_tripped else "ok"
  chips = ['<span class="ltd-trust-label">Guard</span>']
  if guard_off:
    chips.append(_chip("tắt", kind="muted"))
  else:
    g_kind = "off" if guard_tripped else "muted"
    g_txt = f"day {guard_day} · week {guard_week}"
    if guard_tripped:
      g_txt += " · TRIPPED"
    chips.append(_chip(g_txt, kind=g_kind))
  detail = ""
  if guard_tripped:
    detail = '<p class="ltd-trust-detail">Loss guard đã kích hoạt — Bridge FLAT / Stop.</p>'
  return (
    f'<div class="ltd-trust {kind}">'
    f'<div class="ltd-trust-row">{"".join(chips)}</div>'
    f"{detail}"
    f"</div>"
  )


def _render_dashboard_body() -> None:
  _inject_css()
  active = get_active_trade_model()
  snap = snapshot_live_desk()
  connection = snap["connection"]
  decision = snap["decision"]
  file_status = snap["file_status"]
  service_status = snap["service_status"]
  health = snap["health"]
  today_stats = snap["today_stats"]
  week_stats = snap["week_stats"]
  open_t = snap["open_trade"]
  ur = snap["unrealized_r"]

  model_ids = snap.get("model_ids") or []
  per_model = snap.get("per_model") or []
  if not model_ids:
    from gui.trade_model import get_bridge_runtime_model_ids
    model_ids = get_bridge_runtime_model_ids()
  if len(model_ids) > 1:
    from gui.trade_model import format_model_short
    parts = []
    for mid in model_ids[:4]:
      m = get_model_by_id(mid)
      parts.append(format_model_short(m, max_len=24) if m else mid[:16])
    model_line = f"{len(model_ids)} model · " + " · ".join(parts)
    if len(model_ids) > 4:
      model_line += f" +{len(model_ids) - 4}"
  elif model_ids:
    m0 = get_model_by_id(model_ids[0])
    model_line = format_model_label(m0) if m0 else model_ids[0][:28]
  else:
    model_line = format_model_label(active) if active else "Chưa chọn Trade Model"

  bridge_running = bool(service_status.get("running"))
  ea_online = bool(health.get("online"))
  try:
    cfg_risk = bridge_bg.load_config()
    risk_pct = float(cfg_risk.get("risk_pct") or 1.0)
  except Exception:
    risk_pct = 1.0
  n_models = max(1, len(model_ids))
  risk_txt = f"Risk {risk_pct:g}%/lệnh · max ~{risk_pct * n_models:g}%"

  st.markdown(
    f'<div class="ltd-wrap">'
    f'<p class="ltd-title">Live Trade</p>'
    f'<p class="ltd-model">{escape(model_line)}</p>'
    f"</div>",
    unsafe_allow_html=True,
  )

  # A. System pulse
  age = health.get("age_seconds")
  age_txt = f"{age:.0f}s" if age is not None else "—"
  bid, ask = connection.get("bid"), connection.get("ask")
  spread = connection.get("spread_points")
  if bid is not None and ask is not None:
    quote_txt = f"{fmt_px(bid)} / {fmt_px(ask)}"
    if spread is not None:
      quote_txt += f" · {spread} pts"
  else:
    quote_txt = "Quote —"
  # B. Context once — week + strategy (shared by hero/trust, no repeats)
  action = str(decision.get("action") or service_status.get("last_action") or "FLAT").upper()
  strat = decision.get("strategy_name") or file_status.get("strategy_name") or "—"
  week = decision.get("week_start") or file_status.get("week_start") or "—"
  reason = str(decision.get("reason") or file_status.get("reason") or "")

  st.markdown(
    _pulse_html(
      ea_online=ea_online,
      age_txt=age_txt,
      bridge_running=bridge_running,
      algo_on=bool(health.get("trade_allowed")),
      quote_txt=quote_txt,
      risk_txt=risk_txt,
    )
    + _context_html(week=str(week), strategy=str(strat)),
    unsafe_allow_html=True,
  )

  # Start/Stop — một nút theo trạng thái; điều hướng Bridge nằm ở sidebar
  if bridge_running:
    if st.button(
      "Stop Bridge",
      type="secondary",
      use_container_width=True,
      key="live_dash_stop_bridge",
    ):
      bridge_bg.stop_worker()
      as_ok, as_msg = disable_live_autostart()
      if as_ok:
        st.toast("Đã Stop Bridge · đã gỡ auto-start Windows")
      else:
        st.toast("Đã Stop Bridge")
        st.warning(as_msg)
      st.rerun()
  else:
    start_label = (
      "Start Bridge Live" if ea_online else "Deploy EA Live + Start Bridge"
    )
    if st.button(
      start_label,
      type="primary",
      use_container_width=True,
      key="live_dash_start_bridge",
      disabled=not model_ids,
      help=(
        "Bật Bridge với roster đang chọn. Đồng thời đăng ký tự chạy App + MT5 "
        "sau khi Windows đăng nhập (phòng restart)."
        if ea_online else
        "Live EA offline — Deploy Live rồi Start Bridge trong một bước. "
        "Start cũng đăng ký tự chạy App + MT5 sau Windows logon."
      ),
    ):
      ea_ready = ea_online
      if not ea_ready:
        from gui.mt5_deploy_ui import deploy_ea_and_wait_online, ea_live_name
        if bridge_bg.is_running():
          st.warning("Live Bridge đang chạy — không Deploy lại.")
        else:
          with st.spinner(f"Đang deploy `{ea_live_name()}` (tối đa ~90s)…"):
            ok_dep, detail = deploy_ea_and_wait_online(
              "Live",
              _live_dir(),
              enable_trading=True,
              wait_sec=20.0,
              deploy_timeout_sec=90.0,
            )
          if not ok_dep:
            st.error(detail.split("\n", 1)[0])
            if "\n" in detail:
              st.code(detail.split("\n", 1)[1])
          else:
            st.toast(f"Đã deploy `{ea_live_name()}` · EA online")
            ea_ready = True
      if ea_ready:
        if _start_live_bridge(model_ids):
          st.toast(f"Đã Start Bridge · {len(model_ids)} model")
          st.rerun()
        else:
          st.error("Không Start được Bridge — xem tab **Kỹ thuật** / log.")
    if ea_online:
      st.caption(
        "EA online · Bridge tắt — bấm Start để trade với roster đã chọn."
      )
    if not model_ids:
      st.warning("Chưa có Trade Model trong roster — mở tab **Trade Models**.")

  if bridge_running and autostart_is_marked():
    st.caption("Windows restart: tự mở App + XM MT5 + Bridge cho desk này. Stop sẽ gỡ auto-start.")

  sync = snap.get("sync_status") or {}
  if sync:
    st.markdown(_sync_html(sync), unsafe_allow_html=True)

  desync = sync.get("desync") or snap.get("journal_mt5_desync")
  show_sync_btn = (
    bool(health.get("online"))
    and sync.get("state") in ("bad", "warn")
    and not sync.get("positions_match")
  )
  if desync and desync.get("fixable"):
    st.error(str(desync.get("message") or "App và MT5 đang lệch số lệnh mở."))
    c_fix, c_sync = st.columns(2)
    with c_fix:
      if st.button(
        "Xóa lệnh treo trên App",
        type="primary",
        use_container_width=True,
        key="live_dash_clear_ghost_opens",
        help="Chỉ khi MT5 đã hết lệnh mở.",
      ):
        from mt5_bridge.trade_journal import (
          ea_position_count,
          reconcile_journal_from_ea_positions,
          request_live_redecide,
        )
        ea_n = ea_position_count(snap.get("connection"))
        if ea_n is None:
          st.warning("Chưa đọc được số lệnh MT5 — đợi EA heartbeat rồi thử lại.")
        elif ea_n > 0:
          st.warning("MT5 vẫn còn lệnh mở — đóng trên MT5 hoặc dùng «Đồng bộ từ MT5».")
        else:
          reconcile_journal_from_ea_positions(
            _live_dir(),
            connection=snap.get("connection") if isinstance(snap.get("connection"), dict) else None,
            require_fresh_heartbeat=False,
          )
          request_live_redecide(_live_dir())
          st.toast("Đã đồng bộ từ MT5 · Bridge tính lại decision")
          st.rerun()
    with c_sync:
      if st.button(
        "Đồng bộ từ MT5",
        use_container_width=True,
        key="live_dash_sync_from_mt5",
        help="Cập nhật App từ positions.json (SL/TP/entry thực tế trên MT5).",
      ):
        from mt5_bridge.trade_journal import (
          reconcile_journal_from_ea_positions,
          request_live_redecide,
        )
        out = reconcile_journal_from_ea_positions(
          _live_dir(),
          connection=snap.get("connection") if isinstance(snap.get("connection"), dict) else None,
          require_fresh_heartbeat=False,
        )
        request_live_redecide(_live_dir())
        st.toast(
          f"Đồng bộ MT5: ghost={out.get('closed_ghosts', 0)} "
          f"update={out.get('updated', 0)} import={out.get('imported', 0)}"
        )
        st.rerun()
  elif show_sync_btn:
    if st.button(
      "Đồng bộ từ MT5",
      type="secondary",
      use_container_width=True,
      key="live_dash_sync_from_mt5_soft",
      help="Lấy SL/TP/entry và số lệnh mở từ EA — MT5 là nguồn đúng.",
    ):
      from mt5_bridge.trade_journal import (
        reconcile_journal_from_ea_positions,
        request_live_redecide,
      )
      out = reconcile_journal_from_ea_positions(
        _live_dir(),
        connection=snap.get("connection") if isinstance(snap.get("connection"), dict) else None,
        require_fresh_heartbeat=False,
      )
      request_live_redecide(_live_dir())
      st.toast(
        f"Đồng bộ MT5: ghost={out.get('closed_ghosts', 0)} "
        f"update={out.get('updated', 0)} import={out.get('imported', 0)}"
      )
      st.rerun()
  elif desync and not desync.get("fixable"):
    st.warning(str(desync.get("message") or "App và MT5 đang lệch."))

  # C. Hero — position(s) or decision
  opens = snap.get("open_trades") or ([] if not open_t else [open_t])
  if opens:
    if len(opens) == 1:
      st.markdown(_hero_open_html(opens[0], ur), unsafe_allow_html=True)
    else:
      st.markdown(
        f'<div class="ltd-hero open-long"><p class="ltd-hero-kicker">Open</p>'
        f'<p class="ltd-hero-dir buy">{len(opens)} lệnh mở</p>'
        f'<p class="ltd-hero-meta">Tổng unrealized xem từng model bên dưới</p></div>',
        unsafe_allow_html=True,
      )
  else:
    st.markdown(
      _hero_flat_html(action=action, reason=reason),
      unsafe_allow_html=True,
    )

  from gui.signal_wait_ui import wait_side_caption

  # D. Scoreboard — aggregate (all models)
  today_r = float(today_stats.get("total_r") or 0.0) if today_stats.get("n_trades") else 0.0
  week_r = float(week_stats.get("total_r") or 0.0) if week_stats.get("n_trades") else 0.0
  wr = today_stats.get("win_rate_pct")
  n_today = int(today_stats.get("n_trades") or 0)

  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Today R (tổng)", f"{today_r:+.2f}")
  c2.metric("Week R (tổng)", f"{week_r:+.2f}")
  c3.metric("WR hôm nay", f"{float(wr):.0f}%" if wr is not None else "—")
  c4.metric("Closed hôm nay", n_today)
  if snap.get("open_manual"):
    st.caption(
      f"Có **{snap['open_manual']}** lệnh mở mode sửa — không tính vào R auto."
    )
  if snap.get("open_auto"):
    st.caption(f"Lệnh auto đang mở: **{snap['open_auto']}**")

  # D2. Per-model breakdown
  sync_by_id = {
    str(p.get("model_id")): p
    for p in (sync.get("per_model") or [])
    if p.get("model_id")
  }
  if len(per_model) >= 1:
    with st.expander(f"Theo từng model ({len(per_model)})", expanded=len(per_model) > 1):
      rows = []
      for pm in per_model:
        mid = pm.get("model_id")
        m = get_model_by_id(mid) if mid else None
        ts = pm.get("today_stats") or {}
        ws = pm.get("week_stats") or {}
        ot_m = pm.get("open_trade")
        ur_m = pm.get("unrealized_r")
        wait = pm.get("signal_wait") if isinstance(pm.get("signal_wait"), dict) else {}
        sm = sync_by_id.get(str(mid)) or {}
        rows.append({
          "Model": format_model_label(m) if m else (mid or "?")[:28],
          "Magic": pm.get("magic"),
          "EA sync": sm.get("ea_status") or "—",
          "M/A open": f"{sm.get('mt5_open', '—')}/{sm.get('journal_open', '—')}",
          "Open": (
            f"{ot_m.get('direction')} uR={ur_m:+.2f}" if ot_m and ur_m is not None
            else (str(ot_m.get("direction")) if ot_m else "—")
          ),
          "BUY": wait_side_caption(wait.get("buy")),
          "SELL": wait_side_caption(wait.get("sell")),
          "Today R": ts.get("total_r"),
          "Week R": ws.get("total_r"),
          "N today": ts.get("n_trades") or 0,
          "Last": pm.get("last_action") or "—",
        })
      import pandas as pd
      st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

  # E. Guard only — Live là giai đoạn sau OOS, không so Parity tuần
  guard_day = guard_week = "—"
  guard_tripped = False
  guard_off = True
  try:
    cfg = bridge_bg.load_config()
    guard = loss_guard_status(cfg, bridge_dir=_live_dir(), trades=snap["trades"])
    guard_off = not bool(guard.get("enabled"))
    if not guard_off:
      guard_day = f"{guard.get('day_streak')}/{guard.get('max_day')}"
      guard_week = f"{guard.get('week_streak')}/{guard.get('max_week')}"
      guard_tripped = bool(guard.get("tripped"))
  except Exception:
    pass

  st.markdown(
    _guard_html(
      guard_day=guard_day,
      guard_week=guard_week,
      guard_tripped=guard_tripped,
      guard_off=guard_off,
    ),
    unsafe_allow_html=True,
  )

  from gui.signal_wait_ui import render_signal_wait
  render_signal_wait(file_status=file_status, decision=decision)


@st.fragment(run_every=timedelta(seconds=5))
def _live_trade_fragment() -> None:
  _render_dashboard_body()


def render():
  render_page_header(ALL_ITEMS["live_trade"], show_workspace=False)

  (
    tab_now,
    tab_models,
    tab_risk,
    tab_stats,
    tab_chart,
    tab_health,
    tab_tech,
    tab_hist,
  ) = st.tabs([
    "Now",
    "Trade Models",
    "Risk control",
    "Thống kê",
    "Biểu đồ",
    LABEL_TAB_REWARD,
    "Kỹ thuật",
    "Test lịch sử",
  ])

  with tab_now:
    _inject_css()
    _live_trade_fragment()

  with tab_models:
    render_tab_models()

  with tab_risk:
    render_tab_risk_control()

  with tab_stats:
    render_tab_stats()

  with tab_chart:
    render_tab_chart()

  with tab_health:
    render_tab_health()

  with tab_tech:
    render_tab_tech()

  with tab_hist:
    render_tab_history()
