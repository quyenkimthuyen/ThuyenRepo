"""MT5 Bridge — Trader desk: EA live status, decision, open risk, PnL."""
from __future__ import annotations

from datetime import date, timedelta
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from gui.charts import show_plotly
from gui.mt5_live_chart import build_ea_chart, connection_health, load_ea_chart_data, load_sim_chart_data
from gui.navigation import ALL_ITEMS
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
from mt5_bridge.live_monitor_server import DEFAULT_MONITOR_PORT
from mt5_bridge.protocol import (
  BRIDGE_DIR,
  BRIDGE_SIM_DIR,
  DEFAULT_MODEL_ID,
  DEFAULT_TIMEFRAME,
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
  resolve_live_bridge_dir,
  resolve_sim_bridge_dir,
  status_path,
  write_manual_close_command,
  write_manual_market_command,
)


def _desk_symbol() -> str:
  """Fallback chart symbol when connection.json is empty (EUR vs GBP desks)."""
  name = ROOT.name.upper()
  if "GBP" in name or INSTANCE_ID.upper().startswith(("M15G", "M5G")):
    return "GBPUSD"
  return "EURUSD"
from mt5_bridge.trade_journal import (
  clear_trades,
  compute_stats,
  filter_trades,
  load_trades,
  trade_mode,
)


def _bridge_any_service_running() -> bool:
  return bool(bridge_bg.get_status().get("running")) or bool(
    bridge_bg.get_sim_status().get("running")
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
    "Chọn model **một lần** — áp dụng cho cả **Live** và **Simulate**. "
    "Mỗi model một magic · tối đa 1 lệnh mở · Risk % chung. "
    "Danh sách không gồm model Archived."
  )
  picked_labels = st.multiselect(
    "Trade models (1–5)",
    labels,
    key="mt5_bridge_models",
    max_selections=MAX_BRIDGE_MODELS,
    disabled=running or not labels,
    on_change=preference_callback("mt5_bridge_models", "mt5.bridge_model_labels"),
    help="Đổi model khi cả Live và Simulate đang Stop. Archived không hiện ở đây.",
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

  st.session_state.setdefault("mt5_risk_pct", float(cfg.get("risk_pct", 1.0)))
  risk = st.number_input(
    "Risk % / lệnh (chung mọi model · Live & Simulate)",
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
    st.info("Live hoặc Simulate đang chạy — Stop trước khi đổi model / Risk %.")

  # Roster snapshot
  ids_runtime = get_bridge_runtime_model_ids() or model_ids
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
          "OOS R": oos,
          "Last": r.get("last_action") or "—",
          "Reason": r.get("last_reason") or "—",
        })
      st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True)
    else:
      for mid in ids_runtime:
        m = by_id.get(mid)
        label = format_model_short(m) if m else f"{mid[:28]} (id ma)"
        st.caption(f"· {label}")

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
  models = list_trade_models(include_archived=False)
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
  """Return 'live' or 'sim' from the page mode switcher."""
  label = st.session_state.get("mt5_bridge_mode") or "Live"
  return "sim" if str(label).startswith("Simulate") else "live"


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
  """Live EA I/O directory (desk / chart / feed). Always current sim dir in Simulate."""
  from mt5_bridge.protocol import resolve_live_bridge_dir, resolve_sim_bridge_dir
  return resolve_sim_bridge_dir() if _bridge_mode() == "sim" else resolve_live_bridge_dir()


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
  if _bridge_mode() != "sim":
    return "Live"
  viewing, _ = _sim_viewing_archive()
  return "Simulate · lịch sử" if viewing else "Simulate"


