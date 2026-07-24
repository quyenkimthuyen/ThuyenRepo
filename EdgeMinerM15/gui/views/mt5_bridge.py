"""MT5 Bridge — Trader desk: EA live status, decision, open risk, PnL."""
from __future__ import annotations

from datetime import date, timedelta
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from gui.mt5_live_chart import build_ea_chart, connection_health, load_ea_chart_data
from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header
from gui.trade_model import format_model_label, get_active_trade_model
from gui.ui_preferences import preference_callback, restore_widget
from mt5_bridge.history_sync import get_history_status, start_history_sync
from mt5_bridge import background as bridge_bg
from mt5_bridge.comm_log import clear_log, read_events
from mt5_bridge.live_monitor_server import DEFAULT_MONITOR_PORT
from mt5_bridge.protocol import (
  BRIDGE_DIR,
  DEFAULT_MODEL_ID,
  bar_path,
  bars_path,
  connection_path,
  decision_path,
  fill_path,
  read_json,
  status_path,
)
from mt5_bridge.trade_journal import clear_trades, compute_stats, filter_trades, load_trades


def _save_bridge_runtime_settings() -> None:
  active = get_active_trade_model()
  bridge_bg.save_config(
    model_id=(active or {}).get("id") or DEFAULT_MODEL_ID,
    risk_pct=float(st.session_state.get("mt5_risk_pct", 1.0)),
    poll_sec=float(st.session_state.get("mt5_poll_sec", 2.0)),
  )


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


def _open_trade(trades: list[dict]) -> dict | None:
  for trade in reversed(trades):
    if str(trade.get("status") or "").upper() == "OPEN":
      return trade
  return None


def _period_stats(trades: list[dict], *, today: date) -> tuple[dict, dict]:
  week_from = today - timedelta(days=today.weekday())
  today_stats = compute_stats(filter_trades(trades, date_from=today, date_to=today))
  week_stats = compute_stats(filter_trades(trades, date_from=week_from, date_to=today))
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


def _render_trader_desk() -> None:
  """Live desk strip + banners + today/week PnL (refreshed by fragment)."""
  connection = read_json(connection_path()) or {}
  decision = read_json(decision_path()) or {}
  file_status = read_json(status_path()) or {}
  service_status = bridge_bg.get_status()
  active = get_active_trade_model()
  active_id = (active or {}).get("id")
  trades = load_trades()
  health = connection_health(connection)
  today = date.today()
  today_stats, week_stats = _period_stats(trades, today=today)

  _render_error_banner(
    file_status=file_status,
    service_status=service_status,
    decision=decision,
    active_model_id=active_id,
  )

  # --- 5-column trader strip ---
  c1, c2, c3, c4, c5 = st.columns(5)
  age = health.get("age_seconds")
  age_txt = f"{age:.0f}s" if age is not None else "—"
  if health.get("online"):
    c1.metric("EA", f"ONLINE · {age_txt}")
  else:
    c1.metric("EA", f"OFFLINE · {age_txt}")

  bid, ask = connection.get("bid"), connection.get("ask")
  spread = connection.get("spread_points")
  if bid is not None and ask is not None:
    c2.metric("Quote", f"{_fmt_px(bid)} / {_fmt_px(ask)}")
  else:
    c2.metric("Quote", "—")
  c2.caption(f"Spread: {spread if spread is not None else '—'} pts")

  algo_on = health.get("trade_allowed")
  c3.metric("Algo", "ON" if algo_on else "OFF")
  c3.caption(f"Acct {connection.get('account') or '—'}")

  action = str(decision.get("action") or service_status.get("last_action") or "—").upper()
  reason = str(decision.get("reason") or file_status.get("reason") or "—")
  c4.metric("Decision", action)
  c4.caption(reason[:48] if reason else "—")

  risk = decision.get("risk_pct")
  if risk is None:
    risk = service_status.get("risk_pct") or bridge_bg.load_config().get("risk_pct")
  slots = decision.get("slots_remaining")
  if slots is None:
    slots = "—"
  c5.metric("Risk / Slots", f"{float(risk):.1f}% · {slots}" if risk is not None else f"— · {slots}")

  # Strategy line
  st.markdown(
    f"**Chiến lược tuần:** "
    f"`{decision.get('strategy_name') or 'đang chờ mine'}` · "
    f"tuần `{decision.get('week_start') or '—'}` · "
    f"TM `{decision.get('model_id') or service_status.get('model_id') or '—'}`"
  )
  svc = "OFF"
  if service_status.get("running"):
    mode = service_status.get("runtime_mode") or "on"
    pid = service_status.get("service_pid")
    svc = f"ON · {mode}" + (f" · pid {pid}" if pid else "")
  st.caption(
    f"Service `{svc}` · Bridge `{file_status.get('state') or '—'}` · "
    f"Bar `{str(service_status.get('last_bar') or '—')[:19]}` · "
    f"Decision `{str(decision.get('updated_at') or '—')[:19]}`"
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
      f"expires `{decision.get('expires_bar_time') or '—'}` · "
      f"id `{decision.get('signal_id') or '—'}`"
    )

  # --- Today / Week compact PnL ---
  p1, p2, p3, p4 = st.columns(4)
  p1.metric(
    "Today R",
    f"{today_stats['total_r']:+.2f}" if today_stats["n_trades"] else "0.00",
  )
  p2.metric(
    "Week R",
    f"{week_stats['total_r']:+.2f}" if week_stats["n_trades"] else "0.00",
  )
  open_n = sum(1 for t in trades if str(t.get("status") or "").upper() == "OPEN")
  p3.metric("Open", open_n)
  wr = today_stats.get("win_rate_pct")
  p4.metric(
    "Today WR",
    f"{wr}%" if wr is not None else "—",
  )


