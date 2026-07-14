"""Find and validate the best RSI zone setup from historical data."""

from __future__ import annotations

from typing import Any, Literal

import pandas as pd

from .trade_backtest import TradeConfig, build_trade_history, simulate_trade
from .zone_stats import ZoneConfig, _bar_timestamp, analyze_zone_touches


# Winning setup from full-data sweep (EURUSD H1, RSI H4, 2023–2026)
RECOMMENDED = {
    "id": "rsi_zone_touch",
    "label": "RSI chạm vùng — Long hỗ trợ / Short kháng cự",
    "direction": "zone_based",
    "zone": "both",
    "entry_mode": "touch",
    "sl_mode": "fixed",
    "stop_loss_pips": 25.0,
    "take_profit_r": 2.5,
    "max_bars": 48,
    "spread_pips": 1.0,
    "filters": [],
    "notes": [
        "Long khi RSI H4 chạm vùng hỗ trợ 28–32",
        "Short khi RSI H4 chạm vùng kháng cự 68–72",
        "Vào lệnh ngay khi chạm vùng — không chờ thoát vùng",
        "SL 25 pip · TP khi RSI chạm vùng đối diện · giữ tối đa 48 nến H1",
        "Vùng 50 không có edge — bỏ qua",
    ],
}

SKIP_SETUPS = [
    {"id": "mid_zone_50", "reason": "Tiếp diễn vs đảo chiều ~50/50 — không dùng"},
    {"id": "exit_entry", "reason": "Entry thoát vùng kém hơn chạm vùng cho long"},
    {"id": "h1_ema_filter", "reason": "Mẫu quá nhỏ, không cải thiện ổn định so với H4"},
]


def _event_entry_index(df: pd.DataFrame, ev: dict[str, Any], entry_mode: str) -> int | None:
    if entry_mode == "exit":
        if not ev.get("exit_signal"):
            return None
        ts = ev.get("exit_time")
    else:
        ts = ev.get("time")
    if ts is None:
        return None
    t = pd.Timestamp(ts, unit="s", tz="UTC")
    loc = df.index.get_indexer([t], method="nearest")[0]
    return int(loc) if loc >= 0 else None


def _matches_filter(ev: dict[str, Any], filt: str) -> bool:
    if filt == "zone_low":
        return ev["zone"] == "low"
    if filt == "zone_high":
        return ev["zone"] == "high"
    if filt == "h4_up":
        return ev.get("h4_trend_up", False)
    if filt == "h4_down":
        return not ev.get("h4_trend_up", True)
    if filt == "ema_aligned":
        return ev.get("ema_aligned", False)
    return True


def backtest_setup(
    df: pd.DataFrame,
    events: list[dict[str, Any]],
    *,
    zone: Literal["low", "high", "both"] = "low",
    entry_mode: Literal["touch", "exit"] = "touch",
    sl_mode: Literal["fixed", "atr"] = "fixed",
    stop_loss_pips: float = 25.0,
    stop_loss_atr_mult: float = 1.0,
    take_profit_r: float = 2.5,
    max_bars: int = 48,
    spread_pips: float = 1.0,
    filters: list[str] | None = None,
) -> dict[str, Any]:
    tc = TradeConfig(
        sl_mode=sl_mode,
        stop_loss_pips=stop_loss_pips,
        stop_loss_atr_mult=stop_loss_atr_mult,
        take_profit_r=take_profit_r,
        max_bars=max_bars,
        spread_pips=spread_pips,
    )
    filters = filters or []
    trades: list[dict[str, Any]] = []

    for ev in events:
        if zone != "both" and ev["zone"] != zone:
            continue
        if any(not _matches_filter(ev, f) for f in filters):
            continue
        idx = _event_entry_index(df, ev, entry_mode)
        if idx is None:
            continue
        direction = "long" if ev["zone"] == "low" else "short"
        sim = simulate_trade(df, idx, direction, tc)
        sim["time"] = ev.get("exit_time") if entry_mode == "exit" else ev.get("time")
        sim["zone"] = ev["zone"]
        trades.append(sim)

    return _summarize(trades, {
        "zone": zone,
        "entry_mode": entry_mode,
        "sl_mode": sl_mode,
        "stop_loss_pips": stop_loss_pips,
        "take_profit_mode": tc.take_profit_mode,
        "take_profit_r": take_profit_r,
        "max_bars": max_bars,
        "spread_pips": spread_pips,
        "filters": filters,
    })


