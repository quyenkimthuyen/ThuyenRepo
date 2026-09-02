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
  update_settings,
)
from gui.charts import show_plotly
from gui.grid_search_background import (
  clear_grid_results, get_grid_status, is_grid_running, load_job_state,
  start_grid_search, stop_grid_search,
)
from gui.grid_search_engine import (
  OBJECTIVES,
  _score,
  apply_objective_to_run,
  build_grid_from_settings,
  delete_grid_run,
  estimate_grid_count,
  filter_specs_for_incremental,
  grid_readiness,
  list_grid_runs,
  load_grid_run,
  load_latest_grid_run,
  merge_grid_results,
  summarize_grid_config,
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
  if status["running"] or status.get("status") == "interrupted":
    st.progress(
      min(1.0, max(0.0, status["done"] / max(status["total"], 1))),
      text=(
        f"⏳ Grid Search — {status['done']}/{status['total']} "
        f"({status['pct']}%) · {status['current_label'] or '…'}"
      ),
    )
    return
  # Parent still shows "running" until full remount — unlock completed UI.
  st.rerun()


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


def _rows_for_display(
  status: dict,
  *,
  history_run: dict | None = None,
  force_latest: bool = False,
) -> tuple[list, str, dict | None]:
  """Return (rows, objective, source_run_payload).

  When ``history_run`` is set (viewing an archive), use that payload as-is.
  When ``force_latest`` (selector = Hiện tại), always use ``latest.json`` —
  never fall back to leftover ``job_state.rows`` from another run.
  Otherwise prefer live job rows while running, else latest.json.
  """
  job = load_job_state() or {}
  settings = get_settings()
  default_objective = settings.get("grid_objective", "total_r")

  if history_run is not None:
    rows = list(history_run.get("rows") or [])
    objective = history_run.get("objective") or default_objective
    return rows, objective, history_run

  data = load_latest_grid_run()
  objective = default_objective

  if force_latest:
    rows = list((data or {}).get("rows") or [])
    objective = (data or {}).get("objective") or objective
    return rows, objective, data

  if status.get("running") and job.get("rows"):
    rows = list(job["rows"])
    objective = job.get("objective") or (data or {}).get("objective") or objective
    source = data
  else:
    rows = list((data or {}).get("rows") or [])
    objective = (data or {}).get("objective") or job.get("objective") or objective
    source = data

  seed = (job.get("config") or {}).get("seed_rows") or []
  if seed and rows and status.get("running"):
    rows = merge_grid_results(seed, rows, objective=objective)

  return rows, objective, source


def _history_option_label(summary: dict) -> str:
  rid = summary.get("run_id") or "?"
  when = str(summary.get("updated_at") or "")[:19].replace("T", " ")
  n = summary.get("n_ok")
  if n is None:
    n = summary.get("n_runs") or 0
  best_r = summary.get("best_total_r")
  best_txt = f"{float(best_r):+.1f}R" if best_r is not None else "—"
  tag = " · latest" if summary.get("is_latest") else ""
  train = summary.get("train_txt") or "—"
  oos = summary.get("oos_txt") or "—"
  mining = summary.get("mining_txt") or "—"
  # Compact dropdown line; full details shown in the config panel below.
  return (
    f"{when} · `{rid}` · {n} combo · best {best_txt} · "
    f"train {train} · OOS {oos} · mining {mining}{tag}"
  )


def _extract_grid_run_id(value: str | None) -> str | None:
  """Parse ``gs_YYYYMMDD_HHMMSS`` from a preference label or raw id."""
  import re
  text = str(value or "").strip()
  if not text:
    return None
  if text in ("__latest__", "latest", "current"):
    return "__latest__"
  if text.startswith("gs_") and " " not in text and "·" not in text:
    return text
  match = re.search(r"gs_\d{8}_\d{6}", text)
  return match.group(0) if match else None


def _on_grid_objective_changed() -> None:
  persist_widget("gs_objective", "grid.objective")
  obj = st.session_state.get("gs_objective") or "total_r"
  update_settings(grid_objective=obj)
  st.session_state["_gs_objective_dirty"] = True


def _selected_grid_objective() -> str:
  keys = list(OBJECTIVES.keys())
  raw = st.session_state.get("gs_objective")
  if raw in keys:
    return str(raw)
  saved = get_settings().get("grid_objective", "risk_adjusted")
  return saved if saved in keys else "total_r"


def _on_grid_history_changed() -> None:
  persist_widget("gs_history_run_id", "grid.history_run_id")
  # Combo picker options are per-run — drop sticky selection from another run.
  st.session_state.pop("gs_pick_combo", None)
  for key in ("gs_any_tm_name", "grid.selected_combo"):
    st.session_state.pop(key, None)


def _sort_rows_for_objective(rows: list, objective: str) -> list:
  """Stable display order by the selected Grid objective."""
  valid = [r for r in rows if not r.get("error")]
  errors = [r for r in rows if r.get("error")]
  valid.sort(key=lambda r: _score(r, objective or "total_r"), reverse=True)
  return valid + errors


def _resolve_best_row(
  data: dict | None,
  rows: list,
  objective: str,
) -> dict | None:
  """Best combo belonging to this run payload (never borrow from another run)."""
  valid = [r for r in (rows or []) if isinstance(r, dict) and not r.get("error")]
  if not valid:
    return None
  stored = (data or {}).get("best")
  if isinstance(stored, dict) and not stored.get("error"):
    sk = stored.get("key")
    if sk:
      match = next((r for r in valid if r.get("key") == sk), None)
      if match is not None:
        return match
    # Legacy payloads without key — only trust stored if metrics match a row.
    for r in valid:
      if (
        r.get("total_r") == stored.get("total_r")
        and r.get("train_weeks") == stored.get("train_weeks")
        and r.get("win_rate_pct") == stored.get("win_rate_pct")
      ):
        return r
  return max(valid, key=lambda r: _score(r, objective or "total_r"))


def _render_run_config_panel(run_payload: dict | None, *, objective: str, viewing_history: bool) -> None:
  """Show KB / OOS / mining / train / epoch details for the selected grid run."""
  if not run_payload:
    return
  cfg = summarize_grid_config(run_payload.get("config"))
  obj_label = OBJECTIVES.get(objective, objective)
  title = "Cấu hình lần chạy đang xem" + (" (lịch sử)" if viewing_history else "")
  with st.expander(title, expanded=True):
    c1, c2 = st.columns(2)
    with c1:
      st.markdown(
        f"- **Run:** `{run_payload.get('run_id') or '—'}`  \n"
        f"- **Thời điểm:** {run_payload.get('updated_at') or '—'}  \n"
        f"- **Mục tiêu xếp hạng:** {obj_label}  \n"
        f"- **Train weeks:** {cfg['train_txt']}  \n"
        f"- **OOS:** {cfg['oos_txt']}  \n"
        f"- **Phí:** {cfg['cost_txt']}"
      )
    with c2:
      st.markdown(
        f"- **KB / giai đoạn:** {cfg['kb_txt']}  \n"
        f"- **Epoch:** {cfg['epochs_txt']}  \n"
        f"- **Mining space:** {cfg['mining_txt']}  \n"
        f"- **Số combo:** {run_payload.get('n_runs') or len(run_payload.get('rows') or [])}  \n"
        f"- **Chữ ký settings:** `{cfg.get('settings_signature') or '—'}`"
      )


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
      loops = int(get_settings().get("learning_loops") or 4)
      st.warning(
        f"**Chưa đủ vòng học** — hiện **{ready_n}/{expected}** combo. "
        f"Hoàn thành **{loops}** vòng cho các giai đoạn trong Cài đặt "
        f"trước khi chạy Grid Search."
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

  # Mục tiêu xếp hạng — trên trang Grid (không còn ở Cài đặt).
  obj_keys = list(OBJECTIVES.keys())
  restore_widget(
    "gs_objective",
    get_settings().get("grid_objective", "risk_adjusted"),
    preference_key="grid.objective",
    options=obj_keys,
  )
  if st.session_state.get("gs_objective") not in obj_keys:
    st.session_state["gs_objective"] = obj_keys[0]
  st.selectbox(
    "Mục tiêu xếp hạng (Best / bảng kết quả)",
    obj_keys,
    format_func=lambda k: OBJECTIVES.get(k, k),
    key="gs_objective",
    on_change=_on_grid_objective_changed,
    help=(
      "Chỉ đổi thứ tự xếp hạng combo đã có — không cần chạy lại Grid. "
      "Report (latest / lần chạy đang xem) được cập nhật theo mục tiêu mới."
    ),
    disabled=running,
  )
  selected_objective = _selected_grid_objective()

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
    total_n = len(specs)
    if new_specs:
      st.info(
        f"**{len(new_specs)} combo mới** cần chạy · hiện có **{skip_n}/{total_n}** kết quả "
        f"· dự kiến {len(new_specs) * 2:.0f}–{len(new_specs) * 4:.0f} phút."
      )
    else:
      st.success(f"✅ Grid đã đủ **{skip_n}/{total_n} combo** — không cần chạy lại.")

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
    objective = selected_objective
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
    objective = selected_objective
    try:
      rid = start_grid_search(specs, objective=objective, config=grid_config)
      st.session_state["settings_grid_signature"] = settings_grid_signature()
      st.toast(f"Grid full `{rid}` — {len(specs)} combo")
      st.rerun()
    except RuntimeError as e:
      st.error(str(e))

  with st.expander("Reset dữ liệu Grid Search", expanded=False):
    st.caption(
      "Xóa `latest.json`, `job_state.json` và các file `gs_*.json` (cả lịch sử). "
      "Không ảnh hưởng KB hay Trade Model."
    )
    confirm_gs = st.checkbox(
      "Xác nhận xóa toàn bộ kết quả Grid Search",
      key="gs_reset_confirm",
    )
    if st.button(
      "Xóa kết quả Grid Search",
      type="secondary",
      icon=":material/delete_forever:",
      key="gs_reset_btn",
      disabled=running or not confirm_gs,
    ):
      try:
        out = clear_grid_results(delete_archives=True)
        st.session_state.pop("settings_grid_signature", None)
        st.session_state.pop("gs_history_pick", None)
        st.session_state.pop("gs_history_run_id", None)
        n = out.get("n") or 0
        if n:
          st.success(f"Đã xóa {n} file Grid Search.")
        else:
          st.info("Không có dữ liệu Grid để xóa.")
        st.rerun()
      except RuntimeError as e:
        st.error(str(e))

  # --- History selector (archived gs_*.json runs) ---
  history_run = None
  viewing_history = False
  force_latest = True
  selected_run_id = None
  archives = list_grid_runs(limit=40) if not running else []
  if archives and not running:
    st.markdown("#### Lịch sử lần chạy")
    latest_token = "__latest__"
    hist_ids = [latest_token] + [str(a["run_id"]) for a in archives]
    hist_labels = {
      latest_token: "● Hiện tại (latest)",
      **{str(a["run_id"]): _history_option_label(a) for a in archives},
    }

    # Migrate old preference that stored the full dropdown label.
    from gui.ui_preferences import get_preference, delete_preference
    legacy = get_preference("grid.history_run")
    if legacy and not get_preference("grid.history_run_id"):
      migrated = _extract_grid_run_id(str(legacy))
      if migrated and migrated in hist_ids:
        set_widget_preference("gs_history_run_id", migrated, "grid.history_run_id")
      delete_preference("grid.history_run")

    restore_widget(
      "gs_history_run_id", latest_token,
      preference_key="grid.history_run_id",
      options=hist_ids,
    )
    if st.session_state.get("gs_history_run_id") not in hist_ids:
      st.session_state["gs_history_run_id"] = latest_token

    pick_id = st.selectbox(
      "Xem kết quả lần chạy",
      hist_ids,
      format_func=lambda rid: hist_labels.get(rid, rid),
      key="gs_history_run_id",
      on_change=_on_grid_history_changed,
      help=(
        "Mỗi lần Grid Search lưu file `gs_*.json`. "
        "Chọn run_id để xem đúng bảng / cấu hình của lần đó."
      ),
    )
    if pick_id == latest_token:
      viewing_history = False
      force_latest = True
      selected_run_id = next(
        (a.get("run_id") for a in archives if a.get("is_latest")),
        archives[0].get("run_id"),
      )
    else:
      viewing_history = True
      force_latest = False
      selected_run_id = pick_id
      history_run = load_grid_run(selected_run_id)
      if history_run is None:
        st.warning(f"Không đọc được run `{selected_run_id}`.")
        viewing_history = False
        force_latest = True
        selected_run_id = None
        history_run = None
      else:
        # Guard: file payload must match the selected id.
        file_rid = str(history_run.get("run_id") or selected_run_id)
        st.info(
          f"Đang xem lịch sử **`{file_rid}`** · "
          f"{history_run.get('updated_at') or '—'} · "
          f"**{len(history_run.get('rows') or [])}** combo trong file "
          f"(n_runs={history_run.get('n_runs') or '—'}). "
          "Chọn **● Hiện tại (latest)** để quay lại kết quả mới nhất."
        )

    if selected_run_id:
      with st.expander(f"Xóa lần chạy `{selected_run_id}`", expanded=False):
        summary = next((a for a in archives if a.get("run_id") == selected_run_id), None)
        if summary:
          st.caption(
            f"Train **{summary.get('train_txt')}** · OOS **{summary.get('oos_txt')}** · "
            f"KB **{summary.get('kb_txt')}** · Mining **{summary.get('mining_txt')}** · "
            f"Epoch **{summary.get('epochs_txt')}**"
          )
        st.caption(
          "Chỉ xóa file kết quả Grid này (`gs_*.json`). "
          "Không xóa KB hay Trade Model. Nếu đây là latest, app sẽ chuyển latest sang run mới hơn (nếu còn)."
        )
        confirm_one = st.checkbox(
          f"Xác nhận xóa `{selected_run_id}`",
          key=f"gs_delete_one_confirm_{selected_run_id}",
        )
        if st.button(
          "Xóa lần chạy này",
          type="secondary",
          icon=":material/delete:",
          key=f"gs_delete_one_btn_{selected_run_id}",
          disabled=not confirm_one,
        ):
          try:
            if is_grid_running():
              raise RuntimeError("Grid Search đang chạy — hủy trước khi xóa.")
            out = delete_grid_run(selected_run_id)
            st.session_state.pop("gs_history_run_id", None)
            st.session_state.pop("gs_history_pick", None)
            msg = f"Đã xóa `{out.get('deleted')}`."
            if out.get("promoted_latest"):
              msg += f" Latest → `{out['promoted_latest']}`."
            elif out.get("was_latest"):
              msg += " Đã xóa latest (không còn run nào)."
            st.toast(msg)
            st.rerun()
          except (RuntimeError, ValueError, FileNotFoundError) as e:
            st.error(str(e))

  rows, _stored_obj, data = _rows_for_display(
    job_status,
    history_run=history_run if viewing_history else None,
    force_latest=force_latest and not running,
  )
  # Rank by mục tiêu trên trang Grid (không khóa theo objective đã lưu trong run).
  objective = selected_objective
  dirty = bool(st.session_state.pop("_gs_objective_dirty", False))
  if data and not running and (dirty or (data.get("objective") != objective)):
    data = apply_objective_to_run(data, objective, persist=True) or data
    rows = list(data.get("rows") or [])
    if dirty:
      st.toast(f"Đã xếp lại report theo: {OBJECTIVES.get(objective, objective)}")
  else:
    rows = _sort_rows_for_objective(list(rows or []), objective)

  if not rows and not running:
    if ready_n == 0:
      loops = int(get_settings().get("learning_loops") or 4)
      missing = readiness.get("missing_profiles") or []
      era_txt = ", ".join(m["label"] for m in missing) or "theo Cài đặt"
      st.info(
        "Bước tiếp: **Học & tối ưu → Huấn luyện bộ nhớ** — học giai đoạn "
        f"({era_txt}), mỗi giai đoạn **{loops}** vòng. "
        "Sau đó quay lại Grid Search."
      )
    elif archives:
      st.info("Lần chạy hiện tại trống — chọn một run trong **Lịch sử lần chạy** ở trên.")
    else:
      st.info("Nhấn **Chạy Grid Search** để bắt đầu.")
    return

  if running and not rows:
    st.caption("Đang chờ kết quả combo đầu tiên…")
    return

  if data and not running:
    _render_run_config_panel(data, objective=objective, viewing_history=viewing_history)

  display_run_id = str((data or {}).get("run_id") or selected_run_id or "—")
  best = _resolve_best_row(data, rows, objective)
  if best and not best.get("error"):
    obj_label = OBJECTIVES.get(objective, objective)
    st.markdown(
      f"##### Best của lần chạy `{display_run_id}`"
      + (" *(lịch sử)*" if viewing_history else " *(latest)*")
      + f" · xếp theo **{obj_label}**"
    )
    c1, c2, c3, c4 = st.columns(4)
    # Include run_id in labels so Streamlit cannot keep a sticky metric identity.
    c1.metric(f"Total R · {display_run_id[-6:]}", f"{float(best.get('total_r') or 0):+.2f}")
    c2.metric("WR%", f"{best.get('win_rate_pct', 0)}%")
    c3.metric("Max DD", f"{best.get('max_drawdown_r', 0)}R")
    c4.metric("Train", f"{best.get('train_weeks')} tuần")
    st.success(
      f"**Tốt nhất:** {best.get('label')} · "
      f"key `{best.get('key') or '—'}` · "
      f"PF {best.get('profit_factor')} · {best.get('n_trades')} lệnh"
    )
    if not running:
      apply_key = f"gs_apply_tm_{display_run_id}"
      if st.button(
        "✓ Tạo Trade Model từ combo tốt nhất (dùng ngay)",
        key=apply_key,
      ):
        from gui.trade_model import find_model_by_grid_key
        existed = find_model_by_grid_key(best.get("key"))
        m = create_trade_model(best, run_id=display_run_id, set_active=True)
        if existed and existed.get("id") == m.get("id"):
          st.toast("Combo này đã có Trade Model — đã chọn lại (không tạo trùng)")
        else:
          st.toast("Đã tạo & chọn trade model từ best combo")
        st.rerun()

  st.subheader("Bảng kết quả")
  st.caption(
    f"Đang hiển thị run **`{display_run_id}`** · "
    f"{len([r for r in rows if not r.get('error')])} combo hợp lệ"
    + (" · (lịch sử)" if viewing_history else " · (latest)")
    + f" · objective `{objective}`"
  )
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
    "label", "train_weeks", "use_kb", "giai_doan", "kb_snapshot",
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
        f"WR={r.get('win_rate_pct', 0)}% · train={r.get('train_weeks')} tuần"
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
    grid_train_title = "Grid · Total R theo cửa sổ train"
    fig = px.bar(
      plot_df, x="train_weeks", y="total_r", color="kb_tag",
      barmode="group", title=grid_train_title,
    )
    fig.update_layout(height=400)
    show_plotly(fig, grid_train_title)

  with tab2:
    grid_heatmap_title = "Grid · Heatmap Total R"
    pivot_df = plot_df.groupby(["train_weeks", "kb_tag"], as_index=False)["total_r"].max()
    if len(pivot_df) > 1:
      piv = pivot_df.pivot(index="kb_tag", columns="train_weeks", values="total_r")
      fig_h = go.Figure(data=go.Heatmap(
        z=piv.values,
        x=[str(c) for c in piv.columns],
        y=list(piv.index),
        colorscale="RdYlGn",
        text=[[f"{v:+.1f}" for v in row] for row in piv.values],
        texttemplate="%{text}",
      ))
      fig_h.update_layout(title=grid_heatmap_title, height=max(300, len(piv) * 40))
      show_plotly(fig_h, grid_heatmap_title)

  with tab3:
    grid_top_title = "Grid · Top 15 combo"
    top = df.head(15)
    fig2 = go.Figure(go.Bar(
      x=top["total_r"], y=top["label"], orientation="h",
      marker_color=["#2ecc71" if r > 0 else "#e74c3c" for r in top["total_r"]],
    ))
    fig2.update_layout(
      title=grid_top_title, height=500,
      margin=dict(l=200, r=20, t=40, b=40),
      yaxis=dict(autorange="reversed"),
    )
    show_plotly(fig2, grid_top_title)