@st.fragment(run_every=timedelta(seconds=5))
def _trader_desk_fragment() -> None:
  """Refresh desk without rerunning the live chart iframe."""
  _render_trader_desk()


def _render_live_chart(max_bars: int) -> None:
  """Use a persistent browser chart; JavaScript updates data in place."""
  monitor_url = f"http://127.0.0.1:{DEFAULT_MONITOR_PORT}"
  try:
    with urlopen(f"{monitor_url}/health", timeout=0.5) as response:
      server_ready = response.read() == b"ok"
  except (OSError, URLError):
    server_ready = False

  if server_ready:
    components.iframe(
      f"{monitor_url}/chart?bars={max_bars}",
      height=700,
      scrolling=False,
    )
    st.caption(
      "Chart cập nhật mỗi 2s trong trình duyệt (không chớp Streamlit). "
      "Desk phía trên refresh mỗi 5s."
    )
    return

  st.warning("Live chart server chưa chạy; đang dùng snapshot tĩnh.")
  frame, connection = load_ea_chart_data(max_bars=max_bars)
  trades = load_trades()
  fig = build_ea_chart(frame, connection, trades)
  if fig is None:
    st.caption("Đang chờ EA xuất `bars.json` để vẽ chart.")
  else:
    st.plotly_chart(fig, use_container_width=True, key="mt5_ea_live_chart")
    st.caption("▲▼ entry · ✕ exit · đường chấm = SL/TP.")


def _render_service_controls() -> None:
  cfg = bridge_bg.load_config()
  status = bridge_bg.get_status()
  with st.expander("Cấu hình service", expanded=not status.get("running")):
    active_model = get_active_trade_model()
    model_id = (active_model or {}).get("id") or DEFAULT_MODEL_ID
    if cfg.get("model_id") != model_id:
      cfg = bridge_bg.save_config(model_id=model_id)
    st.markdown(
      f"Trade Model: **"
      f"{format_model_label(active_model) if active_model else model_id}**"
    )
    st.session_state.setdefault("mt5_risk_pct", float(cfg.get("risk_pct", 1.0)))
    st.session_state.setdefault("mt5_poll_sec", float(cfg.get("poll_sec", 2.0)))
    risk = st.number_input(
      "Risk % / lệnh", 0.1, 5.0, step=0.1, key="mt5_risk_pct",
      on_change=_save_bridge_runtime_settings,
    )
    poll = st.number_input(
      "Poll (giây)", 0.5, 30.0, step=0.5, key="mt5_poll_sec",
      on_change=_save_bridge_runtime_settings,
    )
    st.caption(f"Bridge dir: `{BRIDGE_DIR}`")

    b1, b2, b3 = st.columns(3)
    if b1.button("Start", icon=":material/play_arrow:", type="primary", use_container_width=True):
      bridge_bg.save_config(model_id=model_id, risk_pct=risk, poll_sec=poll, enabled=True)
      bridge_bg.start_worker(detached=True)
      st.success("Đã start process nền.")
      st.rerun()
    if b2.button("Stop", icon=":material/stop:", use_container_width=True):
      bridge_bg.stop_worker()
      st.rerun()
    if b3.button("1 bar", icon=":material/bolt:", use_container_width=True, help="Xử lý 1 bar ngay"):
      bridge_bg.save_config(model_id=model_id, risk_pct=risk, poll_sec=poll)
      with st.spinner("Decide…"):
        dec = bridge_bg.process_once_now()
      st.write(dec)
      st.rerun()
    st.caption("`results/mt5_bridge_service.log` · `results/mt5_bridge_service.pid`")


