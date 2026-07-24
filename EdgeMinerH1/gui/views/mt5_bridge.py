"""MT5 Bridge — App quyết định (Best 3m), EA ForgeBridge execute + log giao tiếp."""
from __future__ import annotations

from datetime import date, timedelta
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from gui.mt5_live_chart import build_ea_chart, load_ea_chart_data
from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header
from gui.trade_model import format_model_label, get_active_trade_model
from gui.ui_preferences import preference_callback, restore_widget
from mt5_bridge.history_sync import get_history_status, start_history_sync
from mt5_bridge import background as bridge_bg
from mt5_bridge.comm_log import append_event, clear_log, read_events
from mt5_bridge.live_monitor_server import DEFAULT_MONITOR_PORT
from mt5_bridge.protocol import (
  BRIDGE_DIR,
  DEFAULT_MODEL_ID,
  bar_path,
  bars_path,
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
from mt5_bridge.trade_journal import clear_trades, compute_stats, filter_trades, load_trades


def _fmt_px(value) -> str:
  if value is None:
    return "—"
  try:
    return f"{float(value):.5f}"
  except (TypeError, ValueError):
    return str(value)


def _model_label(m: dict) -> str:
  try:
    from gui.trade_model import format_model_label
    return format_model_label(m)
  except Exception:
    return m.get("label") or m.get("id") or "?"


def _save_bridge_runtime_settings() -> None:
  active = get_active_trade_model()
  bridge_bg.save_config(
    model_id=(active or {}).get("id") or DEFAULT_MODEL_ID,
    risk_pct=float(st.session_state.get("mt5_risk_pct", 1.0)),
    poll_sec=float(st.session_state.get("mt5_poll_sec", 2.0)),
  )


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
      "Chart cập nhật trực tiếp mỗi 2 giây trong trình duyệt, "
      "không rerun Streamlit nên không chớp."
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
    st.caption(
      "Nến và đường LIVE lấy trực tiếp từ XM MT5 · "
      "🟢 reward · 🔴 risk · 🔔 SIGNAL · ▲▼ ENTRY · ✕ exit — giống Paper Trade."
    )


def render():
  render_page_header(ALL_ITEMS["mt5_bridge"], show_workspace=False)

  st.info(
    "**MT5 Bridge** = lệnh thật/demo: EA `ForgeBridge` → App decide → EA execute. "
    "**Khác Paper** (chỉ mô phỏng). Paper `SIGNAL`/`FILLED` ≠ đã vào MT5 — "
    "chỉ tin fill trong **Thống kê lệnh** / `trades.json`."
  )
  st.caption(
    "Background mặc định = **process riêng** (`mt5_bridge_service.py`) — "
    "đổi tab / refresh GUI **không** dừng service. Chỉ dừng khi bấm Stop hoặc kill process."
  )

  cfg = bridge_bg.load_config()
  status = bridge_bg.get_status()

  c1, c2, c3, c4 = st.columns(4)
  mode = status.get("runtime_mode") or "off"
  pid = status.get("service_pid")
  svc_label = "OFF"
  if status.get("running"):
    svc_label = f"ON · {mode}" + (f" · pid {pid}" if pid else "")
  c1.metric("Service", svc_label)
  c2.metric("Last action", status.get("last_action") or "—")
  c3.metric("Last bar", str(status.get("last_bar") or "—")[:19])
  file_status = read_json(status_path()) or {}
  c4.metric("Bridge state", file_status.get("state") or "—")
  current_decision = read_json(decision_path()) or {}
  st.markdown(
    f"**Chiến lược tuần hiện tại:** "
    f"`{current_decision.get('strategy_name') or 'đang chờ mine'}`"
  )
  st.caption(
    f"Áp dụng từ tuần `{current_decision.get('week_start') or '—'}` · "
    f"Trade Model `{current_decision.get('model_id') or status.get('model_id') or '—'}` · "
    f"quyết định gần nhất `{current_decision.get('updated_at') or '—'}` · "
    "tự mine lại khi bước sang tuần mới."
  )

  with st.expander("Cấu hình service", expanded=not status.get("running")):
    active_model = get_active_trade_model()
    model_id = (active_model or {}).get("id") or DEFAULT_MODEL_ID
    if cfg.get("model_id") != model_id:
      cfg = bridge_bg.save_config(model_id=model_id)
    st.markdown(
      f"Trade Model dùng chung với Paper: **"
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
    st.caption(f"Thư mục bridge: `{BRIDGE_DIR}`")

    b1, b2, b3 = st.columns(3)
    if b1.button("Start", icon=":material/play_arrow:", type="primary", use_container_width=True):
      bridge_bg.save_config(model_id=model_id, risk_pct=risk, poll_sec=poll, enabled=True)
      bridge_bg.start_worker(detached=True)
      st.success("Đã start process nền (sống khi refresh GUI).")
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
    st.caption(f"Log process: `results/mt5_bridge_service.log` · PID file: `results/mt5_bridge_service.pid`")

  with st.expander("Kiểm tra bridge (market ngay)", expanded=False):
    st.caption(
      "Ghi `command.json` → EA xử lý ngay trên tick (không chờ nến đóng). "
      "Cần **ForgeBridge v1.03+** đã biên dịch lại. Lệnh thật/demo trên tài khoản gắn EA."
    )
    connection = read_json(connection_path()) or {}
    bar = read_json(bar_path()) or {}
    bid, ask = connection.get("bid"), connection.get("ask")
    digits = bar.get("digits") if isinstance(bar, dict) else None
    point = bar.get("point") if isinstance(bar, dict) else None
    pip = pip_size_from_quotes(
      digits=int(digits) if digits is not None else None,
      point=float(point) if point is not None else None,
    )
    tc1, tc2, tc3 = st.columns(3)
    sl_pips = tc1.number_input("SL (pips)", 1.0, 200.0, 20.0, step=1.0, key="mt5_test_sl_pips")
    tp_pips = tc2.number_input("TP (pips)", 1.0, 400.0, 40.0, step=1.0, key="mt5_test_tp_pips")
    if bid is not None and ask is not None:
      tc3.metric("Quote", f"{_fmt_px(bid)} / {_fmt_px(ask)}")
      tc3.caption(f"pip≈{pip:g}")
    else:
      tc3.warning("Chưa có bid/ask — EA offline?")
    confirm = st.checkbox(
      "Tôi hiểu đây là lệnh market thật/demo trên MT5",
      key="mt5_test_confirm",
    )
    tb1, tb2, tb3 = st.columns(3)

    def _send_market(action: str) -> None:
      if bid is None or ask is None:
        st.error("Không có quote từ EA (`connection.json`).")
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
      st.success(f"Đã gửi {action} · chờ EA ack · id `{payload.get('signal_id')}`")
      st.session_state["mt5_last_test_cmd"] = payload

    if tb1.button("BUY market", type="primary", use_container_width=True, disabled=not confirm):
      _send_market("BUY")
    if tb2.button("SELL market", use_container_width=True, disabled=not confirm):
      _send_market("SELL")
    if tb3.button("CLOSE all", use_container_width=True, disabled=not confirm):
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
      st.markdown("**command gửi**")
      st.json(last or pending or {"_": "chưa gửi"})
    with a2:
      st.markdown("**command_ack**")
      st.json(ack or {"_": "chưa có ack — kiểm tra EA v1.03 + AutoTrading"})
    with a3:
      st.markdown("**fill gần nhất**")
      st.json(fill or {"_": "chưa có fill"})

  if status.get("last_error"):
    st.error(status["last_error"])

  history = get_history_status()
  history_data = history.get("data") or {}
  received = int(history.get("received_bars") or 0)
  available = int(history.get("available_bars") or 0)
  h1, h2 = st.columns([4, 1])
  with h1:
    if history.get("state") in ("requesting", "receiving"):
      st.progress(
        received / max(available, 1),
        text=f"Đồng bộ lịch sử MT5: {received}/{available or '?'} nến H1",
      )
    elif history_data.get("bars"):
      st.caption(
        f"Dữ liệu MT5: **{history_data.get('bars')} nến H1** · "
        f"{str(history_data.get('start'))[:10]} → {str(history_data.get('end'))[:16]} · "
        f"{history_data.get('broker') or '?'}"
      )
    else:
      st.warning("Chưa có lịch sử MT5 để train và tạo tín hiệu.")
  with h2:
    if st.button("Đồng bộ history", key="mt5_history_sync", use_container_width=True):
      start_history_sync(force=True)
      st.rerun()

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
  max_bars = {"48 giờ": 48, "7 ngày": 168, "14 ngày": 336}[range_label]
  _render_live_chart(max_bars)

  st.subheader("Thống kê lệnh Bridge")
  st.caption("Từ `mt5/bridge/trades.json` — lọc theo giai đoạn (closed dùng exit_time)")

  all_trades = load_trades()
  today = date.today()
  # Default range from data
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
    "Tất cả",
    "Hôm nay",
    "7 ngày",
    "30 ngày",
    "Tuần này (T2→nay)",
    "Tháng này",
    "Tùy chọn",
  ]
  restore_widget(
    "bridge_stats_preset", "Tất cả",
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
    st.caption(f"Lọc: **{date_from or '…'} → {date_to or '…'}** · {stats['n_filtered']} lệnh trong khoảng")

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
    st.info("Không có lệnh trong giai đoạn đã chọn (hoặc chưa có lệnh Bridge).")
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

  st.subheader("Snapshot files (App ↔ EA)")
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

  st.subheader("Nhật ký giao tiếp")
  st.caption("File: `mt5/bridge/comm_log.jsonl` — bar / decision / fill / system")
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
    st.warning(
      "Chưa có log. Start service và gắn EA ForgeBridge (Live), "
      "hoặc bấm **Xử lý 1 bar ngay**."
    )
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

  st.divider()
  st.markdown("Chi tiết: **Hướng dẫn** (mục MT5 Bridge) hoặc `mt5/bridge/README.md`.")
