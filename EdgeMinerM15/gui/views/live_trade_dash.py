"""Live Trade — daily trader desk (one viewport, no chart / Start-Stop)."""
from __future__ import annotations

from datetime import timedelta
from html import escape

import streamlit as st

from gui.bridge_desk_stats import fmt_px, snapshot_live_desk
from gui.bridge_model_monitor import compare_live_week_to_oos
from gui.live_readiness import assess_live_readiness, render_live_readiness
from gui.trade_model import format_model_label, get_active_trade_model
from gui.ui_preferences import set_widget_preference
from mt5_bridge import background as bridge_bg
from mt5_bridge.loss_guard import loss_guard_status
from mt5_bridge.protocol import BRIDGE_DIR

_CSS_KEY = "_live_trade_dash_css_v4"  # bump when CSS changes (debug/cache only)

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


def _go_mt5_bridge() -> None:
  set_widget_preference("nav_page", "mt5_bridge", "navigation.page")
  st.rerun()


def _chip(label: str, *, kind: str = "muted") -> str:
  return f'<span class="ltd-chip {kind}">{escape(label)}</span>'


def _pulse_html(
  *,
  ea_online: bool,
  age_txt: str,
  bridge_running: bool,
  algo_on: bool | None,
  quote_txt: str,
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
    _chip(quote_txt, kind="muted"),
  ]
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
  # EURUSD M15 desk: 1 pip = 0.0001
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


def _parity_status_label(status: str | None) -> tuple[str, str]:
  """Return (chip_label, chip_kind)."""
  s = str(status or "")
  if s == "match":
    return "MATCH", "on"
  if s == "mismatch":
    return "LỆCH", "off"
  if s == "week_not_in_report":
    return "Ngoài OOS", "warn"
  if s == "waiting_strategy":
    return "Chờ strategy", "warn"
  if s in ("no_decision", "no_model", "no_report"):
    return "Chưa đủ data", "muted"
  return (s.upper() if s else "—"), "muted"


def _ready_badge(verdict: str, summary: str) -> str:
  kind = "ok" if verdict == "ready" else ("warn" if verdict == "caution" else "bad")
  label = {
    "ready": "READY",
    "caution": "CAUTION",
    "blocked": "BLOCKED",
  }.get(verdict, verdict.upper())
  # Keep badge short — full checklist is in expander
  short_map = {
    "ready": "OK để theo dõi Live",
    "caution": "Có cảnh báo — xem checklist",
    "blocked": "Chưa sẵn sàng — xem checklist",
  }
  short = escape(short_map.get(verdict) or (summary or "")[:80])
  return f'<span class="ltd-ready {kind}"><b>{label}</b> · {short}</span>'


