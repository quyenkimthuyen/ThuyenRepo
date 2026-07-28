"""MT5 Bridge — Trader desk: EA live status, decision, open risk, PnL."""
from __future__ import annotations

from datetime import date, timedelta
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from gui.mt5_live_chart import build_ea_chart, connection_health, load_ea_chart_data, load_sim_chart_data
from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header
from gui.trade_model import get_active_trade_model, render_shared_trade_model_banner
from gui.ui_preferences import preference_callback, restore_widget, set_preference
from mt5_bridge.history_sync import get_history_status, start_history_sync
from mt5_bridge import background as bridge_bg
from mt5_bridge.comm_log import append_event
from mt5_bridge.live_monitor_server import ensure_chart_server, monitor_port_for
from mt5_bridge.protocol import (
  DEFAULT_MODEL_ID,
  bar_path,
  command_ack_path,
  command_path,
  connection_path,
  decision_path,
  fill_path,
  pip_size_from_quotes,
  prices_from_pips,
  read_json,
  status_path,
  write_manual_close_command,
  write_manual_market_command,
)
from mt5_bridge.trade_journal import (
  clear_trades,
  compute_stats,
  filter_trades,
  load_trades,
  trade_mode,
)
from config import get_active_tf, set_active_tf
from runtime_profiles import get_profile


def _bridge_tf() -> str:
  label = st.session_state.get("mt5_bridge_tf") or get_active_tf()
  return str(label).upper()


def _sk(base: str) -> str:
  """Session / widget key scoped to active Bridge TF."""
  return f"{base}_{_bridge_tf()}"


def _pref(base: str) -> str:
  """Persisted preference key scoped to active Bridge TF."""
  return f"{base}_{_bridge_tf()}"


def _save_bridge_runtime_settings() -> None:
  active = get_active_trade_model(tf=_bridge_tf())
  bridge_bg.save_config(
    tf=_bridge_tf(),
    model_id=(active or {}).get("id") or DEFAULT_MODEL_ID,
    risk_pct=float(st.session_state.get(_sk("mt5_risk_pct"), 1.0)),
    poll_sec=float(st.session_state.get(_sk("mt5_poll_sec"), 2.0)),
  )


def _bridge_mode() -> str:
  """Return 'live' or 'sim' from the page mode switcher."""
  label = st.session_state.get("mt5_bridge_mode") or "Live"
  return "sim" if str(label).startswith("Simulate") else "live"


def _active_bridge_dir():
  return get_profile(_bridge_tf(), _bridge_mode()).bridge_dir


def _mode_label() -> str:
  return "Simulate" if _bridge_mode() == "sim" else "Live"


def _render_mode_switcher() -> str:
  """Live/Simulate only — TF comes from sidebar Timeframe Bridge."""
  tf = get_active_tf()
  st.session_state["mt5_bridge_tf"] = tf
  set_active_tf(tf)

  modes = ["Live", "Simulate"]
  restore_widget(
    "mt5_bridge_mode", "Live",
    preference_key="mt5.bridge_mode",
    options=modes,
  )
  st.radio(
    "Chế độ",
    modes,
    horizontal=True,
    key="mt5_bridge_mode",
    on_change=preference_callback("mt5_bridge_mode", "mt5.bridge_mode"),
  )
  mode = _bridge_mode()
  bdir = _active_bridge_dir()
  profile = get_profile(_bridge_tf(), mode)
  ea = (
    f"ForgeBridge{_bridge_tf()}Sim" if mode == "sim"
    else f"ForgeBridge{_bridge_tf()}"
  )
  st.caption(
    f"**{_bridge_tf()} · {_mode_label()}** · `{bdir.name}` · "
    f"magic `{profile.magic}` · `{ea}`"
  )
  return mode


def _render_conditions_alignment(
  *,
  active: dict | None,
  decision: dict,
  file_status: dict,
) -> None:
  """Show that Bridge remine uses the same strategy conditions as Health."""
  from mt5_bridge.models import (
    conditions_fingerprint,
    describe_strategy_conditions,
    get_model_run_params,
  )

  if not active:
    st.caption("Chưa chọn Trade Model.")
    return

  model_params = get_model_run_params(active, active.get("id"))
  model_desc = describe_strategy_conditions(model_params)
  model_fp = model_desc["conditions_fp"]
  live_fp = (
    decision.get("conditions_fp")
    or file_status.get("conditions_fp")
  )
  live_desc = file_status.get("run_conditions") or decision.get("run_conditions") or {}

  if live_fp and live_fp != model_fp:
    st.warning(
      f"Bridge fp lệch model — Stop/Start service. "
      f"`{live_fp}` ≠ `{model_fp}`"
    )
  elif live_fp:
    pass  # matched — quiet on success
  elif live_desc:
    live_check = conditions_fingerprint({
      **model_params,
      **{k: live_desc.get(k) for k in (
        "train_weeks", "kb_profile", "kb_snapshot", "feature_profile",
        "spread_pips", "slippage_pips", "use_learning",
      ) if live_desc.get(k) is not None},
      "mining_search_space": active.get("mining_search_space"),
      "trade_model_id": active.get("id"),
    })
    if live_check != model_fp:
      st.caption("Chưa xác nhận fingerprint — Start Bridge để khớp Sức khỏe.")
  else:
    st.caption("Chưa có decision — Start Bridge để xác nhận model.")


