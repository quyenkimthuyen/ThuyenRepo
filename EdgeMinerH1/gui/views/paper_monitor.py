"""7. Paper / Live Monitor — tín hiệu tuần hiện tại + chart TradingView."""
from __future__ import annotations

from datetime import date, timedelta
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components

from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS
from kb_profiles import DEFAULT_PROFILE_ID
from gui.trade_model import format_model_label, get_active_trade_model, get_model_run_params
from gui.services import get_ohlc_window_cached, get_paper_monitor
from gui.ui_preferences import preference_callback, restore_widget
from paper_journal import (
  compute_stats,
  filter_trades,
  load_meta,
  load_trades,
  reset_monitor,
  sync_from_state,
)
from paper_live_monitor_server import (
  DEFAULT_PAPER_MONITOR_PORT,
  start_paper_live_monitor_server,
)
from paper_service import (
  get_status as get_background_status,
  is_background_enabled,
  load_config,
  load_saved_state,
  run_once_now,
  save_config,
  start_worker,
  stop_worker,
)

TV_BG = "#131722"
TV_GRID = "#363a45"
TV_TEXT = "#d1d4dc"
TV_UP = "#26a69a"
TV_DOWN = "#ef5350"
TV_ENTRY = "#2962ff"
TV_SL = "#f23645"
TV_TP = "#089981"


def _tv_layout(fig: go.Figure, title: str = "", height: int = 580):
  fig.update_layout(
    title=dict(text=title, font=dict(size=14, color=TV_TEXT)),
    template="plotly_dark",
    paper_bgcolor=TV_BG,
    plot_bgcolor=TV_BG,
    font=dict(color=TV_TEXT, size=11),
    height=height,
    margin=dict(l=8, r=72, t=48, b=32),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    hovermode="x unified",
    xaxis_rangeslider_visible=False,
  )
  fig.update_xaxes(gridcolor=TV_GRID, showgrid=True, zeroline=False)
  fig.update_yaxes(gridcolor=TV_GRID, showgrid=True, zeroline=False, side="right")