def _trust_html(
  *,
  parity_status: str | None,
  live_strat: str | None,
  oos_strat: str | None,
  oos_r: float | None,
  guard_day: str,
  guard_week: str,
  guard_tripped: bool,
  guard_off: bool,
) -> str:
  """Parity / OOS R / Guard only — week+strategy live in _context_html."""
  kind = "ok"
  if parity_status == "mismatch" or guard_tripped:
    kind = "bad"
  elif parity_status in ("week_not_in_report", "waiting_strategy", "no_report"):
    kind = "warn"

  p_label, p_chip = _parity_status_label(parity_status)
  chips = [
    '<span class="ltd-trust-label">Parity</span>',
    _chip(p_label, kind=p_chip),
  ]
  if oos_r is not None:
    try:
      chips.append(_chip(f"OOS {float(oos_r):+.1f}R", kind="muted"))
    except (TypeError, ValueError):
      pass

  chips.append('<span class="ltd-trust-label" style="margin-left:0.35rem">Guard</span>')
  if guard_off:
    chips.append(_chip("tắt", kind="muted"))
  else:
    g_kind = "off" if guard_tripped else "muted"
    g_txt = f"day {guard_day} · week {guard_week}"
    if guard_tripped:
      g_txt += " · TRIPPED"
    chips.append(_chip(g_txt, kind=g_kind))

  # Detail only when something needs attention (avoid repeating strategy on MATCH)
  live_s = _short_strat(live_strat)
  oos_s = _short_strat(oos_strat)
  detail = ""
  if parity_status == "mismatch":
    detail = (
      f'Live <b>{escape(live_s)}</b> ≠ Health <b>{escape(oos_s)}</b>'
      " — Stop/Start Bridge hoặc refresh Health"
    )
  elif parity_status == "week_not_in_report":
    detail = "Tuần live mới hơn tip OOS — bình thường nếu đang live tuần mới"
  elif parity_status in ("waiting_strategy", "no_decision", "no_model", "no_report"):
    detail = "Chưa đối chiếu được với Health tuần này"

  detail_html = f'<p class="ltd-trust-detail">{detail}</p>' if detail else ""
  return (
    f'<div class="ltd-trust {kind}">'
    f'<div class="ltd-trust-row">{"".join(chips)}</div>'
    f"{detail_html}"
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

  ready = assess_live_readiness(
    active,
    decision=decision,
    file_status=file_status,
    include_bridge=True,
  )
  verdict = str(ready.get("verdict") or "blocked")

  model_line = format_model_label(active) if active else "Chưa chọn Trade Model"
  st.markdown(
    f'<div class="ltd-wrap">'
    f'<p class="ltd-title">Live Trade</p>'
    f'<p class="ltd-model">{escape(model_line)}</p>'
    f'{_ready_badge(verdict, str(ready.get("summary") or ""))}'
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
  fp = decision.get("conditions_fp") or file_status.get("conditions_fp")

  st.markdown(
    _pulse_html(
      ea_online=bool(health.get("online")),
      age_txt=age_txt,
      bridge_running=bool(service_status.get("running")),
      algo_on=bool(health.get("trade_allowed")),
      quote_txt=quote_txt,
    )
    + _context_html(week=str(week), strategy=str(strat)),
    unsafe_allow_html=True,
  )

  # C. Hero — position or decision only
  if open_t:
    st.markdown(_hero_open_html(open_t, ur), unsafe_allow_html=True)
  else:
    st.markdown(
      _hero_flat_html(action=action, reason=reason),
      unsafe_allow_html=True,
    )

  # D. Scoreboard — 4 numbers only
  today_r = float(today_stats.get("total_r") or 0.0) if today_stats.get("n_trades") else 0.0
  week_r = float(week_stats.get("total_r") or 0.0) if week_stats.get("n_trades") else 0.0
  wr = today_stats.get("win_rate_pct")
  n_today = int(today_stats.get("n_trades") or 0)

  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Today R", f"{today_r:+.2f}")
  c2.metric("Week R", f"{week_r:+.2f}")
  c3.metric("WR hôm nay", f"{float(wr):.0f}%" if wr is not None else "—")
  c4.metric("Closed hôm nay", n_today)
  if snap.get("open_manual"):
    st.caption(
      f"Có **{snap['open_manual']}** lệnh mở mode sửa — không tính vào R auto."
    )

  # E. Trust — status only (week/strategy already in context line)
  parity = compare_live_week_to_oos(
    active,
    week_start=week if week != "—" else None,
    strategy_name=strat if strat != "—" else None,
    conditions_fp=fp,
  )
  pst = parity.get("status")
  live_name = parity.get("live_strategy") or strat
  oos_name = parity.get("oos_strategy")
  oos_r = parity.get("oos_r")

  guard_day = guard_week = "—"
  guard_tripped = False
  guard_off = True
  try:
    cfg = bridge_bg.load_config()
    guard = loss_guard_status(cfg, bridge_dir=BRIDGE_DIR, trades=snap["trades"])
    guard_off = not bool(guard.get("enabled"))
    if not guard_off:
      guard_day = f"{guard.get('day_streak')}/{guard.get('max_day')}"
      guard_week = f"{guard.get('week_streak')}/{guard.get('max_week')}"
      guard_tripped = bool(guard.get("tripped"))
  except Exception:
    pass

  st.markdown(
    _trust_html(
      parity_status=pst,
      live_strat=str(live_name) if live_name else None,
      oos_strat=str(oos_name) if oos_name else None,
      oos_r=float(oos_r) if oos_r is not None else None,
      guard_day=guard_day,
      guard_week=guard_week,
      guard_tripped=guard_tripped,
      guard_off=guard_off,
    ),
    unsafe_allow_html=True,
  )

  # F. Footer
  render_live_readiness(
    active,
    decision=decision,
    file_status=file_status,
    include_bridge=True,
    expanded=False,
    key_prefix="live_dash_ready",
  )
  if st.button(
    "MT5 Bridge — Start/Stop · chart",
    type="secondary",
    use_container_width=True,
    key="live_dash_goto_bridge",
  ):
    _go_mt5_bridge()


@st.fragment(run_every=timedelta(seconds=5))
def _live_trade_fragment() -> None:
  _render_dashboard_body()


def render():
  _inject_css()
  _live_trade_fragment()
