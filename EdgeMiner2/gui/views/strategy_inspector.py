"""4. Strategy Inspector — rules, genomes, active strategy."""
from __future__ import annotations

import streamlit as st

from analytics import genomes_table, rule_stats_table
from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header
from gui.services import load_backtest_report, load_kb
from gui.ui_preferences import preference_callback, restore_widget
from gui.workspace import get_active_workspace


def render(embedded: bool = False):
  if not embedded:
    render_page_header(ALL_ITEMS["analysis"])

  ws = get_active_workspace()
  report = load_backtest_report()
  kb = load_kb(ws.get("kb_profile") or "default")

  tab_rules, tab_genome, tab_active, tab_ml = st.tabs(
    ["Rules (KB)", "Genomes", "Active Strategy", "ML"]
  )

  with tab_rules:
    st.subheader("Rule Memory")
    rules_df = rule_stats_table(kb.rule_stats)
    if rules_df.empty:
      st.info("Chưa có rule stats. Chạy Learning để tích lũy.")
    else:
      restore_widget(
        "si_dir", ["long", "short"],
        preference_key="analysis.strategy_directions",
        options=["long", "short"],
        multiple=True,
      )
      direction = st.multiselect(
        "Direction", ["long", "short"],
        key="si_dir",
        on_change=preference_callback("si_dir", "analysis.strategy_directions"),
      )
      restore_widget("si_min_uses", 3, preference_key="analysis.strategy_min_uses")
      min_uses = st.slider(
        "Min uses", 1, 50, key="si_min_uses",
        on_change=preference_callback("si_min_uses", "analysis.strategy_min_uses"),
      )
      show = rules_df[
        rules_df["direction"].isin(direction) & (rules_df["uses"] >= min_uses)
      ]
      st.dataframe(show.head(100), use_container_width=True, hide_index=True, height=400)
      st.caption(f"{len(show)} rules (top 100)")

  with tab_genome:
    st.subheader("Top Genomes")
    st.caption(
      "Mine v4: tối đa **6 rule LONG + 6 SHORT** — loại rule trùng correlation; "
      "feature regime/session (`regime_trending`, `london_open`, …); "
      "KB chọn strategy khớp regime tuần."
    )
    gdf = genomes_table(kb.genomes)
    if gdf.empty:
      st.info("Chưa có genomes.")
    else:
      st.dataframe(gdf, use_container_width=True, hide_index=True)
      from genome_naming import display_name
      options = {display_name(g.get("name", "?"), g): g for g in kb.genomes[:15]}
      labels = list(options.keys())
      restore_widget(
        "si_genome", labels[0],
        preference_key="analysis.strategy_genome",
        options=labels,
      )
      pick = st.selectbox(
        "Xem DNA", labels, key="si_genome",
        on_change=preference_callback("si_genome", "analysis.strategy_genome"),
      )
      genome = options.get(pick)
      if genome:
        st.json({
          k: genome[k] for k in [
            "fitness", "rr_ratio", "atr_mult_sl", "exit_mode", "ml_prob_min",
            "score_threshold", "min_rules_match", "trail_activate_r", "trail_distance_r",
          ] if k in genome
        })
        c1, c2 = st.columns(2)
        with c1:
          st.markdown("**Long rules**")
          st.json(genome.get("long_rules", [])[:8])
        with c2:
          st.markdown("**Short rules**")
          st.json(genome.get("short_rules", [])[:8])

  with tab_active:
    st.subheader("Strategy tuần gần nhất (từ backtest)")
    strat = report.get("last_strategy") if report else None
    if not strat:
      st.info("Chạy backtest để xem strategy active.")
    else:
      st.json({
        "name": strat.get("name"),
        "exit_mode": strat.get("exit_mode"),
        "rr": strat.get("rr"),
        "atr_mult": strat.get("atr_mult"),
        "ml_prob_min": strat.get("ml_prob_min"),
      })
      c1, c2 = st.columns(2)
      with c1:
        st.markdown("**Long rules**")
        for r in strat.get("long_rules", []):
          st.code(f"{r['feat']} {r['op']} {r['thr']} (w={r['w']})")
      with c2:
        st.markdown("**Short rules**")
        for r in strat.get("short_rules", []):
          st.code(f"{r['feat']} {r['op']} {r['thr']} (w={r['w']})")

      wlog = [w for w in (report.get("weekly_log") or []) if "strategy" in w]
      if wlog:
        st.markdown("**Lịch sử đổi strategy (10 tuần cuối)**")
        import pandas as pd
        st.dataframe(pd.DataFrame(wlog).tail(10), use_container_width=True, hide_index=True)

  with tab_ml:
    st.subheader("ML Experience")
    st.metric("ML samples", len(kb.ml_experience))
    st.metric("Best fitness", round(kb.best_fitness_ever, 1))
    st.metric("Epochs recorded", kb.epoch_count)
    if kb.ml_experience:
      sample = kb.ml_experience[-1]
      st.markdown("**Mẫu gần nhất**")
      st.json({"long_win": sample.get("long_win"), "short_win": sample.get("short_win"),
               "features": list(sample.get("features", {}).keys())[:12]})
