"""Học & tối ưu → Final Train — xếp hạng combo Grid qua nhiều lần chạy."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from gui.charts import show_plotly
from gui.final_train import (
  DEFAULT_MAX_DD_R,
  build_final_train_scatter,
  collect_grid_combo_rows,
  list_oos_windows,
  rank_final_train_combos,
  weights_caption,
)
from gui.trade_model import (
  create_trade_model,
  desk_pair_code,
  find_model_by_grid_key,
)
from gui.ui_preferences import preference_callback, restore_widget, set_widget_preference

_SORT_OPTIONS = {
  "composite": "Composite (đề xuất)",
  "wr": "WR % ↓",
  "total_r": "Total R ↓",
  "dd": "Max DD ↑",
  "pf": "PF ↓",
  "risk_adj": "Risk-adj ↓",
}

_STRIP_DISPLAY = {
  "#", "Score", "WR %", "Total R", "Max DD", "PF",
  "Train", "KB", "Preset", "OOS", "Run", "TM", "Combo", "Badge",
}


def _grid_key_of(row: dict | None) -> str | None:
  if not row:
    return None
  key = row.get("_grid_key") or row.get("key")
  return str(key) if key else None


def _idx_by_grid_key(rows: list[dict], grid_key: str | None) -> int | None:
  if not grid_key:
    return None
  want = str(grid_key)
  for i, r in enumerate(rows):
    if _grid_key_of(r) == want:
      return i
  return None


def _table_selected_row_idx(widget_key: str = "ft_top_table") -> int | None:
  state = st.session_state.get(widget_key)
  if state is None:
    return None
  rows = None
  try:
    rows = state.selection.rows  # type: ignore[attr-defined]
  except Exception:
    try:
      rows = (state.get("selection") or {}).get("rows")  # type: ignore[union-attr]
    except Exception:
      rows = None
  if not rows:
    return None
  try:
    return int(rows[0])
  except (TypeError, ValueError, IndexError):
    return None


def _resolve_pick_key(
  *,
  chart_key: str | None,
  chart_sig: str | None,
  table_key: str | None,
) -> tuple[str | None, str | None]:
  """Prefer the widget that changed since last run.

  Returns ``(pick_key, source)`` where source is ``\"chart\"``, ``\"table\"``, or None.
  Never assigns Streamlit widget keys (forbidden with ``on_select``).
  Remounts the opposite widget via a revision counter instead.
  """
  last_chart_sig = st.session_state.get("_ft_last_chart_sig")
  last_table = st.session_state.get("_ft_last_table_key")
  prev_pick = st.session_state.get("ft_pick_key")

  pick = prev_pick
  source: str | None = None
  if chart_key and chart_sig and chart_sig != last_chart_sig:
    pick = chart_key
    source = "chart"
  elif table_key and table_key != last_table:
    pick = table_key
    source = "table"
  elif chart_key and not pick:
    pick = chart_key
  elif table_key and not pick:
    pick = table_key

  if source == "chart":
    st.session_state["_ft_last_chart_sig"] = chart_sig
    # Remount table so native row-selection cannot fight the chart pick.
    st.session_state["_ft_table_rev"] = int(st.session_state.get("_ft_table_rev") or 0) + 1
    st.session_state["_ft_last_table_key"] = None
  elif source == "table":
    st.session_state["_ft_last_table_key"] = table_key
    # Remount chart so stale plotly point-selection cannot fight the table.
    st.session_state["_ft_scatter_rev"] = int(st.session_state.get("_ft_scatter_rev") or 0) + 1
    st.session_state["_ft_last_chart_sig"] = None

  st.session_state["ft_pick_key"] = pick
  return pick, source


def _plotly_selection_sig(widget_key: str) -> tuple[str | None, str | None]:
  """Return ``(grid_key, signature)`` for the current plotly point selection."""
  state = st.session_state.get(widget_key)
  if state is None:
    return None, None
  points = None
  try:
    points = state.selection.points  # type: ignore[attr-defined]
  except Exception:
    try:
      points = (state.get("selection") or {}).get("points")  # type: ignore[union-attr]
    except Exception:
      points = None
  if not points:
    return None, None
  pt = points[0]
  try:
    cd = pt.get("customdata") if isinstance(pt, dict) else getattr(pt, "customdata", None)
  except Exception:
    cd = None
  key = None
  if isinstance(cd, (list, tuple)) and cd:
    key = str(cd[0]) if cd[0] not in (None, "") else None
  elif isinstance(cd, str) and cd:
    key = cd
  try:
    curve = pt.get("curve_number") if isinstance(pt, dict) else getattr(pt, "curve_number", None)
    pnum = pt.get("point_number") if isinstance(pt, dict) else getattr(pt, "point_number", None)
    x = pt.get("x") if isinstance(pt, dict) else getattr(pt, "x", None)
    y = pt.get("y") if isinstance(pt, dict) else getattr(pt, "y", None)
    sig = f"{curve}:{pnum}:{x}:{y}:{key}"
  except Exception:
    sig = str(key)
  return key, sig


def render(embedded: bool = False):
  if not embedded:
    st.subheader("Final Train")

  st.caption(
    "Gộp kết quả **mọi lần Grid Search** → xếp hạng combo (theo `key`) → "
    "chọn ứng viên rồi **Tạo Trade Model**. "
    "Click điểm trên chart ⇄ chọn dòng trong bảng."
  )

  desk = desk_pair_code()
  sort_keys = list(_SORT_OPTIONS.keys())

  restore_widget(
    "ft_hide_promoted", False, preference_key="final_train.hide_promoted",
  )
  restore_widget(
    "ft_max_dd_r", float(DEFAULT_MAX_DD_R),
    preference_key="final_train.max_dd_r",
    decode=float,
  )
  restore_widget(
    "ft_top_n", 15, preference_key="final_train.top_n", decode=int,
  )
  restore_widget(
    "ft_sort_mode", "composite",
    preference_key="final_train.sort_mode",
    options=sort_keys,
  )
  restore_widget(
    "ft_tm_active", False, preference_key="final_train.set_active",
  )

  c1, c2, c3, c4 = st.columns([1.2, 1.1, 1, 1.4])
  with c1:
    hide_promoted = st.toggle(
      "Ẩn đã có Trade Model",
      key="ft_hide_promoted",
      help="Chỉ hiện combo chưa promote.",
      on_change=preference_callback("ft_hide_promoted", "final_train.hide_promoted"),
    )
  with c2:
    max_dd_r = float(st.number_input(
      "Ngưỡng Max DD (R)",
      min_value=1.0,
      max_value=200.0,
      step=0.5,
      key="ft_max_dd_r",
      help=(
        f"Ẩn combo có Max DD lớn hơn ngưỡng này. Mặc định {DEFAULT_MAX_DD_R:g}R. "
        "Tăng ngưỡng để xem thêm ứng viên Grid."
      ),
      on_change=preference_callback("ft_max_dd_r", "final_train.max_dd_r"),
    ))
  with c3:
    top_n = int(st.number_input(
      "Top N",
      min_value=3,
      max_value=50,
      step=1,
      key="ft_top_n",
      on_change=preference_callback("ft_top_n", "final_train.top_n"),
    ))
  with c4:
    sort_mode = st.selectbox(
      "Xếp hạng",
      options=sort_keys,
      format_func=lambda k: _SORT_OPTIONS[k],
      key="ft_sort_mode",
      on_change=preference_callback("ft_sort_mode", "final_train.sort_mode"),
    )

  st.markdown(weights_caption(desk, max_dd_r=max_dd_r))

  with st.spinner("Đang gộp các lần Grid Search…"):
    raw_rows = collect_grid_combo_rows(max_dd_r=max_dd_r)

  oos_all = "(Tất cả OOS)"
  oos_opts = [oos_all] + list_oos_windows(raw_rows)
  restore_widget(
    "ft_oos_window",
    oos_opts[1] if len(oos_opts) > 1 else oos_all,
    preference_key="final_train.oos_window",
    options=oos_opts,
  )
  oos_window = st.selectbox(
    "Lọc theo OOS",
    options=oos_opts,
    key="ft_oos_window",
    help="Chỉ hiện combo Grid đúng cửa sổ OOS đã chọn. Chọn «Tất cả OOS» để gộp mọi cửa sổ.",
    on_change=preference_callback("ft_oos_window", "final_train.oos_window"),
  )
  oos_filter = None if oos_window == oos_all else oos_window

  ranked = rank_final_train_combos(
    raw_rows,
    desk=desk,
    mode=sort_mode,  # type: ignore[arg-type]
    hide_promoted=hide_promoted,
    max_dd_r=max_dd_r,
    oos_window=oos_filter,
  )

  if not ranked:
    st.info(
      "Chưa có combo Grid hợp lệ. Chạy **Grid Search** trước, "
      "hoặc đổi **Lọc theo OOS** / tăng **Ngưỡng Max DD** / tắt **Ẩn đã có Trade Model**."
    )
    return

  n_promoted = sum(1 for r in ranked if r.get("_has_model"))
  oos_note = oos_window if oos_filter else "mọi OOS"
  st.caption(
    f"{len(ranked)} combo sau filter ({oos_note} · Max DD ≤ {max_dd_r:g}R) · "
    f"{n_promoted} đã có Trade Model · "
    f"cột Run = lần Grid có kết quả tốt nhất cho `key` đó."
  )
  if len(ranked) < top_n:
    why = []
    why.append(f"ngưỡng **Max DD ≤ {max_dd_r:g}R** — tăng ngưỡng để xem thêm")
    if oos_filter:
      why.append(f"đang lọc OOS **{oos_filter}**")
    if hide_promoted:
      why.append("đang **Ẩn đã có Trade Model**")
    st.warning(
      f"Top N = {top_n} nhưng chỉ còn **{len(ranked)}** combo vì "
      + " · ".join(why)
      + "."
    )

  top = ranked[:top_n]

  scatter_rev = int(st.session_state.get("_ft_scatter_rev") or 0)
  table_rev = int(st.session_state.get("_ft_table_rev") or 0)
  scatter_key = f"ft_scatter_{scatter_rev}"
  table_key_widget = f"ft_top_table_{table_rev}"

  chart_key, chart_sig = _plotly_selection_sig(scatter_key)
  table_idx_raw = _table_selected_row_idx(table_key_widget)
  if table_idx_raw is not None and not (0 <= table_idx_raw < len(top)):
    table_idx_raw = None
  table_key = _grid_key_of(top[table_idx_raw]) if table_idx_raw is not None else None

  pick_key, _source = _resolve_pick_key(
    chart_key=chart_key, chart_sig=chart_sig, table_key=table_key,
  )
  # Revisions may bump during resolve — use fresh keys for widgets this run.
  scatter_rev = int(st.session_state.get("_ft_scatter_rev") or 0)
  table_rev = int(st.session_state.get("_ft_table_rev") or 0)
  scatter_key = f"ft_scatter_{scatter_rev}"
  table_key_widget = f"ft_top_table_{table_rev}"
  selected_idx = _idx_by_grid_key(top, pick_key)

  title = f"Final Train · {desk} · Grid combos · WR vs Total R"
  fig = build_final_train_scatter(
    ranked, top_n=top_n, highlight_key=pick_key, title=title,
  )
  if fig is not None:
    show_plotly(
      fig,
      title,
      key=scatter_key,
      on_select="rerun",
      selection_mode="points",
    )
    if pick_key:
      picked_preview = next(
        (r for r in ranked if _grid_key_of(r) == pick_key), None,
      )
      if picked_preview is not None:
        in_top = selected_idx is not None
        st.caption(
          f"● Đang chọn: **{picked_preview.get('Combo')}** · "
          f"WR {picked_preview.get('WR %')}% · R {picked_preview.get('Total R')}"
          + ("" if in_top else " · (ngoài Top N — tăng Top N để thấy trong bảng)")
        )
  else:
    st.info("Chưa đủ WR + Total R để vẽ scatter.")

  st.markdown(
    f"**Top {len(top)}** · click chart hoặc chọn dòng → Tạo Trade Model"
  )

  display_cols = [
    "▶", "#", "Score", "Badge", "Combo", "WR %", "Total R", "Max DD", "PF",
    "Train", "KB", "Preset", "TM", "Run", "OOS",
  ]
  show_df = pd.DataFrame(top)
  show_df["▶"] = [
    "●" if _grid_key_of(r) == pick_key else ""
    for r in top
  ]
  for col in display_cols:
    if col not in show_df.columns:
      show_df[col] = None
  show_df = show_df[display_cols]

  event = st.dataframe(
    show_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key=table_key_widget,
    column_config={
      "▶": st.column_config.TextColumn(" ", width="small"),
      "#": st.column_config.NumberColumn("#", format="%d", width="small"),
      "Score": st.column_config.NumberColumn("Score", format="%.3f"),
      "Total R": st.column_config.NumberColumn("Total R", format="%+.2f"),
      "WR %": st.column_config.NumberColumn("WR %", format="%.1f"),
      "Max DD": st.column_config.NumberColumn("Max DD", format="%.2f"),
      "PF": st.column_config.NumberColumn("PF", format="%.2f"),
      "Combo": st.column_config.TextColumn("Combo", width="large"),
      "Preset": st.column_config.TextColumn("Preset", width="medium"),
      "TM": st.column_config.TextColumn("TM", width="small"),
    },
  )

  # Fresh table event can override pick within this run (after chart already drawn).
  try:
    sel_rows = (event.selection.rows if event and event.selection else None) or []
    if sel_rows:
      fresh_idx = int(sel_rows[0])
      if 0 <= fresh_idx < len(top):
        fresh_key = _grid_key_of(top[fresh_idx])
        if fresh_key and fresh_key != pick_key:
          last_table = st.session_state.get("_ft_last_table_key")
          if fresh_key != last_table:
            st.session_state["ft_pick_key"] = fresh_key
            st.session_state["_ft_last_table_key"] = fresh_key
            st.session_state["_ft_scatter_rev"] = (
              int(st.session_state.get("_ft_scatter_rev") or 0) + 1
            )
            st.session_state["_ft_last_chart_sig"] = None
            st.rerun()
  except Exception:
    pass

  picked = None
  if pick_key:
    picked = next((r for r in ranked if _grid_key_of(r) == pick_key), None)
  if picked is None and selected_idx is not None:
    picked = top[selected_idx]

  if picked is None:
    st.caption("Tip: click một điểm trên chart hoặc chọn 1 dòng trong bảng.")
    return

  grid_key = _grid_key_of(picked)
  default_name = str(picked.get("label") or picked.get("Combo") or "Grid combo")[:80]

  st.markdown(f"**Đang chọn:** {picked.get('Combo')}")
  st.caption(
    f"#{picked.get('#')} · Score `{picked.get('Score')}` · "
    f"`{picked.get('Badge')}` · R={picked.get('Total R')} · "
    f"WR={picked.get('WR %')}% · DD={picked.get('Max DD')} · "
    f"run `{picked.get('_run_id')}` · key `{str(grid_key)[:48]}`"
  )
  if selected_idx is None and pick_key:
    st.warning("Combo đang chọn nằm ngoài Top N — tăng Top N để thấy dòng trong bảng.")
  if picked.get("_has_model"):
    st.info(
      f"Combo này đã có Trade Model «{picked.get('_model_label')}». "
      "Tạo lại sẽ tái sử dụng model (không nhân đôi), có thể đổi tên / Active."
    )

  name = st.text_input(
    "Tên Trade Model",
    value=default_name,
    key="ft_tm_name",
  )
  set_active = st.checkbox(
    "Đặt làm Active sau khi tạo",
    key="ft_tm_active",
    help="Mặc định tắt — đánh giá nhiều combo trước khi chọn Active.",
    on_change=preference_callback("ft_tm_active", "final_train.set_active"),
  )

  a1, a2, a3 = st.columns([1.3, 1, 1.5])
  with a1:
    if st.button(
      "Tạo Trade Model",
      type="primary",
      icon=":material/add_box:",
      use_container_width=True,
      key="ft_create_tm",
    ):
      row = {
        k: v for k, v in picked.items()
        if not str(k).startswith("_") and k not in _STRIP_DISPLAY
      }
      for src, dst in [
        ("_wr", "win_rate_pct"),
        ("_total_r", "total_r"),
        ("_dd", "max_drawdown_r"),
        ("_pf", "profit_factor"),
        ("_grid_key", "key"),
      ]:
        if picked.get(src) is not None and dst not in row:
          row[dst] = picked[src]
      if "key" not in row and grid_key:
        row["key"] = grid_key
      label = (name or "").strip() or None
      existed = find_model_by_grid_key(row.get("key"))
      try:
        run_id = picked.get("_run_id")
        if run_id in (None, "—"):
          run_id = None
        m = create_trade_model(
          row,
          run_id=run_id,
          label=label,
          set_active=set_active,
        )
      except Exception as exc:
        st.error(str(exc))
      else:
        if existed and existed.get("id") == m.get("id"):
          st.toast(f"Combo đã có «{m.get('label')}» — không tạo trùng")
        else:
          st.toast(f"Đã tạo «{m.get('label')}»")
        st.rerun()
  with a2:
    if st.button(
      "Mở Trade Models",
      icon=":material/inventory_2:",
      use_container_width=True,
      key="ft_open_models",
    ):
      set_widget_preference("nav_page", "models", "navigation.page")
      st.rerun()
  with a3:
    if picked.get("_has_model"):
      st.caption(f"TM hiện có: `{picked.get('_model_id')}`")