def _render_mode_switcher() -> str:
  """Top-level Live | Simulate — shared desk/chart/stats/monitor source."""
  modes = ["Live", "Simulate"]
  restore_widget(
    "mt5_bridge_mode", "Live",
    preference_key="mt5.bridge_mode",
    options=modes,
  )
  st.radio(
    "Chế độ",
    modes,
    horizontal=True,
    key="mt5_bridge_mode",
    on_change=preference_callback("mt5_bridge_mode", "mt5.bridge_mode"),
  )
  return _bridge_mode()


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
      st.warning("Có model lệch fp — Stop/Start Simulate hoặc Live để nạp lại roster.")
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
    f"Điều kiện remine (= Sức khỏe): train **{model_desc.get('train_weeks')}w** · "
    f"KB `{model_desc.get('kb_profile')}@ep{model_desc.get('kb_snapshot')}` · "
    f"session `{ss.get('session_ranges')}` · spacing `{ss.get('min_bars_between')}` · "
    f"hold `{ss.get('max_hold_bars')}` · "
    f"spread/slip `{model_desc.get('spread_pips')}/{model_desc.get('slippage_pips')}` · "
    f"fp `{model_fp}`"
  )
  if match_state == "mismatch":
    st.warning(
      f"Bridge đang chạy fp `{live_fp}` ≠ model `{model_fp}`. "
      "Stop/Start service để khớp lại với Trade Model / Sức khỏe."
    )
  elif match_state == "match":
    st.success(f"Bridge khớp điều kiện model (fp `{live_fp or model_fp}`).")
  else:
    st.info("Chưa có decision/status mới — Start Bridge để xác nhận fp khớp Sức khỏe.")


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
        c1.caption("App đã Start — chờ EA History Feed")
      elif health.get("online"):
        c1.metric(ea_label, f"EA OK · {age_txt}")
        c1.caption("Sim EA online · chưa Start feed")
      else:
        c1.metric(ea_label, f"OFFLINE · {age_txt}")
    elif health.get("online"):
      c1.metric(ea_label, f"ONLINE · {age_txt}")
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


@st.fragment(run_every=timedelta(seconds=3))
def _sim_desk_fragment() -> None:
  """Refresh Sim status / Sim R / open trade — chart stays in iframe (no remount)."""
  if hasattr(bridge_bg.get_sim_status, "_cache"):
    bridge_bg.get_sim_status._cache = None
  _render_trader_desk(include_live_metrics=False)


def _chart_server_healthy(url: str) -> bool:
  try:
    with urlopen(f"{url}/health", timeout=0.5) as response:
      return response.read() == b"ok"
  except (OSError, URLError):
    return False


@st.fragment(run_every=timedelta(seconds=2))
def _live_chart_recover_fragment(max_bars: int) -> None:
  """After Stop→Start, chart server may lag; retry until ready then remount iframe."""
  from mt5_bridge.live_monitor_server import ensure_chart_server

  ensure_chart_server(resolve_live_bridge_dir(), DEFAULT_MONITOR_PORT)
  if _chart_server_healthy(f"http://127.0.0.1:{DEFAULT_MONITOR_PORT}"):
    # One-shot remount — do not loop st.rerun every 2s once healthy.
    if not st.session_state.get("_live_chart_recovered"):
      st.session_state["_live_chart_recovered"] = True
      st.rerun()
  else:
    st.session_state["_live_chart_recovered"] = False
    st.caption("Đang chờ Live chart server…")


