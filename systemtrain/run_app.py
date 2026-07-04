#!/usr/bin/env python3
"""Streamlit UI — biểu đồ, cấu hình, tối ưu rolling."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import yaml

from systemtrain.orchestrator.rolling_production import current_trade_year, history_path, train_year_for
from systemtrain.ui.charts import (
    _inject_chart_resize_css,
    make_strategy_detail_chart,
    metrics_all_html,
    metrics_cards_html,
    render_resizable_plotly,
    strategy_color,
    strategy_legend_html,
)
from systemtrain.ui.meta import STRATEGIES, STRATEGY_ORDER
from systemtrain.ui.services import (
    config_year_saved,
    get_config_state,
    get_rolling_state,
    load_base_yaml,
    load_history_year,
    load_history_years,
    load_price_data,
    merge_params,
    optimize_trade_year,
    run_all_backtest,
    run_all_strategies_backtest,
    run_strategy_backtest,
    save_params_for_year,
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
        "4 chiến lược: Wyckoff, RSI, EMA, Pin Bar Elite."
    )

# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — Biểu đồ
# ══════════════════════════════════════════════════════════════════════════
with tab_chart:
    st.subheader("Biểu đồ giá & lệnh")
    chart_options = ["All (tất cả)"] + STRATEGY_ORDER
    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
    with c1:
        chart_strategy = st.selectbox("Chiến lược", chart_options)
    with c2:
        chart_year = st.selectbox("Năm hiển thị", list(range(2021, current_trade_year() + 1)), index=max(0, ty - 2021))
    with c3:
        show_ema = st.checkbox("EMA", value=True)
    with c4:
        show_volume = st.checkbox("Volume", value=False)
    with c5:
        focus_trades = st.checkbox("Focus lệnh", value=True, help="Zoom vùng quanh các lệnh")

    hist_state = load_history_year(chart_year)
    if hist_state is None:
        hist_state = get_rolling_state(chart_year if chart_year == ty else ty)
    overrides = st.session_state.param_overrides
    state = merge_params(hist_state, overrides)
    is_all = chart_strategy.startswith("All")

    if st.button("🔄 Chạy backtest & vẽ biểu đồ", type="primary"):
        with st.spinner("Đang backtest..."):
            try:
                if is_all:
                    results, period_df = run_all_strategies_backtest(
                        state, chart_year, st.session_state.equity,
                    )
                    st.session_state.last_chart = {
                        "mode": "all",
                        "results": results,
                        "df": period_df,
                        "year": chart_year,
                        "strategy": "All",
                    }
                else:
                    metrics, trades, period_df = run_strategy_backtest(
                        chart_strategy, state, chart_year, st.session_state.equity,
                    )
                    st.session_state.last_chart = {
                        "mode": "single",
                        "metrics": metrics,
                        "trades": trades,
                        "df": period_df,
                        "strategy": chart_strategy,
                        "year": chart_year,
                    }
            except Exception as e:
                st.error(str(e))

    lc = st.session_state.get("last_chart")
    chart_ok = (
        lc
        and lc.get("year") == chart_year
        and (lc.get("mode") == "all") == is_all
        and (is_all or lc.get("strategy") == chart_strategy)
    )

    if chart_ok:
        _inject_chart_resize_css()

        def _render_strategy_chart(sname: str, trades: list, metrics: dict | None = None) -> None:
            info = STRATEGIES[sname]
            hint = info.get("chart_hint", "")
            if metrics:
                st.markdown(
                    f"<span style='color:{strategy_color(sname)};font-size:16px'>●</span> "
                    f"**{info['icon']} {sname}** — {metrics_cards_html(metrics)}",
                    unsafe_allow_html=True,
                )
            if hint:
                st.caption(hint)
            ema_override = show_ema if sname != "EMA 50/200" else True
            fig = make_strategy_detail_chart(
                lc["df"],
                sname,
                trades,
                show_ema=ema_override,
                show_volume=show_volume,
                equity=st.session_state.equity,
                focus_trades=focus_trades,
            )
            render_resizable_plotly(
                fig,
                chart_id=f"{sname}-{chart_year}-{lc['mode']}",
            )

        if lc["mode"] == "all":
            st.markdown(metrics_all_html(lc["results"]), unsafe_allow_html=True)
            st.markdown(strategy_legend_html(), unsafe_allow_html=True)
            st.caption("Mỗi chiến lược có biểu đồ riêng — overlay SL/TP, RSI hoặc EMA theo logic từng CL.")
            tabs = st.tabs([f"{STRATEGIES[s]['icon']} {s}" for s in STRATEGY_ORDER])
            for tab, sname in zip(tabs, STRATEGY_ORDER):
                with tab:
                    res = lc["results"].get(sname, {})
                    _render_strategy_chart(sname, res.get("trades", []), res.get("metrics"))
        else:
            _render_strategy_chart(lc["strategy"], lc.get("trades", []), lc.get("metrics"))

        st.caption(
            "Kéo **góc phải-dưới** khung chart để đổi cao/rộng · "
            "Đỏ đứt = SL · Xanh chấm = TP · Zoom: kéo khung trên chart · Reset: double-click"
        )

        rows = []
        if lc["mode"] == "all":
            for sname in STRATEGY_ORDER:
                for t in lc["results"].get(sname, {}).get("trades", []):
                    rows.append({
                        "Chiến lược": sname,
                        "entry": str(t.entry_time)[:16],
                        "exit": str(t.exit_time)[:16] if t.exit_time else "",
                        "dir": "LONG" if t.direction == 1 else "SHORT",
                        "pnl": round(t.pnl, 2),
                        "result": t.result,
                    })
        elif lc.get("trades"):
            for t in lc["trades"]:
                rows.append({
                    "Chiến lược": lc["strategy"],
                    "entry": str(t.entry_time)[:16],
                    "exit": str(t.exit_time)[:16] if t.exit_time else "",
                    "dir": "LONG" if t.direction == 1 else "SHORT",
                    "pnl": round(t.pnl, 2),
                    "result": t.result,
                })
        if rows:
            st.dataframe(rows, use_container_width=True)
    else:
        st.caption("Chọn chiến lược + năm, bấm **Chạy backtest & vẽ biểu đồ**.")

# ══════════════════════════════════════════════════════════════════════════
# TAB 3 — Cấu hình
# ══════════════════════════════════════════════════════════════════════════
with tab_config:
    st.subheader("Cấu hình rolling theo năm trade")

    saved_years = load_history_years()
    year_options = sorted(set(saved_years + list(range(2022, current_trade_year() + 1))))

    c_y1, c_y2, c_y3 = st.columns([1, 1, 2])
    with c_y1:
        default_idx = year_options.index(ty) if ty in year_options else len(year_options) - 1
        config_year = st.selectbox(
            "Năm trade (lưu config)",
            year_options,
            index=default_idx,
            help="Train trên năm trước → trade năm này. Mỗi năm một file history.",
        )
    with c_y2:
        st.metric("Năm train", train_year_for(config_year))
    with c_y3:
        hp = history_path(config_year)
        if config_year_saved(config_year):
            st.success(f"Đã có config: `{hp}`")
        else:
            st.warning(f"Chưa lưu — sẽ dùng base/fixed. File: `{hp}`")

    state = get_config_state(config_year, st.session_state.equity)
    if state.get("optimized_at"):
        st.caption(f"Cập nhật: {str(state['optimized_at'])[:19]} · Vốn ref: ${state.get('equity', 1000):,.0f}")

    edited: dict[str, dict] = {}
    for sname in STRATEGY_ORDER:
        st.markdown(f"### {STRATEGIES[sname]['icon']} {sname}")
        current = state["strategies"][sname]["params"]
        edited[sname] = _render_param_editor(sname, current)

    set_active = config_year == current_trade_year()
    c1, c2, c3 = st.columns(3)
    with c1:
        also_active = st.checkbox(
            "Đặt làm active (production)",
            value=set_active,
            help="Cập nhật config/rolling/active.yaml — dùng khi trade năm này",
        )
    with c2:
        if st.button(f"💾 Lưu cho năm {config_year}", type="primary"):
            new_state = merge_params(state, edited)
            new_state["equity"] = st.session_state.equity
            path = save_params_for_year(new_state, config_year, set_active=also_active)
            if config_year == ty:
                st.session_state.param_overrides = edited
            st.success(f"Đã lưu `{path}`")
            if also_active:
                st.info("Đã cập nhật active.yaml cho production")
            st.rerun()
    with c3:
        if st.button("🧪 Thử nhanh (không lưu)"):
            st.session_state.param_overrides = edited
            res = run_all_backtest(merge_params(state, edited), config_year, st.session_state.equity)
            st.json(res)

    with st.expander("Các năm đã lưu"):
        rows = []
        for y in year_options:
            hs = load_history_year(y)
            rows.append({
                "Năm trade": y,
                "Train": train_year_for(y),
                "Đã lưu": "✓" if config_year_saved(y) else "—",
                "Optimized": str((hs or {}).get("optimized_at", ""))[:19] if hs else "",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    with st.expander(f"Raw — {history_path(config_year).name}"):
        p = history_path(config_year)
        if p.exists():
            st.code(p.read_text(), language="yaml")
        elif Path("config/rolling/active.yaml").exists() and config_year == ty:
            st.code(Path("config/rolling/active.yaml").read_text(), language="yaml")
        else:
            st.caption("Chưa có file — lưu hoặc chạy Tối ưu tab ⚡")

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
