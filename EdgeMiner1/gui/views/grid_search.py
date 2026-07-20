"""Grid Search — tìm setting backtest tối ưu."""
from __future__ import annotations

from datetime import timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from gui.grid_search_background import (
  get_grid_status, is_grid_running, load_job_state,
  start_grid_search, stop_grid_search,
)
from gui.grid_search_engine import (
  OBJECTIVES, apply_best_as_new_trade_profile, apply_best_to_profile,
  build_grid, estimate_grid_count, load_latest_grid_run,
  snapshots_for_profile,
)
from gui.trade_profile import get_active_trade_profile, render_profile_card
from gui.workspace import get_active_workspace


@st.fragment(run_every=timedelta(seconds=5))
def _grid_progress_fragment():
  """Tự refresh tiến trình khi grid đang chạy nền."""
  status = get_grid_status()
  if status["running"]:
    st.rerun()


def _render_job_status():
  status = get_grid_status()
  job = load_job_state() or {}

  if status["status"] == "idle" and not job.get("run_id"):
    return status

  if status["running"]:
    st.info(
      f"⏳ **Grid Search đang chạy nền** — {status['done']}/{status['total']} "
      f"({status['pct']}%) · `{status['current_label'] or '…'}`\n\n"
      "Bạn có thể chuyển tab/trang khác — tiến trình **không bị dừng**."
    )
    st.progress(status["done"] / max(status["total"], 1))
    if st.button("⏹ Hủy grid search", key="gs_cancel"):
      stop_grid_search()
      st.toast("Đã gửi tín hiệu hủy")
      st.rerun()
    _grid_progress_fragment()
  elif status["status"] == "completed":
    st.success(
      f"✅ Hoàn thành `{status.get('run_id')}` — "
      f"{status['n_rows']} combo · mục tiêu **{OBJECTIVES.get(status.get('objective', ''), status.get('objective'))}**"
    )
  elif status["status"] == "cancelled":
    st.warning(f"Đã hủy — hoàn thành {status['done']}/{status['total']} combo (kết quả một phần đã lưu).")
  elif status["status"] == "interrupted":
    st.warning(
      f"⚠️ Grid bị gián đoạn (restart server?) — {status['done']}/{status['total']}. "
      "Đang tự tiếp tục nếu có thể…"
    )
    _grid_progress_fragment()
  elif status["status"] == "error":
    st.error(f"Lỗi grid search: {status.get('error') or 'unknown'}")

  return status


def _rows_for_display(status: dict) -> tuple[list, str]:
  job = load_job_state() or {}
  data = load_latest_grid_run()

  if status.get("running") and job.get("rows"):
    return job["rows"], job.get("objective", "total_r")

  rows = (data or {}).get("rows") or job.get("rows") or []
  objective = (
    (data or {}).get("objective")
    or job.get("objective")
    or "total_r"
  )
  return rows, objective


