"""Analytics helpers for GUI charts and tables."""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .strategy import Trade, max_drawdown_r


def trades_json_to_df(trades: list[dict]) -> pd.DataFrame:
  if not trades:
    return pd.DataFrame()
  df = pd.DataFrame(trades)
  if "entry" in df.columns:
    df["entry"] = pd.to_datetime(df["entry"])
  if "exit" in df.columns:
    df["exit"] = pd.to_datetime(df["exit"])
  return df.sort_values("entry").reset_index(drop=True)


def trade_objects_to_rows(trades: list[Trade]) -> list[dict]:
  return [
    {
      "entry": str(t.entry_time),
      "exit": str(t.exit_time),
      "dir": "LONG" if t.direction == 1 else "SHORT",
      "entry_px": round(t.entry_price, 5),
      "exit_px": round(t.exit_price, 5),
      "sl": round(t.sl, 5),
      "tp": round(t.tp, 5),
      "pnl_pips": round(t.pnl_pips, 1),
      "r": round(t.r_multiple, 2),
      "reason": t.exit_reason,
    }
    for t in trades
  ]


def equity_series(trades_df: pd.DataFrame) -> pd.DataFrame:
  if trades_df.empty or "r" not in trades_df.columns:
    return pd.DataFrame(columns=["entry", "equity_r", "drawdown_r"])
  out = trades_df[["entry", "r"]].copy()
  out["equity_r"] = out["r"].cumsum()
  peak = out["equity_r"].cummax()
  out["drawdown_r"] = peak - out["equity_r"]
  return out


def rolling_win_rate(trades_df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
  if trades_df.empty:
    return pd.DataFrame()
  out = trades_df[["entry", "r"]].copy()
  out["win"] = (out["r"] > 0).astype(float)
  out["rolling_wr"] = out["win"].rolling(window, min_periods=max(5, window // 4)).mean() * 100
  return out.dropna(subset=["rolling_wr"])


def yearly_breakdown(trades_df: pd.DataFrame) -> pd.DataFrame:
  if trades_df.empty:
    return pd.DataFrame()
  df = trades_df.copy()
  df["year"] = df["entry"].dt.year
  rows = []
  for year, g in df.groupby("year"):
    wins = (g["r"] > 0).sum()
    rows.append({
      "year": int(year),
      "n_trades": len(g),
      "win_rate_pct": round(wins / len(g) * 100, 1),
      "total_r": round(g["r"].sum(), 1),
      "avg_r": round(g["r"].mean(), 2),
    })
  return pd.DataFrame(rows)


def weekly_r_histogram(weekly_log: list[dict]) -> pd.DataFrame:
  rows = []
  for w in weekly_log:
    if "oos_r" in w:
      rows.append({"week": w.get("week_start", w.get("week")), "oos_r": w["oos_r"]})
    elif "r" in w:
      rows.append({"week": w.get("week"), "oos_r": w["r"]})
  return pd.DataFrame(rows)


def exit_reason_stats(trades_df: pd.DataFrame) -> pd.DataFrame:
  if trades_df.empty or "reason" not in trades_df.columns:
    return pd.DataFrame()
  g = trades_df.groupby("reason").agg(
    count=("r", "count"),
    total_r=("r", "sum"),
    avg_r=("r", "mean"),
    win_rate=("r", lambda s: (s > 0).mean() * 100),
  ).reset_index()
  g["win_rate"] = g["win_rate"].round(1)
  g["total_r"] = g["total_r"].round(2)
  g["avg_r"] = g["avg_r"].round(2)
  return g.sort_values("count", ascending=False)


def direction_bias(trades_df: pd.DataFrame) -> pd.DataFrame:
  if trades_df.empty or "dir" not in trades_df.columns:
    return pd.DataFrame()
  g = trades_df.groupby("dir").agg(
    count=("r", "count"),
    total_r=("r", "sum"),
    win_rate=("r", lambda s: (s > 0).mean() * 100),
  ).reset_index()
  g["pct"] = (g["count"] / g["count"].sum() * 100).round(1)
  g["win_rate"] = g["win_rate"].round(1)
  g["total_r"] = g["total_r"].round(1)
  return g


def rule_stats_table(rule_stats: dict) -> pd.DataFrame:
  rows = []
  for key, st in rule_stats.items():
    parts = key.split("|", 3)
    if len(parts) != 4:
      continue
    direction, feature, op, thr = parts
    uses = st.get("uses", 0)
    if uses < 1:
      continue
    rows.append({
      "direction": direction,
      "feature": feature,
      "op": op,
      "threshold": float(thr),
      "uses": uses,
      "wins": st.get("wins", 0),
      "losses": st.get("losses", 0),
      "win_rate_pct": round(st.get("wins", 0) / uses * 100, 1),
      "total_r": round(st.get("total_r", 0), 2),
      "avg_r": round(st.get("total_r", 0) / uses, 3),
    })
  if not rows:
    return pd.DataFrame()
  return pd.DataFrame(rows).sort_values("uses", ascending=False)


def genomes_table(genomes: list[dict]) -> pd.DataFrame:
  if not genomes:
    return pd.DataFrame()
  rows = []
  for i, g in enumerate(genomes[:15]):
    rows.append({
      "rank": i + 1,
      "name": g.get("name", "?"),
      "fitness": round(g.get("fitness", 0), 1),
      "exit_mode": g.get("exit_mode"),
      "rr": g.get("rr_ratio"),
      "atr_mult": g.get("atr_mult_sl"),
      "ml_min": round(g.get("ml_prob_min", 0), 3),
      "long_rules": len(g.get("long_rules", [])),
      "short_rules": len(g.get("short_rules", [])),
    })
  return pd.DataFrame(rows)


def filter_trades_df(
  trades_df: pd.DataFrame,
  year: int | None = None,
  direction: str | None = None,
  min_r: float | None = None,
  max_r: float | None = None,
) -> pd.DataFrame:
  if trades_df.empty:
    return trades_df
  out = trades_df.copy()
  if year:
    out = out[out["entry"].dt.year == year]
  if direction and direction != "All":
    out = out[out["dir"] == direction]
  if min_r is not None:
    out = out[out["r"] >= min_r]
  if max_r is not None:
    out = out[out["r"] <= max_r]
  return out


def ohlc_around_trade(ohlc: pd.DataFrame, entry_time: pd.Timestamp, bars: int = 48) -> pd.DataFrame:
  if ohlc.empty:
    return ohlc
  try:
    idx = ohlc.index.get_indexer([entry_time], method="nearest")[0]
  except Exception:
    return pd.DataFrame()
  start = max(0, idx - bars // 2)
  end = min(len(ohlc), idx + bars // 2)
  return ohlc.iloc[start:end].copy()
