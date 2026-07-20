"""6. Paper Monitor"""
from __future__ import annotations

import streamlit as st

from forexforge.paper_sim import load_journal, load_paper_state, run_paper_tick
from forexforge.broker import StubBroker, BrokerOrder


def render() -> None:
  st.header("6. Paper Monitor")
  st.caption("Signal + simulated fill theo cost model. Journal tu dong. Live broker = phase rieng.")

  c1, c2, c3 = st.columns(3)
  use_kb = c1.checkbox("KB ON", value=False)
  profile = c2.text_input("KB profile", "default", disabled=not use_kb)
  spread = c3.number_input("Spread", 0.0, 10.0, 1.0, 0.1)
  slip = st.number_input("Slippage", 0.0, 5.0, 0.3, 0.1)

  if st.button("Paper tick (refresh week)", type="primary"):
    with st.spinner("Mining current week..."):
      mon = run_paper_tick(
        use_kb=use_kb,
        kb_profile=profile if use_kb else None,
        spread_pips=float(spread),
        slippage_pips=float(slip),
      )
    st.session_state["paper_mon"] = mon

  mon = st.session_state.get("paper_mon") or load_paper_state().get("last_monitor")
  state = load_paper_state()
  st.write(f"Enabled: **{state.get('enabled')}** · last_tick: `{state.get('last_tick', '—')}`")

  if isinstance(mon, dict) and mon.get("error"):
    st.error(mon["error"])
  elif isinstance(mon, dict) and mon.get("week_start"):
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Week", mon.get("week_start", "—"))
    k2.metric("Trades", mon.get("week_trades_taken", mon.get("trades", "—")))
    k3.metric("WR %", mon.get("week_wr", "—"))
    k4.metric("Total R", mon.get("week_total_r", "—"))
    if mon.get("strategy"):
      st.subheader("Active strategy")
      st.json(mon["strategy"])
    if mon.get("signals_this_week") is not None:
      st.subheader("Signals")
      st.dataframe(mon.get("signals_this_week") or [], use_container_width=True)
    if mon.get("orders") is not None:
      st.subheader("Orders / fills (cost model)")
      st.dataframe(mon.get("orders") or [], use_container_width=True)
    if mon.get("recent_trades") is not None:
      st.subheader("Closed trades")
      st.dataframe(mon.get("recent_trades") or [], use_container_width=True)

  st.subheader("Journal (jsonl)")
  st.dataframe(load_journal(50), use_container_width=True)

  with st.expander("Broker adapter stub (not live)"):
    st.write("MT5/OANDA adapters se implement BrokerAdapter — khong merge vao core miner.")
    if st.button("Dry-run stub order"):
      broker = StubBroker()
      fill = broker.place_market(
        BrokerOrder(symbol="EURUSD", side="BUY", volume=0.01, comment="paper-dry")
      )
      st.json(fill.__dict__)
