"""MT5 Bridge monitor — Backtest OOS vs Live auto trades (health + risk)."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analytics import equity_series, monthly_breakdown, trades_json_to_df
from gui.model_health import assess_monthly_degradation, monthly_oos_from_report
from gui.trade_model import format_model_label, load_model_report
from mt5_bridge.models import conditions_fingerprint, get_model_run_params
from mt5_bridge.trade_journal import MODE_AUTO, compute_stats, filter_trades, load_trades


def live_trades_to_analytics_df(trades: list[dict]) -> pd.DataFrame:
  """Map Bridge journal rows → analytics schema (entry, r)."""
  rows = []
  for t in trades:
    if t.get("status") and str(t.get("status")).upper() != "CLOSED":
      continue
    if t.get("r") is None:
      continue
    entry = t.get("entry_time") or t.get("exit_time") or t.get("updated_at")
    if not entry:
      continue
    rows.append({
      "entry": entry,
      "exit": t.get("exit_time"),
      "r": float(t["r"]),
      "dir": t.get("direction") or t.get("dir"),
      "result": t.get("result"),
    })
  return trades_json_to_df(rows)


def load_backtest_baseline(model: dict | None) -> dict[str, Any]:
  """Load Trade Model OOS report as backtest baseline."""
  empty = {
    "report": None,
    "overall": {},
    "monthly": pd.DataFrame(columns=["month", "n_trades", "win_rate_pct", "total_r", "avg_r", "cum_r"]),
    "trades_df": pd.DataFrame(),
    "equity": pd.DataFrame(columns=["entry", "equity_r", "drawdown_r"]),
    "conditions_fp": None,
  }
  if not model or not model.get("id"):
    return empty
  report = load_model_report(model["id"])
  params = get_model_run_params(model, model.get("id"))
  if not report:
    return {**empty, "conditions_fp": conditions_fingerprint(params)}
  trades_df = trades_json_to_df(report.get("trades") or [])
  monthly = monthly_oos_from_report(report)
  return {
    "report": report,
    "overall": report.get("overall_oos") or {},
    "monthly": monthly,
    "trades_df": trades_df,
    "equity": equity_series(trades_df),
    "conditions_fp": conditions_fingerprint(params),
  }


def load_live_auto_trades(
  model_id: str | None = None,
  *,
  bridge_dir=None,
  date_from=None,
  date_to=None,
) -> dict[str, Any]:
  """Closed Bridge auto trades, optionally filtered to model_id / date window."""
  raw = load_trades(bridge_dir)
  auto = filter_trades(
    raw, bridge_dir=bridge_dir, mode=MODE_AUTO,
    date_from=date_from, date_to=date_to,
  )
  if model_id:
    matched = [t for t in auto if (t.get("model_id") or model_id) == model_id]
    # Prefer model-matched; if none tagged yet, fall back to all auto
    trades = matched if matched else auto
  else:
    trades = auto
  closed = [t for t in trades if str(t.get("status") or "").upper() == "CLOSED"]
  trades_df = live_trades_to_analytics_df(closed)
  monthly = monthly_breakdown(trades_df)
  stats = compute_stats(
    trades, bridge_dir=bridge_dir, mode=MODE_AUTO,
    date_from=date_from, date_to=date_to,
  )
  return {
    "trades": closed,
    "trades_df": trades_df,
    "monthly": monthly,
    "stats": stats,
    "equity": equity_series(trades_df),
    "n_auto_all": len([t for t in auto if str(t.get("status") or "").upper() == "CLOSED"]),
    "filtered_by_model": bool(model_id) and any(t.get("model_id") == model_id for t in closed),
    "bridge_dir": str(bridge_dir) if bridge_dir else None,
  }


def align_monthly(
  bt_monthly: pd.DataFrame,
  live_monthly: pd.DataFrame,
) -> pd.DataFrame:
  """Join backtest vs live by calendar month; edge = live − bt."""
  cols = ["month", "bt_r", "live_r", "edge_r", "bt_n", "live_n"]
  if (bt_monthly is None or bt_monthly.empty) and (live_monthly is None or live_monthly.empty):
    return pd.DataFrame(columns=cols)

  bt = bt_monthly.copy() if bt_monthly is not None and not bt_monthly.empty else pd.DataFrame(columns=["month", "total_r", "n_trades"])
  lv = live_monthly.copy() if live_monthly is not None and not live_monthly.empty else pd.DataFrame(columns=["month", "total_r", "n_trades"])
  bt = bt.rename(columns={"total_r": "bt_r", "n_trades": "bt_n"})[["month", "bt_r", "bt_n"]]
  lv = lv.rename(columns={"total_r": "live_r", "n_trades": "live_n"})[["month", "live_r", "live_n"]]
  merged = pd.merge(bt, lv, on="month", how="outer").sort_values("month").reset_index(drop=True)
  merged["edge_r"] = (merged["live_r"] - merged["bt_r"]).round(3)
  return merged


def overlapping_months(aligned: pd.DataFrame) -> pd.DataFrame:
  if aligned is None or aligned.empty:
    return pd.DataFrame()
  return aligned.dropna(subset=["bt_r", "live_r"]).copy()


def build_bt_vs_live_monthly_figure(
  bt_monthly: pd.DataFrame,
  live_monthly: pd.DataFrame,
  *,
  title: str = "OOS theo tháng · Backtest vs Live",
  live_name: str = "Live Auto",
) -> go.Figure | None:
  months = sorted(set(
    list(bt_monthly["month"]) if bt_monthly is not None and not bt_monthly.empty else []
  ) | set(
    list(live_monthly["month"]) if live_monthly is not None and not live_monthly.empty else []
  ))
  if not months:
    return None

  bt_map = {}
  bt_cum = {}
  if bt_monthly is not None and not bt_monthly.empty:
    bt_map = dict(zip(bt_monthly["month"], bt_monthly["total_r"]))
    bt_cum = dict(zip(bt_monthly["month"], bt_monthly["cum_r"]))
  live_map = {}
  live_cum = {}
  if live_monthly is not None and not live_monthly.empty:
    live_map = dict(zip(live_monthly["month"], live_monthly["total_r"]))
    live_cum = dict(zip(live_monthly["month"], live_monthly["cum_r"]))

  fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    row_heights=[0.55, 0.45], vertical_spacing=0.12,
    subplot_titles=("R từng tháng", "R tích lũy"),
  )
  fig.add_trace(go.Bar(
    x=months, y=[bt_map.get(m) for m in months], name="Backtest OOS",
    marker_color="#2962ff", opacity=0.85,
  ), row=1, col=1)
  fig.add_trace(go.Bar(
    x=months, y=[live_map.get(m) for m in months], name=live_name,
    marker_color="#26a69a", opacity=0.85,
  ), row=1, col=1)


  # Cumulative only where series exists (don't invent zeros across gaps)
  if bt_cum:
    bx = [m for m in months if m in bt_cum]
    fig.add_trace(go.Scatter(
      x=bx, y=[bt_cum[m] for m in bx], name="Cum Backtest",
      line=dict(color="#2962ff", width=2.5),
    ), row=2, col=1)
  if live_cum:
    lx = [m for m in months if m in live_cum]
    fig.add_trace(go.Scatter(
      x=lx, y=[live_cum[m] for m in lx], name=f"Cum {live_name}",
      line=dict(color="#26a69a", width=2.5),
    ), row=2, col=1)

  fig.update_layout(
    title=dict(text=title, font=dict(size=13)),
    barmode="group",
    bargap=0.18,
    height=520,
    margin=dict(l=48, r=24, t=72, b=96),
    legend=dict(
      orientation="h", yanchor="top", y=-0.18, x=0,
      bgcolor="rgba(255,255,255,0.9)",
      bordercolor="rgba(0,0,0,0.08)", borderwidth=1,
      font=dict(size=11), tracegroupgap=24,
    ),
    hovermode="x unified",
  )
  fig.update_yaxes(title_text="R / tháng", row=1, col=1)
  fig.update_yaxes(title_text="Cum R", row=2, col=1)
  fig.update_xaxes(title_text="Tháng", row=2, col=1)
  return fig


def build_equity_overlay_figure(
  bt_equity: pd.DataFrame,
  live_equity: pd.DataFrame,
  *,
  title: str = "Equity R · Backtest vs Live",
  live_name: str = "Live Auto",
) -> go.Figure | None:
  if (bt_equity is None or bt_equity.empty) and (live_equity is None or live_equity.empty):
    return None
  fig = go.Figure()
  if bt_equity is not None and not bt_equity.empty:
    fig.add_trace(go.Scatter(
      x=bt_equity["entry"], y=bt_equity["equity_r"],
      name="Backtest OOS", line=dict(color="#2962ff", width=2),
    ))
    fig.add_trace(go.Scatter(
      x=bt_equity["entry"], y=-bt_equity["drawdown_r"],
      name="DD Backtest", line=dict(color="#90caf9", width=1, dash="dot"),
    ))
  if live_equity is not None and not live_equity.empty:
    fig.add_trace(go.Scatter(
      x=live_equity["entry"], y=live_equity["equity_r"],
      name=live_name, line=dict(color="#26a69a", width=2.5),
    ))
    fig.add_trace(go.Scatter(
      x=live_equity["entry"], y=-live_equity["drawdown_r"],
      name=f"DD {live_name}", line=dict(color="#80cbc4", width=1, dash="dot"),
    ))
  fig.update_layout(
    title=dict(text=title, font=dict(size=13)),
    height=400,
    margin=dict(l=40, r=20, t=48, b=80),
    legend=dict(orientation="h", yanchor="top", y=-0.2, x=0),
    hovermode="x unified",
    yaxis_title="R",
  )
  return fig


def build_monitor_bundle(
  model: dict | None,
  *,
  source: str = "live",
  date_from=None,
  date_to=None,
) -> dict[str, Any]:
  """
  Assemble Backtest vs Live/Sim bundle.
  source: "live" | "sim"
  """
  from mt5_bridge.protocol import BRIDGE_DIR, BRIDGE_SIM_DIR

  src = (source or "live").lower()
  bridge_dir = BRIDGE_SIM_DIR if src == "sim" else BRIDGE_DIR
  live_label = "Simulate EA" if src == "sim" else "Live Auto"

  bt = load_backtest_baseline(model)
  live = load_live_auto_trades(
    (model or {}).get("id"),
    bridge_dir=bridge_dir,
    date_from=date_from,
    date_to=date_to,
  )

  # When comparing sim window, also clip BT monthly to overlapping months only in edge metrics
  bt_monthly = bt["monthly"]
  if date_from is not None or date_to is not None:
    bt_df = bt["trades_df"]
    if bt_df is not None and not bt_df.empty and "entry" in bt_df.columns:
      mask = pd.Series(True, index=bt_df.index)
      if date_from is not None:
        mask &= bt_df["entry"] >= pd.Timestamp(date_from)
      if date_to is not None:
        mask &= bt_df["entry"] < (pd.Timestamp(date_to) + pd.Timedelta(days=1))
      clipped = bt_df.loc[mask]
      if not clipped.empty:
        from analytics import monthly_breakdown as _mb
        bt_monthly = _mb(clipped)

  aligned = align_monthly(bt_monthly, live["monthly"])
  overlap = overlapping_months(aligned)
  live_assess = assess_monthly_degradation(live["monthly"], baseline=None)

  overlap_edge = None
  overlap_live_r = None
  overlap_bt_r = None
  if not overlap.empty:
    overlap_live_r = round(float(overlap["live_r"].sum()), 3)
    overlap_bt_r = round(float(overlap["bt_r"].sum()), 3)
    overlap_edge = round(overlap_live_r - overlap_bt_r, 3)

  bt_overall = bt["overall"] or {}
  live_stats = live["stats"] or {}

  return {
    "model_label": format_model_label(model) if model else "—",
    "model_id": (model or {}).get("id"),
    "conditions_fp": bt.get("conditions_fp"),
    "has_report": bt["report"] is not None,
    "source": src,
    "live_label": live_label,
    "bt": {**bt, "monthly": bt_monthly},
    "live": live,
    "aligned": aligned,
    "overlap": overlap,
    "live_assess": live_assess,
    "overlap_live_r": overlap_live_r,
    "overlap_bt_r": overlap_bt_r,
    "overlap_edge": overlap_edge,
    "kpi": {
      "bt": {
        "n_trades": bt_overall.get("n_trades"),
        "win_rate_pct": bt_overall.get("win_rate_pct"),
        "total_r": bt_overall.get("total_r"),
        "avg_r": bt_overall.get("avg_rr") or bt_overall.get("avg_r"),
        "max_drawdown_r": bt_overall.get("max_drawdown_r"),
      },
      "live": {
        "n_trades": live_stats.get("n_trades"),
        "win_rate_pct": live_stats.get("win_rate_pct"),
        "total_r": live_stats.get("total_r"),
        "avg_r": live_stats.get("avg_r"),
        "max_drawdown_r": live_stats.get("max_drawdown_r"),
      },
    },
  }
