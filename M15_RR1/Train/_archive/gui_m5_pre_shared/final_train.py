"""Final Train — rank Grid Search combos across runs (before promoting Trade Models)."""
from __future__ import annotations

from typing import Literal

import plotly.graph_objects as go

from gui.trade_model import OVERVIEW_HIGH_DD_R, desk_pair_code, find_model_by_grid_key

SortMode = Literal["composite", "wr", "total_r", "dd", "pf", "risk_adj"]

WEIGHTS_BY_DESK: dict[str, dict[str, float]] = {
  "GBP": {"wr": 0.40, "r": 0.20, "dd": 0.30, "pf": 0.10},
  "EUR": {"wr": 0.25, "r": 0.40, "dd": 0.25, "pf": 0.10},
}

LIVE_OK_BONUS = 0.05  # WR>=60 and DD<=threshold
# Final Train DD gate (UI-adjustable; independent from live OVERVIEW_HIGH_DD_R).
DEFAULT_MAX_DD_R = 10.0


def desk_score_weights(desk: str | None = None) -> dict[str, float]:
  d = (desk or desk_pair_code()).upper()
  return dict(WEIGHTS_BY_DESK.get(d, WEIGHTS_BY_DESK["EUR"]))


def _f(row: dict, *keys: str) -> float | None:
  for k in keys:
    if row.get(k) is not None:
      try:
        return float(row[k])
      except (TypeError, ValueError):
        continue
  return None


def _minmax(vals: list[float | None]) -> list[float]:
  clean = [float(v) for v in vals if v is not None]
  if not clean:
    return [0.0] * len(vals)
  lo, hi = min(clean), max(clean)
  span = hi - lo
  if span <= 1e-12:
    return [0.5 if v is not None else 0.0 for v in vals]
  return [(float(v) - lo) / span if v is not None else 0.0 for v in vals]


def collect_grid_combo_rows(
  *,
  limit_runs: int = 40,
  max_dd_r: float = DEFAULT_MAX_DD_R,
) -> list[dict]:
  """Flatten successful combos from all archived Grid runs (+ latest).

  Each row is a grid combo with ``_run_id``, ``_run_at``, ``_grid_key``.
  Same ``key`` across runs is collapsed later in ``dedupe_grid_combos``.
  ``max_dd_r`` marks High-DD / Live-ok relative to the Final Train threshold.
  """
  from gui.grid_search_engine import list_grid_runs, load_grid_run, load_latest_grid_run

  dd_limit = float(max_dd_r)
  out: list[dict] = []
  seen_run: set[str] = set()

  def _ingest(data: dict | None):
    if not data:
      return
    rid = str(data.get("run_id") or "")
    if rid and rid in seen_run:
      return
    if rid:
      seen_run.add(rid)
    updated = str(data.get("updated_at") or "")
    for row in data.get("rows") or []:
      if not isinstance(row, dict):
        continue
      if row.get("error"):
        continue
      key = row.get("key")
      if not key:
        continue
      wr = _f(row, "win_rate_pct", "win_rate")
      tot = _f(row, "total_r")
      dd = _f(row, "max_drawdown_r", "max_dd_r")
      pf = _f(row, "profit_factor", "pf")
      if wr is None and tot is None:
        continue
      high_dd = dd is not None and float(dd) > dd_limit
      live_ok = (
        wr is not None and float(wr) >= 60.0
        and not high_dd
      )
      item = dict(row)
      item["_run_id"] = rid or "—"
      item["_run_at"] = updated
      item["_grid_key"] = str(key)
      item["_wr"] = wr
      item["_total_r"] = tot
      item["_dd"] = dd
      item["_pf"] = pf
      item["_high_dd"] = high_dd
      item["_live_ok"] = live_ok
      item["_max_dd_limit"] = dd_limit
      item["_risk_adj"] = _f(row, "risk_adjusted")
      existing = find_model_by_grid_key(str(key))
      item["_has_model"] = bool(existing)
      item["_model_id"] = existing.get("id") if existing else None
      item["_model_label"] = (
        (existing.get("label") or existing.get("id")) if existing else None
      )
      out.append(item)

  latest = load_latest_grid_run()
  _ingest(latest)
  for summary in list_grid_runs(limit=limit_runs):
    rid = summary.get("run_id")
    if rid and str(rid) in seen_run:
      continue
    _ingest(load_grid_run(rid))

  return out


