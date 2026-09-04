"""Trade Models — dropdown model chung + Thông tin / Đánh giá OOS / Rủi ro / Nhật ký / Chiến lược."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from gui.export_live_package import default_export_dir, export_model_tmpkg, export_readiness
from gui.trade_model import (
  OVERVIEW_HIGH_DD_R,
  bridge_ghost_model_ids,
  build_trade_models_compare_rows,
  delete_trade_model,
  desk_pair_code,
  format_model_label,
  get_active_trade_model,
  get_bridge_runtime_model_ids,
  get_model_by_id,
  list_trade_models,
  load_model_kb_off_report,
  load_model_report,
  overview_row_visible,
  prune_bridge_roster,
  rename_trade_model,
  reset_trade_model_label,
  set_active_trade_model,
)
from gui.charts import show_plotly
from gui.ui_theme import icon_btn
from gui.ui_preferences import preference_callback, restore_widget, set_widget_preference
from gui.navigation import LABEL_TAB_OOS
from gui.views import risk_dashboard, trade_journal, strategy_inspector

# Sub-views driven by the shared model dropdown above.
SUB_KEYS = ["overview", "info", "health", "risk", "journal", "strategy"]
SUB_LABELS = {
  "overview": "Tổng hợp",
  "info": "Thông tin",
  "health": LABEL_TAB_OOS,
  "risk": "Rủi ro",
  "journal": "Nhật ký",
  "strategy": "Chiến lược",
}
SUB_ICONS = {
  "overview": ":material/table_chart:",
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
  # Old "manage" bookmark → overview compare table
  if st.session_state.get("models_subtab") == "manage":
    set_widget_preference("models_subtab", "overview", "navigation.models_subtab")
  return restore_widget(
    "models_subtab", "overview",
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


def _apply_pending_model_pick(updated: dict | None):
  """Sync dropdown + preference after rename/delete/set-active."""
  if not updated:
    return
  from gui.ui_preferences import set_preference
  new_lab = format_model_label(updated)
  st.session_state["_tm_pending_pick"] = new_lab
  set_preference("trade_models.selected", new_lab)


def _render_shared_model_bar(models: list[dict]) -> dict | None:
  """Top dropdown — selection becomes active Trade Model for detail tabs.

  Đổi tên / Export .tmpkg nằm ở tab **Tổng hợp** (chọn dòng trong bảng).
  """
  if not models:
    return None
  id_by_label = {format_model_label(m): m["id"] for m in models}
  labels = list(id_by_label.keys())
  active = get_active_trade_model()
  default_pick = format_model_label(active) if active else labels[0]
  if default_pick not in labels:
    default_pick = labels[0]

  # Apply rename/reset pick before the selectbox is instantiated.
  pending = st.session_state.pop("_tm_pending_pick", None)
  if pending and pending in labels:
    st.session_state["tm_shared_pick"] = pending
    default_pick = pending

  restore_widget(
    "tm_shared_pick", default_pick,
    preference_key="trade_models.selected",
    options=labels,
  )
  if st.session_state.get("tm_shared_pick") not in labels:
    st.session_state["tm_shared_pick"] = default_pick

  c1, c2 = st.columns([4, 1])
  with c1:
    pick = st.selectbox(
      "Trade Model đang xem",
      labels,
      key="tm_shared_pick",
      on_change=_on_shared_model_change,
      help=(
        f"Model Active cho tab Thông tin / {LABEL_TAB_OOS} / Rủi ro / Nhật ký / Chiến lược. "
        "Đổi tên / Archive / Export .tmpkg: tab **Tổng hợp** → chọn dòng."
      ),
    )
  mid = id_by_label[pick]
  m = next(x for x in models if x["id"] == mid)
  active = get_active_trade_model()
  if not active or active.get("id") != mid:
    set_active_trade_model(mid)
    active = get_active_trade_model()

  report = load_model_report(mid)
  with c2:
    if report:
      o = report.get("overall_oos") or {}
      st.metric("Backtest R", f"{o.get('total_r', m.get('total_r', 0)):+.2f}")
    elif m.get("total_r") is not None:
      st.metric("Grid R", f"{float(m.get('total_r')):+.2f}")
    else:
      st.caption("Chưa có report")

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
    f"KB pin `{'yes · ' + str(m.get('kb_fingerprint') or '')[:8] if m.get('kb_pin_path') else 'no'}` "
    f"· Đổi tên/Archive/Export ở tab **Tổng hợp**"
  )
  if report:
    mismatches = profile_mismatch_details(report, {**m, "trade_model_id": mid})
    if mismatches:
      grid_r = m.get("total_r")
      extra = f" Grid KPI: **{float(grid_r):+.2f}R**." if grid_r is not None else ""
      st.warning(
        "Báo cáo Backtest **không khớp** model đang chọn — "
        + " · ".join(mismatches)
        + f".{extra} Chạy lại báo cáo / {LABEL_TAB_OOS} (bật **Chạy lại KB ON**)."
      )

  return active


def _render_models_overview(models: list[dict], active: dict | None):
  """Compare table — badges, default filter, desk sort, rename/delete."""
  desk = desk_pair_code()
  sort_hint = (
    "sort mặc định **WR ↓ → DD ↑ → R ↓** (desk GBP)"
    if desk == "GBP"
    else "sort mặc định **Total R ↓** (desk EUR)"
  )
  st.caption(
    f"So sánh Trade Model · desk **{desk}** · {sort_hint}. "
    "Click 1 dòng → **Đổi tên** / **Xóa** / **Export .tmpkg**. Active chọn ở dropdown phía trên."
  )

  ghosts = bridge_ghost_model_ids()
  if ghosts:
    g1, g2 = st.columns([4, 1])
    with g1:
      st.warning(
        "Bridge đang giữ **id ma** (đã xóa khỏi store): "
        + ", ".join(f"`{g}`" for g in ghosts[:8])
        + (" …" if len(ghosts) > 8 else "")
        + ". Dọn roster để Live/Sim không tham chiếu model chết."
      )
    with g2:
      if st.button(
        "Dọn Bridge",
        key="tm_ov_prune_ghosts",
        use_container_width=True,
        help="Gỡ mọi id không còn trong store live khỏi Bridge model_ids.",
      ):
        result = prune_bridge_roster(drop_unknown=True)
        removed = result.get("removed") or []
        if result.get("error"):
          st.error(result["error"])
        elif removed:
          st.toast(f"Đã gỡ {len(removed)} id khỏi Bridge")
          st.rerun()
        else:
          st.info("Không còn id ma.")

  store_models = list_trade_models()
  active_id = str(active["id"]) if active and active.get("id") else None
  bridge_ids = get_bridge_runtime_model_ids()
  all_rows = build_trade_models_compare_rows(
    store_models,
    active_id=active_id,
    bridge_ids=bridge_ids,
    sort_desk=desk,
  )
  if not all_rows:
    st.info("Chưa có Trade Model trong store.")
    return

  restore_widget("tm_ov_show_all", False, preference_key="trade_models.overview_show_all")
  show_all = st.toggle(
    "Hiện tất cả",
    key="tm_ov_show_all",
    help=(
      "Mặc định chỉ Active + Bridge (model đang chọn trên roster). "
      "Bật để xem toàn bộ store."
    ),
    on_change=preference_callback("tm_ov_show_all", "trade_models.overview_show_all"),
  )

  rows = [
    r for r in all_rows
    if overview_row_visible(
      r,
      show_all=show_all,
      bridge_ids=bridge_ids,
    )
  ]
  hidden_n = len(all_rows) - len(rows)
  if hidden_n > 0 and not show_all:
    st.caption(
      f"Đang ẩn **{hidden_n}** model catalog. "
      "Bảng mặc định chỉ **Active + Bridge**. Bật **Hiện tất cả** để xem phần còn lại."
    )

  if not rows:
    st.warning("Không còn model sau filter — bật **Hiện tất cả**.")
    return

  display_cols = [
    "Badge", "Vai trò", "Model", "Total R", "WR %", "Max DD", "PF",
    "Lệnh", "Tpw", "Train", "KB ep", "OOS", "Mining", "Nguồn",
  ]
  show = pd.DataFrame(rows)[display_cols].copy()

  n_live = sum(1 for r in all_rows if "Live-ok" in (r.get("Badge") or ""))
  n_hdd = sum(1 for r in all_rows if "High-DD" in (r.get("Badge") or ""))
  c1, c2, c3, c4, c5 = st.columns(5)
  with c1:
    st.metric("Hiện / Tổng", f"{len(rows)}/{len(all_rows)}")
  with c2:
    best_r = next((r for r in rows if r.get("Total R") is not None), None)
    st.metric(
      "Cao nhất Total R",
      f"{best_r['Total R']:+.1f}" if best_r else "—",
      help=best_r["Model"] if best_r else None,
    )
  with c3:
    wr_ok = [r for r in rows if r.get("WR %") is not None]
    best_wr = max(wr_ok, key=lambda r: r["WR %"]) if wr_ok else None
    st.metric(
      "Cao nhất WR",
      f"{best_wr['WR %']:.1f}%" if best_wr else "—",
      help=best_wr["Model"] if best_wr else None,
    )
  with c4:
    dd_ok = [r for r in rows if r.get("Max DD") is not None]
    best_dd = min(dd_ok, key=lambda r: r["Max DD"]) if dd_ok else None
    st.metric(
      "Thấp nhất DD",
      f"{best_dd['Max DD']:.2f}R" if best_dd else "—",
      help=best_dd["Model"] if best_dd else None,
    )
  with c5:
    st.metric("Live-ok / High-DD", f"{n_live} / {n_hdd}")

  event = st.dataframe(
    show,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key="tm_overview_table",
    column_config={
      "Badge": st.column_config.TextColumn(
        "Badge",
        width="medium",
        help=(
          "Live-ok = có OOS + DD≤"
          f"{OVERVIEW_HIGH_DD_R:g}R · High-DD = DD>"
          f"{OVERVIEW_HIGH_DD_R:g}R · Grid-only = chưa remine report · Stale = thiếu KPI"
        ),
      ),
      "Vai trò": st.column_config.TextColumn("Vai trò", width="small"),
      "Model": st.column_config.TextColumn("Model", width="medium"),
      "Total R": st.column_config.NumberColumn("Total R", format="%+.2f"),
      "WR %": st.column_config.NumberColumn("WR %", format="%.1f"),
      "Max DD": st.column_config.NumberColumn("Max DD", format="%.2f"),
      "PF": st.column_config.NumberColumn("PF", format="%.2f"),
      "Lệnh": st.column_config.NumberColumn("Lệnh", format="%d"),
      "Tpw": st.column_config.NumberColumn("Tpw", format="%.2f"),
      "Train": st.column_config.NumberColumn("Train", format="%d"),
      "Mining": st.column_config.TextColumn("Mining", width="large"),
      "Nguồn": st.column_config.TextColumn(
        "Nguồn",
        width="small",
        help=(
          "● OOS = KPI từ report remine/backtest của model (tin hơn). "
          "○ Grid = KPI lúc tạo từ Grid Search (chưa có report OOS)."
        ),
      ),
    },
  )

  selected_idx = None
  try:
    sel_rows = (event.selection.rows if event and event.selection else None) or []
    if sel_rows:
      selected_idx = int(sel_rows[0])
  except Exception:
    selected_idx = None

  notes = (
    f"- **Badge**: Live-ok / High-DD (>{OVERVIEW_HIGH_DD_R:g}R) / Grid-only / Stale.\n"
    "- **Nguồn**: `● OOS` đậm nghĩa tin hơn; `○ Grid` = KPI tạo model, nên remine trước Live.\n"
    f"- **Sort**: {sort_hint} — click header cột để sort lại.\n"
    "- Model trên **Bridge** luôn hiện dù filter mặc định đang ẩn.\n"
    "- **Xóa** = xóa vĩnh viễn model + report/schedule gắn với id.\n"
    "- **Export .tmpkg** = gói model + schedule OOS + KB pin cho Trade "
    "(`packages_inbox` → Import ở **Models**, không phải tab Live).\n"
    "- Active chỉ để phân tích (dropdown phía trên)."
  )

  if selected_idx is None or not (0 <= selected_idx < len(rows)):
    st.caption("Tip: click 1 dòng → Đổi tên / Xóa / Export .tmpkg. Active chọn ở dropdown phía trên.")
    with st.expander("Ghi chú đọc bảng", expanded=False):
      st.markdown(notes)
    return

  picked = rows[selected_idx]
  mid = picked["id"]
  lab = picked.get("_label") or picked.get("Model")
  model = get_model_by_id(mid) or {}
  is_custom = bool(model.get("label_custom"))
  on_bridge = mid in {str(x) for x in (bridge_ids or []) if x}

  st.markdown(f"**Đang chọn trong bảng:** {lab}")
  st.caption(
    f"Badge `{picked.get('Badge')}` · {picked.get('Nguồn')} · "
    f"R={picked.get('Total R')} · WR={picked.get('WR %')}% · "
    f"DD={picked.get('Max DD')} · id `{mid}`"
    + (" · đang trên Bridge" if on_bridge else "")
  )

  rename_key = f"tm_ov_rename_{mid}"
  if st.session_state.get("_tm_ov_rename_mid") != mid:
    st.session_state[rename_key] = format_model_label(model) if model else lab
    st.session_state["_tm_ov_rename_mid"] = mid
  elif rename_key not in st.session_state:
    st.session_state[rename_key] = format_model_label(model) if model else lab

  r1, r2, r3 = st.columns([3, 1, 1])
  with r1:
    st.text_input(
      "Tên hiển thị",
      key=rename_key,
      placeholder="VD: BestR live · WR60 desk",
      help="Chỉ đổi tên hiển thị; `id` giữ nguyên cho Bridge/journal.",
    )
  with r2:
    if st.button(
      "Lưu tên",
      type="primary",
      key="tm_ov_rename_save",
      use_container_width=True,
    ):
      try:
        updated = rename_trade_model(mid, st.session_state.get(rename_key) or "")
      except ValueError as exc:
        st.error(str(exc))
      else:
        if updated:
          _apply_pending_model_pick(updated)
          st.toast(f"Đã đổi tên → {format_model_label(updated)}")
          st.rerun()
  with r3:
    if st.button(
      "Tên auto",
      key="tm_ov_rename_reset",
      use_container_width=True,
      disabled=not is_custom,
      help="Bỏ tên tùy chỉnh, dùng lại label train/KB/OOS.",
    ):
      updated = reset_trade_model_label(mid)
      if updated:
        _apply_pending_model_pick(updated)
        st.session_state.pop("_tm_ov_rename_mid", None)
        st.toast("Đã khôi phục tên tự động")
        st.rerun()

  ready = export_readiness(model) if model else {"ok": False, "weeks": 0, "error": "không thấy model"}
  confirm_key = "tm_ov_delete_confirm"
  a1, a2, a3 = st.columns([1, 1, 2])
  with a1:
    if st.session_state.get(confirm_key) == mid:
      if st.button(
        "Xác nhận xóa",
        type="primary",
        use_container_width=True,
        key="tm_ov_delete_yes",
        help="Xóa vĩnh viễn model + report/schedule gắn với id này.",
      ):
        if delete_trade_model(mid):
          st.session_state.pop(confirm_key, None)
          st.session_state.pop("_tm_ov_rename_mid", None)
          remaining = list_trade_models()
          if remaining:
            _apply_pending_model_pick(remaining[0])
          else:
            st.session_state.pop("_tm_pending_pick", None)
          st.toast("Đã xóa trade model")
          st.rerun()
      if st.button("Hủy", use_container_width=True, key="tm_ov_delete_cancel"):
        st.session_state.pop(confirm_key, None)
        st.rerun()
    else:
      if st.button(
        "Xóa",
        icon=":material/delete_forever:",
        use_container_width=True,
        key="tm_ov_delete",
        help="Xóa vĩnh viễn model + report/schedule. Cần xác nhận.",
      ):
        st.session_state[confirm_key] = mid
        st.rerun()
  with a2:
    if st.button(
      "Export .tmpkg",
      icon=":material/download:",
      use_container_width=True,
      key="tm_ov_export",
      disabled=not bool(model),
      help=(
        "Gói model + schedule OOS + KB pin thành .tmpkg cho Trade app. "
        f"Ghi vào live/packages_inbox. Cần đã chạy {LABEL_TAB_OOS} (có schedule.json)."
      ),
    ):
      try:
        result = export_model_tmpkg(model)
        st.session_state["_tm_ov_export"] = {
          "mid": mid,
          "path": str(result["path"]),
          "weeks": result["weeks"],
          "error": "",
        }
        st.toast(f"Đã ghi {result['path'].name} → packages_inbox")
      except RuntimeError as exc:
        st.session_state["_tm_ov_export"] = {
          "mid": mid,
          "path": "",
          "weeks": 0,
          "error": str(exc),
        }
  with a3:
    if on_bridge:
      st.warning("Đang trên Bridge — Xóa sẽ gỡ khỏi roster Live.")
    elif st.session_state.get(confirm_key) == mid:
      st.error("Xóa = mất report + schedule gắn với model này.")
    elif ready.get("ok"):
      st.caption(f"Export sẵn sàng · {ready.get('weeks') or 0} tuần OOS.")
    else:
      st.caption(
        f"Export cần schedule từ tab **{LABEL_TAB_OOS}**. "
        + (ready.get("error") or "")
      )

  exp = st.session_state.get("_tm_ov_export") or {}
  if exp.get("mid") == mid:
    if exp.get("error"):
      st.error(exp["error"])
    elif exp.get("path"):
      pkg = Path(exp["path"])
      st.success(
        f"Package `{pkg.name}` · {exp.get('weeks') or 0} tuần OOS · `{pkg}`"
      )
      st.caption(
        "Trade import: [http://127.0.0.1:8801/?nav=Models](http://127.0.0.1:8801/?nav=Models) "
        "(tab **Models**, không phải Live). Live chỉ chạy roster đã import."
      )
      if pkg.is_file():
        st.download_button(
          "Tải .tmpkg",
          data=pkg.read_bytes(),
          file_name=pkg.name,
          mime="application/zip",
          key=f"tm_ov_export_dl_{mid}",
        )
      else:
        st.caption(f"Inbox mặc định: `{default_export_dir()}`")

  with st.expander("Ghi chú đọc bảng", expanded=False):
    st.markdown(notes)


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

  from gui.analysis_support import (
    list_missing_model_health_checks,
    start_missing_model_checks_job,
  )
  from gui.live_readiness import render_live_readiness
  from gui.long_task_ui import render_task_status, task_blocks_ui

  missing = list_missing_model_health_checks(active)
  render_task_status(key_prefix="tm_info_suite")
  blocked = task_blocks_ui("tm_info_suite")

  with st.container(border=True):
    st.markdown(f"#### Checklist {LABEL_TAB_OOS} còn thiếu")
    if not missing:
      st.success(
        "Đủ report: KB ON/OFF · Remine OFF · Mining baseline (nếu cần). "
        f"Chi tiết biểu đồ ở tab **{LABEL_TAB_OOS}**."
      )
    else:
      st.caption(
        f"Một nút chạy lần lượt mọi phần còn thiếu (không cần nhảy từng đoạn trên {LABEL_TAB_OOS})."
      )
      for row in missing:
        st.markdown(f"- **{row['label']}** — {row['reason']}")
      b1, b2 = st.columns([2, 3])
      with b1:
        if st.button(
          "Chạy tất cả check thiếu",
          type="primary",
          icon=":material/playlist_play:",
          use_container_width=True,
          disabled=blocked,
          key="tm_info_run_all_checks",
          help=(
            "Chạy tuần tự: KB ON/OFF → Remine ON/OFF → Mining space vs baseline "
            "(chỉ các mục còn thiếu)."
          ),
        ):
          try:
            start_missing_model_checks_job(active)
            st.toast(f"Đã bắt đầu {len(missing)} check · xem tiến trình phía trên")
            st.rerun()
          except Exception as e:
            st.error(str(e))
      with b2:
        st.caption(
          f"Có thể chuyển tab trong lúc chạy. Kết quả lưu vào model — mở **{LABEL_TAB_OOS}** để xem chart."
        )

  if not report:
    st.info(
      f"Chưa có báo cáo backtest của model. Vào **{LABEL_TAB_OOS}** → **Chạy so sánh** "
      "để tạo report, hoặc tạo model từ Grid Search."
    )
    render_live_readiness(
      active,
      include_bridge=False,
      expanded=True,
      key_prefix="tm_info_ready",
    )
  else:
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

    render_live_readiness(
      active,
      include_bridge=False,
      expanded=False,
      key_prefix="tm_info_ready",
    )

  # Timeline dưới cùng — KPI / readiness trước
  from gui.model_health import build_model_timeline_figure

  st.divider()
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

  if sub == "overview":
    _render_models_overview(models, active)
  elif sub == "info":
    _render_model_info(active)
  elif sub == "health":
    _render_health(active)
  else:
    _render_analysis(sub, active)
