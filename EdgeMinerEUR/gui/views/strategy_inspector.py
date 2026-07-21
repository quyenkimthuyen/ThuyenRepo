"""Strategy Inspector — rules, genomes, active strategy."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics import genomes_table, rule_stats_table
from gui.analysis_support import get_matching_analysis_report
from gui.analysis_viz import render_strategy_cards
from gui.services import load_kb
from gui.workspace import get_active_workspace


def render(embedded: bool = False):
  ws = get_active_workspace()
  report = get_matching_analysis_report() or {}
  kb = load_kb(ws.get("kb_profile") or "default")

  tab_active, tab_rules, tab_genome, tab_ml = st.tabs([
    "⚡ Strategy hiện tại",
    "📚 Rule Memory",
    "🧬 Genomes",
    "🤖 ML",
  ])

  with tab_active:
    strat = report.get("last_strategy")
    if not strat:
      st.info("Chạy backtest / tạo báo cáo phân tích để xem strategy tuần gần nhất.")
    else:
      render_strategy_cards(strat)
      wlog = [w for w in (report.get("weekly_log") or []) if w.get("strategy")]
      if wlog:
        st.markdown("**Lịch sử đổi strategy (10 tuần cuối)**")
        rows = []
        for w in wlog[-10:]:
          s = w.get("strategy")
          if isinstance(s, dict):
            name = s.get("name", "—")
            exit_m = s.get("exit_mode", "—")
            rr = s.get("rr", "—")
          else:
            name = str(s) if s else "—"
            exit_m = "—"
            rr = "—"
          rows.append({
            "Tuần": w.get("week_start", "—"),
            "Tên": name,
            "Exit": exit_m,
            "RR": rr,
            "R tuần": w.get("oos_r", "—"),
          })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

  with tab_rules:
    rules_df = rule_stats_table(kb.rule_stats)
    if rules_df.empty:
      st.info("Chưa có rule stats — huấn luyện bộ nhớ trước.")
    else:
      direction = st.multiselect("Hướng", ["long", "short"], default=["long", "short"], key="si_dir")
      min_uses = st.slider("Tối thiểu lần dùng", 1, 50, 3, key="si_min_uses")
      show = rules_df[rules_df["direction"].isin(direction) & (rules_df["uses"] >= min_uses)]
      st.dataframe(show.head(100), use_container_width=True, hide_index=True, height=400)
      st.caption(f"{len(show)} rules (top 100)")

  with tab_genome:
    gdf = genomes_table(kb.genomes)
    if gdf.empty:
      st.info("Chưa có genomes.")
    else:
      st.dataframe(gdf, use_container_width=True, hide_index=True)
      from genome_naming import display_name
      options = {display_name(g.get("name", "?"), g): g for g in kb.genomes[:15]}
      pick = st.selectbox("Xem DNA chi tiết", list(options.keys()), key="si_genome")
      genome = options.get(pick)
      if genome:
        render_strategy_cards({
          "name": genome.get("name"),
          "exit_mode": genome.get("exit_mode"),
          "rr": genome.get("rr_ratio"),
          "atr_mult": genome.get("atr_mult_sl"),
          "ml_prob_min": genome.get("ml_prob_min"),
          "max_hold_bars": genome.get("max_hold_bars"),
          "min_bars_between": genome.get("min_bars_between"),
          "trail_activate_r": genome.get("trail_activate_r"),
          "trail_distance_r": genome.get("trail_distance_r"),
          "long_rules": [
            {"feat": r["feature"], "op": r["op"], "thr": r["threshold"], "w": r["weight"]}
            for r in genome.get("long_rules", [])
          ],
          "short_rules": [
            {"feat": r["feature"], "op": r["op"], "thr": r["threshold"], "w": r["weight"]}
            for r in genome.get("short_rules", [])
          ],
        })

  with tab_ml:
    c1, c2, c3 = st.columns(3)
    c1.metric("ML samples", len(kb.ml_experience))
    c2.metric("Best fitness", round(kb.best_fitness_ever, 1))
    c3.metric("Epochs", kb.epoch_count)
    if kb.ml_experience:
      sample = kb.ml_experience[-1]
      with st.expander("Mẫu ML gần nhất"):
        st.json({
          "long_win": sample.get("long_win"),
          "short_win": sample.get("short_win"),
          "features": list(sample.get("features", {}).keys())[:12],
        })