def _render_live_chart(max_bars: int) -> None:
  """Live + Simulate: persistent browser iframe (Plotly.react) — no Streamlit flicker."""
  bridge_dir = _active_bridge_dir()
  mode = _bridge_mode()
  legend = "🟢 reward · 🔴 risk · 🔔 SIGNAL · ▲▼ ENTRY · ✕ exit — overlay giống Compare/Sim."
  monitor_url = f"http://127.0.0.1:{DEFAULT_MONITOR_PORT}"

  if mode == "sim":
    from mt5_bridge.live_monitor_server import SIM_MONITOR_PORT, ensure_chart_server
    sim_url = f"http://127.0.0.1:{SIM_MONITOR_PORT}"
    ensure_chart_server(BRIDGE_SIM_DIR, SIM_MONITOR_PORT)
    server_ready = _chart_server_healthy(sim_url)
    if server_ready:
      # Dates are applied only on Start feed — do not write_sim_state here
      # (changing Từ/Đến must not trigger disk/chart rebuild before Start).
      components.iframe(
        f"{sim_url}/chart?mode=sim&bars={max_bars}&v=sim4",
        height=700,
        scrolling=False,
      )
      st.caption(legend)
      return
    st.warning(
      f"Chart server Simulate (:{SIM_MONITOR_PORT}) chưa chạy. Đang fallback snapshot tĩnh."
    )
    from mt5_bridge.ea_simulator import load_sim_state
    sim = load_sim_state()
    frame, connection = load_sim_chart_data(
      date_from=sim.get("date_from") or str(st.session_state.get("sim_ea_from") or ""),
      date_to=sim.get("date_to") or str(st.session_state.get("sim_ea_to") or ""),
      last_bar=sim.get("last_bar"),
      max_bars=max_bars,
      bridge_dir=bridge_dir,
      progress_only=str(sim.get("status") or "") in ("running", "paused"),
    )
    sym = str((connection or {}).get("symbol") or "").strip().upper() or _desk_symbol()
    sim_chart_title = f"{sym} M5 · Simulate (static fallback)"
    fig = build_ea_chart(
      frame, connection, load_trades(bridge_dir),
      title=sim_chart_title,
      price_line_label="SIM",
    )
    if fig is None:
      st.caption("Chưa vẽ được chart — thiếu dữ liệu giá.")
    else:
      show_plotly(fig, sim_chart_title, key="mt5_ea_sim_chart_fallback")
    return

  from mt5_bridge.live_monitor_server import ensure_chart_server
  ensure_chart_server(resolve_live_bridge_dir(), DEFAULT_MONITOR_PORT)
  server_ready = _chart_server_healthy(monitor_url)
  if server_ready:
    components.iframe(
      f"{monitor_url}/chart?bars={max_bars}",
      height=700,
      scrolling=False,
    )
    st.caption(legend)
    return
  st.warning("Live chart server chưa chạy; đang dùng snapshot tĩnh.")
  frame, connection = load_ea_chart_data(max_bars=max_bars, bridge_dir=bridge_dir)
  trades = load_trades(bridge_dir)
  sym = str((connection or {}).get("symbol") or "").strip().upper() or _desk_symbol()
  live_chart_title = f"{sym} M5 · XM MT5 live"
  fig = build_ea_chart(frame, connection, trades, title=live_chart_title)
  if fig is None:
    st.caption("Đang chờ EA gửi nến để vẽ chart.")
  else:
    show_plotly(fig, live_chart_title, key="mt5_ea_live_chart")
    st.caption(legend)
  # Auto-recover after Stop→Start without forcing a manual page refresh.
  if bool(bridge_bg.get_status().get("running")):
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
  from gui.mt5_deploy_ui import ea_live_name, run_deploy_mode
  st.markdown("##### Triển khai EA Live (riêng)")
  st.caption(f"Chỉ `{ea_live_name()}` · folder `{resolve_live_bridge_dir().name}`.")
  if st.button(
    "Deploy Live only",
    icon=":material/settings_suggest:",
    use_container_width=True,
    key="mt5_live_deploy",
  ):
    with st.spinner("Đang deploy Live…"):
      try:
        code, out, err = run_deploy_mode("Live", enable_trading=True)
      except Exception as e:
        st.error(f"Lỗi: {e}")
        return
    if code == 0:
      st.success("Triển khai Live thành công!")
      st.code(out)
    else:
      st.error(f"Lỗi khi triển khai (Mã lỗi: {code}):")
      st.code(err + "\n" + out)


