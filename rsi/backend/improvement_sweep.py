"""Sweep các đề xuất cải tiến — so với baseline delay_1."""

from __future__ import annotations

from typing import Any

from .data_service import load_candles
from .divergence import find_rsi_divergences
from .setup_optimizer import backtest_setup, walk_forward_setup
from .zone_stats import ZoneConfig, analyze_zone_touches

SPLIT_DATE = "2025-01-01"
MIN_TRADES = 25

BASE = {
    "zone": "low",
    "entry_strategy": "delay_1",
    "sl_mode": "fixed",
    "stop_loss_pips": 25.0,
    "take_profit_mode": "r",
    "take_profit_r": 2.5,
    "max_bars": 48,
    "spread_pips": 1.0,
}

# (label, kwargs override)
CANDIDATES: list[tuple[str, dict[str, Any]]] = [
    ("★ Baseline delay_1", {}),
    ("Skip 1 lệnh sau SL", {"sl_skip_one": True, "sequential_trades": True}),
    ("Nến bullish tại entry", {"entry_filters": ["bullish"]}),
    ("RSI đang tăng tại entry", {"entry_filters": ["rsi_rising"]}),
    ("RSI quay đầu (2 nến)", {"entry_filters": ["rsi_turning"]}),
    ("RSI chạm sâu ≤30", {"entry_filters": ["deep_touch"]}),
    ("Giá trên EMA50 H1", {"entry_filters": ["above_ema50"]}),
    ("Filter H4 trend up", {"filters": ["h4_up"]}),
    ("Filter EMA50>200 H1", {"filters": ["ema_aligned"]}),
    ("H4 up + EMA align", {"filters": ["h4_up", "ema_aligned"]}),
    ("Bullish + RSI rising", {"entry_filters": ["bullish", "rsi_rising"]}),
    ("Delay1 + phân kỳ H4", {"entry_strategy": "touch_div"}),
    ("Confirm delay1 nến", {"entry_strategy": "confirm_delay1"}),
    ("TP 3R", {"take_profit_r": 3.0}),
    ("TP 2R", {"take_profit_r": 2.0}),
    ("TP vùng RSI đối diện", {"take_profit_mode": "rsi_zone"}),
    ("SL 20 pip", {"stop_loss_pips": 20.0}),
    ("SL 30 pip", {"stop_loss_pips": 30.0}),
    ("SL swing", {"sl_mode": "swing"}),
    ("SL ATR 1.5x", {"sl_mode": "atr", "stop_loss_atr_mult": 1.5}),
    ("Horizon 72 nến", {"max_bars": 72}),
    ("Horizon 24 nến", {"max_bars": 24}),
    ("Skip1 + bullish", {"sl_skip_one": True, "sequential_trades": True, "entry_filters": ["bullish"]}),
    ("Skip1 + deep RSI", {"sl_skip_one": True, "sequential_trades": True, "entry_filters": ["deep_touch"]}),
    ("Delay 2", {"entry_strategy": "delay_2"}),
    ("Delay 3", {"entry_strategy": "delay_3"}),
]


def run_improvement_sweep(df=None, split_date: str = SPLIT_DATE) -> dict[str, Any]:
    df = df if df is not None else load_candles()
    events = analyze_zone_touches(df, ZoneConfig(horizon_bars=48))["events"]
    div = find_rsi_divergences(df)

    rows: list[dict[str, Any]] = []
    for label, kw in CANDIDATES:
        params = {**BASE, "divergences": div, **kw}
        full = backtest_setup(df, events, **params)
        if full.get("trades", 0) < MIN_TRADES:
            continue
        wf = walk_forward_setup(df, events, split_date=split_date, **params)
        stable = wf["comparison"]["stable"]
        exp = full.get("expectancy_r", 0.0)
        pf = full.get("profit_factor", 0.0)
        score = exp * pf * (1.25 if stable else 0.45)
        rows.append({
            "label": label,
            "trades": full.get("trades"),
            "win_rate": full.get("win_rate"),
            "expectancy_r": exp,
            "profit_factor": pf,
            "total_pips": full.get("total_pips"),
            "stable": stable,
            "train_exp": wf["train"].get("expectancy_r", 0),
            "test_exp": wf["test"].get("expectancy_r", 0),
            "score": round(score, 3),
            "params": kw,
        })

    rows.sort(key=lambda r: (r["score"], r["expectancy_r"], r["total_pips"]), reverse=True)
    baseline = next((r for r in rows if r["label"].startswith("★ Baseline")), rows[0] if rows else None)
    best = rows[0] if rows else None
    return {
        "baseline": baseline,
        "best": best,
        "top10": rows[:10],
        "all": rows,
        "tested": len(CANDIDATES),
        "passed": len(rows),
    }


if __name__ == "__main__":
    out = run_improvement_sweep()
    b = out["baseline"]
    print(f"=== IMPROVEMENT SWEEP ({out['passed']}/{out['tested']} đủ {MIN_TRADES} lệnh) ===\n")
    if b:
        print(f"Baseline: {b['trades']} lệnh exp={b['expectancy_r']:+.2f}R PF={b['profit_factor']:.2f} pip={b['total_pips']:+.0f}\n")
    print(f"{'#':<3} {'Phương án':<32} {'n':>4} {'WR':>5} {'Exp':>7} {'PF':>5} {'Pip':>7} {'WF':>4}")
    print("-" * 78)
    for i, r in enumerate(out["top10"], 1):
        wf = "✓" if r["stable"] else "✗"
        mark = " ←" if r["label"].startswith("★") else ""
        print(
            f"{i:<3} {r['label']:<32} {r['trades']:>4} {r['win_rate']:>4.0f}% "
            f"{r['expectancy_r']:>+6.2f}R {r['profit_factor']:>5.2f} {r['total_pips']:>+7.0f} {wf:>4}{mark}"
        )
    if out["best"] and b and out["best"]["label"] != b["label"]:
        d = out["best"]["expectancy_r"] - b["expectancy_r"]
        print(f"\nBest: {out['best']['label']} (Δ exp {d:+.2f}R vs baseline)")