def _render_history_sync() -> None:
  history = get_history_status()
  history_data = history.get("data") or {}
  received = int(history.get("received_bars") or 0)
  available = int(history.get("available_bars") or 0)
  h1, h2 = st.columns([4, 1])
  with h1:
    if history.get("state") in ("requesting", "receiving"):
      st.progress(
        received / max(available, 1),
        text=f"Đồng bộ lịch sử MT5: {received}/{available or '?'} nến M15",
      )
    elif history_data.get("bars"):
      st.caption(
        f"MT5 history: **{history_data.get('bars')} nến** · "
        f"{str(history_data.get('start'))[:10]} → {str(history_data.get('end'))[:16]} · "
        f"{history_data.get('broker') or '?'}"
      )
    else:
      st.warning("Chưa có lịch sử MT5 để train / tín hiệu.")
  with h2:
    if st.button("Đồng bộ history", key="mt5_history_sync", use_container_width=True):
      start_history_sync(force=True)
      st.rerun()


def _render_stats_section() -> None:
  st.subheader("Thống kê lệnh Bridge")
  st.caption("Từ `mt5/bridge/trades.json` — lọc theo giai đoạn (closed dùng exit_time)")

  all_trades = load_trades()
  today = date.today()
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
  preset_options = [
    "Hôm nay",
    "Tuần này (T2→nay)",
    "7 ngày",
    "30 ngày",
    "Tháng này",
    "Tất cả",
    "Tùy chọn",
  ]
  restore_widget(
    "bridge_stats_preset", "Hôm nay",
    preference_key="mt5.stats_preset",
    options=preset_options,
  )
  preset = p1.selectbox(
    "Giai đoạn",
    preset_options,
    key="bridge_stats_preset",
    on_change=preference_callback("bridge_stats_preset", "mt5.stats_preset"),
  )
  date_from = None
  date_to = None
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
      "bridge_from", default_from,
      preference_key="mt5.date_from",
      decode=date.fromisoformat,
    )
    restore_widget(
      "bridge_to", default_to,
      preference_key="mt5.date_to",
      decode=date.fromisoformat,
    )
    date_from = p2.date_input(
      "Từ ngày", key="bridge_from",
      on_change=preference_callback("bridge_from", "mt5.date_from"),
    )
    date_to = p3.date_input(
      "Đến ngày", key="bridge_to",
      on_change=preference_callback("bridge_to", "mt5.date_to"),
    )
  else:
    p2.caption("—")
    p3.caption("—")

  if date_from and date_to and date_from > date_to:
    st.warning("Từ ngày > Đến ngày — đã đảo lại.")
    date_from, date_to = date_to, date_from

  trades = filter_trades(all_trades, date_from=date_from, date_to=date_to)
  stats = compute_stats(trades)
  if date_from or date_to:
    st.caption(
      f"Lọc: **{date_from or '…'} → {date_to or '…'}** · "
      f"{stats['n_filtered']} lệnh trong khoảng"
    )

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

  tc1, tc2 = st.columns([1, 4])
  if tc1.button("Xóa nhật ký lệnh"):
    clear_trades()
    st.rerun()
  restore_widget("bridge_show_open", True, preference_key="mt5.show_open")
  show_open = tc2.checkbox(
    "Hiện cả lệnh đang mở", key="bridge_show_open",
    on_change=preference_callback("bridge_show_open", "mt5.show_open"),
  )

  view = trades if show_open else [t for t in trades if t.get("status") == "CLOSED"]
  view = list(reversed(view))
  if not view:
    st.info("Không có lệnh trong giai đoạn đã chọn.")
  else:
    table = []
    for t in view:
      table.append({
        "status": t.get("status"),
        "result": t.get("result") or ("OPEN" if t.get("status") == "OPEN" else "—"),
        "dir": t.get("direction"),
        "entry_time": t.get("entry_time"),
        "exit_time": t.get("exit_time"),
        "entry": t.get("entry_px"),
        "exit": t.get("exit_px"),
        "sl": t.get("sl"),
        "tp": t.get("tp"),
        "R": t.get("r"),
        "profit": t.get("profit"),
        "reason": t.get("reason"),
        "ticket": t.get("ticket"),
        "signal_id": t.get("signal_id"),
        "strategy": t.get("strategy_name"),
      })
    st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
    with st.expander("JSON lệnh đầy đủ"):
      st.json(view[:30])


