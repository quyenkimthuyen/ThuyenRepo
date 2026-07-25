"""Trade Models — quản lý model + phân tích (Risk / Nhật ký / Chiến lược / Sức khỏe)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from gui.trade_model import (
  delete_trade_model,
  format_model_label,
  format_model_oneline,
  get_active_trade_model,
  list_trade_models,
  load_model_kb_off_report,
  load_model_report,
  set_active_trade_model,
)
from gui.ui_theme import icon_btn
from gui.ui_preferences import preference_callback, restore_widget, set_widget_preference
from gui.views import risk_dashboard, trade_journal, strategy_inspector

# Child of Trade Models: quản lý + phân tích theo model đang chọn
SUB_KEYS = ["manage", "health", "risk", "journal", "strategy"]
SUB_LABELS = {
  "manage": "Quản lý",
  "health": "Sức khỏe",
  "risk": "Rủi ro",
  "journal": "Nhật ký",
  "strategy": "Chiến lược",
}
SUB_ICONS = {
  "manage": ":material/inventory_2:",
  "health": ":material/monitor_heart:",
  "risk": ":material/shield:",
  "journal": ":material/receipt_long:",
  "strategy": ":material/candlestick_chart:",
}


def _resolve_subtab() -> str:
  # Compat: old analysis_tab / analysis hub
  legacy = st.session_state.get("analysis_tab")
  if legacy in ("risk", "journal", "strategy") and "models_subtab" not in st.session_state:
    set_widget_preference("models_subtab", legacy, "navigation.models_subtab")
  return restore_widget(
    "models_subtab", "manage",
    preference_key="navigation.models_subtab",
    options=SUB_KEYS,
  )


def _render_manage(models, active):
  st.caption(
    f"**{len(models)}** model · Active: **{format_model_label(active) if active else '—'}**"
  )

  rows = []
  for m in models:
    from gui.app_settings import kb_profile_label
    rows.append({
      "Tên": format_model_label(m),
      "Train": f"{m.get('train_weeks')} tuần",
      "Giai đoạn học": kb_profile_label(m.get("kb_profile")),
      "Vòng": m.get("kb_snapshot") or "latest",
      "Total R": m.get("total_r"),
      "WR%": m.get("win_rate_pct"),
      "Active": "✓" if active and m.get("id") == active.get("id") else "",
      "id": m.get("id"),
    })
  df = pd.DataFrame(rows)
  st.dataframe(
    df.drop(columns=["id"]),
    use_container_width=True,
    hide_index=True,
    height=min(400, 60 + len(rows) * 38),
  )

  st.markdown("#### Thao tác")
  id_by_label = {format_model_label(m): m["id"] for m in models}
  labels = list(id_by_label.keys())
  default_pick = format_model_label(active) if active else labels[0]
  restore_widget(
    "tm_view_pick", default_pick,
    preference_key="trade_models.selected",
    options=labels,
  )
  pick = st.selectbox(
    "Chọn model",
    labels,
    key="tm_view_pick",
    on_change=preference_callback("tm_view_pick", "trade_models.selected"),
  )
  mid = id_by_label[pick]
  m = next(x for x in models if x["id"] == mid)

  c1, c2, c3 = st.columns(3)
  with c1:
    if st.button(
      "Dùng cho paper & phân tích",
      icon=":material/check_circle:",
      key="tm_activate",
      use_container_width=True,
    ):
      set_active_trade_model(mid)
      st.toast(f"Đã chọn «{pick}»")
      st.rerun()
  with c2:
    report = load_model_report(mid)
    if report:
      o = report.get("overall_oos") or {}
      st.metric("Backtest R", f"{o.get('total_r', m.get('total_r', 0)):+.2f}")
    else:
      st.caption("Chưa có báo cáo backtest lưu riêng")
  with c3:
    if st.button("Xóa", icon=":material/delete:", key="tm_delete", use_container_width=True):
      if delete_trade_model(mid):
        st.toast("Đã xóa trade model")
        st.rerun()

  if st.button("Gộp model trùng", icon=":material/merge:", key="tm_dedupe"):
    from gui.trade_model import dedupe_trade_models, load_active_model_id
    keep = set()
    aid = load_active_model_id()
    if aid:
      keep.add(aid)
    result = dedupe_trade_models(keep_ids=keep)
    st.success(
      f"Giữ {result['kept']} · xóa {len(result['removed'])} trùng combo · "
      f"đổi tên {len(result['renamed'])}"
    )
    st.rerun()

  with st.expander("Chi tiết model"):
    st.json(m)
    st.caption(format_model_oneline(m))


def _render_health():
  """Monthly OOS chart KB ON vs OFF + degradation signals."""
  from gui.analysis_support import start_model_health_job
  from gui.long_task_ui import render_task_status, task_blocks_ui
  from gui.model_health import (
    assess_monthly_degradation,
    build_model_timeline_figure,
    build_monthly_kb_compare_figure,
    monthly_oos_from_report,
  )
  from gui.trade_model import (
    report_search_space_matches_model,
    render_model_picker,
  )

  models = list_trade_models()
  if not models:
    st.warning("Chưa có Trade Model — tạo từ Grid Search rồi quay lại.")
    return

  st.caption(
    "Chọn model để xem sức khỏe. Grid có nhiều **vòng KB (ep1…ep4)**; "
    "chỉ các combo đã **Lưu Trade Model** mới xuất hiện ở đây "
    f"(hiện **{len(models)}** model)."
  )
  active = render_model_picker(key="tm_health_pick", label="Trade model để kiểm tra")
  if not active:
    return

  rows = []
  for m in models:
    ss = m.get("mining_search_space") or {}
    spacing = ss.get("min_bars_between") or ["—"]
    rows.append({
      "Model": format_model_label(m),
      "KB vòng": m.get("kb_snapshot") or "—",
      "Train": f"{m.get('train_weeks')}w",
      "Session": ss.get("session_ranges") or "default",
      "Spacing": spacing[0] if spacing else "—",
      "Grid R": m.get("total_r"),
      "WR%": m.get("win_rate_pct"),
      "Active": "✓" if m.get("id") == active.get("id") else "",
    })
  st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

  st.caption(
    f"Đang xem: **{format_model_label(active)}** · "
    f"OOS `{active.get('oos_from') or '—'} → {active.get('oos_to') or '—'}` · "
    f"KB ep**{active.get('kb_snapshot') or '—'}** · "
    "KPI Grid ở bảng trên; report backtest dùng **cùng điều kiện remine** với MT5 Bridge "
    "(train/KB/session/spacing/spread)."
  )

  timeline = build_model_timeline_figure(
    active,
    title=f"Giai đoạn model · {format_model_label(active)}",
  )
  if timeline:
    st.plotly_chart(timeline, use_container_width=True)
    st.caption(
      "KB học = era bộ nhớ · Train shift = cửa sổ remine "
      f"**{active.get('train_weeks') or '—'} tuần** trước mỗi tuần OOS · "
      "OOS = khoảng kiểm chứng."
    )
  else:
    st.info("Chưa đủ thông tin KB / OOS để vẽ timeline giai đoạn.")

  render_task_status(key_prefix="tm_health")
  blocked = task_blocks_ui("tm_health")

  report_on = load_model_report(active["id"])
  report_off = load_model_kb_off_report(active["id"])
  space_ok = report_search_space_matches_model(report_on, active) if report_on else True

  if report_on and not space_ok:
    cfg_ss = (report_on.get("config") or {}).get("mining_search_space") or {}
    model_ss = active.get("mining_search_space") or {}
    st.error(
      "Report hiện tại **không khớp** search space của model "
      f"(report: session `{cfg_ss.get('session_ranges')}` · spacing "
      f"`{cfg_ss.get('min_bars_between')}` vs model: "
      f"`{model_ss.get('session_ranges')}` · `{model_ss.get('min_bars_between')}`). "
      "Lần chạy Sức khỏe trước đã dùng miner **default** → số lệch KPI Grid. "
      "Bật **Chạy lại KB ON** và bấm **Chạy so sánh**."
    )

  c1, c2, c3 = st.columns([2, 2, 1])
  with c1:
    refresh_on = st.checkbox(
      "Chạy lại KB ON (cập nhật report model)",
      value=(not bool(report_on)) or (not space_ok),
      key="tm_health_refresh_on",
      help="Bật khi chưa có report hoặc report lệch session/spacing của model.",
    )
  with c2:
    reg_r = active.get("total_r")
    on_r = (report_on or {}).get("overall_oos", {}).get("total_r") if report_on else None
    bits = [
      f"KB ON report: **{'có' if report_on else 'chưa'}**"
      + (f" ({on_r:+.1f}R)" if on_r is not None else ""),
      f"Grid KPI: **{float(reg_r):+.1f}R**" if reg_r is not None else "Grid KPI: —",
      f"KB OFF: **{'có' if report_off else 'chưa'}**",
    ]
    st.caption(" · ".join(bits))
  with c3:
    if st.button(
      "Chạy so sánh",
      type="primary",
      icon=":material/play_arrow:",
      use_container_width=True,
      disabled=blocked,
      key="tm_health_run",
    ):
      try:
        start_model_health_job(active, refresh_kb_on=refresh_on)
        st.toast("Đã bắt đầu backtest KB ON/OFF (đúng search space model)")
        st.rerun()
      except Exception as e:
        st.error(str(e))

  if not report_on:
    st.info(
      "Chưa có báo cáo backtest của model. Bấm **Chạy so sánh** "
      "(bật cập nhật KB ON) hoặc tạo report từ tab Phân tích."
    )
    return

  if not space_ok:
    st.warning(
      "Đang hiển thị report **lệch config** — chỉ mang tính tham khảo. "
      "Chạy lại so sánh để có số khớp model."
    )

  on_m = monthly_oos_from_report(report_on)
  off_m = monthly_oos_from_report(report_off) if report_off else None
  assess = assess_monthly_degradation(on_m, baseline=off_m)

  verdict = assess.get("verdict")
  if verdict == "degraded":
    st.error(assess["message"])
  elif verdict == "watch":
    st.warning(assess["message"])
  elif verdict == "stable":
    st.success(assess["message"])
  else:
    st.info(assess["message"])

  m1, m2, m3, m4 = st.columns(4)
  m1.metric("Tháng OOS", assess.get("n_months") or 0)
  m2.metric(
    "R nửa đầu",
    f"{assess['early_r']:+.1f}" if assess.get("early_r") is not None else "—",
  )
  m3.metric(
    "R nửa sau",
    f"{assess['late_r']:+.1f}" if assess.get("late_r") is not None else "—",
    delta=(
      f"{assess['delta_r']:+.1f}" if assess.get("delta_r") is not None else None
    ),
  )
  edge = assess.get("edge_late")
  m4.metric(
    "Edge KB (nửa sau)",
    f"{edge:+.1f}R" if edge is not None else "—",
    help="Tổng (KB ON − KB OFF) trên nửa sau giai đoạn OOS.",
  )

  fig = build_monthly_kb_compare_figure(
    on_m, off_m,
    title=f"OOS theo tháng · {format_model_label(active)}",
  )
  if fig:
    st.plotly_chart(fig, use_container_width=True)
  else:
    st.warning("Không gom được chuỗi theo tháng từ report.")

  if report_off is None:
    st.caption(
      "Chưa có baseline **KB OFF**. Chạy so sánh để vẽ cặp ON/OFF và đo lợi thế KB theo tháng."
    )

  table = on_m.copy()
  if off_m is not None and not off_m.empty:
    off_r = off_m.set_index("month")["total_r"]
    table["kb_off_r"] = table["month"].map(off_r)
    table["edge_r"] = (table["total_r"] - table["kb_off_r"]).round(3)
  st.dataframe(table, use_container_width=True, hide_index=True)

  with st.expander("Cách đọc"):
    st.markdown(
      "- **Bảng model**: KPI lúc **Grid/optimize** (ep3, ep4 nếu đã lưu).\n"
      "- **Timeline**: KB học → train shift → OOS.\n"
      "- **KB ON/OFF chart**: phải chạy với **đúng** session/spacing của model.\n"
      "- Nửa sau yếu / edge thu hẹp → cân nhắc học era mới hoặc Grid lại."
    )


def _render_analysis(sub: str):
  active = get_active_trade_model()
  if not active:
    st.warning("Chưa chọn Trade Model — mở tab **Quản lý** và bấm dùng model.")
    return

  from gui.trade_model import format_model_label
  st.caption(f"Phân tích theo: **{format_model_label(active)}**")

  if sub == "health":
    _render_health()
    return

  st.session_state["_analysis_hub"] = True
  try:
    if sub == "risk":
      risk_dashboard.render(embedded=True)
    elif sub == "journal":
      trade_journal.render(embedded=True)
    else:
      strategy_inspector.render(embedded=True)
  finally:
    st.session_state.pop("_analysis_hub", None)


def render(embedded: bool = False):
  if not embedded:
    st.header("Trade Models")

  models = list_trade_models()
  active = get_active_trade_model()

  if not models:
    st.info(
      "Chưa có trade model. Chạy **Grid Search** và nhấn **Tạo Trade Model** "
      "trên combo tốt nhất."
    )
    return

  sub = _resolve_subtab()

  cols = st.columns(len(SUB_KEYS))
  for col, key in zip(cols, SUB_KEYS):
    with col:
      if icon_btn(
        SUB_LABELS[key],
        key=f"tm_sub_{key}",
        icon=SUB_ICONS[key],
        active=(sub == key),
      ):
        set_widget_preference("models_subtab", key, "navigation.models_subtab")
        if key in ("risk", "journal", "strategy"):
          set_widget_preference("analysis_tab", key, "navigation.analysis_tab")
        st.rerun()

  st.divider()

  if sub == "manage":
    _render_manage(models, active)
  elif sub == "health":
    _render_health()
  else:
    _render_analysis(sub)
