"""Mining-space freshness — active preset vs baseline miner on same KB/OOS."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from gui.model_health import monthly_oos_from_report


def _oos_metrics(report: dict | None) -> dict[str, float | None]:
  oos = (report or {}).get("overall_oos") or {}
  out: dict[str, float | None] = {}
  for key in (
    "win_rate_pct", "avg_rr", "total_r", "max_drawdown_r",
    "profit_factor", "trades_per_week", "n_trades",
  ):
    raw = oos.get(key)
    out[key] = None if raw is None else float(raw)
  return out


def _half_sum(monthly: pd.DataFrame, *, late: bool) -> float | None:
  if monthly is None or monthly.empty or "total_r" not in monthly.columns:
    return None
  m = monthly.sort_values("month").reset_index(drop=True)
  n = len(m)
  if n < 2:
    return float(m["total_r"].sum()) if n == 1 else None
  mid = max(1, n // 2)
  chunk = m.iloc[mid:] if late else m.iloc[:mid]
  return float(chunk["total_r"].sum())


def _tail_sum(monthly: pd.DataFrame, n_months: int = 3) -> float | None:
  if monthly is None or monthly.empty or "total_r" not in monthly.columns:
    return None
  m = monthly.sort_values("month")
  return float(m.tail(n_months)["total_r"].sum())


def assess_mining_space_freshness(
  active_report: dict | None,
  baseline_report: dict | None,
  *,
  preset_name: str | None = None,
  recent_months: int = 3,
) -> dict[str, Any]:
  """
  Compare active mining space vs baseline miner (same KB/train/OOS).

  Space is \"stale\" when the active preset loses its edge vs baseline on the
  recent / late OOS window — not merely when absolute R falls (market-wide).
  """
  empty = {
    "verdict": "insufficient",
    "message": "Chưa đủ dữ liệu so sánh mining space (cần report active + baseline).",
    "preset_name": preset_name,
    "n_months": 0,
    "active": {},
    "baseline": {},
    "delta": {},
    "early_edge_r": None,
    "late_edge_r": None,
    "edge_delta": None,
    "recent_edge_r": None,
  }
  if not active_report or not baseline_report:
    return empty

  active_m = monthly_oos_from_report(active_report)
  base_m = monthly_oos_from_report(baseline_report)
  if active_m.empty or base_m.empty:
    return {
      **empty,
      "message": "Không gom được chuỗi theo tháng từ report active/baseline.",
    }

  active = _oos_metrics(active_report)
  baseline = _oos_metrics(baseline_report)
  delta = {
    key: (
      None if active.get(key) is None or baseline.get(key) is None
      else round(float(active[key]) - float(baseline[key]), 4)
    )
    for key in active
  }

  # Align months for edge series.
  on = active_m.set_index("month")["total_r"]
  off = base_m.set_index("month")["total_r"]
  shared = sorted(set(on.index) & set(off.index))
  n = len(shared)
  if n < 2:
    return {
      **empty,
      "n_months": n,
      "active": active,
      "baseline": baseline,
      "delta": delta,
      "message": "Cần ≥2 tháng OOS chung để đánh giá mining space.",
    }

  edge = pd.Series({m: float(on[m] - off[m]) for m in shared}).sort_index()
  mid = max(1, n // 2)
  early_edge = round(float(edge.iloc[:mid].sum()), 3)
  late_edge = round(float(edge.iloc[mid:].sum()), 3)
  edge_delta = round(late_edge - early_edge, 3)
  recent_n = min(recent_months, n)
  recent_edge = round(float(edge.iloc[-recent_n:].sum()), 3)

  wr_d = delta.get("win_rate_pct")
  rr_d = delta.get("avg_rr")
  r_d = delta.get("total_r")
  label = preset_name or "active"

  quality_lost = (
    wr_d is not None and rr_d is not None and wr_d < 0 and rr_d < 0
  )
  late_bad = late_edge <= -5.0
  late_soft = late_edge <= -2.0
  recent_bad = recent_edge <= -4.0
  recent_soft = recent_edge <= -1.5
  edge_worsening = edge_delta <= -3.0

  if late_bad or recent_bad or quality_lost:
    verdict = "stale"
    bits = []
    if quality_lost:
      bits.append(
        f"WR {wr_d:+.1f}pp và RR {rr_d:+.2f} đều thua baseline "
        "(mất lợi thế chất lượng của preset)"
      )
    if late_bad:
      bits.append(f"edge nửa sau {late_edge:+.1f}R (active − baseline)")
    if recent_bad:
      bits.append(f"edge {recent_n} tháng gần {recent_edge:+.1f}R")
    msg = (
      f"Mining space **có dấu hiệu lỗi thời** (`{label}`): "
      + "; ".join(bits)
      + ". Cân nhắc audit preset / Grid lại / đổi Trade Model."
    )
  elif late_soft or recent_soft or edge_worsening:
    verdict = "watch"
    msg = (
      f"Theo dõi mining space (`{label}`): "
      f"edge nửa sau {late_edge:+.1f}R · {recent_n} tháng gần {recent_edge:+.1f}R "
      f"· Δ edge (sau−đầu) {edge_delta:+.1f}R"
    )
    if wr_d is not None:
      msg += f" · ΔWR {wr_d:+.1f}pp"
    if r_d is not None:
      msg += f" · ΔR full {r_d:+.1f}"
    msg += ". Chưa kết luận lỗi thời — chạy lại sau thêm tháng OOS."
  else:
    verdict = "fresh"
    msg = (
      f"Mining space vẫn giữ lợi thế vs baseline (`{label}`): "
      f"edge nửa sau {late_edge:+.1f}R · {recent_n} tháng gần {recent_edge:+.1f}R"
    )
    if wr_d is not None:
      msg += f" · ΔWR {wr_d:+.1f}pp"
    if rr_d is not None:
      msg += f" · ΔRR {rr_d:+.2f}"
    msg += "."

  return {
    "verdict": verdict,
    "message": msg,
    "preset_name": preset_name,
    "n_months": n,
    "shared_months": shared,
    "active": active,
    "baseline": baseline,
    "delta": delta,
    "early_edge_r": early_edge,
    "late_edge_r": late_edge,
    "edge_delta": edge_delta,
    "recent_edge_r": recent_edge,
    "recent_months": recent_n,
    "active_early_r": _half_sum(active_m, late=False),
    "active_late_r": _half_sum(active_m, late=True),
    "baseline_early_r": _half_sum(base_m, late=False),
    "baseline_late_r": _half_sum(base_m, late=True),
    "active_recent_r": _tail_sum(active_m, recent_n),
    "baseline_recent_r": _tail_sum(base_m, recent_n),
  }


def build_monthly_space_compare_figure(
  active_monthly: pd.DataFrame,
  baseline_monthly: pd.DataFrame | None = None,
  *,
  title: str = "OOS theo tháng · Active space vs Baseline miner",
  active_name: str = "Active space",
  baseline_name: str = "Baseline miner",
) -> go.Figure | None:
  if active_monthly is None or active_monthly.empty:
    return None

  on = active_monthly.sort_values("month").copy()
  months = list(on["month"])
  fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    row_heights=[0.55, 0.45], vertical_spacing=0.12,
    subplot_titles=("R từng tháng", "Edge tích lũy (active − baseline)"),
  )

  fig.add_trace(go.Bar(
    x=months, y=on["total_r"], name=active_name,
    marker_color="#5c6bc0", opacity=0.85,
  ), row=1, col=1)

  if baseline_monthly is not None and not baseline_monthly.empty:
    base = baseline_monthly.sort_values("month")
    base_map = dict(zip(base["month"], base["total_r"]))
    base_y = [base_map.get(m) for m in months]
    fig.add_trace(go.Bar(
      x=months, y=base_y, name=baseline_name,
      marker_color="#90a4ae", opacity=0.75,
    ), row=1, col=1)

    edge_months = []
    edge_vals = []
    cum = 0.0
    cum_y = []
    for m, ar in zip(months, on["total_r"]):
      br = base_map.get(m)
      if br is None:
        continue
      e = float(ar) - float(br)
      cum += e
      edge_months.append(m)
      edge_vals.append(e)
      cum_y.append(cum)
    if edge_months:
      fig.add_trace(go.Bar(
        x=edge_months, y=edge_vals, name="Edge tháng",
        marker_color="#26a69a", opacity=0.55, showlegend=False,
      ), row=2, col=1)
      fig.add_trace(go.Scatter(
        x=edge_months, y=cum_y, name="Cum edge",
        line=dict(color="#ef6c00", width=2.5),
      ), row=2, col=1)
      fig.add_hline(y=0, line_width=1, line_dash="dot", line_color="#78909c", row=2, col=1)

  fig.update_layout(
    title=dict(text=title, font=dict(size=13), y=0.98, yanchor="top"),
    barmode="group",
    bargap=0.18,
    bargroupgap=0.08,
    height=560,
    margin=dict(l=48, r=24, t=72, b=96),
    legend=dict(
      orientation="h",
      yanchor="top",
      y=-0.18,
      x=0,
      xanchor="left",
      bgcolor="rgba(255,255,255,0.9)",
      bordercolor="rgba(0,0,0,0.08)",
      borderwidth=1,
      font=dict(size=11),
    ),
    hovermode="x unified",
    plot_bgcolor="rgba(248,249,250,1)",
  )
  fig.update_yaxes(title_text="R", row=1, col=1)
  fig.update_yaxes(title_text="Edge R", row=2, col=1)
  return fig
