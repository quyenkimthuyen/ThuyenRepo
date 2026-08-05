"""Trade Model health — monthly OOS KB ON vs OFF + degradation signals."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analytics import monthly_breakdown, monthly_from_weekly_log, trades_json_to_df


def monthly_oos_from_report(report: dict | None) -> pd.DataFrame:
  if not report:
    return pd.DataFrame(columns=["month", "n_trades", "win_rate_pct", "total_r", "avg_r", "cum_r"])
  trades_df = trades_json_to_df(report.get("trades") or [])
  monthly = monthly_breakdown(trades_df)
  if not monthly.empty:
    return monthly
  return monthly_from_weekly_log(report.get("weekly_log") or [])


def assess_monthly_degradation(
  monthly: pd.DataFrame,
  *,
  baseline: pd.DataFrame | None = None,
) -> dict[str, Any]:
  """
  Compare early vs late half of OOS months.
  If baseline (KB OFF) given, also track ON−OFF edge over time.
  """
  empty = {
    "n_months": 0,
    "early_r": None,
    "late_r": None,
    "delta_r": None,
    "verdict": "insufficient",
    "message": "Chưa đủ tháng OOS để đánh giá.",
    "edge_early": None,
    "edge_late": None,
    "edge_delta": None,
  }
  if monthly is None or monthly.empty or "total_r" not in monthly.columns:
    return empty

  m = monthly.sort_values("month").reset_index(drop=True)
  n = len(m)
  if n < 2:
    return {
      **empty,
      "n_months": n,
      "message": "Cần ≥2 tháng OOS để so nửa đầu / nửa cuối.",
    }

  mid = max(1, n // 2)
  early = m.iloc[:mid]
  late = m.iloc[mid:]
  early_r = float(early["total_r"].sum())
  late_r = float(late["total_r"].sum())
  delta = round(late_r - early_r, 3)

  edge_early = edge_late = edge_delta = None
  if baseline is not None and not baseline.empty:
    b = baseline.set_index("month")["total_r"]
    on = m.set_index("month")["total_r"]
    shared = sorted(set(on.index) & set(b.index))
    if len(shared) >= 2:
      smid = max(1, len(shared) // 2)
      early_m, late_m = shared[:smid], shared[smid:]
      edge_early = round(float((on[early_m] - b[early_m]).sum()), 3)
      edge_late = round(float((on[late_m] - b[late_m]).sum()), 3)
      edge_delta = round(edge_late - edge_early, 3)

  # Heuristic thresholds (R over half-window).
  # Absolute R and KB edge are independent signals — edge can degrade while
  # late-half R is still higher (e.g. market easy for both ON and OFF).
  r_bad = delta <= -8
  r_soft = delta <= -3
  edge_bad = edge_delta is not None and edge_delta <= -5
  edge_soft = edge_delta is not None and edge_delta <= -2

  def _r_half() -> str:
    return f"nửa sau {late_r:+.1f}R vs nửa đầu {early_r:+.1f}R (Δ {delta:+.1f}R)"

  def _edge_half() -> str:
    return (
      f"lợi thế KB ON−OFF nửa sau {edge_late:+.1f}R "
      f"vs nửa đầu {edge_early:+.1f}R (Δ edge {edge_delta:+.1f}R)"
    )

  if r_bad or edge_bad:
    verdict = "degraded"
    if edge_bad and not r_bad:
      msg = (
        f"Dấu hiệu suy giảm lợi thế KB: {_edge_half()}. "
        f"Tổng R vẫn ổn ({_r_half()}) — OFF bắt kịp / ON kém nổi hơn."
      )
    elif r_bad and edge_bad:
      msg = f"Dấu hiệu suy giảm: {_r_half()}; {_edge_half()}."
    else:
      msg = f"Dấu hiệu suy giảm tổng R: {_r_half()}."
      if edge_delta is not None:
        msg += f" {_edge_half().capitalize()}."
  elif r_soft or edge_soft:
    verdict = "watch"
    if edge_soft and not r_soft:
      msg = (
        f"Theo dõi lợi thế KB: {_edge_half()}. "
        f"Tổng R: {_r_half()}."
      )
    else:
      msg = (
        f"Theo dõi: nửa sau yếu hơn nửa đầu (Δ {delta:+.1f}R). "
        "Nên so KB ON/OFF và Paper Auto gần đây."
      )
  elif late_r < 0 and early_r > 0:
    verdict, msg = "watch", (
      f"Nửa đầu dương ({early_r:+.1f}R) nhưng nửa sau âm ({late_r:+.1f}R)."
    )
  else:
    verdict, msg = "stable", (
      f"Chưa thấy suy giảm rõ: nửa đầu {early_r:+.1f}R · nửa sau {late_r:+.1f}R "
      f"(Δ {delta:+.1f}R)."
    )
    if edge_delta is not None:
      msg += f" Edge KB Δ {edge_delta:+.1f}R."

  return {
    "n_months": n,
    "early_months": mid,
    "late_months": n - mid,
    "early_r": round(early_r, 3),
    "late_r": round(late_r, 3),
    "delta_r": delta,
    "verdict": verdict,
    "message": msg,
    "edge_early": edge_early,
    "edge_late": edge_late,
    "edge_delta": edge_delta,
  }


def _as_ts(value) -> pd.Timestamp | None:
  if value is None or value == "":
    return None
  try:
    return pd.Timestamp(value)
  except Exception:
    return None


def resolve_model_periods(model: dict | None) -> list[dict[str, Any]]:
  """
  Timeline segments for a Trade Model:
  KB học, cửa sổ train đầu/cuối (shift), OOS.
  """
  if not model:
    return []

  segments: list[dict[str, Any]] = []
  kb_id = model.get("kb_profile")
  train_weeks = int(model.get("train_weeks") or 3)
  oos_from = _as_ts(model.get("oos_from"))
  oos_to = _as_ts(model.get("oos_to"))

  kb_from = kb_to = None
  kb_label = "KB học"
  if kb_id:
    try:
      from kb_profiles import get_profile
      from gui.app_settings import era_by_kb_profile, kb_profile_label

      prof = get_profile(str(kb_id)) or {}
      era = era_by_kb_profile(str(kb_id)) or {}
      kb_from = _as_ts(prof.get("trained_from") or era.get("learn_from"))
      kb_to = _as_ts(prof.get("trained_to") or era.get("learn_until"))
      kb_label = f"KB học · {kb_profile_label(kb_id)}"
      snap = model.get("kb_snapshot")
      if snap:
        kb_label += f" (ep{int(snap):03d})" if str(snap).isdigit() else f" ({snap})"
    except Exception:
      kb_from = kb_to = None

  if kb_from is not None and kb_to is not None and kb_to >= kb_from:
    segments.append({
      "lane": "KB học",
      "label": kb_label,
      "start": kb_from,
      "end": kb_to,
      "color": "#7e57c2",
      "detail": f"{kb_from.date()} → {kb_to.date()}",
    })

  if oos_from is not None and train_weeks > 0:
    first_start = oos_from - pd.Timedelta(weeks=train_weeks)
    segments.append({
      "lane": "Train shift",
      "label": f"Train đầu · {train_weeks} tuần trước OOS",
      "start": first_start,
      "end": oos_from,
      "color": "#ffa726",
      "detail": (
        f"Cửa sổ remine tuần đầu OOS: {first_start.date()} → {oos_from.date()} "
        f"(dịch {train_weeks} tuần mỗi tuần)"
      ),
    })
    if oos_to is not None and oos_to > oos_from:
      # Last remine typically ends just before the last OOS week.
      last_as_of = max(oos_from, oos_to - pd.Timedelta(weeks=1))
      last_start = last_as_of - pd.Timedelta(weeks=train_weeks)
      segments.append({
        "lane": "Train shift",
        "label": f"Train cuối · {train_weeks} tuần (shift)",
        "start": last_start,
        "end": last_as_of,
        "color": "#ffb74d",
        "detail": (
          f"Ví dụ cửa sổ remine gần cuối: {last_start.date()} → {last_as_of.date()}"
        ),
      })

  if oos_from is not None and oos_to is not None and oos_to >= oos_from:
    segments.append({
      "lane": "OOS",
      "label": "OOS (kiểm chứng)",
      "start": oos_from,
      "end": oos_to,
      "color": "#26a69a",
      "detail": f"{oos_from.date()} → {oos_to.date()}",
    })
  elif oos_from is not None:
    end = oos_from + pd.Timedelta(days=365)
    segments.append({
      "lane": "OOS",
      "label": "OOS (từ …)",
      "start": oos_from,
      "end": end,
      "color": "#26a69a",
      "detail": f"Từ {oos_from.date()} (chưa có oos_to)",
    })

  return segments


def build_model_timeline_figure(
  model: dict | None,
  *,
  title: str = "Giai đoạn dùng trong model",
) -> go.Figure | None:
  """Horizontal timeline: KB học · train shift · OOS."""
  segments = resolve_model_periods(model)
  if not segments:
    return None

  lane_order = ["KB học", "Train shift", "OOS"]
  present = [lane for lane in lane_order if any(s["lane"] == lane for s in segments)]
  y_map = {lane: i for i, lane in enumerate(reversed(present))}

  fig = go.Figure()
  for seg in segments:
    y = y_map[seg["lane"]]
    start, end = seg["start"], seg["end"]
    fig.add_trace(go.Scatter(
      x=[start, end, end, start, start],
      y=[y - 0.32, y - 0.32, y + 0.32, y + 0.32, y - 0.32],
      fill="toself",
      mode="lines",
      line=dict(width=0),
      fillcolor=seg["color"],
      opacity=0.85,
      name=seg["label"],
      hovertemplate=(
        f"<b>{seg['label']}</b><br>"
        f"{seg['detail']}<extra></extra>"
      ),
      showlegend=True,
    ))
    # Only label inside long bars; short shift windows use legend/hover.
    if (end - start) >= pd.Timedelta(days=45):
      mid = start + (end - start) / 2
      fig.add_annotation(
        x=mid, y=y,
        text=seg["label"],
        showarrow=False,
        font=dict(size=11, color="white"),
        xanchor="center", yanchor="middle",
      )

  # Markers: end of KB / start of OOS
  oos_from = _as_ts((model or {}).get("oos_from"))
  if oos_from is not None:
    fig.add_vline(
      x=oos_from, line_width=1.5, line_dash="dash", line_color="#546e7a",
      annotation_text="OOS bắt đầu", annotation_position="top",
      annotation_font_size=10,
    )

  fig.update_layout(
    title=dict(text=title, font=dict(size=14)),
    height=220 + 48 * len(present),
    margin=dict(l=20, r=20, t=56, b=88),
    legend=dict(
      orientation="h",
      yanchor="top",
      y=-0.22,
      x=0,
      xanchor="left",
      bgcolor="rgba(255,255,255,0.85)",
      bordercolor="rgba(0,0,0,0.08)",
      borderwidth=1,
      font=dict(size=11),
      tracegroupgap=18,
      itemsizing="constant",
      itemwidth=40,
    ),
    hovermode="closest",
    yaxis=dict(
      tickmode="array",
      tickvals=[y_map[l] for l in present],
      ticktext=present,
      range=[-0.7, len(present) - 0.3],
      fixedrange=True,
    ),
    xaxis=dict(
      title="Thời gian",
      type="date",
      showgrid=True,
      gridcolor="rgba(0,0,0,0.06)",
    ),
    plot_bgcolor="rgba(248,249,250,1)",
  )
  return fig


def build_monthly_kb_compare_figure(
  on_monthly: pd.DataFrame,
  off_monthly: pd.DataFrame | None = None,
  *,
  title: str = "OOS theo tháng · KB ON vs OFF",
) -> go.Figure | None:
  if on_monthly is None or on_monthly.empty:
    return None

  on = on_monthly.sort_values("month").copy()
  months = list(on["month"])
  fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    row_heights=[0.55, 0.45], vertical_spacing=0.12,
    subplot_titles=("R từng tháng", "R tích lũy"),
  )

  fig.add_trace(go.Bar(
    x=months, y=on["total_r"], name="KB ON",
    marker_color="#26a69a", opacity=0.85,
  ), row=1, col=1)

  if off_monthly is not None and not off_monthly.empty:
    off = off_monthly.sort_values("month")
    off_map = dict(zip(off["month"], off["total_r"]))
    off_y = [off_map.get(m) for m in months]
    fig.add_trace(go.Bar(
      x=months, y=off_y, name="KB OFF",
      marker_color="#787b86", opacity=0.75,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
      x=list(off["month"]), y=off["cum_r"], name="Cum KB OFF",
      line=dict(color="#787b86", width=2, dash="dot"),
    ), row=2, col=1)

  fig.add_trace(go.Scatter(
    x=months, y=on["cum_r"], name="Cum KB ON",
    line=dict(color="#2962ff", width=2.5),
  ), row=2, col=1)

  fig.update_layout(
    title=dict(text=title, font=dict(size=13), y=0.98, yanchor="top"),
    barmode="group",
    bargap=0.18,
    bargroupgap=0.08,
    height=560,
    # Extra bottom room so legend items are not cramped under the plot.
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
      tracegroupgap=24,
      itemsizing="constant",
      itemwidth=42,
      entrywidth=0.22,
      entrywidthmode="fraction",
    ),
    hovermode="x unified",
  )
  fig.update_yaxes(title_text="R / tháng", row=1, col=1)
  fig.update_yaxes(title_text="Cum R", row=2, col=1)
  fig.update_xaxes(title_text="Tháng", row=2, col=1)
  fig.update_annotations(font_size=12)
  return fig
