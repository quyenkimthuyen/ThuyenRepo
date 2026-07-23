"""Report Compare — so sánh nhiều báo cáo backtest."""
from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from analytics import equity_series, trades_json_to_df
from gui.report_store import (
  delete_report, import_current_backtest, list_reports, load_report,
  report_label, save_report, summaries_table,
)
from gui.live_workflow import apply_report_to_profile, assess_workflow, load_workflow_state
from gui.services import BACKTEST_REPORT, load_backtest_report


def _metrics_bar_chart(df, metric: str, title: str):
  if df.empty:
    return None
  colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in df[metric]] if metric == "Total R" else "#3498db"
  fig = go.Figure(go.Bar(x=df["label"], y=df[metric], marker_color=colors))
  fig.update_layout(title=title, height=320, margin=dict(l=40, r=20, t=50, b=80))
  fig.update_xaxes(tickangle=-25)
  return fig


def _equity_overlay(reports: list[dict]):
  fig = go.Figure()
  for r in reports:
    trades = trades_json_to_df(r.get("trades", []))
    eq = equity_series(trades)
    if eq.empty:
      continue
    fig.add_trace(go.Scatter(
      x=eq["entry"], y=eq["equity_r"],
      name=r.get("_label", "run")[:40],
      mode="lines",
    ))
  fig.update_layout(
    title="Equity curve (R) — overlay",
    height=400, margin=dict(l=40, r=20, t=50, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
  )
  return fig


def render(embedded: bool = False):
  embedded = embedded or bool(st.session_state.get("_research_hub"))
  if not embedded:
    st.header("Report Compare")
    st.caption("Lưu và so sánh nhiều lần chạy backtest — KB ON/OFF, profile, giai đoạn OOS")

  wf = assess_workflow()
  state = load_workflow_state()
  st.markdown("#### Bước 3 — Chọn combo OOS (ổn định, không chỉ R cao)")
  st.caption(
    "Xếp hạng theo **điểm ổn định** = ưu tiên R & PF cao, sụt giảm thấp. "
    "Nhấn **Áp dụng** để gán vào Trade Profile đang dùng."
  )
  ranked = wf.get("ranked_reports") or []
  if ranked:
    for e in ranked[:6]:
      s = e.get("summary") or {}
      chosen = state.get("chosen_report_id") == e["id"]
      c1, c2, c3 = st.columns([5, 1, 1])
      with c1:
        mark = "✅ " if chosen else ""
        st.markdown(
          f"{mark}**{e.get('label', e['id'])}**  \n"
          f"{s.get('total_r', '—')}R · DD {s.get('max_drawdown_r', '—')}R · "
          f"PF {s.get('profit_factor', '—')} · WR {s.get('win_rate_pct', '—')}% · "
          f"điểm **{e.get('stability', '—')}**"
        )
      with c2:
        if st.button("Áp dụng", key=f"rc_apply_{e['id']}", use_container_width=True):
          out = apply_report_to_profile(e["id"])
          if out.get("ok"):
            st.toast(f"Đã áp dụng profile: {out.get('label')}")
            st.rerun()
          else:
            st.error(out.get("error"))
      with c3:
        if chosen:
          st.caption("Đang dùng")
  else:
    st.info("Chưa có báo cáo trong kho — hoàn thành bước 1–2 trước.")

  st.divider()

  archived = list_reports()
  current = load_backtest_report()

  c1, c2, c3 = st.columns(3)
  with c1:
    if st.button("💾 Lưu báo cáo hiện tại", type="primary", use_container_width=True):
      if current:
        rid = save_report(current)
        st.success(f"Đã lưu `{rid}`")
        st.rerun()
      else:
        st.warning("Chưa có backtest_report.json — chạy backtest trước.")
  with c2:
    if st.button("📥 Import từ file mới nhất", use_container_width=True):
      rid = import_current_backtest(BACKTEST_REPORT)
      if rid:
        st.success(f"Đã import `{rid}`")
        st.rerun()
      else:
        st.warning("Không tìm thấy báo cáo.")
  with c3:
    if archived and st.button("🗑 Xóa tất cả archive", use_container_width=True):
      for r in archived:
        delete_report(r["id"])
      st.rerun()

  st.divider()
  st.subheader("Kho báo cáo đã lưu")

  if not archived:
    st.info(
      "Chưa có báo cáo trong kho. Chạy backtest tại **Nghiên cứu → Backtest**, "
      "rồi nhấn **Lưu báo cáo hiện tại** (hoặc bật Lưu Report Compare khi chạy)."
    )
    if current:
      st.markdown("**Báo cáo mới nhất (chưa lưu):**")
      st.caption(report_label(current))
      o = current.get("overall_oos", {})
      st.write(
        f"WR **{o.get('win_rate_pct')}%** · RR **{o.get('avg_rr')}** · "
        f"**{o.get('total_r')}R** · DD **{o.get('max_drawdown_r')}R**"
      )
    return

  df_all = summaries_table(archived)
  st.dataframe(df_all.drop(columns=["id"]), use_container_width=True, hide_index=True)

  st.subheader("Chọn báo cáo để so sánh")
  options = {f"{r['label']} ({r['id']})": r["id"] for r in archived}
  selected_labels = st.multiselect(
    "Chọn 2–4 báo cáo",
    list(options.keys()),
    default=list(options.keys())[: min(2, len(options))],
    key="cmp_pick",
  )
  selected_ids = [options[l] for l in selected_labels]

  if len(selected_ids) < 2:
    st.caption("Chọn ít nhất 2 báo cáo để so sánh.")
    return

  reports = []
  for rid in selected_ids:
    r = load_report(rid)
    if r:
      meta = next((x for x in archived if x["id"] == rid), {})
      r["_label"] = meta.get("label", rid)
      r["_id"] = rid
      reports.append(r)

  cmp_rows = []
  for r in reports:
    o = r.get("overall_oos", {})
    cfg = r.get("config", {})
    cmp_rows.append({
      "label": r["_label"],
      "KB": "ON" if cfg.get("use_learning_kb") else "OFF",
      "Profile": cfg.get("kb_profile") or "-",
      "OOS": f"{cfg.get('oos_from') or '?'} → {cfg.get('oos_to') or '?'}",
      "Lệnh": o.get("n_trades"),
      "WR%": o.get("win_rate_pct"),
      "RR": o.get("avg_rr"),
      "Total R": o.get("total_r"),
      "DD (R)": o.get("max_drawdown_r"),
      "PF": o.get("profit_factor"),
      "Lệnh/tuần": o.get("trades_per_week"),
    })

  import pandas as pd
  cmp_df = pd.DataFrame(cmp_rows)
  st.markdown("#### Bảng so sánh")
  st.dataframe(cmp_df, use_container_width=True, hide_index=True)

  if len(cmp_df) >= 2:
    base_r = cmp_df.iloc[0]["Total R"]
    deltas = [0.0] + [float(cmp_df.iloc[i]["Total R"]) - float(base_r) for i in range(1, len(cmp_df))]
    st.caption(f"Δ Total R so với **{cmp_df.iloc[0]['label'][:50]}**: " +
               " · ".join(f"{d:+.2f}R" for d in deltas))

  c1, c2 = st.columns(2)
  with c1:
    fig = _metrics_bar_chart(cmp_df, "Total R", "Total R")
    if fig:
      st.plotly_chart(fig, use_container_width=True)
  with c2:
    fig2 = _metrics_bar_chart(cmp_df, "WR%", "Win Rate %")
    if fig2:
      st.plotly_chart(fig2, use_container_width=True)

  fig3 = _equity_overlay(reports)
  if fig3 and fig3.data:
    st.plotly_chart(fig3, use_container_width=True)

  st.subheader("Xóa báo cáo")
  del_id = st.selectbox("Chọn ID xóa", [r["id"] for r in archived], key="cmp_del")
  if st.button("Xóa báo cáo đã chọn"):
    delete_report(del_id)
    st.rerun()
