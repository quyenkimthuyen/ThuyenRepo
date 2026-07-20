"""5. Risk / Journal / Inspector"""
from __future__ import annotations

import streamlit as st

from forexforge import services as svc
from forexforge.analytics import (
  direction_bias,
  equity_series,
  exit_reason_stats,
  filter_trades_df,
  genomes_table,
  rule_stats_table,
  trades_json_to_df,
)
from forexforge.store import Store


def render() -> None:
  st.header("5. Risk / Journal / Inspector")
  store = Store()
  rows = store.list_reports(50)
  if not rows:
    st.info("Chua co report.")
    return

  rid = st.selectbox("Report", [r["id"] for r in rows], format_func=lambda i: _label(rows, i))
  report = store.get_report(rid)
  if not report:
    st.error("Khong load duoc report.")
    return

  tab_risk, tab_journal, tab_insp = st.tabs(["Risk", "Journal", "Inspector"])

  o = report.overall_oos
  with tab_risk:
    if o:
      c1, c2, c3, c4 = st.columns(4)
      c1.metric("Max DD R", o.max_drawdown_r)
      c2.metric("Win streak", o.max_win_streak)
      c3.metric("Loss streak", o.max_loss_streak)
      c4.metric("Risk of ruin %", o.risk_of_ruin_pct)
    if report.holdout_forward:
      st.subheader("Hold-out forward")
      st.json(report.holdout_forward.get("metrics") or {})
    trades = _trades(report)
    eq = equity_series(trades)
    if not eq.empty:
      st.line_chart(eq.set_index("entry")[["equity_r", "drawdown_r"]])
    st.subheader("Constraints")
    st.json(report.constraints_met)

  with tab_journal:
    trades = _trades(report)
    if trades.empty:
      st.info("Khong co trades.")
    else:
      years = sorted(trades["entry"].dt.year.dropna().unique().tolist()) if "entry" in trades else []
      year = st.selectbox("Year", ["all"] + [str(y) for y in years])
      direction = st.selectbox("Direction", ["all", "LONG", "SHORT"])
      filtered = filter_trades_df(
        trades,
        year=None if year == "all" else int(year),
        direction=None if direction == "all" else direction,
      )
      st.dataframe(filtered, use_container_width=True)
      st.write("Direction bias")
      st.dataframe(direction_bias(filtered), use_container_width=True)
      st.write("Exit reasons")
      st.dataframe(exit_reason_stats(filtered), use_container_width=True)

  with tab_insp:
    if report.last_strategy:
      st.subheader("Last strategy")
      st.json(report.last_strategy)
    profile = report.spec.kb_profile or "default"
    try:
      kb = svc.kb(profile)
      st.subheader(f"KB rules — {profile}")
      st.dataframe(rule_stats_table(kb.rule_stats), use_container_width=True)
      st.subheader("Genomes")
      st.dataframe(genomes_table(kb.genomes), use_container_width=True)
      st.caption(f"ML samples: {len(kb.ml_experience)}")
    except Exception as exc:
      st.warning(f"Khong load KB: {exc}")


def _label(rows, rid: str) -> str:
  for r in rows:
    if r["id"] == rid:
      kb = "ON" if r.get("use_kb") else "OFF"
      return f"{rid} · KB {kb} · R={r.get('total_r')} · WR={r.get('win_rate_pct')}"
  return rid


def _trades(report):
  trades = [t.model_dump() if hasattr(t, "model_dump") else t for t in report.trades]
  if not trades:
    trades = (report.raw or {}).get("trades") or []
  df = trades_json_to_df(trades)
  if "direction" in df.columns and "dir" not in df.columns:
    df = df.rename(columns={"direction": "dir"})
  if "r" not in df.columns and "pnl_pips" in df.columns:
    pass
  return df