def _add_order_overlays(fig: go.Figure, order: dict, row: int = 1, chart_end=None):
  """Vẽ entry / SL / TP / exit trên chart."""
  entry_t = pd.Timestamp(order.get("entry") or order.get("entry_time"))
  entry_px = order.get("entry_px")
  sl = order.get("sl")
  tp = order.get("tp")
  direction = order.get("dir") or order.get("direction", "")
  status = order.get("status", "CLOSED")
  is_long = direction == "LONG"
  is_signal = status == "SIGNAL"

  exit_t = order.get("exit")
  if exit_t:
    exit_t = pd.Timestamp(exit_t)
  elif chart_end:
    exit_t = pd.Timestamp(chart_end)
  else:
    exit_t = entry_t + pd.Timedelta(hours=48)

  x0, x1 = entry_t, exit_t
  line_dash = "dash" if is_signal else "dot"
  risk_fill = "rgba(255,193,7,0.08)" if is_signal else "rgba(242,54,69,0.12)"
  rew_fill = "rgba(255,193,7,0.06)" if is_signal else "rgba(8,153,129,0.10)"

  # Vùng risk (entry → SL) và reward (entry → TP)
  if entry_px and sl and tp:
    risk_y0, risk_y1 = (sl, entry_px) if is_long else (entry_px, sl)
    rew_y0, rew_y1 = (entry_px, tp) if is_long else (tp, entry_px)
    fig.add_shape(
      type="rect", xref="x", yref="y", row=row, col=1,
      x0=x0, x1=x1, y0=risk_y0, y1=risk_y1,
      fillcolor=risk_fill, line=dict(width=0),
    )
    fig.add_shape(
      type="rect", xref="x", yref="y", row=row, col=1,
      x0=x0, x1=x1, y0=rew_y0, y1=rew_y1,
      fillcolor=rew_fill, line=dict(width=0),
    )
    sl_color = "#ffc107" if is_signal else TV_SL
    tp_color = "#ffc107" if is_signal else TV_TP
    for y, color, label in [(sl, sl_color, "SL"), (tp, tp_color, "TP")]:
      fig.add_trace(go.Scatter(
        x=[x0, x1], y=[y, y],
        mode="lines",
        line=dict(color=color, width=1.5, dash=line_dash),
        name=label,
        showlegend=False,
        hovertemplate=f"{label}: %{{y:.5f}}<extra></extra>",
      ), row=row, col=1)
      fig.add_annotation(
        x=x1, y=y, xref="x", yref="y",
        text=f"{label} {y:.5f}",
        showarrow=False, font=dict(size=9, color=color),
        xanchor="left", xshift=4,
      )

  # Entry marker
  if is_signal:
    signal_t = pd.Timestamp(order.get("signal_time", entry_t))
    fig.add_trace(go.Scatter(
      x=[signal_t], y=[entry_px],
      mode="markers+text",
      marker=dict(symbol="diamond", size=16, color="#ffc107", line=dict(width=2, color="white")),
      text=["🔔 SIGNAL"],
      textposition="top center" if is_long else "bottom center",
      textfont=dict(size=10, color="#ffc107"),
      showlegend=False,
      hovertemplate=(
        f"Tín hiệu {direction}<br>%{{x}}<br>"
        f"Entry dự kiến: {entry_px}<br>SL: {sl}<br>TP: {tp}<extra></extra>"
      ),
    ), row=row, col=1)
    fig.add_trace(go.Scatter(
      x=[entry_t], y=[entry_px],
      mode="markers+text",
      marker=dict(symbol="circle-open", size=12, color="#ffc107", line=dict(width=2)),
      text=[f"ENTRY? {entry_px:.5f}"],
      textposition="middle right",
      textfont=dict(size=9, color="#ffc107"),
      showlegend=False,
      hovertemplate=f"Entry dự kiến<br>%{{x}} @ %{{y:.5f}}<extra></extra>",
    ), row=row, col=1)
  else:
    marker_symbol = "triangle-up" if is_long else "triangle-down"
    marker_color = TV_UP if is_long else TV_DOWN
    fig.add_trace(go.Scatter(
      x=[entry_t], y=[entry_px],
      mode="markers+text",
      marker=dict(symbol=marker_symbol, size=14, color=marker_color, line=dict(width=1, color="white")),
      text=[f"ENTRY {entry_px:.5f}"],
      textposition="top center" if is_long else "bottom center",
      textfont=dict(size=9, color=TV_ENTRY),
      name="Entry",
      showlegend=False,
      hovertemplate=(
        f"Entry<br>%{{x}}<br>{direction} @ %{{y:.5f}}<br>"
        f"SL: {sl}<br>TP: {tp}<extra></extra>"
      ),
    ), row=row, col=1)

  if not is_signal and status == "CLOSED" and order.get("exit_px"):
    exit_px = order["exit_px"]
    reason = order.get("reason", "")
    r_val = order.get("r", 0)
    exit_color = TV_TP if (r_val or 0) > 0 else TV_SL
    fig.add_trace(go.Scatter(
      x=[pd.Timestamp(exit_t)], y=[exit_px],
      mode="markers+text",
      marker=dict(symbol="x", size=10, color=exit_color, line=dict(width=2)),
      text=[f"EXIT {exit_px:.5f} ({reason})"],
      textposition="bottom center",
      textfont=dict(size=9, color=exit_color),
      showlegend=False,
      hovertemplate=f"Exit: %{{y:.5f}}<br>R={r_val}<extra></extra>",
    ), row=row, col=1)
  elif status == "OPEN":
    fig.add_annotation(
      x=entry_t, y=entry_px, xref="x", yref="y",
      text="● OPEN", showarrow=True, arrowhead=2,
      font=dict(size=10, color="#ffeb3b"),
      bgcolor="rgba(0,0,0,0.6)", bordercolor="#ffeb3b",
    )


def _tradingview_chart(
  ohlc_window: pd.DataFrame,
  orders: list[dict],
  chart_from: str,
  chart_to: str,
  title: str = "EUR/USD H1",
) -> go.Figure | None:
  window = ohlc_window
  if window.empty:
    return None

  has_vol = "Volume" in window.columns and window["Volume"].sum() > 0
  if has_vol:
    fig = make_subplots(
      rows=2, cols=1, shared_xaxes=True,
      row_heights=[0.78, 0.22], vertical_spacing=0.03,
    )
    price_row, vol_row = 1, 2
  else:
    fig = make_subplots(rows=1, cols=1)
    price_row, vol_row = 1, None

  fig.add_trace(go.Candlestick(
    x=window.index,
    open=window["Open"], high=window["High"],
    low=window["Low"], close=window["Close"],
    increasing_line_color=TV_UP, decreasing_line_color=TV_DOWN,
    increasing_fillcolor=TV_UP, decreasing_fillcolor=TV_DOWN,
    name="EUR/USD",
    showlegend=False,
  ), row=price_row, col=1)

  if vol_row:
    colors = [
      TV_UP if c >= o else TV_DOWN
      for o, c in zip(window["Open"], window["Close"])
    ]
    fig.add_trace(go.Bar(
      x=window.index, y=window["Volume"],
      marker_color=colors, opacity=0.5, name="Volume", showlegend=False,
    ), row=vol_row, col=1)
    fig.update_yaxes(title_text="Vol", row=vol_row, col=1)

  for order in orders:
    _add_order_overlays(fig, order, row=price_row, chart_end=chart_to)

  _tv_layout(fig, title=title, height=620 if has_vol else 560)
  fig.update_yaxes(title_text="Price", row=price_row, col=1)
  return fig