def _render_service_controls() -> None:
  """Trader desk controls: loss guard + Start/Stop (model chọn ở tab Trade Models)."""
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

  st.subheader("Điều khiển Live")
  if not model_ids:
    st.warning("Chưa chọn Trade Model — mở tab **Trade Models**.")

  st.session_state.setdefault("mt5_risk_pct", float(cfg.get("risk_pct", 1.0)))
  st.session_state.setdefault("mt5_poll_sec", float(cfg.get("poll_sec", 2.0)))
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

  risk = float(st.session_state.get("mt5_risk_pct", cfg.get("risk_pct", 1.0)))
  poll = float(st.session_state.get("mt5_poll_sec", cfg.get("poll_sec", 2.0)))

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

  if running:
    if st.button(
      "Stop",
      icon=":material/stop:",
      use_container_width=True,
      key="mt5_live_svc_stop",
    ):
      bridge_bg.stop_worker()
      st.toast("Đã stop service")
      st.rerun()
  else:
    live_dir = resolve_live_bridge_dir()
    live_conn = read_json(connection_path(live_dir)) or {}
    live_health = connection_health(
      live_conn, stale_after_seconds=15.0, bridge_dir=live_dir,
    )
    ea_online = bool(live_health.get("online"))
    start_label = "Start" if ea_online else "Deploy EA Live + Start"
    start_icon = ":material/play_arrow:" if ea_online else ":material/settings_suggest:"
    if st.button(
      start_label,
      icon=start_icon,
      type="primary",
      use_container_width=True,
      key="mt5_live_svc_start",
      disabled=not model_ids,
      help=(
        "Live EA online — Start Bridge service."
        if ea_online else
        "Live EA offline — Deploy Live rồi Start trong một bước."
      ),
    ):
      ea_ready = ea_online
      if not ea_ready:
        from gui.mt5_deploy_ui import deploy_ea_and_wait_online, ea_live_name
        if bridge_bg.is_running():
          st.warning("Live Bridge đang chạy — không Deploy lại. Dùng Stop rồi Start.")
        else:
          with st.spinner(f"Đang deploy `{ea_live_name()}` (tối đa ~90s)…"):
            ok_dep, detail = deploy_ea_and_wait_online(
              "Live",
              live_dir,
              enable_trading=True,
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
        bridge_bg.save_config(
          model_id=primary_id,
          model_ids=model_ids,
          risk_pct=risk,
          poll_sec=poll,
          enabled=True,
          loss_guard_enabled=bool(st.session_state.get("mt5_loss_guard_enabled", True)),
          loss_guard_max_day=int(st.session_state.get("mt5_loss_guard_max_day", 3)),
          loss_guard_max_week=int(st.session_state.get("mt5_loss_guard_max_week", 5)),
          loss_guard_tripped=False,
          loss_guard_tripped_at=None,
          loss_guard_tripped_reason=None,
          last_error=None,
        )
        bridge_bg.sync_bridge_roster(
          bridge_dir=live_dir,
          model_ids=model_ids,
          risk_pct=float(risk),
        )
        ok = bridge_bg.start_worker(detached=True)
        if ok:
          from mt5_bridge.live_monitor_server import ensure_chart_server
          import time as _time
          ensure_chart_server(live_dir, DEFAULT_MONITOR_PORT)
          monitor_url = f"http://127.0.0.1:{DEFAULT_MONITOR_PORT}"
          for _ in range(15):
            if _chart_server_healthy(monitor_url):
              break
            _time.sleep(0.2)
          st.toast(f"Đã start service · {len(model_ids)} model")
        else:
          st.error("Không start được service — mở mục Kỹ thuật để xem log.")
        st.rerun()
    if ea_online:
      age = live_health.get("age_seconds")
      age_txt = f"{age:.0f}s" if age is not None else "—"
      st.caption(f"Live EA online · heartbeat {age_txt}")

  # Per-model stats strip
  trades = load_trades(resolve_live_bridge_dir())
  if model_ids and trades:
    rows = []
    for mid in model_ids:
      stt = compute_stats(trades, mode="auto", model_id=mid, use_exit_time=False)
      m = by_id.get(mid)
      rows.append({
        "Model": format_model_label(m) if m is not None else mid[:24],
        "N": stt.get("n_trades") or 0,
        "WR%": stt.get("win_rate_pct"),
        "Total R": stt.get("total_r"),
        "MaxDD": stt.get("max_drawdown_r"),
      })
    agg = compute_stats(trades, mode="auto", use_exit_time=False)
    st.caption(
      f"Tổng (auto): N={agg.get('n_trades') or 0} · "
      f"WR={agg.get('win_rate_pct')}% · R={agg.get('total_r')}"
    )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


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
    f"Bridge dir: `{resolve_live_bridge_dir()}` · model `{model_id}` · "
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
        text=f"Đồng bộ lịch sử MT5: {received}/{available or '?'} nến M5",
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
      + f" · EA `{ea_st}` · {bars_done}/{bars_total} nến · "
      f"{sim.get('n_fills') or 0} lệnh"
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

  b2, b3, b4, b5 = st.columns(4)
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
  if b4.button(
    "Reset data",
    icon=":material/delete_sweep:",
    use_container_width=True,
    key="sim_ea_reset",
    help="Xóa trades/fills/log/bar/decision/sim_control lần chạy trước để chạy lại sạch.",
    disabled=running,
  ):
    bridge_bg.reset_sim_data()
    st.toast("Đã xóa dữ liệu Simulate — có thể Start feed lại")
    st.rerun()
  if b5.button("Refresh", icon=":material/refresh:", use_container_width=True, key="sim_ea_refresh"):
    import time as _time
    st.session_state["bridge_ui_refresh_tick"] = _time.strftime("%H:%M:%S")
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

  st.subheader("Điều khiển History Feed")
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

  c1, c2, c3 = st.columns(3)
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
  with c3:
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
  _start_label = "Start feed" if _ea_online else "Deploy EA Sim + Start feed"
  _start_icon = ":material/play_arrow:" if _ea_online else ":material/settings_suggest:"
  start_clicked = st.button(
    _start_label,
    type="primary",
    icon=_start_icon,
    disabled=running or not model_ids,
    use_container_width=True,
    key="sim_ea_start",
    help=(
      "Sim EA đang online — Start History Feed."
      if _ea_online else
      "Sim EA offline — Deploy Simulate rồi Start feed trong một bước."
    ),
  )
  if _ea_online:
    _age = _sim_health.get("age_seconds")
    _age_txt = f"{_age:.0f}s" if _age is not None else "—"
    st.caption(f"Sim EA online · heartbeat {_age_txt}")

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
        from gui.mt5_deploy_ui import deploy_ea_and_wait_online, ea_sim_name
        if bridge_bg.is_sim_running():
          st.warning("Sim feed đang chạy — không Deploy lại. Dùng Stop rồi Start.")
        else:
          with st.spinner(f"Đang deploy `{ea_sim_name()}` (tối đa ~90s)…"):
            ok_dep, detail = deploy_ea_and_wait_online(
              "HistoryFeed",
              BRIDGE_SIM_DIR,
              skip_bridge_service=True,
              wait_sec=20.0,
              deploy_timeout_sec=90.0,
            )
          if not ok_dep:
            st.error(detail.split("\n", 1)[0])
            if "\n" in detail:
              st.code(detail.split("\n", 1)[1])
          else:
            st.toast(f"Đã deploy `{ea_sim_name()}` · EA online")
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
            f"Sim feed đã start · {len(model_ids)} model · "
            f"pid=`{st2.get('service_pid')}`"
          )
          st.rerun()
        else:
          st.warning("Feed đang chạy")

  _render_sim_history_picker()

  # Per-model stats on live sim journal
  sim_trades = load_trades(BRIDGE_SIM_DIR)
  _sim_open_n = sum(
    1 for t in (sim_trades or []) if str(t.get("status") or "").upper() == "OPEN"
  )
  if _sim_open_n > 0 and not running:
    st.warning(
      f"App đang nhớ **{_sim_open_n} lệnh mở** trên Simulate trong khi feed đã dừng — "
      "model sẽ bị HOLD (`position_open`) nếu Start lại mà không xóa treo. "
      "Thường do mất close fill (multi-model / delay thấp)."
    )
    if st.button(
      "Xóa lệnh treo trên App",
      key="sim_clear_ghost_opens",
      type="primary",
      help="Đóng ghost OPEN trong journal Simulate (R=0 / BE) để model vào lệnh lại.",
    ):
      from mt5_bridge.trade_journal import close_ghost_journal_opens
      n = close_ghost_journal_opens(BRIDGE_SIM_DIR, reason="journal_desync")
      st.toast(f"Đã đóng {n} lệnh treo" if n else "Không còn lệnh treo")
      st.rerun()
  if model_ids and sim_trades:
    rows = []
    for mid in model_ids:
      stt = compute_stats(sim_trades, mode="auto", model_id=mid, use_exit_time=False)
      m = by_id.get(mid)
      rows.append({
        "Model": format_model_label(m) if m else mid[:24],
        "N": stt.get("n_trades") or 0,
        "WR%": stt.get("win_rate_pct"),
        "Total R": stt.get("total_r"),
        "MaxDD": stt.get("max_drawdown_r"),
      })
    agg = compute_stats(sim_trades, mode="auto", use_exit_time=False)
    st.caption(
      f"Tổng sim (auto): N={agg.get('n_trades') or 0} · "
      f"WR={agg.get('win_rate_pct')}% · R={agg.get('total_r')}"
    )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