def dedupe_grid_combos(rows: list[dict]) -> list[dict]:
  """Keep one row per grid ``key`` — prefer higher Total R, then newer run."""
  best: dict[str, dict] = {}
  for r in rows:
    key = str(r.get("_grid_key") or r.get("key") or "")
    if not key:
      continue
    prev = best.get(key)
    if prev is None:
      best[key] = r
      continue
    r_score = (
      r.get("_total_r") if r.get("_total_r") is not None else float("-inf"),
      str(r.get("_run_at") or ""),
    )
    p_score = (
      prev.get("_total_r") if prev.get("_total_r") is not None else float("-inf"),
      str(prev.get("_run_at") or ""),
    )
    if r_score > p_score:
      best[key] = r
  return list(best.values())


def oos_window_label(row: dict) -> str:
  """Stable OOS window text used for filter + table column."""
  a = str(row.get("oos_from") or "—")[:10]
  b = str(row.get("oos_to") or "—")[:10]
  return f"{a}→{b}"


def list_oos_windows(rows: list[dict]) -> list[str]:
  """Distinct OOS windows, newest end-date first."""
  seen: set[str] = set()
  out: list[str] = []
  for r in rows:
    label = oos_window_label(r)
    if label in seen or label == "—→—":
      continue
    seen.add(label)
    out.append(label)

  def _sort_key(label: str) -> tuple:
    parts = label.split("→", 1)
    end = parts[1] if len(parts) > 1 else ""
    start = parts[0] if parts else ""
    return (end, start)

  out.sort(key=_sort_key, reverse=True)
  return out


def filter_final_train_combos(
  rows: list[dict],
  *,
  hide_promoted: bool = False,
  max_dd_r: float = DEFAULT_MAX_DD_R,
  oos_window: str | None = None,
) -> list[dict]:
  """Drop promoted (optional), OOS mismatch, and combos with Max DD above ``max_dd_r``."""
  limit = float(max_dd_r)
  want = (oos_window or "").strip()
  if want in ("", "(Tất cả OOS)", "all", "*"):
    want = ""
  out: list[dict] = []
  for r in rows:
    if hide_promoted and r.get("_has_model"):
      continue
    if want and oos_window_label(r) != want:
      continue
    dd = r.get("_dd")
    if dd is not None and float(dd) > limit:
      continue
    out.append(r)
  return out