def _order_card(order: dict, idx: int):
  """Hiển thị chi tiết một lệnh."""
  status = order.get("status", "CLOSED")
  direction = order.get("dir") or order.get("direction", "?")
  is_long = direction == "LONG"
  status_icon = {"CLOSED": "✅", "OPEN": "🟡", "SIGNAL": "🔔"}.get(status, "•")
  r_val = order.get("r")
  r_str = f"{r_val:+.2f}R" if r_val is not None else "—"
  r_color = "green" if (r_val or 0) > 0 else ("red" if (r_val or 0) < 0 else "gray")

  with st.expander(
    f"{status_icon} #{idx + 1} · {direction} · {status} · "
    f"Entry {order.get('entry_px', '?')} · {r_str}",
    expanded=(status in ("OPEN", "SIGNAL")),
  ):
    c1, c2, c3 = st.columns(3)
    with c1:
      st.markdown("**Entry**")
      st.write(f"Thời gian: `{order.get('entry') or order.get('entry_time', '—')}`")
      st.write(f"Giá: **{order.get('entry_px', '—')}**")
      st.write(f"Hướng: **{direction}** {'📈' if is_long else '📉'}")
    with c2:
      st.markdown("**Stop Loss / Take Profit**")
      st.write(f"SL: :red[**{order.get('sl', '—')}**]")
      st.write(f"TP: :green[**{order.get('tp', '—')}**]")
      risk = order.get("risk_pips")
      if risk:
        st.write(f"Risk: **{risk}** pips")
      rr = order.get("rr")
      if rr:
        st.write(f"RR mục tiêu: **1:{rr}**")
    with c3:
      st.markdown("**Kết quả**")
      if status == "CLOSED":
        st.write(f"Exit: `{order.get('exit', '—')}`")
        st.write(f"Giá thoát: **{order.get('exit_px', '—')}**")
        st.markdown(f"R: :{r_color}[**{r_str}**]")
        st.write(f"Lý do: **{order.get('reason', '—')}**")
        pnl = order.get("pnl_pips")
        if pnl is not None:
          st.write(f"P/L: **{pnl:+.1f}** pips")
      elif status == "OPEN":
        st.warning("Lệnh đang mở — chưa chạm SL/TP/timeout")
        st.write(f"Bars giữ: **{order.get('bars_held', 0)}** / {order.get('max_hold_bars', '?')}")
      elif status == "SIGNAL":
        st.info("Tín hiệu — chưa khớp (hết slot tuần hoặc chưa tới entry)")
        st.write(f"Tín hiệu: `{order.get('signal_time', '—')}`")
        st.write(f"Entry dự kiến: `{order.get('entry_time', '—')}`")


def _orders_for_display(state: dict) -> list[dict]:
  """Gộp orders + tín hiệu SIGNAL (fallback khi state file cũ chưa có trong orders)."""
  orders = list(state.get("orders") or [])
  signal_entries = {
    o.get("entry") or o.get("entry_time")
    for o in orders
    if o.get("status") == "SIGNAL"
  }
  for sig in state.get("signals_this_week") or []:
    if sig.get("status") != "SIGNAL":
      continue
    entry_time = sig.get("entry_time")
    if entry_time in signal_entries:
      continue
    orders.append({
      "status": "SIGNAL",
      "signal_time": sig["signal_time"],
      "entry": entry_time,
      "entry_time": entry_time,
      "dir": sig["direction"],
      "direction": sig["direction"],
      "entry_px": sig["entry_px"],
      "sl": sig["sl"],
      "tp": sig["tp"],
      "risk_pips": sig.get("risk_pips"),
      "rr": sig.get("rr"),
      "exit": None,
      "exit_px": None,
      "r": None,
      "reason": None,
    })
    signal_entries.add(entry_time)
  return orders


def _trade_journal_df(orders: list[dict]) -> pd.DataFrame:
  rows = []
  for i, o in enumerate(orders, start=1):
    status = o.get("status", "CLOSED")
    direction = o.get("dir") or o.get("direction") or "—"
    r_val = o.get("r")
    rows.append({
      "#": i,
      "Trạng thái": status,
      "Hướng": direction,
      "Tín hiệu": str(o.get("signal_time") or "—")[:16],
      "Entry": str(o.get("entry") or o.get("entry_time") or "—")[:16],
      "Giá": o.get("entry_px"),
      "SL": o.get("sl"),
      "TP": o.get("tp"),
      "Exit": str(o.get("exit") or o.get("exit_time") or "—")[:16] if status == "CLOSED" else "—",
      "Exit giá": o.get("exit_px") if status == "CLOSED" else None,
      "R": None if r_val is None else round(float(r_val), 2),
      "Pips": o.get("pnl_pips"),
      "Lý do": o.get("reason") or ("chờ entry" if status == "SIGNAL" else "—"),
      "Risk pips": o.get("risk_pips"),
    })
  return pd.DataFrame(rows)


def _chart_cache_key(state: dict) -> str:
  orders = _orders_for_display(state)
  sig_n = sum(1 for o in orders if o.get("status") == "SIGNAL")
  return "|".join([
    str(state.get("updated_at", "")),
    str(state.get("chart_from", "")),
    str(state.get("chart_to", "")),
    str(len(orders)),
    str(sig_n),
  ])


