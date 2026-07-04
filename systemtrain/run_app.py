#!/usr/bin/env python3
"""Streamlit UI — biểu đồ, cấu hình, tối ưu rolling."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import yaml

from systemtrain.orchestrator.rolling_production import current_trade_year, train_year_for
from systemtrain.ui.charts import make_strategy_chart, metrics_cards_html
from systemtrain.ui.meta import STRATEGIES, STRATEGY_ORDER
from systemtrain.ui.services import (
    get_rolling_state,
    load_base_yaml,
    load_history_year,
    load_history_years,
    load_price_data,
    merge_params,
    optimize_trade_year,
    run_all_backtest,
    run_strategy_backtest,
    save_params_to_active,
)

st.set_page_config(
    page_title="SystemTrain — EURUSD",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session defaults ─────────────────────────────────────────────────────
if "trade_year" not in st.session_state:
    st.session_state.trade_year = current_trade_year()
if "param_overrides" not in st.session_state:
    st.session_state.param_overrides = {}
if "equity" not in st.session_state:
    st.session_state.equity = 1000.0


def _render_param_editor(strategy: str, params: dict) -> dict:
    """Form widget cho rolling params."""
    meta = STRATEGIES[strategy]["rolling_params"]
    out = dict(params)
    cols = st.columns(2)
    for i, (key, spec) in enumerate(meta.items()):
        col = cols[i % 2]
        val = params.get(key, spec.get("default"))
        with col:
            if spec["type"] == "select":
                opts = spec["options"]
                idx = opts.index(val) if val in opts else 0
                out[key] = st.selectbox(spec["label"], opts, index=idx, key=f"{strategy}_{key}")
            elif spec["type"] == "int":
                out[key] = st.number_input(spec["label"], min_value=int(spec["min"]), max_value=int(spec["max"]), value=int(val) if val is not None else int(spec["min"]), step=int(spec.get("step", 1)), key=f"{strategy}_{key}")
            else:
                out[key] = st.number_input(spec["label"], min_value=float(spec["min"]), max_value=float(spec["max"]), value=float(val) if val is not None else float(spec["min"]), step=float(spec.get("step", 0.1)), key=f"{strategy}_{key}")
    return out


# ── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ SystemTrain")
    st.caption("EURUSD 1H · Rolling production")

    st.session_state.equity = st.number_input("Vốn ($)", min_value=100.0, value=st.session_state.equity, step=100.0)
    st.session_state.trade_year = st.selectbox(
        "Năm trade",
        list(range(2022, current_trade_year() + 1)),
        index=list(range(2022, current_trade_year() + 1)).index(st.session_state.trade_year)
        if st.session_state.trade_year in range(2022, current_trade_year() + 1)
        else len(list(range(2022, current_trade_year() + 1))) - 1,
    )

    try:
        df = load_price_data()
        st.success(f"Data: {df.index.min().date()} → {df.index.max().date()}")
        st.caption(f"{len(df):,} bar 1H")
    except Exception as e:
        st.error(f"Không load được data: {e}")

    st.divider()
    st.markdown("**Lệnh nhanh**")
    st.code("python3 run_rolling_remine.py", language="bash")
    st.code("streamlit run run_app.py", language="bash")

# ── Header ───────────────────────────────────────────────────────────────
st.title("📈 SystemTrain Dashboard")
ty = st.session_state.trade_year
st.markdown(f"**Năm trade {ty}** · Train trên **{train_year_for(ty)}** · Vốn **${st.session_state.equity:,.0f}**")

tab_overview, tab_chart, tab_config, tab_opt, tab_results = st.tabs(
    ["📋 Tổng quan", "📊 Biểu đồ", "🔧 Cấu hình", "⚡ Tối ưu", "📑 Kết quả"]
)

# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — Tổng quan
# ══════════════════════════════════════════════════════════════════════════
with tab_overview:
    st.subheader("Chiến lược production")
    try:
        state = get_rolling_state(ty)
    except Exception:
        state = None

    for sname in STRATEGY_ORDER:
        info = STRATEGIES[sname]
        with st.expander(f"{info['icon']} {info['title']}", expanded=True):
            st.markdown(info["summary"])
            st.markdown(info["description"])
            if state and sname in state.get("strategies", {}):
                p = state["strategies"][sname]["params"]
                tr = state["strategies"][sname].get("train", {})
                st.json({"params": p, "train_metrics": tr})
            base = load_base_yaml(sname)
            with st.popover("Xem base config"):
                st.json(base)

    st.info(
        "**Rolling walk-forward:** Đầu mỗi năm optimize trên năm trước → trade năm hiện tại. "
        "Pin Bar đã loại (không robust 2021–22)."
    )

# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — Biểu đồ
# ══════════════════════════════════════════════════════════════════════════
with tab_chart:
    st.subheader("Biểu đồ giá & lệnh")
    c1, c2, c3 = st.columns(3)
    with c1:
        chart_strategy = st.selectbox("Chiến lược", STRATEGY_ORDER)
    with c2:
        chart_year = st.selectbox("Năm hiển thị", list(range(2021, current_trade_year() + 1)), index=max(0, ty - 2021))
    with c3:
        show_ema = st.checkbox("EMA 50/200", value=chart_strategy == "EMA 50/200")

    hist_state = load_history_year(chart_year)
    if hist_state is None:
        hist_state = get_rolling_state(chart_year if chart_year == ty else ty)
    overrides = st.session_state.param_overrides
    state = merge_params(hist_state, overrides)

    if st.button("🔄 Chạy backtest & vẽ biểu đồ", type="primary"):
        with st.spinner("Đang backtest..."):
            try:
                metrics, trades, period_df = run_strategy_backtest(
                    chart_strategy, state, chart_year, st.session_state.equity,
                )
                st.session_state.last_chart = {
                    "metrics": metrics, "trades": trades, "df": period_df,
                    "strategy": chart_strategy, "year": chart_year,
                }
            except Exception as e:
                st.error(str(e))

    if "last_chart" in st.session_state and st.session_state.last_chart.get("year") == chart_year:
        lc = st.session_state.last_chart
        st.markdown(metrics_cards_html(lc["metrics"]))
        fig = make_strategy_chart(
            lc["df"], lc["trades"],
            title=f"{lc['strategy']} — {chart_year}",
            show_ema=show_ema or lc["strategy"] == "EMA 50/200",
        )
        st.plotly_chart(fig, use_container_width=True)

        if lc["trades"]:
            rows = [{
                "entry": str(t.entry_time)[:16],
                "exit": str(t.exit_time)[:16] if t.exit_time else "",
                "dir": "LONG" if t.direction == 1 else "SHORT",
                "pnl": round(t.pnl, 2),
                "result": t.result,
            } for t in lc["trades"]]
            st.dataframe(rows, use_container_width=True)
    else:
        st.caption("Chọn chiến lược + năm, bấm **Chạy backtest & vẽ biểu đồ**.")

# ══════════════════════════════════════════════════════════════════════════
# TAB 3 — Cấu hình
# ══════════════════════════════════════════════════════════════════════════
with tab_config:
    st.subheader("Cấu hình rolling")
    state = get_rolling_state(ty)

    st.markdown(f"**Active:** `config/rolling/active.yaml` · Trade year **{state.get('trade_year')}**")
    st.caption(f"Optimized: {str(state.get('optimized_at', ''))[:19]}")

    edited: dict[str, dict] = {}
    for sname in STRATEGY_ORDER:
        st.markdown(f"### {STRATEGIES[sname]['icon']} {sname}")
        current = state["strategies"][sname]["params"]
        edited[sname] = _render_param_editor(sname, current)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Lưu làm config active", type="primary"):
            new_state = merge_params(state, edited)
            save_params_to_active(new_state)
            st.session_state.param_overrides = edited
            st.success("Đã lưu config/rolling/active.yaml")
    with c2:
        if st.button("🧪 Thử nhanh (không lưu)"):
            st.session_state.param_overrides = edited
            res = run_all_backtest(merge_params(state, edited), ty, st.session_state.equity)
            st.json(res)

    with st.expander("Raw active.yaml"):
        st.code(Path("config/rolling/active.yaml").read_text() if Path("config/rolling/active.yaml").exists() else "", language="yaml")

# ══════════════════════════════════════════════════════════════════════════
# TAB 4 — Tối ưu
# ══════════════════════════════════════════════════════════════════════════
with tab_opt:
    st.subheader("Tối ưu tham số (rolling grid-search)")
    st.markdown(
        f"Grid-search trên năm **{train_year_for(ty)}** → lưu param cho trade **{ty}**. "
        "Mất ~1–2 phút / chiến lược."
    )

    opt_year = st.number_input("Năm trade cần optimize", min_value=2022, max_value=current_trade_year(), value=ty)

    if st.button("⚡ Chạy tối ưu rolling", type="primary"):
        progress = st.progress(0, text="Đang optimize...")
        try:
            with st.spinner(f"Train {train_year_for(int(opt_year))} → Trade {int(opt_year)}..."):
                new_state = optimize_trade_year(int(opt_year), st.session_state.equity)
            progress.progress(100, text="Hoàn tất")
            st.success(f"Đã lưu config cho trade year {int(opt_year)}")
            for sname in STRATEGY_ORDER:
                d = new_state["strategies"][sname]
                st.markdown(f"**{sname}** — train: {d['train'].get('trade_count',0)}t WR{d['train'].get('win_rate',0):.0%}")
                st.json(d["params"])
            bt = __import__("systemtrain.orchestrator.rolling_production", fromlist=["backtest_trade_year"]).backtest_trade_year(new_state, __import__("systemtrain.config", fromlist=["Config"]).Config.load(), st.session_state.equity)
            st.metric("Tổng trade year (preview)", f"{bt['combined_return']:+.1%}")
        except Exception as e:
            st.error(str(e))

    st.divider()
    st.markdown("**Tối ưu tất cả folds (2021→2026)**")
    if st.button("Chạy full walk-forward (chậm ~5 phút)"):
        import subprocess
        with st.spinner("Đang chạy run_rolling_remine.py --all ..."):
            r = subprocess.run(["python3", "run_rolling_remine.py", "--all"], capture_output=True, text=True, cwd=".")
        st.code(r.stdout[-3000:] if len(r.stdout) > 3000 else r.stdout)
        if r.returncode != 0:
            st.error(r.stderr[-2000:])

# ══════════════════════════════════════════════════════════════════════════
# TAB 5 — Kết quả
# ══════════════════════════════════════════════════════════════════════════
with tab_results:
    st.subheader("Báo cáo theo năm")

    years = load_history_years() or list(range(2022, current_trade_year() + 1))
    rows = []
    for y in years:
        hs = load_history_year(y)
        if not hs:
            continue
        from systemtrain.config import Config
        from systemtrain.orchestrator.rolling_production import backtest_trade_year
        try:
            bt = backtest_trade_year(hs, Config.load(), st.session_state.equity)
            for sname, m in bt["strategies"].items():
                rows.append({
                    "Năm": y,
                    "Chiến lược": sname,
                    "Lệnh": m.get("trade_count", 0),
                    "WR": f"{m.get('win_rate', 0):.1%}",
                    "PF": f"{m.get('profit_factor', 0):.2f}",
                    "Return": f"{m.get('total_return', 0):+.1%}",
                })
            rows.append({
                "Năm": y, "Chiến lược": "— TỔNG —",
                "Lệnh": "", "WR": "", "PF": "",
                "Return": f"{bt.get('combined_return', 0):+.1%}",
            })
        except Exception:
            pass

    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.warning("Chưa có history. Chạy: `python3 run_rolling_remine.py --all`")

    for fname in ["output/production_report.json", "output/rolling_walkforward_report.json", "output/rolling_remine_report.json"]:
        p = Path(fname)
        if p.exists():
            with st.expander(p.name):
                st.json(json.loads(p.read_text()))

    if st.button("🔄 Refresh kết quả năm hiện tại"):
        state = get_rolling_state(ty)
        res = run_all_backtest(state, ty, st.session_state.equity)
        st.json(res)
