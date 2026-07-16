"""5. Learning Center — epochs, tiến bộ, cảnh báo overfit."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from gui.services import execute_learning, load_kb, load_learning_report


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
    title="Tiến bộ qua Epoch",
    yaxis=dict(title="Win Rate %"),
    yaxis2=dict(title="Total R", overlaying="y", side="right"),
    height=360, margin=dict(l=40, r=40, t=50, b=40),
  )
  return fig


def render():
  st.header("Learning Center")
  st.caption("Self-learning v4 — epoch, KB, cảnh báo overfit")

  learning = load_learning_report()
  kb = load_kb()

  st.warning(
    "⚠️ **Overfit risk:** Chạy nhiều epoch trên cùng dataset làm WR tăng dần nhưng "
    "không chứng minh dự đoán tương lai. Luôn xác nhận bằng backtest **KB OFF**."
  )

  c1, c2, c3 = st.columns(3)
  with c1:
    epochs = st.number_input("Số epoch", 1, 30, 2, key="lc_epochs")
  with c2:
    reset = st.checkbox("Reset KB trước khi chạy", key="lc_reset")
  with c3:
    st.write("")
    if st.button("▶ Start Learning", type="primary", use_container_width=True):
      prog = st.progress(0, text="Epoch 0")

      def on_ep(ep, total, _state):
        prog.progress(ep / total, text=f"Epoch {ep}/{total}")

      with st.spinner("Learning..."):
        learning = execute_learning(epochs=int(epochs), reset_kb=reset, on_epoch_done=on_ep)
      st.session_state["learning_report"] = learning
      prog.empty()
      st.success("Learning hoàn tất")
      st.rerun()

  learning = st.session_state.get("learning_report") or learning

  m1, m2, m3, m4 = st.columns(4)
  summary = learning.get("kb_summary", {}) if learning else {}
  m1.metric("Genomes", summary.get("genomes", len(kb.genomes)))
  m2.metric("Rules tracked", summary.get("rules", len(kb.rule_stats)))
  m3.metric("ML samples", summary.get("ml_samples", len(kb.ml_experience)))
  m4.metric("Best fitness", round(summary.get("best_fitness", kb.best_fitness_ever), 1))

  history = learning.get("epoch_history", []) if learning else kb.epoch_history
  if history:
    st.subheader("Epoch comparison")
    import pandas as pd
    hdf = pd.DataFrame(history)
    cols = [c for c in ["epoch", "n_trades", "win_rate_pct", "avg_rr", "total_r",
                        "genomes_in_kb", "rules_tracked", "ml_samples"] if c in hdf.columns]
    st.dataframe(hdf[cols], use_container_width=True, hide_index=True)

    fig = _epoch_chart(history)
    if fig:
      st.plotly_chart(fig, use_container_width=True)

    if len(history) >= 2:
      first, last = history[0], history[-1]
      d_wr = last.get("win_rate_pct", 0) - first.get("win_rate_pct", 0)
      d_r = last.get("total_r", 0) - first.get("total_r", 0)
      st.info(
        f"Δ Epoch {first.get('epoch')}→{last.get('epoch')}: "
        f"WR **{d_wr:+.1f}%** | Total R **{d_r:+.1f}**"
      )
  else:
    st.info("Chưa có lịch sử epoch. Nhấn Start Learning.")

  st.subheader("KB epoch history (disk)")
  if kb.epoch_history:
    import pandas as pd
    st.dataframe(pd.DataFrame(kb.epoch_history).tail(20), use_container_width=True, hide_index=True)
  else:
    st.caption("Trống")

  st.caption(kb.improvement_summary())