def _settings_signature(use_kb, kb_profile, kb_snapshot, spread, slip) -> str:
  return f"{use_kb}|{kb_profile}|{kb_snapshot}|{spread}|{slip}"


def _on_settings_changed(new_sig: str):
  prev = st.session_state.get("pm_settings_sig")
  if prev is not None and prev != new_sig:
    st.session_state.pop("monitor_state", None)
    _invalidate_chart_cache()
  st.session_state["pm_settings_sig"] = new_sig


def _invalidate_chart_cache():
  st.session_state.pop("pm_fig", None)
  st.session_state.pop("pm_fig_key", None)


@st.cache_resource
def _paper_live_chart_server():
  try:
    return start_paper_live_monitor_server()
  except OSError:
    return None


def _get_chart_figure(state: dict) -> go.Figure | None:
  """Dùng lại figure đã build — chart hiện ngay khi quay lại tab."""
  key = _chart_cache_key(state)
  if st.session_state.get("pm_fig_key") == key and st.session_state.get("pm_fig") is not None:
    return st.session_state["pm_fig"]

  orders = _orders_for_display(state)
  chart_from = state.get("chart_from", state.get("week_start", ""))
  chart_to = state.get("chart_to", state.get("last_bar", ""))
  try:
    window = get_ohlc_window_cached(chart_from, chart_to)
    fig = _tradingview_chart(
      window, orders, chart_from, chart_to,
      title=f"EUR/USD H1 · Tuần {state.get('week_start', '')}",
    )
  except Exception:
    return None

  if fig is not None:
    st.session_state["pm_fig_key"] = key
    st.session_state["pm_fig"] = fig
  return fig


def _resolve_monitor_state(monitor_params: dict, *, manual_refresh: bool) -> dict:
  """Ưu tiên session/file cache — không chặn UI trong lúc EA đồng bộ history."""
  if manual_refresh:
    _invalidate_chart_cache()
    st.session_state.pop("monitor_state", None)

  if manual_refresh:
    with st.spinner("Đang tải giá & tính lại..."):
      if is_background_enabled():
        state = run_once_now(force_refresh=True)
      else:
        state = get_paper_monitor(**monitor_params)
    st.session_state["monitor_state"] = state
    st.session_state["pm_shown_at"] = state.get("updated_at")
    return state

  cached = st.session_state.get("monitor_state")

  if is_background_enabled():
    saved = load_saved_state()
    if cached and saved and saved.get("updated_at") == cached.get("updated_at"):
      return cached
    if saved and (not cached or saved.get("updated_at") != cached.get("updated_at")):
      _invalidate_chart_cache()
      st.session_state["monitor_state"] = saved
      st.session_state["pm_shown_at"] = saved.get("updated_at")
      return saved
    if cached:
      return cached
    # Chưa có state — hiện placeholder, để background tự cập nhật (không sync download).
    st.info("Đang chờ background cập nhật paper… (hoặc bấm **Refresh ngay**)")
    return {"error": None, "pending": True, "week_start": "—", "week_trades_taken": 0,
            "strategy": {"max_trades_per_day": 0}, "slots_remaining": 0, "in_session": False,
            "signals_this_week": [], "recent_trades": [], "last_bar": "—", "week_wr": "—",
            "week_total_r": "—"}

  if cached:
    return cached

  with st.spinner("Cập nhật..."):
    state = get_paper_monitor(**monitor_params)
  st.session_state["monitor_state"] = state
  return state


def _poll_check_update() -> bool:
  """Kiểm tra data background mới; cập nhật session nếu có."""
  if not is_background_enabled():
    return False
  saved = load_saved_state()
  shown = st.session_state.get("pm_shown_at")
  if saved and saved.get("updated_at") and saved.get("updated_at") != shown:
    st.session_state["pm_shown_at"] = saved["updated_at"]
    st.session_state["monitor_state"] = saved
    _invalidate_chart_cache()
    return True
  return False


def _period_options() -> list[str]:
  return [
    "Hôm nay",
    "Tuần này (T2→nay)",
    "7 ngày",
    "30 ngày",
    "Tháng này",
    "Tất cả",
    "Tùy chọn",
  ]


def _resolve_period(preset: str) -> tuple[date | None, date | None]:
  today = date.today()
  if preset == "Hôm nay":
    return today, today
  if preset == "7 ngày":
    return today - timedelta(days=6), today
  if preset == "30 ngày":
    return today - timedelta(days=29), today
  if preset == "Tuần này (T2→nay)":
    return today - timedelta(days=today.weekday()), today
  if preset == "Tháng này":
    return today.replace(day=1), today
  if preset == "Tùy chọn":
    return None, None  # filled by date_input callers
  return None, None  # Tất cả


def _bars_for_period(date_from: date | None, date_to: date | None) -> int:
  """M15 bars estimate for chart window (cap 5000)."""
  if date_from is None or date_to is None:
    return 1344
  days = max(1, (date_to - date_from).days + 1)
  return max(48, min(5000, days * 24))