def _render_live_oos_parity(
  *,
  active: dict | None,
  decision: dict,
  file_status: dict,
) -> None:
  """Live desk: compare this week strategy vs Health OOS weekly_log."""
  from gui.bridge_model_monitor import compare_live_week_to_oos

  week = decision.get("week_start") or file_status.get("week_start")
  strat = decision.get("strategy_name") or file_status.get("strategy_name")
  fp = decision.get("conditions_fp") or file_status.get("conditions_fp")
  with st.expander("Parity tuần này · Live vs Health OOS", expanded=False):
    parity = compare_live_week_to_oos(
      active,
      week_start=week,
      strategy_name=strat,
      conditions_fp=fp,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Tuần", str(parity.get("week_start") or "—"))
    fp_ok = parity.get("fp_match")
    c2.metric(
      "conditions_fp",
      "khớp" if fp_ok is True else ("lệch" if fp_ok is False else "—"),
    )
    sm = parity.get("strategy_match")
    c3.metric(
      "strategy",
      "MATCH" if sm is True else ("LỆCH" if sm is False else "—"),
    )
    st.caption(
      f"Live `{parity.get('live_strategy') or '—'}` · "
      f"OOS `{parity.get('oos_strategy') or '—'}`"
    )
    status = parity.get("status")
    msg = parity.get("message") or ""
    if status == "match" and fp_ok is not False:
      st.success(msg)
    elif status == "mismatch" or fp_ok is False:
      st.warning(msg if status == "mismatch" else (
        f"fp Live `{parity.get('live_fp')}` ≠ model `{parity.get('model_fp')}`. " + msg
      ))
    elif status == "week_not_in_report":
      st.info(msg)
    elif msg:
      st.caption(msg)



def _fmt_px(value) -> str:
  try:
    return f"{float(value):.5f}"
  except (TypeError, ValueError):
    return "—"


def _unrealized_r(trade: dict, connection: dict) -> float | None:
  """Estimate open R from live bid/ask vs entry/SL."""
  try:
    entry = float(trade.get("entry_px") if trade.get("entry_px") is not None else trade.get("entry"))
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


def _parse_ui_date(val) -> date | None:
  if val is None or val == "":
    return None
  if isinstance(val, date):
    return val
  if hasattr(val, "date") and callable(getattr(val, "date", None)):
    try:
      return val.date()
    except Exception:
      pass
  s = str(val).strip().replace("/", "-").replace(".", "-")[:10]
  try:
    return date.fromisoformat(s)
  except Exception:
    return None


def _sim_feed_window() -> tuple[date | None, date | None]:
  """History Feed Từ/Đến — session widgets, then sim_state (per TF)."""
  d0 = _parse_ui_date(st.session_state.get(_sk("sim_ea_from")))
  d1 = _parse_ui_date(st.session_state.get(_sk("sim_ea_to")))
  if d0 and d1:
    return d0, d1
  try:
    from mt5_bridge.ea_simulator import load_sim_state
    sim = load_sim_state(get_profile(_bridge_tf(), "sim").bridge_dir)
    d0 = d0 or _parse_ui_date(sim.get("date_from"))
    d1 = d1 or _parse_ui_date(sim.get("date_to") or sim.get("last_bar"))
  except Exception:
    pass
  return d0, d1


def _months_spanning(d0: date, d1: date) -> list[str]:
  """YYYY-MM labels from d0 through d1 inclusive."""
  if d1 < d0:
    d0, d1 = d1, d0
  months: list[str] = []
  y, m = d0.year, d0.month
  while (y, m) <= (d1.year, d1.month):
    months.append(f"{y:04d}-{m:02d}")
    m += 1
    if m > 12:
      m = 1
      y += 1
  return months


def _month_bounds(ym: str) -> tuple[date, date]:
  y, m = int(ym[:4]), int(ym[5:7])
  start = date(y, m, 1)
  if m == 12:
    end = date(y + 1, 1, 1) - timedelta(days=1)
  else:
    end = date(y, m + 1, 1) - timedelta(days=1)
  return start, end


def _open_trade(trades: list[dict]) -> dict | None:
  for trade in reversed(trades):
    if str(trade.get("status") or "").upper() == "OPEN":
      return trade
  return None


def _period_stats(trades: list[dict], *, today: date) -> tuple[dict, dict]:
  """Desk PnL = Auto only (Trade Model). Manual-edited fills stay out."""
  week_from = today - timedelta(days=today.weekday())
  today_stats = compute_stats(
    filter_trades(trades, date_from=today, date_to=today, mode="auto"),
  )
  week_stats = compute_stats(
    filter_trades(trades, date_from=week_from, date_to=today, mode="auto"),
  )
  return today_stats, week_stats


def _render_error_banner(
  *,
  file_status: dict,
  service_status: dict,
  decision: dict,
  active_model_id: str | None,
) -> None:
  errors: list[str] = []
  if service_status.get("last_error"):
    errors.append(str(service_status["last_error"]))
  state = str(file_status.get("state") or "").lower()
  if state == "error" and file_status.get("error"):
    errors.append(str(file_status["error"]))
  decision_model = decision.get("model_id") or file_status.get("model_id")
  if active_model_id and decision_model and decision_model != active_model_id:
    errors.append(
      f"Model lệch: decision=`{decision_model}` · active=`{active_model_id}`"
    )
  if errors:
    st.error(" · ".join(dict.fromkeys(errors)))


def _render_trader_desk(*, include_live_metrics: bool = True) -> None:
  """Desk strip + banners + today/week PnL (refreshed by fragment).

  include_live_metrics=False (Simulate): skip Streamlit metric strip — FEED/Quote
  update smoothly inside the chart iframe instead (avoids 5s remount chop).
  """
  bridge_dir = _active_bridge_dir()
  mode = _bridge_mode()
  connection = read_json(connection_path(bridge_dir)) or {}
  decision = read_json(decision_path(bridge_dir)) or {}
  file_status = read_json(status_path(bridge_dir)) or {}
  service_status = (
    bridge_bg.get_status(tf=_bridge_tf()) if mode == "live"
    else bridge_bg.get_sim_status(tf=_bridge_tf())
  )
  active = get_active_trade_model(tf=_bridge_tf())
  active_id = (active or {}).get("id")
  trades = load_trades(bridge_dir)
  stale = 30.0 if mode == "sim" else 30.0
  health = connection_health(connection, stale_after_seconds=stale, bridge_dir=bridge_dir)
  today = date.today()
  today_stats, week_stats = _period_stats(trades, today=today)
  action = str(decision.get("action") or service_status.get("last_action") or "—").upper()

  _render_error_banner(
    file_status=file_status,
    service_status=service_status if mode == "live" else {},
    decision=decision,
    active_model_id=active_id,
  )

  if include_live_metrics:
    # --- 5-column trader strip ---
    c1, c2, c3, c4, c5 = st.columns(5)
    age = health.get("age_seconds")
    age_txt = f"{age:.0f}s" if age is not None else "—"
    ea_label = "FEED" if mode == "sim" else "EA"
    if health.get("online") or (mode == "sim" and service_status.get("running")):
      c1.metric(ea_label, f"ONLINE · {age_txt}")
    else:
      c1.metric(ea_label, f"OFFLINE · {age_txt}")
      if mode == "live":
        st.warning(
          f"EA **{_bridge_tf()}** không heartbeat (`connection.json` {age_txt}). "
          "Trên XM MT5: mở chart EURUSD đúng TF · EA ForgeBridge đang attach · "
          "nút **AutoTrading** bật · rồi **Deploy 4 EA** lại nếu cần."
        )

    bid, ask = connection.get("bid"), connection.get("ask")
    spread = connection.get("spread_points")
    if bid is not None and ask is not None:
      c2.metric("Quote", f"{_fmt_px(bid)} / {_fmt_px(ask)}")
    else:
      c2.metric("Quote", "—")
    c2.caption(f"Spread: {spread if spread is not None else '—'} pts")

    if mode == "sim":
      ea_st = service_status.get("ea_status") or "—"
      c3.metric("Feed", str(service_status.get("status") or "idle").upper())
      c3.caption(
        f"EA `{ea_st}` · {service_status.get('bars_done') or 0}/"
        f"{service_status.get('bars_total') or '—'}"
      )
    else:
      algo_on = health.get("trade_allowed")
      c3.metric("AutoTrade", "ON" if algo_on else "OFF")
      c3.caption(f"Acct {connection.get('account') or '—'}")

    reason = str(decision.get("reason") or file_status.get("reason") or "—")
    c4.metric("Decision", action)
    c4.caption(reason[:48] if reason else "—")

    risk = decision.get("risk_pct")
    if risk is None:
      risk = service_status.get("risk_pct") or bridge_bg.load_config(tf=_bridge_tf()).get("risk_pct")
    slots = decision.get("slots_remaining")
    if slots is None:
      slots = "—"
    c5.metric("Risk / Slots", f"{float(risk):.1f}% · {slots}" if risk is not None else f"— · {slots}")

  # Strategy line
  st.caption(
    f"Chiến lược: `{decision.get('strategy_name') or 'đang chờ mine'}` · "
    f"tuần `{decision.get('week_start') or '—'}` · "
    f"TM `{decision.get('model_id') or service_status.get('model_id') or '—'}`"
  )
  _render_conditions_alignment(
    active=active,
    decision=decision,
    file_status=file_status,
  )
  if mode != "sim":
    _render_live_oos_parity(
      active=active,
      decision=decision,
      file_status=file_status,
    )

  if mode == "live":
    svc = "OFF"
    if service_status.get("running"):
      runtime = service_status.get("runtime_mode") or "on"
      pid = service_status.get("service_pid")
      svc = f"ON · {runtime}" + (f" · pid {pid}" if pid else "")
    st.caption(
      f"Service `{svc}` · Bridge `{file_status.get('state') or '—'}` · "
      f"Bar `{str(service_status.get('last_bar') or '—')[:19]}`"
    )

  # --- Open position / pending SIGNAL ---
  open_trade = _open_trade(trades)
  if open_trade:
    ur = _unrealized_r(open_trade, connection)
    ur_txt = f"{ur:+.2f}R" if ur is not None else "—"
    direction = str(open_trade.get("direction") or open_trade.get("dir") or "?").upper()
    st.info(
      f"**Lệnh đang mở:** {direction} @ **{_fmt_px(open_trade.get('entry_px') or open_trade.get('entry'))}** · "
      f"SL **{_fmt_px(open_trade.get('sl'))}** · TP **{_fmt_px(open_trade.get('tp'))}** · "
      f"Ước tính **{ur_txt}** · ticket `{open_trade.get('ticket') or '—'}`"
    )
  elif action in ("BUY", "SELL"):
    st.warning(
      f"**SIGNAL chờ:** {action} @ **{_fmt_px(decision.get('entry'))}** · "
      f"SL **{_fmt_px(decision.get('sl'))}** · TP **{_fmt_px(decision.get('tp'))}** · "
      f"expires `{decision.get('expires_bar_time') or '—'}`"
    )

  # --- PnL Metrics (Auto / Trade Model only) ---
  p1, p2, p3, p4 = st.columns(4)
  if mode == "sim":
    sim_stats = compute_stats(filter_trades(trades, mode="auto"))
    p1.metric(
      "Sim R (auto)",
      f"{sim_stats['total_r']:+.2f}" if sim_stats["n_trades"] else "0.00",
    )
    p2.metric(
      "Sim Trades",
      f"{sim_stats['n_trades']} lệnh",
    )
    open_n = sum(
      1 for t in trades
      if str(t.get("status") or "").upper() == "OPEN" and trade_mode(t) == "auto"
    )
    open_manual = sum(
      1 for t in trades
      if str(t.get("status") or "").upper() == "OPEN" and trade_mode(t) == "manual"
    )
    p3.metric("Open auto", open_n)
    wr = sim_stats.get("win_rate_pct")
    p4.metric(
      "Sim WR (auto)",
      f"{wr}%" if wr is not None else "—",
    )
  else:
    p1.metric(
      "Today R (auto)",
      f"{today_stats['total_r']:+.2f}" if today_stats["n_trades"] else "0.00",
    )
    p2.metric(
      "Week R (auto)",
      f"{week_stats['total_r']:+.2f}" if week_stats["n_trades"] else "0.00",
    )
    open_n = sum(
      1 for t in trades
      if str(t.get("status") or "").upper() == "OPEN" and trade_mode(t) == "auto"
    )
    open_manual = sum(
      1 for t in trades
      if str(t.get("status") or "").upper() == "OPEN" and trade_mode(t) == "manual"
    )
    p3.metric("Open auto", open_n)
    wr = today_stats.get("win_rate_pct")
    p4.metric(
      "Today WR (auto)",
      f"{wr}%" if wr is not None else "—",
    )
  if open_manual:
    st.caption(f"{open_manual} lệnh mở mode sửa — không tính vào R auto.")


@st.fragment(run_every=timedelta(seconds=5))
def _trader_desk_fragment() -> None:
  """Refresh desk without rerunning the live chart iframe."""
  _render_trader_desk(include_live_metrics=True)


@st.fragment(run_every=timedelta(seconds=3))
def _sim_desk_fragment() -> None:
  """Refresh Sim status / Sim R / open trade — chart stays in iframe (no remount)."""
  if hasattr(bridge_bg.get_sim_status, "_cache"):
    bridge_bg.get_sim_status._cache = None
  _render_trader_desk(include_live_metrics=False)


def _chart_public_origin(port: int) -> str:
  """Browser-reachable chart base URL.

  Streamlit may be opened as http://LAN:8501 — iframe must NOT use 127.0.0.1
  (that would hit the viewer's machine, not the app host). Chart server binds
  0.0.0.0 so LAN host works.
  """
  host = "127.0.0.1"
  try:
    ctx = getattr(st, "context", None)
    headers = getattr(ctx, "headers", None) if ctx is not None else None
    raw = ""
    if headers is not None:
      raw = headers.get("Host") or headers.get("host") or ""
    if raw:
      host = str(raw).split(":")[0].strip() or host
  except Exception:
    pass
  return f"http://{host}:{int(port)}"


def _render_live_chart(max_bars: int) -> None:
  """Live + Simulate: persistent browser iframe (Plotly.react) — no Streamlit flicker."""
  bridge_dir = _active_bridge_dir()
  mode = _bridge_mode()
  tf = _bridge_tf()
  port = monitor_port_for(tf, mode)
  legend = "🟢 reward · 🔴 risk · 🔔 SIGNAL · ▲▼ ENTRY · ✕ exit"
  # Server-side health always hits local loopback
  local_url = f"http://127.0.0.1:{port}"
  chart_url = _chart_public_origin(port)

  ensure_chart_server(bridge_dir, port, tf=tf, mode=mode)
  try:
    with urlopen(f"{local_url}/health", timeout=0.5) as response:
      server_ready = response.read() == b"ok"
  except (OSError, URLError):
    server_ready = False

  if mode == "sim":
    if server_ready:
      components.iframe(
        f"{chart_url}/chart?mode=sim&bars={max_bars}&v=sim5",
        height=700,
        scrolling=False,
      )
      st.caption(legend)
      return
    st.warning(f"Chart server Simulate {tf} (:{port}) chưa sẵn sàng.")
    from mt5_bridge.ea_simulator import load_sim_state
    sim = load_sim_state(bridge_dir)
    frame, connection = load_sim_chart_data(
      date_from=sim.get("date_from") or str(st.session_state.get(_sk("sim_ea_from")) or ""),
      date_to=sim.get("date_to") or str(st.session_state.get(_sk("sim_ea_to")) or ""),
      last_bar=sim.get("last_bar"),
      max_bars=max_bars,
      bridge_dir=bridge_dir,
      progress_only=str(sim.get("status") or "") in ("running", "paused"),
      tf=tf,
    )
    fig = build_ea_chart(
      frame, connection, load_trades(bridge_dir),
      title=f"EURUSD {tf} · Simulate (static fallback)",
      price_line_label="SIM",
    )
    if fig is None:
      st.caption(f"Chưa vẽ được chart — cần cache MT5 {tf}.")
    else:
      st.plotly_chart(fig, use_container_width=True, key=_sk("mt5_ea_sim_chart_fallback"))
    return

  if server_ready:
    components.iframe(
      f"{chart_url}/chart?bars={max_bars}&v=live2",
      height=700,
      scrolling=False,
    )
    st.caption(legend)
    return
  st.warning(f"Live chart server {tf} (:{port}) chưa sẵn sàng.")
  frame, connection = load_ea_chart_data(max_bars=max_bars, bridge_dir=bridge_dir)
  trades = load_trades(bridge_dir)
  fig = build_ea_chart(
    frame, connection, trades,
    title=f"EURUSD {tf} · XM MT5 live",
  )
  if fig is None:
    st.caption(f"Đang chờ `bars.json` · `{bridge_dir.name}/`")
  else:
    st.plotly_chart(fig, use_container_width=True, key=_sk("mt5_ea_live_chart"))
    st.caption(legend)


def _render_manual_test_orders() -> None:
  """Immediate BUY/SELL/CLOSE via command.json — verify EA bridge without waiting for bar close."""
  with st.expander("Kiểm tra bridge (market ngay)", expanded=False):
    connection = read_json(connection_path()) or {}
    bar = read_json(bar_path()) or {}
    bid, ask = connection.get("bid"), connection.get("ask")
    digits = bar.get("digits") if isinstance(bar, dict) else None
    point = bar.get("point") if isinstance(bar, dict) else None
    pip = pip_size_from_quotes(
      digits=int(digits) if digits is not None else None,
      point=float(point) if point is not None else None,
    )

    c1, c2, c3 = st.columns(3)
    sl_pips = c1.number_input("SL (pips)", 1.0, 200.0, 20.0, step=1.0, key="mt5_test_sl_pips")
    tp_pips = c2.number_input("TP (pips)", 1.0, 400.0, 40.0, step=1.0, key="mt5_test_tp_pips")
    if bid is not None and ask is not None:
      c3.metric("Quote", f"{_fmt_px(bid)} / {_fmt_px(ask)}")
    else:
      c3.warning("EA offline?")

    confirm = st.checkbox(
      "Xác nhận lệnh market trên MT5",
      key="mt5_test_confirm",
    )
    b1, b2, b3 = st.columns(3)

    def _send_market(action: str) -> None:
      if bid is None or ask is None:
        st.error("Không có quote từ EA.")
        return
      _entry, sl, tp = prices_from_pips(
        action, bid=float(bid), ask=float(ask),
        sl_pips=float(sl_pips), tp_pips=float(tp_pips), pip_size=pip,
      )
      payload = write_manual_market_command(action, sl=sl, tp=tp)
      append_event(
        "app_to_ea",
        "manual_command",
        payload=payload,
        summary=f"test {action} sl={sl} tp={tp} sid={payload.get('signal_id')}",
      )
      st.success(f"Đã gửi {action} · id `{payload.get('signal_id')}`")
      st.session_state["mt5_last_test_cmd"] = payload

    if b1.button("BUY market", type="primary", use_container_width=True, disabled=not confirm):
      _send_market("BUY")
    if b2.button("SELL market", use_container_width=True, disabled=not confirm):
      _send_market("SELL")
    if b3.button("CLOSE all", use_container_width=True, disabled=not confirm):
      payload = write_manual_close_command()
      append_event(
        "app_to_ea",
        "manual_command",
        payload=payload,
        summary=f"test CLOSE sid={payload.get('signal_id')}",
      )
      st.success(f"Đã gửi CLOSE · id `{payload.get('signal_id')}`")
      st.session_state["mt5_last_test_cmd"] = payload

    last = st.session_state.get("mt5_last_test_cmd")
    pending = read_json(command_path())
    ack = read_json(command_ack_path()) or {}
    fill = read_json(fill_path()) or {}
    a1, a2, a3 = st.columns(3)
    with a1:
      st.markdown("**command**")
      st.json(last or pending or {"_": "—"})
    with a2:
      st.markdown("**ack**")
      st.json(ack or {"_": "—"})
    with a3:
      st.markdown("**fill**")
      st.json(fill or {"_": "—"})


def _render_service_controls() -> None:
  cfg = bridge_bg.load_config(tf=_bridge_tf())
  status = bridge_bg.get_status(tf=_bridge_tf())
  active_model = get_active_trade_model(tf=_bridge_tf())
  model_id = (active_model or {}).get("id") or DEFAULT_MODEL_ID
  if cfg.get("model_id") != model_id:
    cfg = bridge_bg.save_config(tf=_bridge_tf(), model_id=model_id)

  risk_key = _sk("mt5_risk_pct")
  poll_key = _sk("mt5_poll_sec")
  st.session_state.setdefault(risk_key, float(cfg.get("risk_pct", 1.0)))
  st.session_state.setdefault(poll_key, float(cfg.get("poll_sec", 2.0)))

  b1, b2, b3, b4 = st.columns([1, 1, 1, 2])
  risk = float(st.session_state.get(risk_key, 1.0))
  poll = float(st.session_state.get(poll_key, 2.0))
  if b1.button("Start", icon=":material/play_arrow:", type="primary", use_container_width=True):
    bridge_bg.save_config(tf=_bridge_tf(), model_id=model_id, risk_pct=risk, poll_sec=poll, enabled=True)
    bridge_bg.start_worker(detached=True, tf=_bridge_tf())
    st.rerun()
  if b2.button("Stop", icon=":material/stop:", use_container_width=True):
    bridge_bg.stop_worker(tf=_bridge_tf())
    st.rerun()
  if b3.button("1 bar", icon=":material/bolt:", use_container_width=True, help="Xử lý 1 bar ngay"):
    bridge_bg.save_config(tf=_bridge_tf(), model_id=model_id, risk_pct=risk, poll_sec=poll)
    with st.spinner("Decide…"):
      dec = bridge_bg.process_once_now(tf=_bridge_tf())
    st.write(dec)
    st.rerun()
  running = bool(status.get("running"))
  b4.caption(
    f"Service **{'ON' if running else 'OFF'}**"
    + (f" · pid `{status.get('service_pid')}`" if status.get("service_pid") else "")
  )

  with st.expander("Risk / poll", expanded=False):
    st.number_input(
      f"Risk % / lệnh · {_bridge_tf()}", 0.1, 5.0, step=0.1, key=risk_key,
      on_change=_save_bridge_runtime_settings,
    )
    st.number_input(
      f"Poll (giây) · {_bridge_tf()}", 0.5, 30.0, step=0.5, key=poll_key,
      on_change=_save_bridge_runtime_settings,
    )


def _render_history_sync() -> None:
  tf = _bridge_tf()
  live_dir = get_profile(tf, "live").bridge_dir
  history = get_history_status(live_dir, tf=tf)
  history_data = history.get("data") or {}
  received = int(history.get("received_bars") or 0)
  available = int(history.get("available_bars") or 0)
  h1, h2 = st.columns([4, 1])
  with h1:
    if history.get("state") in ("requesting", "receiving"):
      st.progress(
        received / max(available, 1),
        text=f"Đồng bộ lịch sử MT5: {received}/{available or '?'} nến {tf}",
      )
    elif history_data.get("bars"):
      st.caption(
        f"MT5 history **{tf}**: **{history_data.get('bars')} nến** · "
        f"{str(history_data.get('start'))[:10]} → {str(history_data.get('end'))[:16]} · "
        f"{history_data.get('broker') or '?'}"
      )
    else:
      st.warning(f"Chưa có lịch sử MT5 **{tf}** để train / tín hiệu.")
  with h2:
    if st.button("Đồng bộ history", key=_sk("mt5_history_sync"), use_container_width=True):
      start_history_sync(live_dir, force=True, tf=tf)
      st.rerun()


@st.fragment(run_every=timedelta(seconds=2))
def _render_sim_progress_fragment() -> None:
  """Auto status/progress + Pause/Stop while feed runs (no full-page Refresh needed)."""
  try:
    # Bust short status cache so each fragment tick sees fresh sim_control
    if hasattr(bridge_bg.get_sim_status, "_cache"):
      bridge_bg.get_sim_status._cache = None
    sim = bridge_bg.get_sim_status(tf=_bridge_tf())
  except Exception as e:
    st.warning(f"Không đọc được sim status: {e}")
    return
  running = bool(sim.get("running"))

  # Form Start/disabled uses full-script `running` — remount page when feed flips
  prev_run = bool(st.session_state.get("_sim_ui_was_running"))
  if prev_run != running:
    st.session_state["_sim_ui_was_running"] = running
    st.rerun()

  ea_st = sim.get("ea_status") or "—"
  runtime = sim.get("runtime") or "—"
  pid = sim.get("service_pid")
  st.caption(
    f"`{sim.get('status') or 'idle'}` · EA `{ea_st}` · "
    f"{sim.get('bars_done') or 0}/{sim.get('bars_total') or '—'} bars · "
    f"trades `{sim.get('n_fills') or 0}`"
    + (f" · pid `{pid}`" if pid else "")
  )
  if running and runtime not in ("process", "thread"):
    st.warning("Runtime chưa rõ — đợi vài giây hoặc Restart app.")
  if sim.get("error"):
    st.error(sim["error"])

  try:
    prog = float(sim.get("progress") or 0)
  except (TypeError, ValueError):
    prog = 0.0
  if sim.get("bars_total"):
    st.progress(min(1.0, max(0.0, prog)))

  b2, b3, b4, b5 = st.columns(4)
  if b2.button(
    "Pause" if not sim.get("paused") else "Resume",
    icon=":material/pause:",
    disabled=not running, use_container_width=True, key=_sk("sim_ea_pause"),
  ):
    bridge_bg.pause_sim_worker(not bool(sim.get("paused")), tf=_bridge_tf())
    st.rerun()
  if b3.button(
    "Stop", icon=":material/stop:",
    disabled=not running, use_container_width=True, key=_sk("sim_ea_stop"),
  ):
    bridge_bg.stop_sim_worker(tf=_bridge_tf())
    st.rerun()
  if b4.button(
    "Reset data",
    icon=":material/delete_sweep:",
    use_container_width=True,
    key=_sk("sim_ea_reset"),
    help="Xóa trades/fills/log/bar/decision/sim_control lần chạy trước để chạy lại sạch.",
    disabled=running,
  ):
    bridge_bg.reset_sim_data(tf=_bridge_tf())
    st.toast("Đã xóa dữ liệu Simulate — có thể Start feed lại")
    st.rerun()
  if b5.button("Refresh", icon=":material/refresh:", use_container_width=True, key=_sk("sim_ea_refresh")):
    import time as _time
    st.session_state["bridge_ui_refresh_tick"] = _time.strftime("%H:%M:%S")
    st.rerun()


def _render_simulate_ea() -> None:
  """App controls EA HISTORY_FEED (from/to/delay); EA sends bar/fill via bridge_sim."""
  from datetime import date as date_cls

  tf = _bridge_tf()
  from_key = _sk("sim_ea_from")
  to_key = _sk("sim_ea_to")
  delay_key = _sk("sim_ea_delay")

  active = get_active_trade_model(tf=tf)
  sim = bridge_bg.get_sim_status(tf=tf)
  running = bool(sim.get("running"))

  st.markdown(f"##### History Feed · {tf}")

  default_from = date_cls.fromisoformat(
    str((active or {}).get("oos_from") or "2026-01-01")[:10]
  )
  default_to = date_cls.fromisoformat(
    str((active or {}).get("oos_to") or "2026-01-31")[:10]
  )
  if (default_to - default_from).days > 60:
    from datetime import timedelta as _td
    default_to = default_from + _td(days=14)

  # Persist like other tabs (ui_preferences.json) — survive refresh / app restart
  restore_widget(
    from_key, default_from,
    preference_key=_pref("mt5.sim_from"),
    decode=_parse_ui_date,
  )
  restore_widget(
    to_key, default_to,
    preference_key=_pref("mt5.sim_to"),
    decode=_parse_ui_date,
  )
  restore_widget(
    delay_key, 100,
    preference_key=_pref("mt5.sim_delay"),
    decode=lambda v: int(v),
  )
  # Sanitize after restore / code change (slider: min=10, step=10)
  try:
    if not isinstance(st.session_state[from_key], date):
      st.session_state[from_key] = _parse_ui_date(st.session_state[from_key]) or default_from
    if not isinstance(st.session_state[to_key], date):
      st.session_state[to_key] = _parse_ui_date(st.session_state[to_key]) or default_to
    delay_cur = int(st.session_state[delay_key])
    if delay_cur < 10 or delay_cur > 2000 or delay_cur % 10 != 0:
      st.session_state[delay_key] = max(10, min(2000, round(delay_cur / 10) * 10 or 100))
  except Exception:
    st.session_state[from_key] = default_from
    st.session_state[to_key] = default_to
    st.session_state[delay_key] = 100

  def _persist_sim_ea_settings() -> None:
    set_preference(_pref("mt5.sim_from"), st.session_state.get(from_key))
    set_preference(_pref("mt5.sim_to"), st.session_state.get(to_key))
    try:
      set_preference(_pref("mt5.sim_delay"), int(st.session_state.get(delay_key) or 100))
    except (TypeError, ValueError):
      set_preference(_pref("mt5.sim_delay"), 100)

  with st.form(_sk("sim_ea_params_form"), clear_on_submit=False):
    c1, c2, c3 = st.columns(3)
    with c1:
      st.date_input("Từ ngày", key=from_key, disabled=running)
    with c2:
      st.date_input("Đến ngày", key=to_key, disabled=running)
    with c3:
      st.slider(
        "Delay (ms)",
        min_value=10,
        max_value=2000,
        step=10,
        key=delay_key,
        disabled=running,
      )
    b_save, b_start = st.columns(2)
    with b_save:
      save_clicked = st.form_submit_button(
        "Lưu",
        icon=":material/save:",
        disabled=running,
        use_container_width=True,
      )
    with b_start:
      start_clicked = st.form_submit_button(
        "Start feed",
        type="primary",
        icon=":material/play_arrow:",
        disabled=running or not active,
        use_container_width=True,
      )

  d_from = st.session_state[from_key]
  d_to = st.session_state[to_key]
  delay_ms = int(st.session_state[delay_key])

  _render_sim_progress_fragment()

  if save_clicked:
    if d_to < d_from:
      st.error("Đến ngày phải ≥ Từ ngày")
    else:
      _persist_sim_ea_settings()
      st.toast("Đã lưu setting Simulate")

  if start_clicked:
    if d_to < d_from:
      st.error("Đến ngày phải ≥ Từ ngày")
    else:
      _persist_sim_ea_settings()
      ok = bridge_bg.start_sim_worker(
        date_from=str(d_from),
        date_to=str(d_to),
        delay_ms=int(delay_ms),
        model_id=(active or {}).get("id"),
        risk_pct=float(st.session_state.get(_sk("mt5_risk_pct"), 1.0)),
        tf=_bridge_tf(),
      )
      if ok:
        import time as _time
        if hasattr(bridge_bg.get_sim_status, "_cache"):
          bridge_bg.get_sim_status._cache = None
        _time.sleep(0.4)
        st.rerun()
      else:
        st.warning("Feed đang chạy")


def _render_model_monitor() -> None:
  """Backtest OOS vs Live Auto / Simulate EA — health + risk."""
  try:
    _render_model_monitor_body()
  except Exception as e:
    st.error(f"Không render được Theo dõi model: {e}")
    with st.expander("Chi tiết lỗi"):
      st.exception(e)


@st.fragment(run_every=timedelta(seconds=12))
def _model_monitor_auto_fragment() -> None:
  """Auto-refresh Sức khỏe / Rủi ro while Live service or Sim feed is running."""
  _render_model_monitor()


@st.fragment(run_every=timedelta(seconds=12))
def _stats_auto_fragment() -> None:
  """Auto-refresh Thống kê lệnh while feed/service is running."""
  _render_stats_section()


def _render_model_monitor_body() -> None:
  from gui.bridge_model_monitor import (
    LIVE_SERIES_COLOR,
    OOS_SERIES_COLOR,
    build_bt_vs_live_monthly_figure,
    build_equity_overlay_figure,
    build_equity_series_figure,
    build_monthly_series_figure,
    build_monitor_bundle,
  )
  from mt5_bridge.ea_simulator import load_sim_state

  active = get_active_trade_model(tf=_bridge_tf())
  source = _bridge_mode()
  st.markdown(f"##### Sức khỏe / Rủi ro · {_mode_label()}")
  if not active:
    st.info("Chọn Trade Model active để xem OOS và lệnh Bridge.")
    return

  sim_st = load_sim_state(get_profile(_bridge_tf(), "sim").bridge_dir)
  date_from = date_to = None
  if source == "sim":
    d0 = st.session_state.get(_sk("sim_ea_from"))
    d1 = st.session_state.get(_sk("sim_ea_to"))
    date_from = (
      d0.isoformat() if hasattr(d0, "isoformat") else None
    ) or sim_st.get("date_from") or None
    date_to = (
      d1.isoformat() if hasattr(d1, "isoformat") else None
    ) or sim_st.get("date_to") or None

  bundle = build_monitor_bundle(
    active,
    source=source,
    date_from=date_from,
    date_to=date_to,
    tf=_bridge_tf(),
    bridge_dir=_active_bridge_dir(),
  )
  live_label = bundle.get("live_label") or "Live Auto"
  st.caption(
    f"**{bundle['model_label']}** · fp `{bundle.get('conditions_fp') or '—'}`"
    + (f" · cửa sổ sim `{date_from} → {date_to}`" if source == "sim" and date_from else "")
    + f" · nguồn `{bundle.get('live', {}).get('bridge_dir') or '—'}`"
    + "."
  )

  if not bundle["has_report"]:
    st.warning(
      "Chưa có report backtest của model. Chạy **Trade Models → Sức khỏe** "
      "(bật Chạy lại KB ON, đúng search space) rồi quay lại."
    )

  kpi = bundle["kpi"]
  live_n = int(kpi["live"].get("n_trades") or 0)

  # Live: OOS và Live khác giai đoạn thời gian → tách 2 đoạn, mặc định thu gọn.
  if source == "live":
    st.caption(
      "OOS (Health) và Live Auto **không cùng giai đoạn** — xem riêng từng phần bên dưới."
    )
    with st.expander("① OOS · Health report", expanded=False):
      b = kpi["bt"]
      m1, m2, m3, m4 = st.columns(4)
      m1.metric("Total R", f"{b.get('total_r'):+.1f}" if b.get("total_r") is not None else "—")
      m2.metric("WR%", f"{b.get('win_rate_pct')}%" if b.get("win_rate_pct") is not None else "—")
      m3.metric("Max DD", f"{b.get('max_drawdown_r')}R" if b.get("max_drawdown_r") is not None else "—")
      m4.metric("Trades", f"{b.get('n_trades') or '—'}")
      th, tr = st.tabs(["Sức khỏe", "Rủi ro"])
      with th:
        fig = build_monthly_series_figure(
          bundle["bt"]["monthly"],
          title=f"Tháng · OOS · {bundle['model_label']}",
          series_name="Backtest OOS",
          color=OOS_SERIES_COLOR,
        )
        if fig:
          st.plotly_chart(fig, use_container_width=True)
        else:
          st.info("Chưa có chuỗi tháng OOS.")
      with tr:
        eq = build_equity_series_figure(
          bundle["bt"]["equity"],
          title=f"Equity · OOS · {bundle['model_label']}",
          series_name="Backtest OOS",
          color=OOS_SERIES_COLOR,
        )
        if eq:
          st.plotly_chart(eq, use_container_width=True)
        else:
          st.info("Chưa có equity OOS.")

    with st.expander(f"② {live_label} · Bridge auto", expanded=False):
      lv = kpi["live"]
      assess = bundle["live_assess"]
      m1, m2, m3, m4 = st.columns(4)
      m1.metric("Total R", f"{lv.get('total_r'):+.1f}" if lv.get("total_r") is not None else "—")
      m2.metric("WR%", f"{lv.get('win_rate_pct')}%" if lv.get("win_rate_pct") is not None else "—")
      m3.metric("Max DD", f"{lv.get('max_drawdown_r')}R" if lv.get("max_drawdown_r") is not None else "—")
      m4.metric("Trades", f"{live_n}")
      verdict = assess.get("verdict")
      if live_n == 0:
        st.info(
          f"Chưa có lệnh **auto** đã đóng trên Bridge "
          f"(`mt5/{_active_bridge_dir().name}/trades.json`)."
        )
      elif live_n < 5:
        st.caption(f"{live_label} còn ít lệnh — chỉ theo dõi.")
      elif verdict == "degraded":
        st.error(assess.get("message") or "")
      elif verdict == "watch":
        st.warning(assess.get("message") or "")
      elif verdict == "stable":
        st.success(assess.get("message") or "")
      elif assess.get("message"):
        st.info(assess.get("message"))
      th, tr = st.tabs(["Sức khỏe", "Rủi ro"])
      with th:
        fig = build_monthly_series_figure(
          bundle["live"]["monthly"],
          title=f"Tháng · {live_label} · {bundle['model_label']}",
          series_name=live_label,
          color=LIVE_SERIES_COLOR,
        )
        if fig:
          st.plotly_chart(fig, use_container_width=True)
        else:
          st.info(f"Chưa có chuỗi tháng {live_label}.")
      with tr:
        eq = build_equity_series_figure(
          bundle["live"]["equity"],
          title=f"Equity · {live_label} · {bundle['model_label']}",
          series_name=live_label,
          color=LIVE_SERIES_COLOR,
        )
        if eq:
          st.plotly_chart(eq, use_container_width=True)
        else:
          st.info(f"Chưa có equity {live_label}.")
    return

  # Simulate: cùng cửa sổ lịch sử → giữ overlay Backtest vs Sim
  st.caption(
    f"Simulate: KPI/biểu đồ đọc `mt5/{_active_bridge_dir().name}/trades.json` theo **entry_time** lịch sử "
    "(không dùng giờ tường lúc fill). Tự cập nhật ~12s khi feed chạy; hoặc bấm Refresh."
  )
  tab_h, tab_r = st.tabs(["Sức khỏe", "Rủi ro"])

  with tab_h:
    assess = bundle["live_assess"]
    m1, m2, m3, m4 = st.columns(4)
    bt_r = kpi["bt"].get("total_r")
    live_r = kpi["live"].get("total_r")
    m1.metric("Backtest OOS (full)", f"{bt_r:+.1f}R" if bt_r is not None else "—")
    m2.metric(f"{live_label}", f"{live_r:+.1f}R" if live_r is not None else "—")
    ov_e = bundle.get("overlap_edge")
    m3.metric(
      f"Edge {live_label}−BT (tháng trùng)",
      f"{ov_e:+.1f}R" if ov_e is not None else "—",
      help="Tổng R nguồn − backtest trên các tháng có cả hai chuỗi.",
    )
    verdict = assess.get("verdict")
    m4.metric(f"{live_label} verdict", verdict or "—")

    if live_n == 0:
      st.info(
        "Chưa có lệnh Simulate — ở mode **Simulate**, Start feed "
        "(EA HISTORY_FEED) rồi Refresh."
      )
    elif live_n < 5:
      st.caption(f"{live_label} còn ít lệnh — chỉ theo dõi, chưa đủ để kết luận suy giảm.")
    elif verdict == "degraded":
      st.error(assess.get("message") or "")
    elif verdict == "watch":
      st.warning(assess.get("message") or "")
    elif verdict == "stable":
      st.success(assess.get("message") or "")
    else:
      st.info(assess.get("message") or f"Chưa đủ tháng {live_label}.")

    if ov_e is not None and live_n >= 5:
      st.caption(
        "Edge gần 0 / cùng hướng với BT trên cửa sổ sim → protocol App↔EA "
        "và Trade Model khớp kỳ vọng train trên giai đoạn đó."
      )

    fig = build_bt_vs_live_monthly_figure(
      bundle["bt"]["monthly"],
      bundle["live"]["monthly"],
      title=f"Tháng · Backtest vs {live_label} · {bundle['model_label']}",
      live_name=live_label,
    )
    if fig:
      st.plotly_chart(fig, use_container_width=True)
      st.caption(
        "Cùng trục tháng · nền/chú thích **xanh dương = Timeline OOS**, "
        f"**xanh ngọc = Timeline {live_label}** (khoảng tháng có dữ liệu từng nguồn)."
      )
    else:
      st.info("Chưa có chuỗi tháng để vẽ (cần report OOS và/hoặc lệnh live/sim).")

    aligned = bundle.get("aligned")
    if aligned is not None and not aligned.empty:
      st.dataframe(aligned, use_container_width=True, hide_index=True)

  with tab_r:
    c1, c2 = st.columns(2)
    with c1:
      st.markdown("**Backtest OOS**")
      b = kpi["bt"]
      r1, r2, r3 = st.columns(3)
      r1.metric("WR%", f"{b.get('win_rate_pct')}%" if b.get("win_rate_pct") is not None else "—")
      r2.metric("Total R", f"{b.get('total_r'):+.1f}" if b.get("total_r") is not None else "—")
      r3.metric("Max DD", f"{b.get('max_drawdown_r')}R" if b.get("max_drawdown_r") is not None else "—")
      st.caption(
        f"n={b.get('n_trades') or '—'} · avg "
        f"{b.get('avg_r') if b.get('avg_r') is not None else '—'}"
      )
    with c2:
      st.markdown(f"**{live_label}**")
      lv = kpi["live"]
      r1, r2, r3 = st.columns(3)
      r1.metric("WR%", f"{lv.get('win_rate_pct')}%" if lv.get("win_rate_pct") is not None else "—")
      r2.metric("Total R", f"{lv.get('total_r'):+.1f}" if lv.get("total_r") is not None else "—")
      r3.metric("Max DD", f"{lv.get('max_drawdown_r')}R" if lv.get("max_drawdown_r") is not None else "—")
      st.caption(
        f"n={lv.get('n_trades') or '—'} · avg "
        f"{lv.get('avg_r') if lv.get('avg_r') is not None else '—'}"
      )

    if live_n == 0:
      st.warning(
        f"Chưa có trade **{live_label}** — biểu đồ Rủi ro hiện chỉ **Backtest OOS**."
      )
    elif live_n < 5:
      st.caption("Mẫu đối chiếu nhỏ — so sánh rủi ro mang tính tham khảo.")

    eq_fig = build_equity_overlay_figure(
      bundle["bt"]["equity"],
      bundle["live"]["equity"],
      title=f"Equity · Backtest vs {live_label} · {bundle['model_label']}",
      live_name=live_label,
    )
    if eq_fig:
      st.plotly_chart(eq_fig, use_container_width=True)
    else:
      st.info("Chưa đủ equity series để overlay.")


def _render_stats_section() -> None:
  """Thống kê lệnh — đọc lại trades.json mỗi lần gọi (không cache fragment)."""
  bridge_dir = _active_bridge_dir()
  mode = _bridge_mode()
  st.markdown(f"##### Lệnh · {_mode_label()}")
  st.caption(f"`{bridge_dir.name}/trades.json` · Auto vs lệnh sửa")

  all_trades = load_trades(bridge_dir)
  today = date.today()
  sim_from, sim_to = _sim_feed_window() if mode == "sim" else (None, None)

  # Defaults for "Tùy chọn" pickers
  if mode == "sim" and sim_from and sim_to:
    default_from, default_to = sim_from, sim_to
  else:
    default_from = today - timedelta(days=30)
    default_to = today
    for t in all_trades:
      for key in ("entry_time", "exit_time"):
        try:
          ts = pd.Timestamp(t.get(key)).date()
          if ts < default_from:
            default_from = ts
        except Exception:
          pass

  p1, p2, p3 = st.columns([2, 1, 1])
  if mode == "sim":
    preset_options = [
      "Cửa sổ History Feed",
      "Tháng trong cửa sổ",
      "Tất cả lệnh",
      "Tùy chọn",
    ]
    default_preset = "Cửa sổ History Feed"
    pref_key = _pref("mt5.sim_stats_preset")
    widget_key = _sk("bridge_stats_preset_sim")
  else:
    preset_options = [
      "Hôm nay",
      "Tuần này (T2→nay)",
      "7 ngày",
      "30 ngày",
      "Tháng này",
      "Tất cả",
      "Tùy chọn",
    ]
    default_preset = "Hôm nay"
    pref_key = _pref("mt5.stats_preset")
    widget_key = _sk("bridge_stats_preset_live")

  restore_widget(
    widget_key, default_preset,
    preference_key=pref_key,
    options=preset_options,
  )
  # Migrate old live-relative presets saved under sim key
  cur = st.session_state.get(widget_key)
  if mode == "sim" and cur not in preset_options:
    st.session_state[widget_key] = default_preset

  preset = p1.selectbox(
    "Giai đoạn",
    preset_options,
    key=widget_key,
    on_change=preference_callback(widget_key, pref_key),
  )
  date_from = None
  date_to = None

  if mode == "sim":
    if preset == "Cửa sổ History Feed":
      date_from, date_to = sim_from, sim_to
      if not date_from or not date_to:
        st.warning("Chưa có Từ/Đến History Feed — chọn **Tùy chọn** hoặc Start feed.")
      else:
        p2.caption(f"Từ `{date_from}`")
        p3.caption(f"Đến `{date_to}`")
    elif preset == "Tháng trong cửa sổ":
      if sim_from and sim_to:
        months = _months_spanning(sim_from, sim_to)
      else:
        months = []
        for t in all_trades:
          et = _parse_ui_date(str(t.get("entry_time") or "")[:10].replace(".", "-"))
          if et:
            ym = f"{et.year:04d}-{et.month:02d}"
            if ym not in months:
              months.append(ym)
        months.sort()
      if not months:
        st.warning("Chưa xác định được tháng trong cửa sổ feed.")
        p2.caption("—")
        p3.caption("—")
      else:
        month_key = _sk("bridge_stats_sim_month")
        restore_widget(
          month_key, months[0],
          preference_key=_pref("mt5.sim_stats_month"),
          options=months,
        )
        if st.session_state.get(month_key) not in months:
          st.session_state[month_key] = months[0]
        ym = p2.selectbox(
          "Tháng",
          months,
          key=month_key,
          on_change=preference_callback(month_key, _pref("mt5.sim_stats_month")),
        )
        date_from, date_to = _month_bounds(ym)
        # Clip to feed window when known
        if sim_from and date_from < sim_from:
          date_from = sim_from
        if sim_to and date_to > sim_to:
          date_to = sim_to
        p3.caption(f"`{date_from}` → `{date_to}`")
    elif preset == "Tùy chọn":
      restore_widget(
        _sk("bridge_from_sim"), default_from,
        preference_key=_pref("mt5.sim_date_from"),
        decode=date.fromisoformat,
      )
      restore_widget(
        _sk("bridge_to_sim"), default_to,
        preference_key=_pref("mt5.sim_date_to"),
        decode=date.fromisoformat,
      )
      date_from = p2.date_input(
        "Từ ngày", key=_sk("bridge_from_sim"),
        on_change=preference_callback(_sk("bridge_from_sim"), _pref("mt5.sim_date_from")),
      )
      date_to = p3.date_input(
        "Đến ngày", key=_sk("bridge_to_sim"),
        on_change=preference_callback(_sk("bridge_to_sim"), _pref("mt5.sim_date_to")),
      )
    else:
      # Tất cả lệnh
      p2.caption("Toàn bộ journal")
      p3.caption("—")
  else:
    if preset == "Hôm nay":
      date_from = date_to = today
    elif preset == "7 ngày":
      date_from, date_to = today - timedelta(days=6), today
    elif preset == "30 ngày":
      date_from, date_to = today - timedelta(days=29), today
    elif preset == "Tuần này (T2→nay)":
      date_from = today - timedelta(days=today.weekday())
      date_to = today
    elif preset == "Tháng này":
      date_from = today.replace(day=1)
      date_to = today
    elif preset == "Tùy chọn":
      restore_widget(
        _sk("bridge_from"), default_from,
        preference_key=_pref("mt5.date_from"),
        decode=date.fromisoformat,
      )
      restore_widget(
        _sk("bridge_to"), default_to,
        preference_key=_pref("mt5.date_to"),
        decode=date.fromisoformat,
      )
      date_from = p2.date_input(
        "Từ ngày", key=_sk("bridge_from"),
        on_change=preference_callback(_sk("bridge_from"), _pref("mt5.date_from")),
      )
      date_to = p3.date_input(
        "Đến ngày", key=_sk("bridge_to"),
        on_change=preference_callback(_sk("bridge_to"), _pref("mt5.date_to")),
      )
    else:
      p2.caption("—")
      p3.caption("—")

  if date_from and date_to and date_from > date_to:
    st.warning("Từ ngày > Đến ngày — đã đảo lại.")
    date_from, date_to = date_to, date_from

  period_trades = filter_trades(all_trades, date_from=date_from, date_to=date_to)
  n_auto = sum(1 for t in period_trades if trade_mode(t) == "auto")
  n_manual = sum(1 for t in period_trades if trade_mode(t) == "manual")
  if date_from or date_to:
    st.caption(
      f"Lọc: **{date_from or '…'} → {date_to or '…'}** · "
      f"{len(period_trades)} lệnh (auto {n_auto} · sửa {n_manual})"
    )
  elif mode == "sim":
    st.caption(
      f"Lọc: **tất cả lệnh journal** · "
      f"{len(period_trades)} lệnh (auto {n_auto} · sửa {n_manual})"
    )

  def _stats_block(label: str, mode: str | None) -> None:
    trades = filter_trades(all_trades, date_from=date_from, date_to=date_to, mode=mode)
    stats = compute_stats(trades)
    st.markdown(f"**{label}** · {stats['n_filtered']} lệnh")
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    s1.metric("Đã đóng", stats["n_trades"])
    s2.metric("Đang mở", stats["n_open"])
    s3.metric("Thắng", stats["n_wins"])
    s4.metric("Thua", stats["n_losses"])
    s5.metric("WR %", stats["win_rate_pct"] if stats["win_rate_pct"] is not None else "—")
    s6.metric("Total R", f"{stats['total_r']:+.2f}" if stats["n_trades"] else "—")
    m2 = st.columns(3)
    m2[0].metric("Avg R", stats["avg_r"] if stats["avg_r"] is not None else "—")
    m2[1].metric("Max DD (R)", stats["max_drawdown_r"])
    m2[2].metric(
      "Profit ($)",
      stats["total_profit"] if stats["total_profit"] is not None else "—",
    )

  tab_auto, tab_manual, tab_all = st.tabs([
    f"Auto (review chiến lược) · {n_auto}",
    f"Lệnh sửa · {n_manual}",
    f"Tất cả · {len(period_trades)}",
  ])
  with tab_auto:
    st.caption(
      "Review Trade Model: **không** gồm lệnh đã sửa SL/TP, đóng tay, hay test market."
    )
    _stats_block("Auto", "auto")
  with tab_manual:
    st.caption("Test market / user sửa SL·TP / đóng tay trên MT5 — đồng bộ App nhưng tách khỏi review auto.")
    _stats_block("Lệnh sửa", "manual")
  with tab_all:
    _stats_block("Tất cả", None)

  tc1, tc2 = st.columns([1, 4])
  if tc1.button("Xóa nhật ký lệnh", key="bridge_clear_trades"):
    clear_trades(bridge_dir)
    st.rerun()
  restore_widget("bridge_show_open", True, preference_key="mt5.show_open")
  show_open = tc2.checkbox(
    "Hiện cả lệnh đang mở", key="bridge_show_open",
    on_change=preference_callback("bridge_show_open", "mt5.show_open"),
  )

  mode_options = ["Auto", "Lệnh sửa", "Tất cả"]
  restore_widget(
    "bridge_stats_table_mode", "Tất cả",
    preference_key="mt5.stats_table_mode",
    options=mode_options,
  )
  table_mode = st.radio(
    "Bảng lệnh theo mode",
    mode_options,
    horizontal=True,
    key="bridge_stats_table_mode",
    on_change=preference_callback("bridge_stats_table_mode", "mt5.stats_table_mode"),
  )
  mode_filter = {"Auto": "auto", "Lệnh sửa": "manual", "Tất cả": None}[table_mode]
  trades = filter_trades(all_trades, date_from=date_from, date_to=date_to, mode=mode_filter)
  view = trades if show_open else [t for t in trades if t.get("status") == "CLOSED"]
  view = list(reversed(view))
  if not view:
    st.info("Không có lệnh trong giai đoạn / mode đã chọn.")
  else:
    table = []
    for t in view:
      table.append({
        "mode": trade_mode(t),
        "status": t.get("status"),
        "result": t.get("result") or ("OPEN" if t.get("status") == "OPEN" else "—"),
        "dir": t.get("direction"),
        "entry_time": t.get("entry_time"),
        "exit_time": t.get("exit_time"),
        "entry": t.get("entry_px"),
        "exit": t.get("exit_px"),
        "sl": t.get("sl"),
        "sl₀": t.get("sl_initial"),
        "tp": t.get("tp"),
        "R": t.get("r"),
        "profit": t.get("profit"),
        "reason": t.get("reason"),
        "intervened": ",".join(t.get("interventions") or []) or "—",
        "ticket": t.get("ticket"),
        "signal_id": t.get("signal_id"),
        "strategy": t.get("strategy_name"),
      })
    st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)