def _render_sim_history_picker() -> None:
  """Browse archived Simulate runs (results/simulate_runs)."""
  from mt5_bridge.sim_history import delete_sim_run, list_sim_runs

  archives = list_sim_runs(limit=50)
  live_token = "__live__"
  hist_ids = [live_token] + [str(a.get("run_id")) for a in archives if a.get("run_id")]
  seen: set[str] = set()
  hist_ids = [x for x in hist_ids if not (x in seen or seen.add(x))]
  id_to_summary = {str(a.get("run_id")): a for a in archives if a.get("run_id")}
  hist_labels = {
    live_token: "★ Live · bridge_sim hiện tại (feed / desk)",
    **{
      rid: _sim_history_label(id_to_summary[rid])
      for rid in hist_ids if rid != live_token and rid in id_to_summary
    },
  }

  pending = st.session_state.pop("_sim_pending_history", None)
  if pending and pending in hist_ids:
    st.session_state["sim_history_run_id"] = pending

  restore_widget(
    "sim_history_run_id", live_token,
    preference_key="mt5.sim_history_run_id",
    options=hist_ids,
  )
  if st.session_state.get("sim_history_run_id") not in hist_ids:
    st.session_state["sim_history_run_id"] = live_token

  st.subheader("Lịch sử Simulate")
  st.caption(
    "Mỗi lần Start/Stop/hoàn tất feed được lưu vào `results/simulate_runs/`. "
    "Chọn run cũ để xem lại Thống kê / Sức khỏe (read-only)."
  )
  h1, h2 = st.columns([4, 1])
  with h1:
    st.selectbox(
      "Run đã lưu",
      hist_ids,
      format_func=lambda rid: hist_labels.get(rid, rid),
      key="sim_history_run_id",
      on_change=lambda: set_preference(
        "mt5.sim_history_run_id",
        st.session_state.get("sim_history_run_id"),
      ),
      help="Live = dữ liệu bridge_sim đang dùng cho EA feed.",
    )
  with h2:
    selected = st.session_state.get("sim_history_run_id") or live_token
    running_now = bool(bridge_bg.get_sim_status().get("running"))
    can_delete = selected != live_token and selected in id_to_summary and not running_now
    if st.button(
      "Xóa run",
      key="sim_history_delete",
      use_container_width=True,
      disabled=not can_delete,
      help="Xóa archive results/simulate_runs/<run_id>.",
    ):
      if delete_sim_run(str(selected)):
        st.session_state["_sim_pending_history"] = live_token
        set_preference("mt5.sim_history_run_id", live_token)
        st.toast(f"Đã xóa `{selected}`")
        st.rerun()

  viewing, meta = _sim_viewing_archive()
  if viewing and meta:
    st.info(
      f"Đang xem lịch sử **`{meta.get('run_id')}`** · "
      f"{meta.get('date_from')} → {meta.get('date_to')} · "
      f"model `{meta.get('model_id') or '—'}` · "
      f"status **{meta.get('status')}** — "
      "Start feed vẫn dùng Live bridge_sim."
    )


