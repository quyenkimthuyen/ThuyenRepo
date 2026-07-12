#!/usr/bin/env python3
"""BestTrade — Pin Bar Elite with paper trading & forward validation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import plotly.graph_objects as go
import streamlit as st

from besttrade.analytics import (
    bootstrap_monte_carlo,
    collect_oos_trades,
    monthly_breakdown,
    monthly_stability_score,
    quarterly_breakdown,
    stress_spread_comparison,
)
from besttrade.engine import STRATEGY_NAME, equity_curve, load_strategy_config, run_multi_year, run_year_backtest
from besttrade.forward import compare_forward_backtest, forward_paper_metrics
from besttrade.params import (
    active_params,
    load_forward_test,
    locked_params,
    locked_risk,
    params_equal,
    start_forward_test,
    stop_forward_test,
)
from besttrade.paper import run_paper_once
from besttrade.paths import ensure_systemtrain_on_path
from besttrade.store import load_journal, load_paper_state, reset_paper
from besttrade.ui.components import fmt_pct, hero, inject_styles, metric_grid, strategy_card, trades_table_rows, validated_banner
from besttrade.ui.styles import CUSTOM_CSS

ensure_systemtrain_on_path()

from systemtrain.ui.charts import render_professional_chart  # noqa: E402
from systemtrain.ui.meta import STRATEGIES  # noqa: E402

st.set_page_config(page_title="BestTrade — Pin Bar Elite", page_icon="📌", layout="wide", initial_sidebar_state="expanded")
inject_styles(CUSTOM_CSS)

cfg = load_strategy_config()
val = cfg.get("validation", {}).get("metrics", {})
locked = locked_params()
risk_locked = locked_risk()

# Session defaults
if "equity" not in st.session_state:
    st.session_state.equity = 1000.0
if "sandbox_mode" not in st.session_state:
    st.session_state.sandbox_mode = False
if "sandbox_params" not in st.session_state:
    st.session_state.sandbox_params = dict(locked)
if "backtest_cache" not in st.session_state:
    st.session_state.backtest_cache = None
if "trade_year" not in st.session_state:
    st.session_state.trade_year = 2024

# ── Sidebar ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📌 BestTrade")
    st.caption("Pin Bar Elite · EURUSD 1H")

    mode = st.radio(
        "Chế độ",
        ["Validated (khóa)", "Sandbox (thử)"],
        index=1 if st.session_state.sandbox_mode else 0,
        help="Validated: dùng params đã kiểm chứng, bắt buộc cho forward test. Sandbox: chỉnh thử, không dùng live.",
    )
    st.session_state.sandbox_mode = mode.startswith("Sandbox")

    st.session_state.equity = st.number_input("Vốn ($)", min_value=100.0, value=float(st.session_state.equity), step=100.0)
    if st.session_state.sandbox_mode:
        risk_pct = st.number_input("Risk/lệnh (%)", min_value=0.5, max_value=5.0, value=risk_locked["sl_pct"] * 100, step=0.1)
        target_rr = st.number_input("RR", min_value=1.0, max_value=5.0, value=risk_locked["min_rr"], step=0.1)
    else:
        risk_pct = risk_locked["sl_pct"] * 100
        target_rr = risk_locked["min_rr"]
        st.info(f"Risk **{risk_pct:.1f}%** · RR **{target_rr:.1f}R** (khóa)")
    sl_pct = risk_pct / 100.0

    forward = load_forward_test()
    if forward and forward.get("status") == "active":
        st.success(f"Forward test active từ {forward['started_at'][:10]}")
    elif forward and forward.get("status") == "stopped":
        st.warning("Forward test đã dừng")

    if st.session_state.sandbox_mode:
        st.divider()
        st.markdown("**Sandbox params**")
        sp = st.session_state.sandbox_params
        sp["min_htf_adx"] = st.slider("4H ADX min", 18.0, 30.0, float(sp.get("min_htf_adx", locked["min_htf_adx"])), 1.0)
        sp["max_adx_1h"] = st.slider("1H ADX max", 22.0, 40.0, float(sp.get("max_adx_1h", locked["max_adx_1h"])), 1.0)
        sp["min_wick_body_ratio"] = st.slider("Wick/body", 2.5, 5.0, float(sp.get("min_wick_body_ratio", locked["min_wick_body_ratio"])), 0.5)
        sp["min_wick_range_ratio"] = st.slider("Wick/range", 0.45, 0.65, float(sp.get("min_wick_range_ratio", locked["min_wick_range_ratio"])), 0.02)
        sp["swing_lookback"] = st.slider("Swing LB", 6, 20, int(sp.get("swing_lookback", locked["swing_lookback"])), 1)
        sp["htf_mode"] = st.selectbox("4H filter", ["stack", "strict", "soft"], index=["stack", "strict", "soft"].index(str(sp.get("htf_mode", "stack"))))
        st.session_state.sandbox_params = sp
        if st.button("↺ Reset sandbox"):
            st.session_state.sandbox_params = dict(locked)
            st.rerun()
    else:
        with st.expander("Params khóa (validated)"):
            st.json(locked)

    active = active_params(st.session_state.sandbox_mode, st.session_state.sandbox_params)
    if not st.session_state.sandbox_mode and not params_equal(active, locked):
        st.error("Params lệch khỏi profile validated!")

# ── Header ──────────────────────────────────────────────────────────────
hero(
    "BestTrade",
    "Paper trading + forward test blind + Monte Carlo — bước tiếp theo trước khi trade thật.",
    badges=["Pin Bar Elite", "Forward Test", "Monte Carlo"],
)

validated_banner(
    f"OOS validated: {val.get('trade_count', 18)} lệnh · WR {val.get('win_rate', 0.61):.0%} · "
    f"PF {val.get('profit_factor', 2.9):.2f} · Return {val.get('total_return', 0.33):.0%}"
)

tab_dash, tab_paper, tab_analytics, tab_backtest, tab_chart, tab_strategy = st.tabs(
    ["Dashboard", "Paper & Forward", "Analytics", "Backtest", "Chart", "Chiến lược"]
)

params = active_params(st.session_state.sandbox_mode, st.session_state.sandbox_params)

# ══════════════════════════════════════════════════════════════════════════
# Dashboard
# ══════════════════════════════════════════════════════════════════════════
with tab_dash:
    paper_state = load_paper_state()
    fwd_m = forward_paper_metrics(paper_state) if paper_state else {"active": False, "trade_count": 0}

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Historical OOS (validated)")
        metric_grid([
            ("Return", fmt_pct(val.get("total_return", 0.33)), "pos"),
            ("Win Rate", f"{val.get('win_rate', 0.61):.0%}", "accent"),
            ("PF", f"{val.get('profit_factor', 2.9):.2f}", "pos"),
            ("Max DD", f"{val.get('max_drawdown', 0.04):.0%}", ""),
        ])
    with c2:
        st.markdown("#### Forward test (live paper)")
        if fwd_m.get("active"):
            metric_grid([
                ("Lệnh", str(fwd_m.get("trade_count", 0)), ""),
                ("WR", f"{fwd_m.get('win_rate', 0):.0%}", "accent"),
                ("PF", f"{fwd_m.get('profit_factor', 0):.2f}", "pos" if fwd_m.get("profit_factor", 0) >= 1 else "neg"),
                ("Return", fmt_pct(fwd_m.get("total_return", 0)), "pos" if fwd_m.get("total_return", 0) >= 0 else "neg"),
            ])
        else:
            st.info("Chưa bắt đầu forward test. Vào tab **Paper & Forward** để khởi động.")

    oos_trades = collect_oos_trades([2023, 2024, 2025], st.session_state.equity)
    mc = bootstrap_monte_carlo(oos_trades, st.session_state.equity)
    st.markdown("#### Monte Carlo (OOS trades 2023–2025)")
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Mô phỏng dương", f"{mc['positive_pct']:.0%}")
    mc2.metric("Return median", fmt_pct(mc["median_return"]))
    mc3.metric("P5 return", fmt_pct(mc["p5_return"]))
    mc4.metric("Worst DD (P95)", f"{mc['worst_drawdown_p95']:.0%}")
    st.caption(f"**{mc['verdict']}** — {mc['trade_count']} lệnh, {mc['simulations']} simulations")

    strategy_card("Lộ trình khuyến nghị", "1) Forward test 3–6 tháng với params khóa → 2) So sánh paper vs backtest → 3) Trade thủ công size nhỏ → 4) Mới cân nhắc semi-auto.")

# ══════════════════════════════════════════════════════════════════════════
# Paper & Forward
# ══════════════════════════════════════════════════════════════════════════
with tab_paper:
    st.markdown("#### Paper trading (không broker)")
    st.caption("Đánh giá tín hiệu trên nến 1H đã đóng — giống live nhưng không gửi lệnh thật.")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("▶ Chạy paper 1 lần", type="primary"):
            try:
                result = run_paper_once(
                    equity=st.session_state.equity,
                    refresh_data=False,
                    sandbox=st.session_state.sandbox_mode,
                    sandbox_params=st.session_state.sandbox_params if st.session_state.sandbox_mode else None,
                    sl_pct=sl_pct,
                    min_rr=target_rr,
                )
                st.session_state.paper_result = result
                st.success(f"Bar mới nhất: {result['latest_bar'][:16]} · Events: {len(result['events'])}")
            except Exception as e:
                st.error(str(e))
    with col_b:
        refresh = st.checkbox("Refresh data Dukascopy", value=False)
        if st.button("🔄 Refresh & chạy"):
            try:
                result = run_paper_once(
                    equity=st.session_state.equity, refresh_data=refresh,
                    sandbox=st.session_state.sandbox_mode,
                    sandbox_params=st.session_state.sandbox_params if st.session_state.sandbox_mode else None,
                    sl_pct=sl_pct, min_rr=target_rr,
                )
                st.session_state.paper_result = result
                st.rerun()
            except Exception as e:
                st.error(str(e))
    with col_c:
        if st.button("🗑 Reset paper", help="Xóa state và journal paper"):
            reset_paper()
            st.session_state.pop("paper_result", None)
            st.rerun()

    st.divider()
    st.markdown("#### Forward test blind")
    f1, f2, f3 = st.columns(3)
    with f1:
        if st.button("🚀 Bắt đầu forward test", disabled=st.session_state.sandbox_mode):
            if st.session_state.sandbox_mode:
                st.warning("Tắt Sandbox trước khi bắt đầu forward test.")
            else:
                start_forward_test(st.session_state.equity)
                reset_paper()
                st.success("Đã khóa params và reset paper. Forward test bắt đầu.")
                st.rerun()
    with f2:
        if st.button("⏹ Dừng forward test"):
            stop_forward_test()
            st.info("Forward test đã dừng.")
            st.rerun()
    with f3:
        st.caption("Forward test yêu cầu chế độ **Validated** và params khóa.")

    paper_state = load_paper_state()
    if paper_state:
        st.markdown("**Trạng thái paper**")
        ps1, ps2, ps3, ps4 = st.columns(4)
        ps1.metric("Equity", f"${paper_state.get('equity', 0):,.2f}")
        ps2.metric("Status", paper_state.get("status", "—"))
        ps3.metric("Lệnh đóng", len(paper_state.get("closed_trades", [])))
        ps4.metric("Bar cuối", str(paper_state.get("latest_bar", ""))[:16])

        if paper_state.get("open_trade"):
            t = paper_state["open_trade"]
            st.warning(f"Đang mở: {t.get('direction', '?')} @ {t.get('entry_time', '')[:16]} · SL {t.get('sl_price', 0):.5f}")

        fwd = load_forward_test()
        if fwd and fwd.get("status") == "active" and paper_state:
            st.markdown("**So sánh Forward: Paper vs Backtest**")
            try:
                cmp = compare_forward_backtest(st.session_state.equity, sl_pct, target_rr, paper_state)
                if "error" not in cmp:
                    cm1, cm2, cm3 = st.columns(3)
                    cm1.metric("Paper return", fmt_pct(cmp["paper"].get("total_return", 0)))
                    cm2.metric("Backtest return", fmt_pct(cmp["backtest"].get("total_return", 0)))
                    cm3.metric("Delta", fmt_pct(cmp["delta_return"]))
                    st.caption(
                        f"Kỳ: {cmp['period']['start'][:10]} → {cmp['period']['end'][:10]} · "
                        f"Paper {cmp['paper'].get('trade_count', 0)} lệnh vs BT {cmp['backtest'].get('trade_count', 0)} lệnh"
                    )
            except Exception as e:
                st.error(f"So sánh lỗi: {e}")

        with st.expander("Journal gần đây"):
            journal = load_journal(30)
            if journal:
                st.dataframe(
                    [{"event": j.get("event"), "time": j.get("updated_at", "")[:19], "dir": j.get("trade", {}).get("direction")} for j in journal],
                    use_container_width=True, hide_index=True,
                )
            else:
                st.caption("Chưa có journal.")

# ══════════════════════════════════════════════════════════════════════════
# Analytics
# ══════════════════════════════════════════════════════════════════════════
with tab_analytics:
    trades = collect_oos_trades([2023, 2024, 2025], st.session_state.equity)

    st.markdown("#### Phân tích theo tháng")
    months = monthly_breakdown(trades, st.session_state.equity)
    stab = monthly_stability_score(trades)
    st.caption(f"Monthly stability: **{stab:.0%}** tháng có lãi (OOS 2023–2025)")
    if months:
        st.dataframe(months, use_container_width=True, hide_index=True)

    st.markdown("#### Phân tích theo quý")
    quarters = quarterly_breakdown(trades, st.session_state.equity)
    if quarters:
        st.dataframe(quarters, use_container_width=True, hide_index=True)

    st.markdown("#### Stress test spread")
    st.caption("Backtest cùng params validated, thay đổi spread giả định.")
    stress = stress_spread_comparison([2023, 2024, 2025], st.session_state.equity, sl_pct, target_rr)
    st.dataframe(stress, use_container_width=True, hide_index=True)

    st.markdown("#### Monte Carlo bootstrap")
    mc = bootstrap_monte_carlo(trades, st.session_state.equity, simulations=2000)
    fig = go.Figure()
    if mc["trade_count"] > 0:
        # Re-run for histogram
        import numpy as np
        pnls = np.array([t.pnl for t in trades])
        rng = np.random.default_rng(42)
        finals = []
        for _ in range(500):
            shuffled = rng.permutation(pnls)
            eq = st.session_state.equity + shuffled.sum()
            finals.append(eq / st.session_state.equity - 1)
        fig.add_trace(go.Histogram(x=finals, nbinsx=30, marker_color="#f0b429", opacity=0.85))
        fig.update_layout(
            title="Phân phối return (bootstrap shuffle)",
            height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#12161f",
            font=dict(color="#8b93a7"), xaxis=dict(gridcolor="#2a3142", title="Return"),
            yaxis=dict(gridcolor="#2a3142", title="Count"),
        )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.info(mc["verdict"])

# ══════════════════════════════════════════════════════════════════════════
# Backtest
# ══════════════════════════════════════════════════════════════════════════
with tab_backtest:
    if st.session_state.sandbox_mode:
        st.warning("Đang ở Sandbox — kết quả chỉ để thử, không thay thế validated profile.")

    b1, b2 = st.columns(2)
    with b1:
        year = st.selectbox("Năm", list(range(2021, 2027)), index=3)
    with b2:
        multi = st.multiselect("Nhiều năm", [], default=[])

    if st.button("Chạy backtest", type="primary"):
        years = multi if multi else [year]
        with st.spinner("Backtesting..."):
            st.session_state.backtest_cache = run_multi_year(
                years, params, st.session_state.equity, sl_pct, target_rr,
            )

    if st.session_state.backtest_cache:
        for r in st.session_state.backtest_cache:
            m = r.metrics
            st.markdown(f"### {r.year}")
            metric_grid([
                ("Lệnh", str(m.get("trade_count", 0)), ""),
                ("WR", f"{m.get('win_rate', 0):.0%}", ""),
                ("PF", f"{m.get('profit_factor', 0):.2f}", ""),
                ("Return", fmt_pct(m.get("total_return", 0)), "pos" if m.get("total_return", 0) >= 0 else "neg"),
            ])
            if r.trades:
                curve = equity_curve(r.trades, st.session_state.equity)
                if not curve.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=curve["time"], y=curve["equity"], mode="lines", line=dict(color="#f0b429", width=2)))
                    fig.update_layout(height=200, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#12161f")
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                st.dataframe(trades_table_rows(r.trades), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════
# Chart
# ══════════════════════════════════════════════════════════════════════════
with tab_chart:
    chart_year = st.selectbox("Năm chart", list(range(2021, 2027)), index=3)
    if st.button("Tải chart", type="primary"):
        with st.spinner("..."):
            st.session_state.chart_result = run_year_backtest(
                chart_year, params, st.session_state.equity, sl_pct, target_rr,
            )
    cr = st.session_state.get("chart_result")
    if cr and cr.year == chart_year:
        try:
            render_professional_chart(
                cr.period_df, STRATEGY_NAME, cr.trades,
                chart_id=f"bt-{chart_year}", show_ema=False, equity=st.session_state.equity, height=680,
            )
        except Exception as e:
            st.error(str(e))

# ══════════════════════════════════════════════════════════════════════════
# Strategy
# ══════════════════════════════════════════════════════════════════════════
with tab_strategy:
    st.markdown(STRATEGIES.get(STRATEGY_NAME, {}).get("description", ""))
    st.markdown("#### Workflow BestTrade")
    st.markdown("""
1. **Validated mode** — params khóa, dùng cho forward test
2. **Paper trading** — chạy định kỳ (cron/15 phút) để bắt tín hiệu
3. **Forward test** — so sánh paper vs backtest trên cùng kỳ
4. **Analytics** — Monte Carlo, monthly stability, stress spread
5. **Sandbox** — chỉ thử ý tưởng, không dùng cho quyết định live
    """)
    st.json({"locked_params": locked, "risk": risk_locked})