def render():
  render_page_header(ALL_ITEMS["mt5_bridge"], show_workspace=False)

  mode = _render_mode_switcher()
  render_shared_trade_model_banner(context="simulate" if mode == "sim" else "live")

  chart_ranges = ["48 giờ", "7 ngày", "14 ngày"]
  chart_key = "mt5_chart_range_sim" if mode == "sim" else "mt5_chart_range_live"
  pref_key = "mt5.chart_range_sim" if mode == "sim" else "mt5.chart_range"

  def _chart_block():
    restore_widget(
      chart_key, "7 ngày",
      preference_key=pref_key,
      options=chart_ranges,
    )
    c_range, _ = st.columns([1, 3])
    with c_range:
      range_label = st.selectbox(
        "Chart",
        chart_ranges,
        key=chart_key,
        on_change=preference_callback(chart_key, pref_key),
      )
    max_bars = {"48 giờ": 192, "7 ngày": 672, "14 ngày": 1344}[range_label]
    _render_live_chart(max_bars)

  if mode == "sim":
    # 1) Feed control → 2) Desk → 3) Chart → 4) Stats → 5) Health → 6) Debug
    _render_simulate_ea()
    _sim_desk_fragment()
    st.divider()
    _chart_block()
    svc_running = bool(bridge_bg.get_sim_status(tf=_bridge_tf()).get("running"))
    if svc_running:
      _stats_auto_fragment()
    else:
      _render_stats_section()
    with st.expander("Sức khỏe / Rủi ro", expanded=False):
      if svc_running:
        _model_monitor_auto_fragment()
      else:
        _render_model_monitor()
  else:
    # 1) Service → 2) Desk → 3) Chart → 4) Stats → 5) Health → 6) Tools
    _render_service_controls()
    _trader_desk_fragment()
    st.divider()
    _chart_block()
    live_running = bool(bridge_bg.get_status(tf=_bridge_tf()).get("running"))
    if live_running:
      _stats_auto_fragment()
    else:
      _render_stats_section()
    with st.expander("Sức khỏe / Rủi ro", expanded=False):
      if live_running:
        _model_monitor_auto_fragment()
      else:
        _render_model_monitor()
    with st.expander("Công cụ", expanded=False):
      _render_history_sync()
      _render_manual_test_orders()
