#!/usr/bin/env python3
"""Streamlit UI — biểu đồ, cấu hình, tối ưu rolling."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import yaml

from systemtrain.orchestrator.rolling_production import current_trade_year, history_path_for_train_year, train_year_for
from systemtrain.ui.charts import (
    make_strategy_illustration_chart,
    metrics_all_html,
    metrics_cards_html,
    render_professional_chart,
    render_professional_multi_strategy_chart,
    strategy_color,
    strategy_legend_html,
)
from systemtrain.ui.meta import STRATEGIES, STRATEGY_ORDER
from systemtrain.ui.optimize_jobs import list_jobs, start_optimize_job
from systemtrain.ui.services import (
    get_train_config_state,
    get_rolling_state,
    load_base_yaml,
    load_history_train_year,
    load_history_train_years,
    load_price_data,
    merge_params,
    run_all_backtest,
    run_all_strategies_backtest,
    run_strategy_backtest,
    save_params_for_train_year,
    config_train_year_saved,
)

st.set_page_config(
    page_title="SystemTrain — EURUSD",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

UI_SETTINGS_PATH = Path("config/ui_settings.json")


def _load_ui_settings() -> dict:
    if not UI_SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(UI_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_ui_settings(settings: dict) -> None:
    UI_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    UI_SETTINGS_PATH.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")


_ui_settings = _load_ui_settings()


# ── Session defaults ─────────────────────────────────────────────────────
if "trade_year" not in st.session_state:
    st.session_state.trade_year = int(_ui_settings.get("trade_year", current_trade_year()))
if "param_overrides" not in st.session_state:
    st.session_state.param_overrides = {}
if "equity" not in st.session_state:
    st.session_state.equity = float(_ui_settings.get("equity", 1000.0))
if "risk_per_trade_pct" not in st.session_state:
    st.session_state.risk_per_trade_pct = float(_ui_settings.get("risk_per_trade_pct", 2.0))
if "target_rr" not in st.session_state:
    st.session_state.target_rr = float(_ui_settings.get("target_rr", 2.0))
if "chart_backtest_cache" not in st.session_state:
    st.session_state.chart_backtest_cache = {}


def _persist_ui_settings(**updates) -> None:
    current = _load_ui_settings()
    current.update(updates)
    _save_ui_settings(current)


def _risk_sl_pct() -> float:
    return float(st.session_state.risk_per_trade_pct) / 100.0


def _target_rr() -> float:
    return float(st.session_state.target_rr)


def _chart_cache_key(train_year: int, trade_year: int, sl_pct: float | None = None) -> str:
    risk = _risk_sl_pct() if sl_pct is None else float(sl_pct)
    return f"train:{int(train_year)}|trade:{int(trade_year)}|risk:{risk:.4f}|rr:{_target_rr():.2f}|all"


def _cache_all_chart_result(train_year: int, trade_year: int, results: dict, period_df, sl_pct: float | None = None) -> None:
    risk = _risk_sl_pct() if sl_pct is None else float(sl_pct)
    st.session_state.chart_backtest_cache[_chart_cache_key(train_year, trade_year, risk)] = {
        "mode": "all",
        "results": results,
        "df": period_df,
        "trade_year": int(trade_year),
        "train_year": int(train_year),
        "risk_sl_pct": risk,
        "risk_min_rr": _target_rr(),
        "strategy": "All",
    }


def _combined_return_from_all_results(results: dict) -> float:
    return sum(float(item.get("metrics", {}).get("total_return", 0)) for item in results.values())


def _clear_chart_cache_for_train_year(train_year: int) -> None:
    prefix = f"train:{int(train_year)}|"
    for key in list(st.session_state.chart_backtest_cache.keys()):
        if key.startswith(prefix):
            del st.session_state.chart_backtest_cache[key]


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
                min_v = int(spec["min"])
                max_v = int(spec["max"])
                raw_v = int(val) if val is not None else min_v
                value = min(max(raw_v, min_v), max_v)
                if raw_v != value:
                    st.caption(f"Giá trị lưu `{raw_v}` nằm ngoài range UI, tạm hiển thị `{value}`.")
                out[key] = st.number_input(spec["label"], min_value=min_v, max_value=max_v, value=value, step=int(spec.get("step", 1)), key=f"{strategy}_{key}")
            else:
                min_v = float(spec["min"])
                max_v = float(spec["max"])
                raw_v = float(val) if val is not None else min_v
                value = min(max(raw_v, min_v), max_v)
                if abs(raw_v - value) > 1e-12:
                    st.caption(f"Giá trị lưu `{raw_v:g}` nằm ngoài range UI, tạm hiển thị `{value:g}`.")
                out[key] = st.number_input(spec["label"], min_value=min_v, max_value=max_v, value=value, step=float(spec.get("step", 0.1)), key=f"{strategy}_{key}")
    return out


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    avg = _avg(values)
    return (sum((v - avg) ** 2 for v in values) / len(values)) ** 0.5


def _fmt_pct(value: float) -> str:
    return f"{value:+.1%}"


def _stability_score(
    avg_ret: float,
    worst_ret: float,
    volatility: float,
    negative_years: int,
    avg_pf: float,
    avg_wr: float,
) -> float:
    """Simple 0-100 score: reward steady positive OOS, punish bad/wobbly years."""
    raw = (
        50
        + avg_ret * 120
        + worst_ret * 80
        - volatility * 70
        - negative_years * 8
        + min(avg_pf, 2.5) * 7
        + avg_wr * 10
    )
    return max(0.0, min(100.0, raw))


# ── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📈 SystemTrain")
    st.caption("Optimize theo train year, kiểm chứng qua nhiều trade year.")

    st.markdown("**⚙️ Phiên làm việc**")
    trade_year_options = list(range(2022, current_trade_year() + 1))
    if st.session_state.trade_year not in trade_year_options:
        st.session_state.trade_year = trade_year_options[-1]
    st.session_state.equity = st.number_input(
        "Vốn tham chiếu ($)",
        min_value=100.0,
        value=st.session_state.equity,
        step=100.0,
        help="Dùng để quy đổi PnL/return trong backtest và chart.",
    )
    st.session_state.risk_per_trade_pct = st.number_input(
        "Risk mỗi lệnh (%)",
        min_value=0.1,
        max_value=10.0,
        value=float(st.session_state.risk_per_trade_pct),
        step=0.1,
        help="Mặc định 2%. Ví dụ vốn $1,000 và risk 2% nghĩa là rủi ro tối đa khoảng $20/lệnh trước spread/slippage.",
    )
    st.session_state.target_rr = st.number_input(
        "RR mục tiêu",
        min_value=0.5,
        max_value=10.0,
        value=float(st.session_state.target_rr),
        step=0.1,
        help="Mặc định 2R. Ví dụ RR 2.0 nghĩa là TP xa gấp 2 lần khoảng rủi ro SL.",
    )
    st.session_state.trade_year = st.selectbox(
        "Năm trade mặc định",
        trade_year_options,
        index=trade_year_options.index(st.session_state.trade_year),
        help="Năm trade được dùng làm mặc định cho các màn So sánh và Soi chart.",
    )
    _persist_ui_settings(
        equity=float(st.session_state.equity),
        risk_per_trade_pct=float(st.session_state.risk_per_trade_pct),
        target_rr=float(st.session_state.target_rr),
        trade_year=int(st.session_state.trade_year),
    )

    sidebar_trade_year = st.session_state.trade_year
    sidebar_train_year = train_year_for(sidebar_trade_year)
    st.info(
        f"Config mặc định: **Train {sidebar_train_year}** → Backtest **Trade {sidebar_trade_year}** · "
        f"Risk **{st.session_state.risk_per_trade_pct:.1f}%/lệnh** · RR **{st.session_state.target_rr:.1f}R**"
    )

    st.divider()
    st.markdown("**✅ Trạng thái hệ thống**")
    saved_train_years = load_history_train_years()
    if config_train_year_saved(sidebar_train_year):
        st.success(f"Đã có config train {sidebar_train_year}")
    else:
        st.warning(f"Chưa có config train {sidebar_train_year}")
    st.caption(f"{len(saved_train_years)} config train đã lưu" if saved_train_years else "Chưa có config train đã lưu")

    try:
        df = load_price_data()
        st.success("Dữ liệu giá sẵn sàng")
        st.caption(f"{df.index.min().date()} → {df.index.max().date()} · {len(df):,} nến 1H")
    except Exception as e:
        st.error(f"Không load được data: {e}")

    cache_count = len(st.session_state.chart_backtest_cache)
    st.caption(f"{cache_count} chart cache trong phiên hiện tại")

    with st.expander("🧰 Công cụ kỹ thuật"):
        st.code("python3 run_rolling_remine.py", language="bash")
        st.code("streamlit run run_app.py", language="bash")

# ── Header ───────────────────────────────────────────────────────────────
ty = st.session_state.trade_year
st.title("📈 SystemTrain")
st.caption("Tạo config, kiểm chứng độ ổn định và soi chart từng lệnh.")

tab_opt, tab_config, tab_results, tab_chart, tab_overview = st.tabs(
    ["🧪 Tạo config", "🛠️ Chỉnh config", "📊 So sánh", "📈 Soi chart", "📚 Chiến lược"]
)

# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — Tổng quan
# ══════════════════════════════════════════════════════════════════════════
with tab_overview:
    st.subheader("📚 Các chiến lược trong hệ thống")
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
        "**Workflow:** Tạo config từ năm train, kiểm chứng trên nhiều năm trade, rồi soi chart từng lệnh. "
        "5 chiến lược: Wyckoff, RSI, EMA Elite, EMA Flow, Pin Bar."
    )

# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — Biểu đồ
# ══════════════════════════════════════════════════════════════════════════
with tab_chart:
    st.subheader("📈 Soi chart và lệnh")
    chart_options = ["All (tất cả)"] + STRATEGY_ORDER
    chart_train_options = load_history_train_years() or list(range(2021, current_trade_year()))
    with st.container(border=True):
        top1, top2, top3 = st.columns([2.0, 1.1, 1.1])
        with top1:
            chart_strategy = st.selectbox("Nhóm tín hiệu", chart_options)
        with top2:
            chart_train_year = st.selectbox(
                "Bộ config",
                chart_train_options,
                index=len(chart_train_options) - 1,
                format_func=lambda y: f"Train {y}",
            )
        with top3:
            chart_trade_year = st.selectbox(
                "Năm trade",
                list(range(2021, current_trade_year() + 1)),
                index=max(0, ty - 2021),
            )

        nav1, nav2 = st.columns([1, 1])
        with nav1:
            show_ema = st.toggle("EMA", value=bool(_ui_settings.get("show_ema", True)))
        with nav2:
            show_volume = st.toggle("Volume", value=bool(_ui_settings.get("show_volume", True)))
        if chart_strategy.startswith("All"):
            saved_strategies = _ui_settings.get("selected_chart_strategies", STRATEGY_ORDER)
            if not isinstance(saved_strategies, list):
                saved_strategies = STRATEGY_ORDER
            saved_strategies = [s for s in saved_strategies if s in STRATEGY_ORDER] or STRATEGY_ORDER
            selected_chart_strategies = st.multiselect(
                "Chiến lược muốn hiển thị",
                STRATEGY_ORDER,
                default=saved_strategies,
                help="Bỏ chọn chiến lược nếu muốn ẩn tín hiệu/lệnh của chiến lược đó khỏi chart và trade blotter.",
            )
        else:
            selected_chart_strategies = [chart_strategy]
        _persist_ui_settings(
            show_ema=bool(show_ema),
            show_volume=bool(show_volume),
            selected_chart_strategies=selected_chart_strategies if chart_strategy.startswith("All") else _ui_settings.get("selected_chart_strategies", STRATEGY_ORDER),
        )

    chart_max_bars = 100_000_000
    chart_height = 700
    focus_trades = False

    hist_state = load_history_train_year(chart_train_year)
    if hist_state is None:
        hist_state = get_train_config_state(chart_train_year, st.session_state.equity)
    overrides = st.session_state.param_overrides
    state = merge_params(hist_state, overrides)
    is_all = chart_strategy.startswith("All")
    cache_key = _chart_cache_key(chart_train_year, chart_trade_year, _risk_sl_pct())
    cached_chart = st.session_state.chart_backtest_cache.get(cache_key) if is_all and not overrides else None
    if cached_chart and (
        not st.session_state.get("last_chart")
        or st.session_state.last_chart.get("train_year") != chart_train_year
        or st.session_state.last_chart.get("trade_year") != chart_trade_year
        or st.session_state.last_chart.get("mode") != "all"
    ):
        st.session_state.last_chart = cached_chart
        st.caption("Đang dùng lại kết quả backtest đã có từ Tạo config/So sánh. Bấm refresh nếu muốn chạy lại.")

    if st.button("🔄 Refresh backtest & mở chart" if cached_chart else "▶️ Chạy backtest & mở chart", type="primary"):
        with st.spinner("Đang backtest..."):
            try:
                if is_all:
                    results, period_df = run_all_strategies_backtest(
                        state, chart_trade_year, st.session_state.equity, sl_pct=_risk_sl_pct(), min_rr=_target_rr(),
                    )
                    _cache_all_chart_result(chart_train_year, chart_trade_year, results, period_df, _risk_sl_pct())
                    st.session_state.last_chart = st.session_state.chart_backtest_cache[cache_key]
                else:
                    metrics, trades, period_df = run_strategy_backtest(
                        chart_strategy, state, chart_trade_year, st.session_state.equity, sl_pct=_risk_sl_pct(), min_rr=_target_rr(),
                    )
                    st.session_state.last_chart = {
                        "mode": "single",
                        "metrics": metrics,
                        "trades": trades,
                        "df": period_df,
                        "strategy": chart_strategy,
                        "trade_year": chart_trade_year,
                        "train_year": chart_train_year,
                        "risk_sl_pct": _risk_sl_pct(),
                        "risk_min_rr": _target_rr(),
                    }
            except Exception as e:
                st.error(str(e))

    lc = st.session_state.get("last_chart")
    chart_ok = (
        lc
        and lc.get("trade_year") == chart_trade_year
        and lc.get("train_year") == chart_train_year
        and abs(float(lc.get("risk_sl_pct", 0.02)) - _risk_sl_pct()) < 1e-9
        and abs(float(lc.get("risk_min_rr", 2.0)) - _target_rr()) < 1e-9
        and (lc.get("mode") == "all") == is_all
        and (is_all or lc.get("strategy") == chart_strategy)
    )

    if chart_ok:
        def _trade_key(sname: str, trade) -> str:
            return f"{sname}|{trade.entry_time}"

        chart_trades: list[tuple[str, str, object]] = []
        if lc["mode"] == "all":
            for trade_sname in selected_chart_strategies:
                for trade in lc["results"].get(trade_sname, {}).get("trades", []):
                    chart_trades.append((_trade_key(trade_sname, trade), trade_sname, trade))
        elif lc.get("trades"):
            for trade in lc["trades"]:
                chart_trades.append((_trade_key(lc["strategy"], trade), lc["strategy"], trade))

        focused_key = st.session_state.get("chart_focus_trade_key")
        focused_match = next((item for item in chart_trades if item[0] == focused_key), None)
        focused_strategy = focused_match[1] if focused_match else None
        focused_trade = focused_match[2] if focused_match else None
        if focused_key and not focused_match:
            st.session_state.chart_focus_trade_key = None

        if focused_trade is not None:
            f1, f2 = st.columns([4, 1])
            with f1:
                st.info(
                    f"Đang focus lệnh {focused_strategy}: "
                    f"{str(focused_trade.entry_time)[:16]} → "
                    f"{str(focused_trade.exit_time)[:16] if focused_trade.exit_time else 'open'} "
                    f"· PnL {focused_trade.pnl:+.2f}"
                )
            with f2:
                if st.button("Clear focus"):
                    st.session_state.chart_focus_trade_key = None
                    st.rerun()

        def _render_strategy_chart(sname: str, trades: list, metrics: dict | None = None) -> None:
            info = STRATEGIES[sname]
            hint = info.get("chart_hint", "")
            strategy_focus_trade = focused_trade if focused_strategy == sname else None
            if metrics:
                st.markdown(
                    f"<span style='color:{strategy_color(sname)};font-size:16px'>●</span> "
                    f"**{info['icon']} {sname}** — {metrics_cards_html(metrics)}",
                    unsafe_allow_html=True,
                )
            if hint:
                st.caption(hint)
            ema_override = show_ema if sname not in ("EMA 50/200", "EMA Flow") else True

            try:
                render_professional_chart(
                    lc["df"],
                    sname,
                    trades,
                    chart_id=f"{sname}-train{chart_train_year}-trade{chart_trade_year}-{lc['mode']}",
                    show_ema=ema_override,
                    show_volume=show_volume,
                    equity=st.session_state.equity,
                    max_bars=chart_max_bars,
                    height=chart_height,
                    focus_trades=focus_trades,
                    focus_trade=strategy_focus_trade,
                )
            except Exception as e:
                st.error(f"Professional chart lỗi: {e}")

        if lc["mode"] == "all":
            selected_results = {
                sname: lc["results"].get(sname, {})
                for sname in selected_chart_strategies
                if sname in lc["results"]
            }
            if not selected_results:
                st.warning("Chọn ít nhất một chiến lược để hiển thị trên chart tổng hợp.")
            else:
                st.markdown(metrics_all_html(selected_results), unsafe_allow_html=True)
                st.markdown(strategy_legend_html(list(selected_results.keys())), unsafe_allow_html=True)
                st.caption("Chart tổng hợp mặc định: một biểu đồ giá overlay tín hiệu/lệnh của các chiến lược đã chọn.")
            strategy_trades = {
                sname: selected_results.get(sname, {}).get("trades", [])
                for sname in selected_results.keys()
            }
            try:
                render_professional_multi_strategy_chart(
                    lc["df"],
                    strategy_trades,
                    chart_id=f"all-strategies-train{chart_train_year}-trade{chart_trade_year}-{lc['mode']}",
                    show_ema=show_ema,
                    show_volume=show_volume,
                    equity=st.session_state.equity,
                    max_bars=chart_max_bars,
                    height=chart_height,
                    focus_trades=focus_trades,
                    focus_trade=focused_trade,
                )
            except Exception as e:
                st.error(f"Chart tổng hợp Professional lỗi: {e}")
        else:
            _render_strategy_chart(lc["strategy"], lc.get("trades", []), lc.get("metrics"))

        st.caption(
            "Professional chart: lăn chuột để zoom, kéo chart để pan, nút Fit để reset. "
            "Đỏ đứt = SL · Xanh chấm = TP."
        )

        rows = []
        if lc["mode"] == "all":
            for sname in selected_chart_strategies:
                for t in lc["results"].get(sname, {}).get("trades", []):
                    rows.append({
                        "key": _trade_key(sname, t),
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
                    "key": _trade_key(lc["strategy"], t),
                    "Chiến lược": lc["strategy"],
                    "entry": str(t.entry_time)[:16],
                    "exit": str(t.exit_time)[:16] if t.exit_time else "",
                    "dir": "LONG" if t.direction == 1 else "SHORT",
                    "pnl": round(t.pnl, 2),
                    "result": t.result,
                })
        if rows:
            with st.expander(f"Trade blotter ({len(rows)} lệnh)", expanded=False):
                header = st.columns([1.2, 2.0, 2.0, 0.8, 0.9, 1.0, 0.9])
                for col, label in zip(header, ["Chiến lược", "Entry", "Exit", "Dir", "PnL", "Result", "Focus"]):
                    col.markdown(f"**{label}**")
                for i, row in enumerate(rows):
                    cols = st.columns([1.2, 2.0, 2.0, 0.8, 0.9, 1.0, 0.9])
                    cols[0].write(row["Chiến lược"])
                    cols[1].write(row["entry"])
                    cols[2].write(row["exit"])
                    cols[3].write(row["dir"])
                    cols[4].write(row["pnl"])
                    cols[5].write(row["result"])
                    active_focus = row["key"] == st.session_state.get("chart_focus_trade_key")
                    if cols[6].button("Focus" if not active_focus else "Focused", key=f"focus_trade_{i}_{row['key']}", disabled=active_focus):
                        st.session_state.chart_focus_trade_key = row["key"]
                        st.rerun()
    else:
        st.caption("Chọn config + năm trade, sau đó bấm **Chạy/refresh backtest & mở chart**.")

# ══════════════════════════════════════════════════════════════════════════
# TAB 3 — Cấu hình
# ══════════════════════════════════════════════════════════════════════════
with tab_config:
    st.subheader("🛠️ Chỉnh bộ config theo năm train")

    saved_train_years = load_history_train_years()
    train_year_options = sorted(set(saved_train_years + list(range(2021, current_trade_year()))))

    c_y1, c_y2, c_y3 = st.columns([1, 1, 2])
    with c_y1:
        default_train = train_year_for(ty)
        default_idx = train_year_options.index(default_train) if default_train in train_year_options else len(train_year_options) - 1
        config_train_year = st.selectbox(
            "Bộ config train",
            train_year_options,
            index=default_idx,
            help="Config được lưu theo năm train. Một config train có thể backtest nhiều năm trade.",
        )
    with c_y2:
        st.metric("Năm trade gợi ý", config_train_year + 1)
    with c_y3:
        hp = history_path_for_train_year(config_train_year)
        if config_train_year_saved(config_train_year):
            st.success(f"Đã có config: `{hp}`")
        else:
            st.warning(f"Chưa lưu — sẽ dùng base/fixed. File: `{hp}`")

    state = get_train_config_state(config_train_year, st.session_state.equity)
    if state.get("optimized_at"):
        st.caption(f"Cập nhật: {str(state['optimized_at'])[:19]} · Vốn ref: ${state.get('equity', 1000):,.0f}")
    auto_save_config = st.toggle(
            "Tự lưu thay đổi",
        value=bool(_ui_settings.get("auto_save_config", True)),
        help="Bật để mọi thay đổi được lưu vào bộ config train year, kể cả khi refresh trang.",
    )
    _persist_ui_settings(auto_save_config=bool(auto_save_config))

    edited: dict[str, dict] = {}
    for sname in STRATEGY_ORDER:
        st.markdown(f"### {STRATEGIES[sname]['icon']} {sname}")
        current = state["strategies"][sname]["params"]
        edited[sname] = _render_param_editor(sname, current)

    params_changed = any(
        edited[sname] != state["strategies"][sname]["params"]
        for sname in STRATEGY_ORDER
    )
    if auto_save_config and params_changed:
        new_state = merge_params(state, edited)
        new_state["equity"] = st.session_state.equity
        new_state["risk_sl_pct"] = _risk_sl_pct()
        new_state["risk_min_rr"] = _target_rr()
        path = save_params_for_train_year(new_state, config_train_year, set_active=False)
        _clear_chart_cache_for_train_year(config_train_year)
        if config_train_year == train_year_for(ty):
            st.session_state.param_overrides = edited
        st.success(f"Đã tự lưu thay đổi vào `{path}`")

    c1, c2, c3 = st.columns(3)
    with c1:
        also_active = st.checkbox(
            "Đặt làm config active",
            value=config_train_year == train_year_for(current_trade_year()),
            help="Cập nhật config/rolling/active.yaml bằng bộ config train này",
        )
    with c2:
        if st.button(f"💾 Lưu config train {config_train_year}", type="primary"):
            new_state = merge_params(state, edited)
            new_state["equity"] = st.session_state.equity
            new_state["risk_sl_pct"] = _risk_sl_pct()
            new_state["risk_min_rr"] = _target_rr()
            path = save_params_for_train_year(new_state, config_train_year, set_active=also_active)
            _clear_chart_cache_for_train_year(config_train_year)
            if config_train_year == train_year_for(ty):
                st.session_state.param_overrides = edited
            st.success(f"Đã lưu `{path}`")
            if also_active:
                st.info("Đã cập nhật config active")
            st.rerun()
    with c3:
        quick_trade_year = st.selectbox(
            "Năm trade test nhanh",
            list(range(2021, current_trade_year() + 1)),
            index=max(0, min(current_trade_year(), config_train_year + 1) - 2021),
        )
        if st.button("🧪 Test nhanh"):
            st.session_state.param_overrides = edited
            res = run_all_backtest(merge_params(state, edited), quick_trade_year, st.session_state.equity, sl_pct=_risk_sl_pct(), min_rr=_target_rr())
            st.json(res)

    with st.expander("Các bộ config đã lưu"):
        rows = []
        for y in train_year_options:
            hs = load_history_train_year(y)
            rows.append({
                "Năm train": y,
                "Trade mặc định": y + 1,
                "Đã lưu": "✓" if config_train_year_saved(y) else "—",
                "Optimized": str((hs or {}).get("optimized_at", ""))[:19] if hs else "",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    with st.expander(f"Raw — {history_path_for_train_year(config_train_year).name}"):
        p = history_path_for_train_year(config_train_year)
        if p.exists():
            st.code(p.read_text(encoding="utf-8"), language="yaml")
        elif Path("config/rolling/active.yaml").exists() and config_train_year == train_year_for(ty):
            st.code(Path("config/rolling/active.yaml").read_text(encoding="utf-8"), language="yaml")
        else:
            st.caption("Chưa có file — lưu hoặc dùng màn Tạo config.")

# ══════════════════════════════════════════════════════════════════════════
# TAB 4 — Tối ưu
# ══════════════════════════════════════════════════════════════════════════
with tab_opt:
    st.subheader("🧪 Tạo config bằng dữ liệu train")
    st.markdown(
        "Chọn năm dữ liệu dùng để tạo bộ config, sau đó kiểm chứng bộ config đó trên một hoặc nhiều năm trade."
    )

    train_candidates = list(range(2021, current_trade_year()))
    trade_candidates = list(range(2021, current_trade_year() + 1))
    o1, o2 = st.columns([1, 2])
    with o1:
        opt_train_years = st.multiselect(
            "Năm train để tạo config",
            train_candidates,
            default=[train_year_for(ty)] if train_year_for(ty) in train_candidates else train_candidates[-1:],
        )
    with o2:
        preview_trade_years = st.multiselect(
            "Năm trade để kiểm chứng",
            trade_candidates,
            default=[ty],
            help="Dùng config train vừa optimize để chạy thử trên các năm trade được chọn.",
        )
    adv1, adv2 = st.columns([1, 1])
    with adv1:
        advanced_search = st.toggle(
            "Tìm nâng cao",
            value=bool(_ui_settings.get("advanced_search", False)),
            help="Chạy nhiều candidate, kiểm chứng trên các năm trade đã chọn và tự chọn bộ config ổn định nhất.",
        )
    with adv2:
        advanced_runs = st.number_input(
            "Số candidate",
            min_value=2,
            max_value=8,
            value=int(_ui_settings.get("advanced_runs", 3)),
            step=1,
            disabled=not advanced_search,
        )
    _persist_ui_settings(advanced_search=bool(advanced_search), advanced_runs=int(advanced_runs))

    if st.button("🚀 Tạo config", type="primary", disabled=not opt_train_years):
        check_years = [int(y) for y in (preview_trade_years or [ty])]
        job = start_optimize_job(
            train_years=[int(y) for y in opt_train_years],
            trade_years=check_years,
            equity=float(st.session_state.equity),
            sl_pct=_risk_sl_pct(),
            min_rr=_target_rr(),
            advanced_search=bool(advanced_search),
            advanced_runs=int(advanced_runs),
        )
        st.success(f"Đã tạo job `{job['job_id']}`. Job sẽ tiếp tục chạy kể cả khi refresh trang.")
        st.rerun()

    jobs = list_jobs(limit=6)
    if jobs:
        st.markdown("**Job tạo config gần đây**")
        job_rows = []
        for job in jobs:
            progress_value = int(job.get("progress", 0))
            total_value = max(1, int(job.get("total", 1)))
            job_rows.append({
                "Job": job.get("job_id"),
                "Trạng thái": job.get("status"),
                "Tiến độ": f"{progress_value}/{total_value}",
                "Train": ", ".join(map(str, job.get("train_years", []))),
                "Trade": ", ".join(map(str, job.get("trade_years", []))),
                "Cập nhật": str(job.get("updated_at", ""))[:19],
                "Ghi chú": job.get("message", ""),
            })
            if job.get("status") in {"running", "queued"}:
                st.progress(progress_value / total_value, text=f"{job.get('job_id')} · {job.get('message', '')}")
        st.dataframe(job_rows, use_container_width=True, hide_index=True)
        if st.button("🔄 Refresh trạng thái job"):
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════
# TAB 5 — Kết quả
# ══════════════════════════════════════════════════════════════════════════
with tab_results:
    st.subheader("📊 So sánh độ ổn định theo Train x Trade")

    saved_train_years = load_history_train_years()
    result_train_options = saved_train_years or list(range(2021, current_trade_year()))
    result_trade_options = list(range(2021, current_trade_year() + 1))
    r1, r2 = st.columns(2)
    with r1:
        result_train_years = st.multiselect(
            "Bộ config train",
            result_train_options,
            default=result_train_options[-2:] if len(result_train_options) >= 2 else result_train_options,
        )
    with r2:
        result_trade_years = st.multiselect(
            "Năm trade kiểm chứng",
            result_trade_options,
            default=[ty],
        )

    rows = []
    stability_by_train: dict[int, list[dict[str, float]]] = {}
    stability_by_strategy: dict[tuple[int, str], list[dict[str, float]]] = {}
    if result_train_years and result_trade_years:
        with st.spinner("Đang chạy backtest matrix..."):
            for train_year in result_train_years:
                state = load_history_train_year(train_year)
                if not state:
                    continue
                try:
                    for trade_year in [int(y) for y in result_trade_years]:
                        chart_results, chart_df = run_all_strategies_backtest(state, trade_year, st.session_state.equity, sl_pct=_risk_sl_pct(), min_rr=_target_rr())
                        _cache_all_chart_result(int(train_year), trade_year, chart_results, chart_df, _risk_sl_pct())
                        combined_ret = _combined_return_from_all_results(chart_results)
                        stability_by_train.setdefault(train_year, []).append({
                            "return": combined_ret,
                            "trade_count": 0.0,
                            "win_rate": 0.0,
                            "profit_factor": 0.0,
                        })
                        rows.append({
                            "Train": train_year,
                            "Trade": trade_year,
                            "Chiến lược": "— TỔNG —",
                            "Lệnh": "",
                            "WR": "",
                            "PF": "",
                            "Return": _fmt_pct(combined_ret),
                        })
                        for sname, payload in chart_results.items():
                            m = payload.get("metrics", {})
                            trade_count = float(m.get("trade_count", 0))
                            win_rate = float(m.get("win_rate", 0))
                            profit_factor = float(m.get("profit_factor", 0))
                            total_return = float(m.get("total_return", 0))
                            stability_by_strategy.setdefault((train_year, sname), []).append({
                                "return": total_return,
                                "trade_count": trade_count,
                                "win_rate": win_rate,
                                "profit_factor": profit_factor,
                            })
                            stability_by_train[train_year][-1]["trade_count"] += trade_count
                            rows.append({
                                "Train": train_year,
                                "Trade": trade_year,
                                "Chiến lược": sname,
                                "Lệnh": int(trade_count),
                                "WR": f"{win_rate:.1%}",
                                "PF": f"{profit_factor:.2f}",
                                "Return": _fmt_pct(total_return),
                            })
                except Exception as e:
                    rows.append({
                        "Train": train_year,
                        "Trade": "",
                        "Chiến lược": "ERROR",
                        "Lệnh": "",
                        "WR": "",
                        "PF": "",
                        "Return": str(e),
                    })

    stability_rows = []
    for train_year, year_metrics in stability_by_train.items():
        returns = [m["return"] for m in year_metrics]
        strategy_metrics = [
            item
            for (strategy_train_year, _), items in stability_by_strategy.items()
            if strategy_train_year == train_year
            for item in items
        ]
        avg_pf = _avg([m["profit_factor"] for m in strategy_metrics])
        avg_wr = _avg([m["win_rate"] for m in strategy_metrics])
        total_trades = int(sum(m["trade_count"] for m in year_metrics))
        volatility = _std(returns)
        negative_years = sum(1 for r in returns if r < 0)
        score = _stability_score(_avg(returns), min(returns), volatility, negative_years, avg_pf, avg_wr)
        stability_rows.append({
            "Train": train_year,
            "Score ổn định": round(score, 1),
            "Avg Return": _fmt_pct(_avg(returns)),
            "Worst Year": _fmt_pct(min(returns)),
            "Volatility": f"{volatility:.1%}",
            "Năm âm": negative_years,
            "Tổng lệnh": total_trades,
            "Avg WR": f"{avg_wr:.1%}",
            "Avg PF": f"{avg_pf:.2f}",
        })
    stability_rows.sort(key=lambda row: row["Score ổn định"], reverse=True)

    strategy_stability_rows = []
    for (train_year, sname), items in stability_by_strategy.items():
        returns = [m["return"] for m in items]
        avg_pf = _avg([m["profit_factor"] for m in items])
        avg_wr = _avg([m["win_rate"] for m in items])
        volatility = _std(returns)
        negative_years = sum(1 for r in returns if r < 0)
        strategy_stability_rows.append({
            "Train": train_year,
            "Chiến lược": sname,
            "Score ổn định": round(_stability_score(_avg(returns), min(returns), volatility, negative_years, avg_pf, avg_wr), 1),
            "Avg Return": _fmt_pct(_avg(returns)),
            "Worst Year": _fmt_pct(min(returns)),
            "Năm âm": negative_years,
            "Tổng lệnh": int(sum(m["trade_count"] for m in items)),
            "Avg WR": f"{avg_wr:.1%}",
            "Avg PF": f"{avg_pf:.2f}",
        })
    strategy_stability_rows.sort(key=lambda row: (row["Train"], -row["Score ổn định"]))

    if stability_rows:
        best = stability_rows[0]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Config ổn định nhất", f"Train {best['Train']}")
        m2.metric("Score", best["Score ổn định"])
        m3.metric("Avg Return", best["Avg Return"])
        m4.metric("Worst Year", best["Worst Year"])
        st.caption(
            "Score ổn định ưu tiên return dương đều qua nhiều trade year, phạt worst year xấu, return biến động mạnh và số năm âm."
        )
        st.markdown("**Bảng xếp hạng bộ config**")
        st.dataframe(stability_rows, use_container_width=True, hide_index=True)
        with st.expander("Xem theo từng chiến lược"):
            st.dataframe(strategy_stability_rows, use_container_width=True, hide_index=True)

    if rows:
        st.markdown("**Chi tiết từng cặp Train x Trade**")
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.warning("Chưa có config train year hoặc chưa chọn năm backtest.")

    for fname in ["output/production_report.json", "output/rolling_walkforward_report.json", "output/rolling_remine_report.json"]:
        p = Path(fname)
        if p.exists():
            with st.expander(p.name):
                st.json(json.loads(p.read_text(encoding="utf-8")))

    if st.button("🔄 Backtest nhanh bộ config hiện tại"):
        quick_train_year = train_year_for(ty)
        state = get_train_config_state(quick_train_year, st.session_state.equity)
        quick_results, quick_df = run_all_strategies_backtest(state, ty, st.session_state.equity, sl_pct=_risk_sl_pct(), min_rr=_target_rr())
        _cache_all_chart_result(quick_train_year, ty, quick_results, quick_df, _risk_sl_pct())
        st.success("Đã backtest và lưu cache cho màn Soi chart.")
        st.json({
            "train_year": quick_train_year,
            "trade_year": ty,
            "combined_return": _combined_return_from_all_results(quick_results),
            "strategies": {sname: payload.get("metrics", {}) for sname, payload in quick_results.items()},
        })
