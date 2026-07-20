"""2. Backtest Lab — KB OFF default"""
from __future__ import annotations

import streamlit as st

from forexforge import services as svc
from forexforge.leakage import LeakageError
from forexforge.store import Store
from forexforge.ui.helpers import equity_chart, job_progress_panel, leakage_banner, metric_row


def render() -> None:
  st.header("2. Backtest Lab")
  st.success("Buoc 2/6 — Do baseline. Lan dau: de KB OFF (dung tick KB ON).")
  st.caption("Giong Backtest Lab ban cu. Ket qua luu vao Report Compare.")

  c1, c2, c3 = st.columns(3)
  oos_from = c1.text_input("OOS from", "2024-01-01")
  oos_to = c2.text_input("OOS to", "2024-12-31")
  train_months = c3.number_input("Train months", 1, 12, 3)

  c4, c5, c6 = st.columns(3)
  spread = c4.number_input("Spread pips", 0.0, 10.0, 1.0, 0.1)
  slip = c5.number_input("Slippage pips", 0.0, 5.0, 0.3, 0.1)
  holdout = c6.number_input("Hold-out months", 0, 24, 0)

  use_kb = st.checkbox("KB ON (chi bat sau khi da hoc era)", value=False)
  profile = st.text_input("KB profile", "default", disabled=not use_kb)
  label = st.text_input("Ten report", "kb_off_baseline" if not use_kb else f"kb_on_{profile}")

  if use_kb:
    check = svc.leakage_status(profile, oos_from)
    leakage_banner(check.ok, check.message)
    if not check.ok:
      st.stop()

  bg = st.checkbox("Chay nen (khuyen nghi — UI khong treo)", value=True)
  col_a, col_b = st.columns(2)

  if col_a.button("Run backtest", type="primary"):
    try:
      if bg:
        jid = svc.submit_backtest_job(
          use_kb=use_kb,
          spread_pips=float(spread),
          slippage_pips=float(slip),
          train_months=int(train_months),
          holdout_months=int(holdout),
          kb_profile=profile,
          oos_from=oos_from,
          oos_to=oos_to,
          label=label,
        )
        st.session_state["bt_job"] = jid
        st.success(f"Da queue job_id={jid}. Bam Refresh de xem tien do. Xong thi sang Report Compare.")
      else:
        with st.spinner("Running walk-forward..."):
          report, rid = svc.run_backtest_sync(
            use_kb=use_kb,
            spread_pips=float(spread),
            slippage_pips=float(slip),
            train_months=int(train_months),
            holdout_months=int(holdout),
            kb_profile=profile,
            oos_from=oos_from,
            oos_to=oos_to,
            label=label,
          )
        st.session_state["last_report"] = report
        st.session_state["last_report_id"] = rid
        st.success(f"Xong report_id={rid}")
    except LeakageError as exc:
      st.error(str(exc))
    except Exception as exc:
      st.error(str(exc))

  if col_b.button("Refresh job status"):
    st.rerun()

  job_progress_panel(Store(), st.session_state.get("bt_job"))

  report = st.session_state.get("last_report")
  if report is not None:
    metric_row(report)
    trades = [t.model_dump() if hasattr(t, "model_dump") else t for t in (report.trades or [])]
    norm = []
    for t in trades:
      row = dict(t)
      if "direction" in row and "r" in row:
        row["dir"] = row.get("direction")
      norm.append(row)
    equity_chart(norm)
    with st.expander("Weekly log"):
      st.dataframe(report.weekly_log, width="stretch")

  st.caption("Tiep theo: **3. KB Era Hub** (hoc) hoac **4. Report Compare** (xem ket qua job nen).")
