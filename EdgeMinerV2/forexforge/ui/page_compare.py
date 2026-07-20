"""4. Report Compare"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from forexforge.analytics import equity_series, trades_json_to_df
from forexforge.store import Store


def render() -> None:
  st.header("4. Report Compare")
  st.success("Buoc so sanh — KB OFF vs KB ON. Chi tin so, khong cam tinh.")
  st.caption("Giong Report Compare ban cu.")

  store = Store()
  rows = store.list_reports(100)
  if not rows:
    st.info("Chua co report. Chay Backtest Lab truoc.")
    return

  st.dataframe(rows, width="stretch")
  ids = st.multiselect(
    "Chon 2–4 reports",
    options=[r["id"] for r in rows],
    default=[r["id"] for r in rows[:2]] if len(rows) >= 2 else [rows[0]["id"]],
  )
  if len(ids) < 2:
    st.warning("Chon it nhat 2 reports (vd 1 KB OFF + 1 KB ON).")
    return

  compared = store.compare_reports(ids)
  st.subheader("Metrics")
  st.dataframe(pd.DataFrame(compared), width="stretch")

  base = compared[0]
  deltas = []
  for row in compared[1:]:
    deltas.append({
      "id": row["id"],
      "d_WR": (row.get("win_rate_pct") or 0) - (base.get("win_rate_pct") or 0),
      "d_RR": (row.get("avg_rr") or 0) - (base.get("avg_rr") or 0),
      "d_R": (row.get("total_r") or 0) - (base.get("total_r") or 0),
      "d_trades": (row.get("n_trades") or 0) - (base.get("n_trades") or 0),
    })
  if deltas:
    st.subheader(f"Delta vs {base['id']}")
    st.dataframe(pd.DataFrame(deltas), width="stretch")

  st.subheader("Equity overlay")
  chart_frames = []
  for rid in ids:
    rep = store.get_report(rid)
    if not rep:
      continue
    trades = [t.model_dump() if hasattr(t, "model_dump") else t for t in rep.trades]
    df = trades_json_to_df(trades)
    if df.empty:
      raw_trades = (rep.raw or {}).get("trades") or []
      df = trades_json_to_df(raw_trades)
    if "direction" in df.columns and "dir" not in df.columns:
      df = df.rename(columns={"direction": "dir"})
    eq = equity_series(df)
    if eq.empty:
      continue
    s = eq.set_index("entry")["equity_r"].rename(rid)
    chart_frames.append(s)
  if chart_frames:
    st.line_chart(pd.concat(chart_frames, axis=1).ffill())
  else:
    st.caption("Reports khong co trades de ve equity.")
