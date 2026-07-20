"""1. Data Hub"""
from __future__ import annotations

import streamlit as st

from forexforge import services as svc
from forexforge.store import Store


def render() -> None:
  st.header("1. Data Hub")
  st.success("Buoc 1/6 — Lay gia EUR/USD H1. Xong roi chuyen sang Backtest Lab.")
  st.caption("Giong nut Refresh Data o Command Center ban cu.")

  meta = svc.load_data_meta()
  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Bars", meta.get("bars", "—"))
  c2.metric("Start", str(meta.get("start", "—"))[:10])
  c3.metric("End", str(meta.get("end", "—"))[:10])
  c4.metric("Fetched", str(meta.get("fetched_at", "—"))[:19])

  start = st.text_input("Data from", "2022-01-01")
  if st.button("Refresh Data (Dukascopy)", type="primary"):
    with st.spinner("Downloading..."):
      try:
        df = svc.refresh_market_data(start)
        st.success(f"OK — {len(df)} bars · {df.index[0].date()} → {df.index[-1].date()}")
        st.rerun()
      except Exception as exc:
        st.error(str(exc))

  st.subheader("Jobs (theo doi tien do)")
  store = Store()
  rows = store.list_runs(10)
  if rows:
    st.dataframe(rows, width="stretch")
  else:
    st.info("Chua co job. Sau khi Run backtest / learning se hien o day.")

  st.subheader("Profiles KB")
  st.dataframe(svc.profiles(), width="stretch")
  st.caption("Tiep theo: menu **2. Backtest Lab** (KB OFF).")
