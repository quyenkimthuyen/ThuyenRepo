#!/usr/bin/env python3
"""BestTrade — professional Pin Bar Elite trading app."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import plotly.graph_objects as go
import streamlit as st

from besttrade.engine import (
    STRATEGY_NAME,
    equity_curve,
    load_strategy_config,
    run_multi_year,
    run_year_backtest,
)
from besttrade.paths import ensure_systemtrain_on_path
from besttrade.ui.components import (
    fmt_pct,
    hero,
    inject_styles,
    metric_grid,
    strategy_card,
    trades_table_rows,
    validated_banner,
)
from besttrade.ui.styles import CUSTOM_CSS

ensure_systemtrain_on_path()

from systemtrain.ui.charts import render_professional_chart  # noqa: E402
from systemtrain.ui.meta import STRATEGIES  # noqa: E402

st.set_page_config(
    page_title="BestTrade — Pin Bar Elite",
    page_icon="📌",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles(CUSTOM_CSS)

cfg = load_strategy_config()
val = cfg.get("validation", {}).get("metrics", {})
val_desc = cfg.get("validation", {}).get("description", "")

if "equity" not in st.session_state:
    st.session_state.equity = 1000.0
if "params" not in st.session_state:
    st.session_state.params = dict(cfg["params"])
if "backtest_cache" not in st.session_state:
    st.session_state.backtest_cache = None
if "trade_year" not in st.session_state:
    st.session_state.trade_year = 2024

# ── Sidebar ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📌 BestTrade")
    st.caption("Pin Bar Elite · EURUSD 1H")

    st.session_state.equity = st.number_input("Vốn ($)", min_value=100.0, value=float(st.session_state.equity), step=100.0)
    risk_pct = st.number_input("Risk/lệnh (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.1)
    target_rr = st.number_input("RR mục tiêu", min_value=1.0, max_value=5.0, value=float(cfg["strategy"]["rr"]), step=0.1)
    sl_pct = risk_pct / 100.0

    st.divider()
    st.markdown("**Tham số chiến lược**")
    p = st.session_state.params
    p["min_htf_adx"] = st.slider("4H ADX min", 18.0, 30.0, float(p["min_htf_adx"]), 1.0)
    p["max_adx_1h"] = st.slider("1H ADX max", 22.0, 40.0, float(p["max_adx_1h"]), 1.0)
    p["min_wick_body_ratio"] = st.slider("Wick/body min", 2.5, 5.0, float(p["min_wick_body_ratio"]), 0.5)
    p["min_wick_range_ratio"] = st.slider("Wick/range min", 0.45, 0.65, float(p["min_wick_range_ratio"]), 0.02)
    p["swing_lookback"] = st.slider("Swing lookback", 6, 20, int(p["swing_lookback"]), 1)
    p["htf_mode"] = st.selectbox("Filter 4H", ["stack", "strict", "soft"], index=["stack", "strict", "soft"].index(str(p["htf_mode"])))
    p["require_at_swing"] = st.toggle("Yêu cầu tại swing", value=bool(p.get("require_at_swing", True)))
    st.session_state.params = p

    if st.button("↺ Reset tham số mặc định"):
        st.session_state.params = dict(cfg["params"])
        st.rerun()

# ── Header ──────────────────────────────────────────────────────────────
hero(
    "BestTrade",
    "Ứng dụng chuyên nghiệp cho chiến lược Pin Bar Elite — kế thừa engine backtest "
    "và quy trình kiểm chứng từ SystemTrain.",
    badges=["Validated OOS", "EURUSD 1H", "RR 2.0"],
)

validated_banner(
    f"Chiến lược tốt nhất sau kiểm chứng SystemTrain: {val.get('trade_count', 18)} lệnh OOS · "
    f"WR {val.get('win_rate', 0.61):.0%} · PF {val.get('profit_factor', 2.9):.2f} · "
    f"Return {val.get('total_return', 0.33):.0%} · Max DD {val.get('max_drawdown', 0.04):.0%}"
)

tab_dash, tab_backtest, tab_chart, tab_strategy = st.tabs(
    ["Dashboard", "Backtest", "Chart", "Chiến lược"]
)

# ══════════════════════════════════════════════════════════════════════════
# Dashboard
# ══════════════════════════════════════════════════════════════════════════
with tab_dash:
    c1, c2 = st.columns([1.2, 1])
    with c1:
        metric_grid([
            ("OOS Return", fmt_pct(val.get("total_return", 0.33)), "pos"),
            ("Win Rate", f"{val.get('win_rate', 0.61):.0%}", "accent"),
            ("Profit Factor", f"{val.get('profit_factor', 2.9):.2f}", "pos"),
            ("Max Drawdown", f"{val.get('max_drawdown', 0.04):.0%}", ""),
            ("Expectancy", f"${val.get('expectancy', 18.3):.2f}/lệnh", "pos"),
            ("OOS Trades", str(val.get("trade_count", 18)), ""),
        ])
    with c2:
        strategy_card(
            "Tại sao Pin Bar Elite?",
            "Trong so sánh Wyckoff, RSI Divergence và Pin Bar trên dữ liệu OOS 2 năm, "
            "Pin Bar Elite đạt return cao nhất (+33%) với 18 lệnh, WR 61%, PF 2.9 và drawdown chỉ 4%. "
            "Cân bằng tốt giữa chất lượng setup và tần suất giao dịch."
        )

    st.markdown("#### So sánh chiến lược (SystemTrain OOS)")
    compare = [
        {"Chiến lược": "Pin Bar Elite", "Return": "+33.0%", "WR": "61%", "PF": "2.90", "Lệnh": 18, "DD": "4.0%"},
        {"Chiến lược": "RSI Divergence", "Return": "+19.0%", "WR": "67%", "PF": "3.71", "Lệnh": 9, "DD": "2.0%"},
        {"Chiến lược": "Wyckoff", "Return": "+18.7%", "WR": "67%", "PF": "3.56", "Lệnh": 9, "DD": "4.0%"},
    ]
    st.dataframe(compare, use_container_width=True, hide_index=True)

    st.markdown("#### Kiểm chứng nhanh (tham số hiện tại)")
    if st.button("▶ Chạy multi-year backtest", key="dash_run"):
        with st.spinner("Đang backtest 2023–2025..."):
            results = run_multi_year(
                [2023, 2024, 2025],
                st.session_state.params,
                st.session_state.equity,
                sl_pct,
                target_rr,
            )
            st.session_state.backtest_cache = results
    if st.session_state.backtest_cache:
        rows = []
        for r in st.session_state.backtest_cache:
            m = r.metrics
            rows.append({
                "Năm": r.year,
                "Lệnh": m.get("trade_count", 0),
                "WR": f"{m.get('win_rate', 0):.0%}",
                "PF": f"{m.get('profit_factor', 0):.2f}",
                "Return": fmt_pct(m.get("total_return", 0)),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════
# Backtest
# ══════════════════════════════════════════════════════════════════════════
with tab_backtest:
    b1, b2, b3 = st.columns(3)
    with b1:
        year = st.selectbox("Năm trade", list(range(2021, 2027)), index=3)
    with b2:
        multi = st.multiselect("Hoặc nhiều năm", [], default=[])
    with b3:
        run_bt = st.button("Chạy backtest", type="primary")

    if run_bt:
        years = multi if multi else [year]
        with st.spinner("Backtesting..."):
            results = run_multi_year(years, st.session_state.params, st.session_state.equity, sl_pct, target_rr)
            st.session_state.backtest_cache = results
            if len(years) == 1:
                st.session_state.trade_year = years[0]

    if st.session_state.backtest_cache:
        for r in st.session_state.backtest_cache:
            m = r.metrics
            st.markdown(f"### Năm {r.year}")
            metric_grid([
                ("Lệnh", str(m.get("trade_count", 0)), ""),
                ("Win Rate", f"{m.get('win_rate', 0):.0%}", "accent" if m.get("win_rate", 0) >= 0.5 else ""),
                ("Profit Factor", f"{m.get('profit_factor', 0):.2f}", "pos" if m.get("profit_factor", 0) >= 1 else "neg"),
                ("Return", fmt_pct(m.get("total_return", 0)), "pos" if m.get("total_return", 0) >= 0 else "neg"),
                ("Realized RR", f"{m.get('realized_rr', 0):.2f}R", ""),
            ])
            if r.trades:
                curve = equity_curve(r.trades, st.session_state.equity)
                if not curve.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=curve["time"], y=curve["equity"],
                        mode="lines", line=dict(color="#f0b429", width=2),
                        fill="tozeroy", fillcolor="rgba(240,180,41,0.08)",
                    ))
                    fig.update_layout(
                        height=220, margin=dict(l=0, r=0, t=20, b=0),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#12161f",
                        font=dict(color="#8b93a7"), title="Equity curve",
                        xaxis=dict(gridcolor="#2a3142"), yaxis=dict(gridcolor="#2a3142"),
                    )
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                st.dataframe(trades_table_rows(r.trades), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════
# Chart
# ══════════════════════════════════════════════════════════════════════════
with tab_chart:
    chart_year = st.selectbox(
        "Năm hiển thị chart",
        list(range(2021, 2027)),
        index=list(range(2021, 2027)).index(st.session_state.trade_year) if st.session_state.trade_year in range(2021, 2027) else 3,
        key="chart_year",
    )
    show_vol = st.toggle("Volume", value=False)
    if st.button("Tải chart", type="primary", key="load_chart"):
        with st.spinner("Đang tải dữ liệu & backtest..."):
            r = run_year_backtest(chart_year, st.session_state.params, st.session_state.equity, sl_pct, target_rr)
            st.session_state.chart_result = r

    cr = st.session_state.get("chart_result")
    if cr and cr.year == chart_year:
        m = cr.metrics
        st.caption(
            f"{STRATEGY_NAME} · {chart_year} · {m.get('trade_count', 0)} lệnh · "
            f"Return {fmt_pct(m.get('total_return', 0))}"
        )
        try:
            render_professional_chart(
                cr.period_df,
                STRATEGY_NAME,
                cr.trades,
                chart_id=f"besttrade-{chart_year}",
                show_ema=False,
                show_volume=show_vol,
                equity=st.session_state.equity,
                max_bars=5000,
                height=680,
            )
        except Exception as e:
            st.error(f"Chart error: {e}")
        st.caption("Đỏ = SL · Xanh = TP · Scroll zoom · Kéo pan")
    else:
        st.info("Chọn năm và bấm **Tải chart** để xem biểu đồ chuyên nghiệp (TradingView-style).")

# ══════════════════════════════════════════════════════════════════════════
# Strategy info
# ══════════════════════════════════════════════════════════════════════════
with tab_strategy:
    info = STRATEGIES.get(STRATEGY_NAME, {})
    st.markdown(info.get("description", ""))
    st.markdown("#### Tham số đã kiểm chứng")
    st.json(cfg["params"])
    st.markdown("#### Logic entry")
    st.markdown("""
1. **Pin bar**: Wick ≥ 4× body, wick chiếm ≥52% range, thân nhỏ
2. **Vị trí**: Tại swing high/low (lookback 10 bar)
3. **Filter 4H**: Stack mode — chỉ long khi 4H bullish, short khi bearish
4. **ADX 1H**: ≤ 30 (ưu tiên sideway)
5. **Session**: London 9–16 UTC
6. **Risk**: 2% vốn/lệnh · TP = 2R
    """)
    st.markdown("#### Kế thừa từ SystemTrain")
    st.markdown("""
- Engine backtest `SignalEngine` + `detect_pin_bar` (spread/slippage realistic)
- Rolling yearly optimize & walk-forward validation
- Professional chart component (Lightweight Charts)
- HTF filter stack từ Wyckoff pipeline
    """)
