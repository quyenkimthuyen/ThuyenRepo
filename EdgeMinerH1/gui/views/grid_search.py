"""Grid Search — tìm setting tối ưu theo Cài đặt."""
from __future__ import annotations

from datetime import timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from gui.app_settings import (
  get_settings,
  settings_changed_since_last_grid,
  settings_grid_signature,
)
from gui.grid_search_background import (
  get_grid_status, is_grid_running, load_job_state,
  start_grid_search, stop_grid_search,
)
from gui.grid_search_engine import (
  OBJECTIVES,
  build_grid_from_settings,
  estimate_grid_count,
  filter_specs_for_incremental,
  grid_readiness,
  load_latest_grid_run,
  merge_grid_results,
)
from gui.trade_model import create_trade_model
from gui.ui_preferences import (
  persist_widget,
  preference_callback,
  restore_widget,
  set_widget_preference,
)


def _grid_combo_changed(default_names: dict[str, str]) -> None:
  persist_widget("gs_pick_combo", "grid.selected_combo")
  selected = st.session_state.get("gs_pick_combo")
  set_widget_preference(
    "gs_any_tm_name",
    default_names.get(selected, "Grid model"),
    "grid.model_name",
  )


@st.fragment(run_every=timedelta(seconds=5))
def _grid_progress_fragment():
  status = get_grid_status()
  if status["running"]:
    st.progress(
      status["done"] / max(status["total"], 1),
      text=(
        f"⏳ Grid Search — {status['done']}/{status['total']} "
        f"({status['pct']}%) · {status['current_label'] or '…'}"
      ),
    )


def _render_job_status():
  status = get_grid_status()
  job = load_job_state() or {}
  latest = load_latest_grid_run() or {}

  # Job state cũ (0 combo) nhưng đã có lần chạy thành công sau đó → dùng latest.
  if (
    status.get("status") == "completed"
    and (status.get("n_rows") or 0) == 0
    and (status.get("total") or 0) == 0
    and (latest.get("rows") or [])
  ):
    n = len(latest.get("rows") or [])
    status = {
      **status,
      "run_id": latest.get("run_id"),
      "objective": latest.get("objective") or status.get("objective"),
      "n_rows": n,
      "total": n,
      "done": n,
      "finished_at": latest.get("updated_at"),
    }

  if status["status"] == "idle" and not job.get("run_id") and not latest.get("run_id"):
    return status

  if status["running"]:
    st.info("Grid Search đang chạy nền; có thể chuyển trang mà không làm dừng tác vụ.")
    _grid_progress_fragment()
    if st.button("⏹ Hủy grid search", key="gs_cancel"):
      stop_grid_search()
      st.toast("Đã gửi tín hiệu hủy")
      st.rerun()
  elif status["status"] == "completed":
    n = status.get("n_rows") or 0
    total = status.get("total") or 0
    if n == 0 and total == 0:
      if grid_readiness().get("kb_complete"):
        st.caption(
          f"_Lần chạy `{status.get('run_id')}` trước đó trống (chưa đủ KB). "
          "KB đã sẵn sàng — chạy Grid Search lại._"
        )
      else:
        st.error(
          f"⚠️ Grid `{status.get('run_id')}` kết thúc với **0 combo** — "
          "chưa huấn luyện bộ nhớ. Vào **Huấn luyện bộ nhớ** trước."
        )
    elif n == 0:
      st.warning(f"Hoàn thành `{status.get('run_id')}` — không có kết quả hợp lệ.")
  elif status["status"] == "cancelled":
    st.warning(f"Đã hủy — {status['done']}/{status['total']} combo.")
  elif status["status"] == "interrupted":
    st.warning(f"⚠️ Grid bị gián đoạn — {status['done']}/{status['total']}. Đang tự tiếp tục…")
    _grid_progress_fragment()
  elif status["status"] == "error":
    st.error(f"Lỗi grid search: {status.get('error') or 'unknown'}")

  return status


def _rows_for_display(status: dict) -> tuple[list, str]:
  job = load_job_state() or {}
  data = load_latest_grid_run()
  settings = get_settings()
  objective = settings.get("grid_objective", "total_r")

  if status.get("running") and job.get("rows"):
    rows = job["rows"]
  else:
    rows = (data or {}).get("rows") or job.get("rows") or []
    objective = (data or {}).get("objective") or job.get("objective") or objective

  seed = (job.get("config") or {}).get("seed_rows") or []
  if seed and rows:
    rows = merge_grid_results(seed, rows, objective=objective)

  return rows, objective