def _render_model_monitor() -> None:
  """Backtest OOS vs Live Auto / Simulate EA — health + risk."""
  try:
    _render_model_monitor_body()
  except Exception as e:
    st.error(f"Không render được Theo dõi model: {e}")
    with st.expander("Chi tiết lỗi"):
      st.exception(e)


@st.fragment(run_every=timedelta(seconds=12))
def _model_monitor_auto_fragment() -> None:
  """Auto-refresh Sức khỏe / Rủi ro while Live service or Sim feed is running."""
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
    build_multi_model_equity_figure,
    build_multi_model_monthly_figure,
    load_live_auto_trades,
  )
  from gui.trade_model import (
    format_model_label,
    get_bridge_runtime_model_ids,
    get_model_by_id,
  )
  from mt5_bridge.ea_simulator import load_sim_state

  active = get_active_trade_model()
  source = _bridge_mode()
  bridge_mids = get_bridge_runtime_model_ids()
  st.subheader(f"Theo dõi model · {_mode_label()}")
  if not active and not bridge_mids:
    st.info("Chọn Trade Model active để xem report OOS và lệnh Bridge auto.")
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

  # Multi-model Bridge: overlay Live/Sim equity + monthly per selected model
  if len(bridge_mids) > 1:
    st.markdown(f"**{len(bridge_mids)} model đang chạy Bridge** — equity / tháng (auto)")
    eq_map: dict = {}
    mo_map: dict = {}
    kpi_rows = []
    for mid in bridge_mids:
      bm = get_model_by_id(mid)
      label = format_model_label(bm) if bm else mid[:24]
      live = load_live_auto_trades(
        mid,
        bridge_dir=view_bridge,
        date_from=date_from,
        date_to=date_to,
        use_exit_time=(source != "sim"),
      )
      short = label if len(label) <= 36 else label[:34] + "…"
      if live.get("equity") is not None and not getattr(live["equity"], "empty", True):
        eq_map[short] = live["equity"]
      if live.get("monthly") is not None and not getattr(live["monthly"], "empty", True):
        mo_map[short] = live["monthly"]
      stt = live.get("stats") or {}
      kpi_rows.append({
        "Model": short,
        "N": stt.get("n_trades") or 0,
        "WR%": stt.get("win_rate_pct"),
        "Total R": stt.get("total_r"),
        "MaxDD": stt.get("max_drawdown_r"),
      })
    if kpi_rows:
      st.dataframe(pd.DataFrame(kpi_rows), hide_index=True, use_container_width=True)
    fig_eq = build_multi_model_equity_figure(
      eq_map, title=f"Equity R · {_mode_label()} · multi-model",
    )
    if fig_eq:
      show_plotly(fig_eq, f"Equity multi · {_mode_label()}")
    else:
      st.info("Chưa đủ lệnh auto theo model để vẽ equity overlay.")
    fig_mo = build_multi_model_monthly_figure(
      mo_map, title=f"R theo tháng · {_mode_label()} · multi-model",
    )
    if fig_mo:
      show_plotly(fig_mo, f"Tháng multi · {_mode_label()}")
    st.divider()

  # Detail: pick any roster model (no “model chính”)
  from gui.trade_model import format_model_short
  detail_ids = bridge_mids if bridge_mids else (
    [str(active["id"])] if active and active.get("id") else []
  )
  if not detail_ids:
    return
  if len(detail_ids) > 1:
    st.markdown("**Chi tiết OOS vs Bridge** — chọn model:")
    pick = st.selectbox(
      "Model",
      detail_ids,
      format_func=lambda mid: format_model_short(get_model_by_id(mid), max_len=48),
      key=f"monitor_detail_mid_{source}",
      label_visibility="collapsed",
    )
    active = get_model_by_id(pick)
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
  else:
    st.caption(f"**{bundle['model_label']}**")

  if not bundle["has_report"]:
    st.warning(
      "Chưa có report backtest của model. Chạy **Trade Models → Sức khỏe** "
      "(bật Chạy lại KB ON, đúng search space) rồi quay lại."
    )

  kpi = bundle["kpi"]
  live_n = int(kpi["live"].get("n_trades") or 0)

  # Live: OOS và Live khác giai đoạn thời gian → tách 2 đoạn, mặc định thu gọn.
  if source == "live":
    st.caption(
      "OOS (Health) và Live Auto **không cùng giai đoạn** — xem riêng từng phần bên dưới."
    )
    with st.expander("① OOS · Health report", expanded=False):
      b = kpi["bt"]
      m1, m2, m3, m4 = st.columns(4)
      m1.metric("Total R", f"{b.get('total_r'):+.1f}" if b.get("total_r") is not None else "—")
      m2.metric("WR%", f"{b.get('win_rate_pct')}%" if b.get("win_rate_pct") is not None else "—")
      m3.metric("Max DD", f"{b.get('max_drawdown_r')}R" if b.get("max_drawdown_r") is not None else "—")
      m4.metric("Trades", f"{b.get('n_trades') or '—'}")
      th, tr = st.tabs(["Sức khỏe", "Rủi ro"])
      with th:
        oos_monthly_title = f"Tháng · OOS · {bundle['model_label']}"
        fig = build_monthly_series_figure(
          bundle["bt"]["monthly"],
          title=oos_monthly_title,
          series_name="Backtest OOS",
          color=OOS_SERIES_COLOR,
        )
        if fig:
          show_plotly(fig, oos_monthly_title)
        else:
          st.info("Chưa có chuỗi tháng OOS.")
      with tr:
        oos_equity_title = f"Equity · OOS · {bundle['model_label']}"
        eq = build_equity_series_figure(
          bundle["bt"]["equity"],
          title=oos_equity_title,
          series_name="Backtest OOS",
          color=OOS_SERIES_COLOR,
        )
        if eq:
          show_plotly(eq, oos_equity_title)
        else:
          st.info("Chưa có equity OOS.")

    with st.expander(f"② {live_label} · Bridge auto", expanded=False):
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
          f"Chưa có lệnh **auto** đã đóng trên Bridge (`mt5/{resolve_live_bridge_dir().name}/trades.json`)."
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
      th, tr = st.tabs(["Sức khỏe", "Rủi ro"])
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
    f"Simulate: KPI/biểu đồ đọc `mt5/{BRIDGE_SIM_DIR.name}/trades.json` theo **entry_time** lịch sử "
    "(không dùng giờ tường lúc fill). Tự cập nhật ~12s khi feed chạy; hoặc bấm Refresh."
  )
  tab_h, tab_r = st.tabs(["Sức khỏe", "Rủi ro"])

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
        "Chưa có lệnh Simulate — ở mode **Simulate**, Start feed "
        "(EA HISTORY_FEED) rồi Refresh."
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

  with st.expander("Cách đọc Backtest vs Simulate"):
    st.markdown(
      "- **Backtest OOS** = report Trade Model (cùng điều kiện remine / Health).\n"
      f"- **Simulate EA** = fill từ `{BRIDGE_SIM_DIR.name}/` (EA HISTORY_FEED).\n"
      "- Overlay cùng cửa sổ sim → Edge gần 0 nghĩa là model + App↔EA khớp.\n"
      "- Live mode xem **riêng** OOS vs Live (khác giai đoạn)."
    )


