"""MT5 Bridge monitor — Backtest OOS vs Live auto trades (health + risk)."""
from __future__ import annotations

from typing import Any
from pathlib import Path

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
  from mt5_bridge.trade_journal import _compute_r

  rows = []
  for t in trades:
    if t.get("status") and str(t.get("status")).upper() != "CLOSED":
      continue
    r_val = t.get("r")
    if r_val is None:
      entry = t.get("entry_px")
      exit_px = t.get("exit_px")
      sl = t.get("sl_initial") if t.get("sl_initial") is not None else t.get("sl")
      direction = t.get("direction") or t.get("dir")
      if entry is not None and exit_px is not None and sl is not None:
        r_val = _compute_r(str(direction), float(entry), float(exit_px), float(sl))
      elif t.get("profit") is not None:
        try:
          r_val = float(t["profit"])  # HistoryFeed paper: profit often = R
        except (TypeError, ValueError):
          r_val = None
    if r_val is None:
      continue
    # Prefer historical entry (sim); wall-clock exit breaks monthly buckets
    entry = t.get("entry_time") or t.get("bar_time") or t.get("exit_time") or t.get("updated_at")
    if not entry:
      continue
    rows.append({
      "entry": entry,
      "exit": t.get("exit_time"),
      "r": float(r_val),
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
  use_exit_time: bool = True,
) -> dict[str, Any]:
  """Closed Bridge auto trades, optionally filtered to model_id / date window.

  use_exit_time=False → filter by entry_time (HistoryFeed / Simulate: exit may be
  wall-clock while entry is broker bar time).
  """
  from mt5_bridge.trade_journal import _compute_r

  raw = load_trades(bridge_dir)
  # Backfill missing R so health/risk charts can use sim fills
  for t in raw:
    if str(t.get("status") or "").upper() != "CLOSED":
      continue
    if t.get("r") is not None:
      continue
    entry = t.get("entry_px")
    exit_px = t.get("exit_px")
    sl = t.get("sl_initial") if t.get("sl_initial") is not None else t.get("sl")
    r_val = None
    if entry is not None and exit_px is not None and sl is not None:
      r_val = _compute_r(str(t.get("direction") or ""), float(entry), float(exit_px), float(sl))
    # HistoryFeed paper often stores R-multiple in profit when open fill was missed
    if r_val is None and t.get("profit") is not None:
      try:
        r_val = float(t["profit"])
      except (TypeError, ValueError):
        r_val = None
    if r_val is None:
      continue
    t["r"] = r_val
    if not t.get("result"):
      if r_val > 0.05:
        t["result"] = "WIN"
      elif r_val < -0.05:
        t["result"] = "LOSS"
      else:
        t["result"] = "BE"

  auto = filter_trades(
    raw, bridge_dir=bridge_dir, mode=MODE_AUTO,
    date_from=date_from, date_to=date_to,
    use_exit_time=use_exit_time,
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
    use_exit_time=use_exit_time,
  )
  # Recompute stats R from closed list (filter_trades path may still miss R fill)
  rs = [float(t["r"]) for t in closed if t.get("r") is not None]
  if rs:
    wins = sum(1 for t in closed if t.get("result") == "WIN")
    stats = {
      **stats,
      "n_trades": len(closed),
      "total_r": round(sum(rs), 3),
      "avg_r": round(sum(rs) / len(rs), 3),
      "win_rate_pct": round(100.0 * wins / len(closed), 1) if closed else None,
    }
    peak = eq = max_dd = 0.0
    for r in rs:
      eq += r
      peak = max(peak, eq)
      max_dd = min(max_dd, eq - peak)
    stats["max_drawdown_r"] = round(max_dd, 3)

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


_OOS_COLOR = "#2962ff"
_LIVE_COLOR = "#26a69a"
_OOS_DD_COLOR = "#7b1fa2"   # purple — clear vs blue equity + gold DD
_LIVE_DD_COLOR = "#f9a825"  # gold — clear vs teal equity + purple DD
OOS_SERIES_COLOR = _OOS_COLOR
LIVE_SERIES_COLOR = _LIVE_COLOR


def _month_range_label(months: list) -> str:
  ms = sorted({str(m) for m in months if m is not None and str(m)})
  if not ms:
    return "—"
  if len(ms) == 1:
    return ms[0]
  return f"{ms[0]} → {ms[-1]}"


def _add_timeline_annotations(
  fig: go.Figure,
  *,
  oos_months: list,
  live_months: list,
  live_name: str = "Live Auto",
  row: int | None = None,
  show_legend: bool = True,
) -> None:
  """Soft vrects + optional legend: cùng trục tháng, 2 chú thích thời gian màu OOS / Live."""
  oos_m = sorted({str(m) for m in (oos_months or []) if m is not None and str(m)})
  live_m = sorted({str(m) for m in (live_months or []) if m is not None and str(m)})
  trace_kw = {"row": row, "col": 1} if row else {}

  if show_legend and oos_m:
    fig.add_trace(go.Scatter(
      x=[None], y=[None], mode="lines",
      name=f"Timeline OOS · {_month_range_label(oos_m)}",
      line=dict(color=_OOS_COLOR, width=8),
      hoverinfo="skip",
      showlegend=True,
      legendgroup="timeline_oos",
    ), **trace_kw)
  if show_legend and live_m:
    fig.add_trace(go.Scatter(
      x=[None], y=[None], mode="lines",
      name=f"Timeline {live_name} · {_month_range_label(live_m)}",
      line=dict(color=_LIVE_COLOR, width=8),
      hoverinfo="skip",
      showlegend=True,
      legendgroup="timeline_live",
    ), **trace_kw)

  shape_kwargs: dict[str, Any] = dict(layer="below", line_width=0)
  if row is not None:
    shape_kwargs["row"] = row
    shape_kwargs["col"] = 1
  if oos_m:
    fig.add_vrect(
      x0=oos_m[0], x1=oos_m[-1],
      fillcolor="rgba(41,98,255,0.07)",
      **shape_kwargs,
    )
  if live_m:
    fig.add_vrect(
      x0=live_m[0], x1=live_m[-1],
      fillcolor="rgba(38,166,154,0.07)",
      **shape_kwargs,
    )


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
  oos_months: list = []
  if bt_monthly is not None and not bt_monthly.empty:
    bt_map = dict(zip(bt_monthly["month"], bt_monthly["total_r"]))
    bt_cum = dict(zip(bt_monthly["month"], bt_monthly["cum_r"]))
    oos_months = list(bt_monthly["month"])
  live_map = {}
  live_cum = {}
  live_months: list = []
  if live_monthly is not None and not live_monthly.empty:
    live_map = dict(zip(live_monthly["month"], live_monthly["total_r"]))
    live_cum = dict(zip(live_monthly["month"], live_monthly["cum_r"]))
    live_months = list(live_monthly["month"])

  fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    row_heights=[0.55, 0.45], vertical_spacing=0.12,
    subplot_titles=("R từng tháng", "R tích lũy"),
  )
  fig.add_trace(go.Bar(
    x=months, y=[bt_map.get(m) for m in months], name="Backtest OOS",
    marker_color=_OOS_COLOR, opacity=0.85,
    legendgroup="series_oos",
  ), row=1, col=1)
  fig.add_trace(go.Bar(
    x=months, y=[live_map.get(m) for m in months], name=live_name,
    marker_color=_LIVE_COLOR, opacity=0.85,
    legendgroup="series_live",
  ), row=1, col=1)

  # Cumulative only where series exists (don't invent zeros across gaps)
  if bt_cum:
    bx = [m for m in months if m in bt_cum]
    fig.add_trace(go.Scatter(
      x=bx, y=[bt_cum[m] for m in bx], name="Cum Backtest",
      line=dict(color=_OOS_COLOR, width=2.5),
      legendgroup="series_oos",
    ), row=2, col=1)
  if live_cum:
    lx = [m for m in months if m in live_cum]
    fig.add_trace(go.Scatter(
      x=lx, y=[live_cum[m] for m in lx], name=f"Cum {live_name}",
      line=dict(color=_LIVE_COLOR, width=2.5),
      legendgroup="series_live",
    ), row=2, col=1)

  _add_timeline_annotations(
    fig,
    oos_months=oos_months,
    live_months=live_months,
    live_name=live_name,
    row=1,
    show_legend=True,
  )
  _add_timeline_annotations(
    fig,
    oos_months=oos_months,
    live_months=live_months,
    live_name=live_name,
    row=2,
    show_legend=False,
  )

  fig.update_layout(
    title=dict(text=title, font=dict(size=13)),
    barmode="group",
    bargap=0.18,
    height=540,
    margin=dict(l=48, r=24, t=72, b=120),
    legend=dict(
      orientation="h", yanchor="top", y=-0.22, x=0,
      bgcolor="rgba(255,255,255,0.9)",
      bordercolor="rgba(0,0,0,0.08)", borderwidth=1,
      font=dict(size=11), tracegroupgap=16,
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
  oos_months: list = []
  live_months: list = []
  if bt_equity is not None and not bt_equity.empty:
    fig.add_trace(go.Scatter(
      x=bt_equity["entry"], y=bt_equity["equity_r"],
      name="Backtest OOS", line=dict(color=_OOS_COLOR, width=2),
      legendgroup="series_oos",
    ))
    fig.add_trace(go.Scatter(
      x=bt_equity["entry"], y=-bt_equity["drawdown_r"],
      name="DD Backtest", line=dict(color=_OOS_DD_COLOR, width=2, dash="dash"),
      legendgroup="series_oos",
    ))
    try:
      oos_months = list(
        pd.to_datetime(bt_equity["entry"], errors="coerce").dropna().dt.to_period("M").astype(str)
      )
    except Exception:
      oos_months = []
  if live_equity is not None and not live_equity.empty:
    fig.add_trace(go.Scatter(
      x=live_equity["entry"], y=live_equity["equity_r"],
      name=live_name, line=dict(color=_LIVE_COLOR, width=2.5),
      legendgroup="series_live",
    ))
    fig.add_trace(go.Scatter(
      x=live_equity["entry"], y=-live_equity["drawdown_r"],
      name=f"DD {live_name}", line=dict(color=_LIVE_DD_COLOR, width=2, dash="dot"),
      legendgroup="series_live",
    ))
    try:
      live_months = list(
        pd.to_datetime(live_equity["entry"], errors="coerce").dropna().dt.to_period("M").astype(str)
      )
    except Exception:
      live_months = []

  # Date-axis timeline bands (min→max entry) + legend swatches
  if oos_months:
    fig.add_trace(go.Scatter(
      x=[None], y=[None], mode="lines",
      name=f"Timeline OOS · {_month_range_label(oos_months)}",
      line=dict(color=_OOS_COLOR, width=8),
      hoverinfo="skip",
      legendgroup="timeline_oos",
    ))
  if live_months:
    fig.add_trace(go.Scatter(
      x=[None], y=[None], mode="lines",
      name=f"Timeline {live_name} · {_month_range_label(live_months)}",
      line=dict(color=_LIVE_COLOR, width=8),
      hoverinfo="skip",
      legendgroup="timeline_live",
    ))
  if bt_equity is not None and not bt_equity.empty:
    xs = pd.to_datetime(bt_equity["entry"], errors="coerce").dropna()
    if len(xs):
      fig.add_vrect(
        x0=xs.min(), x1=xs.max(),
        fillcolor="rgba(41,98,255,0.06)", layer="below", line_width=0,
      )
  if live_equity is not None and not live_equity.empty:
    xs = pd.to_datetime(live_equity["entry"], errors="coerce").dropna()
    if len(xs):
      fig.add_vrect(
        x0=xs.min(), x1=xs.max(),
        fillcolor="rgba(38,166,154,0.06)", layer="below", line_width=0,
      )

  fig.update_layout(
    title=dict(text=title, font=dict(size=13)),
    height=420,
    margin=dict(l=40, r=20, t=48, b=100),
    legend=dict(orientation="h", yanchor="top", y=-0.22, x=0),
    hovermode="x unified",
    yaxis_title="R",
  )
  return fig


def build_monthly_series_figure(
  monthly: pd.DataFrame,
  *,
  title: str,
  series_name: str,
  color: str | None = None,
) -> go.Figure | None:
  """Single-source monthly R chart (own time axis — no OOS/Live overlay)."""
  if monthly is None or monthly.empty:
    return None
  color = color or _OOS_COLOR
  months = list(monthly["month"])
  fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    row_heights=[0.55, 0.45], vertical_spacing=0.12,
    subplot_titles=("R từng tháng", "R tích lũy"),
  )
  fig.add_trace(go.Bar(
    x=months, y=list(monthly["total_r"]), name=series_name,
    marker_color=color, opacity=0.9,
  ), row=1, col=1)
  fig.add_trace(go.Scatter(
    x=months, y=list(monthly["cum_r"]), name=f"Cum {series_name}",
    line=dict(color=color, width=2.5),
  ), row=2, col=1)
  fig.update_layout(
    title=dict(text=title, font=dict(size=13)),
    height=480,
    margin=dict(l=48, r=24, t=64, b=48),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    hovermode="x unified",
  )
  fig.update_yaxes(title_text="R / tháng", row=1, col=1)
  fig.update_yaxes(title_text="Cum R", row=2, col=1)
  fig.update_xaxes(title_text="Tháng", row=2, col=1)
  return fig


def build_equity_series_figure(
  equity: pd.DataFrame,
  *,
  title: str,
  series_name: str,
  color: str | None = None,
) -> go.Figure | None:
  """Single-source equity / DD chart (own time axis)."""
  if equity is None or equity.empty:
    return None
  color = color or _OOS_COLOR
  dd_color = _OOS_DD_COLOR if color == _OOS_COLOR else _LIVE_DD_COLOR
  fig = go.Figure()
  fig.add_trace(go.Scatter(
    x=equity["entry"], y=equity["equity_r"],
    name=series_name, line=dict(color=color, width=2.5),
  ))
  fig.add_trace(go.Scatter(
    x=equity["entry"], y=-equity["drawdown_r"],
    name=f"DD {series_name}",
    line=dict(
      color=dd_color, width=2,
      dash="dash" if color == _OOS_COLOR else "dot",
    ),
  ))
  fig.update_layout(
    title=dict(text=title, font=dict(size=13)),
    height=380,
    margin=dict(l=40, r=20, t=48, b=48),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
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
  bridge_dir=None,
) -> dict[str, Any]:
  """
  Assemble Backtest vs Live/Sim bundle.
  source: "live" | "sim"
  bridge_dir: optional override (e.g. archived simulate_runs/<id>).
  """
  from mt5_bridge.protocol import BRIDGE_DIR, BRIDGE_SIM_DIR

  src = (source or "live").lower()
  if bridge_dir is not None:
    bridge_dir = Path(bridge_dir)
  else:
    bridge_dir = BRIDGE_SIM_DIR if src == "sim" else BRIDGE_DIR
  live_label = "Simulate EA" if src == "sim" else "Live Auto"

  bt = load_backtest_baseline(model)
  live = load_live_auto_trades(
    (model or {}).get("id"),
    bridge_dir=bridge_dir,
    date_from=date_from,
    date_to=date_to,
    # Simulate: filter by historical entry_time, not wall-clock exit_time
    use_exit_time=(src != "sim"),
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



def compare_live_week_to_oos(
  model: dict | None,
  *,
  week_start: str | None,
  strategy_name: str | None,
  conditions_fp: str | None = None,
) -> dict[str, Any]:
  """Compare Live decision week vs Health OOS weekly_log (no remine)."""
  params = get_model_run_params(model, (model or {}).get("id"))
  model_fp = conditions_fingerprint(params)
  out: dict[str, Any] = {
    "model_fp": model_fp,
    "live_fp": conditions_fp,
    "fp_match": (
      None if not conditions_fp else str(conditions_fp) == str(model_fp)
    ),
    "week_start": week_start,
    "live_strategy": strategy_name,
    "oos_strategy": None,
    "oos_r": None,
    "strategy_match": None,
    "status": "no_decision",
    "message": "Chưa có week_start / strategy trên decision — đợi Bridge decide.",
  }
  if not week_start:
    return out
  if not model or not model.get("id"):
    out["status"] = "no_model"
    out["message"] = "Chưa chọn Trade Model active."
    return out

  report = load_model_report(model["id"])
  if not report:
    out["status"] = "no_report"
    out["message"] = (
      "Chưa có report Health OOS — chạy Trade Models → Sức khỏe (KB ON) rồi đối chiếu."
    )
    return out

  week_key = str(week_start)[:10]
  hit = None
  for row in report.get("weekly_log") or []:
    if not isinstance(row, dict):
      continue
    if str(row.get("week_start") or "")[:10] == week_key:
      hit = row
      break

  if hit is None:
    out["status"] = "week_not_in_report"
    out["message"] = (
      f"Tuần `{week_key}` chưa có trong report Health "
      "(tuần mới hơn tip OOS, hoặc chưa refresh KB ON)."
    )
    return out

  oos_name = hit.get("strategy") or hit.get("strategy_name")
  out["oos_strategy"] = oos_name
  out["oos_r"] = hit.get("oos_r")
  if not strategy_name:
    out["status"] = "waiting_strategy"
    out["message"] = f"OOS tuần này: `{oos_name}` — Live chưa ghi strategy_name."
    return out

  match = str(strategy_name) == str(oos_name)
  out["strategy_match"] = match
  if match:
    out["status"] = "match"
    out["message"] = (
      f"MATCH · Live = OOS `{oos_name}`"
      + (f" · OOS R={out['oos_r']}" if out["oos_r"] is not None else "")
    )
  else:
    out["status"] = "mismatch"
    out["message"] = (
      f"LỆCH strategy · Live `{strategy_name}` ≠ OOS `{oos_name}`. "
      "Kiểm tra fp / Restart bridge service / refresh Health cùng search space."
    )
  return out


_COMPARE_PALETTE = (
  "#2962ff",
  "#26a69a",
  "#ef6c00",
  "#8e24aa",
  "#00897b",
  "#c62828",
  "#5d4037",
)


def build_multi_model_equity_figure(
  series_by_model: dict[str, pd.DataFrame],
  *,
  title: str = "Equity R · Compare Trade",
) -> go.Figure | None:
  """Overlay equity (+ optional DD) for many models on one chart."""
  items = [
    (name, eq) for name, eq in (series_by_model or {}).items()
    if eq is not None and not eq.empty and "equity_r" in eq.columns
  ]
  if not items:
    return None
  fig = go.Figure()
  for i, (name, eq) in enumerate(items):
    color = _COMPARE_PALETTE[i % len(_COMPARE_PALETTE)]
    fig.add_trace(go.Scatter(
      x=eq["entry"], y=eq["equity_r"],
      name=name,
      line=dict(color=color, width=2.2),
      legendgroup=f"m_{i}",
    ))
    if "drawdown_r" in eq.columns:
      fig.add_trace(go.Scatter(
        x=eq["entry"], y=-eq["drawdown_r"],
        name=f"DD {name}",
        line=dict(color=color, width=1.4, dash="dot"),
        legendgroup=f"m_{i}",
        opacity=0.75,
      ))
  fig.update_layout(
    title=dict(text=title, font=dict(size=13)),
    height=440,
    margin=dict(l=40, r=20, t=48, b=110),
    legend=dict(orientation="h", yanchor="top", y=-0.22, x=0),
    hovermode="x unified",
    yaxis_title="R",
  )
  return fig


def build_multi_model_monthly_figure(
  monthly_by_model: dict[str, pd.DataFrame],
  *,
  title: str = "R theo tháng · Compare Trade",
) -> go.Figure | None:
  """Grouped monthly total_r bars + multi-line cum R."""
  items = [
    (name, mo) for name, mo in (monthly_by_model or {}).items()
    if mo is not None and not mo.empty and "month" in mo.columns
  ]
  if not items:
    return None
  fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    row_heights=[0.55, 0.45], vertical_spacing=0.12,
    subplot_titles=("R từng tháng", "R tích lũy"),
  )
  for i, (name, mo) in enumerate(items):
    color = _COMPARE_PALETTE[i % len(_COMPARE_PALETTE)]
    months = list(mo["month"])
    totals = list(mo["total_r"]) if "total_r" in mo.columns else [0] * len(months)
    if "cum_r" in mo.columns:
      cum = list(mo["cum_r"])
    else:
      running = 0.0
      cum = []
      for v in totals:
        running += float(v or 0)
        cum.append(running)
    fig.add_trace(go.Bar(
      x=months, y=totals, name=name,
      marker_color=color, opacity=0.85,
      legendgroup=f"m_{i}",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
      x=months, y=cum, name=f"Cum {name}",
      line=dict(color=color, width=2),
      legendgroup=f"m_{i}",
      showlegend=False,
    ), row=2, col=1)
  fig.update_layout(
    title=dict(text=title, font=dict(size=13)),
    barmode="group",
    bargap=0.18,
    height=520,
    margin=dict(l=48, r=24, t=72, b=80),
    legend=dict(orientation="h", yanchor="top", y=-0.12, x=0),
    hovermode="x unified",
  )
  fig.update_yaxes(title_text="R / tháng", row=1, col=1)
  fig.update_yaxes(title_text="Cum R", row=2, col=1)
  return fig


def _parse_compare_trade_time(value) -> pd.Timestamp | None:
  if value is None or value == "":
    return None
  try:
    raw = str(value).strip().replace("-", ".")
    ts = pd.to_datetime(raw, format="%Y.%m.%d %H:%M:%S", errors="coerce")
    if pd.isna(ts):
      ts = pd.to_datetime(raw[:16], format="%Y.%m.%d %H:%M", errors="coerce")
    if pd.isna(ts):
      ts = pd.to_datetime(str(value), errors="coerce")
    if pd.isna(ts):
      return None
    if getattr(ts, "tzinfo", None) is not None:
      ts = ts.tz_convert(None)
    return pd.Timestamp(ts)
  except Exception:
    return None


def load_compare_ohlc(
  date_from: str | None,
  date_to: str | None,
  *,
  max_bars: int = 8000,
) -> pd.DataFrame:
  """Broker-time OHLC window from MT5 cache for Compare Trade price chart."""
  from mt5_bridge.history_sync import load_mt5_cache, utc_to_broker_time

  cache = load_mt5_cache()
  if cache is None or cache.empty:
    return pd.DataFrame()
  frame = cache.copy()
  if not isinstance(frame.index, pd.DatetimeIndex):
    return pd.DataFrame()
  frame.index = pd.DatetimeIndex([utc_to_broker_time(ts) for ts in frame.index])
  frame = frame[~frame.index.duplicated(keep="last")].sort_index()
  # Normalize Open/High/Low/Close
  colmap = {}
  for c in frame.columns:
    key = str(c).lower()
    if key == "open":
      colmap[c] = "Open"
    elif key == "high":
      colmap[c] = "High"
    elif key == "low":
      colmap[c] = "Low"
    elif key == "close":
      colmap[c] = "Close"
    elif key in ("volume", "tick_volume"):
      colmap[c] = "Volume"
  if colmap:
    frame = frame.rename(columns=colmap)
  need = {"Open", "High", "Low", "Close"}
  if not need.issubset(frame.columns):
    return pd.DataFrame()

  t0 = _parse_compare_trade_time(str(date_from)[:10] + " 00:00") if date_from else None
  t1 = _parse_compare_trade_time(str(date_to)[:10] + " 23:59") if date_to else None
  if t0 is not None:
    frame = frame.loc[frame.index >= t0]
  if t1 is not None:
    frame = frame.loc[frame.index <= t1]
  if frame.empty:
    return frame
  if len(frame) > max_bars:
    frame = frame.tail(max_bars)
  if "Volume" not in frame.columns:
    frame["Volume"] = 0
  return frame[["Open", "High", "Low", "Close", "Volume"]]


def build_multi_model_price_figure(
  ohlc: pd.DataFrame,
  trades_by_model: dict[str, list[dict]],
  *,
  title: str = "Giá M15 · lệnh theo model",
  show_connectors: bool = True,
) -> go.Figure | None:
  """Candlestick + per-model entry/exit markers (color-coded) for Compare Trade."""
  if ohlc is None or ohlc.empty:
    return None
  need = {"Open", "High", "Low", "Close"}
  if not need.issubset(ohlc.columns):
    return None

  fig = go.Figure()
  fig.add_trace(go.Candlestick(
    x=ohlc.index,
    open=ohlc["Open"], high=ohlc["High"],
    low=ohlc["Low"], close=ohlc["Close"],
    increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
    increasing_fillcolor="#26a69a", decreasing_fillcolor="#ef5350",
    name="BTCUSD",
    showlegend=False,
  ))

  chart_start, chart_end = ohlc.index[0], ohlc.index[-1]
  items = list((trades_by_model or {}).items())
  any_trade = False

  for i, (label, trades) in enumerate(items):
    color = _COMPARE_PALETTE[i % len(_COMPARE_PALETTE)]
    legend_shown = False
    for trade in trades or []:
      status = str(trade.get("status") or "").upper()
      if status not in ("OPEN", "CLOSED"):
        continue
      entry_t = _parse_compare_trade_time(
        trade.get("entry_time") or trade.get("bar_time") or trade.get("entry")
      )
      entry_px = trade.get("entry_px") if trade.get("entry_px") is not None else trade.get("entry")
      if entry_t is None or entry_px is None:
        continue
      try:
        entry_px = float(entry_px)
      except (TypeError, ValueError):
        continue
      if entry_t < chart_start or entry_t > chart_end:
        continue

      direction = str(trade.get("direction") or trade.get("dir") or "").upper()
      is_long = direction in ("BUY", "LONG")
      symbol = "triangle-up" if is_long else "triangle-down"
      r_val = trade.get("r")
      reason = trade.get("reason") or ""
      hover = (
        f"<b>{label}</b><br>{direction} entry<br>"
        f"%{{x}} @ %{{y:.5f}}<br>"
        f"R={r_val if r_val is not None else '—'} · {reason}<extra></extra>"
      )
      fig.add_trace(go.Scatter(
        x=[entry_t], y=[entry_px],
        mode="markers",
        marker=dict(
          symbol=symbol, size=11, color=color,
          line=dict(width=1, color="white"),
        ),
        name=label,
        legendgroup=f"m_{i}",
        showlegend=not legend_shown,
        hovertemplate=hover,
      ))
      legend_shown = True
      any_trade = True

      exit_t = _parse_compare_trade_time(trade.get("exit_time") or trade.get("exit"))
      exit_px = trade.get("exit_px")
      if status == "CLOSED" and exit_t is not None and exit_px is not None:
        try:
          exit_px = float(exit_px)
        except (TypeError, ValueError):
          continue
        if chart_start <= exit_t <= chart_end:
          win = (float(r_val) > 0) if r_val is not None else False
          fig.add_trace(go.Scatter(
            x=[exit_t], y=[exit_px],
            mode="markers",
            marker=dict(
              symbol="x", size=9,
              color="#089981" if win else "#f23645",
              line=dict(width=2, color=color),
            ),
            name=f"{label} exit",
            legendgroup=f"m_{i}",
            showlegend=False,
            hovertemplate=(
              f"<b>{label}</b> exit<br>%{{x}} @ %{{y:.5f}}<br>"
              f"R={r_val if r_val is not None else '—'} · {reason}<extra></extra>"
            ),
          ))
          if show_connectors:
            fig.add_trace(go.Scatter(
              x=[entry_t, exit_t], y=[entry_px, exit_px],
              mode="lines",
              line=dict(color=color, width=1.2, dash="dot"),
              opacity=0.55,
              legendgroup=f"m_{i}",
              showlegend=False,
              hoverinfo="skip",
            ))
      elif status == "OPEN":
        fig.add_trace(go.Scatter(
          x=[entry_t], y=[entry_px],
          mode="markers",
          marker=dict(symbol="circle-open", size=14, color=color, line=dict(width=2)),
          legendgroup=f"m_{i}",
          showlegend=False,
          hovertemplate=f"<b>{label}</b> OPEN<br>%{{x}} @ %{{y:.5f}}<extra></extra>",
        ))

  fig.update_layout(
    title=dict(text=title, font=dict(size=13)),
    height=560,
    margin=dict(l=40, r=20, t=48, b=100),
    legend=dict(orientation="h", yanchor="top", y=-0.18, x=0),
    xaxis_rangeslider_visible=False,
    hovermode="closest",
    yaxis_title="Price",
  )
  if not any_trade:
    fig.update_layout(
      annotations=[dict(
        text="Chưa có lệnh trong cửa sổ giá",
        xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False, font=dict(size=13, color="#888"),
      )]
    )
  return fig
