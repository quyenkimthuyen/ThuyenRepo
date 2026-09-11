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


def _half_wr_edge(
  active_m: pd.DataFrame,
  base_m: pd.DataFrame,
  shared: list,
  *,
  late: bool,
) -> float | None:
  """Mean (active − baseline) WR pp on early/late half of shared months."""
  if "win_rate_pct" not in active_m.columns or "win_rate_pct" not in base_m.columns:
    return None
  on = active_m.set_index("month")["win_rate_pct"]
  off = base_m.set_index("month")["win_rate_pct"]
  mid = max(1, len(shared) // 2)
  chunk = shared[mid:] if late else shared[:mid]
  diffs = []
  for m in chunk:
    a, b = on.get(m), off.get(m)
    if a is None or b is None or pd.isna(a) or pd.isna(b):
      continue
    diffs.append(float(a) - float(b))
  if not diffs:
    return None
  return round(sum(diffs) / len(diffs), 2)


def _tail_wr_edge(
  active_m: pd.DataFrame,
  base_m: pd.DataFrame,
  shared: list,
  n_months: int,
) -> float | None:
  if "win_rate_pct" not in active_m.columns or "win_rate_pct" not in base_m.columns:
    return None
  on = active_m.set_index("month")["win_rate_pct"]
  off = base_m.set_index("month")["win_rate_pct"]
  chunk = shared[-n_months:]
  diffs = []
  for m in chunk:
    a, b = on.get(m), off.get(m)
    if a is None or b is None or pd.isna(a) or pd.isna(b):
      continue
    diffs.append(float(a) - float(b))
  if not diffs:
    return None
  return round(sum(diffs) / len(diffs), 2)


def assess_mining_space_freshness(
  active_report: dict | None,
  baseline_report: dict | None,
  *,
  preset_name: str | None = None,
  recent_months: int = 3,
) -> dict[str, Any]:
  """
  Compare active mining space vs baseline miner (same KB/train/OOS).

  Verdict uses **both** Win rate (primary for WR-oriented presets) and Total R:
  - R kém nhưng WR vẫn hơn baseline → ``watch`` (không kết luận lỗi thời chỉ vì R)
  - WR thua rõ / WR+RR đều thua → ``stale``
  - R kém và WR không giữ lợi thế → ``stale``
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
    "late_edge_wr_pp": None,
    "recent_edge_wr_pp": None,
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
  late_wr = _half_wr_edge(active_m, base_m, shared, late=True)
  recent_wr = _tail_wr_edge(active_m, base_m, shared, recent_n)

  wr_d = delta.get("win_rate_pct")
  rr_d = delta.get("avg_rr")
  r_d = delta.get("total_r")
  label = preset_name or "active"

  quality_lost = (
    wr_d is not None and rr_d is not None and wr_d < 0 and rr_d < 0
  )
  wr_lost = wr_d is not None and wr_d <= -2.0
  wr_beats = wr_d is not None and wr_d >= 1.0
  wr_soft = wr_d is not None and wr_d < 0
  late_bad = late_edge <= -5.0
  late_soft = late_edge <= -2.0
  recent_bad = recent_edge <= -4.0
  recent_soft = recent_edge <= -1.5
  edge_worsening = edge_delta <= -3.0
  r_bad = late_bad or recent_bad
  r_soft = late_soft or recent_soft or edge_worsening

  def _fmt_quality() -> str:
    bits = []
    if wr_d is not None:
      bits.append(f"ΔWR {wr_d:+.1f}pp")
    if rr_d is not None:
      bits.append(f"ΔRR {rr_d:+.2f}")
    if r_d is not None:
      bits.append(f"ΔR full {r_d:+.1f}")
    return " · ".join(bits) if bits else "—"

  def _fmt_r_edges() -> str:
    bits = [
      f"edge R nửa sau {late_edge:+.1f}",
      f"edge R {recent_n} tháng gần {recent_edge:+.1f}",
    ]
    if late_wr is not None:
      bits.append(f"edge WR nửa sau {late_wr:+.1f}pp")
    if recent_wr is not None:
      bits.append(f"edge WR {recent_n} tháng {recent_wr:+.1f}pp")
    return " · ".join(bits)

  # --- Verdict: WR primary for quality presets; R alone cannot force stale ---
  if quality_lost or (wr_lost and r_bad):
    verdict = "stale"
    bits = []
    if quality_lost:
      bits.append(
        f"WR {wr_d:+.1f}pp và RR {rr_d:+.2f} đều thua baseline "
        "(mất lợi thế chất lượng)"
      )
    elif wr_lost:
      bits.append(f"WR thua baseline {wr_d:+.1f}pp")
    if late_bad:
      bits.append(f"edge R nửa sau {late_edge:+.1f}")
    if recent_bad:
      bits.append(f"edge R {recent_n} tháng gần {recent_edge:+.1f}")
    msg = (
      f"Mining space **có dấu hiệu lỗi thời** (`{label}`): "
      + "; ".join(bits)
      + f". [{_fmt_quality()}]. "
      "Cân nhắc audit preset / Grid lại / đổi Trade Model."
    )
  elif r_bad and wr_beats:
    # PnL thua nhưng WR vẫn hơn — không kết luận stale chỉ vì Total R
    verdict = "watch"
    msg = (
      f"Theo dõi mining space (`{label}`): Total R kém baseline "
      f"({_fmt_r_edges()}) nhưng **WR vẫn hơn** ({_fmt_quality()}). "
      "Theo mục tiêu WR của preset — chưa kết luận lỗi thời; "
      "theo dõi thêm PnL / chạy lại sau thêm tháng OOS."
    )
  elif wr_lost:
    verdict = "stale"
    msg = (
      f"Mining space **có dấu hiệu lỗi thời** (`{label}`): "
      f"WR thua baseline rõ ({_fmt_quality()}). "
      f"{_fmt_r_edges()}. "
      "Cân nhắc audit preset / Grid lại / đổi Trade Model."
    )
  elif r_bad:
    # R kém, WR không giữ lợi thế (flat/unknown/slightly down)
    verdict = "stale"
    wr_note = (
      f"WR không giữ lợi thế ({_fmt_quality()})"
      if wr_d is not None
      else "chưa có ΔWR để đối chiếu"
    )
    msg = (
      f"Mining space **có dấu hiệu lỗi thời** (`{label}`): "
      f"{_fmt_r_edges()}; {wr_note}. "
      "Cân nhắc audit preset / Grid lại / đổi Trade Model."
    )
  elif wr_soft and r_soft:
    verdict = "watch"
    msg = (
      f"Theo dõi mining space (`{label}`): {_fmt_r_edges()} · {_fmt_quality()}. "
      "Chưa kết luận lỗi thời — chạy lại sau thêm tháng OOS."
    )
  elif r_soft or wr_soft or edge_worsening:
    verdict = "watch"
    msg = (
      f"Theo dõi mining space (`{label}`): {_fmt_r_edges()} · {_fmt_quality()}. "
      "Chưa kết luận lỗi thời — chạy lại sau thêm tháng OOS."
    )
  else:
    verdict = "fresh"
    msg = (
      f"Mining space vẫn giữ lợi thế vs baseline (`{label}`): "
      f"{_fmt_r_edges()} · {_fmt_quality()}."
    )

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
    "late_edge_wr_pp": late_wr,
    "recent_edge_wr_pp": recent_wr,
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
  """Dual view: Total R (bars) + Win rate % (lines) — same months."""
  if active_monthly is None or active_monthly.empty:
    return None

  on = active_monthly.sort_values("month").copy()
  months = list(on["month"])
  has_wr = "win_rate_pct" in on.columns and on["win_rate_pct"].notna().any()

  fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    row_heights=[0.50, 0.50], vertical_spacing=0.14,
    subplot_titles=("Total R theo tháng", "Win rate % theo tháng"),
  )

  fig.add_trace(go.Bar(
    x=months, y=on["total_r"], name=f"{active_name} · R",
    marker_color="#5c6bc0", opacity=0.85,
    legendgroup="active",
  ), row=1, col=1)

  base = None
  base_r_map: dict = {}
  base_wr_map: dict = {}
  if baseline_monthly is not None and not baseline_monthly.empty:
    base = baseline_monthly.sort_values("month")
    base_r_map = dict(zip(base["month"], base["total_r"]))
    if "win_rate_pct" in base.columns:
      base_wr_map = {
        m: w for m, w in zip(base["month"], base["win_rate_pct"])
        if w is not None and pd.notna(w)
      }
    fig.add_trace(go.Bar(
      x=months, y=[base_r_map.get(m) for m in months],
      name=f"{baseline_name} · R",
      marker_color="#90a4ae", opacity=0.75,
      legendgroup="baseline",
    ), row=1, col=1)

  # WR lines (skip months with no WR)
  if has_wr:
    on_wr = [
      float(w) if w is not None and pd.notna(w) else None
      for w in on["win_rate_pct"]
    ]
    fig.add_trace(go.Scatter(
      x=months, y=on_wr, name=f"{active_name} · WR",
      mode="lines+markers",
      line=dict(color="#2962ff", width=2.5),
      marker=dict(size=7),
      legendgroup="active",
    ), row=2, col=1)
    if base_wr_map:
      fig.add_trace(go.Scatter(
        x=months,
        y=[base_wr_map.get(m) for m in months],
        name=f"{baseline_name} · WR",
        mode="lines+markers",
        line=dict(color="#ef6c00", width=2.5, dash="dot"),
        marker=dict(size=7),
        legendgroup="baseline",
      ), row=2, col=1)

  fig.update_layout(
    title=dict(text=title, font=dict(size=13), y=0.98, yanchor="top"),
    barmode="group",
    bargap=0.18,
    bargroupgap=0.08,
    height=620,
    margin=dict(l=48, r=24, t=72, b=100),
    legend=dict(
      orientation="h",
      yanchor="top",
      y=-0.16,
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
  fig.update_yaxes(title_text="WR %", row=2, col=1)
  fig.update_xaxes(title_text="Tháng", row=2, col=1)
  fig.update_annotations(font_size=12)
  return fig