def _render_period_controls() -> tuple[date | None, date | None, int]:
  """Period filter shared by stats + chart. Returns (from, to, max_bars)."""
  all_trades = load_trades()
  today = date.today()
  default_from = today - timedelta(days=30)
  default_to = today
  for trade in all_trades:
    for key in ("entry_time", "exit_time", "entry", "exit"):
      try:
        ts = pd.Timestamp(trade.get(key)).date()
        if ts < default_from:
          default_from = ts
      except Exception:
        pass

  p1, p2, p3, p4 = st.columns([2, 1, 1, 1])
  restore_widget(
    "paper_stats_preset", "Tuần này (T2→nay)",
    preference_key="paper.stats_preset",
    options=_period_options(),
  )
  preset = p1.selectbox(
    "Giai đoạn",
    _period_options(),
    key="paper_stats_preset",
    on_change=preference_callback("paper_stats_preset", "paper.stats_preset"),
  )
  date_from, date_to = _resolve_period(preset)
  if preset == "Tùy chọn":
    restore_widget(
      "paper_from", default_from,
      preference_key="paper.date_from",
      decode=date.fromisoformat,
    )
    restore_widget(
      "paper_to", default_to,
      preference_key="paper.date_to",
      decode=date.fromisoformat,
    )
    date_from = p2.date_input(
      "Từ ngày", key="paper_from",
      on_change=preference_callback("paper_from", "paper.date_from"),
    )
    date_to = p3.date_input(
      "Đến ngày", key="paper_to",
      on_change=preference_callback("paper_to", "paper.date_to"),
    )
  else:
    p2.caption(str(date_from or "—"))
    p3.caption(str(date_to or "—"))

  meta = load_meta()
  if p4.button(
    "Reset data",
    icon=":material/restart_alt:",
    help="Xóa nhật ký paper + snapshot — monitor lại từ đầu (bỏ qua lệnh remine trước mốc reset).",
    use_container_width=True,
  ):
    info = reset_monitor()
    st.session_state.pop("monitor_state", None)
    st.session_state.pop("pm_shown_at", None)
    _invalidate_chart_cache()
    st.success(
      f"Đã reset paper. Monitor từ `{info.get('monitor_from')}`. "
      "Bấm **Chạy ngay** / đợi service để ghi lệnh mới."
    )
    st.rerun()

  if date_from and date_to and date_from > date_to:
    st.warning("Từ ngày > Đến ngày — đã đảo lại.")
    date_from, date_to = date_to, date_from

  if meta.get("monitor_from"):
    st.caption(
      f"Journal: **{meta.get('n_trades', 0)}** lệnh · "
      f"monitor từ `{meta.get('monitor_from')}` · "
      f"cập nhật `{meta.get('updated_at') or '—'}`"
    )
  else:
    st.caption(
      f"Journal: **{meta.get('n_trades', 0)}** lệnh · "
      "chưa reset — đang gom từ remine tuần."
    )

  return date_from, date_to, _bars_for_period(date_from, date_to)


def _render_chart_panel(
  state: dict,
  *,
  date_from: date | None = None,
  date_to: date | None = None,
  max_bars: int = 672,
):
  """Persistent browser chart; window follows selected period."""
  st.subheader("Biểu đồ theo giai đoạn")
  monitor_url = f"http://127.0.0.1:{DEFAULT_PAPER_MONITOR_PORT}"
  try:
    with urlopen(f"{monitor_url}/health", timeout=0.5) as response:
      server_ready = response.read() == b"ok"
  except (OSError, URLError):
    server_ready = (
      False if is_background_enabled()
      else _paper_live_chart_server() is not None
    )
  if server_ready:
    poll_sec = max(0.5, float(load_config().get("poll_sec", 2.0)))
    query = {
      "bars": int(max_bars),
      "poll": f"{poll_sec:g}",
    }
    if date_from:
      query["from"] = date_from.isoformat()
    if date_to:
      query["to"] = date_to.isoformat()
    components.iframe(
      f"{monitor_url}/chart?{urlencode(query)}",
      height=700,
      scrolling=False,
    )
    label = (
      f"{date_from} → {date_to}" if date_from or date_to else "toàn bộ / gần đây"
    )
    st.caption(
      f"Chart Paper · giai đoạn **{label}** · ~{max_bars} nến H1 · "
      "cập nhật tại chỗ, không chớp."
    )
    return

  # Plotly fallback — slice OHLC to period
  chart_from = (
    str(date_from) if date_from
    else state.get("chart_from", state.get("week_start", ""))
  )
  chart_to = (
    str(date_to) if date_to
    else state.get("chart_to", state.get("last_bar", ""))
  )
  period_orders = filter_trades(
    load_trades(), date_from=date_from, date_to=date_to,
  )
  # Map journal rows to overlay schema
  overlay = []
  for row in period_orders:
    overlay.append({
      **row,
      "dir": row.get("dir") or row.get("direction"),
      "entry": row.get("entry") or row.get("entry_time"),
      "exit": row.get("exit") or row.get("exit_time"),
      "status": row.get("status") or "CLOSED",
    })
  for row in _orders_for_display(state):
    if str(row.get("status") or "").upper() == "SIGNAL":
      overlay.append(row)

  try:
    window = get_ohlc_window_cached(chart_from, chart_to)
    fig = _tradingview_chart(
      window, overlay, chart_from, chart_to,
      title=f"EUR/USD H1 · {chart_from} → {chart_to}",
    )
  except Exception:
    fig = None
  if fig:
    st.plotly_chart(fig, use_container_width=True, key="pm_tv_chart_period")
  else:
    st.caption("Không đủ dữ liệu OHLC cho chart giai đoạn này.")

  st.caption(
    "🟢 reward · 🔴 risk · 🔔 SIGNAL · ▲▼ ENTRY · ✕ exit"
  )