def _summarize(trades: list[dict[str, Any]], params: dict[str, Any]) -> dict[str, Any]:
    if not trades:
        return {"trades": 0, "valid": False, "params": params}

    wins = [t for t in trades if t["result"] == "win"]
    losses = [t for t in trades if t["result"] == "loss"]
    r_vals = [t["r_multiple"] for t in trades]
    pnl = [t["pnl_pips"] for t in trades]
    loss_sum = sum(t["pnl_pips"] for t in losses)
    pf = abs(sum(t["pnl_pips"] for t in wins)) / abs(loss_sum) if losses and loss_sum != 0 else 0.0

    return {
        "valid": True,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "expectancy_r": round(sum(r_vals) / len(r_vals), 2),
        "profit_factor": round(pf, 2),
        "total_pips": round(sum(pnl), 1),
        "avg_pips": round(sum(pnl) / len(pnl), 1),
        "params": params,
    }


def walk_forward_setup(
    df: pd.DataFrame,
    events: list[dict[str, Any]],
    split_date: str,
    **setup_kw: Any,
) -> dict[str, Any]:
    split_ts = pd.Timestamp(split_date, tz="UTC")
    train_df = df[df.index < split_ts]
    test_df = df[df.index >= split_ts]
    train_ev = [e for e in events if pd.Timestamp(e["time"], unit="s", tz="UTC") < split_ts]
    test_ev = [e for e in events if pd.Timestamp(e["time"], unit="s", tz="UTC") >= split_ts]

    train = backtest_setup(train_df, train_ev, **setup_kw)
    test = backtest_setup(test_df, test_ev, **setup_kw)
    d_e = round(test.get("expectancy_r", 0) - train.get("expectancy_r", 0), 2)
    d_wr = round(test.get("win_rate", 0) - train.get("win_rate", 0), 1)

    return {
        "split_date": split_date,
        "train": train,
        "test": test,
        "comparison": {
            "expectancy_r_delta": d_e,
            "win_rate_delta": d_wr,
            "stable": test.get("expectancy_r", 0) > 0 and train.get("expectancy_r", 0) > 0,
        },
    }


def build_recommended_report(df: pd.DataFrame, cfg: ZoneConfig | None = None, split_date: str = "2025-01-01") -> dict[str, Any]:
    """Full report for the validated winning setup."""
    cfg = cfg or ZoneConfig(
        horizon_bars=48,
        stop_loss_pips=25.0,
        take_profit_r=2.5,
    )
    stats = analyze_zone_touches(df, cfg)
    events = stats["events"]
    rec = RECOMMENDED

    full = backtest_setup(
        df,
        events,
        zone="both",
        entry_mode="touch",
        sl_mode="fixed",
        stop_loss_pips=rec["stop_loss_pips"],
        take_profit_r=rec["take_profit_r"],
        max_bars=rec["max_bars"],
        spread_pips=rec["spread_pips"],
        filters=[],
    )
    wf = walk_forward_setup(
        df,
        events,
        split_date=split_date,
        zone="both",
        entry_mode="touch",
        sl_mode="fixed",
        stop_loss_pips=rec["stop_loss_pips"],
        take_profit_r=rec["take_profit_r"],
        max_bars=rec["max_bars"],
        spread_pips=rec["spread_pips"],
        filters=[],
    )

    # Compare rejected alternatives (for transparency)
    alternatives = [
        backtest_setup(df, events, zone="high", entry_mode="touch",
                       stop_loss_pips=25, take_profit_r=2.5, max_bars=48),
        backtest_setup(df, events, zone="low", entry_mode="exit",
                       stop_loss_pips=25, take_profit_r=2.5, max_bars=48),
        backtest_setup(df, events, zone="both", entry_mode="touch",
                       stop_loss_pips=20, take_profit_r=2.0, max_bars=24),
    ]

    trade_cfg = TradeConfig(
        sl_mode="fixed",
        stop_loss_pips=rec["stop_loss_pips"],
        take_profit_r=rec["take_profit_r"],
        max_bars=rec["max_bars"],
        spread_pips=rec["spread_pips"],
    )
    trade_history = build_trade_history(df, events, trade_cfg, zone="both", entry_mode="touch")

    return {
        "setup": rec,
        "skipped": SKIP_SETUPS,
        "performance": full,
        "walk_forward": wf,
        "trade_history": trade_history,
        "rejected_alternatives": [
            {"label": "Short kháng cự (touch)", "result": alternatives[0]},
            {"label": "Long thoát vùng", "result": alternatives[1]},
            {"label": "Cả hai vùng SL20 · TP vùng RSI đối diện", "result": alternatives[2]},
        ],
    }
