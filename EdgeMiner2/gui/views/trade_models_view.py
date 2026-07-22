"""Trade Models — quản lý model + phân tích (Risk / Nhật ký / Chiến lược)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from gui.trade_model import (
  delete_trade_model,
  format_model_label,
  format_model_oneline,
  get_active_trade_model,
  list_trade_models,
  load_model_report,
  set_active_trade_model,
)
from gui.ui_theme import icon_btn
from gui.ui_preferences import preference_callback, restore_widget, set_widget_preference
from gui.views import risk_dashboard, trade_journal, strategy_inspector

# Child of Trade Models: quản lý + phân tích theo model đang chọn
SUB_KEYS = ["manage", "risk", "journal", "strategy"]
SUB_LABELS = {
  "manage": "Quản lý",
  "risk": "Rủi ro",
  "journal": "Nhật ký",
  "strategy": "Chiến lược",
}
SUB_ICONS = {
  "manage": ":material/inventory_2:",
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
      "Train": f"{m.get('train_months')}T",
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
    keep.add("tm_best_3m_64e3f742")
    result = dedupe_trade_models(keep_ids=keep)
    st.success(
      f"Giữ {result['kept']} · xóa {len(result['removed'])} trùng combo · "
      f"đổi tên {len(result['renamed'])}"
    )
    st.rerun()

  with st.expander("Chi tiết model"):
    st.json(m)
    st.caption(format_model_oneline(m))


def _render_analysis(sub: str):
  active = get_active_trade_model()
  if not active:
    st.warning("Chưa chọn Trade Model — mở tab **Quản lý** và bấm dùng model.")
    return

  from gui.trade_model import format_model_label
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
  active = get_active_trade_model()

  if not models:
    st.info(
      "Chưa có trade model. Chạy **Grid Search** và nhấn **Tạo Trade Model** "
      "trên combo tốt nhất."
    )
    return

  sub = _resolve_subtab()

  cols = st.columns(4)
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
  else:
    _render_analysis(sub)