def _render_stats_section() -> None:
  """Thống kê lệnh — đọc lại trades.json mỗi lần gọi (không cache fragment)."""
  bridge_dir = _sim_stats_bridge_dir() if _bridge_mode() == "sim" else _active_bridge_dir()
  mode = _bridge_mode()
  tick = st.session_state.get("bridge_ui_refresh_tick")
  st.subheader(f"Thống kê lệnh · {_mode_label()}")
  if tick:
    st.caption(f"Cập nhật `{tick}`")

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
    default_preset = "Hôm nay"
    pref_key = "mt5.stats_preset"
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


def _render_sim_deploy() -> None:
  from gui.mt5_deploy_ui import ea_sim_name, run_deploy_mode
  st.markdown("##### Triển khai EA Simulate (riêng)")
  st.caption(
    f"Chỉ `{ea_sim_name()}` · junction `{BRIDGE_SIM_DIR.name}`."
  )
  if st.button(
    "Deploy Simulate only",
    icon=":material/settings_suggest:",
    use_container_width=True,
    key="sim_ea_deploy",
  ):
    with st.spinner("Đang deploy Simulate…"):
      try:
        code, out, err = run_deploy_mode("HistoryFeed", skip_bridge_service=True)
      except Exception as e:
        st.error(f"Lỗi: {e}")
        return
    if code == 0:
      st.success("Deploy Simulate thành công.")
      st.code(out or "(no stdout)")
    else:
      st.error(f"Lỗi deploy (code {code}):")
      st.code((err or "") + "\n" + (out or ""))


