"""Equity / drawdown charts for Live History (journal + schedule-parity weeks)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from journal_view import (
  PERIOD_LABELS,
  _is_closed,
  _label_map,
  _model_key,
  _trade_close_ts,
  _trade_r,
  filter_trades_by_period,
)


def _ts_sort_key(ts: datetime | None, idx: int) -> tuple:
  if ts is None:
    return (1, idx)
  if ts.tzinfo is None:
    ts = ts.replace(tzinfo=timezone.utc)
  return (0, ts.timestamp(), idx)


def trades_to_equity_df(
  trades: list[dict],
  *,
  period: str = "all",
) -> pd.DataFrame:
  """Closed trades → equity_r / drawdown_r sorted by close time."""
  filtered = filter_trades_by_period(trades, period, closed_only=True)
  rows = []
  for i, t in enumerate(filtered):
    if not _is_closed(t):
      continue
    r = _trade_r(t)
    if r is None:
      continue
    ts = _trade_close_ts(t) or _trade_close_ts({
      "exit_time": t.get("entry_time") or t.get("opened_at"),
    })
    rows.append({
      "t": ts,
      "r": float(r),
      "model_id": _model_key(t),
      "_i": i,
    })
  if not rows:
    return pd.DataFrame(columns=["t", "r", "equity_r", "drawdown_r", "model_id"])
  rows.sort(key=lambda x: _ts_sort_key(x["t"], x["_i"]))
  df = pd.DataFrame(rows)
  df["equity_r"] = df["r"].cumsum()
  peak = df["equity_r"].cummax()
  df["drawdown_r"] = peak - df["equity_r"]
  return df


def parity_weeks_to_equity_df(models: list[dict]) -> dict[str, pd.DataFrame]:
  """Build per-model equity from schedule-parity week rows."""
  labels = _label_map()
  out: dict[str, pd.DataFrame] = {}
  for m in models:
    if not m.get("ok"):
      continue
    mid = str(m.get("model_id") or "unknown")
    weeks = []
    for w in m.get("weeks") or []:
      if w.get("status"):
        continue
      ws = w.get("week_start")
      try:
        r = float(w.get("total_r") or 0.0)
      except (TypeError, ValueError):
        continue
      weeks.append({"t": pd.Timestamp(ws) if ws else None, "r": r, "model_id": mid})
    if not weeks:
      # fallback: single point from overall
      try:
        r = float(m.get("total_r") or 0.0)
      except (TypeError, ValueError):
        r = 0.0
      weeks = [{"t": pd.Timestamp("2026-01-01"), "r": r, "model_id": mid}]
    weeks.sort(key=lambda x: (x["t"] is None, x["t"]))
    df = pd.DataFrame(weeks)
    df["equity_r"] = df["r"].cumsum()
    df["drawdown_r"] = df["equity_r"].cummax() - df["equity_r"]
    df.attrs["label"] = labels.get(mid) or m.get("label") or mid
    out[mid] = df
  return out


def max_dd(df: pd.DataFrame) -> float:
  if df.empty or "drawdown_r" not in df.columns:
    return 0.0
  return float(df["drawdown_r"].max() or 0.0)


def _short_label(name: str, *, max_len: int = 28) -> str:
  s = " ".join(str(name or "").split())
  if len(s) <= max_len:
    return s
  return s[: max_len - 1] + "…"


def build_equity_figure(
  *,
  combined: pd.DataFrame | None = None,
  by_model: dict[str, pd.DataFrame] | None = None,
  title: str = "Equity & drawdown (R)",
  labels: dict[str, str] | None = None,
  theme: str = "light",
) -> go.Figure | None:
  labels = labels or {}
  by_model = by_model or {}
  has_combined = combined is not None and not combined.empty
  has_models = any(not d.empty for d in by_model.values())
  if not has_combined and not has_models:
    return None

  # Light-only desk theme
  dark = False
  # No subplot_titles — they collide with the legend. Axis titles carry meaning.
  fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    vertical_spacing=0.12,
    row_heights=[0.62, 0.38],
  )

  palette = (
    "#2dd4bf", "#fb7185", "#38bdf8", "#fbbf24",
    "#a78bfa", "#34d399", "#f472b6", "#94a3b8",
  ) if dark else (
    "#0f766e", "#b91c1c", "#1d4ed8", "#b45309",
    "#6d28d9", "#047857", "#be185d", "#475569",
  )
  all_line = "#5eead4" if dark else "#0f766e"
  all_fill = "rgba(45,212,191,0.16)" if dark else "rgba(15,118,110,0.10)"
  dd_line = "#fb7185" if dark else "#b91c1c"
  dd_fill = "rgba(251,113,133,0.22)" if dark else "rgba(185,28,28,0.18)"
  grid = "rgba(232,238,246,0.10)" if dark else "rgba(15,23,42,0.08)"
  zero = "rgba(232,238,246,0.28)" if dark else "rgba(15,23,42,0.28)"
  font_c = "#e8eef6" if dark else "#0f172a"
  plot_bg = "#0f172a" if dark else "#f8fafc"
  paper_bg = "#151d2b" if dark else "#ffffff"
  legend_bg = "rgba(15,23,42,0.92)" if dark else "rgba(255,255,255,0.92)"

  if has_combined:
    x = combined["t"]
    fig.add_trace(
      go.Scatter(
        x=x,
        y=combined["equity_r"],
        name="All",
        legendgroup="all",
        line=dict(color=all_line, width=2.6),
        fill="tozeroy",
        fillcolor=all_fill,
        hovertemplate="%{x|%Y-%m-%d}<br>All: %{y:.2f}R<extra></extra>",
      ),
      row=1, col=1,
    )
    # Drawdown as positive depth (read as "how far below peak")
    fig.add_trace(
      go.Scatter(
        x=x,
        y=combined["drawdown_r"],
        name="Drawdown",
        legendgroup="dd",
        line=dict(color=dd_line, width=1.8),
        fill="tozeroy",
        fillcolor=dd_fill,
        hovertemplate="%{x|%Y-%m-%d}<br>DD: %{y:.2f}R<extra></extra>",
      ),
      row=2, col=1,
    )

  # Per-model: thin lines on equity only (no fill) — skip if only one model
  model_items = [(m, d) for m, d in by_model.items() if not d.empty]
  if has_combined and len(model_items) > 1:
    for i, (mid, df) in enumerate(model_items):
      color = palette[i % len(palette)]
      raw = labels.get(mid) or df.attrs.get("label") or mid
      name = _short_label(raw)
      fig.add_trace(
        go.Scatter(
          x=df["t"],
          y=df["equity_r"],
          name=name,
          legendgroup=f"m{i}",
          line=dict(color=color, width=1.3, dash="dot"),
          opacity=0.9,
          hovertemplate=f"%{{x|%Y-%m-%d}}<br>{name}: %{{y:.2f}}R<extra></extra>",
        ),
        row=1, col=1,
      )

  n_legend = 1 + (len(model_items) if has_combined and len(model_items) > 1 else 0) + (1 if has_combined else 0)
  # Legend below plot — avoids overlap with title / subplot headers
  layout_kw: dict[str, Any] = dict(
    height=500 if n_legend <= 5 else 540,
    margin=dict(l=56, r=16, t=16 if not title else 36, b=92 if n_legend <= 6 else 118),
    font=dict(color=font_c, size=12),
    legend=dict(
      orientation="h",
      yanchor="top",
      y=-0.16,
      x=0,
      xanchor="left",
      font=dict(size=11, color=font_c),
      bgcolor=legend_bg,
      borderwidth=0,
      itemwidth=36,
      traceorder="normal",
    ),
    hovermode="x unified",
    template="plotly_dark" if dark else "plotly_white",
    plot_bgcolor=plot_bg,
    paper_bgcolor=paper_bg,
  )
  if title:
    layout_kw["title"] = dict(
      text=title, x=0.0, xanchor="left", font=dict(size=14, color=font_c),
    )
  fig.update_layout(**layout_kw)
  fig.update_yaxes(
    title_text="Equity (R)", title_font=dict(size=12, color=font_c),
    tickfont=dict(color=font_c),
    showgrid=True, gridcolor=grid, zeroline=True,
    zerolinecolor=zero, row=1, col=1,
  )
  fig.update_yaxes(
    title_text="Drawdown (R)", title_font=dict(size=12, color=font_c),
    tickfont=dict(color=font_c),
    showgrid=True, gridcolor=grid,
    rangemode="tozero",
    row=2, col=1,
  )
  fig.update_xaxes(showticklabels=False, row=1, col=1)
  fig.update_xaxes(
    title_text=None, showgrid=False,
    tickfont=dict(size=11, color=font_c), row=2, col=1,
  )
  return fig


def equity_payload_from_trades(
  trades: list[dict],
  *,
  period: str = "all",
  theme: str = "light",
) -> dict[str, Any]:
  labels = _label_map()
  combined = trades_to_equity_df(trades, period=period)
  by_model: dict[str, pd.DataFrame] = {}
  # split
  filtered = filter_trades_by_period(trades, period, closed_only=True)
  groups: dict[str, list[dict]] = {}
  for t in filtered:
    if _trade_r(t) is None:
      continue
    groups.setdefault(_model_key(t), []).append(t)
  for mid, group in groups.items():
    by_model[mid] = trades_to_equity_df(group, period="all")  # already filtered
    by_model[mid].attrs["label"] = labels.get(mid) or mid

  fig = build_equity_figure(
    combined=combined,
    by_model=by_model if len(by_model) > 1 else {},
    title="",
    labels=labels,
    theme=theme,
  )
  return {
    "source": "journal",
    "period": period,
    "n_points": int(len(combined)),
    "total_r": round(float(combined["equity_r"].iloc[-1]), 3) if len(combined) else 0.0,
    "max_dd_r": round(max_dd(combined), 3),
    "figure": fig,
    "by_model": {
      mid: {
        "label": labels.get(mid) or mid,
        "total_r": round(float(df["equity_r"].iloc[-1]), 3) if len(df) else 0.0,
        "max_dd_r": round(max_dd(df), 3),
        "n": int(len(df)),
      }
      for mid, df in by_model.items()
    },
  }


def equity_payload_from_parity(
  books: list[dict],
  *,
  theme: str = "light",
) -> dict[str, Any]:
  """Aggregate parity book results into equity charts (week grain)."""
  labels = _label_map()
  all_weeks: list[dict] = []
  by_model: dict[str, pd.DataFrame] = {}
  for book in books:
    models = book.get("models") or book.get("parity_models") or []
    # normalize parity_models shape from load_sim_progress
    norm = []
    for m in models:
      if "weeks" in m:
        norm.append(m)
      elif m.get("id") or m.get("model_id"):
        # thin progress row — skip week equity
        continue
    if not norm and book.get("models"):
      norm = list(book["models"])
    part = parity_weeks_to_equity_df(norm)
    by_model.update(part)
    for mid, df in part.items():
      for _, row in df.iterrows():
        all_weeks.append({"t": row["t"], "r": row["r"], "model_id": mid, "_i": 0})

  combined = pd.DataFrame(columns=["t", "r", "equity_r", "drawdown_r", "model_id"])
  if all_weeks:
    all_weeks.sort(key=lambda x: (x["t"] is None, x["t"], x["model_id"]))
    # When multiple models close same week, cumulate in stable model order
    combined = pd.DataFrame(all_weeks)
    combined["equity_r"] = combined["r"].cumsum()
    combined["drawdown_r"] = combined["equity_r"].cummax() - combined["equity_r"]

  fig = build_equity_figure(
    combined=combined if not combined.empty else None,
    by_model=by_model if len(by_model) > 1 else {},
    title="",
    labels={**labels, **{m: (by_model[m].attrs.get("label") or m) for m in by_model}},
    theme=theme,
  )
  return {
    "source": "parity_weeks",
    "period": "all",
    "n_points": int(len(combined)),
    "total_r": round(float(combined["equity_r"].iloc[-1]), 3) if len(combined) else 0.0,
    "max_dd_r": round(max_dd(combined), 3),
    "figure": fig,
    "by_model": {
      mid: {
        "label": df.attrs.get("label") or labels.get(mid) or mid,
        "total_r": round(float(df["equity_r"].iloc[-1]), 3) if len(df) else 0.0,
        "max_dd_r": round(max_dd(df), 3),
        "n": int(len(df)),
      }
      for mid, df in by_model.items()
    },
  }


def render_equity_section(
  trades: list[dict],
  *,
  period: str = "all",
  parity_books: list[dict] | None = None,
  theme: str | None = None,
) -> dict[str, Any] | None:
  """Pick best data source and return payload (caller renders figure)."""
  if theme is None:
    theme = "light"
  journal = equity_payload_from_trades(trades, period=period, theme="light")
  if journal["n_points"] > 0:
    return journal
  if parity_books:
    # Prefer full parity JSON books with weeks
    rich = []
    for b in parity_books:
      if b.get("models") and any("weeks" in (m or {}) for m in b.get("models") or []):
        rich.append(b)
    if rich:
      return equity_payload_from_parity(rich, theme=theme)
    # load from results files if only progress stubs
    try:
      import json

      from live_config import RESULTS_DIR

      loaded = []
      for b in parity_books:
        sym = (b.get("symbol") or "").lower()
        tf = (b.get("timeframe") or "").lower()
        if not sym or not tf:
          continue
        path = RESULTS_DIR / f"parity_{sym}_{tf}.json"
        if path.exists():
          loaded.append(json.loads(path.read_text(encoding="utf-8")))
      if loaded:
        return equity_payload_from_parity(loaded, theme=theme)
      books = []
      for p in RESULTS_DIR.glob("parity_*.json"):
        books.append(json.loads(p.read_text(encoding="utf-8")))
      if books:
        return equity_payload_from_parity(books, theme=theme)
    except Exception:
      pass
  return journal if journal.get("figure") is not None else None