def rank_final_train_combos(
  rows: list[dict] | None = None,
  *,
  desk: str | None = None,
  mode: SortMode = "composite",
  hide_promoted: bool = False,
  max_dd_r: float = DEFAULT_MAX_DD_R,
  oos_window: str | None = None,
  limit_runs: int = 40,
) -> list[dict]:
  """Collect → dedupe → filter → score → sort Grid combos for Final Train."""
  if rows is None:
    rows = collect_grid_combo_rows(limit_runs=limit_runs, max_dd_r=max_dd_r)
  else:
    # Re-stamp High-DD / Live-ok against the current threshold.
    limit = float(max_dd_r)
    for r in rows:
      dd = r.get("_dd")
      high = dd is not None and float(dd) > limit
      r["_high_dd"] = high
      r["_max_dd_limit"] = limit
      wr = r.get("_wr")
      r["_live_ok"] = bool(wr is not None and float(wr) >= 60.0 and not high)
  merged = dedupe_grid_combos(rows)
  filtered = filter_final_train_combos(
    merged,
    hide_promoted=hide_promoted,
    max_dd_r=max_dd_r,
    oos_window=oos_window,
  )
  if not filtered:
    return []

  w = desk_score_weights(desk)
  wrs = [r.get("_wr") for r in filtered]
  rs = [r.get("_total_r") for r in filtered]
  dds = [r.get("_dd") for r in filtered]
  pfs = [r.get("_pf") for r in filtered]
  n_wr, n_r = _minmax(wrs), _minmax(rs)
  n_dd_raw = _minmax(dds)
  n_dd = [1.0 - x if dds[i] is not None else 0.0 for i, x in enumerate(n_dd_raw)]
  n_pf = _minmax(pfs)

  ranked: list[dict] = []
  for i, r in enumerate(filtered):
    score = (
      w["wr"] * n_wr[i]
      + w["r"] * n_r[i]
      + w["dd"] * n_dd[i]
      + w["pf"] * n_pf[i]
    )
    if r.get("_live_ok"):
      score = min(1.0, score + LIVE_OK_BONUS)
    row = dict(r)
    row["_score"] = round(float(score), 4)
    preset = row.get("mining_preset") or "—"
    row["#"] = 0
    row["Score"] = row["_score"]
    row["WR %"] = round(float(row["_wr"]), 1) if row.get("_wr") is not None else None
    row["Total R"] = (
      round(float(row["_total_r"]), 2) if row.get("_total_r") is not None else None
    )
    row["Max DD"] = (
      round(float(row["_dd"]), 2) if row.get("_dd") is not None else None
    )
    row["PF"] = round(float(row["_pf"]), 2) if row.get("_pf") is not None else None
    row["Train"] = row.get("train_weeks")
    snap = row.get("kb_snapshot")
    row["KB"] = (
      "off" if not row.get("use_kb")
      else f"{row.get('kb_profile') or '—'}·{'latest' if snap is None else f'ep{snap}'}"
    )
    row["Preset"] = preset
    row["OOS"] = oos_window_label(row)
    row["Run"] = str(row.get("_run_id") or "")[:18]
    row["TM"] = "đã có" if row.get("_has_model") else "—"
    row["Combo"] = str(row.get("label") or row.get("_grid_key") or "")[:56]
    row["Badge"] = " · ".join(
      b for b in [
        "Live-ok" if row.get("_live_ok") else None,
        "High-DD" if row.get("_high_dd") else None,
        "Đã TM" if row.get("_has_model") else None,
      ] if b
    ) or "—"
    ranked.append(row)

  if mode == "wr":
    ranked.sort(
      key=lambda x: x.get("_wr") if x.get("_wr") is not None else float("-inf"),
      reverse=True,
    )
  elif mode == "total_r":
    ranked.sort(
      key=lambda x: x.get("_total_r") if x.get("_total_r") is not None else float("-inf"),
      reverse=True,
    )
  elif mode == "dd":
    ranked.sort(
      key=lambda x: x.get("_dd") if x.get("_dd") is not None else float("inf"),
    )
  elif mode == "pf":
    ranked.sort(
      key=lambda x: x.get("_pf") if x.get("_pf") is not None else float("-inf"),
      reverse=True,
    )
  elif mode == "risk_adj":
    ranked.sort(
      key=lambda x: x.get("_risk_adj") if x.get("_risk_adj") is not None else float("-inf"),
      reverse=True,
    )
  else:
    ranked.sort(key=lambda x: x.get("_score", 0.0), reverse=True)

  for i, row in enumerate(ranked, 1):
    row["_rank"] = i
    row["#"] = i
  return ranked


