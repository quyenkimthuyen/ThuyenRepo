"""KB & Giai đoạn — tạo nhiều KB, backtest OOS theo từng profile."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from kb_profiles import DEFAULT_PROFILE_ID, delete_profile, get_profile, list_profiles
from gui.components import (
  ERA_PRESETS, constraint_checklist, kpi_row,
  kb_profile_and_epoch_picker, kb_profile_picker, kb_validation_banner,
  list_kb_profiles_df, oos_period_inputs, suggested_oos_range,
)
from gui.services import execute_backtest, execute_learning, load_backtest_report, load_learning_report


def _epoch_chart(history: list[dict]):
  if not history:
    return None
  epochs = [h["epoch"] for h in history]
  fig = go.Figure()
  fig.add_trace(go.Scatter(x=epochs, y=[h["win_rate_pct"] for h in history],
                           name="WR%", line=dict(color="#3498db")))
  fig.add_trace(go.Scatter(x=epochs, y=[h["total_r"] for h in history],
                           name="Total R", yaxis="y2", line=dict(color="#2ecc71")))
  fig.update_layout(
    title="Tiến bộ Epoch (in-sample giai đoạn học)",
    yaxis=dict(title="Win Rate %"),
    yaxis2=dict(title="Total R", overlaying="y", side="right"),
    height=320, margin=dict(l=40, r=40, t=50, b=40),
  )
  return fig


def _tab_profiles():
  st.subheader("Danh sách KB Profiles")
  pdf = list_kb_profiles_df()
  if pdf.empty:
    st.info("Chưa có profile. Dùng tab **Học KB** để tạo profile đầu tiên.")
  else:
    show = [c for c in ["id", "name", "trained_from", "trained_to", "epochs", "exists"] if c in pdf.columns]
    st.dataframe(pdf[show], use_container_width=True, hide_index=True)

  sel = st.selectbox(
    "Xem snapshot epoch của profile",
    [p["id"] for p in list_profiles() if p.get("exists") and p["id"] != DEFAULT_PROFILE_ID],
    key="hub_snap_profile",
  ) if list_profiles() else None
  if sel:
    from kb_profiles import list_snapshots
    import pandas as pd
    snaps = [s for s in list_snapshots(sel) if s.get("cumulative")]
    if snaps:
      st.dataframe(pd.DataFrame(snaps)[["cumulative", "label", "win_rate_pct", "total_r"]],
                   use_container_width=True, hide_index=True)
    else:
      st.caption("Chưa có snapshot từng epoch — chạy học mới để tạo ep001, ep002, …")

  st.markdown("#### Preset giai đoạn phổ biến")
  for label, pid, lf, lt, of, ot in ERA_PRESETS:
    exists = any(p["id"] == pid and p.get("exists") for p in list_profiles())
    icon = "✅" if exists else "○"
    c1, c2 = st.columns([3, 1])
    with c1:
      st.caption(f"{icon} **{label}** — học `{lf}→{lt}`, backtest OOS `{of}→{ot}`")
    with c2:
      if st.button("Dùng preset", key=f"preset_{pid}"):
        st.session_state["hub_learn_id"] = pid
        st.session_state["hub_learn_name"] = label.split("→")[0].strip()
        st.session_state["hub_learn_from"] = lf
        st.session_state["hub_learn_until"] = lt
        st.session_state["hub_bt_profile"] = pid
        st.session_state["hub_bt_oos_from"] = of
        st.session_state["hub_bt_oos_to"] = ot
        st.session_state["hub_tab"] = 1
        st.rerun()

  st.divider()
  c1, c2 = st.columns(2)
  with c1:
    del_candidates = [p["id"] for p in list_profiles() if p["id"] != DEFAULT_PROFILE_ID]
    if del_candidates:
      del_id = st.selectbox("Xóa profile", del_candidates, key="hub_del")
      if st.button("Xóa profile", type="secondary", key="hub_del_btn"):
        delete_profile(del_id)
        st.warning(f"Đã xóa **{del_id}**")
        st.rerun()
  with c2:
    pick = st.selectbox(
      "Chọn profile → backtest",
      [p["id"] for p in list_profiles() if p.get("exists")],
      key="hub_goto_bt",
    ) if list_profiles() else None
    if pick and st.button("Mở tab Backtest", key="hub_goto_bt_btn"):
      of, ot = suggested_oos_range(pick)
      st.session_state["hub_bt_profile"] = pick
      st.session_state["hub_bt_oos_from"] = of
      st.session_state["hub_bt_oos_to"] = ot
      st.session_state["hub_tab"] = 2
      st.rerun()


def _tab_learn():
  st.subheader("Học KB theo giai đoạn")
  st.caption("Mỗi profile = một file KB riêng, gắn khoảng `trained_from` → `trained_to`.")

  c1, c2 = st.columns(2)
  with c1:
    new_id = st.text_input("Profile ID", st.session_state.get("hub_learn_id", "era_2022_2023"), key="hub_learn_id")
    new_name = st.text_input("Tên hiển thị", st.session_state.get("hub_learn_name", "Era 2022-2023"), key="hub_learn_name")
    learn_from = st.text_input("Học từ", st.session_state.get("hub_learn_from", "2022-01-01"), key="hub_learn_from")
  with c2:
    learn_until = st.text_input("Học đến", st.session_state.get("hub_learn_until", "2023-12-31"), key="hub_learn_until")
    epochs = st.number_input("Số epoch", 1, 30, 3, key="hub_epochs")
    reset = st.checkbox("Reset profile trước khi học", key="hub_reset")

  existing = get_profile(new_id.strip())
  if existing and existing.get("exists"):
    st.info(f"Profile **{new_id}** đã tồn tại — học tiếp sẽ **cộng dồn** KB (trừ khi bật Reset).")

  if st.button("▶ Học & lưu profile", type="primary", key="hub_learn_run"):
    prog = st.progress(0)

    def on_ep(ep, total, _):
      prog.progress(ep / total, text=f"Epoch {ep}/{total}")

    with st.spinner("Đang học..."):
      report = execute_learning(
        epochs=int(epochs), reset_kb=reset,
        kb_profile=new_id.strip(), kb_name=new_name,
        from_date=learn_from, until_date=learn_until or None,
        on_epoch_done=on_ep,
      )
    st.session_state["learning_report"] = report
    prog.empty()
    st.success(f"Đã lưu **{new_id}** ({learn_from} → {learn_until})")
    st.rerun()

  learning = st.session_state.get("learning_report") or load_learning_report()
  if learning:
    st.markdown("#### Kết quả học gần nhất")
    st.caption(
      f"Profile **{learning.get('kb_profile')}** · "
      f"{learning.get('trained_from')} → {learning.get('trained_to')}"
    )
    history = learning.get("epoch_history", [])
    if history:
      import pandas as pd
      st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
      fig = _epoch_chart(history)
      if fig:
        st.plotly_chart(fig, use_container_width=True)


def _tab_backtest():
  st.subheader("Backtest OOS theo KB & giai đoạn")
  st.caption("Chọn profile đã học **trước** giai đoạn OOS → không dùng thông tin tương lai.")

  c1, c2, c3 = st.columns(3)
  with c1:
    spread = st.number_input("Spread (pip)", 0.0, 3.0, 1.0, 0.1, key="hub_spread")
  with c2:
    slip = st.number_input("Slippage (pip)", 0.0, 2.0, 0.3, 0.1, key="hub_slip")
  with c3:
    train_mo = st.selectbox("Train window (tháng)", [2, 3, 4, 6], index=1, key="hub_train")

  kb_profile, kb_snapshot = kb_profile_and_epoch_picker("hub_bt", show_meta=True)
  st.markdown("**Giai đoạn OOS cần test**")
  oos_from, oos_to = oos_period_inputs(
    "hub_bt", kb_profile,
    default_from=st.session_state.get("hub_bt_oos_from", ""),
    default_to=st.session_state.get("hub_bt_oos_to", ""),
  )
  if kb_profile:
    kb_validation_banner(kb_profile, oos_from)

  compare_kb_off = st.checkbox("Chạy thêm bản KB OFF để so sánh", key="hub_compare_off")

  if st.button("▶ Chạy Backtest", type="primary", key="hub_bt_run"):
    results = {}
    prog = st.progress(0)

    def on_prog(step, total, _):
      prog.progress(step / total, text=f"WF {step}/{total}")

    with st.spinner("Backtest KB ON..."):
      results["kb_on"] = execute_backtest(
        use_learning=True, train_months=train_mo,
        spread_pips=spread, slippage_pips=slip,
        kb_profile=kb_profile or DEFAULT_PROFILE_ID,
        kb_snapshot=kb_snapshot,
        oos_from=oos_from or None, oos_to=oos_to or None,
        on_progress=on_prog, archive=True,
        archive_label=f"KB ON ep{kb_snapshot or 'latest'} · {kb_profile} · OOS {oos_from}→{oos_to}",
      )
    if compare_kb_off:
      with st.spinner("Backtest KB OFF..."):
        results["kb_off"] = execute_backtest(
          use_learning=False, train_months=train_mo,
          spread_pips=spread, slippage_pips=slip,
          oos_from=oos_from or None, oos_to=oos_to or None,
          on_progress=on_prog, archive=True,
          archive_label=f"KB OFF · OOS {oos_from}→{oos_to}",
        )
    st.session_state["hub_backtest_results"] = results
    st.session_state["backtest_report"] = results["kb_on"]
    prog.empty()
    st.rerun()

  results = st.session_state.get("hub_backtest_results", {})
  report = results.get("kb_on") or load_backtest_report()
  if not report:
    st.info("Chọn profile + OOS rồi nhấn **Chạy Backtest**.")
    return

  if "kb_off" in results:
    st.markdown("#### So sánh KB ON vs OFF")
    st.caption("Đã lưu vào **Report Compare** — mở trang đó để xem lịch sử đầy đủ.")
    on, off = results["kb_on"]["overall_oos"], results["kb_off"]["overall_oos"]
    import pandas as pd
    cmp_df = pd.DataFrame([
      {"Mode": "KB ON", "Lệnh": on["n_trades"], "WR%": on["win_rate_pct"],
       "RR": on["avg_rr"], "Total R": on["total_r"], "DD": on.get("max_drawdown_r")},
      {"Mode": "KB OFF", "Lệnh": off["n_trades"], "WR%": off["win_rate_pct"],
       "RR": off["avg_rr"], "Total R": off["total_r"], "DD": off.get("max_drawdown_r")},
    ])
    st.dataframe(cmp_df, use_container_width=True, hide_index=True)
    delta_r = on["total_r"] - off["total_r"]
    st.metric("KB ON − OFF (Total R)", f"{delta_r:+.2f}R")

  cfg = report.get("config", {})
  st.caption(
    f"Profile: **{cfg.get('kb_profile', '-')}** · "
    f"Epoch: **{cfg.get('kb_snapshot') or 'latest'}** · "
    f"OOS: **{cfg.get('oos_from') or 'auto'} → {cfg.get('oos_to') or 'auto'}** · "
    f"Spread {cfg.get('spread_pips')} / Slip {cfg.get('slippage_pips')}"
  )
  o = report["overall_oos"]
  kpi_row([
    ("OOS WR", f"{o['win_rate_pct']}%", None),
    ("RR", f"{o['avg_rr']}", None),
    ("Total R", f"{o['total_r']}", None),
    ("Max DD", f"{o.get('max_drawdown_r', 0)}R", None),
    ("Lệnh/tuần", f"{o['trades_per_week']}", f"{o['n_trades']} lệnh"),
  ])
  constraint_checklist(report.get("constraints_met", {}))


def render():
  st.header("KB & Giai đoạn")
  st.caption("Tạo nhiều Knowledge Base theo thời gian · Backtest OOS đúng profile · không leakage")

  st.info(
    "**Quy trình:** (1) Tab **Học KB** — tạo profile `era_2022_2023` trên 2022–2023 · "
    "(2) Tab **Backtest** — chọn profile đó, OOS `2024-01-01 → 2024-12-31` · "
    "Hệ thống kiểm tra `trained_to ≤ oos_from`."
  )

  tab_names = ["📋 Profiles", "🧠 Học KB", "📊 Backtest OOS"]
  tab_idx = st.session_state.get("hub_tab", 0)
  selected = st.radio("Bước", tab_names, horizontal=True, index=min(tab_idx, 2), key="hub_tab_radio")
  st.session_state["hub_tab"] = tab_names.index(selected)

  st.divider()
  if selected == tab_names[0]:
    _tab_profiles()
  elif selected == tab_names[1]:
    _tab_learn()
  else:
    _tab_backtest()
