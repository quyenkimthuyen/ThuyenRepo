"""So sánh ERA / epoch / train window — dùng trong Nghiên cứu."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from gui.components import constraint_checklist, kb_profile_picker, oos_period_inputs
from gui.long_task_background import start_job
from gui.long_task_ui import render_task_status, task_blocks_ui

def render_era_compare():
  import pandas as pd
  from analytics import equity_series, trades_json_to_df
  from gui.era_compare import (
    discover_era_specs, load_era_compare_cache, metrics_row, profile_exists,
  )
  from gui.trade_profile import get_active_trade_profile
  from kb_profiles import get_profile

  st.subheader("So sánh các giai đoạn thị trường")
  st.caption(
    "Chọn **một hoặc nhiều** giai đoạn bộ nhớ để học/so sánh · "
    "Có thể ghép giai đoạn mới tại **Bộ nhớ & học → Ghép giai đoạn**."
  )

  tp = get_active_trade_profile()
  all_specs = discover_era_specs(
    oos_from=tp.get("oos_from") or "2025-01-01",
    oos_to=tp.get("oos_to") or "2026-12-31",
  )
  spec_by_key = {s["key"]: s for s in all_specs}
  default_keys = [s["key"] for s in all_specs if s.get("oos_group") == "2025-2026"]
  if not default_keys:
    default_keys = [s["key"] for s in all_specs[:3]]

  selected_keys = st.multiselect(
    "Chọn giai đoạn cần so sánh",
    options=[s["key"] for s in all_specs],
    default=[k for k in default_keys if k in spec_by_key],
    format_func=lambda k: spec_by_key[k]["label"],
    key="era_cmp_pick",
    help="Chọn 1 hoặc nhiều giai đoạn — chỉ các mục được chọn mới backtest/so sánh.",
  )
  if not selected_keys:
    st.warning("Chọn ít nhất một giai đoạn.")
    return

  selected_specs = [spec_by_key[k] for k in selected_keys if k in spec_by_key]

  render_task_status(key_prefix="era_cmp")
  running = task_blocks_ui("era_cmp")

  rows = []
  for spec in selected_specs:
    p = get_profile(spec["kb_profile"])
    rows.append({
      "Profile": spec["label"],
      "ID": spec["kb_profile"],
      "Bộ nhớ học": f"{spec.get('learn_from') or '?'} → {spec.get('learn_until') or '?'}",
      "Giai đoạn test": f"{spec['oos_from']} → {spec['oos_to']}",
      "Vòng học": (p or {}).get("epochs", spec.get("epochs") or "—"),
      "Sẵn sàng": "✅" if profile_exists(spec["kb_profile"]) else "○",
    })
  st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

  st.markdown("#### Chọn vòng học cho từng giai đoạn đã chọn")
  from gui.kb_epoch_ui import kb_epoch_picker, snapshot_options

  epoch_by_key: dict[str, int | None] = {}
  ncols = min(len(selected_specs), 4)
  cols = st.columns(ncols)
  for i, spec in enumerate(selected_specs):
    with cols[i % ncols]:
      st.caption(spec["label"])
      snap = kb_epoch_picker(
        f"era_cmp_{spec['key']}", spec["kb_profile"],
        show_table=len(snapshot_options(spec["kb_profile"])) > 1,
      )
      epoch_by_key[spec["key"]] = snap

  c1, c2 = st.columns([1, 2])
  with c1:
    learn_reset = st.checkbox("Reset trước khi học", key="era_cmp_reset")
  with c2:
    learn_pick = st.multiselect(
      "Học nhanh (chọn giai đoạn)",
      options=selected_keys,
      default=[],
      format_func=lambda k: spec_by_key[k]["label"],
      key="era_cmp_learn_pick",
      help="Chọn giai đoạn cần huấn luyện thêm trước khi backtest.",
    )

  learn_cols = st.columns(min(len(learn_pick) or 1, 4))
  for i, key in enumerate(learn_pick):
    spec = spec_by_key[key]
    ep_n = spec.get("epochs") or 3
    with learn_cols[i % len(learn_cols)]:
      if st.button(
        f"🧠 Học {spec['kb_profile']}",
        use_container_width=True,
        key=f"era_cmp_learn_{key}",
        disabled=running,
      ):
        try:
          start_job(
            "era_learn",
            {
              "era_key": key,
              "epochs": int(ep_n),
              "reset": learn_reset,
              "label": spec.get("kb_name") or spec["label"],
            },
            label=f"Học {spec['label']}",
          )
          st.rerun()
        except RuntimeError as e:
          st.error(str(e))

  run_bt = st.button(
    "▶ Backtest các giai đoạn đã chọn",
    type="primary",
    use_container_width=True,
    key="era_cmp_bt",
    disabled=running,
  )

  if run_bt:
    try:
      start_job(
        "era_compare",
        {"epoch_by_key": epoch_by_key, "profile_keys": selected_keys},
        label=f"So sánh {len(selected_keys)} giai đoạn",
      )
      st.rerun()
    except RuntimeError as e:
      st.error(str(e))

  cache = load_era_compare_cache()
  reports = st.session_state.get("era_compare_reports") or (cache or {}).get("reports") or {}
  epoch_used = st.session_state.get("era_compare_epochs") or (cache or {}).get("meta", {}).get("epoch_by_key") or {}
  cached_keys = (cache or {}).get("meta", {}).get("keys") or list(reports.keys())
  display_specs = [spec_by_key[k] for k in cached_keys if k in spec_by_key and k in reports]
  if not display_specs:
    display_specs = [s for s in selected_specs if reports.get(s["key"])]

  if not reports:
    st.info("Học profile mới (nếu cần) rồi **Backtest các giai đoạn đã chọn**.")
    return

  if cache and cache.get("updated_at"):
    st.caption(f"Cập nhật lần cuối: `{cache['updated_at']}`")

  cmp_rows = []
  for spec in display_specs:
    snap = epoch_used.get(spec["key"])
    ep_lbl = f"ep{snap}" if snap is not None else "latest"
    cmp_rows.append(metrics_row(spec, reports.get(spec["key"]), epoch_label=ep_lbl))
  st.markdown("#### Bảng so sánh OOS")
  st.dataframe(pd.DataFrame(cmp_rows), use_container_width=True, hide_index=True)

  # So sánh trực tiếp OOS 2025-2026
  oos_2526 = [s for s in display_specs if s.get("oos_group") == "2025-2026"]
  if len(oos_2526) >= 2:
    st.markdown("#### So sánh trực tiếp OOS 2025–2026 (KB dài vs ngắn)")
    sub = []
    for spec in oos_2526:
      rep = reports.get(spec["key"])
      if not rep:
        continue
      o = rep["overall_oos"]
      sub.append({
        "Profile": spec["label"],
        "KB": spec["learn_from"][:4] + "→" + (spec["learn_until"] or "")[:4],
        "WR%": o.get("win_rate_pct"),
        "Total R": o.get("total_r"),
        "DD": o.get("max_drawdown_r"),
      })
    if len(sub) >= 2:
      st.dataframe(pd.DataFrame(sub), hide_index=True, use_container_width=True)
      a, b = sub[0], sub[1]
      st.caption(
        f"Δ R ({b['Profile'].split('→')[0].strip()} vs {a['Profile'].split('→')[0].strip()}): "
        f"**{float(b['Total R']) - float(a['Total R']):+.2f}R** · "
        f"Δ WR: **{float(b['WR%']) - float(a['WR%']):+.1f}%**"
      )

  st.markdown("#### Equity curve (R)")
  fig = go.Figure()
  for spec in display_specs:
    rep = reports.get(spec["key"])
    if not rep:
      continue
    snap = epoch_used.get(spec["key"])
    ep_lbl = f" · ep{snap}" if snap is not None else " · latest"
    eq = equity_series(trades_json_to_df(rep.get("trades", [])))
    if eq.empty:
      continue
    fig.add_trace(go.Scatter(
      x=eq["entry"], y=eq["equity_r"],
      name=spec["label"] + ep_lbl, mode="lines",
    ))
  fig.update_layout(height=420, margin=dict(l=40, r=20, t=40, b=40), legend=dict(orientation="h", y=1.02))
  st.plotly_chart(fig, use_container_width=True)

  st.markdown("#### Drawdown (R)")
  fig_dd = go.Figure()
  for spec in display_specs:
    rep = reports.get(spec["key"])
    if not rep:
      continue
    eq = equity_series(trades_json_to_df(rep.get("trades", [])))
    if eq.empty:
      continue
    fig_dd.add_trace(go.Scatter(
      x=eq["entry"], y=eq["drawdown_r"],
      name=spec["label"], mode="lines",
    ))
  fig_dd.update_layout(height=300, margin=dict(l=40, r=20, t=40, b=40))
  st.plotly_chart(fig_dd, use_container_width=True)

  with st.expander("Chi tiết constraints từng profile"):
    for spec in display_specs:
      rep = reports.get(spec["key"])
      if not rep:
        continue
      st.markdown(f"**{spec['label']}**")
      constraint_checklist(rep.get("constraints_met", {}))


def render_epoch_sweep():
  import pandas as pd
  from analytics import equity_series, trades_json_to_df
  from gui.components import kb_profile_picker, oos_period_inputs
  from gui.epoch_compare import (
    best_oos_epoch, epoch_key_to_snapshot, load_epoch_sweep_cache,
    snapshot_key, sweep_metrics_table,
  )
  from gui.kb_epoch_ui import format_snapshot_label, snapshot_options
  from gui.workspace import get_active_workspace, set_active_workspace

  st.subheader("So sánh các vòng học trong cùng profile")
  st.caption(
    "Chạy kiểm chứng cho **từng vòng học** (vòng 1, 2, …, mới nhất) — "
    "chọn vòng tốt nhất theo **tổng R** trên giai đoạn test, không chỉ kết quả khi học."
  )

  ws = get_active_workspace()
  profile = kb_profile_picker("ep_sw", show_meta=True)
  oos_from, oos_to = oos_period_inputs(
    "ep_sw", profile,
    default_from=st.session_state.get("ep_sw_oos_from", ws.get("oos_from", "")),
    default_to=st.session_state.get("ep_sw_oos_to", ws.get("oos_to", "")),
  )

  snaps = snapshot_options(profile) if profile else []
  if snaps:
    st.markdown("**Các vòng học có sẵn**")
    st.dataframe(pd.DataFrame([
      {
        "Vòng": "Mới nhất" if s.get("cumulative") is None else f"Vòng {s['cumulative']:03d}",
        "Thắng % (khi học)": s.get("win_rate_pct"),
        "R (khi học)": s.get("total_r"),
      }
      for s in snaps
    ]), hide_index=True, use_container_width=True)

  run_sw = st.button("▶ Kiểm chứng mọi vòng học", type="primary", key="ep_sw_run", disabled=task_blocks_ui("ep_sw"))

  render_task_status(key_prefix="ep_sw", compact=True)

  if run_sw and profile:
    try:
      start_job(
        "epoch_sweep",
        {"profile_id": profile, "oos_from": oos_from, "oos_to": oos_to},
        label=f"Sweep epoch · {profile}",
      )
      st.rerun()
    except RuntimeError as e:
      st.error(str(e))

  ctx = st.session_state.get("epoch_sweep_ctx") or {}
  if profile and ctx.get("profile") == profile:
    cache = load_epoch_sweep_cache(profile, ctx.get("oos_from", oos_from), ctx.get("oos_to", oos_to))
  elif profile:
    cache = load_epoch_sweep_cache(profile, oos_from, oos_to)
  else:
    cache = None

  reports = st.session_state.get("epoch_sweep_reports") or (cache or {}).get("reports") or {}
  cache_snaps = (cache or {}).get("snapshots") or snaps

  if not reports:
    st.info("Chọn profile + giai đoạn kiểm chứng → **Kiểm chứng mọi vòng học**.")
    return

  if cache and cache.get("updated_at"):
    st.caption(f"Cập nhật: `{cache['updated_at']}` · kiểm chứng `{cache.get('oos_from')}` → `{cache.get('oos_to')}`")

  table = sweep_metrics_table(cache_snaps, reports)
  st.markdown("#### Khi học vs khi kiểm chứng (theo vòng)")
  st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)

  best_key, best_r = best_oos_epoch(cache_snaps, reports)
  if best_key is not None and best_r is not None:
    st.success(f"**Tốt nhất khi kiểm chứng:** `{best_key}` · **{best_r:+.2f}R** (lưu vào cấu hình bên dưới)")
    b1, b2 = st.columns(2)
    with b1:
      if st.button("✓ Dùng vòng tốt nhất → Cấu hình giao dịch", key="ep_sw_set_best"):
        snap = epoch_key_to_snapshot(best_key)
        set_active_workspace(
          kb_profile=profile,
          kb_snapshot=snap,
          oos_from=oos_from,
          oos_to=oos_to,
        )
        st.toast(f"Workspace: {profile} · {best_key}")
        st.rerun()
    with b2:
      sel_ep = st.selectbox(
        "Hoặc chọn vòng thủ công",
        [snapshot_key(s) for s in cache_snaps],
        format_func=lambda k: next(
          (format_snapshot_label(s) for s in cache_snaps if snapshot_key(s) == k), k,
        ),
        key="ep_sw_manual",
      )
      if st.button("Áp dụng vòng đã chọn", key="ep_sw_set_manual"):
        set_active_workspace(
          kb_profile=profile,
          kb_snapshot=epoch_key_to_snapshot(sel_ep),
          oos_from=oos_from,
          oos_to=oos_to,
        )
        st.rerun()

  st.markdown("#### Lợi nhuận kiểm chứng theo vòng")
  fig = go.Figure()
  for s in cache_snaps:
    key = snapshot_key(s)
    rep = reports.get(key)
    if not rep:
      continue
    ep = "Latest" if s.get("cumulative") is None else f"ep{s['cumulative']:03d}"
    eq = equity_series(trades_json_to_df(rep.get("trades", [])))
    if eq.empty:
      continue
    oos_r = rep.get("overall_oos", {}).get("total_r", 0)
    fig.add_trace(go.Scatter(
      x=eq["entry"], y=eq["equity_r"],
      name=f"{ep} ({oos_r:+.1f}R OOS)", mode="lines",
    ))
  fig.update_layout(height=420, margin=dict(l=40, r=20, t=40, b=40), legend=dict(orientation="h", y=1.02))
  st.plotly_chart(fig, use_container_width=True)


def render_train_window():
  import pandas as pd
  from analytics import equity_series, trades_json_to_df
  from gui.components import kb_profile_picker, oos_period_inputs
  from gui.train_window_compare import (
    DEFAULT_SPEC, TRAIN_MONTHS_OPTIONS, best_combo, load_train_window_cache,
    metrics_table, result_key,
  )
  from gui.workspace import get_active_workspace

  st.subheader("So sánh cửa sổ học (3 / 6 / 12 tháng)")
  st.caption(
    "Mỗi tuần tìm chiến lược trên **N tháng** data gần nhất · "
    "So có bộ nhớ vs không bộ nhớ cho từng độ dài."
  )

  ws = get_active_workspace()
  c1, c2 = st.columns(2)
  with c1:
    kb_profile = kb_profile_picker("tw", show_meta=True)
  with c2:
    oos_from, oos_to = oos_period_inputs(
      "tw", kb_profile,
      default_from=ws.get("oos_from", DEFAULT_SPEC["oos_from"]),
      default_to=ws.get("oos_to", DEFAULT_SPEC["oos_to"]),
    )

  train_opts = st.multiselect(
    "Cửa sổ học (tháng)", TRAIN_MONTHS_OPTIONS,
    default=TRAIN_MONTHS_OPTIONS, key="tw_months",
  )

  if st.button("▶ Chạy so sánh (cửa sổ × bộ nhớ)", type="primary", key="tw_run", disabled=task_blocks_ui("tw")):
    if not train_opts:
      st.warning("Chọn ít nhất một train window.")
    else:
      try:
        start_job(
          "train_window",
          {
            "train_months_list": train_opts,
            "oos_from": oos_from,
            "oos_to": oos_to,
            "kb_profile": kb_profile or DEFAULT_SPEC["kb_profile"],
          },
          label="So sánh train window",
        )
        st.rerun()
      except RuntimeError as e:
        st.error(str(e))

  render_task_status(key_prefix="tw", compact=True)

  cache = load_train_window_cache()
  reports = st.session_state.get("tw_reports") or (cache or {}).get("reports") or {}
  months = train_opts or (cache or {}).get("train_months_list") or TRAIN_MONTHS_OPTIONS

  if not reports:
    st.info("Chọn profile + giai đoạn kiểm chứng → **Chạy so sánh**.")
    return

  if cache and cache.get("updated_at"):
    st.caption(
      f"Cập nhật: `{cache['updated_at']}` · OOS `{cache.get('oos_from')}` → `{cache.get('oos_to')}` · "
      f"KB profile: `{cache.get('kb_profile')}`"
    )

  table = metrics_table(reports, months)
  st.markdown("#### Bảng so sánh")
  st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)

  best = best_combo(reports, months)
  if best:
    st.success(f"**Tốt nhất OOS:** `{best[0]}` · **{best[1]:+.2f}R**")

  st.markdown("#### Có bộ nhớ vs không bộ nhớ (tổng R)")
  fig = go.Figure()
  for use_kb, color, name in [(False, "#95a5a6", "Không bộ nhớ"), (True, "#2ecc71", "Có bộ nhớ")]:
    xs, ys = [], []
    for tm in months:
      rep = reports.get(result_key(tm, use_kb))
      if rep:
        xs.append(f"{tm} tháng")
        ys.append(rep["overall_oos"]["total_r"])
    if xs:
      fig.add_trace(go.Bar(x=xs, y=ys, name=name, marker_color=color))
  fig.update_layout(barmode="group", height=360, title="Tổng R (kiểm chứng)", margin=dict(l=40, r=20, t=50, b=40))
  st.plotly_chart(fig, use_container_width=True)

  st.markdown("#### Đường lợi nhuận kiểm chứng")
  fig2 = go.Figure()
  for tm in months:
    for use_kb in (False, True):
      key = result_key(tm, use_kb)
      rep = reports.get(key)
      if not rep:
        continue
      eq = equity_series(trades_json_to_df(rep.get("trades", [])))
      if eq.empty:
        continue
      tag = "KB ON" if use_kb else "KB OFF"
      r = rep["overall_oos"]["total_r"]
      fig2.add_trace(go.Scatter(
        x=eq["entry"], y=eq["equity_r"],
        name=f"{tm}m {tag} ({r:+.1f}R)", mode="lines",
      ))
  fig2.update_layout(height=440, margin=dict(l=40, r=20, t=40, b=40), legend=dict(orientation="h", y=1.02))
  st.plotly_chart(fig2, use_container_width=True)

