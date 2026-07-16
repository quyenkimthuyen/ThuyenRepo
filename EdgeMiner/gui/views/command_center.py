"""1. Command Center — dashboard tổng quan."""
from __future__ import annotations

import streamlit as st

from analytics import direction_bias, trades_json_to_df, yearly_breakdown
from gui.components import constraint_checklist, kpi_row, status_banner, warn_long_bias, warn_no_costs
from gui.services import execute_backtest, load_backtest_report, load_data_meta, load_kb, load_learning_report, refresh_market_data


def render():
  st.header("Command Center")
  st.caption("Tổng quan nhanh — KPI, mục tiêu, hành động chính")

  report = load_backtest_report()
  learning = load_learning_report()
  kb = load_kb()
  data_meta = load_data_meta()

  kb_summary = learning.get("kb_summary", {}) if learning else {
    "genomes": len(kb.genomes),
    "rules": len(kb.rule_stats),
    "ml_samples": len(kb.ml_experience),
  }

  status_banner(report, kb_summary, data_meta)
  warn_no_costs()

  if report:
    o = report["overall_oos"]
    y = report["last_1_year"]
    kpi_row([
      ("OOS Win Rate", f"{o['win_rate_pct']}%", f"1Y: {y['win_rate_pct']}%"),
      ("RR", f"{o['avg_rr']}", f"1Y: {y['avg_rr']}"),
      ("Total R", f"{o['total_r']}", None),
      ("Trades/week", f"{o['trades_per_week']}", f"{o['n_trades']} lệnh"),
      ("Max DD", f"{o.get('max_drawdown_r', 0)}R", f"1Y: {y.get('max_drawdown_r', 0)}R"),
    ])

    st.subheader("Mục tiêu")
    constraint_checklist(report.get("constraints_met", {}))

    trades_df = trades_json_to_df(report.get("trades", []))
    if not trades_df.empty:
      bias = direction_bias(trades_df)
      if not bias.empty and "LONG" in bias["dir"].values:
        pct = bias.loc[bias["dir"] == "LONG", "pct"].iloc[0]
        warn_long_bias(pct)

    with st.expander("OOS theo năm"):
      st.dataframe(yearly_breakdown(trades_df), use_container_width=True, hide_index=True)
  else:
    st.warning("Chưa có kết quả backtest. Dùng Quick Actions bên dưới.")

  st.divider()
  st.subheader("Quick Actions")

  c1, c2, c3, c4 = st.columns(4)
  with c1:
    use_kb = st.toggle("Dùng KB", value=False, key="cc_use_kb")
  with c2:
    train_mo = st.selectbox("Train", [3, 2, 4], index=0, key="cc_train_mo")
  with c3:
    spread = st.number_input("Spread", 0.0, 3.0, 1.0, 0.1, key="cc_spread")
  with c4:
    slip = st.number_input("Slippage", 0.0, 2.0, 0.3, 0.1, key="cc_slip")
  holdout = st.selectbox("Hold-out (tháng)", [0, 6, 12], index=0, key="cc_holdout")
  epochs = st.number_input("Learning epochs", 1, 20, 2, key="cc_epochs")

  b1, b2, b3 = st.columns(3)
  with b1:
    if st.button("▶ Run Backtest", type="primary", use_container_width=True):
      if use_kb:
        st.session_state["show_kb_warn"] = True
      prog = st.progress(0, text="Walk-forward...")
      status = st.empty()

      def on_prog(step, total, week_start):
        prog.progress(step / total, text=f"Tuần {step}/{total} — {week_start.date()}")

      with st.spinner("Đang chạy walk-forward..."):
        report = execute_backtest(
          use_learning=use_kb, train_months=train_mo,
          spread_pips=spread, slippage_pips=slip, holdout_months=holdout,
          on_progress=on_prog,
        )
      st.session_state["backtest_report"] = report
      prog.empty()
      status.success(f"Xong — {report['overall_oos']['n_trades']} lệnh OOS")
      st.rerun()

  with b2:
    if st.button("🧠 Run Learning", use_container_width=True):
      prog = st.progress(0, text="Learning...")
      with st.spinner(f"Chạy {epochs} epoch..."):
        def on_ep(ep, total, state):
          prog.progress(ep / total, text=f"Epoch {ep}/{total}")

        execute_learning(epochs=int(epochs), on_epoch_done=on_ep)
      prog.empty()
      st.success(f"Hoàn thành {epochs} epoch")
      st.rerun()

  with b3:
    if st.button("🔄 Refresh Data", use_container_width=True):
      with st.spinner("Tải Dukascopy..."):
        refresh_market_data()
      st.success("Đã cập nhật data cache")
      st.rerun()

  if st.session_state.get("show_kb_warn") and use_kb:
    st.warning("Backtest vừa chạy với KB ON — xem cảnh báo trong Backtest Lab.")
