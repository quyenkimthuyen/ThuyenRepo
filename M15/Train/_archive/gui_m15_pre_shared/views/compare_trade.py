"""Compare Trade — multi-model history replay (no EA)."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header
from gui.trade_model import format_model_label, get_model_by_id, list_trade_models
from gui.ui_preferences import preference_callback, restore_widget, set_preference

MAX_COMPARE_MODELS = 5


def _parse_ui_date(v):
  if isinstance(v, date):
    return v
  try:
    return date.fromisoformat(str(v)[:10])
  except Exception:
    return None


def _mt5_cache_range() -> tuple[date | None, date | None]:
  """Available broker dates in MT5 M15 cache (Compare source)."""
  try:
    from mt5_bridge.history_sync import load_mt5_cache

    df = load_mt5_cache()
    if df is None or df.empty:
      return None, None
    return df.index[0].date(), df.index[-1].date()
  except Exception:
    return None, None


def _compare_history_label(summary: dict) -> str:
  rid = summary.get("run_id") or "?"
  when = str(summary.get("updated_at") or summary.get("started_at") or "")[:19].replace("T", " ")
  d0 = summary.get("date_from") or "?"
  d1 = summary.get("date_to") or "?"
  n = summary.get("n_models") or 0
  best = summary.get("best_total_r")
  best_txt = f"{float(best):+.1f}R" if best is not None else "—"
  status = summary.get("status") or "?"
  tag = " · latest" if summary.get("is_latest") else ""
  return (
    f"{when} · `{rid}` · {d0}→{d1} · {n} model · best {best_txt} · {status}{tag}"
  )


def _extract_compare_run_id(value: str | None) -> str | None:
  import re
  text = str(value or "").strip()
  if not text:
    return None
  if text in ("__latest__", "latest", "current"):
    return "__latest__"
  if text.startswith("ct_") and " " not in text and "·" not in text:
    return text
  match = re.search(r"ct_\d{8}_\d{6}_[0-9a-f]+", text)
  return match.group(0) if match else None


def _on_compare_history_changed() -> None:
  raw = st.session_state.get("cmp_history_run_id")
  rid = _extract_compare_run_id(raw) or raw
  if rid:
    set_preference("compare.history_run_id", rid)


def render():
  render_page_header(ALL_ITEMS["compare_trade"], show_profile=False)
  st.caption(
    "Chạy nhiều Trade Model song song trên lịch sử MT5 cache — "
    "không dùng EA. Live / Simulate 1-model giữ nguyên ở MT5 Bridge. "
    "Mỗi lần Start được lưu — chọn lịch sử bên dưới để xem lại."
  )

  cache_from, cache_to = _mt5_cache_range()
  if cache_from and cache_to:
    st.info(
      f"MT5 M15 cache: **{cache_from} → {cache_to}**. "
      "Compare chỉ chạy trong khoảng này "
      "(đồng bộ thêm history ở MT5 Bridge nếu cần năm cũ hơn)."
    )
  else:
    st.warning(
      "Chưa có MT5 M15 cache — Start Bridge / sync history trước khi Compare."
    )

  from gui.long_task_background import get_task_status, is_task_running, start_job
  from gui.long_task_ui import render_task_status, task_blocks_ui
  from mt5_bridge.compare_runner import (
    COMPARE_ROOT,
    delete_compare_run,
    list_compare_runs,
    load_latest_run,
    load_run,
    model_stats_rows,
  )
  from gui.bridge_model_monitor import (
    build_multi_model_equity_figure,
    build_multi_model_monthly_figure,
    build_multi_model_price_figure,
    live_trades_to_analytics_df,
    load_compare_ohlc,
  )
  from analytics import equity_series, monthly_breakdown
  from mt5_bridge.trade_journal import load_trades

  models = list_trade_models()
  if len(models) < 2:
    st.warning("Cần ít nhất 2 Trade Model để so sánh. Tạo model từ Grid Search trước.")
    return

  label_by_id = {m["id"]: format_model_label(m) for m in models}
  id_by_label = {v: k for k, v in label_by_id.items()}
  labels = [label_by_id[m["id"]] for m in models]

  running = is_task_running() and (get_task_status().get("job_type") == "compare_trade")
  blocked = task_blocks_ui("compare_trade")

  first = models[0]
  default_from = _parse_ui_date(first.get("oos_from")) or date(2026, 1, 1)
  default_to = _parse_ui_date(first.get("oos_to")) or date(2026, 1, 31)
  if (default_to - default_from).days > 60:
    default_to = default_from + timedelta(days=14)

  restore_widget(
    "cmp_from", default_from,
    preference_key="compare.from",
    decode=_parse_ui_date,
  )
  restore_widget(
    "cmp_to", default_to,
    preference_key="compare.to",
    decode=_parse_ui_date,
  )
  restore_widget(
    "cmp_risk", 1.0,
    preference_key="compare.risk_pct",
    decode=lambda v: float(v),
  )
  restore_widget(
    "cmp_models", labels[:2],
    preference_key="compare.model_labels",
    options=labels,
    multiple=True,
  )

  picked_labels = st.multiselect(
    "Trade models (2–5)",
    labels,
    key="cmp_models",
    max_selections=MAX_COMPARE_MODELS,
    disabled=running or blocked,
    on_change=preference_callback("cmp_models", "compare.model_labels"),
  )
  c1, c2, c3 = st.columns(3)
  with c1:
    st.date_input(
      "Từ ngày",
      key="cmp_from",
      disabled=running or blocked,
      on_change=preference_callback("cmp_from", "compare.from"),
    )
  with c2:
    st.date_input(
      "Đến ngày",
      key="cmp_to",
      disabled=running or blocked,
      on_change=preference_callback("cmp_to", "compare.to"),
    )
  with c3:
    st.number_input(
      "Risk % / lệnh",
      min_value=0.1,
      max_value=5.0,
      step=0.1,
      key="cmp_risk",
      disabled=running or blocked,
      on_change=preference_callback("cmp_risk", "compare.risk_pct"),
    )

  render_task_status(key_prefix="cmp_task", show_cancel=True)

  start = st.button(
    "Start compare",
    type="primary",
    icon=":material/play_arrow:",
    disabled=running or blocked or len(picked_labels) < 2,
    use_container_width=True,
    key="cmp_start",
  )

  d_from = st.session_state["cmp_from"]
  d_to = st.session_state["cmp_to"]
  risk = float(st.session_state.get("cmp_risk") or 1.0)
  model_ids = [id_by_label[lb] for lb in picked_labels if lb in id_by_label]

  if start:
    if d_to < d_from:
      st.error("Đến ngày phải ≥ Từ ngày")
    elif len(model_ids) < 2:
      st.error("Chọn ít nhất 2 model")
    elif cache_from and cache_to and (d_to < cache_from or d_from > cache_to):
      st.error(
        f"Khoảng {d_from} → {d_to} nằm ngoài MT5 M15 cache "
        f"({cache_from} → {cache_to}). Đổi ngày hoặc sync thêm history."
      )
    else:
      set_preference("compare.from", d_from)
      set_preference("compare.to", d_to)
      set_preference("compare.risk_pct", risk)
      set_preference("compare.model_labels", picked_labels)
      try:
        start_job(
          "compare_trade",
          {
            "model_ids": model_ids,
            "date_from": d_from.isoformat() if hasattr(d_from, "isoformat") else str(d_from),
            "date_to": d_to.isoformat() if hasattr(d_to, "isoformat") else str(d_to),
            "risk_pct": risk,
          },
          label="Compare Trade",
        )
        st.success("Đã bắt đầu Compare Trade nền")
        st.rerun()
      except Exception as e:
        st.error(str(e))

  st.divider()
  archives = list_compare_runs(limit=50)
  latest_token = "__latest__"
  hist_ids = [latest_token] + [
    str(a.get("run_id")) for a in archives if a.get("run_id")
  ]
  # Deduplicate while keeping order
  seen = set()
  hist_ids = [x for x in hist_ids if not (x in seen or seen.add(x))]
  id_to_summary = {str(a.get("run_id")): a for a in archives if a.get("run_id")}
  hist_labels = {
    latest_token: (
      "★ Latest · " + _compare_history_label(archives[0])
      if archives else "★ Latest (chưa có run)"
    ),
    **{rid: _compare_history_label(id_to_summary[rid]) for rid in hist_ids if rid != latest_token and rid in id_to_summary},
  }

  # After a new Start completes, jump to latest unless user pinned another run.
  status = get_task_status()
  result = status.get("result") or {}
  if (
    status.get("job_type") == "compare_trade"
    and result.get("run_id")
    and not status.get("running")
  ):
    just_done = str(result["run_id"])
    if st.session_state.get("_cmp_seen_result_run") != just_done:
      st.session_state["_cmp_seen_result_run"] = just_done
      st.session_state["_cmp_pending_history"] = latest_token

  pending_hist = st.session_state.pop("_cmp_pending_history", None)
  if pending_hist and pending_hist in hist_ids:
    st.session_state["cmp_history_run_id"] = pending_hist

  restore_widget(
    "cmp_history_run_id", latest_token,
    preference_key="compare.history_run_id",
    options=hist_ids,
  )
  if st.session_state.get("cmp_history_run_id") not in hist_ids:
    st.session_state["cmp_history_run_id"] = latest_token

  h1, h2 = st.columns([4, 1])
  with h1:
    st.selectbox(
      "Lịch sử Compare",
      hist_ids,
      format_func=lambda rid: hist_labels.get(rid, rid),
      key="cmp_history_run_id",
      on_change=_on_compare_history_changed,
      help="Mỗi lần Start Compare được lưu. Chọn run cũ để xem lại equity / lệnh.",
    )
  with h2:
    selected_hist = st.session_state.get("cmp_history_run_id") or latest_token
    can_delete = (
      selected_hist not in (latest_token, None, "")
      and selected_hist in id_to_summary
      and not (is_task_running() and status.get("job_type") == "compare_trade")
    )
    if st.button(
      "Xóa run",
      key="cmp_history_delete",
      use_container_width=True,
      disabled=not can_delete,
      help="Xóa thư mục results/compare_trade/<run_id> của run đang xem.",
    ):
      if delete_compare_run(str(selected_hist)):
        st.session_state["_cmp_pending_history"] = latest_token
        set_preference("compare.history_run_id", latest_token)
        st.toast(f"Đã xóa `{selected_hist}`")
        st.rerun()

  selected_hist = st.session_state.get("cmp_history_run_id") or latest_token
  if selected_hist == latest_token:
    run = load_latest_run()
  else:
    run = load_run(str(selected_hist))

  # Live job override only when viewing Latest and a compare job just finished / is active
  if selected_hist == latest_token and status.get("job_type") == "compare_trade" and result.get("run_id"):
    rid = result["run_id"]
    run = load_run(rid) or run

  if not run:
    st.info("Chưa có run Compare Trade. Chọn ≥2 model và bấm Start.")
    return

  run_id = run.get("run_id")
  viewing_old = bool(selected_hist != latest_token and run_id)
  st.subheader(
    f"Kết quả · `{run_id}`"
    + (" · (lịch sử)" if viewing_old else " · (latest)")
  )
  st.caption(
    f"Status: **{run.get('status')}** · "
    f"{run.get('date_from')} → {run.get('date_to')} · "
    f"bars {run.get('bars_done', 0)}/{run.get('bars_total', 0)}"
    + (f" · started `{str(run.get('started_at') or '')[:19]}`" if run.get("started_at") else "")
  )
  if run.get("error"):
    st.error(run["error"])

  rows = model_stats_rows(run)
  if rows:
    st.dataframe(
      pd.DataFrame(rows),
      use_container_width=True,
      hide_index=True,
    )

  series_by_model: dict[str, pd.DataFrame] = {}
  monthly_by_model: dict[str, pd.DataFrame] = {}
  trades_by_model: dict[str, list] = {}
  for mid in run.get("model_ids") or []:
    mdir = COMPARE_ROOT / str(run_id) / "models" / str(mid)
    trades = load_trades(mdir)
    df = live_trades_to_analytics_df(trades)
    label = label_by_id.get(mid) or (get_model_by_id(mid) or {}).get("label") or mid
    trades_by_model[label] = trades
    if not df.empty:
      series_by_model[label] = equity_series(df)
      monthly_by_model[label] = monthly_breakdown(df)

  eq_fig = build_multi_model_equity_figure(series_by_model, title="Equity R · Compare Trade")
  if eq_fig is not None:
    st.plotly_chart(eq_fig, use_container_width=True)
  else:
    st.caption("Chưa đủ lệnh đóng để vẽ equity.")

  mo_fig = build_multi_model_monthly_figure(monthly_by_model, title="R theo tháng · Compare Trade")
  if mo_fig is not None:
    st.plotly_chart(mo_fig, use_container_width=True)

  st.subheader("Biểu đồ giá · lệnh theo model")
  chart_labels = list(trades_by_model.keys())
  if chart_labels:
    run_from = _parse_ui_date(run.get("date_from")) or date(2026, 1, 1)
    run_to = _parse_ui_date(run.get("date_to")) or date(2026, 1, 31)
    if run_to < run_from:
      run_to = run_from

    chart_ranges = ["1 ngày", "1 tuần", "1 tháng", "6 tháng", "Tất cả"]
    # M15 ≈ 96 bars/day — giống Simulate
    chart_bars = {
      "1 ngày": 96,
      "1 tuần": 672,
      "1 tháng": 2880,
      "6 tháng": 17472,
      "Tất cả": 200_000,
    }

    # Apply Full-run reset *before* chart widgets are instantiated
    if st.session_state.pop("_cmp_chart_reset", False):
      st.session_state["cmp_chart_from"] = run_from
      st.session_state["cmp_chart_to"] = run_to
      st.session_state["cmp_chart_range"] = "Tất cả"
      set_preference("compare.chart_from", run_from)
      set_preference("compare.chart_to", run_to)
      set_preference("compare.chart_range", "Tất cả")

    restore_widget(
      "cmp_chart_range", "1 tuần",
      preference_key="compare.chart_range",
      options=chart_ranges,
    )
    restore_widget(
      "cmp_chart_from", run_from,
      preference_key="compare.chart_from",
      decode=_parse_ui_date,
    )
    restore_widget(
      "cmp_chart_to", run_to,
      preference_key="compare.chart_to",
      decode=_parse_ui_date,
    )
    # Clamp into run window before widgets (safe: keys not bound yet this run)
    cf = st.session_state.get("cmp_chart_from")
    ct = st.session_state.get("cmp_chart_to")
    if not isinstance(cf, date):
      cf = _parse_ui_date(cf) or run_from
    if not isinstance(ct, date):
      ct = _parse_ui_date(ct) or run_to
    cf = max(run_from, min(cf, run_to))
    ct = max(run_from, min(ct, run_to))
    if ct < cf:
      ct = cf
    st.session_state["cmp_chart_from"] = cf
    st.session_state["cmp_chart_to"] = ct

    c_range, c_from, c_to, c_reset = st.columns([1.4, 1.2, 1.2, 0.8])
    with c_range:
      def _on_cmp_chart_range():
        preference_callback("cmp_chart_range", "compare.chart_range")()
        label = st.session_state.get("cmp_chart_range")
        ct = st.session_state.get("cmp_chart_to")
        if not isinstance(ct, date):
          ct = _parse_ui_date(ct) or run_to
        ct = max(run_from, min(ct, run_to))
        days_back = {
          "1 ngày": 0,
          "1 tuần": 6,
          "1 tháng": 29,
          "6 tháng": 182,
        }
        if label == "Tất cả":
          st.session_state["cmp_chart_from"] = run_from
          st.session_state["cmp_chart_to"] = run_to
          set_preference("compare.chart_from", run_from)
          set_preference("compare.chart_to", run_to)
        elif label in days_back:
          cf = max(run_from, ct - timedelta(days=days_back[label]))
          st.session_state["cmp_chart_from"] = cf
          st.session_state["cmp_chart_to"] = ct
          set_preference("compare.chart_from", cf)
          set_preference("compare.chart_to", ct)

      range_label = st.selectbox(
        "Khoảng chart",
        chart_ranges,
        key="cmp_chart_range",
        on_change=_on_cmp_chart_range,
        help="Đặt Chart từ theo cuối cửa sổ (Chart đến) và giới hạn số nến OHLC.",
      )
    with c_from:
      st.date_input(
        "Chart từ",
        min_value=run_from,
        max_value=run_to,
        key="cmp_chart_from",
        on_change=preference_callback("cmp_chart_from", "compare.chart_from"),
      )
    with c_to:
      st.date_input(
        "Chart đến",
        min_value=run_from,
        max_value=run_to,
        key="cmp_chart_to",
        on_change=preference_callback("cmp_chart_to", "compare.chart_to"),
      )
    with c_reset:
      st.write("")  # align with inputs
      if st.button(
        "Full run",
        key="cmp_chart_reset",
        use_container_width=True,
        help="Đặt lại chart = toàn bộ cửa sổ Compare run",
      ):
        st.session_state["_cmp_chart_reset"] = True
        st.rerun()

    chart_from = st.session_state["cmp_chart_from"]
    chart_to = st.session_state["cmp_chart_to"]
    if not isinstance(chart_from, date):
      chart_from = _parse_ui_date(chart_from) or run_from
    if not isinstance(chart_to, date):
      chart_to = _parse_ui_date(chart_to) or run_to
    if chart_to < chart_from:
      st.warning("Chart đến phải ≥ Chart từ")
      chart_to = chart_from

    show_on_chart = st.multiselect(
      "Model hiện trên chart giá",
      chart_labels,
      default=chart_labels,
      key="cmp_price_models",
      help="Tam giác = entry (▲ BUY / ▼ SELL), X = exit. Màu theo model.",
    )
    show_lines = st.checkbox(
      "Nối entry → exit",
      value=True,
      key="cmp_price_connectors",
    )
    max_bars = chart_bars.get(range_label, 672)
    from_txt = chart_from.isoformat() if hasattr(chart_from, "isoformat") else str(chart_from)
    to_txt = chart_to.isoformat() if hasattr(chart_to, "isoformat") else str(chart_to)

    # Stable iframe chart (Plotly.react) — same smooth UX as MT5 Bridge Simulate.
    # Controls write chart_view.json; iframe polls snapshot without Streamlit remount.
    import streamlit.components.v1 as components
    from mt5_bridge.live_monitor_server import (
      COMPARE_MONITOR_PORT,
      ensure_chart_server,
      write_compare_chart_view,
    )

    palette = ("#2962ff", "#26a69a", "#ef6c00", "#8e24aa", "#00897b", "#c62828", "#5d4037")
    models_payload = []
    for i, label in enumerate(show_on_chart):
      mid = None
      for m_id in run.get("model_ids") or []:
        lb = label_by_id.get(m_id) or (get_model_by_id(m_id) or {}).get("label") or m_id
        if lb == label:
          mid = m_id
          break
      if not mid:
        mid = id_by_label.get(label)
      if not mid:
        continue
      models_payload.append({
        "model_id": mid,
        "label": label,
        "color": palette[i % len(palette)],
      })

    write_compare_chart_view({
      "run_id": run_id,
      "date_from": from_txt,
      "date_to": to_txt,
      "max_bars": int(max_bars),
      "show_connectors": bool(show_lines),
      "models": models_payload,
    })

    cmp_url = f"http://127.0.0.1:{COMPARE_MONITOR_PORT}"
    server_ok = ensure_chart_server(port=COMPARE_MONITOR_PORT)
    if server_ok:
      # Stable URL — date/model/max_bars via chart_view.json (keeps pan/zoom like Simulate)
      components.iframe(
        f"{cmp_url}/chart?mode=compare&bars=200000&v=cmp3",
        height=700,
        scrolling=False,
      )
      st.caption(
        "▲▼ entry · ✕ exit · màu theo model · pan/scroll-zoom như Simulate. "
        f"Run gốc: `{run.get('date_from')}` → `{run.get('date_to')}`."
      )
    else:
      st.warning(
        f"Chart server Compare (:{COMPARE_MONITOR_PORT}) chưa chạy — fallback snapshot tĩnh."
      )
      ohlc = load_compare_ohlc(from_txt, to_txt, max_bars=int(max_bars))
      filtered = {k: trades_by_model[k] for k in show_on_chart if k in trades_by_model}
      n_bars = len(ohlc) if ohlc is not None and not ohlc.empty else 0
      price_fig = build_multi_model_price_figure(
        ohlc,
        filtered,
        title=f"Giá M15 · {from_txt} → {to_txt} · {range_label} ({n_bars} bar)",
        show_connectors=bool(show_lines),
      )
      if price_fig is not None:
        st.plotly_chart(price_fig, use_container_width=True)
      elif ohlc is None or ohlc.empty:
        st.warning("Không load được OHLC — đồng bộ history MT5 trước.")
      else:
        st.caption("Chưa có lệnh để vẽ trên chart giá.")

  detail_ids = list(run.get("model_ids") or [])
  if detail_ids:
    detail_labels = [label_by_id.get(m, m) for m in detail_ids]
    pick = st.selectbox("Chi tiết journal theo model", detail_labels, key="cmp_detail_model")
    mid = id_by_label.get(pick) or detail_ids[detail_labels.index(pick)]
    mdir = COMPARE_ROOT / str(run_id) / "models" / str(mid)
    trades = load_trades(mdir)
    if trades:
      st.dataframe(pd.DataFrame(trades), use_container_width=True, hide_index=True)
    else:
      st.caption("Model này chưa có lệnh trong journal.")