def _background_status_bar():
  status = get_background_status()
  if not status["enabled"]:
    st.caption("⏸ Paper service **đang tắt** — bấm **Start** hoặc **Chạy ngay**.")
    return

  st.caption(
    f"Lần cuối: `{status.get('last_run_at', '—')}` · "
    f"Data mới: `{status.get('updated_at', '—')}`"
  )
  if status.get("last_error"):
    st.error(f"Background lỗi: {status['last_error']}")


@st.fragment(run_every=timedelta(seconds=5))
def _background_live_panel():
  """Refresh Paper details while the persistent chart stays outside this fragment."""
  if not is_background_enabled():
    return
  _poll_check_update()
  state = st.session_state.get("monitor_state")
  if state:
    date_from = st.session_state.get("pm_period_from")
    date_to = st.session_state.get("pm_period_to")
    _render_monitor_body(
      state,
      include_chart=False,
      date_from=date_from,
      date_to=date_to,
    )


def _render_monitor_body(
  state: dict,
  *,
  include_chart: bool = True,
  date_from: date | None = None,
  date_to: date | None = None,
  max_bars: int = 672,
):
  if state.get("pending"):
    st.caption("Chưa có snapshot paper — đợi chu kỳ nền hoặc **Refresh ngay**.")
    return
  if state.get("error"):
    st.error(state["error"])
    return

  st.info(
    "**Paper Trade** = mô phỏng trên nến MT5 (cùng data với Bridge) — "
    "**không** gửi lệnh sang EA. Muốn lệnh thật/demo → trang **MT5 Bridge**."
  )

  # Sync latest week into journal (idempotent)
  try:
    sync_from_state(state)
  except Exception:
    pass

  period_trades = filter_trades(load_trades(), date_from=date_from, date_to=date_to)
  stats = compute_stats(period_trades)
  strategy = state.get("strategy") or {}

  # --- Desk KPI theo giai đoạn ---
  k1, k2, k3, k4, k5, k6 = st.columns(6)
  k1.metric("Đã đóng", stats["n_trades"])
  k2.metric("Đang mở", stats["n_open"])
  k3.metric("Thắng / Thua", f"{stats['n_wins']}/{stats['n_losses']}")
  k4.metric(
    "Win rate",
    f"{stats['win_rate_pct']}%" if stats["win_rate_pct"] is not None else "—",
  )
  k5.metric(
    "Tổng R",
    f"{stats['total_r']:+.2f}R" if stats["n_trades"] else "—",
  )
  k6.metric("Max DD", f"{stats['max_drawdown_r']:.2f}R")

  s1, s2, s3, s4, s5 = st.columns(5)
  s1.metric(
    "Tuần live",
    f"{state.get('week_trades_taken', 0)}/{strategy.get('max_trades_per_week') or strategy.get('max_trades_per_day') or '?'}",
  )
  s2.metric("Slots còn", state.get("slots_remaining", 0))
  s3.metric("Session", "ACTIVE" if state.get("in_session") else "OFF")
  s4.metric("Avg R", stats["avg_r"] if stats["avg_r"] is not None else "—")
  s5.metric("Pips", f"{stats['total_pips']:+.1f}")

  if date_from or date_to:
    st.caption(
      f"Thống kê lọc: **{date_from or '…'} → {date_to or '…'}** · "
      f"{stats['n_filtered']} lệnh trong khoảng"
    )
  ep = state.get("kb_snapshot", "latest")
  st.caption(
    f"Tuần live **{state.get('week_start')}** → **{state.get('week_end')}** · "
    f"Bar cuối `{state.get('last_bar')}` · "
    f"Risk **{state.get('risk_pct', 1.0)}%**/lệnh · "
    f"KB `{state.get('kb_profile', '-')}@{ep}` · "
    f"Model `{state.get('model_id') or '—'}`"
    + (f" · Cập nhật `{state.get('updated_at')}`" if state.get("updated_at") else "")
  )
  st.markdown(
    f"**Strategy tuần này:** `{strategy.get('name') or 'đang chờ mine'}` · "
    f"RR 1:{strategy.get('rr', '—')} · hold ≤{strategy.get('max_hold_bars', '—')} bars · "
    f"exit `{strategy.get('exit_mode', '—')}`"
  )

  b1, b2, b3 = st.columns(3)
  with b1:
    st.markdown("**Hướng (giai đoạn)**")
    st.write(f"LONG **{stats['n_long']}** · SHORT **{stats['n_short']}**")
  with b2:
    st.markdown("**Thoát lệnh**")
    reasons = stats.get("by_reason") or {}
    if reasons:
      st.write(" · ".join(f"{k} **{v}**" for k, v in sorted(reasons.items())))
    else:
      st.caption("Chưa có lệnh đóng trong giai đoạn.")
  with b3:
    st.markdown("**Tuần live (remine)**")
    st.write(
      f"WR {state.get('week_wr', 0)}% · "
      f"R {state.get('week_total_r', 0):+.2f} · "
      f"{state.get('week_trades_taken', 0)} lệnh"
    )

  if state.get("open_position"):
    op = state["open_position"]
    st.warning(
      f"Lệnh **OPEN:** {op.get('dir')} @ **{op.get('entry_px')}** · "
      f"SL **{op.get('sl')}** · TP **{op.get('tp')}** · "
      f"Giữ {op.get('bars_held', 0)}/{op.get('max_hold_bars', '?')} bars"
    )

  if include_chart:
    _render_chart_panel(
      state, date_from=date_from, date_to=date_to, max_bars=max_bars,
    )

  st.subheader("Nhật ký lệnh (giai đoạn)")
  st.caption(
    "`CLOSED` / `OPEN` từ journal bền vững · `SIGNAL` từ tuần live. "
    "**Reset data** xóa journal để monitor từ đầu."
  )
  show_open = st.checkbox("Hiện cả lệnh đang mở", value=True, key="paper_show_open")
  view = period_trades if show_open else [
    t for t in period_trades if t.get("status") == "CLOSED"
  ]
  # Attach current SIGNAL rows (not in journal)
  signal_rows = [
    o for o in _orders_for_display(state)
    if str(o.get("status") or "").upper() == "SIGNAL"
  ]
  journal_df = _trade_journal_df(list(reversed(view)) + signal_rows)
  if not journal_df.empty:
    st.dataframe(
      journal_df,
      hide_index=True,
      use_container_width=True,
      column_config={
        "R": st.column_config.NumberColumn(format="%+.2f"),
        "Pips": st.column_config.NumberColumn(format="%+.1f"),
        "Giá": st.column_config.NumberColumn(format="%.5f"),
        "SL": st.column_config.NumberColumn(format="%.5f"),
        "TP": st.column_config.NumberColumn(format="%.5f"),
        "Exit giá": st.column_config.NumberColumn(format="%.5f"),
      },
    )
    with st.expander("Chi tiết từng lệnh", expanded=any(
      str(o.get("status") or "").upper() in ("OPEN", "SIGNAL")
      for o in (view + signal_rows)
    )):
      for i, order in enumerate(view + signal_rows):
        _order_card(order, i)
  else:
    st.caption("Không có lệnh trong giai đoạn đã chọn.")

  with st.expander("Strategy JSON (tuần hiện tại)"):
    st.json(strategy)

  with st.expander("Paper vs MT5 Bridge — nhớ nhanh"):
    st.markdown(
      """
| | **Paper** (trang này) | **MT5 Bridge** |
|---|---|---|
| Lệnh | Mô phỏng trên history/live bars | EA mở/đóng trên tài khoản MT5 |
| Journal | `results/paper_trades.json` | `mt5/bridge/trades.json` |
| Giai đoạn | Lọc + chart theo preset (giống Bridge) | Lọc + chart theo preset |
| Reset | Nút **Reset data** — monitor từ đầu | Xóa nhật ký lệnh Bridge |
"""
    )