def _render_debug_sections() -> None:
  with st.expander("Snapshot files (App ↔ EA)", expanded=False):
    t1, t2, t3, t4, t5 = st.tabs([
      "connection.json",
      "bars.json",
      "bar.json (EA→App)",
      "decision.json (App→EA)",
      "fill.json (EA→App)",
    ])
    with t1:
      st.json(read_json(connection_path()) or {"_": "chưa có heartbeat"})
    with t2:
      bars = read_json(bars_path()) or {}
      if isinstance(bars, dict) and bars.get("bars"):
        st.caption(f"{len(bars['bars'])} nến · cập nhật `{bars.get('updated_at', '—')}`")
        st.json({**bars, "bars": bars["bars"][-5:]})
      else:
        st.json({"_": "chưa có lịch sử nến"})
    with t3:
      st.json(read_json(bar_path()) or {"_": "chưa có — EA Live chưa ghi bar"})
    with t4:
      st.json(read_json(decision_path()) or {"_": "chưa có decision"})
    with t5:
      st.json(read_json(fill_path()) or {"_": "chưa có fill"})

  with st.expander("Nhật ký giao tiếp", expanded=False):
    st.caption("`mt5/bridge/comm_log.jsonl` — bar / decision / fill / system")
    lc1, lc2 = st.columns([1, 4])
    restore_widget("bridge_log_limit", 200, preference_key="mt5.log_limit")
    limit = lc1.number_input(
      "Số dòng", 20, 1000, step=20, key="bridge_log_limit",
      on_change=preference_callback("bridge_log_limit", "mt5.log_limit"),
    )
    if lc2.button("Xóa log"):
      clear_log()
      st.rerun()

    events = list(reversed(read_events(limit=int(limit))))
    if not events:
      st.warning("Chưa có log. Start service + gắn EA ForgeBridge, hoặc bấm **1 bar**.")
    else:
      rows = [{
        "ts": e.get("ts"),
        "hướng": e.get("direction"),
        "sự kiện": e.get("event"),
        "tóm tắt": e.get("summary"),
      } for e in events]
      st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
      with st.expander("Chi tiết JSON từng event"):
        st.json(events[:50])


def render():
  render_page_header(ALL_ITEMS["mt5_bridge"], show_workspace=False)

  st.caption(
    "MT5 ForgeBridge · App quyết định theo Trade Model · EA execute. "
    "Service chạy process riêng — refresh GUI không dừng."
  )

  # Trader desk (auto-refresh) — chart stays outside fragment
  _trader_desk_fragment()

  _render_service_controls()
  _render_history_sync()

  st.subheader("Giám sát MT5 trực tiếp")
  chart_ranges = ["48 giờ", "7 ngày", "14 ngày"]
  restore_widget(
    "mt5_chart_range", "7 ngày",
    preference_key="mt5.chart_range",
    options=chart_ranges,
  )
  range_label = st.selectbox(
    "Khoảng chart",
    chart_ranges,
    key="mt5_chart_range",
    on_change=preference_callback("mt5_chart_range", "mt5.chart_range"),
  )
  max_bars = {"48 giờ": 192, "7 ngày": 672, "14 ngày": 1344}[range_label]
  _render_live_chart(max_bars)

  _render_stats_section()
  _render_debug_sections()

  st.divider()
  st.caption("Chi tiết: mục **Hướng dẫn** / `mt5/bridge/README.md`.")
