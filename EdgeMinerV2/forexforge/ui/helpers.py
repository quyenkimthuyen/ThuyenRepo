"""Shared Streamlit UI helpers."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from forexforge.analytics import equity_series, trades_json_to_df
from forexforge.contracts import Report
from forexforge.store import Store


def metric_row(report: Report | dict | None) -> None:
  if report is None:
    st.info("Chua co report.")
    return
  if isinstance(report, Report):
    o = report.overall_oos
    if not o:
      st.warning("Report khong co overall_oos.")
      return
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Trades", o.n_trades)
    c2.metric("WR %", o.win_rate_pct)
    c3.metric("Avg RR", o.avg_rr)
    c4.metric("Total R", o.total_r)
    c5.metric("Max DD R", o.max_drawdown_r)
  else:
    o = report.get("overall_oos") or {}
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Trades", o.get("n_trades"))
    c2.metric("WR %", o.get("win_rate_pct"))
    c3.metric("Avg RR", o.get("avg_rr"))
    c4.metric("Total R", o.get("total_r"))
    c5.metric("Max DD R", o.get("max_drawdown_r"))


def equity_chart(trades: list[dict]) -> None:
  df = trades_json_to_df(trades)
  # normalize dir/r keys from TradeRecord
  if not df.empty and "direction" in df.columns and "dir" not in df.columns:
    df = df.rename(columns={"direction": "dir"})
  eq = equity_series(df)
  if eq.empty:
    st.caption("Khong du trades de ve equity.")
    return
  st.line_chart(eq.set_index("entry")[["equity_r", "drawdown_r"]])


def job_progress_panel(store: Store, job_id: str | None) -> None:
  if not job_id:
    return
  run = store.get_run(job_id)
  ev = store.latest_event(job_id)
  if not run:
    st.warning(f"Job {job_id} khong tim thay.")
    return
  st.write(f"**Job** `{job_id}` · status=`{run['status']}`")
  if ev and ev.get("total"):
    st.progress(min(ev["current"] / max(ev["total"], 1), 1.0))
    st.caption(f"{ev['current']}/{ev['total']} · {ev.get('message','')}")
  if run.get("error"):
    st.error(run["error"])


def leakage_banner(ok: bool, message: str) -> None:
  if ok:
    st.success(message)
  else:
    st.error(f"LEAKAGE BLOCK — {message}")