def render(embedded: bool = False):
  embedded = embedded or bool(st.session_state.get("_research_hub"))
  if not embedded:
    st.header("Tìm tham số tối ưu")
    st.caption("Thử nhiều combo — kết quả lưu vào **Cấu hình giao dịch**")

  render_profile_card(show_hint=not embedded)
  st.caption(
    "_Quét nhiều cửa sổ học / bộ nhớ / vòng học. Giai đoạn kiểm chứng & phí cố định theo profile._"
  )

  job_status = _render_job_status()
  running = bool(job_status.get("running"))

  tp = get_active_trade_profile()
  ws = get_active_workspace()
  oos_from = tp.get("oos_from") or ws.get("oos_from", "2025-01-01")
  oos_to = tp.get("oos_to") or ws.get("oos_to", "2026-12-31")
  spread = float(tp.get("spread_pips", ws.get("spread_pips", 1.0)))
  slip = float(tp.get("slippage_pips", ws.get("slippage_pips", 0.3)))
  profile_train = tp.get("train_months", 6)
  default_trains = sorted(set([profile_train, 3, 6, 12]))

  st.subheader("Không gian tìm kiếm")

  c1, c2 = st.columns(2)
  with c1:
    train_months = st.multiselect(
      "Cửa sổ học (tháng)",
      [2, 3, 4, 6, 12],
      default=default_trains,
      key="gs_train",
      disabled=running,
    )
    include_kb_off = st.checkbox("Thử không dùng bộ nhớ", value=True, key="gs_kb_off", disabled=running)
    from gui.components import _profile_label
    from kb_profiles import list_era_profiles as kb_list_profiles
    era_options = {
      _profile_label(p): p["id"]
      for p in kb_list_profiles()
    }
    default_era_labels = [
      lbl for lbl, pid in era_options.items()
      if pid in {ws.get("kb_profile"), "era_2024", "era_2023_2024"}
    ]
    picked_era_labels = st.multiselect(
      "Giai đoạn bộ nhớ (chọn nhiều)",
      list(era_options.keys()),
      default=[l for l in default_era_labels if l in era_options],
      key="gs_profiles",
      disabled=running,
      help="Chọn một hoặc nhiều giai đoạn — grid sẽ thử từng combo.",
    )
    kb_profiles = [era_options[l] for l in picked_era_labels]
  with c2:
    epoch_mode = st.radio(
      "Vòng học",
      ["latest", "all", "selected"],
      format_func=lambda x: {
        "latest": "Chỉ mới nhất",
        "all": "Mọi vòng (1, 2, …)",
        "selected": "Chọn vòng thủ công",
      }[x],
      key="gs_epoch_mode",
      help="Mỗi giai đoạn có các vòng học riêng — 'mọi vòng' tăng số lần chạy.",
      disabled=running,
    )
    objective = st.selectbox(
      "Mục tiêu tối ưu",
      list(OBJECTIVES.keys()),
      format_func=lambda k: OBJECTIVES[k],
      key="gs_objective",
      disabled=running,
    )
    max_runs = st.slider("Giới hạn số lần chạy", 6, 120, 48, 6, key="gs_max_runs", disabled=running)

  selected_epochs: dict[str, list] = {}
  if epoch_mode == "selected" and kb_profiles and not running:
    st.markdown("**Chọn epoch theo profile**")
    for pid in kb_profiles:
      snaps = snapshots_for_profile(pid)
      labels = ["latest" if s is None else f"ep{s:03d}" for s in snaps]
      pick = st.multiselect(
        f"`{pid}`",
        labels,
        default=labels[:1],
        key=f"gs_ep_{pid}",
      )
      selected_epochs[pid] = [
        None if p == "latest" else int(p.replace("ep", "")) for p in pick
      ]

  grid_kwargs = dict(
    train_months=train_months or [3],
    kb_profiles=kb_profiles or [],
    include_kb_off=include_kb_off,
    epoch_mode=epoch_mode,
    selected_epochs=selected_epochs,
    oos_from=oos_from,
    oos_to=oos_to,
    spread_pips=spread,
    slippage_pips=slip,
    max_runs=max_runs,
  )
  full_n, run_n = estimate_grid_count(**grid_kwargs)

  if not running:
    if full_n > max_runs:
      st.warning(f"Tổ hợp đầy đủ: **{full_n}** — sẽ chạy **{run_n}** (giới hạn slider).")
    else:
      st.info(
        f"Sẽ chạy **{run_n}** backtest walk-forward (~{run_n * 1.5:.0f}–{run_n * 3:.0f} phút). "
        "Chạy **nền** — đổi tab/trang không làm dừng."
      )

  run_btn = st.button(
    "▶ Chạy Grid Search (nền)",
    type="primary",
    key="gs_run",
    disabled=running,
  )

  if run_btn:
    if not train_months:
      st.error("Chọn ít nhất một train window.")
      return
    if not include_kb_off and not kb_profiles:
      st.error("Bật KB OFF hoặc chọn ít nhất một KB profile.")
      return
    if is_grid_running():
      st.warning("Grid search đang chạy.")
      return

    specs = build_grid(**grid_kwargs)
    try:
      rid = start_grid_search(specs, objective=objective, config=grid_kwargs)
      st.toast(f"Đã bắt đầu grid `{rid}` — chạy nền")
      st.rerun()
    except RuntimeError as e:
      st.error(str(e))

  rows, objective = _rows_for_display(job_status)
  data = load_latest_grid_run()

  if not rows and not running:
    st.info("Cấu hình không gian tìm kiếm và nhấn **Chạy Grid Search (nền)**.")
    return

  if running and not rows:
    st.caption("Đang chờ kết quả combo đầu tiên…")
    return

  if data and data.get("updated_at") and not running:
    st.caption(
      f"Lần chạy: `{data.get('run_id')}` · {data['updated_at']} · "
      f"Mục tiêu: **{OBJECTIVES.get(objective, objective)}**"
    )

  best = rows[0] if rows else None
  if best and not best.get("error"):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏆 Total R", f"{best.get('total_r', 0):+.2f}")
    c2.metric("WR%", f"{best.get('win_rate_pct', 0)}%")
    c3.metric("Max DD", f"{best.get('max_drawdown_r', 0)}R")
    c4.metric("Train", f"{best.get('train_months')}m")
    st.success(
      f"**Tốt nhất hiện tại:** {best.get('label')} · "
      f"PF {best.get('profit_factor')} · {best.get('n_trades')} lệnh"
    )
    if not running:
      b1, b2 = st.columns(2)
      with b1:
        if st.button("✓ Áp dụng combo tốt → Trade Profile", key="gs_apply_ws"):
          apply_best_to_profile(best, run_id=(data or {}).get("run_id"))
          st.toast("Đã cập nhật trade profile active")
          st.rerun()
      with b2:
        new_name = st.text_input(
          "Tên profile mới",
          value=f"Grid best {best.get('train_months')}m",
          key="gs_new_tp_name",
          label_visibility="collapsed",
        )
        if st.button("＋ Tạo Trade Profile mới", key="gs_new_tp"):
          name = (new_name.strip() or None)
          if not name:
            st.error("Nhập tên profile.")
          else:
            try:
              apply_best_as_new_trade_profile(
                best, run_id=(data or {}).get("run_id"), label=name,
              )
            except ValueError as e:
              st.error(str(e))
            else:
              st.toast(f"Đã tạo trade profile «{name}»")
              st.rerun()

  st.subheader("Bảng kết quả (xếp theo mục tiêu)")
  df = pd.DataFrame([r for r in rows if not r.get("error")])
  if df.empty:
    if running:
      st.caption("Chưa có combo hoàn thành.")
    else:
      st.warning("Không có kết quả hợp lệ.")
    return

  show_cols = [
    "label", "train_months", "use_kb", "kb_profile", "kb_snapshot",
    "n_trades", "win_rate_pct", "avg_rr", "total_r", "max_drawdown_r",
    "profit_factor", "risk_adjusted",
  ]
  show_cols = [c for c in show_cols if c in df.columns]
  st.dataframe(
    df[show_cols].head(50),
    use_container_width=True,
    hide_index=True,
    height=400,
  )

  err_rows = [r for r in rows if r.get("error")]
  if err_rows:
    with st.expander(f"Lỗi ({len(err_rows)})"):
      st.dataframe(pd.DataFrame(err_rows), hide_index=True)

  if running:
    return

  st.subheader("Biểu đồ")
  tab1, tab2, tab3 = st.tabs(["Train × KB", "Heatmap R", "Top 15"])

  with tab1:
    plot_df = df.copy()
    plot_df["kb_tag"] = plot_df.apply(
      lambda r: "KB OFF" if not r.get("use_kb") else f"{r.get('kb_profile')} {r.get('kb_snapshot') or 'latest'}",
      axis=1,
    )
    fig = px.bar(
      plot_df, x="train_months", y="total_r", color="kb_tag",
      barmode="group", title="Total R theo train window",
      labels={"train_months": "Train (tháng)", "total_r": "Total R"},
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

  with tab2:
    pivot_df = plot_df.groupby(["train_months", "kb_tag"], as_index=False)["total_r"].max()
    if len(pivot_df) > 1:
      piv = pivot_df.pivot(index="kb_tag", columns="train_months", values="total_r")
      fig_h = go.Figure(data=go.Heatmap(
        z=piv.values,
        x=[str(c) for c in piv.columns],
        y=list(piv.index),
        colorscale="RdYlGn",
        text=[[f"{v:+.1f}" for v in row] for row in piv.values],
        texttemplate="%{text}",
      ))
      fig_h.update_layout(title="Total R heatmap", height=max(300, len(piv) * 40))
      st.plotly_chart(fig_h, use_container_width=True)

  with tab3:
    top = df.head(15)
    fig2 = go.Figure(go.Bar(
      x=top["total_r"], y=top["label"], orientation="h",
      marker_color=["#2ecc71" if r > 0 else "#e74c3c" for r in top["total_r"]],
    ))
    fig2.update_layout(
      title="Top 15 theo mục tiêu", height=500,
      margin=dict(l=200, r=20, t=40, b=40),
      yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig2, use_container_width=True)
