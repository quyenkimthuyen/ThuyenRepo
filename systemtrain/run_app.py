#!/usr/bin/env python3
"""Streamlit UI — biểu đồ, cấu hình, tối ưu rolling."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yaml

from systemtrain.orchestrator.rolling_production import current_trade_year, history_path, train_year_for
from systemtrain.ui.charts import (
    _inject_chart_resize_css,
    make_strategy_illustration_chart,
    make_strategy_detail_chart,
    metrics_all_html,
    metrics_cards_html,
    render_resizable_plotly,
    render_professional_chart,
    strategy_color,
    strategy_legend_html,
)
from systemtrain.ui.meta import STRATEGIES, STRATEGY_ORDER
from systemtrain.ui.services import (
    advance_replay,
    config_year_saved,
    finish_replay,
    get_config_state,
    get_rolling_state,
    load_base_yaml,
    load_history_year,
    load_history_years,
    load_live_chart_data,
    load_live_paper_state,
    load_price_data,
    load_replay_chart_df,
    merge_params,
    optimize_trade_year,
    paper_trade_to_chart_trade,
    refresh_live_paper,
    replay_current_bar,
    replay_visible_df,
    reset_live_paper,
    run_all_backtest,
    run_all_strategies_backtest,
    run_strategy_backtest,
    save_params_for_year,
    save_params_to_active,
    scrub_replay,
    start_replay_session,
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

tab_overview, tab_chart, tab_live, tab_replay, tab_config, tab_opt, tab_results = st.tabs(
    ["📋 Tổng quan", "📊 Biểu đồ", "🟢 Live Paper", "⏪ Replay", "🔧 Cấu hình", "⚡ Tối ưu", "📑 Kết quả"]
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
            chart_col, text_col = st.columns([1.15, 1.85])
            with chart_col:
                st.plotly_chart(
                    make_strategy_illustration_chart(sname),
                    use_container_width=True,
                    config={"displayModeBar": False, "responsive": True},
                    key=f"overview-chart-{sname}",
                )
            with text_col:
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
        "5 chiến lược: Wyckoff, RSI, EMA Elite, EMA Flow, Pin Bar."
    )

# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — Biểu đồ
# ══════════════════════════════════════════════════════════════════════════
with tab_chart:
    st.subheader("Biểu đồ giá & lệnh")
    chart_options = ["All (tất cả)"] + STRATEGY_ORDER
    with st.container(border=True):
        top1, top2, top3, top4 = st.columns([2.2, 1, 1.2, 1.2])
        with top1:
            chart_strategy = st.selectbox("Chiến lược", chart_options)
        with top2:
            chart_year = st.selectbox("Năm", list(range(2021, current_trade_year() + 1)), index=max(0, ty - 2021))
        with top3:
            chart_renderer = st.radio(
                "Renderer",
                ["Professional", "Plotly fallback"],
                index=0,
                horizontal=True,
            )
        with top4:
            chart_window = st.selectbox(
                "Số nến",
                ["500", "1000", "2000", "5000", "All"],
                index=2,
                help="Giảm số nến nếu chart nặng, chọn All để xem toàn bộ dữ liệu năm.",
            )

        nav1, nav2, nav3, nav4, nav5 = st.columns([1, 1, 1, 1, 1.4])
        with nav1:
            show_ema = st.toggle("EMA", value=True)
        with nav2:
            show_volume = st.toggle("Volume", value=True)
        with nav3:
            focus_trades = st.toggle("Focus lệnh", value=False, help="Chỉ zoom quanh vùng có lệnh. Tắt để xem và điều hướng toàn bộ năm.")
        with nav4:
            chart_height = st.slider("Chiều cao", min_value=460, max_value=980, value=700, step=40)
        with nav5:
            drag_label = st.radio(
                "Kéo chuột",
                ["Pan / di chuyển", "Zoom vùng"],
                horizontal=True,
                help="Plotly dùng lựa chọn này. Professional renderer luôn hỗ trợ kéo pan và lăn chuột zoom.",
            )

    chart_max_bars = 100_000_000 if chart_window == "All" else int(chart_window)
    chart_dragmode = "pan" if drag_label.startswith("Pan") else "zoom"
    use_professional_chart = chart_renderer == "Professional"

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
            ema_override = show_ema if sname not in ("EMA 50/200", "EMA Flow") else True

            def _render_plotly_fallback() -> None:
                fig = make_strategy_detail_chart(
                    lc["df"],
                    sname,
                    trades,
                    show_ema=ema_override,
                    show_volume=show_volume,
                    equity=st.session_state.equity,
                    max_bars=chart_max_bars,
                    height=chart_height,
                    focus_trades=focus_trades,
                    dragmode=chart_dragmode,
                )
                render_resizable_plotly(
                    fig,
                    chart_id=f"{sname}-{chart_year}-{lc['mode']}",
                    default_height=chart_height,
                )

            if use_professional_chart:
                try:
                    render_professional_chart(
                        lc["df"],
                        sname,
                        trades,
                        chart_id=f"{sname}-{chart_year}-{lc['mode']}",
                        show_ema=ema_override,
                        show_volume=show_volume,
                        equity=st.session_state.equity,
                        max_bars=chart_max_bars,
                        height=chart_height,
                        focus_trades=focus_trades,
                    )
                except Exception as e:
                    st.warning(f"Professional chart lỗi, đang dùng Plotly fallback: {e}")
                    _render_plotly_fallback()
            else:
                _render_plotly_fallback()

        if lc["mode"] == "all":
            st.markdown(metrics_all_html(lc["results"]), unsafe_allow_html=True)
            st.markdown(strategy_legend_html(), unsafe_allow_html=True)
            st.caption("Mỗi chiến lược có biểu đồ riêng — chart terminal, marker lệnh, SL/TP, EMA/RSI theo logic từng CL.")
            tabs = st.tabs([f"{STRATEGIES[s]['icon']} {s}" for s in STRATEGY_ORDER])
            for tab, sname in zip(tabs, STRATEGY_ORDER):
                with tab:
                    res = lc["results"].get(sname, {})
                    _render_strategy_chart(sname, res.get("trades", []), res.get("metrics"))
        else:
            _render_strategy_chart(lc["strategy"], lc.get("trades", []), lc.get("metrics"))

        st.caption(
            "Professional: lăn chuột để zoom, kéo chart để pan, nút Fit để reset. "
            "Plotly fallback: chọn Pan/Zoom vùng, double-click để reset. "
            "Đỏ đứt = SL · Xanh chấm = TP."
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
            with st.expander(f"Trade blotter ({len(rows)} lệnh)", expanded=False):
                st.dataframe(rows, use_container_width=True)
    else:
        st.caption("Chọn chiến lược + năm, bấm **Chạy backtest & vẽ biểu đồ**.")

# ══════════════════════════════════════════════════════════════════════════
# TAB 3 — Live Paper
# ══════════════════════════════════════════════════════════════════════════
with tab_live:
    st.subheader("Live Paper Trading")
    st.caption(
        "Paper test theo candle 1H đã đóng. Không đặt lệnh thật; trạng thái được lưu ở `data/paper`."
    )

    live_state = load_live_paper_state()
    session = live_state["session"]
    saved_years = load_history_years()
    live_year_options = sorted(set(saved_years + list(range(2022, current_trade_year() + 1))))
    live_config_labels = {
        year: f"Trade {year} (optimize {train_year_for(year)})"
        for year in live_year_options
    }
    default_live_year = session.get("trade_year") or ty
    live_year_index = (
        live_year_options.index(default_live_year)
        if default_live_year in live_year_options
        else len(live_year_options) - 1
    )

    with st.container(border=True):
        live_c1, live_c2, live_c3, live_c4 = st.columns([1, 2, 1, 1])
        with live_c1:
            live_trade_year = st.selectbox(
                "Bộ config optimize",
                live_year_options,
                index=live_year_index,
                format_func=lambda y: live_config_labels[y],
                help="Live Paper không optimize lại. Nó dùng bộ params đã optimize từ năm trước để trade/paper năm được chọn.",
            )
            st.caption(f"Dùng params train trên dữ liệu **{train_year_for(live_trade_year)}**.")
        with live_c2:
            live_strategies = st.multiselect(
                "Chiến lược paper",
                STRATEGY_ORDER,
                default=[STRATEGY_ORDER[0]],
                help="Mỗi chiến lược dùng một paper account riêng.",
            )
        with live_c3:
            live_equity = st.number_input("Vốn/account ($)", min_value=100.0, value=float(st.session_state.equity), step=100.0)
        with live_c4:
            live_warmup = st.number_input("Warmup ngày", min_value=30, max_value=180, value=90, step=15)

        act1, act2, act3 = st.columns([1, 1, 2])
        with act1:
            if st.button("Cập nhật tín hiệu", type="primary", disabled=not live_strategies):
                try:
                    result = refresh_live_paper(
                        live_trade_year,
                        live_strategies,
                        live_equity,
                        refresh_data=False,
                        warmup_days=int(live_warmup),
                    )
                    st.success(f"Đã xử lý {result['bars']} nến, latest bar {result['latest_bar']}. Events: {len(result['events'])}")
                    live_state = load_live_paper_state()
                    session = live_state["session"]
                except Exception as e:
                    st.error(str(e))
        with act2:
            if st.button("Refresh giá Dukascopy", disabled=not live_strategies):
                try:
                    result = refresh_live_paper(
                        live_trade_year,
                        live_strategies,
                        live_equity,
                        refresh_data=True,
                        warmup_days=int(live_warmup),
                    )
                    st.success(f"Đã refresh giá và xử lý latest bar {result['latest_bar']}.")
                    live_state = load_live_paper_state()
                    session = live_state["session"]
                except Exception as e:
                    st.error(str(e))
        with act3:
            reset_choice = st.selectbox("Reset paper", ["Không reset", "Toàn bộ"] + STRATEGY_ORDER)
            if st.button("Reset", disabled=reset_choice == "Không reset"):
                reset_live_paper(None if reset_choice == "Toàn bộ" else reset_choice)
                st.warning("Đã reset paper state.")
                live_state = load_live_paper_state()
                session = live_state["session"]

        auto1, auto2, auto3 = st.columns([1, 1, 2])
        with auto1:
            live_auto_update = st.toggle(
                "Tự cập nhật giá",
                value=st.session_state.get("live_auto_update", False),
                help="Khi bật, trang sẽ tự refresh giá Dukascopy và chạy paper signal theo chu kỳ.",
            )
            st.session_state.live_auto_update = live_auto_update
        with auto2:
            live_auto_minutes = st.number_input(
                "Chu kỳ phút",
                min_value=5,
                max_value=120,
                value=int(st.session_state.get("live_auto_minutes", 15)),
                step=5,
            )
            st.session_state.live_auto_minutes = live_auto_minutes
        with auto3:
            if live_auto_update:
                st.success("Auto update đang bật. Giữ tab này mở để tự cập nhật.")
            else:
                st.caption("Bật **Tự cập nhật giá** nếu muốn paper mode tự refresh khi trang đang mở.")

    if live_auto_update and live_strategies:
        interval_seconds = int(live_auto_minutes * 60)
        now = time.time()
        last_auto = float(st.session_state.get("live_auto_last", 0.0))
        if now - last_auto >= interval_seconds:
            try:
                result = refresh_live_paper(
                    live_trade_year,
                    live_strategies,
                    live_equity,
                    refresh_data=True,
                    warmup_days=int(live_warmup),
                )
                st.session_state.live_auto_last = now
                st.toast(f"Auto update xong: {result['latest_bar']} · events {len(result['events'])}")
                live_state = load_live_paper_state()
                session = live_state["session"]
            except Exception as e:
                st.error(f"Auto update lỗi: {e}")
        remaining = max(5, interval_seconds - int(time.time() - st.session_state.get("live_auto_last", now)))
        components.html(
            f"""
            <script>
              setTimeout(function() {{
                window.parent.location.reload();
              }}, {remaining * 1000});
            </script>
            """,
            height=0,
        )

    st.markdown(
        f"**Nguồn:** {session.get('source', 'dukascopy-cache')} · "
        f"**Latest bar:** `{session.get('latest_bar') or 'chưa có'}` · "
        f"**Updated:** `{session.get('updated_at') or 'chưa chạy'}`"
    )

    strategy_states = session.get("strategies", {})
    if not strategy_states:
        st.info("Bấm **Cập nhật tín hiệu** để khởi tạo paper mode. Lần đầu chỉ đặt mốc candle, chưa backfill lệnh cũ.")
    else:
        cols = st.columns(min(4, max(1, len(STRATEGY_ORDER))))
        for idx, sname in enumerate(STRATEGY_ORDER):
            s = strategy_states.get(sname)
            with cols[idx % len(cols)]:
                if not s:
                    st.metric(sname, "Not started")
                    continue
                closed = s.get("closed_trades", [])
                open_trade = s.get("open_trade")
                st.metric(
                    sname,
                    f"${s.get('equity', 0):,.0f}",
                    f"{s.get('equity', 0) - s.get('initial_equity', 0):+.0f}",
                )
                st.caption(
                    f"{s.get('status', 'idle')} · closed {len(closed)}"
                    + (" · OPEN" if open_trade else "")
                )

    live_view_strategy = st.selectbox("Xem chart live", STRATEGY_ORDER)
    selected_state = strategy_states.get(live_view_strategy, {})
    live_chart_trades = []
    for trade in selected_state.get("closed_trades", [])[-30:]:
        live_chart_trades.append(paper_trade_to_chart_trade(trade))
    if selected_state.get("open_trade"):
        live_chart_trades.append(paper_trade_to_chart_trade(selected_state["open_trade"]))

    try:
        live_df = load_live_chart_data(warmup_days=30, max_bars=1000)
        render_professional_chart(
            live_df,
            live_view_strategy,
            live_chart_trades,
            chart_id=f"live-{live_view_strategy}",
            show_ema=True,
            show_volume=True,
            equity=float(selected_state.get("initial_equity", live_equity)),
            max_bars=1000,
            height=620,
            focus_trades=False,
        )
    except Exception as e:
        st.warning(f"Chưa vẽ được live chart: {e}")

    journal_rows = []
    for event in reversed(live_state.get("journal", [])[-100:]):
        trade = event.get("trade", {})
        journal_rows.append({
            "event": event.get("event"),
            "strategy": event.get("strategy"),
            "entry": str(trade.get("entry_time", ""))[:16],
            "exit": str(trade.get("exit_time", ""))[:16] if trade.get("exit_time") else "",
            "dir": "LONG" if trade.get("direction") == 1 else "SHORT",
            "pnl": round(float(trade.get("pnl", 0.0)), 2),
            "result": trade.get("result", ""),
        })
    if journal_rows:
        with st.expander(f"Paper journal ({len(journal_rows)} events)", expanded=False):
            st.dataframe(journal_rows, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════
# TAB 4 — Replay Backtest
# ══════════════════════════════════════════════════════════════════════════
with tab_replay:
    st.subheader("Replay Backtest")
    st.caption(
        "Chọn thời điểm trong quá khứ, chạy từng nến 1H và xem chiến lược vào/ra lệnh "
        "cùng P&L paper account — giống Live Paper nhưng trên dữ liệu lịch sử."
    )

    saved_years = load_history_years()
    replay_year_options = sorted(set(saved_years + list(range(2022, current_trade_year() + 1))))
    replay_config_labels = {
        year: f"Trade {year} (optimize {train_year_for(year)})"
        for year in replay_year_options
    }
    default_replay_year = st.session_state.get("replay_trade_year", ty)
    replay_year_index = (
        replay_year_options.index(default_replay_year)
        if default_replay_year in replay_year_options
        else len(replay_year_options) - 1
    )

    with st.container(border=True):
        r1, r2, r3, r4 = st.columns([1, 2, 1, 1])
        with r1:
            replay_config_year = st.selectbox(
                "Bộ config optimize",
                replay_year_options,
                index=replay_year_index,
                format_func=lambda y: replay_config_labels[y],
                key="replay_config_year",
            )
        with r2:
            replay_strategies = st.multiselect(
                "Chiến lược replay",
                STRATEGY_ORDER,
                default=st.session_state.get("replay_strategies", STRATEGY_ORDER[:2]),
                key="replay_strategies",
            )
        with r3:
            replay_equity = st.number_input(
                "Vốn/account ($)",
                min_value=100.0,
                value=float(st.session_state.get("replay_equity", st.session_state.equity)),
                step=100.0,
                key="replay_equity",
            )
        with r4:
            replay_warmup = st.number_input(
                "Warmup ngày",
                min_value=30,
                max_value=180,
                value=int(st.session_state.get("replay_warmup", 60)),
                step=15,
                key="replay_warmup",
            )

        d1, d2, d3 = st.columns([1, 1, 2])
        with d1:
            default_start = datetime(replay_config_year, 3, 1, tzinfo=timezone.utc)
            replay_start_date = st.date_input(
                "Ngày bắt đầu replay",
                value=st.session_state.get("replay_start_date", default_start.date()),
                key="replay_start_date",
            )
        with d2:
            replay_start_hour = st.selectbox(
                "Giờ UTC",
                list(range(24)),
                index=int(st.session_state.get("replay_start_hour", 8)),
                format_func=lambda h: f"{h:02d}:00",
                key="replay_start_hour",
            )
        with d3:
            replay_end_date = st.date_input(
                "Ngày kết thúc (tùy chọn)",
                value=st.session_state.get("replay_end_date", datetime(replay_config_year, 12, 31).date()),
                key="replay_end_date",
                help="Mặc định cuối năm trade. Replay không vượt quá năm đã chọn.",
            )

        start_ts = pd.Timestamp(
            datetime.combine(replay_start_date, datetime.min.time().replace(hour=replay_start_hour)),
            tz="UTC",
        )
        end_ts = pd.Timestamp(
            datetime.combine(replay_end_date, datetime.max.time().replace(hour=23, minute=0, second=0, microsecond=0)),
            tz="UTC",
        )

        b1, b2, b3, b4, b5 = st.columns(5)
        with b1:
            if st.button("▶ Khởi tạo replay", type="primary", disabled=not replay_strategies):
                try:
                    session_dict, _df = start_replay_session(
                        trade_year=replay_config_year,
                        config_year=replay_config_year,
                        strategies=replay_strategies,
                        equity=replay_equity,
                        start_ts=start_ts,
                        end_ts=end_ts,
                        warmup_days=int(replay_warmup),
                    )
                    st.session_state.replay_session = session_dict
                    st.session_state.replay_params = {
                        "start_ts": start_ts.isoformat(),
                        "trade_year": replay_config_year,
                    }
                    st.session_state.replay_auto_play = False
                    st.success(
                        f"Replay từ `{session_dict['start_bar'][:16]}` → `{session_dict['end_bar'][:16]}`"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        with b2:
            step_n = st.number_input("+N nến", min_value=1, max_value=200, value=1, step=1, key="replay_step_n")
        with b3:
            if st.button(f"+{step_n} nến", disabled=not st.session_state.get("replay_session")):
                try:
                    df = load_replay_chart_df(
                        st.session_state.replay_session,
                        pd.Timestamp(st.session_state.replay_params["start_ts"]),
                    )
                    session_dict, events = advance_replay(
                        st.session_state.replay_session, df, steps=int(step_n),
                    )
                    st.session_state.replay_session = session_dict
                    bar = replay_current_bar(session_dict, df)
                    st.toast(f"→ `{bar[:16] if bar else '?'}` · {len(events)} events")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        with b4:
            if st.button("⏩ Chạy đến hết", disabled=not st.session_state.get("replay_session")):
                try:
                    df = load_replay_chart_df(
                        st.session_state.replay_session,
                        pd.Timestamp(st.session_state.replay_params["start_ts"]),
                    )
                    session_dict, events = finish_replay(st.session_state.replay_session, df)
                    st.session_state.replay_session = session_dict
                    st.success(f"Hoàn tất replay · {len(events)} events")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        with b5:
            if st.button("↺ Reset", disabled=not st.session_state.get("replay_session")):
                st.session_state.pop("replay_session", None)
                st.session_state.pop("replay_params", None)
                st.session_state.replay_auto_play = False
                st.rerun()

        ap1, ap2, ap3 = st.columns([1, 1, 2])
        with ap1:
            replay_auto = st.toggle(
                "Tự chạy",
                value=st.session_state.get("replay_auto_play", False),
                help="Tự advance nến theo chu kỳ — giữ tab mở.",
            )
            st.session_state.replay_auto_play = replay_auto
        with ap2:
            replay_bars_per_tick = st.number_input(
                "Nến/tick",
                min_value=1,
                max_value=50,
                value=int(st.session_state.get("replay_bars_per_tick", 1)),
                step=1,
            )
            st.session_state.replay_bars_per_tick = replay_bars_per_tick
        with ap3:
            replay_tick_seconds = st.slider(
                "Tốc độ (giây/tick)",
                min_value=0.2,
                max_value=5.0,
                value=float(st.session_state.get("replay_tick_seconds", 1.0)),
                step=0.2,
            )
            st.session_state.replay_tick_seconds = replay_tick_seconds

    replay_session = st.session_state.get("replay_session")
    if not replay_session:
        st.info("Chọn thời điểm bắt đầu và bấm **Khởi tạo replay** để bắt đầu.")
    else:
        try:
            replay_df = load_replay_chart_df(
                replay_session,
                pd.Timestamp(st.session_state.replay_params["start_ts"]),
            )
        except Exception as e:
            st.error(f"Không load được dữ liệu: {e}")
            replay_df = None

        if replay_df is not None and not replay_df.empty:
            cursor_idx = int(replay_session["cursor_idx"])
            start_idx = int(replay_session["start_idx"])
            end_idx = int(replay_session["end_idx"])
            current_bar = replay_current_bar(replay_session, replay_df)
            total_bars = end_idx - start_idx + 1
            done_bars = max(0, cursor_idx - start_idx + 1)
            progress = done_bars / total_bars if total_bars > 0 else 0.0

            st.markdown(
                f"**Nến hiện tại:** `{current_bar[:19] if current_bar else 'chưa bắt đầu'}` · "
                f"**Tiến độ:** {done_bars}/{total_bars} nến ({progress:.0%}) · "
                f"**Khoảng:** `{replay_session['start_bar'][:16]}` → `{replay_session['end_bar'][:16]}`"
            )
            st.progress(min(1.0, progress))

            scrub_idx = st.slider(
                "Tua nến (scrub)",
                min_value=start_idx,
                max_value=end_idx,
                value=min(max(cursor_idx, start_idx), end_idx),
                format="%d",
                help="Kéo để nhảy tới nến — hệ thống tính lại từ đầu (deterministic).",
            )
            if scrub_idx != cursor_idx and st.button("Áp dụng vị trí scrub"):
                try:
                    session_dict, _events = scrub_replay(
                        replay_session,
                        replay_df,
                        scrub_idx,
                        strategies=replay_strategies,
                        equity=replay_equity,
                    )
                    st.session_state.replay_session = session_dict
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

            strategy_states = replay_session.get("strategies", {})
            cols = st.columns(min(5, max(1, len(STRATEGY_ORDER))))
            for idx, sname in enumerate(STRATEGY_ORDER):
                s = strategy_states.get(sname)
                with cols[idx % len(cols)]:
                    if not s:
                        st.metric(sname, "—")
                        continue
                    closed = s.get("closed_trades", [])
                    open_trade = s.get("open_trade")
                    st.metric(
                        sname,
                        f"${s.get('equity', 0):,.0f}",
                        f"{s.get('equity', 0) - s.get('initial_equity', 0):+.0f}",
                    )
                    st.caption(
                        f"{s.get('status', 'idle')} · {len(closed)} closed"
                        + (" · OPEN" if open_trade else "")
                    )

            replay_view_strategy = st.selectbox(
                "Xem chart replay",
                [s for s in STRATEGY_ORDER if s in strategy_states] or STRATEGY_ORDER,
                key="replay_view_strategy",
            )
            selected_state = strategy_states.get(replay_view_strategy, {})
            replay_chart_trades = []
            for trade in selected_state.get("closed_trades", []):
                replay_chart_trades.append(paper_trade_to_chart_trade(trade))
            if selected_state.get("open_trade"):
                replay_chart_trades.append(paper_trade_to_chart_trade(selected_state["open_trade"]))

            visible_df = replay_visible_df(replay_session, replay_df)
            render_professional_chart(
                visible_df,
                replay_view_strategy,
                replay_chart_trades,
                chart_id=f"replay-{replay_view_strategy}",
                show_ema=True,
                show_volume=True,
                equity=float(selected_state.get("initial_equity", replay_equity)),
                max_bars=2000,
                height=620,
                focus_trades=True,
            )

            journal_rows = []
            for event in reversed(replay_session.get("journal", [])[-80:]):
                trade = event.get("trade", {})
                journal_rows.append({
                    "event": event.get("event"),
                    "at_bar": str(event.get("at_bar", ""))[:16],
                    "strategy": event.get("strategy"),
                    "entry": str(trade.get("entry_time", ""))[:16],
                    "exit": str(trade.get("exit_time", ""))[:16] if trade.get("exit_time") else "",
                    "dir": "LONG" if trade.get("direction") == 1 else "SHORT",
                    "pnl": round(float(trade.get("pnl", 0.0)), 2),
                    "result": trade.get("result", ""),
                })
            if journal_rows:
                with st.expander(f"Replay journal ({len(journal_rows)} events)", expanded=False):
                    st.dataframe(journal_rows, use_container_width=True)

            if replay_auto and cursor_idx < end_idx:
                df = replay_df
                session_dict, events = advance_replay(
                    replay_session,
                    df,
                    steps=int(replay_bars_per_tick),
                )
                st.session_state.replay_session = session_dict
                delay_ms = int(replay_tick_seconds * 1000)
                components.html(
                    f"""
                    <script>
                      setTimeout(function() {{
                        window.parent.location.reload();
                      }}, {delay_ms});
                    </script>
                    """,
                    height=0,
                )
            elif replay_auto and cursor_idx >= end_idx:
                st.session_state.replay_auto_play = False
                st.success("Replay đã tới cuối khoảng.")

# ══════════════════════════════════════════════════════════════════════════
# TAB 5 — Cấu hình
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
