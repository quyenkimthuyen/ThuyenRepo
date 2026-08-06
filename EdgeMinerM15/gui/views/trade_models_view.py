"""Trade Models — dropdown model chung + Thông tin / Sức khỏe / Rủi ro / Nhật ký / Chiến lược."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from gui.trade_model import (
  delete_trade_model,
  format_model_label,
  get_active_trade_model,
  list_trade_models,
  load_model_kb_off_report,
  load_model_report,
  set_active_trade_model,
)
from gui.charts import show_plotly
from gui.ui_theme import icon_btn
from gui.ui_preferences import preference_callback, restore_widget, set_widget_preference
from gui.views import risk_dashboard, trade_journal, strategy_inspector

# Sub-views driven by the shared model dropdown above.
SUB_KEYS = ["info", "health", "risk", "journal", "strategy"]
SUB_LABELS = {
  "info": "Thông tin",
  "health": "Sức khỏe",
  "risk": "Rủi ro",
  "journal": "Nhật ký",
  "strategy": "Chiến lược",
}
SUB_ICONS = {
  "info": ":material/info:",
  "health": ":material/monitor_heart:",
  "risk": ":material/shield:",
  "journal": ":material/receipt_long:",
  "strategy": ":material/candlestick_chart:",
}


def _resolve_subtab() -> str:
  legacy = st.session_state.get("analysis_tab")
  if legacy in ("risk", "journal", "strategy", "health") and "models_subtab" not in st.session_state:
    set_widget_preference("models_subtab", legacy, "navigation.models_subtab")
  # Old "manage" bookmark → info
  if st.session_state.get("models_subtab") == "manage":
    set_widget_preference("models_subtab", "info", "navigation.models_subtab")
  return restore_widget(
    "models_subtab", "info",
    preference_key="navigation.models_subtab",
    options=SUB_KEYS,
  )


def _on_shared_model_change():
  preference_callback("tm_shared_pick", "trade_models.selected")()
  models = list_trade_models()
  id_by_label = {format_model_label(m): m["id"] for m in models}
  pick = st.session_state.get("tm_shared_pick")
  mid = id_by_label.get(pick)
  active = get_active_trade_model()
  if mid and (not active or active.get("id") != mid):
    set_active_trade_model(mid)


def _render_shared_model_bar(models: list[dict]) -> dict | None:
  """Top dropdown — selection becomes active Trade Model for all tabs."""
  id_by_label = {format_model_label(m): m["id"] for m in models}
  labels = list(id_by_label.keys())
  active = get_active_trade_model()
  default_pick = format_model_label(active) if active else labels[0]
  if default_pick not in labels:
    default_pick = labels[0]

  restore_widget(
    "tm_shared_pick", default_pick,
    preference_key="trade_models.selected",
    options=labels,
  )

  c1, c2, c3 = st.columns([3, 1, 1])
  with c1:
    pick = st.selectbox(
      "Trade Model",
      labels,
      key="tm_shared_pick",
      on_change=_on_shared_model_change,
      help="Mọi tab Thông tin / Sức khỏe / Rủi ro / Nhật ký / Chiến lược dùng model này.",
    )
  mid = id_by_label[pick]
  m = next(x for x in models if x["id"] == mid)
  active = get_active_trade_model()
  if not active or active.get("id") != mid:
    set_active_trade_model(mid)
    active = get_active_trade_model()

  with c2:
    report = load_model_report(mid)
    if report:
      o = report.get("overall_oos") or {}
      st.metric("Backtest R", f"{o.get('total_r', m.get('total_r', 0)):+.2f}")
    elif m.get("total_r") is not None:
      st.metric("Grid R", f"{float(m.get('total_r')):+.2f}")
    else:
      st.caption("Chưa có report")

  with c3:
    if st.button(
      "Xóa",
      icon=":material/delete:",
      key="tm_delete",
      use_container_width=True,
      help="Xóa Trade Model đang chọn.",
    ):
      if delete_trade_model(mid):
        st.toast("Đã xóa trade model")
        st.rerun()

  from gui.app_settings import kb_profile_label
  from gui.workspace import profile_mismatch_details
  ss = m.get("mining_search_space") or {}
  mining_bits = []
  if ss.get("anti_chase"):
    mining_bits.append(
      f"chase rsi<{ss.get('anti_chase_fixed_rsi', '?')}"
      + (f"∨vwap<{ss.get('anti_chase_fixed_vwap')}" if ss.get("anti_chase_use_vwap") else "")
    )
  if ss.get("rr_ratios"):
    mining_bits.append(f"RR{ss.get('rr_ratios')}")
  if ss.get("selection_mode") and ss.get("selection_mode") != "legacy":
    mining_bits.append(str(ss.get("selection_mode")))
  if ss.get("exit_modes_full_only"):
    mining_bits.append("exit:full")
  mining_txt = " · ".join(mining_bits) if mining_bits else "baseline miner"
  st.caption(
    f"**{len(models)}** model · "
    f"train `{m.get('train_weeks')} tuần` · "
    f"KB `{kb_profile_label(m.get('kb_profile'))}` · "
    f"ep `{m.get('kb_snapshot') or 'latest'}` · "
    f"OOS `{m.get('oos_from') or '—'} → {m.get('oos_to') or '—'}` · "
    f"mining `{mining_txt}` · "
    f"KB pin `{'yes · ' + str(m.get('kb_fingerprint') or '')[:8] if m.get('kb_pin_path') else 'no'}`"
  )
  if report:
    mismatches = profile_mismatch_details(report, {**m, "trade_model_id": mid})
    if mismatches:
      grid_r = m.get("total_r")
      extra = f" Grid KPI: **{float(grid_r):+.2f}R**." if grid_r is not None else ""
      st.warning(
        "Báo cáo Backtest **không khớp** model đang chọn — "
        + " · ".join(mismatches)
        + f".{extra} Chạy lại báo cáo / Sức khỏe (bật **Chạy lại KB ON**)."
      )

  return active


def _render_model_info(active: dict):
  """KPI + mục tiêu của Trade Model đang chọn (trước đây ở Tổng quan)."""
  from analytics import direction_bias, trades_json_to_df, yearly_breakdown
  from gui.components import constraint_checklist, kpi_row, status_banner, warn_long_bias, warn_no_costs
  from gui.glossary import METRIC_LABELS, backtest_kpi_items
  from gui.services import load_data_meta, load_kb

  st.caption(f"Thông tin backtest của **{format_model_label(active)}**.")

  from mining_presets import space_direction_line

  ss = active.get("mining_search_space") or {}
  preset_hint = None
  grid_key = str(active.get("grid_key") or "")
  if "|msp:" in grid_key:
    preset_hint = grid_key.split("|msp:", 1)[-1].split("|", 1)[0].strip() or None
  st.info(
    f"**Hướng mining:** {space_direction_line(ss, preset_name=preset_hint)}"
    + (
      ""
      if not ss
      else (
        f"  \nKnobs: mode `{ss.get('selection_mode', 'legacy')}` · "
        f"RR `{ss.get('rr_ratios')}` · anti-chase "
        + (
          f"RSI<{ss.get('anti_chase_fixed_rsi')} "
          f"{'OR' if ss.get('anti_chase_logic') == 'or' else 'AND'} "
          f"VWAP<{ss.get('anti_chase_fixed_vwap')}"
          if ss.get("anti_chase") else "off"
        )
        + (" · exit full only" if ss.get("exit_modes_full_only") else "")
      )
    )
  )

  from gui.model_health import build_model_timeline_figure

  timeline_title = f"Giai đoạn model · {format_model_label(active)}"
  timeline = build_model_timeline_figure(active, title=timeline_title)
  if timeline:
    show_plotly(timeline, timeline_title)
    st.caption(
      "KB học = era bộ nhớ · Train shift = cửa sổ remine "
      f"**{active.get('train_weeks') or '—'} tuần** trước mỗi tuần OOS · "
      "OOS = khoảng kiểm chứng."
    )
  else:
    st.caption("Chưa đủ thông tin KB / OOS để vẽ timeline giai đoạn.")

  report = load_model_report(active["id"])
  kb = load_kb(active.get("kb_profile") or "default")
  kb_summary = {
    "genomes": len(kb.genomes),
    "rules": len(kb.rule_stats),
    "ml_samples": len(kb.ml_experience),
  }
  data_meta = load_data_meta()

  status_banner(report, kb_summary, data_meta)
  warn_no_costs()

  if not report:
    st.info(
      "Chưa có báo cáo backtest của model. Vào **Sức khỏe** → **Chạy so sánh** "
      "để tạo report, hoặc tạo model từ Grid Search."
    )
    from gui.live_readiness import render_live_readiness
    render_live_readiness(
      active,
      include_bridge=False,
      expanded=True,
      key_prefix="tm_info_ready",
    )
    return

  o = report.get("overall_oos") or {}
  y = report.get("last_1_year") or {}
  items = backtest_kpi_items(o, y)
  if o.get("trades_per_week") is not None:
    items.append((
      METRIC_LABELS["trades_per_week"],
      f"{o['trades_per_week']}",
      f"{o.get('n_trades', '—')} lệnh",
    ))
  kpi_row(items)

  with st.expander("Mục tiêu & OOS theo năm", expanded=False):
    constraint_checklist(report.get("constraints_met", {}))
    trades_df = trades_json_to_df(report.get("trades", []))
    if not trades_df.empty:
      st.dataframe(yearly_breakdown(trades_df), use_container_width=True, hide_index=True)
      bias = direction_bias(trades_df)
      if not bias.empty and "LONG" in bias["dir"].values:
        pct = bias.loc[bias["dir"] == "LONG", "pct"].iloc[0]
        warn_long_bias(pct)

  from gui.live_readiness import render_live_readiness

  render_live_readiness(
    active,
    include_bridge=False,
    expanded=False,
    key_prefix="tm_info_ready",
  )


def _render_health(active: dict):
  """Monthly OOS chart KB ON vs OFF + degradation signals."""
  from gui.analysis_support import start_model_health_job
  from gui.long_task_ui import render_task_status, task_blocks_ui
  from gui.model_health import (
    assess_monthly_degradation,
    build_monthly_kb_compare_figure,
    monthly_oos_from_report,
  )
  from gui.trade_model import report_search_space_matches_model

  st.caption(
    f"Đang xem: **{format_model_label(active)}** · "
    "report backtest dùng cùng điều kiện remine với MT5 Bridge. "
    "Timeline giai đoạn nằm ở tab **Thông tin**."
  )

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
      "(bật cập nhật KB ON)."
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

  m1, m2, m3, m4, m5 = st.columns(5)
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
  m4.metric(
    "Edge KB nửa đầu",
    f"{assess['edge_early']:+.1f}R" if assess.get("edge_early") is not None else "—",
    help="Tổng (KB ON − KB OFF) trên nửa đầu OOS.",
  )
  m5.metric(
    "Edge KB nửa sau",
    f"{assess['edge_late']:+.1f}R" if assess.get("edge_late") is not None else "—",
    delta=(
      f"{assess['edge_delta']:+.1f}" if assess.get("edge_delta") is not None else None
    ),
    help="Tổng (KB ON − KB OFF) nửa sau · delta = nửa sau − nửa đầu.",
  )

  monthly_title = f"OOS theo tháng · {format_model_label(active)}"
  fig = build_monthly_kb_compare_figure(on_m, off_m, title=monthly_title)
  if fig:
    show_plotly(fig, monthly_title)
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
      "- **KB ON/OFF chart**: phải chạy với **đúng** session/spacing của model.\n"
      "- Nửa sau yếu / edge thu hẹp → cân nhắc học era mới hoặc Grid lại.\n"
      "- Timeline giai đoạn (KB / train / OOS) nằm ở tab **Thông tin**.\n"
      "- **Remine ON/OFF** (bên dưới): freeze strategy tuần đầu vs remine mỗi tuần.\n"
      "- **Mining space vs baseline** (bên dưới): tách riêng “preset lỗi thời” "
      "khỏi suy giảm KB/market."
    )

  _render_remine_on_off(active, report_on)
  _render_mining_space_freshness(active, report_on)


def _render_remine_on_off(active: dict, report_on: dict | None):
  """Remine weekly (ON) vs freeze first-week strategy (OFF)."""
  from gui.analysis_support import start_remine_health_job
  from gui.charts import show_plotly
  from gui.long_task_ui import render_task_status, task_blocks_ui
  from gui.model_health import (
    assess_monthly_degradation,
    build_monthly_kb_compare_figure,
    monthly_oos_from_report,
  )
  from gui.trade_model import load_model_remine_off_report

  st.divider()
  st.markdown("#### Remine ON / OFF")
  st.caption(
    "**ON** = mine lại mỗi tuần (report Health hiện có). "
    "**OFF** = mine tuần OOS đầu rồi **giữ nguyên** strategy cho các tuần sau "
    "(cùng KB / train / OOS)."
  )

  render_task_status(key_prefix="tm_remine_health")
  blocked = task_blocks_ui("tm_remine_health")
  report_off = load_model_remine_off_report(active["id"])

  c1, c2, c3 = st.columns([2, 2, 1])
  with c1:
    refresh_on = st.checkbox(
      "Chạy lại Remine ON trước khi so",
      value=not bool(report_on),
      key="tm_remine_refresh_on",
      help="Thường tắt nếu đã có report Health (KB ON / remine weekly).",
    )
  with c2:
    on_r = (report_on or {}).get("overall_oos", {}).get("total_r") if report_on else None
    off_r = (report_off or {}).get("overall_oos", {}).get("total_r") if report_off else None
    bits = [
      f"Remine ON: **{'có' if report_on else 'chưa'}**"
      + (f" ({on_r:+.1f}R)" if on_r is not None else ""),
      f"Remine OFF: **{'có' if report_off else 'chưa'}**"
      + (f" ({off_r:+.1f}R)" if off_r is not None else ""),
    ]
    st.caption(" · ".join(bits))
  with c3:
    if st.button(
      "So Remine",
      type="secondary",
      icon=":material/compare_arrows:",
      use_container_width=True,
      disabled=blocked,
      key="tm_remine_run",
    ):
      try:
        start_remine_health_job(active, refresh_remine_on=refresh_on)
        st.toast("Đã bắt đầu Remine ON/OFF")
        st.rerun()
      except Exception as e:
        st.error(str(e))

  if not report_on or not report_off:
    st.info(
      "Bấm **So Remine** để chạy Remine OFF (freeze tuần đầu). "
      "Remine ON dùng report Health nếu đã có."
    )
    return

  on_m = monthly_oos_from_report(report_on)
  off_m = monthly_oos_from_report(report_off)
  assess = assess_monthly_degradation(on_m, baseline=off_m)

  on_total = (report_on.get("overall_oos") or {}).get("total_r")
  off_total = (report_off.get("overall_oos") or {}).get("total_r")
  edge = None
  if on_total is not None and off_total is not None:
    edge = float(on_total) - float(off_total)

  k1, k2, k3, k4 = st.columns(4)
  k1.metric(
    "Total R · Remine ON",
    f"{float(on_total):+.1f}" if on_total is not None else "—",
  )
  k2.metric(
    "Total R · Remine OFF",
    f"{float(off_total):+.1f}" if off_total is not None else "—",
  )
  k3.metric(
    "Edge ON−OFF",
    f"{edge:+.1f}R" if edge is not None else "—",
    help="Dương = remine hàng tuần tốt hơn freeze strategy tuần đầu.",
  )
  k4.metric(
    "Edge nửa sau",
    f"{assess['edge_late']:+.1f}R" if assess.get("edge_late") is not None else "—",
    delta=(
      f"{assess['edge_delta']:+.1f}" if assess.get("edge_delta") is not None else None
    ),
    help="Σ (Remine ON − OFF) trên nửa sau OOS.",
  )

  if edge is not None:
    if edge >= 5:
      st.success(
        f"Remine ON hơn OFF **{edge:+.1f}R** trên toàn OOS — "
        "remine hàng tuần đang có giá trị."
      )
    elif edge <= -5:
      st.warning(
        f"Remine ON kém OFF **{edge:+.1f}R** — "
        "trên kỳ này freeze strategy tuần đầu tốt hơn (remine có thể nhiễu)."
      )
    else:
      st.info(
        f"Remine ON≈OFF (Δ {edge:+.1f}R) — lợi thế remine chưa rõ trên kỳ OOS này."
      )

  title = f"OOS theo tháng · Remine ON vs OFF · {format_model_label(active)}"
  fig = build_monthly_kb_compare_figure(
    on_m, off_m,
    title=title,
    on_name="Remine ON",
    off_name="Remine OFF",
    on_color="#26a69a",
    off_color="#ef6c00",
    cum_on_color="#2962ff",
  )
  if fig:
    show_plotly(fig, title)

  table = on_m.copy()
  if off_m is not None and not off_m.empty:
    off_map = off_m.set_index("month")["total_r"]
    table["remine_off_r"] = table["month"].map(off_map)
    table["edge_r"] = (table["total_r"] - table["remine_off_r"]).round(3)
  st.dataframe(table, use_container_width=True, hide_index=True)

  with st.expander("Cách đọc Remine ON/OFF"):
    st.markdown(
      "- **Remine ON**: mỗi tuần mine lại trên cửa sổ train (đường Live/Health).\n"
      "- **Remine OFF**: chỉ mine tuần đầu OOS, giữ strategy đó suốt kỳ.\n"
      "- **Edge dương** → nên giữ remine tuần. **Edge âm mạnh** → cân nhắc freeze / "
      "rà soát search space.\n"
      "- Khác KB ON/OFF: cả hai nhánh Remine đều dùng **cùng KB** của model."
    )


def _render_mining_space_freshness(active: dict, report_on: dict | None):
  """A/B active mining space vs baseline miner — stale-space signal."""
  from gui.analysis_support import start_mining_space_health_job
  from gui.charts import show_plotly
  from gui.long_task_ui import render_task_status, task_blocks_ui
  from gui.mining_space_health import (
    assess_mining_space_freshness,
    build_monthly_space_compare_figure,
  )
  from gui.model_health import monthly_oos_from_report
  from gui.trade_model import load_model_mining_baseline_report
  from mining_presets import match_preset_name, preset_label, space_direction_line

  st.divider()
  st.markdown("#### Mining space vs baseline miner")
  ss = active.get("mining_search_space") or {}
  preset = match_preset_name(ss)
  if not ss or preset == "baseline":
    st.info(
      "Model đang dùng **baseline miner** (hoặc không gắn preset) — "
      "không cần A/B mining space. Đổi preset qua Grid nếu muốn hướng Elite/…"
    )
    return

  st.caption(
    f"Hướng model: {space_direction_line(ss, preset_name=preset)}. "
    "So với **baseline** trên **cùng** KB / train / OOS — "
    "để biết preset còn giữ lợi thế hay đã lỗi thời."
  )

  render_task_status(key_prefix="tm_msp_health")
  blocked = task_blocks_ui("tm_msp_health")
  report_base = load_model_mining_baseline_report(active["id"])

  c1, c2, c3 = st.columns([2, 2, 1])
  with c1:
    refresh_active = st.checkbox(
      "Chạy lại report active trước khi so",
      value=not bool(report_on),
      key="tm_msp_refresh_active",
      help="Thường tắt nếu đã có report KB ON khớp model.",
    )
  with c2:
    st.caption(
      f"Active report: **{'có' if report_on else 'chưa'}** · "
      f"Baseline miner: **{'có' if report_base else 'chưa'}** · "
      f"Preset: **{preset_label(preset) if preset else 'custom'}**"
    )
  with c3:
    if st.button(
      "So mining space",
      type="secondary",
      icon=":material/compare_arrows:",
      use_container_width=True,
      disabled=blocked,
      key="tm_msp_run",
    ):
      try:
        start_mining_space_health_job(active, refresh_active=refresh_active)
        st.toast("Đã bắt đầu A/B mining space vs baseline")
        st.rerun()
      except Exception as e:
        st.error(str(e))

  if not report_on or not report_base:
    st.info(
      "Bấm **So mining space** để chạy walk-forward baseline miner "
      "(cùng KB/train/OOS). Có thể mất vài phút."
    )
    return

  assess = assess_mining_space_freshness(
    report_on, report_base, preset_name=preset,
  )
  verdict = assess.get("verdict")
  if verdict == "stale":
    st.error(assess["message"])
  elif verdict == "watch":
    st.warning(assess["message"])
  elif verdict == "fresh":
    st.success(assess["message"])
  else:
    st.info(assess["message"])

  active_oos = assess.get("active") or {}
  base_oos = assess.get("baseline") or {}
  delta = assess.get("delta") or {}
  on_r = active_oos.get("total_r")
  off_r = base_oos.get("total_r")
  on_wr = active_oos.get("win_rate_pct")
  off_wr = base_oos.get("win_rate_pct")
  d_r = delta.get("total_r")
  d_wr = delta.get("win_rate_pct")
  d_rr = delta.get("avg_rr")

  m1, m2, m3, m4, m5, m6 = st.columns(6)
  m1.metric(
    "Total R · Active",
    f"{float(on_r):+.1f}" if on_r is not None else "—",
  )
  m2.metric(
    "Total R · Baseline",
    f"{float(off_r):+.1f}" if off_r is not None else "—",
  )
  m3.metric(
    "ΔR",
    f"{float(d_r):+.1f}" if d_r is not None else "—",
    help="Active − Baseline · Total R toàn OOS.",
  )
  m4.metric(
    "WR · Active",
    f"{float(on_wr):.1f}%" if on_wr is not None else "—",
  )
  m5.metric(
    "WR · Baseline",
    f"{float(off_wr):.1f}%" if off_wr is not None else "—",
  )
  m6.metric(
    "ΔWR",
    f"{float(d_wr):+.1f}pp" if d_wr is not None else "—",
    delta=(f"ΔRR {float(d_rr):+.2f}" if d_rr is not None else None),
    help="Active − Baseline · Win rate toàn OOS. ΔRR ở dòng phụ.",
  )

  e1, e2, e3 = st.columns(3)
  e1.metric("Tháng chung", assess.get("n_months") or 0)
  e2.metric(
    "Edge R nửa sau",
    f"{assess['late_edge_r']:+.1f}R" if assess.get("late_edge_r") is not None else "—",
    help="Σ (active − baseline) R trên nửa sau OOS.",
  )
  e3.metric(
    f"Edge R {assess.get('recent_months') or 3} tháng gần",
    f"{assess['recent_edge_r']:+.1f}R" if assess.get("recent_edge_r") is not None else "—",
  )

  on_m = monthly_oos_from_report(report_on)
  base_m = monthly_oos_from_report(report_base)
  space_title = (
    f"Mining space · {preset_label(preset) if preset else 'active'} vs baseline"
  )
  fig = build_monthly_space_compare_figure(
    on_m, base_m,
    title=space_title,
    active_name=preset_label(preset) if preset else "Active space",
    baseline_name="Baseline miner",
  )
  if fig:
    show_plotly(fig, space_title)

  # Monthly table: R + WR side by side
  table = on_m.copy()
  if base_m is not None and not base_m.empty:
    b = base_m.set_index("month")
    table["baseline_r"] = table["month"].map(b["total_r"])
    table["edge_r"] = (table["total_r"] - table["baseline_r"]).round(3)
    if "win_rate_pct" in b.columns:
      table["baseline_wr"] = table["month"].map(b["win_rate_pct"])
    if "win_rate_pct" in table.columns and "baseline_wr" in table.columns:
      table["edge_wr_pp"] = (table["win_rate_pct"] - table["baseline_wr"]).round(1)
    table = table.rename(columns={
      "total_r": "active_r",
      "win_rate_pct": "active_wr",
    })
  st.dataframe(table, use_container_width=True, hide_index=True)

  with st.expander("Cách đọc mining space"):
    st.markdown(
      "- Biểu đồ trên: **Total R** (cột) và **Win rate %** (đường) — cùng tháng.\n"
      "- Preset hướng WR: ưu tiên **ΔWR**; **ΔR** là sanity check PnL.\n"
      "- **ΔWR và ΔRR đều âm** hoặc edge R nửa sau / 3 tháng gần âm mạnh → "
      "preset có thể lỗi thời.\n"
      "- Khác KB ON/OFF: cố định KB, chỉ đổi **khung mine**."
    )


def _render_analysis(sub: str, active: dict):
  st.caption(f"Phân tích theo: **{format_model_label(active)}**")
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
  if not models:
    st.info(
      "Chưa có trade model. Chạy **Grid Search** và nhấn **Tạo Trade Model** "
      "trên combo tốt nhất."
    )
    return

  active = _render_shared_model_bar(models)
  if not active:
    st.warning("Chưa chọn được Trade Model.")
    return

  st.divider()
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

  if sub == "info":
    _render_model_info(active)
  elif sub == "health":
    _render_health(active)
  else:
    _render_analysis(sub, active)
