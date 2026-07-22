"""Trade Models — danh sách mô hình tạo từ Grid Search."""
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
  pick = st.selectbox(
    "Chọn model",
    list(id_by_label.keys()),
    key="tm_view_pick",
  )
  mid = id_by_label[pick]
  m = next(x for x in models if x["id"] == mid)

  c1, c2, c3 = st.columns(3)
  with c1:
    if st.button("✓ Dùng cho paper & phân tích", key="tm_activate", use_container_width=True):
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
    if st.button("🗑 Xóa", key="tm_delete", use_container_width=True):
      if delete_trade_model(mid):
        st.toast("Đã xóa trade model")
        st.rerun()

  if st.button("🧹 Gộp model trùng combo / trùng tên", key="tm_dedupe"):
    from gui.trade_model import dedupe_trade_models, load_active_model_id
    keep = set()
    aid = load_active_model_id()
    if aid:
      keep.add(aid)
    # Prefer known Best 3m id if present
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
