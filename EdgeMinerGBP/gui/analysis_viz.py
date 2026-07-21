"""Visualization & layout helpers — Phân tích / Báo cáo."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from analytics import (
  equity_series, exit_reason_stats, rolling_win_rate,
  trades_json_to_df, weekly_r_histogram, yearly_breakdown,
)
from config import DEFAULT_MAX_WEEKLY_LOSS_R, DEFAULT_RISK_PCT_PER_TRADE
from gui.execution_profile import AB_FILES, load_ab_json, resolve_execution_config
from gui.glossary import CONSTRAINT_LABELS, METRIC_LABELS
from strategy import risk_of_ruin_approx

# Plotly palette
C_GREEN = "#2ecc71"
C_RED = "#e74c3c"
C_BLUE = "#3498db"
C_AMBER = "#f39c12"
C_PURPLE = "#9b59b6"
C_MUTED = "#95a5a6"

_CHART_MARGIN = dict(l=48, r=24, t=48, b=40)


def inject_analysis_css():
  st.markdown(
    """
    <style>
    .ff-hero { padding: 0.25rem 0 0.75rem; }
    .ff-kpi-grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 0.65rem;
      margin-bottom: 0.75rem;
    }
    @media (max-width: 1100px) {
      .ff-kpi-grid { grid-template-columns: repeat(3, 1fr); }
    }
    .ff-kpi-card {
      border-radius: 12px;
      padding: 0.85rem 1rem;
      border: 1px solid rgba(128,128,128,0.25);
      background: linear-gradient(145deg, rgba(52,152,219,0.12), rgba(0,0,0,0.02));
    }
    .ff-kpi-card.pos { border-left: 4px solid #2ecc71; }
    .ff-kpi-card.neg { border-left: 4px solid #e74c3c; }
    .ff-kpi-card.neu { border-left: 4px solid #3498db; }
    .ff-kpi-card.warn { border-left: 4px solid #f39c12; }
    .ff-kpi-label { font-size: 0.78rem; opacity: 0.75; margin-bottom: 0.2rem; }
    .ff-kpi-value { font-size: 1.45rem; font-weight: 700; line-height: 1.2; }
    .ff-kpi-hint { font-size: 0.72rem; opacity: 0.6; margin-top: 0.15rem; }
    .ff-pill-row { display: flex; flex-wrap: wrap; gap: 0.45rem; margin: 0.5rem 0 0.75rem; }
    .ff-pill {
      display: inline-block;
      padding: 0.28rem 0.65rem;
      border-radius: 999px;
      font-size: 0.78rem;
      background: rgba(52,152,219,0.15);
      border: 1px solid rgba(52,152,219,0.35);
    }
    .ff-pill.lock { background: rgba(46,204,113,0.12); border-color: rgba(46,204,113,0.4); }
    .ff-ab-card {
      border-radius: 10px;
      padding: 0.55rem 0.75rem;
      margin-bottom: 0.45rem;
      border: 1px solid rgba(128,128,128,0.2);
      font-size: 0.85rem;
    }
    .ff-ab-card b { color: #2ecc71; }
    .ff-constraint-bar {
      height: 8px; border-radius: 4px; background: rgba(128,128,128,0.2); overflow: hidden;
      margin: 0.35rem 0 0.75rem;
    }
    .ff-constraint-fill {
      height: 100%; border-radius: 4px;
      background: linear-gradient(90deg, #2ecc71, #27ae60);
    }
    .ff-trade-win { border-left: 3px solid #2ecc71 !important; }
    .ff-trade-loss { border-left: 3px solid #e74c3c !important; }
    </style>
    """,
    unsafe_allow_html=True,
  )


def _chart_layout(title: str, height: int = 360) -> dict:
  return dict(
    title=dict(text=title, x=0, xanchor="left", font=dict(size=15)),
    height=height,
    margin=_CHART_MARGIN,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    hovermode="x unified",
  )


def _kpi_card(label: str, value: str, hint: str = "", tone: str = "neu") -> str:
  return (
    f'<div class="ff-kpi-card {tone}">'
    f'<div class="ff-kpi-label">{label}</div>'
    f'<div class="ff-kpi-value">{value}</div>'
    f'<div class="ff-kpi-hint">{hint}</div></div>'
  )


def render_hero_kpis(report: dict):
  o = report.get("overall_oos") or {}
  y = report.get("last_1_year") or {}
  total_r = float(o.get("total_r") or 0)
  tone_r = "pos" if total_r > 0 else "neg"
  wr = float(o.get("win_rate_pct") or 0)
  tone_wr = "pos" if wr >= 60 else ("warn" if wr >= 50 else "neg")

  cards = [
    _kpi_card(METRIC_LABELS["total_r"], f"{total_r:+.1f}R", f"1Y: {y.get('total_r', 0):+.1f}R", tone_r),
    _kpi_card(METRIC_LABELS["win_rate_pct"], f"{wr:.1f}%", f"1Y: {y.get('win_rate_pct', '—')}%", tone_wr),
    _kpi_card(METRIC_LABELS["profit_factor"], f"{o.get('profit_factor', '—')}", METRIC_LABELS["avg_rr"], "neu"),
    _kpi_card(METRIC_LABELS["max_drawdown_r"], f"{o.get('max_drawdown_r', 0)}R", "Càng thấp càng tốt", "warn"),
    _kpi_card(
      METRIC_LABELS["trades_per_week"],
      f"{o.get('trades_per_week', '—')}",
      f"{o.get('n_trades', 0)} lệnh OOS",
      "neu",
    ),
  ]
  st.markdown(f'<div class="ff-kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_constraints_score(constraints: dict | None):
  constraints = constraints or {}
  total = len(CONSTRAINT_LABELS)
  passed = sum(1 for k in CONSTRAINT_LABELS if constraints.get(k))
  pct = int(passed / total * 100) if total else 0

  st.markdown(f"**Mục tiêu hệ thống** — đạt **{passed}/{total}** ({pct}%)")
  st.markdown(
    f'<div class="ff-constraint-bar"><div class="ff-constraint-fill" '
    f'style="width:{pct}%"></div></div>',
    unsafe_allow_html=True,
  )
  cols = st.columns(2)
  items = list(CONSTRAINT_LABELS.items())
  for i, (key, label) in enumerate(items):
    ok = constraints.get(key, False)
    icon = "✅" if ok else "❌"
    cols[i % 2].markdown(f"{icon} {label}")


def render_config_pills(report: dict | None):
  ex = resolve_execution_config(report)
  cfg = (report or {}).get("config") or {}
  reopt = "mỗi tuần" if ex["reopt_period"] == "week" else "mỗi tháng"
  pills = [
    ("🔁 Reopt", reopt, True),
    ("⏱ Hold", f"{ex['max_hold_bars']} bars", True),
    ("↔ Gap", f"{ex['min_bars_between']} bars", True),
    ("📈 Trail", f"{ex['trail_activate_r']}/{ex['trail_distance_r']} R", True),
    ("🎯 Quota", f"{ex['max_trades_per_week']}/tuần", True),
    ("💸 Phí", f"{cfg.get('spread_pips', 1)}/{cfg.get('slippage_pips', 0.3)} pip", False),
  ]
  if report:
    pills.append((
      "🧠 KB",
      f"{'ON' if cfg.get('use_learning_kb') else 'OFF'} · {cfg.get('train_months', '?')}T",
      False,
    ))
  html = '<div class="ff-pill-row">'
  for label, val, locked in pills:
    cls = "ff-pill lock" if locked else "ff-pill"
    html += f'<span class="{cls}">{label}: <b>{val}</b></span>'
  html += "</div>"
  st.markdown(html, unsafe_allow_html=True)


def render_ab_decision_cards():
  rows = []
  if data := load_ab_json(AB_FILES["reopt"][1]):
    rows.append(("Reopt", data.get("winner", "week"), "✓ Giữ weekly"))
  if data := load_ab_json(AB_FILES["quota"][1]):
    rows.append(("Quota", data.get("winner", ""), "✓ Giữ 2 lệnh/tuần"))
  if data := load_ab_json(AB_FILES["max_hold"][1]):
    w = data.get("winner", 24)
    rows.append(("Max hold", f"{w} bars (max R)", "✓ Lock 24 bars"))
  if data := load_ab_json(AB_FILES["exec"][1]):
    rows.append(("Min bars", data.get("min_bars_winner", "gap=4"), "✓ Lock gap=4"))
    rows.append(("Trail", data.get("trail_winner", ""), "✓ Lock 1.0/0.5"))
  if not rows:
    return
  st.markdown("**Quyết định A/B**")
  for name, winner, decision in rows:
    st.markdown(
      f'<div class="ff-ab-card"><b>{name}</b> · test thắng: <code>{winner}</code><br/>{decision}</div>',
      unsafe_allow_html=True,
    )


def chart_equity_drawdown(trades_df: pd.DataFrame) -> go.Figure | None:
  eq = equity_series(trades_df)
  if eq.empty:
    return None
  fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3],
    vertical_spacing=0.06,
  )
  fig.add_trace(
    go.Scatter(
      x=eq["entry"], y=eq["equity_r"], name="Equity (R)",
      fill="tozeroy", line=dict(color=C_GREEN, width=2),
    ),
    row=1, col=1,
  )
  fig.add_trace(
    go.Scatter(
      x=eq["entry"], y=-eq["drawdown_r"], name="Drawdown",
      fill="tozeroy", line=dict(color=C_RED, width=1.5),
    ),
    row=2, col=1,
  )
  fig.update_layout(**_chart_layout("Đường lợi nhuận & sụt giảm (R)", 420))
  fig.update_yaxes(title_text="R", row=1, col=1)
  fig.update_yaxes(title_text="DD", row=2, col=1)
  return fig


def chart_weekly_bars(weekly_log: list[dict], *, max_weekly_r: float = 4.0) -> go.Figure | None:
  wdf = weekly_r_histogram(weekly_log)
  if wdf.empty:
    return None
  wdf["week"] = pd.to_datetime(wdf["week"])
  colors = [C_GREEN if r >= 0 else C_RED for r in wdf["oos_r"]]
  fig = go.Figure(go.Bar(
    x=wdf["week"], y=wdf["oos_r"],
    marker_color=colors, name="R/tuần",
  ))
  fig.add_hline(y=0, line_color=C_MUTED, line_width=1)
  fig.add_hline(y=-max_weekly_r, line_dash="dash", line_color=C_AMBER,
                annotation_text=f"Giới hạn -{max_weekly_r}R")
  fig.update_layout(**_chart_layout("Lợi nhuận theo tuần (R)", 300))
  return fig


def chart_r_distribution(trades_df: pd.DataFrame) -> go.Figure | None:
  if trades_df.empty or "r" not in trades_df.columns:
    return None
  fig = px.histogram(
    trades_df, x="r", nbins=24, color_discrete_sequence=[C_BLUE],
  )
  fig.add_vline(x=0, line_color=C_MUTED)
  fig.update_layout(**_chart_layout("Phân bố R mỗi lệnh", 280))
  return fig


def chart_direction_pie(trades_df: pd.DataFrame) -> go.Figure | None:
  if trades_df.empty or "dir" not in trades_df.columns:
    return None
  g = trades_df.groupby("dir").size().reset_index(name="count")
  fig = px.pie(g, names="dir", values="count", hole=0.45,
               color="dir", color_discrete_map={"LONG": C_GREEN, "SHORT": C_RED})
  fig.update_layout(**_chart_layout("Long vs Short", 280))
  return fig


def chart_monthly_r(trades_df: pd.DataFrame) -> go.Figure | None:
  if trades_df.empty:
    return None
  df = trades_df.copy()
  df["month"] = df["entry"].dt.to_period("M").astype(str)
  m = df.groupby("month")["r"].sum().reset_index()
  colors = [C_GREEN if r >= 0 else C_RED for r in m["r"]]
  fig = go.Figure(go.Bar(x=m["month"], y=m["r"], marker_color=colors))
  fig.add_hline(y=0, line_color=C_MUTED)
  fig.update_layout(**_chart_layout("Lợi nhuận theo tháng (R)", 300))
  return fig


def chart_exit_reasons(trades_df: pd.DataFrame) -> go.Figure | None:
  stats = exit_reason_stats(trades_df)
  if stats.empty:
    return None
  fig = go.Figure(go.Bar(
    x=stats["reason"], y=stats["count"],
    marker_color=C_PURPLE, text=stats["total_r"].round(1),
    textposition="outside",
  ))
  fig.update_layout(**_chart_layout("Lý do thoát lệnh", 300))
  fig.update_xaxes(tickangle=-20)
  return fig


def chart_rolling_wr(trades_df: pd.DataFrame, window: int = 20) -> go.Figure | None:
  roll = rolling_win_rate(trades_df, window)
  if roll.empty:
    return None
  fig = go.Figure(go.Scatter(
    x=roll["entry"], y=roll["rolling_wr"],
    line=dict(color=C_AMBER, width=2), name=f"WR {window} lệnh",
  ))
  fig.add_hline(y=60, line_dash="dot", line_color=C_GREEN, annotation_text="Mục tiêu 60%")
  fig.update_layout(**_chart_layout(f"Tỷ lệ thắng trượt ({window} lệnh)", 280))
  fig.update_yaxes(range=[0, 100], ticksuffix="%")
  return fig


def _show_chart(fig: go.Figure | None, key: str):
  if fig is not None:
    st.plotly_chart(fig, use_container_width=True, key=key)


def render_overview(report: dict):
  """Tab tổng quan — dashboard trực quan."""
  trades_df = trades_json_to_df(report.get("trades", []))
  render_hero_kpis(report)

  c1, c2 = st.columns([1.4, 1])
  with c1:
    _show_chart(chart_equity_drawdown(trades_df), "an_ov_equity")
  with c2:
    render_constraints_score(report.get("constraints_met"))
    ydf = yearly_breakdown(trades_df)
    if not ydf.empty:
      st.markdown("**Theo năm**")
      st.dataframe(ydf, use_container_width=True, hide_index=True)

  c3, c4, c5 = st.columns(3)
  with c3:
    _show_chart(chart_weekly_bars(report.get("weekly_log") or []), "an_ov_weekly")
  with c4:
    _show_chart(chart_monthly_r(trades_df), "an_ov_monthly")
  with c5:
    _show_chart(chart_direction_pie(trades_df), "an_ov_dir")

  c6, c7 = st.columns(2)
  with c6:
    _show_chart(chart_r_distribution(trades_df), "an_ov_rdist")
  with c7:
    _show_chart(chart_rolling_wr(trades_df), "an_ov_rollwr")


def render_risk_panel(report: dict, *, risk_pct: float, max_weekly_r: float):
  o = report["overall_oos"]
  trades_df = trades_json_to_df(report.get("trades", []))
  ruin_pct = o.get("risk_of_ruin_pct", 0)
  if not trades_df.empty and "r" in trades_df.columns:
    rs = trades_df["r"].astype(float)
    wins = rs > 0
    wr = float(wins.mean())
    aw = float(rs[wins].mean()) if wins.any() else 0.0
    al = float(abs(rs[~wins].mean())) if (~wins).any() else 1.0
    ruin_pct = round(risk_of_ruin_approx(wr, aw, al, risk_pct) * 100, 1)

  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Sụt giảm max", f"{o.get('max_drawdown_r', 0)}R")
  c2.metric("Chuỗi thắng", o.get("max_win_streak", "—"))
  c3.metric("Chuỗi thua", o.get("max_loss_streak", "—"))
  c4.metric("Risk of ruin", f"{ruin_pct}%", help="Ước lượng thống kê")

  _show_chart(chart_equity_drawdown(trades_df), "an_risk_equity")

  c5, c6 = st.columns(2)
  with c5:
    _show_chart(
      chart_weekly_bars(report.get("weekly_log") or [], max_weekly_r=max_weekly_r),
      "an_risk_weekly",
    )
  with c6:
    wlog = report.get("weekly_log") or []
    wdf = pd.DataFrame([w for w in wlog if "oos_r" in w])
    if not wdf.empty:
      breach = wdf[wdf["oos_r"] <= -max_weekly_r]
      st.metric("Tuần vượt giới hạn lỗ", f"{len(breach)} / {len(wdf)}")
      if len(breach):
        st.dataframe(
          breach[["week_start", "oos_r", "oos_trades"]].rename(
            columns={"week_start": "Tuần", "oos_r": "R", "oos_trades": "Lệnh"},
          ),
          use_container_width=True, hide_index=True,
        )

  if "holdout_forward" in report:
    with st.expander("Hold-out forward (strict)"):
      st.json(report["holdout_forward"]["metrics"])


def render_strategy_cards(strat: dict):
  """Hiển thị strategy dạng thẻ — không dùng JSON thô."""
  if not strat:
    st.info("Chưa có strategy.")
    return
  st.markdown(f"### {strat.get('name', 'Strategy')}")
  chips = [
    ("Exit", strat.get("exit_mode", "—")),
    ("RR", strat.get("rr", "—")),
    ("ATR×", strat.get("atr_mult", "—")),
    ("ML min", f"{float(strat.get('ml_prob_min', 0)):.2f}"),
    ("Hold", f"{strat.get('max_hold_bars', '—')} bars"),
    ("Gap", f"{strat.get('min_bars_between', '—')}"),
    ("Trail", f"{strat.get('trail_activate_r', '—')}/{strat.get('trail_distance_r', '—')}"),
  ]
  html = '<div class="ff-pill-row">'
  for k, v in chips:
    html += f'<span class="ff-pill">{k}: <b>{v}</b></span>'
  html += "</div>"
  st.markdown(html, unsafe_allow_html=True)

  c1, c2 = st.columns(2)
  with c1:
    st.markdown("**Long rules**")
    for r in strat.get("long_rules", []):
      st.markdown(f"`{r['feat']}` {r['op']} {r['thr']} · w={r['w']}")
  with c2:
    st.markdown("**Short rules**")
    for r in strat.get("short_rules", []):
      st.markdown(f"`{r['feat']}` {r['op']} {r['thr']} · w={r['w']}")


def default_risk_controls(report: dict, *, key_prefix: str = "risk"):
  cfg = report.get("config", {})
  c1, c2 = st.columns(2)
  with c1:
    risk_pct = st.slider(
      "Rủi ro % / lệnh (giả định)", 0.25, 3.0,
      float(cfg.get("risk_pct_per_trade", DEFAULT_RISK_PCT_PER_TRADE)),
      0.25, key=f"{key_prefix}_pct",
    )
  with c2:
    max_weekly_r = st.number_input(
      "Giới hạn lỗ tuần (R)", 1.0, 20.0, DEFAULT_MAX_WEEKLY_LOSS_R,
      key=f"{key_prefix}_week",
    )
  return risk_pct, max_weekly_r