def render(embedded: bool = False):
  embedded = embedded or bool(st.session_state.get("_learning_hub"))
  if not embedded:
    st.header("Grid Search")

  if settings_changed_since_last_grid():
    st.warning("Cài đặt đã đổi — chạy grid để bổ sung combo mới (combo cũ được giữ lại).")

  readiness = grid_readiness()
  expected = readiness["expected_combos"]
  ready_n = readiness["ready_combos"]
  kb_done = readiness["kb_complete"]

  if not kb_done:
    if readiness["missing_profiles"]:
      st.error(
        f"**Chưa huấn luyện bộ nhớ** — Grid cần **{expected}** combo nhưng hiện **0** sẵn sàng."
      )
      for m in readiness["missing_profiles"]:
        st.markdown(
          f"- **{m['label']}** (`{m['id']}`) — cần **{m['epochs_needed']}** vòng học"
        )
    elif readiness["under_trained"]:
      st.warning(
        f"**Chưa đủ vòng học** — hiện **{ready_n}/{expected}** combo. "
        "Hoàn thành 4 vòng cho cả 3 giai đoạn trước khi chạy Grid Search."
      )
      for u in readiness["under_trained"]:
        st.markdown(
          f"- **{u['label']}**: {u['epochs_have']}/{u['epochs_needed']} vòng"
        )
    elif ready_n < expected:
      st.warning(f"Sẵn sàng **{ready_n}/{expected}** combo — kiểm tra KB và mốc OOS.")
    if st.button("→ Mở Huấn luyện bộ nhớ", key="gs_goto_train", type="primary"):
      st.session_state["learning_tab"] = "train_kb"
      st.rerun()
  job_status = _render_job_status()
  running = bool(job_status.get("running"))

  specs, grid_config = build_grid_from_settings()
  grid_kw = {
    k: v for k, v in grid_config.items()
    if k not in ("settings_signature", "learning_era_keys", "learning_loops", "source", "seed_rows")
  }
  full_n, run_n = estimate_grid_count(**grid_kw)

  latest = load_latest_grid_run()
  existing_rows = (latest or {}).get("rows") or []
  new_specs, kept_rows = filter_specs_for_incremental(specs, existing_rows)
  skip_n = len(specs) - len(new_specs)

  if not running:
    if new_specs:
      st.info(
        f"**{len(new_specs)} combo mới** cần chạy · hiện có **{skip_n}/{expected}** kết quả "
        f"· dự kiến {len(new_specs) * 2:.0f}–{len(new_specs) * 4:.0f} phút."
      )
    else:
      st.success(f"✅ Grid đã đủ **{skip_n}/{expected} combo** — không cần chạy lại.")

  run_btn = False
  if new_specs:
    c1, c2 = st.columns(2)
    with c1:
      run_btn = st.button(
        "▶ Chạy Grid Search (chỉ combo mới)",
        type="primary",
        key="gs_run",
        disabled=running or not kb_done,
      )
    with c2:
      force_btn = st.button(
        "↺ Chạy lại toàn bộ",
        key="gs_force",
        disabled=running or not kb_done,
      )
  else:
    force_btn = st.button(
      "↺ Chạy lại toàn bộ",
      key="gs_force",
      disabled=running or not kb_done,
      help="Chỉ dùng khi muốn tính lại toàn bộ kết quả.",
    )

  if run_btn:
    if is_grid_running():
      st.warning("Grid search đang chạy.")
      return
    objective = get_settings().get("grid_objective", "total_r")
    config = {**grid_config, "seed_rows": kept_rows}
    try:
      rid = start_grid_search(new_specs, objective=objective, config=config)
      st.session_state["settings_grid_signature"] = settings_grid_signature()
      st.toast(f"Grid `{rid}` — {len(new_specs)} combo mới")
      st.rerun()
    except RuntimeError as e:
      st.error(str(e))

  if force_btn:
    if is_grid_running():
      st.warning("Grid search đang chạy.")
      return
    objective = get_settings().get("grid_objective", "total_r")
    try:
      rid = start_grid_search(specs, objective=objective, config=grid_config)
      st.session_state["settings_grid_signature"] = settings_grid_signature()
      st.toast(f"Grid full `{rid}` — {len(specs)} combo")
      st.rerun()
    except RuntimeError as e:
      st.error(str(e))

  rows, objective = _rows_for_display(job_status)
  data = load_latest_grid_run()

  if not rows and not running:
    if ready_n == 0:
      st.info(
        "Bước tiếp: **Học & tối ưu → Huấn luyện bộ nhớ** — học 3 giai đoạn "
        f"({', '.join(m['label'] for m in readiness['missing_profiles']) or 'theo Cài đặt'}), "
        f"mỗi giai đoạn **{get_settings().get('learning_loops', 4)}** vòng. "
        "Sau đó quay lại Grid Search."
      )
    else:
      st.info("Nhấn **Chạy Grid Search** để bắt đầu.")
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
      f"**Tốt nhất:** {best.get('label')} · PF {best.get('profit_factor')} · {best.get('n_trades')} lệnh"
    )
    if not running:
      if st.button("✓ Tạo Trade Model từ combo tốt nhất (dùng ngay)", key="gs_apply_tm"):
        from gui.trade_model import find_model_by_grid_key
        existed = find_model_by_grid_key(best.get("key"))
        m = create_trade_model(best, run_id=(data or {}).get("run_id"), set_active=True)
        if existed and existed.get("id") == m.get("id"):
          st.toast("Combo này đã có Trade Model — đã chọn lại (không tạo trùng)")
        else:
          st.toast("Đã tạo & chọn trade model từ best combo")
        st.rerun()

  st.subheader("Bảng kết quả")
  valid_rows = [r for r in rows if not r.get("error")]
  df = pd.DataFrame(valid_rows)
  if df.empty:
    if running:
      st.caption("Chưa có combo hoàn thành.")
    else:
      st.warning("Không có kết quả hợp lệ.")
    return

  from gui.app_settings import kb_profile_label

  show_cols = [
    "label", "train_months", "use_kb", "giai_doan", "kb_snapshot",
    "n_trades", "win_rate_pct", "avg_rr", "total_r", "max_drawdown_r",
    "profit_factor", "risk_adjusted",
  ]
  display_df = df.copy()
  if "kb_profile" in display_df.columns:
    display_df["giai_doan"] = display_df["kb_profile"].map(kb_profile_label)
  show_cols = [c for c in show_cols if c in display_df.columns]
  st.dataframe(display_df[show_cols].head(50), use_container_width=True, hide_index=True, height=400)

  if not running and valid_rows:
    st.subheader("Tạo Trade Model từ combo bất kỳ")
    st.caption("Chọn bất kỳ dòng trong bảng (không chỉ best) → đặt tên → tạo model.")
    options = []
    for i, r in enumerate(valid_rows[:50]):
      options.append(
        f"#{i+1} · {r.get('label')} · R={r.get('total_r', 0):+.2f} · "
        f"WR={r.get('win_rate_pct', 0)}% · train={r.get('train_months')}m"
      )
    default_names = {
      option: str((valid_rows[i].get("label") or f"Grid #{i + 1}"))[:80]
      for i, option in enumerate(options)
    }
    restore_widget(
      "gs_pick_combo", options[0],
      preference_key="grid.selected_combo",
      options=options,
    )
    pick = st.selectbox(
      "Combo", options, key="gs_pick_combo",
      on_change=_grid_combo_changed,
      args=(default_names,),
    )
    pick_idx = options.index(pick) if pick in options else 0
    chosen = valid_rows[pick_idx]
    default_name = chosen.get("label") or f"Grid #{pick_idx+1}"
    restore_widget(
      "gs_any_tm_name", str(default_name)[:80],
      preference_key="grid.model_name",
    )
    name = st.text_input(
      "Tên Trade Model", key="gs_any_tm_name",
      on_change=preference_callback("gs_any_tm_name", "grid.model_name"),
    )
    restore_widget("gs_any_tm_active", True, preference_key="grid.set_active")
    set_active = st.checkbox(
      "Đặt làm model đang dùng", key="gs_any_tm_active",
      on_change=preference_callback("gs_any_tm_active", "grid.set_active"),
    )
    if st.button("＋ Tạo Trade Model từ combo đã chọn", type="primary", key="gs_create_any_tm"):
      from gui.trade_model import find_model_by_grid_key
      label = (name or "").strip() or None
      existed = find_model_by_grid_key(chosen.get("key"))
      m = create_trade_model(
        chosen,
        run_id=(data or {}).get("run_id"),
        label=label,
        set_active=set_active,
      )
      if existed and existed.get("id") == m.get("id"):
        st.toast(f"Combo đã có model «{m.get('label')}» — không tạo trùng")
      else:
        st.toast(f"Đã tạo «{m.get('label')}»")
      st.rerun()

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
      lambda r: "KB OFF" if not r.get("use_kb") else (
        f"{kb_profile_label(r.get('kb_profile'))} · vòng {r.get('kb_snapshot') or 'mới nhất'}"
      ),
      axis=1,
    )
    fig = px.bar(
      plot_df, x="train_months", y="total_r", color="kb_tag",
      barmode="group", title="Total R theo train window",
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
      title="Top 15", height=500,
      margin=dict(l=200, r=20, t=40, b=40),
      yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig2, use_container_width=True)
