"""Phân tích hiệu quả setup theo regime thị trường (sideways / trend)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

EMA_SEP_SIDEWAYS_PIPS = 15.0

REGIME_LABELS = {
    "sideways": "Đi ngang (EMA H1 sep < 15 pip)",
    "h4_uptrend": "H4 uptrend (EMA tách rõ)",
    "h4_downtrend": "H4 downtrend (EMA tách rõ)",
}


def ema_separation_pips(row: pd.Series) -> float:
    ema50 = float(row.get("ema50", np.nan))
    ema200 = float(row.get("ema200", np.nan))
    if np.isnan(ema50) or np.isnan(ema200):
        return 0.0
    return abs(ema50 - ema200) * 10_000


def classify_regime(row: pd.Series, *, sep_threshold: float = EMA_SEP_SIDEWAYS_PIPS) -> str:
    sep = ema_separation_pips(row)
    h4_up = bool(row.get("h4_trend_up", False))
    if sep < sep_threshold:
        return "sideways"
    if h4_up:
        return "h4_uptrend"
    return "h4_downtrend"


def _entry_row(df: pd.DataFrame, entry_time: int) -> pd.Series | None:
    ts = pd.Timestamp(entry_time, unit="s", tz="UTC")
    loc = df.index.get_indexer([ts], method="nearest")[0]
    if loc < 0:
        return None
    return df.iloc[loc]


def enrich_trade(df: pd.DataFrame, trade: dict[str, Any]) -> dict[str, Any]:
    row = _entry_row(df, trade["entry_time"])
    if row is None:
        return {**trade, "regime": "unknown", "h4_trend_up": None, "ema_sep_pips": None}
    regime = classify_regime(row)
    return {
        **trade,
        "regime": regime,
        "regime_label": REGIME_LABELS.get(regime, regime),
        "h4_trend_up": bool(row.get("h4_trend_up", False)),
        "ema_sep_pips": round(ema_separation_pips(row), 1),
    }


def _group_stats(trades: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if not trades:
        return {
            "label": label,
            "trades": 0,
            "win_rate": 0.0,
            "sl_rate": 0.0,
            "expectancy_r": 0.0,
            "profit_factor": 0.0,
            "total_pips": 0.0,
            "pip_share_pct": 0.0,
        }
    n = len(trades)
    wins = sum(1 for t in trades if (t.get("r_multiple") or 0) > 0)
    sl = sum(1 for t in trades if t.get("exit_reason") == "sl")
    exp = sum(t.get("r_multiple", 0) or 0 for t in trades) / n
    pip = sum(t.get("pnl_pips", 0) or 0 for t in trades)
    gross_win = sum(t.get("pnl_pips", 0) for t in trades if (t.get("pnl_pips") or 0) > 0)
    gross_loss = abs(sum(t.get("pnl_pips", 0) for t in trades if (t.get("pnl_pips") or 0) < 0))
    pf = gross_win / gross_loss if gross_loss else 0.0
    return {
        "label": label,
        "trades": n,
        "win_rate": round(100 * wins / n, 1),
        "sl_rate": round(100 * sl / n, 1),
        "expectancy_r": round(exp, 2),
        "profit_factor": round(pf, 2),
        "total_pips": round(pip, 1),
    }


def _max_sl_streak(trades: list[dict[str, Any]]) -> int:
    streak = mx = 0
    for t in sorted(trades, key=lambda x: x.get("entry_time", 0)):
        if t.get("exit_reason") == "sl":
            streak += 1
            mx = max(mx, streak)
        else:
            streak = 0
    return mx


def build_regime_report(
    df: pd.DataFrame,
    trades: list[dict[str, Any]],
    *,
    filter_avoid_sideways: dict[str, Any] | None = None,
    baseline_unfiltered: dict[str, Any] | None = None,
) -> dict[str, Any]:
    enriched = [enrich_trade(df, t) for t in trades]
    total_pip = sum(t.get("pnl_pips", 0) or 0 for t in enriched) or 1.0

    by_regime: list[dict[str, Any]] = []
    for key in ("sideways", "h4_downtrend", "h4_uptrend"):
        group = [t for t in enriched if t.get("regime") == key]
        row = _group_stats(group, REGIME_LABELS[key])
        row["regime"] = key
        row["pip_share_pct"] = round(100 * row["total_pips"] / total_pip, 0)
        by_regime.append(row)

    h4_up = _group_stats([t for t in enriched if t.get("h4_trend_up")], "H4 tăng (tại entry)")
    h4_down = _group_stats([t for t in enriched if t.get("h4_trend_up") is False], "H4 giảm (tại entry)")

    worst = min((r for r in by_regime if r["trades"] > 0), key=lambda r: r["expectancy_r"], default=None)
    best = max((r for r in by_regime if r["trades"] > 0), key=lambda r: r["expectancy_r"], default=None)

    conclusion_parts = []
    if worst and worst["regime"] == "sideways" and worst["expectancy_r"] < 0:
        conclusion_parts.append(
            f"Đi ngang kém nhất ({worst['expectancy_r']:+.2f}R, SL {worst['sl_rate']:.0f}%)"
        )
    if best:
        conclusion_parts.append(
            f"Tốt nhất: {best['label']} ({best['expectancy_r']:+.2f}R, PF {best['profit_factor']:.2f})"
        )
    conclusion_parts.append(f"Chuỗi SL dài nhất: {_max_sl_streak(enriched)} lệnh")

    filter_note = None
    if baseline_unfiltered and enriched:
        cur_exp = sum(t.get("r_multiple", 0) or 0 for t in enriched) / len(enriched)
        base_exp = baseline_unfiltered.get("expectancy_r", 0)
        filter_note = (
            f"Đã áp dụng lọc sideways: {len(enriched)} lệnh {cur_exp:+.2f}R vs "
            f"không lọc {baseline_unfiltered.get('trades', 0)} lệnh {base_exp:+.2f}R"
        )
    elif filter_avoid_sideways and filter_avoid_sideways.get("trades", 0) >= 10:
        base_exp = sum(t.get("r_multiple", 0) or 0 for t in enriched) / max(len(enriched), 1)
        f_exp = filter_avoid_sideways.get("expectancy_r", 0)
        if f_exp > base_exp + 0.05:
            filter_note = (
                f"Lọc tránh sideways (EMA sep ≥ {EMA_SEP_SIDEWAYS_PIPS:.0f} pip): "
                f"{filter_avoid_sideways['trades']} lệnh, {f_exp:+.2f}R vs baseline {base_exp:+.2f}R — "
                "cân nhắc bỏ qua tín hiệu khi EMA50/200 H1 sát nhau"
            )
        else:
            filter_note = (
                f"Lọc tránh sideways: {filter_avoid_sideways.get('trades', 0)} lệnh, "
                f"{f_exp:+.2f}R — chưa vượt rõ baseline, dùng làm cảnh báo thủ công"
            )

    return {
        "ema_sep_threshold_pips": EMA_SEP_SIDEWAYS_PIPS,
        "by_regime": by_regime,
        "by_h4_trend": [h4_up, h4_down],
        "max_sl_streak": _max_sl_streak(enriched),
        "filter_avoid_sideways": filter_avoid_sideways,
        "conclusion": " · ".join(conclusion_parts),
        "filter_note": filter_note,
        "trading_hints": [
            "Long RSI thấp là kỳ vọng giá bật lại — không phải trade theo xu hướng",
            f"Tránh vào lệnh khi EMA50 và EMA200 H1 cách nhau < {EMA_SEP_SIDEWAYS_PIPS:.0f} pip (sideways)",
            "Sau 3–4 SL liên tiếp: cân nhắc tạm dừng thủ công (rule 2 SL→vùng 68–72 đã thử, kém baseline)",
        ],
    }
