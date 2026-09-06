"""MT5 Bridge — Trader desk: EA live status, decision, open risk, PnL."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from gui.charts import show_plotly
from gui.desk_ui import tf_label
from gui.mt5_live_chart import build_ea_chart, connection_health, load_ea_chart_data
from gui.navigation import (
  ALL_ITEMS,
  LABEL_CHART_EQUITY,
  LABEL_CHART_MONTHLY,
  LABEL_CHART_WEEKLY,
  LABEL_TAB_OOS,
  LABEL_TAB_REWARD,
)
from gui.page_chrome import render_page_header
from gui.trade_model import (
  format_model_label,
  get_active_trade_model,
  list_trade_models,
)
from gui.ui_preferences import preference_callback, restore_widget, set_preference
from mt5_bridge.history_sync import get_history_status, start_history_sync
from mt5_bridge import background as bridge_bg
from mt5_bridge.comm_log import append_event, clear_log, read_events
from mt5_bridge.live_monitor_server import desk_chart_port
from mt5_bridge.protocol import (
  BRIDGE_DIR,
  BRIDGE_SIM_DIR,
  DEFAULT_MODEL_ID,
  INSTANCE_ID,
  MAX_BRIDGE_MODELS,
  ROOT,
  bar_path,
  bars_path,
  command_ack_path,
  command_path,
  connection_path,
  decision_path,
  fill_path,
  normalize_model_ids,
  pip_size_from_quotes,
  prices_from_pips,
  read_json,
  bridge_dir_display,
  bridge_file_display,
  resolve_live_bridge_dir,
  resolve_sim_bridge_dir,
  status_path,
  write_manual_close_command,
  write_manual_market_command,
)


from mt5_bridge.trade_journal import (
  clear_trades,
  compute_stats,
  filter_trades,
  load_trades,
  trade_mode,
)
from gui.views.mt5_bridge_helpers import (
  CHART_RANGE_OPTIONS,
  chart_bars_full,
  desk_symbol as _desk_symbol,
)



def _bridge_any_service_running() -> bool:
  return bool(bridge_bg.get_status().get("running")) or bool(
    bridge_bg.get_sim_status().get("running")
  )


LIVE_VIEW_ALL = "__all__"


def _live_roster_model_ids() -> list[str]:
  from gui.trade_model import get_bridge_runtime_model_ids

  ids = get_bridge_runtime_model_ids()
  if ids:
    return list(ids)
  active = get_active_trade_model()
  if active and active.get("id"):
    return [str(active["id"])]
  return []


def _legend_model_label(mid: str) -> str:
  from gui.trade_model import format_model_label, get_model_by_id

  m = get_model_by_id(mid)
  s = format_model_label(m) if m else str(mid)
  return s if len(s) <= 28 else s[:27] + "…"


def _render_live_model_scope(*, widget_key: str, pref_key: str) -> str | None:
  """Tất cả → None; một model → id. Ẩn dropdown nếu roster chỉ 1 model."""
  from gui.trade_model import format_model_label, get_model_by_id

  ids = _live_roster_model_ids()
  if len(ids) <= 1:
    return ids[0] if ids else None
  options = [LIVE_VIEW_ALL, *ids]

  def _label(mid: str) -> str:
    if mid == LIVE_VIEW_ALL:
      return f"Tất cả ({len(ids)} model)"
    m = get_model_by_id(mid)
    return format_model_label(m) if m else mid

  restore_widget(
    widget_key, LIVE_VIEW_ALL,
    preference_key=pref_key,
    options=options,
  )
  pick = st.selectbox(
    "Trade Model",
    options,
    format_func=_label,
    key=widget_key,
    on_change=preference_callback(widget_key, pref_key),
  )
  if pick == LIVE_VIEW_ALL:
    return None
  return str(pick)


def _render_manual_remine_controls(model_ids: list[str]) -> None:
  """Force remine current broker week for the Live roster (running Bridge)."""
  from mt5_bridge.manual_remine import read_remine_status, request_live_remine
  from mt5_bridge.protocol import history_replay_active
  from mt5_bridge.weekend_preremine import this_week_start

  live_dir = resolve_live_bridge_dir()
  live_on = bool(bridge_bg.get_status().get("running"))
  feed_on = False
  try:
    feed_on = bool(history_replay_active(live_dir))
  except Exception:
    feed_on = False
  file_st = read_json(status_path(live_dir)) or {}
  status = read_remine_status(live_dir)
  state = str(status.get("state") or "")
  week = str(file_st.get("week_start") or this_week_start().date())[:10]
  n = len(model_ids or [])
  busy = state in ("queued", "running")

  if state == "running":
    cur = status.get("current_model") or "…"
    st.info(status.get("message") or f"Đang remine **{cur}** · tuần {status.get('week_start') or week}.")
  elif state == "queued":
    st.warning(
      "Đã gửi lúc **"
      + str(status.get("updated_at") or "—")
      + "**. Bridge nhận trong **vài giây** rồi mine (vài phút/model) — "
      "không đợi Chủ nhật. Nếu dòng này đứng yên: process đang chạy code cũ → "
      "**Stop rồi Start Bridge** (không cần bấm lại)."
    )
  elif state == "done":
    bits = []
    for row in status.get("results") or []:
      if row.get("ok") and row.get("name"):
        bits.append(str(row["name"])[:48])
    extra = (" · " + " · ".join(bits[:5])) if bits else ""
    st.success(
      (status.get("message") or "Remine xong")
      + f" · tuần {status.get('week_start') or week}{extra}"
    )
  elif state == "error":
    st.error(status.get("error") or status.get("message") or "Remine thất bại.")

  disabled = (not live_on) or (not n) or busy or feed_on
  help_txt = (
    "Mine lại strategy tuần broker hiện tại với công thức SL hiện tại "
    "(ATR×mult + spread). Ghi đè live_weeks tuần này. Lệnh đang mở giữ SL cũ. "
    "Vài phút mỗi model — Bridge tạm ngừng quyết định trong lúc mine."
  )
  if not live_on:
    help_txt = "Cần Start Bridge Live trước."
  elif feed_on:
    help_txt = "Tắt Test lịch sử trước khi remine Live."
  elif not n:
    help_txt = "Chọn model trên roster trước."

  if st.button(
    f"Remine tuần này ({n} model · {week})",
    type="primary",
    use_container_width=True,
    key="bridge_manual_remine_week",
    disabled=disabled,
    help=help_txt,
  ):
    request_live_remine(live_dir, model_ids=list(model_ids), week_start=week)
    st.toast(f"Đã gửi remine tuần {week} — Bridge đang mine.")
    st.rerun()
  st.caption(
    "Không đợi Chủ nhật. Genome mới dùng SL đã cộng spread. "
    "Health OOS trên card model chưa đổi cho đến khi chạy lại Đánh giá OOS."
  )


def _render_bridge_models_tab() -> list[str]:
  """Một chỗ chọn Trade Model + Risk + checklist — dùng chung Live & Simulate."""
  from gui.live_readiness import render_live_readiness
  from gui.trade_model import (
    bridge_ghost_model_ids,
    bridge_roster_display_rows,
    format_model_short,
    get_bridge_runtime_model_ids,
    prune_bridge_roster,
  )

  cfg = bridge_bg.load_config()
  labels, by_label, by_id = _bridge_model_options()
  cfg_ids = normalize_model_ids(cfg.get("model_ids"), fallback=cfg.get("model_id"))
  ghosts = bridge_ghost_model_ids()
  if ghosts:
    g1, g2 = st.columns([4, 1])
    with g1:
      st.warning(
        "Roster Bridge có **id ma** (đã Archive/xóa): "
        + ", ".join(f"`{g}`" for g in ghosts[:6])
        + (" …" if len(ghosts) > 6 else "")
      )
    with g2:
      if st.button(
        "Dọn roster",
        key="bridge_prune_ghosts",
        use_container_width=True,
        help="Gỡ id không còn trong store live khỏi Bridge config + models.json.",
      ):
        result = prune_bridge_roster(drop_unknown=True)
        if result.get("error"):
          st.error(result["error"])
        else:
          removed = result.get("removed") or []
          st.toast(f"Đã gỡ {len(removed)} id" if removed else "Roster đã sạch")
          st.rerun()

  default_labels = []
  for mid in cfg_ids:
    if mid in ghosts:
      continue
    m = by_id.get(mid)
    if m is not None:
      default_labels.append(format_model_label(m))
  if not default_labels and labels:
    # Migrate old Simulate-only preference if present
    sim_pref = st.session_state.get("mt5_sim_models")
    if isinstance(sim_pref, list) and sim_pref:
      default_labels = [x for x in sim_pref if x in labels]
    if not default_labels:
      active = get_active_trade_model()
      if active:
        default_labels = [format_model_label(active)]
      else:
        default_labels = labels[:1]

  running = _bridge_any_service_running()
  restore_widget(
    "mt5_bridge_models", default_labels,
    preference_key="mt5.bridge_model_labels",
    options=labels,
    multiple=True,
  )
  st.subheader("Trade Models · Bridge")
  st.caption(
    "Chọn model **một lần** — dùng cho **Live** và **test lịch sử**. "
    "Mỗi model một magic · tối đa 1 lệnh mở · Risk % ở tab **Risk control**. "
    "Danh sách không gồm model Archived."
  )
  picked_labels = st.multiselect(
    "Trade models (1–5)",
    labels,
    key="mt5_bridge_models",
    max_selections=MAX_BRIDGE_MODELS,
    disabled=running or not labels,
    on_change=preference_callback("mt5_bridge_models", "mt5.bridge_model_labels"),
    help="Đổi model khi Live và test lịch sử đang Stop. Archived không hiện ở đây.",
  )
  model_ids = normalize_model_ids([by_label[x] for x in picked_labels if x in by_label])
  # Never persist ghost ids from stale config when user has an empty/valid pick
  if not model_ids and cfg_ids:
    live_cfg = [mid for mid in cfg_ids if mid in by_id]
    model_ids = live_cfg
  primary_id = model_ids[0] if model_ids else (
    (get_active_trade_model() or {}).get("id") or DEFAULT_MODEL_ID
  )
  if model_ids and (
    cfg.get("model_ids") != model_ids or cfg.get("model_id") != primary_id
  ):
    cfg = bridge_bg.save_config(model_id=primary_id, model_ids=model_ids)
  elif ghosts and not running:
    # Auto-suggest prune path already shown; do not silently rewrite while
    # user may still want to inspect ghosts via "Dọn roster".
    pass

  if running:
    st.info("Live hoặc test lịch sử đang chạy — Stop trước khi đổi model.")

  remine_on = bool(cfg.get("remine_each_week", True))
  restore_widget(
    "bridge_remine_each_week",
    remine_on,
    preference_key="mt5.bridge_remine_each_week",
  )
  picked_remine = st.toggle(
    "Remine mỗi tuần (Live)",
    key="bridge_remine_each_week",
    disabled=running,
    help=(
      "ON (mặc định): đầu mỗi tuần broker, Bridge mine strategy mới "
      "(sau khi dùng hết tuần trong OOS schedule). "
      "OFF: freeze strategy sau lần mine đầu trong phiên Bridge — "
      "không ghi thêm live_weeks."
    ),
    on_change=preference_callback(
      "bridge_remine_each_week", "mt5.bridge_remine_each_week",
    ),
  )
  if picked_remine != remine_on and not running:
    cfg = bridge_bg.save_config(remine_each_week=bool(picked_remine))
  st.caption(
    "Remine chạy ở **bar M15 đóng đầu tiên của tuần broker** (Chủ nhật 00:00). "
    f"Chế độ hiện tại: **{'ON — remine hàng tuần' if cfg.get('remine_each_week', True) else 'OFF — freeze'}**."
  )

  wk_on = bool(cfg.get("weekend_preremine_enabled", True))
  restore_widget(
    "bridge_weekend_preremine",
    wk_on,
    preference_key="mt5.bridge_weekend_preremine",
  )
  picked_wk = st.toggle(
    "Weekend pre-remine (T6≥18h / T7 / CN)",
    key="bridge_weekend_preremine",
    disabled=running,
    help=(
      "Mine / warm strategy cho **tuần tới** khi thị trường nghỉ — "
      "Thứ Hai mở cửa chỉ cần đọc live_weeks/schedule (nhanh hơn remine lúc mở cửa). "
      "Cần Bridge **Start** trong cửa sổ cuối tuần."
    ),
    on_change=preference_callback(
      "bridge_weekend_preremine", "mt5.bridge_weekend_preremine",
    ),
  )
  if picked_wk != wk_on and not running:
    cfg = bridge_bg.save_config(weekend_preremine_enabled=bool(picked_wk))

  # Roster snapshot
  ids_runtime = get_bridge_runtime_model_ids() or model_ids
  try:
    from mt5_bridge.weekend_preremine import (
      build_quality_status_table,
      prune_preremine_to_roster,
    )
    prune_preremine_to_roster(ids_runtime)
    q = build_quality_status_table(ids_runtime)
    if q.get("rows"):
      mode = q.get("mode") or "trading"
      week = q.get("week") or "—"
      if mode == "preremine":
        st.caption(
          f"**Weekend pre-remine** · tuần tới **{week}** "
          f"({q.get('ready_n', 0)}/{len(q['rows'])} READY) · "
          f"tuần giao dịch hiện tại {q.get('trade_week') or '—'}"
        )
      else:
        st.caption(
          f"Remine tuần **{week}** · "
          f"{q.get('ready_n', 0)}/{len(q['rows'])} READY"
          + (
            " · pre-remine bật — cửa sổ T6≥18h / T7 / CN"
            if q.get("enabled") else ""
          )
        )
      qtable = []
      for r in q["rows"]:
        qtable.append({
          "Model": r.get("model"),
          "Tuần": r.get("week"),
          "Status": r.get("status"),
          "Remine": r.get("remine"),
          "Strategy": r.get("strategy"),
          "Cập nhật": r.get("updated"),
        })
      st.dataframe(pd.DataFrame(qtable), hide_index=True, use_container_width=True)
  except Exception as exc:
    st.caption(f"Weekend pre-remine status: — ({exc})")

  if ids_runtime:
    prefer_sim = bool(bridge_bg.get_sim_status().get("running")) and not bool(
      bridge_bg.get_status().get("running")
    )
    rows = bridge_roster_display_rows(include_runtime=True, prefer_sim=prefer_sim)
    if rows:
      table = []
      for i, r in enumerate(rows, 1):
        oos = f"{r['oos_r']:+.1f}R" if r.get("oos_r") is not None else "—"
        table.append({
          "#": i,
          "Model": r["name"],
          "Magic": r.get("magic") or "—",
          "Tuần": r.get("week_start") or "—",
          "Strategy": r.get("strategy") or "—",
          "Remine": r.get("remine_status") or "—",
          "OOS R": oos,
          "Last": r.get("last_action") or "—",
          "BUY": _wait_side_caption((r.get("signal_wait") or {}).get("buy")),
          "SELL": _wait_side_caption((r.get("signal_wait") or {}).get("sell")),
          "Reason": r.get("last_reason") or "—",
        })
      st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True)
    else:
      for mid in ids_runtime:
        m = by_id.get(mid)
        label = format_model_short(m) if m else f"{mid[:28]} (id ma)"
        st.caption(f"· {label}")

  if ids_runtime:
    _render_manual_remine_controls(list(ids_runtime))

  st.divider()
  # Prefer live status; fall back to sim — use configured/clone bridge dirs
  live_st = read_json(status_path(resolve_live_bridge_dir())) or {}
  sim_st = read_json(status_path(resolve_sim_bridge_dir())) or {}
  if bridge_bg.get_status().get("running") or (
    live_st.get("per_model") or live_st.get("model_ids")
  ):
    bridge_dir = resolve_live_bridge_dir()
    file_status = live_st
  else:
    bridge_dir = resolve_sim_bridge_dir()
    file_status = sim_st
  decision = read_json(decision_path(bridge_dir)) or {}
  active = by_id.get(primary_id) or get_active_trade_model()
  render_live_readiness(
    active,
    decision=decision,
    file_status=file_status,
    include_bridge=True,
    expanded=True,
    key_prefix="bridge_models_ready",
  )
  return model_ids


def _bridge_model_options() -> tuple[list[str], dict[str, str], dict[str, dict]]:
  """labels, label→id, id→model for multiselect (live models only)."""
  models = list_trade_models()
  labels = [format_model_label(m) for m in models]
  by_label = {format_model_label(m): str(m.get("id") or "") for m in models}
  by_id = {str(m.get("id") or ""): m for m in models if m.get("id")}
  return labels, by_label, by_id


def _selected_bridge_model_ids(
  *,
  widget_key: str = "mt5_bridge_models",
  fallback_active: bool = True,
) -> list[str]:
  labels, by_label, _ = _bridge_model_options()
  picked = st.session_state.get(widget_key) or []
  ids = normalize_model_ids([by_label[x] for x in picked if x in by_label])
  if ids:
    return ids
  cfg_ids = normalize_model_ids(bridge_bg.load_config().get("model_ids"))
  if cfg_ids:
    return cfg_ids
  if fallback_active:
    active = get_active_trade_model()
    if active and active.get("id"):
      return [str(active["id"])]
  if labels:
    return normalize_model_ids([by_label[labels[0]]])
  return []


def _max_trades_by_model_from_session(model_ids: list[str]) -> dict[str, int]:
  out: dict[str, int] = {}
  for mid in model_ids:
    key = f"mt5_max_trades_{mid}"
    if key in st.session_state:
      try:
        out[str(mid)] = max(0, int(st.session_state[key]))
      except (TypeError, ValueError):
        continue
  return out


def _save_bridge_runtime_settings() -> None:
  ids = _selected_bridge_model_ids()
  bridge_bg.save_config(
    model_id=ids[0] if ids else DEFAULT_MODEL_ID,
    model_ids=ids,
    risk_pct=float(st.session_state.get("mt5_risk_pct", 1.0)),
    poll_sec=float(st.session_state.get("mt5_poll_sec", 2.0)),
    loss_guard_enabled=bool(st.session_state.get("mt5_loss_guard_enabled", True)),
    loss_guard_max_day=int(st.session_state.get("mt5_loss_guard_max_day", 3)),
    loss_guard_max_week=int(st.session_state.get("mt5_loss_guard_max_week", 5)),
    max_trades_per_day_by_model=_max_trades_by_model_from_session(ids),
  )


def resolve_loss_guard_limits(
  *,
  prev_model_id: str | None,
  model_id: str,
  cfg_max_day: int | None,
  cfg_max_week: int | None,
  suggested: int,
) -> tuple[int, int, bool]:
  """Pick day/week limits for the Loss guard widgets.

  Returns ``(max_day, max_week, reset_for_model_change)``.
  On refresh (``prev_model_id is None``) restore from config; only when the
  Trade Model changes in-session do we reset to ``suggested``.
  """
  if prev_model_id is None:
    day = int(cfg_max_day if cfg_max_day is not None else suggested)
    week = int(cfg_max_week if cfg_max_week is not None else suggested)
    return day, week, False
  if prev_model_id != model_id:
    return int(suggested), int(suggested), True
  day = int(cfg_max_day if cfg_max_day is not None else suggested)
  week = int(cfg_max_week if cfg_max_week is not None else suggested)
  return day, week, False


def _bridge_mode() -> str:
  """Desk / chart / stats always Live. Test lịch sử is a sibling tab, not a mode."""
  return "live"


def _sim_history_label(summary: dict) -> str:
  rid = summary.get("run_id") or "?"
  when = str(summary.get("updated_at") or summary.get("started_at") or "")[:19].replace("T", " ")
  d0 = summary.get("date_from") or "?"
  d1 = summary.get("date_to") or "?"
  n = summary.get("n_fills")
  if n is None:
    n = "?"
  total_r = summary.get("total_r")
  r_txt = f"{float(total_r):+.1f}R" if total_r is not None else "—"
  status = summary.get("status") or "?"
  tag = " · latest" if summary.get("is_latest") else ""
  return f"{when} · `{rid}` · {d0}→{d1} · {n} fills · {r_txt} · {status}{tag}"


def _sim_viewing_archive() -> tuple[bool, dict | None]:
  """Whether Simulate UI is showing an archived run (not live bridge_sim)."""
  if _bridge_mode() != "sim":
    return False, None
  token = st.session_state.get("sim_history_run_id") or "__live__"
  if token in ("__live__", "", None):
    return False, None
  try:
    from mt5_bridge.sim_history import load_sim_run
    meta = load_sim_run(str(token))
  except Exception:
    return False, None
  return (True, meta) if meta else (False, None)


def _active_bridge_dir():
  """Live EA I/O directory (desk / chart / history test)."""
  from mt5_bridge.protocol import resolve_live_bridge_dir
  return resolve_live_bridge_dir()


def _sim_stats_bridge_dir():
  """Trades source for Simulate stats/monitor — live or archived run."""
  from mt5_bridge.protocol import resolve_live_bridge_dir, resolve_sim_bridge_dir
  if _bridge_mode() != "sim":
    return resolve_live_bridge_dir()
  viewing, meta = _sim_viewing_archive()
  if viewing and meta and meta.get("run_id"):
    from mt5_bridge.sim_history import archived_trades_dir
    return archived_trades_dir(str(meta["run_id"]))
  return resolve_sim_bridge_dir()


def _mode_label() -> str:
  return "Test lịch sử" if _bridge_mode() == "sim" else "Live"


def _render_conditions_alignment(
  *,
  active: dict | None,
  decision: dict,
  file_status: dict,
  detailed: bool = False,
) -> None:
  """Show Bridge remine fp khớp roster Trade Models (multi-model aware)."""
  from gui.trade_model import (
    format_model_short,
    get_bridge_runtime_model_ids,
    get_model_by_id,
  )
  from mt5_bridge.models import (
    conditions_fingerprint,
    describe_strategy_conditions,
    get_model_run_params,
  )
  from mt5_bridge.protocol import normalize_model_ids

  roster_ids = normalize_model_ids(
    file_status.get("model_ids") or get_bridge_runtime_model_ids(),
    fallback=(active or {}).get("id"),
  )
  per = file_status.get("per_model") if isinstance(file_status.get("per_model"), dict) else {}

  def _fp_for_model(m: dict | None, mid: str) -> str | None:
    if not m:
      return None
    params = get_model_run_params(m, mid)
    return conditions_fingerprint(params)

  # Multi-model: verify each roster slot (not “active” vs primary root fp)
  if len(roster_ids) > 1:
    rows = []
    n_match = n_miss = n_skip = 0
    for mid in roster_ids:
      m = get_model_by_id(mid)
      expect = _fp_for_model(m, mid)
      slot = per.get(mid) if isinstance(per.get(mid), dict) else {}
      live = (
        (slot or {}).get("conditions_fp")
        or (decision.get("conditions_fp") if decision.get("model_id") == mid else None)
      )
      if expect and live and str(live) == str(expect):
        state = "match"
        n_match += 1
      elif expect and live:
        state = "mismatch"
        n_miss += 1
      else:
        state = "unknown"
        n_skip += 1
      rows.append({
        "Model": format_model_short(m, max_len=36) if m else mid[:28],
        "State": state,
        "Expect": (str(expect)[:10] + "…") if expect else "—",
        "Bridge": (str(live)[:10] + "…") if live else "—",
      })

    if not detailed:
      if n_miss:
        st.warning(
          f"Bridge lệch **{n_miss}/{len(roster_ids)}** model — "
          "Stop rồi Start lại feed/service để đồng bộ."
        )
      elif n_match == len(roster_ids):
        st.success(f"Bridge khớp **{len(roster_ids)}** Trade Model trong roster.")
      else:
        st.caption(
          f"Chưa xác nhận đủ fp ({n_match} khớp · {n_skip} chờ) — "
          "Start feed / đợi decision mới."
        )
      return

    st.caption(f"Roster Bridge · {len(roster_ids)} model · kiểm tra `conditions_fp` từng slot")
    import pandas as pd
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    if n_miss:
      st.warning("Có model lệch fp — Stop/Start Live hoặc test lịch sử để nạp lại roster.")
    elif n_match == len(roster_ids):
      st.success("Mọi model trong roster khớp điều kiện remine / Health.")
    else:
      st.info("Một số slot chưa có fp — đợi Bridge decide.")
    return

  # Single-model: compare against roster primary (or active)
  mid = roster_ids[0] if roster_ids else (active or {}).get("id")
  model = get_model_by_id(mid) if mid else active
  if not model:
    st.caption("Chưa chọn Trade Model.")
    return

  model_params = get_model_run_params(model, mid or model.get("id"))
  model_desc = describe_strategy_conditions(model_params)
  model_fp = model_desc["conditions_fp"]
  slot = per.get(str(mid)) if mid and isinstance(per.get(str(mid)), dict) else {}
  live_fp = (
    (slot or {}).get("conditions_fp")
    or decision.get("conditions_fp")
    or file_status.get("conditions_fp")
  )
  live_desc = file_status.get("run_conditions") or decision.get("run_conditions") or {}

  match_state = "unknown"
  if live_fp and live_fp != model_fp:
    match_state = "mismatch"
  elif live_fp:
    match_state = "match"
  elif live_desc:
    live_check = conditions_fingerprint({
      **model_params,
      **{k: live_desc.get(k) for k in (
        "train_weeks", "kb_profile", "kb_snapshot", "feature_profile",
        "spread_pips", "slippage_pips", "use_learning",
      ) if live_desc.get(k) is not None},
      "mining_search_space": model.get("mining_search_space"),
      "trade_model_id": model.get("id"),
    })
    match_state = "match" if live_check == model_fp else "unknown"

  if not detailed:
    if match_state == "match":
      st.success("Bridge khớp Trade Model đang chọn.")
    elif match_state == "mismatch":
      st.warning("Bridge lệch Trade Model — Stop rồi Start lại service để đồng bộ.")
    else:
      st.caption("Chưa xác nhận khớp model — Start service / đợi tín hiệu mới.")
    return

  ss = model.get("mining_search_space") or {}
  st.caption(
    f"Điều kiện remine (= báo cáo OOS): train **{model_desc.get('train_weeks')}w** · "
    f"KB `{model_desc.get('kb_profile')}@ep{model_desc.get('kb_snapshot')}` · "
    f"session `{ss.get('session_ranges')}` · spacing `{ss.get('min_bars_between')}` · "
    f"hold `{ss.get('max_hold_bars')}` · "
    f"fill SpreadPoints nến · "
    f"fp `{model_fp}`"
  )
  if match_state == "mismatch":
    st.warning(
      f"Bridge đang chạy fp `{live_fp}` ≠ model `{model_fp}`. "
      "Stop/Start service để khớp lại với Trade Model / báo cáo OOS."
    )
  elif match_state == "match":
    st.success(f"Bridge khớp điều kiện model (fp `{live_fp or model_fp}`).")
  else:
    st.info("Chưa có decision/status mới — Start Bridge để xác nhận fp khớp báo cáo OOS.")


def _wait_side_caption(block: dict | None) -> str:
  from gui.signal_wait_ui import wait_side_caption
  return wait_side_caption(block)


def _render_signal_wait(*, file_status: dict | None = None, decision: dict | None = None) -> None:
  from gui.signal_wait_ui import render_signal_wait
  if file_status is None or decision is None:
    bridge_dir = _active_bridge_dir()
    file_status = file_status or read_json(status_path(bridge_dir)) or {}
    decision = decision or read_json(decision_path(bridge_dir)) or {}
  render_signal_wait(file_status=file_status, decision=decision)


@st.fragment(run_every=timedelta(seconds=5))
def _signal_wait_fragment() -> None:
  _render_signal_wait()


def _fmt_px(value) -> str:
  from gui.bridge_desk_stats import fmt_px
  return fmt_px(value)


def _unrealized_r(trade: dict, connection: dict) -> float | None:
  from gui.bridge_desk_stats import unrealized_r
  return unrealized_r(trade, connection)


def _parse_ui_date(val) -> date | None:
  if val is None or val == "":
    return None
  if isinstance(val, date):
    return val
  if hasattr(val, "date") and callable(getattr(val, "date", None)):
    try:
      return val.date()
    except Exception:
      pass
  s = str(val).strip().replace("/", "-").replace(".", "-")[:10]
  try:
    return date.fromisoformat(s)
  except Exception:
    return None


def _sim_feed_window() -> tuple[date | None, date | None]:
  """History Feed Từ/Đến — archive meta when viewing history, else widgets/sim_state."""
  viewing, meta = _sim_viewing_archive()
  if viewing and meta:
    d0 = _parse_ui_date(meta.get("date_from"))
    d1 = _parse_ui_date(meta.get("date_to"))
    if d0 and d1:
      return d0, d1
  d0 = _parse_ui_date(st.session_state.get("sim_ea_from"))
  d1 = _parse_ui_date(st.session_state.get("sim_ea_to"))
  if d0 and d1:
    return d0, d1
  try:
    from mt5_bridge.ea_simulator import load_sim_state
    sim = load_sim_state()
    d0 = d0 or _parse_ui_date(sim.get("date_from"))
    d1 = d1 or _parse_ui_date(sim.get("date_to") or sim.get("last_bar"))
  except Exception:
    pass
  return d0, d1


def _months_spanning(d0: date, d1: date) -> list[str]:
  """YYYY-MM labels from d0 through d1 inclusive."""
  if d1 < d0:
    d0, d1 = d1, d0
  months: list[str] = []
  y, m = d0.year, d0.month
  while (y, m) <= (d1.year, d1.month):
    months.append(f"{y:04d}-{m:02d}")
    m += 1
    if m > 12:
      m = 1
      y += 1
  return months


def _month_bounds(ym: str) -> tuple[date, date]:
  y, m = int(ym[:4]), int(ym[5:7])
  start = date(y, m, 1)
  if m == 12:
    end = date(y + 1, 1, 1) - timedelta(days=1)
  else:
    end = date(y, m + 1, 1) - timedelta(days=1)
  return start, end


def _open_trade(trades: list[dict]) -> dict | None:
  from gui.bridge_desk_stats import open_trade
  return open_trade(trades)


def _period_stats(trades: list[dict], *, today: date) -> tuple[dict, dict]:
  from gui.bridge_desk_stats import period_stats
  return period_stats(trades, today=today)


def _render_error_banner(
  *,
  file_status: dict,
  service_status: dict,
  decision: dict,
  active_model_id: str | None,
) -> None:
  """Service/EA errors only — model lệch nằm trong Checklist sẵn sàng Live."""
  del decision, active_model_id  # kept in signature for call-site compatibility
  errors: list[str] = []
  if service_status.get("last_error"):
    errors.append(str(service_status["last_error"]))
  state = str(file_status.get("state") or "").lower()
  if state == "error" and file_status.get("error"):
    errors.append(str(file_status["error"]))
  if errors:
    st.error(" · ".join(dict.fromkeys(errors)))


def _render_trader_desk(*, include_live_metrics: bool = True) -> None:
  """Desk strip + banners + today/week PnL (refreshed by fragment).

  include_live_metrics=False (Simulate): skip Streamlit metric strip — FEED/Quote
  update smoothly inside the chart iframe instead (avoids 5s remount chop).
  """
  bridge_dir = _active_bridge_dir()
  mode = _bridge_mode()
  connection = read_json(connection_path(bridge_dir)) or {}
  decision = read_json(decision_path(bridge_dir)) or {}
  file_status = read_json(status_path(bridge_dir)) or {}
  service_status = bridge_bg.get_status() if mode == "live" else bridge_bg.get_sim_status()
  active = get_active_trade_model()
  active_id = (active or {}).get("id")
  trades = load_trades(bridge_dir)
  stale = 30.0 if mode == "sim" else 10.0
  health = connection_health(connection, stale_after_seconds=stale, bridge_dir=bridge_dir)
  today = date.today()
  today_stats, week_stats = _period_stats(trades, today=today)

  _render_error_banner(
    file_status=file_status,
    service_status=service_status if mode == "live" else {},
    decision=decision,
    active_model_id=active_id,
  )

  if include_live_metrics:
    # --- 5-column trader strip ---
    c1, c2, c3, c4, c5 = st.columns(5)
    age = health.get("age_seconds")
    age_txt = f"{age:.0f}s" if age is not None else "—"
    ea_label = "FEED" if mode == "sim" else "EA"
    if mode == "sim":
      ea_st = str(service_status.get("ea_status") or "idle")
      bars_done = int(service_status.get("bars_done") or 0)
      ea_feeding = ea_st == "running" or bars_done > 0
      if health.get("online") and ea_feeding:
        c1.metric(ea_label, f"ONLINE · {age_txt}")
      elif service_status.get("running") and not ea_feeding:
        c1.metric(ea_label, f"CHỜ EA · {age_txt}")
        c1.caption("App đã Start — chờ EA CopyRates")
      elif health.get("online"):
        c1.metric(ea_label, f"EA OK · {age_txt}")
        c1.caption("EA Live online · chưa Start test")
      else:
        c1.metric(ea_label, f"OFFLINE · {age_txt}")
    elif health.get("online"):
      c1.metric(ea_label, f"ONLINE · {age_txt}")
    elif health.get("waiting"):
      c1.metric(ea_label, f"WAIT · {age_txt}")
      c1.caption("EA chờ App decision")
    else:
      c1.metric(ea_label, f"OFFLINE · {age_txt}")

    bid, ask = connection.get("bid"), connection.get("ask")
    spread = connection.get("spread_points")
    if bid is not None and ask is not None:
      c2.metric("Quote", f"{_fmt_px(bid)} / {_fmt_px(ask)}")
    else:
      c2.metric("Quote", "—")
    c2.caption(f"Spread: {spread if spread is not None else '—'} pts")

    if mode == "sim":
      ea_st = service_status.get("ea_status") or "—"
      c3.metric("Feed", str(service_status.get("status") or "idle").upper())
      c3.caption(
        f"EA `{ea_st}` · {service_status.get('bars_done') or 0}/"
        f"{service_status.get('bars_total') or '—'}"
      )
    else:
      algo_on = health.get("trade_allowed")
      c3.metric("Algo", "ON" if algo_on else "OFF")
      c3.caption(f"Acct {connection.get('account') or '—'}")

    action = str(decision.get("action") or service_status.get("last_action") or "—").upper()
    reason = str(decision.get("reason") or file_status.get("reason") or "—")
    c4.metric("Decision", action)
    c4.caption(reason[:48] if reason else "—")

    risk = decision.get("risk_pct")
    if risk is None:
      risk = service_status.get("risk_pct") or bridge_bg.load_config().get("risk_pct")
    slots = decision.get("slots_remaining")
    if slots is None:
      slots = "—"
    c5.metric("Risk / Slots", f"{float(risk):.1f}% · {slots}" if risk is not None else f"— · {slots}")
  else:
    action = str(decision.get("action") or service_status.get("last_action") or "—").upper()
    st.caption("FEED / Quote cập nhật trên chart · Decision / PnL refresh ~3s trên desk.")

  # Strategy line — trader facing
  strat = decision.get("strategy_name") or "đang chờ tín hiệu"
  week = decision.get("week_start") or "—"
  st.markdown(f"**Chiến lược tuần:** {strat}")
  st.caption(f"Tuần bắt đầu · {week}")
  _render_conditions_alignment(
    active=active,
    decision=decision,
    file_status=file_status,
    detailed=False,
  )
  if mode == "sim":
    st.caption(
      f"Feed · {str(service_status.get('status') or 'idle').upper()} · "
      f"tiến độ {service_status.get('bars_done') or 0}/{service_status.get('bars_total') or '—'}"
    )
  else:
    if service_status.get("running"):
      st.caption("Service · đang chạy")
    else:
      st.caption("Service · đang tắt")

  # --- Open position / pending SIGNAL ---
  open_trade = _open_trade(trades)
  if open_trade:
    ur = _unrealized_r(open_trade, connection)
    ur_txt = f"{ur:+.2f}R" if ur is not None else "—"
    direction = str(open_trade.get("direction") or open_trade.get("dir") or "?").upper()
    st.info(
      f"**Lệnh đang mở:** {direction} @ **{_fmt_px(open_trade.get('entry_px') or open_trade.get('entry'))}** · "
      f"SL **{_fmt_px(open_trade.get('sl'))}** · TP **{_fmt_px(open_trade.get('tp'))}** · "
      f"Ước tính **{ur_txt}**"
    )
  elif action in ("BUY", "SELL"):
    st.warning(
      f"**SIGNAL chờ:** {action} @ **{_fmt_px(decision.get('entry'))}** · "
      f"SL **{_fmt_px(decision.get('sl'))}** · TP **{_fmt_px(decision.get('tp'))}**"
    )

  # --- PnL Metrics (Auto / Trade Model only) ---
  p1, p2, p3, p4 = st.columns(4)
  if mode == "sim":
    sim_stats = compute_stats(filter_trades(trades, mode="auto"))
    p1.metric(
      "Sim R (auto)",
      f"{sim_stats['total_r']:+.2f}" if sim_stats["n_trades"] else "0.00",
    )
    p2.metric(
      "Sim Trades",
      f"{sim_stats['n_trades']} lệnh",
    )
    open_n = sum(
      1 for t in trades
      if str(t.get("status") or "").upper() == "OPEN" and trade_mode(t) == "auto"
    )
    open_manual = sum(
      1 for t in trades
      if str(t.get("status") or "").upper() == "OPEN" and trade_mode(t) == "manual"
    )
    p3.metric("Open auto", open_n)
    wr = sim_stats.get("win_rate_pct")
    p4.metric(
      "Sim WR (auto)",
      f"{wr}%" if wr is not None else "—",
    )
  else:
    p1.metric(
      "Today R (auto)",
      f"{today_stats['total_r']:+.2f}" if today_stats["n_trades"] else "0.00",
    )
    p2.metric(
      "Week R (auto)",
      f"{week_stats['total_r']:+.2f}" if week_stats["n_trades"] else "0.00",
    )
    open_n = sum(
      1 for t in trades
      if str(t.get("status") or "").upper() == "OPEN" and trade_mode(t) == "auto"
    )
    open_manual = sum(
      1 for t in trades
      if str(t.get("status") or "").upper() == "OPEN" and trade_mode(t) == "manual"
    )
    p3.metric("Open auto", open_n)
    wr = today_stats.get("win_rate_pct")
    p4.metric(
      "Today WR (auto)",
      f"{wr}%" if wr is not None else "—",
    )
  if open_manual:
    st.caption(f"Có **{open_manual}** lệnh mở thuộc mode sửa — không tính vào R auto.")


@st.fragment(run_every=timedelta(seconds=5))
def _trader_desk_fragment() -> None:
  """Refresh desk without rerunning the live chart iframe."""
  _render_trader_desk(include_live_metrics=True)


def _chart_server_healthy(url: str, bridge_dir=None) -> bool:
  from mt5_bridge.live_monitor_server import chart_server_matches_bridge

  try:
    port = int(str(url).rsplit(":", 1)[-1].split("/")[0])
  except (TypeError, ValueError):
    return False
  return chart_server_matches_bridge(
    port, bridge_dir or resolve_live_bridge_dir(),
  )


@st.fragment(run_every=timedelta(seconds=2))
def _live_chart_recover_fragment(max_bars: int) -> None:
  """After Stop→Start, chart server may lag; retry until ready then remount iframe.

  Do not st.rerun() on the first full-page pass. RerunException aborts the rest of
  Live Trade, so Reward / Kỹ thuật / Test lịch sử stay empty until a manual refresh.
  Arm on this pass, remount on the next fragment tick (~2s).
  """
  from mt5_bridge.live_monitor_server import ensure_chart_server

  port = desk_chart_port()
  ensure_chart_server(resolve_live_bridge_dir(), port)
  if _chart_server_healthy(f"http://127.0.0.1:{port}", resolve_live_bridge_dir()):
    if st.session_state.get("_live_chart_recovered"):
      return
    if not st.session_state.get("_live_chart_recover_armed"):
      st.session_state["_live_chart_recover_armed"] = True
      return
    st.session_state["_live_chart_recovered"] = True
    st.rerun()
  else:
    st.session_state["_live_chart_recovered"] = False
    st.session_state["_live_chart_recover_armed"] = False
    st.caption("Đang chờ Live chart server…")


def _render_live_chart(max_bars: int, *, model_id: str | None = None) -> None:
  """Live chart from the desk bridge folder (history replay writes the same folder)."""
  from urllib.parse import quote

  from mt5_bridge.live_monitor_server import prepare_live_chart_trades

  bridge_dir = _active_bridge_dir()
  legend = "🟢 reward · 🔴 risk · 🔔 SIGNAL · ▲▼ ENTRY · ✕ exit — overlay giống Compare/Sim."
  if model_id is None and len(_live_roster_model_ids()) > 1:
    legend = "▲▼ ENTRY màu theo model · ✕ exit — chọn 1 model để xem SL/TP zone."
  port = desk_chart_port()
  monitor_url = f"http://127.0.0.1:{port}"
  model_q = model_id or "all"

  from mt5_bridge.live_monitor_server import ensure_chart_server
  ensure_chart_server(resolve_live_bridge_dir(), port)
  server_ready = _chart_server_healthy(monitor_url, resolve_live_bridge_dir())
  # Iframe Plotly.react (pan + scrollZoom) — same UX as Compare. Snapshot is
  # Streamlit plotly_chart and remounts on rerun, so it feels sticky/laggy.
  # URL already filters by model=; do not gate iframe on model_id is None.
  use_iframe = server_ready
  if use_iframe:
    components.iframe(
      f"{monitor_url}/chart?bars={max_bars}&model={quote(model_q, safe='')}",
      height=700,
      scrolling=False,
    )
    st.caption(legend)
    return
  if not server_ready:
    st.warning(
      "Live chart server chưa khớp folder EA của desk này; đang dùng snapshot đúng desk."
    )
  frame, connection = load_ea_chart_data(max_bars=max_bars, bridge_dir=bridge_dir)
  roster_ids = _live_roster_model_ids()
  trades = prepare_live_chart_trades(
    load_trades(bridge_dir),
    model_ids=roster_ids,
    model_filter=model_id,
    labels={mid: _legend_model_label(mid) for mid in roster_ids},
  )
  sym = str((connection or {}).get("symbol") or "").strip().upper() or _desk_symbol()
  live_chart_title = f"{sym} {tf_label()} · XM MT5 live"
  if model_id:
    live_chart_title += f" · {_legend_model_label(model_id)}"
  fig = build_ea_chart(frame, connection, trades, title=live_chart_title)
  if fig is None:
    st.caption("Đang chờ EA gửi nến để vẽ chart.")
  else:
    fig.update_layout(dragmode="pan")
    show_plotly(
      fig,
      live_chart_title,
      key="mt5_ea_live_chart",
      config={"scrollZoom": True, "displaylogo": False},
    )
    st.caption(legend)
  # Poll for iframe remount only while waiting for the all-models chart server.
  # (Calling this when a single model is selected would still abort later tabs.)
  if (
    (not server_ready)
    and model_id is None
    and bool(bridge_bg.get_status().get("running"))
  ):
    _live_chart_recover_fragment(max_bars)


def _render_manual_test_orders(*, show_json: bool = True) -> None:
  """Immediate BUY/SELL/CLOSE via command.json — verify EA bridge without waiting for bar close."""
  st.markdown("##### Lệnh thử (market)")
  st.caption(
    "Gửi lệnh market ngay trên tài khoản MT5 đang gắn EA — dùng để kiểm tra kết nối."
  )
  connection = read_json(connection_path()) or {}
  bar = read_json(bar_path()) or {}
  bid, ask = connection.get("bid"), connection.get("ask")
  digits = bar.get("digits") if isinstance(bar, dict) else None
  point = bar.get("point") if isinstance(bar, dict) else None
  pip = pip_size_from_quotes(
    digits=int(digits) if digits is not None else None,
    point=float(point) if point is not None else None,
  )

  c1, c2, c3 = st.columns(3)
  sl_pips = c1.number_input("SL (pips)", 1.0, 200.0, 20.0, step=1.0, key="mt5_test_sl_pips")
  tp_pips = c2.number_input("TP (pips)", 1.0, 400.0, 40.0, step=1.0, key="mt5_test_tp_pips")
  if bid is not None and ask is not None:
    c3.metric("Quote", f"{_fmt_px(bid)} / {_fmt_px(ask)}")
  else:
    c3.warning("Chưa có giá — EA offline?")

  confirm = st.checkbox(
    "Tôi hiểu đây là lệnh market thật/demo trên MT5",
    key="mt5_test_confirm",
  )
  b1, b2, b3 = st.columns(3)

  def _send_market(action: str) -> None:
    if bid is None or ask is None:
      st.error("Không có quote từ EA.")
      return
    _entry, sl, tp = prices_from_pips(
      action, bid=float(bid), ask=float(ask),
      sl_pips=float(sl_pips), tp_pips=float(tp_pips), pip_size=pip,
    )
    payload = write_manual_market_command(action, sl=sl, tp=tp)
    append_event(
      "app_to_ea",
      "manual_command",
      payload=payload,
      summary=f"test {action} sl={sl} tp={tp} sid={payload.get('signal_id')}",
    )
    st.success(f"Đã gửi {action}")
    st.session_state["mt5_last_test_cmd"] = payload

  if b1.button("BUY market", type="primary", use_container_width=True, disabled=not confirm):
    _send_market("BUY")
  if b2.button("SELL market", use_container_width=True, disabled=not confirm):
    _send_market("SELL")
  if b3.button("CLOSE all", use_container_width=True, disabled=not confirm):
    payload = write_manual_close_command()
    append_event(
      "app_to_ea",
      "manual_command",
      payload=payload,
      summary=f"test CLOSE sid={payload.get('signal_id')}",
    )
    st.success("Đã gửi CLOSE")
    st.session_state["mt5_last_test_cmd"] = payload

  if show_json:
    last = st.session_state.get("mt5_last_test_cmd")
    pending = read_json(command_path())
    ack = read_json(command_ack_path()) or {}
    fill = read_json(fill_path()) or {}
    a1, a2, a3 = st.columns(3)
    with a1:
      st.markdown("**command gửi**")
      st.json(last or pending or {"_": "chưa gửi"})
    with a2:
      st.markdown("**command_ack**")
      st.json(ack or {"_": "chưa có ack"})
    with a3:
      st.markdown("**fill gần nhất**")
      st.json(fill or {"_": "chưa có fill"})


def _render_live_deploy() -> None:
  from gui.mt5_deploy_ui import ea_live_name, rerun_app, start_deploy_mode_async
  st.markdown("##### Triển khai EA Live (riêng)")
  st.caption(f"Chỉ `{ea_live_name()}` · folder `{bridge_dir_display()}`.")
  result = st.session_state.pop("_tech_deploy_result", None)
  if result:
    code, out, err = result
    if code == 0:
      st.success("Triển khai Live thành công!")
      st.code(out)
    else:
      st.error(f"Lỗi khi triển khai (Mã lỗi: {code}):")
      st.code(err + "\n" + out)
  if st.button(
    "Deploy Live only",
    icon=":material/settings_suggest:",
    use_container_width=True,
    key="mt5_live_deploy",
    disabled=bool(st.session_state.get("_deploy_job")),
  ):
    try:
      job = start_deploy_mode_async("Live", enable_trading=True)
    except Exception as e:
      st.error(f"Lỗi: {e}")
      return
    st.session_state["_deploy_job"] = {**job, "start_bridge": False, "sidebar": True}
    rerun_app()


def _render_risk_controls() -> None:
  """Risk % + loss guard (Start/Stop chỉ ở tab Now)."""
  from mt5_bridge.loss_guard import (
    default_streak_limit_from_model,
    loss_guard_status,
  )

  cfg = bridge_bg.load_config()
  status = bridge_bg.get_status()
  _, _, by_id = _bridge_model_options()
  model_ids = normalize_model_ids(cfg.get("model_ids"), fallback=cfg.get("model_id"))
  if not model_ids:
    model_ids = _selected_bridge_model_ids()
  primary_id = model_ids[0] if model_ids else (
    (get_active_trade_model() or {}).get("id") or DEFAULT_MODEL_ID
  )
  active_model = by_id.get(primary_id) or get_active_trade_model()
  running = bool(status.get("running"))

  suggested = default_streak_limit_from_model(active_model)

  st.subheader("Risk control")
  if not model_ids:
    st.warning("Chưa chọn Trade Model — mở tab **Trade Models**.")

  st.session_state.setdefault("mt5_risk_pct", float(cfg.get("risk_pct", 1.0)))
  st.session_state.setdefault(
    "mt5_loss_guard_enabled", bool(cfg.get("loss_guard_enabled", True)),
  )

  prev_mid = st.session_state.get("_mt5_loss_guard_model_id")
  day_lim, week_lim, reset_for_model = resolve_loss_guard_limits(
    prev_model_id=prev_mid,
    model_id=str(primary_id),
    cfg_max_day=cfg.get("loss_guard_max_day"),
    cfg_max_week=cfg.get("loss_guard_max_week"),
    suggested=suggested,
  )
  st.session_state["_mt5_loss_guard_model_id"] = primary_id
  if reset_for_model:
    st.session_state["mt5_loss_guard_max_day"] = day_lim
    st.session_state["mt5_loss_guard_max_week"] = week_lim
    bridge_bg.save_config(
      loss_guard_max_day=day_lim,
      loss_guard_max_week=week_lim,
    )
  else:
    st.session_state.setdefault("mt5_loss_guard_max_day", day_lim)
    st.session_state.setdefault("mt5_loss_guard_max_week", week_lim)

  risk = st.number_input(
    "Risk % / lệnh (chung mọi model · Live & test lịch sử)",
    0.1, 5.0, step=0.1,
    key="mt5_risk_pct",
    disabled=running,
    on_change=_save_bridge_runtime_settings,
  )
  n_sel = max(1, len(model_ids))
  st.caption(
    f"**{n_sel}** model · nếu tất cả cùng mở → rủi ro ≈ **{float(risk) * n_sel:.1f}%** balance · "
    "cần tài khoản **hedging**."
  )
  if running:
    st.info("Live hoặc test lịch sử đang chạy — Stop trước khi đổi Risk %.")

  from mt5_bridge.history_sync import utc_to_broker_time
  from mt5_bridge.risk_limits import journal_day_trade_count, model_default_max_trades

  st.markdown("##### Max lệnh / model / ngày")
  st.caption(
    "Giới hạn số lệnh auto mỗi ngày (broker day). Đạt ngưỡng → engine FLAT "
    "(`no_slots`). Ghi đè giá trị Trade Model khi Live."
  )
  by_cfg = dict(cfg.get("max_trades_per_day_by_model") or {})
  bdir = resolve_live_bridge_dir()
  broker_day = utc_to_broker_time(pd.Timestamp.now("UTC")).date()
  for mid in model_ids:
    m = by_id.get(mid) or {}
    label = format_model_label(m) if m else str(mid)
    default_val = int(by_cfg.get(mid, model_default_max_trades(m)))
    wkey = f"mt5_max_trades_{mid}"
    st.session_state.setdefault(wkey, default_val)
    c1, c2 = st.columns([3, 2])
    with c1:
      st.number_input(
        f"Max / ngày — {label}",
        min_value=1, max_value=20, step=1,
        key=wkey,
        disabled=running,
        on_change=_save_bridge_runtime_settings,
        help=(
          f"Mặc định Trade Model: {model_default_max_trades(m)}. "
          "Đếm từ journal (OPEN + CLOSED hôm nay)."
        ),
      )
    with c2:
      taken = journal_day_trade_count(bdir, broker_day, model_id=mid) if bdir else 0
      max_show = int(st.session_state.get(wkey, default_val))
      st.metric("Hôm nay", f"{taken}/{max_show}")

  st.checkbox(
    "Loss guard (thua liên tiếp → FLAT + Stop)",
    key="mt5_loss_guard_enabled",
    on_change=_save_bridge_runtime_settings,
    help=(
      "Đếm chuỗi LOSS auto (ngày / tuần ISO). Chạm ngưỡng → FLAT mọi model + Stop. "
      f"Gợi ý mặc định ≈ ⌊|Max DD|⌋+1 = **{suggested}**."
    ),
  )
  g1, g2 = st.columns(2)
  with g1:
    st.number_input(
      "Max thua / ngày",
      min_value=0, max_value=40, step=1,
      key="mt5_loss_guard_max_day",
      on_change=_save_bridge_runtime_settings,
      help=f"0 = tắt. Gợi ý = {suggested}.",
    )
  with g2:
    st.number_input(
      "Max thua / tuần",
      min_value=0, max_value=40, step=1,
      key="mt5_loss_guard_max_week",
      on_change=_save_bridge_runtime_settings,
      help=f"0 = tắt (ISO Mon–Sun). Gợi ý = {suggested}.",
    )

  guard = loss_guard_status(cfg, bridge_dir=resolve_live_bridge_dir())
  if guard.get("tripped"):
    st.error(
      f"Loss guard đã dừng service lúc `{guard.get('tripped_at') or '—'}` — "
      f"{guard.get('tripped_reason') or ''}"
    )


def _render_live_advanced_controls() -> None:
  """Poll / 1-bar / paths — chỉ trong panel Kỹ thuật."""
  cfg = bridge_bg.load_config()
  status = bridge_bg.get_status()
  active_model = get_active_trade_model()
  model_id = (active_model or {}).get("id") or DEFAULT_MODEL_ID
  st.session_state.setdefault("mt5_risk_pct", float(cfg.get("risk_pct", 1.0)))
  st.session_state.setdefault("mt5_poll_sec", float(cfg.get("poll_sec", 2.0)))
  risk = float(st.session_state.get("mt5_risk_pct", 1.0))
  poll = st.number_input(
    "Poll (giây)", 0.5, 30.0, step=0.5, key="mt5_poll_sec",
    on_change=_save_bridge_runtime_settings,
  )
  st.caption(
    f"Bridge dir: `{bridge_dir_display()}` · model `{model_id}` · "
    f"runtime `{status.get('runtime_mode') or 'off'}` · "
    f"pid `{status.get('service_pid') or '—'}`"
  )
  st.caption("`results/mt5_bridge_service.log` · `results/mt5_bridge_service.pid`")
  if st.button(
    "1 bar",
    icon=":material/bolt:",
    use_container_width=True,
    help="Xử lý 1 bar ngay",
    key="mt5_live_svc_once",
  ):
    bridge_bg.save_config(model_id=model_id, risk_pct=risk, poll_sec=poll)
    with st.spinner("Decide…"):
      dec = bridge_bg.process_once_now()
    st.write(dec)
    st.rerun()
  _render_live_deploy()


def _render_history_sync() -> None:
  history = get_history_status()
  history_data = history.get("data") or {}
  received = int(history.get("received_bars") or 0)
  available = int(history.get("available_bars") or 0)
  h1, h2 = st.columns([4, 1])
  with h1:
    if history.get("state") in ("requesting", "receiving"):
      st.progress(
        received / max(available, 1),
        text=f"Đồng bộ lịch sử MT5: {received}/{available or '?'} nến {tf_label()}",
      )
    elif history_data.get("bars"):
      st.caption(
        f"MT5 history: **{history_data.get('bars')} nến** · "
        f"{str(history_data.get('start'))[:10]} → {str(history_data.get('end'))[:16]} · "
        f"{history_data.get('broker') or '?'}"
      )
    else:
      st.warning("Chưa có lịch sử MT5 để train / tín hiệu.")
  with h2:
    if st.button("Đồng bộ history", key="mt5_history_sync", use_container_width=True):
      start_history_sync(force=True)
      st.rerun()


@st.fragment(run_every=timedelta(seconds=2))
def _render_sim_progress_fragment() -> None:
  """Auto status/progress + Pause/Stop while feed runs (no full-page Refresh needed)."""
  try:
    # Bust short status cache so each fragment tick sees fresh sim_control
    if hasattr(bridge_bg.get_sim_status, "_cache"):
      bridge_bg.get_sim_status._cache = None
    sim = bridge_bg.get_sim_status()
  except Exception as e:
    st.warning(f"Không đọc được sim status: {e}")
    return
  running = bool(sim.get("running"))

  # Remount Start/Stop parent only when run-state flips — debounce to avoid
  # full-page refresh storms that make Simulate feel “treo”.
  prev_run = bool(st.session_state.get("_sim_ui_was_running"))
  if prev_run != running:
    import time as _time
    last = float(st.session_state.get("_sim_ui_flip_ts") or 0.0)
    now = _time.time()
    if (now - last) >= 1.5:
      st.session_state["_sim_ui_was_running"] = running
      st.session_state["_sim_ui_flip_ts"] = now
      st.rerun()

  # Model chọn ở tab Trade Models — chỉ hiện progress feed khi chạy
  if running:
    ea_st = str(sim.get("ea_status") or "idle")
    bars_done = int(sim.get("bars_done") or 0)
    bars_total = sim.get("bars_total") or "—"
    st.caption(
      f"{str(sim.get('status') or 'running').upper()}"
      + (" · tạm dừng" if sim.get("paused") else "")
      + f" · EA `{ea_st}` · {bars_done}/{bars_total} nến"
      + " — lệnh/chart xem ở **Live**"
    )
    if ea_st in ("", "idle") and bars_done == 0 and not sim.get("error"):
      st.warning(
        "Đang chờ EA History Feed… Nếu EA chưa gắn chart / sai folder, "
        "App sẽ tự dừng sau ~25s kèm thông báo lỗi."
      )
  if sim.get("error"):
    st.error(sim["error"])

  try:
    prog = float(sim.get("progress") or 0)
  except (TypeError, ValueError):
    prog = 0.0
  if sim.get("bars_total"):
    st.progress(min(1.0, max(0.0, prog)))

  b2, b3 = st.columns(2)
  if b2.button(
    "Pause" if not sim.get("paused") else "Resume",
    icon=":material/pause:",
    disabled=not running, use_container_width=True, key="sim_ea_pause",
  ):
    bridge_bg.pause_sim_worker(not bool(sim.get("paused")))
    st.rerun()
  if b3.button(
    "Stop", icon=":material/stop:",
    disabled=not running, use_container_width=True, key="sim_ea_stop",
  ):
    bridge_bg.stop_sim_worker()
    st.rerun()


def _render_simulate_ea() -> None:
  """App controls EA HISTORY_FEED (from/to/delay); EA sends bar/fill via bridge_sim."""
  from datetime import date as date_cls

  _, _, by_id = _bridge_model_options()
  cfg = bridge_bg.load_config()
  model_ids = normalize_model_ids(cfg.get("model_ids"), fallback=cfg.get("model_id"))
  if not model_ids:
    model_ids = _selected_bridge_model_ids()
  primary = by_id.get(model_ids[0]) if model_ids else get_active_trade_model()

  sim = bridge_bg.get_sim_status()
  running = bool(sim.get("running"))

  st.caption(
    "Chỉ nhập khoảng thời gian. App ghi `sim_control.json` → EA CopyRates → "
    "bar/fill vào **cùng folder Live**. Chart, lệnh, thống kê xem tab **Thống kê** / **Biểu đồ** "
    "(Live không biết đang replay)."
  )
  if not model_ids:
    st.warning("Chưa chọn Trade Model — mở tab **Trade Models**.")

  st.session_state.setdefault(
    "mt5_risk_pct", float(cfg.get("risk_pct", 1.0)),
  )
  risk = float(st.session_state.get("mt5_risk_pct", cfg.get("risk_pct", 1.0)))

  default_from = date_cls.fromisoformat(
    str((primary or {}).get("oos_from") or "2026-01-01")[:10]
  )
  default_to = date_cls.fromisoformat(
    str((primary or {}).get("oos_to") or "2026-01-31")[:10]
  )
  if (default_to - default_from).days > 60:
    from datetime import timedelta as _td
    default_to = default_from + _td(days=14)

  # Persist like other tabs (ui_preferences.json) — survive refresh / app restart
  restore_widget(
    "sim_ea_from", default_from,
    preference_key="mt5.sim_from",
    decode=_parse_ui_date,
  )
  restore_widget(
    "sim_ea_to", default_to,
    preference_key="mt5.sim_to",
    decode=_parse_ui_date,
  )
  restore_widget(
    "sim_ea_delay", 100,
    preference_key="mt5.sim_delay",
    decode=lambda v: int(v),
  )
  # Sanitize after restore / code change (slider: min=10, step=10)
  try:
    if not isinstance(st.session_state["sim_ea_from"], date):
      st.session_state["sim_ea_from"] = _parse_ui_date(st.session_state["sim_ea_from"]) or default_from
    if not isinstance(st.session_state["sim_ea_to"], date):
      st.session_state["sim_ea_to"] = _parse_ui_date(st.session_state["sim_ea_to"]) or default_to
    delay_cur = int(st.session_state["sim_ea_delay"])
    if delay_cur < 10 or delay_cur > 2000 or delay_cur % 10 != 0:
      st.session_state["sim_ea_delay"] = max(10, min(2000, round(delay_cur / 10) * 10 or 100))
  except Exception:
    st.session_state["sim_ea_from"] = default_from
    st.session_state["sim_ea_to"] = default_to
    st.session_state["sim_ea_delay"] = 100

  def _persist_sim_ea_settings() -> None:
    set_preference("mt5.sim_from", st.session_state.get("sim_ea_from"))
    set_preference("mt5.sim_to", st.session_state.get("sim_ea_to"))
    try:
      set_preference("mt5.sim_delay", int(st.session_state.get("sim_ea_delay") or 100))
    except (TypeError, ValueError):
      set_preference("mt5.sim_delay", 100)
    set_preference("mt5.bridge_model_labels", st.session_state.get("mt5_bridge_models"))

  c1, c2 = st.columns(2)
  with c1:
    st.date_input(
      "Từ ngày",
      key="sim_ea_from",
      disabled=running,
      on_change=preference_callback("sim_ea_from", "mt5.sim_from"),
    )
  with c2:
    st.date_input(
      "Đến ngày",
      key="sim_ea_to",
      disabled=running,
      on_change=preference_callback("sim_ea_to", "mt5.sim_to"),
    )
  with st.expander("Tùy chọn", expanded=False):
    st.slider(
      "Delay giữa các bar (ms)",
      min_value=10,
      max_value=2000,
      step=10,
      key="sim_ea_delay",
      disabled=running,
      help="1000 = 1s. Tự lưu khi đổi.",
      on_change=preference_callback("sim_ea_delay", "mt5.sim_delay"),
    )

  # EA online? → Start feed; offline → Deploy EA Sim + Start feed
  _sim_conn = read_json(connection_path(BRIDGE_SIM_DIR)) or {}
  _sim_health = connection_health(
    _sim_conn, stale_after_seconds=15.0, bridge_dir=BRIDGE_SIM_DIR,
  )
  _ea_online = bool(_sim_health.get("online"))
  _start_label = "Start test lịch sử" if _ea_online else "Deploy Live EA + Start test"
  _start_icon = ":material/play_arrow:" if _ea_online else ":material/settings_suggest:"
  start_clicked = st.button(
    _start_label,
    type="primary",
    icon=_start_icon,
    disabled=running or not model_ids,
    use_container_width=True,
    key="sim_ea_start",
    help=(
      "EA Live đang online — chạy test from/to (fill giấy, không OrderSend)."
      if _ea_online else
      "EA Live offline — Deploy Live rồi Start test lịch sử trên cùng chart."
    ),
  )
  if _ea_online:
    _age = _sim_health.get("age_seconds")
    _age_txt = f"{_age:.0f}s" if _age is not None else "—"
    st.caption(f"EA Live online · heartbeat {_age_txt}")

  d_from = st.session_state["sim_ea_from"]
  d_to = st.session_state["sim_ea_to"]
  delay_ms = int(st.session_state["sim_ea_delay"])

  # Auto-refreshing progress fragment (only polls status — light)
  _render_sim_progress_fragment()

  if start_clicked:
    if d_to < d_from:
      st.error("Đến ngày phải ≥ Từ ngày")
    else:
      import time as _time
      ea_ready = _ea_online

      if not ea_ready:
        from gui.mt5_deploy_ui import deploy_ea_and_wait_online, ea_live_name
        if bridge_bg.is_sim_running():
          st.warning("Test lịch sử đang chạy — không Deploy lại. Dùng Stop rồi Start.")
        else:
          with st.spinner(f"Đang deploy `{ea_live_name()}` (tối đa ~90s)…"):
            ok_dep, detail = deploy_ea_and_wait_online(
              "Live",
              BRIDGE_DIR,
              skip_bridge_service=True,
              wait_sec=20.0,
              deploy_timeout_sec=90.0,
            )
          if not ok_dep:
            st.error(detail.split("\n", 1)[0])
            if "\n" in detail:
              st.code(detail.split("\n", 1)[1])
          else:
            st.toast(f"Đã deploy `{ea_live_name()}` · EA online")
            ea_ready = True

      if ea_ready:
        _persist_sim_ea_settings()
        bridge_bg.save_config(
          model_id=model_ids[0],
          model_ids=model_ids,
          risk_pct=float(risk),
        )
        ok = bridge_bg.start_sim_worker(
          date_from=str(d_from),
          date_to=str(d_to),
          delay_ms=int(delay_ms),
          model_id=model_ids[0],
          model_ids=model_ids,
          risk_pct=float(risk),
        )
        if ok:
          import time as _time
          if hasattr(bridge_bg.get_sim_status, "_cache"):
            bridge_bg.get_sim_status._cache = None
          _time.sleep(0.4)
          st2 = bridge_bg.get_sim_status()
          st.session_state["_sim_pending_history"] = "__live__"
          set_preference("mt5.sim_history_run_id", "__live__")
          st.success(
            f"Đã Start test · {len(model_ids)} model. "
            "Chuyển **Live** để xem chart, hit lệnh và thống kê (cùng folder; Live không biết replay)."
          )
          st.rerun()
        else:
          st.warning("Feed đang chạy")

  st.caption(
    "Xong hoặc đang chạy: mở **Live** — biểu đồ, hit lệnh và bảng thống kê. "
    "Trên Live chọn giai đoạn **Tất cả** nếu lọc Hôm nay trống (fill theo thời gian nến)."
  )


def _render_live_reward_all(
  detail_ids: list[str],
  *,
  bridge_dir=None,
  date_from=None,
  date_to=None,
) -> None:
  """Overlay weekly / monthly / equity for every roster model."""
  from gui.bridge_model_monitor import (
    LIVE_SERIES_COLOR,
    build_equity_series_figure,
    build_multi_model_equity_figure,
    build_multi_model_monthly_figure,
    build_multi_model_weekly_figure,
    load_live_auto_trades,
  )

  live_all = load_live_auto_trades(
    None,
    bridge_dir=bridge_dir,
    date_from=date_from,
    date_to=date_to,
    use_exit_time=True,
  )
  stats = live_all.get("stats") or {}
  live_n = int(stats.get("n_trades") or 0)
  m1, m2, m3, m4 = st.columns(4)
  m1.metric(
    "Total R",
    f"{stats.get('total_r'):+.1f}" if stats.get("total_r") is not None else "—",
  )
  m2.metric(
    "WR%",
    f"{stats.get('win_rate_pct')}%" if stats.get("win_rate_pct") is not None else "—",
  )
  m3.metric(
    "Max DD",
    f"{stats.get('max_drawdown_r')}R" if stats.get("max_drawdown_r") is not None else "—",
  )
  m4.metric("Trades", f"{live_n}")
  st.caption(f"Tổng **{len(detail_ids)}** model · lệnh auto đã đóng trên Bridge.")

  weekly_by: dict = {}
  monthly_by: dict = {}
  equity_by: dict = {}
  rows = []
  for mid in detail_ids:
    label = _legend_model_label(mid)
    live = load_live_auto_trades(
      mid,
      bridge_dir=bridge_dir,
      date_from=date_from,
      date_to=date_to,
      use_exit_time=True,
    )
    weekly_by[label] = live.get("weekly")
    monthly_by[label] = live.get("monthly")
    equity_by[label] = live.get("equity")
    stt = live.get("stats") or {}
    rows.append({
      "Model": label,
      "Đóng": stt.get("n_trades") or 0,
      "WR%": stt.get("win_rate_pct"),
      "Total R": stt.get("total_r"),
      "MaxDD": stt.get("max_drawdown_r"),
    })
  st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

  tw, th, tr = st.tabs([LABEL_CHART_WEEKLY, LABEL_CHART_MONTHLY, LABEL_CHART_EQUITY])
  with tw:
    fig_w = build_multi_model_weekly_figure(
      weekly_by, title="Tuần · tất cả model · Live Auto",
    )
    if fig_w:
      show_plotly(fig_w, "Tuần · tất cả model")
      st.caption("Gom theo tuần bắt đầu **thứ Hai** (cùng mốc remine).")
    else:
      st.info("Chưa có chuỗi tuần Live.")
  with th:
    fig_m = build_multi_model_monthly_figure(
      monthly_by, title="Tháng · tất cả model · Live Auto",
    )
    if fig_m:
      show_plotly(fig_m, "Tháng · tất cả model")
    else:
      st.info("Chưa có chuỗi tháng Live.")
  with tr:
    fig_e = build_multi_model_equity_figure(
      equity_by, title="Equity · tất cả model · Live Auto",
    )
    if fig_e:
      show_plotly(fig_e, "Equity · tất cả model")
    else:
      eq = build_equity_series_figure(
        live_all.get("equity"),
        title="Equity · Live Auto (gộp)",
        series_name="Live Auto",
        color=LIVE_SERIES_COLOR,
      )
      if eq:
        show_plotly(eq, "Equity · Live Auto (gộp)")
      else:
        st.info("Chưa có equity Live.")


def _render_model_monitor() -> None:
  """Theo dõi lệnh Live Auto trên Bridge — KPI, equity, theo tháng."""
  try:
    _render_model_monitor_body()
  except Exception as e:
    st.error(f"Không render được Theo dõi model: {e}")
    with st.expander("Chi tiết lỗi"):
      st.exception(e)


@st.fragment(run_every=timedelta(seconds=12))
def _model_monitor_auto_fragment() -> None:
  """Auto-refresh Theo dõi Live while Live service or Sim feed is running."""
  _render_model_monitor()


@st.fragment(run_every=timedelta(seconds=12))
def _stats_auto_fragment() -> None:
  """Auto-refresh Thống kê lệnh while feed/service is running."""
  _render_stats_section()


def _render_model_monitor_body() -> None:
  from gui.bridge_model_monitor import (
    LIVE_SERIES_COLOR,
    OOS_SERIES_COLOR,
    build_bt_vs_live_monthly_figure,
    build_equity_overlay_figure,
    build_equity_series_figure,
    build_monthly_series_figure,
    build_monitor_bundle,
    build_weekly_series_figure,
  )
  from gui.trade_model import (
    get_bridge_runtime_model_ids,
    get_model_by_id,
  )
  from mt5_bridge.ea_simulator import load_sim_state

  active = get_active_trade_model()
  source = "live"
  bridge_mids = get_bridge_runtime_model_ids()
  if not active and not bridge_mids:
    st.info("Chọn model trên roster Bridge để xem lệnh auto.")
    return

  sim_st = load_sim_state()
  date_from = date_to = None
  view_bridge = None
  if source == "sim":
    viewing, meta = _sim_viewing_archive()
    if viewing and meta:
      date_from = meta.get("date_from")
      date_to = meta.get("date_to")
      from mt5_bridge.sim_history import archived_trades_dir
      view_bridge = archived_trades_dir(str(meta["run_id"]))
    else:
      d0 = st.session_state.get("sim_ea_from")
      d1 = st.session_state.get("sim_ea_to")
      date_from = (
        d0.isoformat() if hasattr(d0, "isoformat") else None
      ) or sim_st.get("date_from") or None
      date_to = (
        d1.isoformat() if hasattr(d1, "isoformat") else None
      ) or sim_st.get("date_to") or None

  # Chọn Trade Model trên roster Bridge (Tất cả / từng model).

  detail_ids = bridge_mids if bridge_mids else (
    [str(active["id"])] if active and active.get("id") else []
  )
  if not detail_ids:
    return

  model_scope = _render_live_model_scope(
    widget_key=f"monitor_detail_mid_{source}",
    pref_key="mt5.reward_view_model",
  )
  if source == "live" and model_scope is None and len(detail_ids) > 1:
    _render_live_reward_all(
      detail_ids,
      bridge_dir=view_bridge,
      date_from=date_from,
      date_to=date_to,
    )
    return
  if model_scope:
    active = get_model_by_id(model_scope)
  elif not active:
    active = get_model_by_id(detail_ids[0])

  if not active:
    return

  bundle = build_monitor_bundle(
    active,
    source=source,
    date_from=date_from,
    date_to=date_to,
    bridge_dir=view_bridge,
  )
  live_label = bundle.get("live_label") or "Live Auto"
  if source == "sim" and date_from:
    st.caption(f"**{bundle['model_label']}** · cửa sổ sim {date_from} → {date_to}")
  elif len(detail_ids) <= 1:
    st.caption(f"**{bundle['model_label']}**")

  if not bundle["has_report"]:
    st.warning(
      f"Chưa có report backtest của model. Chạy **Trade Models → {LABEL_TAB_OOS}** "
      "(bật Chạy lại KB ON, đúng search space) rồi quay lại."
    )

  kpi = bundle["kpi"]
  live_n = int(kpi["live"].get("n_trades") or 0)

  # Live: chỉ Bridge auto — báo cáo OOS xem ở Trade Models → Đánh giá OOS.
  if source == "live":
    with st.expander(f"{live_label} · Bridge auto", expanded=True):
      lv = kpi["live"]
      assess = bundle["live_assess"]
      m1, m2, m3, m4 = st.columns(4)
      m1.metric("Total R", f"{lv.get('total_r'):+.1f}" if lv.get("total_r") is not None else "—")
      m2.metric("WR%", f"{lv.get('win_rate_pct')}%" if lv.get("win_rate_pct") is not None else "—")
      m3.metric("Max DD", f"{lv.get('max_drawdown_r')}R" if lv.get("max_drawdown_r") is not None else "—")
      m4.metric("Trades", f"{live_n}")
      verdict = assess.get("verdict")
      if live_n == 0:
        st.info(
          f"Chưa có lệnh **auto** đã đóng trên Bridge (`{bridge_file_display(None, 'trades.json')}`)."
        )
      elif live_n < 5:
        st.caption(f"{live_label} còn ít lệnh — chỉ theo dõi.")
      elif verdict == "degraded":
        st.error(assess.get("message") or "")
      elif verdict == "watch":
        st.warning(assess.get("message") or "")
      elif verdict == "stable":
        st.success(assess.get("message") or "")
      elif assess.get("message"):
        st.info(assess.get("message"))
      tw, th, tr = st.tabs([LABEL_CHART_WEEKLY, LABEL_CHART_MONTHLY, LABEL_CHART_EQUITY])
      with tw:
        live_weekly_title = f"Tuần · {live_label} · {bundle['model_label']}"
        fig_w = build_weekly_series_figure(
          bundle["live"].get("weekly"),
          title=live_weekly_title,
          series_name=live_label,
          color=LIVE_SERIES_COLOR,
        )
        if fig_w:
          show_plotly(fig_w, live_weekly_title)
          st.caption("Gom theo tuần bắt đầu **thứ Hai** (cùng mốc remine).")
        else:
          st.info(f"Chưa có chuỗi tuần {live_label}.")
      with th:
        live_monthly_title = f"Tháng · {live_label} · {bundle['model_label']}"
        fig = build_monthly_series_figure(
          bundle["live"]["monthly"],
          title=live_monthly_title,
          series_name=live_label,
          color=LIVE_SERIES_COLOR,
        )
        if fig:
          show_plotly(fig, live_monthly_title)
        else:
          st.info(f"Chưa có chuỗi tháng {live_label}.")
      with tr:
        live_equity_title = f"Equity · {live_label} · {bundle['model_label']}"
        eq = build_equity_series_figure(
          bundle["live"]["equity"],
          title=live_equity_title,
          series_name=live_label,
          color=LIVE_SERIES_COLOR,
        )
        if eq:
          show_plotly(eq, live_equity_title)
        else:
          st.info(f"Chưa có equity {live_label}.")
    return

  # Simulate: cùng cửa sổ lịch sử → giữ overlay Backtest vs Sim
  st.caption(
    f"Test lịch sử: KPI/biểu đồ đọc `{bridge_file_display(BRIDGE_SIM_DIR, 'trades.json')}` theo **entry_time** lịch sử "
    "(không dùng giờ tường lúc fill). Tự cập nhật ~12s khi feed chạy — xem trên **Live**."
  )
  tab_h, tab_r = st.tabs([LABEL_CHART_MONTHLY, LABEL_CHART_EQUITY])

  with tab_h:
    assess = bundle["live_assess"]
    m1, m2, m3, m4 = st.columns(4)
    bt_r = kpi["bt"].get("total_r")
    live_r = kpi["live"].get("total_r")
    m1.metric("Backtest OOS (full)", f"{bt_r:+.1f}R" if bt_r is not None else "—")
    m2.metric(f"{live_label}", f"{live_r:+.1f}R" if live_r is not None else "—")
    ov_e = bundle.get("overlap_edge")
    m3.metric(
      f"Edge {live_label}−BT (tháng trùng)",
      f"{ov_e:+.1f}R" if ov_e is not None else "—",
      help="Tổng R nguồn − backtest trên các tháng có cả hai chuỗi.",
    )
    verdict = assess.get("verdict")
    m4.metric(f"{live_label} verdict", verdict or "—")

    if live_n == 0:
      st.info(
        "Chưa có lệnh test lịch sử — Start test (from/to), rồi xem lệnh trên **Live**."
      )
    elif live_n < 5:
      st.caption(f"{live_label} còn ít lệnh — chỉ theo dõi, chưa đủ để kết luận suy giảm.")
    elif verdict == "degraded":
      st.error(assess.get("message") or "")
    elif verdict == "watch":
      st.warning(assess.get("message") or "")
    elif verdict == "stable":
      st.success(assess.get("message") or "")
    else:
      st.info(assess.get("message") or f"Chưa đủ tháng {live_label}.")

    if ov_e is not None and live_n >= 5:
      st.caption(
        "Edge gần 0 / cùng hướng với BT trên cửa sổ sim → protocol App↔EA "
        "và Trade Model khớp kỳ vọng train trên giai đoạn đó."
      )

    bt_vs_live_monthly_title = f"Tháng · Backtest vs {live_label} · {bundle['model_label']}"
    fig = build_bt_vs_live_monthly_figure(
      bundle["bt"]["monthly"],
      bundle["live"]["monthly"],
      title=bt_vs_live_monthly_title,
      live_name=live_label,
    )
    if fig:
      show_plotly(fig, bt_vs_live_monthly_title)
      st.caption(
        "Cùng trục tháng · nền/chú thích **xanh dương = Timeline OOS**, "
        f"**xanh ngọc = Timeline {live_label}** (khoảng tháng có dữ liệu từng nguồn)."
      )
    else:
      st.info("Chưa có chuỗi tháng để vẽ (cần report OOS và/hoặc lệnh live/sim).")

    aligned = bundle.get("aligned")
    if aligned is not None and not aligned.empty:
      st.dataframe(aligned, use_container_width=True, hide_index=True)

  with tab_r:
    c1, c2 = st.columns(2)
    with c1:
      st.markdown("**Backtest OOS**")
      b = kpi["bt"]
      r1, r2, r3 = st.columns(3)
      r1.metric("WR%", f"{b.get('win_rate_pct')}%" if b.get("win_rate_pct") is not None else "—")
      r2.metric("Total R", f"{b.get('total_r'):+.1f}" if b.get("total_r") is not None else "—")
      r3.metric("Max DD", f"{b.get('max_drawdown_r')}R" if b.get("max_drawdown_r") is not None else "—")
      st.caption(
        f"n={b.get('n_trades') or '—'} · avg "
        f"{b.get('avg_r') if b.get('avg_r') is not None else '—'}"
      )
    with c2:
      st.markdown(f"**{live_label}**")
      lv = kpi["live"]
      r1, r2, r3 = st.columns(3)
      r1.metric("WR%", f"{lv.get('win_rate_pct')}%" if lv.get("win_rate_pct") is not None else "—")
      r2.metric("Total R", f"{lv.get('total_r'):+.1f}" if lv.get("total_r") is not None else "—")
      r3.metric("Max DD", f"{lv.get('max_drawdown_r')}R" if lv.get("max_drawdown_r") is not None else "—")
      st.caption(
        f"n={lv.get('n_trades') or '—'} · avg "
        f"{lv.get('avg_r') if lv.get('avg_r') is not None else '—'}"
      )

    if live_n == 0:
      st.warning(
        f"Chưa có trade **{live_label}** — biểu đồ Rủi ro hiện chỉ **Backtest OOS**."
      )
    elif live_n < 5:
      st.caption("Mẫu đối chiếu nhỏ — so sánh rủi ro mang tính tham khảo.")

    eq_overlay_title = f"Equity · Backtest vs {live_label} · {bundle['model_label']}"
    eq_fig = build_equity_overlay_figure(
      bundle["bt"]["equity"],
      bundle["live"]["equity"],
      title=eq_overlay_title,
      live_name=live_label,
    )
    if eq_fig:
      show_plotly(eq_fig, eq_overlay_title)
      st.caption(
        "Cùng trục thời gian entry · nền/chú thích **xanh dương = OOS**, "
        f"**xanh ngọc = {live_label}**."
      )
      if live_n == 0:
        st.caption("Chỉ có đường Backtest — chưa có chuỗi equity đối chiếu.")
    else:
      st.info("Chưa đủ equity series để overlay.")

  with st.expander("Cách đọc Backtest vs test lịch sử"):
    st.markdown(
      "- **Backtest OOS** = report Trade Model (cùng điều kiện remine / Health).\n"
      f"- **Test lịch sử** = fill giấy từ `{bridge_dir_display(BRIDGE_SIM_DIR)}/` (cùng EA Live, không OrderSend).\n"
      "- Overlay cùng cửa sổ → Edge gần 0 nghĩa là model + App↔EA khớp.\n"
      "- Live mode xem **riêng** OOS vs Live (khác giai đoạn)."
    )


def _render_stats_section() -> None:
  """Thống kê lệnh — đọc lại trades.json mỗi lần gọi (không cache fragment)."""
  bridge_dir = _active_bridge_dir()
  mode = "live"
  st.subheader(f"Thống kê lệnh · {_mode_label()}")

  all_trades = load_trades(bridge_dir)
  today = date.today()
  sim_from, sim_to = _sim_feed_window() if mode == "sim" else (None, None)

  # Defaults for "Tùy chọn" pickers
  if mode == "sim" and sim_from and sim_to:
    default_from, default_to = sim_from, sim_to
  else:
    default_from = today - timedelta(days=30)
    default_to = today
    for t in all_trades:
      for key in ("entry_time", "exit_time"):
        try:
          ts = pd.Timestamp(t.get(key)).date()
          if ts < default_from:
            default_from = ts
        except Exception:
          pass

  p1, p2, p3 = st.columns([2, 1, 1])
  if mode == "sim":
    preset_options = [
      "Cửa sổ History Feed",
      "Tháng trong cửa sổ",
      "Tất cả lệnh",
      "Tùy chọn",
    ]
    default_preset = "Cửa sổ History Feed"
    pref_key = "mt5.sim_stats_preset"
    widget_key = "bridge_stats_preset_sim"
  else:
    preset_options = [
      "Hôm nay",
      "Tuần này (T2→nay)",
      "7 ngày",
      "30 ngày",
      "Tháng này",
      "Tất cả",
      "Tùy chọn",
    ]
    default_preset = "Tất cả"
    pref_key = "mt5.stats_preset_v2"
    widget_key = "bridge_stats_preset_live"

  restore_widget(
    widget_key, default_preset,
    preference_key=pref_key,
    options=preset_options,
  )
  # Migrate old live-relative presets saved under sim key
  cur = st.session_state.get(widget_key)
  if mode == "sim" and cur not in preset_options:
    st.session_state[widget_key] = default_preset

  preset = p1.selectbox(
    "Giai đoạn",
    preset_options,
    key=widget_key,
    on_change=preference_callback(widget_key, pref_key),
  )
  date_from = None
  date_to = None

  if mode == "sim":
    if preset == "Cửa sổ History Feed":
      date_from, date_to = sim_from, sim_to
      if not date_from or not date_to:
        st.warning("Chưa có Từ/Đến History Feed — chọn **Tùy chọn** hoặc Start feed.")
      else:
        p2.caption(f"Từ `{date_from}`")
        p3.caption(f"Đến `{date_to}`")
    elif preset == "Tháng trong cửa sổ":
      if sim_from and sim_to:
        months = _months_spanning(sim_from, sim_to)
      else:
        months = []
        for t in all_trades:
          et = _parse_ui_date(str(t.get("entry_time") or "")[:10].replace(".", "-"))
          if et:
            ym = f"{et.year:04d}-{et.month:02d}"
            if ym not in months:
              months.append(ym)
        months.sort()
      if not months:
        st.warning("Chưa xác định được tháng trong cửa sổ feed.")
        p2.caption("—")
        p3.caption("—")
      else:
        month_key = "bridge_stats_sim_month"
        restore_widget(
          month_key, months[0],
          preference_key="mt5.sim_stats_month",
          options=months,
        )
        if st.session_state.get(month_key) not in months:
          st.session_state[month_key] = months[0]
        ym = p2.selectbox(
          "Tháng",
          months,
          key=month_key,
          on_change=preference_callback(month_key, "mt5.sim_stats_month"),
        )
        date_from, date_to = _month_bounds(ym)
        # Clip to feed window when known
        if sim_from and date_from < sim_from:
          date_from = sim_from
        if sim_to and date_to > sim_to:
          date_to = sim_to
        p3.caption(f"`{date_from}` → `{date_to}`")
    elif preset == "Tùy chọn":
      restore_widget(
        "bridge_from_sim", default_from,
        preference_key="mt5.sim_date_from",
        decode=date.fromisoformat,
      )
      restore_widget(
        "bridge_to_sim", default_to,
        preference_key="mt5.sim_date_to",
        decode=date.fromisoformat,
      )
      date_from = p2.date_input(
        "Từ ngày", key="bridge_from_sim",
        on_change=preference_callback("bridge_from_sim", "mt5.sim_date_from"),
      )
      date_to = p3.date_input(
        "Đến ngày", key="bridge_to_sim",
        on_change=preference_callback("bridge_to_sim", "mt5.sim_date_to"),
      )
    else:
      # Tất cả lệnh
      p2.caption("Toàn bộ journal")
      p3.caption("—")
  else:
    if preset == "Hôm nay":
      date_from = date_to = today
    elif preset == "7 ngày":
      date_from, date_to = today - timedelta(days=6), today
    elif preset == "30 ngày":
      date_from, date_to = today - timedelta(days=29), today
    elif preset == "Tuần này (T2→nay)":
      date_from = today - timedelta(days=today.weekday())
      date_to = today
    elif preset == "Tháng này":
      date_from = today.replace(day=1)
      date_to = today
    elif preset == "Tùy chọn":
      restore_widget(
        "bridge_from", default_from,
        preference_key="mt5.date_from",
        decode=date.fromisoformat,
      )
      restore_widget(
        "bridge_to", default_to,
        preference_key="mt5.date_to",
        decode=date.fromisoformat,
      )
      date_from = p2.date_input(
        "Từ ngày", key="bridge_from",
        on_change=preference_callback("bridge_from", "mt5.date_from"),
      )
      date_to = p3.date_input(
        "Đến ngày", key="bridge_to",
        on_change=preference_callback("bridge_to", "mt5.date_to"),
      )
    else:
      p2.caption("—")
      p3.caption("—")

  if date_from and date_to and date_from > date_to:
    st.warning("Từ ngày > Đến ngày — đã đảo lại.")
    date_from, date_to = date_to, date_from

  period_trades = filter_trades(all_trades, date_from=date_from, date_to=date_to)
  n_auto = sum(1 for t in period_trades if trade_mode(t) == "auto")
  n_manual = sum(1 for t in period_trades if trade_mode(t) == "manual")
  if date_from or date_to:
    if mode == "sim":
      st.caption(
        f"Lọc: **{date_from or '…'} → {date_to or '…'}** · {n_auto} lệnh"
      )
    else:
      st.caption(
        f"Lọc: **{date_from or '…'} → {date_to or '…'}** · "
        f"{len(period_trades)} lệnh (auto {n_auto} · sửa {n_manual})"
      )
  elif mode == "sim":
    st.caption(f"Lọc: **tất cả lệnh journal** · {n_auto} lệnh")

  def _stats_block(label: str, mode: str | None, *, model_id: str | None = None) -> None:
    trades = filter_trades(
      all_trades, date_from=date_from, date_to=date_to, mode=mode, model_id=model_id,
    )
    stats = compute_stats(trades, mode=mode, model_id=model_id)
    st.markdown(f"**{label}** · {stats['n_filtered']} lệnh")
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    s1.metric("Đã đóng", stats["n_trades"])
    s2.metric("Đang mở", stats["n_open"])
    s3.metric("Thắng", stats["n_wins"])
    s4.metric("Thua", stats["n_losses"])
    s5.metric("WR %", stats["win_rate_pct"] if stats["win_rate_pct"] is not None else "—")
    s6.metric("Total R", f"{stats['total_r']:+.2f}" if stats["n_trades"] else "—")
    m2 = st.columns(3)
    m2[0].metric("Avg R", stats["avg_r"] if stats["avg_r"] is not None else "—")
    m2[1].metric("Max DD (R)", stats["max_drawdown_r"])
    m2[2].metric(
      "Profit ($)",
      stats["total_profit"] if stats["total_profit"] is not None else "—",
    )

  from gui.trade_model import format_model_label, get_bridge_runtime_model_ids, get_model_by_id
  bridge_mids = get_bridge_runtime_model_ids()

  if mode == "sim":
    _stats_block("Auto (tổng)", "auto")
  else:
    tab_auto, tab_manual, tab_all = st.tabs([
      f"Auto (review chiến lược) · {n_auto}",
      f"Lệnh sửa · {n_manual}",
      f"Tất cả · {len(period_trades)}",
    ])
    with tab_auto:
      _stats_block("Auto (tổng)", "auto")
    with tab_manual:
      _stats_block("Lệnh sửa", "manual")
    with tab_all:
      _stats_block("Tất cả", None)

  if len(bridge_mids) > 1:
    st.markdown("**Theo từng Trade Model (auto)**")
    rows = []
    for mid in bridge_mids:
      stt = compute_stats(
        filter_trades(
          all_trades, date_from=date_from, date_to=date_to, mode="auto", model_id=mid,
        ),
      )
      bm = get_model_by_id(mid)
      rows.append({
        "Model": format_model_label(bm) if bm else mid[:28],
        "Đóng": stt.get("n_trades") or 0,
        "Mở": stt.get("n_open") or 0,
        "WR%": stt.get("win_rate_pct"),
        "Total R": stt.get("total_r"),
        "MaxDD": stt.get("max_drawdown_r"),
        "Avg R": stt.get("avg_r"),
      })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    with st.expander("Chi tiết KPI từng model", expanded=False):
      for mid in bridge_mids:
        bm = get_model_by_id(mid)
        _stats_block(
          format_model_label(bm) if bm else mid[:28],
          "auto",
          model_id=mid,
        )

  tc1, tc2 = st.columns([1, 4])
  if tc1.button(
    "Xóa nhật ký lệnh",
    key="bridge_clear_trades",
    help=(
      "Xóa trades.json + fills log, và clean decision.json stale "
      "(strategy/week cũ). Không cần Start Live chỉ để sync tip — "
      "checklist chưa OK thì không khuyến khích Start."
    ),
  ):
    clear_trades(bridge_dir)
    st.toast("Đã xóa nhật ký + decision stale")
    st.rerun()
  if mode == "sim":
    n_open_now = sum(
      1 for t in all_trades if str(t.get("status") or "").upper() == "OPEN"
    )
    if n_open_now > 0 and tc2.button(
      f"Xóa {n_open_now} lệnh treo",
      key="bridge_sim_clear_ghosts",
      help="Đóng ghost OPEN (journal lệch EA paper) — tránh HOLD vĩnh viễn.",
    ):
      from mt5_bridge.trade_journal import close_ghost_journal_opens
      n = close_ghost_journal_opens(bridge_dir, reason="journal_desync")
      st.toast(f"Đã đóng {n} lệnh treo")
      st.rerun()
  restore_widget("bridge_show_open", True, preference_key="mt5.show_open")
  show_open = tc2.checkbox(
    "Hiện cả lệnh đang mở", key="bridge_show_open",
    on_change=preference_callback("bridge_show_open", "mt5.show_open"),
  )

  if mode == "sim":
    mode_filter = "auto"
  else:
    mode_options = ["Auto", "Lệnh sửa", "Tất cả"]
    restore_widget(
      "bridge_stats_table_mode", "Tất cả",
      preference_key="mt5.stats_table_mode",
      options=mode_options,
    )
    table_mode = st.radio(
      "Bảng lệnh theo mode",
      mode_options,
      horizontal=True,
      key="bridge_stats_table_mode",
      on_change=preference_callback("bridge_stats_table_mode", "mt5.stats_table_mode"),
    )
    mode_filter = {"Auto": "auto", "Lệnh sửa": "manual", "Tất cả": None}[table_mode]
  trades = filter_trades(all_trades, date_from=date_from, date_to=date_to, mode=mode_filter)
  view = trades if show_open else [t for t in trades if t.get("status") == "CLOSED"]
  view = list(reversed(view))
  if not view:
    st.info("Không có lệnh trong giai đoạn / mode đã chọn.")
  else:
    table = []
    for t in view:
      table.append({
        "model": (t.get("model_id") or "—")[:28],
        "mode": trade_mode(t),
        "status": t.get("status"),
        "result": t.get("result") or ("OPEN" if t.get("status") == "OPEN" else "—"),
        "dir": t.get("direction"),
        "entry_time": t.get("entry_time"),
        "exit_time": t.get("exit_time"),
        "entry": t.get("entry_px"),
        "exit": t.get("exit_px"),
        "sl": t.get("sl"),
        "sl₀": t.get("sl_initial"),
        "tp": t.get("tp"),
        "R": t.get("r"),
        "profit": t.get("profit"),
        "reason": t.get("reason"),
        "intervened": ",".join(t.get("interventions") or []) or "—",
        "ticket": t.get("ticket"),
        "signal_id": t.get("signal_id"),
        "strategy": t.get("strategy_name"),
      })
    st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)


def _render_snapshot_files() -> None:
  bridge_dir = _active_bridge_dir()
  st.markdown(f"##### Snapshot files · `{bridge_dir_display(bridge_dir)}`")
  t1, t2, t3, t4, t5, t6 = st.tabs([
    "connection.json",
    "bars.json",
    "bar.json",
    "decision.json",
    "command.json",
    "fill.json",
  ])
  with t1:
    st.json(read_json(connection_path(bridge_dir)) or {"_": "chưa có heartbeat"})
  with t2:
    bars = read_json(bars_path(bridge_dir)) or {}
    if isinstance(bars, dict) and bars.get("bars"):
      st.caption(f"{len(bars['bars'])} nến · cập nhật `{bars.get('updated_at', '—')}`")
      st.json({**bars, "bars": bars["bars"][-5:]})
    else:
      st.json({"_": "chưa có lịch sử nến"})
  with t3:
    st.json(read_json(bar_path(bridge_dir)) or {"_": "chưa có — EA chưa ghi bar"})
  with t4:
    st.json(read_json(decision_path(bridge_dir)) or {"_": "chưa có decision"})
  with t5:
    st.json({
      "command": read_json(command_path(bridge_dir)) or {"_": "trống"},
      "command_ack": read_json(command_ack_path(bridge_dir)) or {"_": "chưa có"},
    })
  with t6:
    st.json(read_json(fill_path(bridge_dir)) or {"_": "chưa có fill"})


def _render_comm_log() -> None:
  bridge_dir = _active_bridge_dir()
  st.markdown(f"##### Nhật ký giao tiếp · `{bridge_dir_display(bridge_dir)}`")
  st.caption("bar / decision / fill / system")
  lc1, lc2 = st.columns([1, 4])
  restore_widget("bridge_log_limit", 200, preference_key="mt5.log_limit")
  limit = lc1.number_input(
    "Số dòng", 20, 1000, step=20, key="bridge_log_limit",
    on_change=preference_callback("bridge_log_limit", "mt5.log_limit"),
  )
  if lc2.button("Xóa log", key="bridge_clear_log"):
    clear_log(bridge_dir)
    st.rerun()

  events = list(reversed(read_events(bridge_dir=bridge_dir, limit=int(limit))))
  if not events:
    st.warning("Chưa có log. Live: Start service + EA. Test lịch sử: Start test + cùng EA Live.")
  else:
    rows = [{
      "ts": e.get("ts"),
      "hướng": e.get("direction"),
      "sự kiện": e.get("event"),
      "tóm tắt": e.get("summary"),
    } for e in events]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    with st.expander("Chi tiết JSON từng event", expanded=False):
      st.json(events[:50])


def _render_live_chart_tab() -> None:
  chart_ranges = list(CHART_RANGE_OPTIONS)
  chart_bars = chart_bars_full()
  chart_key = "mt5_chart_range_live"
  pref_key = "mt5.chart_range"
  st.subheader(f"Biểu đồ · {_mode_label()}")
  restore_widget(
    chart_key, "1 tuần",
    preference_key=pref_key,
    options=chart_ranges,
  )
  roster_ids = _live_roster_model_ids()
  model_scope: str | None
  if len(roster_ids) > 1:
    c1, c2 = st.columns([1.2, 2.4])
    with c1:
      range_label = st.selectbox(
        "Khoảng chart",
        chart_ranges,
        key=chart_key,
        on_change=preference_callback(chart_key, pref_key),
      )
    with c2:
      model_scope = _render_live_model_scope(
        widget_key="live_chart_view_model",
        pref_key="mt5.chart_view_model",
      )
  else:
    range_label = st.selectbox(
      "Khoảng chart",
      chart_ranges,
      key=chart_key,
      on_change=preference_callback(chart_key, pref_key),
    )
    model_scope = roster_ids[0] if roster_ids else None
  _render_live_chart(chart_bars[range_label], model_id=model_scope)


def _render_health_tab() -> None:
  st.subheader(LABEL_TAB_REWARD)
  svc_running = bool(bridge_bg.get_status().get("running")) or bool(
    bridge_bg.get_sim_status().get("running")
  )
  if svc_running:
    _model_monitor_auto_fragment()
  else:
    _render_model_monitor()


def _render_tech_panel() -> None:
  """Fingerprint, deploy, test, snapshots, log — tab Kỹ thuật."""
  bridge_dir = _active_bridge_dir()
  st.subheader("Kỹ thuật · App ↔ EA")
  st.caption(
    "Kiểm tra kết nối / deploy / debug. "
    f"Thư mục đang dùng: `{bridge_dir_display(bridge_dir)}`."
  )

  active = get_active_trade_model()
  decision = read_json(decision_path(bridge_dir)) or {}
  file_status = read_json(status_path(bridge_dir)) or {}

  st.markdown("##### Khớp Trade Model")
  _render_conditions_alignment(
    active=active,
    decision=decision,
    file_status=file_status,
    detailed=True,
  )

  st.divider()
  st.caption("Deploy EA: dùng nút **Deploy Live** trên sidebar (test lịch sử dùng cùng EA).")
  _render_live_advanced_controls()
  st.divider()
  _render_manual_test_orders(show_json=True)
  st.divider()
  _render_history_sync()

  st.divider()
  _render_snapshot_files()
  st.divider()
  _render_comm_log()


def render_tab_models() -> list[str]:
  return _render_bridge_models_tab()


def render_tab_risk_control() -> None:
  _render_risk_controls()


def render_tab_stats() -> None:
  svc_running = bool(bridge_bg.get_status().get("running")) or bool(
    bridge_bg.get_sim_status().get("running")
  )
  if svc_running:
    _stats_auto_fragment()
  else:
    _render_stats_section()


def render_tab_chart() -> None:
  _render_live_chart_tab()


def render_tab_health() -> None:
  _render_health_tab()


def render_tab_tech() -> None:
  _render_tech_panel()


def render_tab_history() -> None:
  _render_simulate_ea()


def render_bridge_tabs() -> None:
  """MT5 Bridge tabs (without Now) — used inside Live Trade."""
  tab_models, tab_risk, tab_stats, tab_chart, tab_health, tab_tech, tab_hist = st.tabs([
    "Trade Models",
    "Risk control",
    "Thống kê",
    "Biểu đồ",
    LABEL_TAB_REWARD,
    "Kỹ thuật",
    "Test lịch sử",
  ])
  with tab_models:
    render_tab_models()
  with tab_risk:
    render_tab_risk_control()
  with tab_stats:
    render_tab_stats()
  with tab_chart:
    render_tab_chart()
  with tab_health:
    render_tab_health()
  with tab_tech:
    render_tab_tech()
  with tab_hist:
    render_tab_history()


def render():
  """Legacy entry — merged into Live Trade."""
  from gui.views import live_trade_dash
  live_trade_dash.render()