def build_final_train_scatter(
  rows_ranked: list[dict],
  *,
  top_n: int = 10,
  highlight_key: str | None = None,
  title: str = "Final Train · Grid combos · WR vs Total R",
) -> go.Figure | None:
  plot_rows = [
    r for r in rows_ranked
    if r.get("_wr") is not None and r.get("_total_r") is not None
  ]
  if not plot_rows:
    return None

  hl = str(highlight_key).strip() if highlight_key else ""
  top_ids = {str(r.get("_grid_key")) for r in plot_rows[: min(5, max(1, top_n))]}
  if hl:
    top_ids.add(hl)

  xs, ys, sizes, colors, texts, customs = [], [], [], [], [], []
  hl_row: dict | None = None
  for r in plot_rows:
    wr = float(r["_wr"])
    tot = float(r["_total_r"])
    dd = r.get("_dd")
    score = float(r.get("_score") or 0.0)
    if dd is not None and float(dd) > 0:
      size = max(8.0, min(28.0, 18.0 / (float(dd) ** 0.5)))
    else:
      size = 12.0
    key = str(r.get("_grid_key") or "")
    is_hl = bool(hl) and key == hl
    if is_hl:
      hl_row = r
      size = max(size, 16.0)
    name = str(r.get("Combo") or key[:20])
    mark = " ●" if r.get("_has_model") else ""
    xs.append(wr)
    ys.append(tot)
    sizes.append(size)
    colors.append(score)
    texts.append(f"{name[:28]}{mark}" if key in top_ids else "")
    hover = (
      f"{r.get('Combo')}<br>"
      f"Score {score:.3f} · WR {wr:.1f}% · R {tot:+.1f} · "
      f"DD {dd if dd is not None else '—'} · {r.get('Preset')} · "
      f"run {r.get('_run_id')}"
      + (" · đã có TM" if r.get("_has_model") else "")
      + (" · ĐANG CHỌN" if is_hl else "")
    )
    # [grid_key, hover] — grid_key used for chart→table selection
    customs.append([key, hover])

  fig = go.Figure()
  fig.add_trace(go.Scatter(
    x=xs, y=ys,
    mode="markers+text",
    text=texts,
    textposition="top center",
    textfont=dict(size=10, color="rgba(55,65,81,0.85)"),
    marker=dict(
      size=sizes,
      color=colors,
      colorscale="Tealgrn",
      showscale=True,
      colorbar=dict(title="Score"),
      line=dict(width=1, color="rgba(0,0,0,0.35)"),
      opacity=0.85,
    ),
    customdata=customs,
    hovertemplate="%{customdata[1]}<extra></extra>",
    name="Grid combos",
  ))

  if hl_row is not None:
    wr = float(hl_row["_wr"])
    tot = float(hl_row["_total_r"])
    label = str(hl_row.get("Combo") or hl)[:32]
    # Selected: same circle shape, stronger amber fill + ring (no dimming others)
    fig.add_trace(go.Scatter(
      x=[wr], y=[tot],
      mode="markers+text",
      text=[label],
      textposition="top center",
      textfont=dict(size=12, color="#9a3412"),
      marker=dict(
        size=22,
        symbol="circle",
        color="#fb923c",
        line=dict(width=3, color="#c2410c"),
      ),
      customdata=[[hl, f"<b>Đang chọn</b><br>{hl_row.get('Combo')}"]],
      hovertemplate="%{customdata[1]}<br>WR %{x:.1f}% · R %{y:+.1f}<extra></extra>",
      name="Đang chọn",
      showlegend=True,
    ))
    fig.add_vline(
      x=wr, line_width=1, line_dash="dot", line_color="rgba(194, 65, 12, 0.45)",
    )
    fig.add_hline(
      y=tot, line_width=1, line_dash="dot", line_color="rgba(194, 65, 12, 0.45)",
    )

  fig.update_layout(
    title=title,
    xaxis_title="WR % (Grid OOS)",
    yaxis_title="Total R (Grid OOS)",
    height=480,
    margin=dict(l=48, r=24, t=56, b=48),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
  )
  return fig


def weights_caption(desk: str | None = None, *, max_dd_r: float = DEFAULT_MAX_DD_R) -> str:
  d = (desk or desk_pair_code()).upper()
  w = desk_score_weights(d)
  return (
    f"Desk **{d}** · xếp hạng **combo Grid** (mọi lần chạy, gộp theo `key`) · "
    f"score = {w['wr']:.0%} WR + {w['r']:.0%} Total R + {w['dd']:.0%} (1−DD) + {w['pf']:.0%} PF"
    f" · Live-ok +{LIVE_OK_BONUS:.0%} · ẩn Max DD >{float(max_dd_r):g}R"
    f" · (live overview {OVERVIEW_HIGH_DD_R:g}R)"
  )