def _render_snapshot_files() -> None:
  bridge_dir = _active_bridge_dir()
  st.markdown(f"##### Snapshot files · `{bridge_dir.name}`")
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
  st.markdown(f"##### Nhật ký giao tiếp · `{bridge_dir.name}`")
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
    st.warning("Chưa có log. Live: Start service + EA. Simulate: Start feed + EA.")
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


def _render_tech_panel() -> None:
  """Một expander Kỹ thuật — fingerprint, deploy, test, snapshots, log."""
  mode = _bridge_mode()
  bridge_dir = _active_bridge_dir()
  with st.expander("Kỹ thuật · App ↔ EA", expanded=False):
    st.caption(
      "Dành cho kiểm tra kết nối / deploy / debug. "
      f"Thư mục đang dùng: `{bridge_dir.name}`."
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
    st.caption("Deploy cả hai: dùng nút **Deploy Live + Simulate** trên sidebar.")
    if mode == "live":
      _render_live_advanced_controls()
      st.divider()
      _render_manual_test_orders(show_json=True)
      st.divider()
      _render_history_sync()
    else:
      _render_sim_deploy()

    st.divider()
    _render_snapshot_files()
    st.divider()
    _render_comm_log()


def render():
  render_page_header(ALL_ITEMS["mt5_bridge"], show_workspace=False)

  tab_models, tab_ops = st.tabs(["Trade Models", "Vận hành"])

  with tab_models:
    _render_bridge_models_tab()

  with tab_ops:
    mode = _render_mode_switcher()

    chart_ranges = ["1 ngày", "1 tuần", "1 tháng", "6 tháng", "1 năm", "Tất cả"]
    # M5 ≈ 288 bars/day
    chart_bars = {
      "1 ngày": 96,
      "1 tuần": 672,
      "1 tháng": 2880,
      "6 tháng": 17472,
      "1 năm": 35040,
      "Tất cả": 200_000,
    }
    chart_key = "mt5_chart_range_sim" if mode == "sim" else "mt5_chart_range_live"
    pref_key = "mt5.chart_range_sim" if mode == "sim" else "mt5.chart_range"

    # 1) Điều khiển
    if mode == "sim":
      _render_simulate_ea()
    else:
      _render_service_controls()

    # 2) Desk
    if mode == "sim":
      _sim_desk_fragment()
    else:
      _trader_desk_fragment()

    # 3) Chart
    st.subheader(f"Biểu đồ · {_mode_label()}")
    restore_widget(
      chart_key, "1 tuần",
      preference_key=pref_key,
      options=chart_ranges,
    )
    range_label = st.selectbox(
      "Khoảng chart",
      chart_ranges,
      key=chart_key,
      on_change=preference_callback(chart_key, pref_key),
    )
    max_bars = chart_bars[range_label]
    _render_live_chart(max_bars)

    # 4) Thống kê
    svc_running = (
      bool(bridge_bg.get_sim_status().get("running")) if mode == "sim"
      else bool(bridge_bg.get_status().get("running"))
    )
    if svc_running:
      _stats_auto_fragment()
    else:
      _render_stats_section()

    # 5) Sức khỏe / Rủi ro (thu gọn)
    live_or_sim_running = svc_running
    with st.expander("Sức khỏe / Rủi ro model", expanded=False):
      if live_or_sim_running:
        _model_monitor_auto_fragment()
      else:
        _render_model_monitor()

    # 6) Kỹ thuật
    _render_tech_panel()