def _save_paper_runtime_settings() -> None:
  active = get_active_trade_model()
  params = get_model_run_params()
  save_config(
    model_id=(active or {}).get("id"),
    risk_pct=float(st.session_state.get("paper_risk_pct", 1.0)),
    poll_sec=float(st.session_state.get("paper_poll_sec", 2.0)),
    use_learning=bool(params.get("use_learning", True)),
    kb_profile=params.get("kb_profile") or "default",
    kb_snapshot=params.get("kb_snapshot"),
    spread_pips=float(params.get("spread_pips", 1.0)),
    slippage_pips=float(params.get("slippage_pips", 0.3)),
  )


def render():
  from gui.navigation import ALL_ITEMS
  from gui.page_chrome import render_page_header

  render_page_header(ALL_ITEMS["paper"])

  from gui.live_workflow import assess_workflow, load_workflow_state, mark_paper_started
  from gui.trade_model import get_model_run_params, get_active_trade_model
  from gui.workflow_ui import render_workflow_banner

  wf = assess_workflow()
  if wf["current_step"] < 4 and not wf["steps"][3]["done"]:
    st.warning("Hoàn thành ① KB → ② Grid → ③ Trade Model trước khi tin vào paper.")
  else:
    render_workflow_banner(page_step=4)
    state = load_workflow_state()
    if not state.get("paper_started_at"):
      if st.button("📌 Ghi nhận bắt đầu paper", key="pm_wf_start"):
        mark_paper_started()
        st.toast("Đã ghi nhận — theo dõi ≥3 tuần trước khi live")
        st.rerun()

  active_model = get_active_trade_model()
  if not active_model:
    st.warning("Chưa chọn Trade Model — paper dùng cài đặt mặc định.")

  params = get_model_run_params()
  use_kb = params["use_kb"]
  kb_profile = params["kb_profile"]
  kb_snapshot = params["kb_snapshot"]
  spread = params["spread_pips"]
  slip = params["slippage_pips"]
  cfg = load_config()
  status = get_background_status()

  s1, s2, s3, s4 = st.columns(4)
  service_label = "OFF"
  if status.get("running"):
    service_label = f"ON · process · pid {status.get('service_pid')}"
  s1.metric("Service", service_label)
  s2.metric("Risk / lệnh", f"{float(cfg.get('risk_pct', 1.0)):.1f}%")
  s3.metric("Poll", f"{float(cfg.get('poll_sec', 2.0)):g} giây")
  s4.metric("Bar cuối", str(status.get("last_bar") or "—")[:19])

  with st.expander("Cấu hình service", expanded=not status.get("running")):
    st.markdown(
      f"Trade Model dùng chung với MT5: **"
      f"{format_model_label(active_model) if active_model else '—'}**"
    )
    st.caption(
      f"Spread **{spread}** / slip **{slip}** pip · "
      f"KB **{'ON' if use_kb else 'OFF'}** · "
      "service chỉ tính lại khi có nến H1 mới hoặc cấu hình/model thay đổi."
    )
    st.session_state.setdefault("paper_risk_pct", float(cfg.get("risk_pct", 1.0)))
    st.session_state.setdefault("paper_poll_sec", float(cfg.get("poll_sec", 2.0)))
    risk = st.number_input(
      "Risk % / lệnh", 0.1, 5.0, step=0.1, key="paper_risk_pct",
      on_change=_save_paper_runtime_settings,
    )
    poll = st.number_input(
      "Poll (giây)", 0.5, 30.0, step=0.5, key="paper_poll_sec",
      on_change=_save_paper_runtime_settings,
      help="Chu kỳ kiểm tra nến/config; không remine liên tục nếu nến chưa đổi.",
    )
    b1, b2, b3 = st.columns(3)
    if b1.button("Start", icon=":material/play_arrow:", type="primary", use_container_width=True):
      _save_paper_runtime_settings()
      save_config(enabled=True, risk_pct=risk, poll_sec=poll)
      start_worker()
      st.success("Đã start Paper service nền.")
      st.rerun()
    if b2.button("Stop", icon=":material/stop:", use_container_width=True):
      stop_worker()
      st.rerun()
    manual_refresh = b3.button(
      "Chạy ngay", icon=":material/bolt:", use_container_width=True,
      help="Tính lại Paper snapshot ngay với cấu hình hiện tại.",
    )
    st.caption(
      "Log: `results/paper_monitor_service.log` · "
      "PID: `results/paper_monitor_service.pid`"
    )

  _on_settings_changed(_settings_signature(use_kb, kb_profile, kb_snapshot, spread, slip))

  monitor_params = dict(
    use_learning=use_kb, train_months=int(params.get("train_months") or params.get("train_weeks") or 3),
    spread_pips=spread, slippage_pips=slip,
    risk_pct=float(risk),
    kb_profile=kb_profile,
    kb_snapshot=kb_snapshot,
  )
  state = _resolve_monitor_state(monitor_params, manual_refresh=manual_refresh)

  st.subheader("Giai đoạn & reset")
  date_from, date_to, max_bars = _render_period_controls()
  st.session_state["pm_period_from"] = date_from
  st.session_state["pm_period_to"] = date_to
  st.session_state["pm_period_bars"] = max_bars

  if is_background_enabled():
    status = get_background_status()
    st.caption(
      f"Service: **{'đang chạy' if status.get('running') else 'đang khởi động'}** · "
      f"Lần tính cuối: `{status.get('last_run_at', '—')}` · "
      f"Snapshot: `{status.get('updated_at', '—')}`"
    )
    if status.get("last_error"):
      st.error(f"Background lỗi: {status['last_error']}")
    _render_chart_panel(
      state, date_from=date_from, date_to=date_to, max_bars=max_bars,
    )
    _background_live_panel()
  else:
    _background_status_bar()
    _render_monitor_body(
      state,
      include_chart=True,
      date_from=date_from,
      date_to=date_to,
      max_bars=max_bars,
    )
