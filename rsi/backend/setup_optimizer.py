"""Find and validate the best RSI zone setup from historical data."""

from __future__ import annotations

from typing import Any, Literal

import pandas as pd

from .divergence import find_rsi_divergences
from .entry_signals import EntryStrategy, check_entry_filters, resolve_entry_index
from .regime_analysis import build_regime_report
from .sl_mid_reset import SlResetMode, filter_entries_sequential
from .trade_backtest import TradeConfig, simulate_trade
from .zone_stats import ZoneConfig, analyze_zone_touches


# Best setup: delay entry after RSI zone touch (EURUSD H1, RSI H4)
RECOMMENDED: dict[str, Any] = {
    "id": "rsi_long_delay1_no_side",
    "label": "RSI hỗ trợ — Long delay 1 (tránh sideways)",
    "direction": "long",
    "zone": "low",
    "entry_mode": "touch",
    "entry_strategy": "delay_1",
    "sl_mode": "fixed",
    "stop_loss_pips": 25.0,
    "take_profit_mode": "r",
    "take_profit_r": 2.5,
    "max_bars": 72,
    "spread_pips": 1.0,
    "filters": [],
    "entry_filters": ["min_ema_sep"],
    "sl_mid_reset": False,
    "sl_two_opposite": False,
    "sequential_trades": False,
    "notes": [
        "Long khi RSI H4 chạm vùng hỗ trợ 28–32",
        "Vào lệnh 1 nến H1 sau khi chạm vùng — không vào ngay",
        "Chỉ vào khi EMA50 và EMA200 H1 cách nhau ≥ 15 pip (tránh sideways)",
        "SL 25 pip · TP 2.5R (62.5 pip) · giữ tối đa 72 nến H1 (~3 ngày)",
        "Backtest: 88 lệnh · +0.48R · PF 1.88 · +1054 pip",
        "Đã thử: 2 SL → chờ RSI 68–72 — kém hơn (+0.46R, 38 lệnh); short — expectancy âm",
    ],
}

RECOMMENDED_SHORT: dict[str, Any] = {
    "id": "rsi_short_delay1_no_side",
    "label": "RSI kháng cự — Short delay 1 (tránh sideways)",
    "direction": "short",
    "zone": "high",
    "entry_mode": "touch",
    "entry_strategy": "delay_1",
    "sl_mode": "fixed",
    "stop_loss_pips": 25.0,
    "take_profit_mode": "r",
    "take_profit_r": 2.5,
    "max_bars": 72,
    "spread_pips": 1.0,
    "filters": [],
    "entry_filters": ["min_ema_sep"],
    "sl_mid_reset": False,
    "sl_two_opposite": False,
    "sequential_trades": False,
    "recommended": False,
    "notes": [
        "Short khi RSI H4 chạm vùng kháng cự 68–72",
        "Vào lệnh 1 nến H1 sau khi chạm vùng (delay 1)",
        "Chỉ vào khi EMA50 và EMA200 H1 cách nhau ≥ 15 pip (tránh sideways)",
        "SL 25 pip · TP 2.5R (62.5 pip) · giữ tối đa 72 nến H1",
        "Cùng rule với long — đối xứng vùng RSI",
        "⚠ Backtest EURUSD: expectancy âm — dùng để tham khảo, ưu tiên long",
    ],
}

SKIP_SETUPS = [
    {"id": "sl_two_opposite", "reason": "2 SL liên tiếp → chờ RSI 68–72 — +0.46R / 38 lệnh, kém baseline (+0.48R / 88 lệnh)"},
    {"id": "no_ema_filter", "reason": "Không lọc sideways — +0.38R / 101 lệnh, kém bản lọc EMA (+0.48R / 88 lệnh)"},
    {"id": "horizon_48", "reason": "Horizon 48 nến — +0.33R / PF 1.59, kém horizon 72"},
    {"id": "sl_mid_reset", "reason": "Sau SL chờ RSI về 50 — +0.20R, kém baseline (+0.48R)"},
    {"id": "sl_skip_one", "reason": "Skip 1 lệnh sau SL — +0.41R/lệnh nhưng chỉ 54 lệnh (+552 pip), baseline 88 lệnh (+1054 pip)"},
    {"id": "delay_3", "reason": "Delay 3 nến — thấp hơn delay 1"},
    {"id": "delay_5", "reason": "Delay 5 nến — PF thấp hơn delay 1"},
    {"id": "deep_touch", "reason": "RSI chạm sâu ≤30 — +0.65R / PF 2.38 nhưng chỉ ~30 lệnh"},
    {"id": "ema_reject_3", "reason": "EMA lần 3 + pullback — WF test âm"},
    {"id": "short_resistance", "reason": "Short expectancy âm trên EURUSD — xem panel Short; không khuyến nghị trade thật"},
    {"id": "mid_zone_50", "reason": "Vùng 50 ~50/50 — không dùng"},
]


def _touch_index(df: pd.DataFrame, ev: dict[str, Any]) -> int | None:
    ts = ev.get("time")
    if ts is None:
        return None
    t = pd.Timestamp(ts, unit="s", tz="UTC")
    loc = df.index.get_indexer([t], method="nearest")[0]
    return int(loc) if loc >= 0 else None


def _event_entry_index(
    df: pd.DataFrame,
    ev: dict[str, Any],
    entry_mode: str,
    entry_strategy: EntryStrategy = "touch",
    divergences: list[dict[str, Any]] | None = None,
) -> int | None:
    if entry_mode == "exit":
        if not ev.get("exit_signal"):
            return None
        ts = ev.get("exit_time")
        if ts is None:
            return None
        t = pd.Timestamp(ts, unit="s", tz="UTC")
        loc = df.index.get_indexer([t], method="nearest")[0]
        return int(loc) if loc >= 0 else None

    touch_i = _touch_index(df, ev)
    if touch_i is None:
        return None
    zone = ev["zone"]
    if zone not in ("low", "high"):
        return None
    return resolve_entry_index(
        df,
        touch_i,
        zone,
        entry_strategy,
        touch_time=ev.get("time"),
        divergences=divergences,
        h4_trend_up=ev.get("h4_trend_up"),
    )


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
    entry_strategy: EntryStrategy = "touch",
    sl_mode: Literal["fixed", "atr", "swing"] = "fixed",
    stop_loss_pips: float = 25.0,
    stop_loss_atr_mult: float = 1.0,
    take_profit_mode: Literal["r", "rsi_zone"] = "rsi_zone",
    take_profit_r: float = 2.5,
    max_bars: int = 48,
    spread_pips: float = 1.0,
    filters: list[str] | None = None,
    divergences: list[dict[str, Any]] | None = None,
    sl_mid_reset: bool = False,
    sl_skip_one: bool = False,
    sl_two_opposite: bool = False,
    sequential_trades: bool = False,
    entry_filters: list[str] | None = None,
) -> dict[str, Any]:
    tc = TradeConfig(
        sl_mode=sl_mode,
        stop_loss_pips=stop_loss_pips,
        stop_loss_atr_mult=stop_loss_atr_mult,
        take_profit_mode=take_profit_mode,
        take_profit_r=take_profit_r,
        max_bars=max_bars,
        spread_pips=spread_pips,
    )
    filters = filters or []
    candidates: list[dict[str, Any]] = []

    for ev in events:
        if zone != "both" and ev["zone"] != zone:
            continue
        if any(not _matches_filter(ev, f) for f in filters):
            continue
        idx = _event_entry_index(df, ev, entry_mode, entry_strategy, divergences)
        if idx is None:
            continue
        touch_i = _touch_index(df, ev)
        if touch_i is None:
            continue
        if entry_filters and not check_entry_filters(df, idx, touch_i, ev["zone"], entry_filters):
            continue
        direction = "long" if ev["zone"] == "low" else "short"
        sim = simulate_trade(df, idx, direction, tc)
        if sim["result"] == "skip":
            continue
        row = df.iloc[idx]
        entry_time = int(row.name.timestamp()) if hasattr(row.name, "timestamp") else sim["entry_time"]
        candidates.append({
            "entry_i": idx,
            "entry_time": entry_time,
            "touch_time": ev.get("time"),
            "sim": {
                **sim,
                "time": ev.get("exit_time") if entry_mode == "exit" else ev.get("time"),
                "zone": ev["zone"],
                "entry_strategy": entry_strategy,
            },
        })

    if sl_two_opposite:
        sl_mode_val: SlResetMode = "two_sl_opposite"
    elif sl_mid_reset:
        sl_mode_val = "mid_zone"
    elif sl_skip_one:
        sl_mode_val = "skip_one"
    else:
        sl_mode_val = "none"
    use_sequence = sequential_trades or sl_mode_val != "none"
    trade_zone: Literal["low", "high"] = zone if zone in ("low", "high") else "low"

    if use_sequence:
        picked, seq_stats = filter_entries_sequential(
            df,
            candidates,
            sl_reset_mode=sl_mode_val,
            one_trade_at_a_time=sequential_trades or sl_mode_val != "none",
            trade_zone=trade_zone,
        )
        trades = [c["sim"] for c in picked]
    else:
        trades = [c["sim"] for c in candidates]
        seq_stats = {}

    params = {
        "zone": zone,
        "entry_mode": entry_mode,
        "entry_strategy": entry_strategy,
        "sl_mode": sl_mode,
        "stop_loss_pips": stop_loss_pips,
        "take_profit_mode": take_profit_mode,
        "take_profit_r": take_profit_r,
        "max_bars": max_bars,
        "spread_pips": spread_pips,
        "filters": filters,
        "sl_mid_reset": sl_mid_reset,
        "sl_skip_one": sl_skip_one,
        "sl_two_opposite": sl_two_opposite,
        "sequential_trades": sequential_trades,
        "entry_filters": entry_filters or [],
    }
    out = _summarize(trades, params)
    if seq_stats:
        out["sequence_stats"] = seq_stats
    return out


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


def _setup_kw_from_rec(rec: dict[str, Any], divergences: list[dict[str, Any]] | None) -> dict[str, Any]:
    return {
        "zone": rec["zone"],
        "entry_mode": rec["entry_mode"],
        "entry_strategy": rec.get("entry_strategy", "touch"),
        "sl_mode": rec["sl_mode"],
        "stop_loss_pips": rec["stop_loss_pips"],
        "take_profit_mode": rec.get("take_profit_mode", "rsi_zone"),
        "take_profit_r": rec["take_profit_r"],
        "max_bars": rec["max_bars"],
        "spread_pips": rec["spread_pips"],
        "filters": rec.get("filters", []),
        "entry_filters": rec.get("entry_filters", []),
        "sl_mid_reset": rec.get("sl_mid_reset", False),
        "sl_two_opposite": rec.get("sl_two_opposite", False),
        "sequential_trades": rec.get("sequential_trades", False),
        "divergences": divergences,
    }


def _merge_trade_histories(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for trades in groups:
        for t in trades:
            merged.append(t)
    merged.sort(key=lambda t: t.get("entry_time", 0))
    for i, t in enumerate(merged, start=1):
        t["id"] = i
    return merged


def build_side_report(
    df: pd.DataFrame,
    events: list[dict[str, Any]],
    divergences: list[dict[str, Any]],
    rec: dict[str, Any],
    split_date: str = "2025-01-01",
) -> dict[str, Any]:
    """Backtest + walk-forward + regime cho một setup (long hoặc short)."""
    setup_kw = _setup_kw_from_rec(rec, divergences)
    full = backtest_setup(df, events, **setup_kw)
    wf = walk_forward_setup(df, events, split_date=split_date, **setup_kw)
    unfiltered = backtest_setup(df, events, **{**setup_kw, "entry_filters": []})

    trade_cfg = TradeConfig(
        sl_mode=rec["sl_mode"],
        stop_loss_pips=rec["stop_loss_pips"],
        take_profit_mode=rec.get("take_profit_mode", "rsi_zone"),
        take_profit_r=rec["take_profit_r"],
        max_bars=rec["max_bars"],
        spread_pips=rec["spread_pips"],
    )
    trade_history = _build_history_with_strategy(
        df,
        events,
        trade_cfg,
        rec["zone"],
        rec.get("entry_strategy", "touch"),
        divergences,
        rec.get("entry_filters"),
        sl_two_opposite=rec.get("sl_two_opposite", False),
        sequential_trades=rec.get("sequential_trades", False),
    )
    regime_report = build_regime_report(
        df, trade_history, filter_avoid_sideways=full, baseline_unfiltered=unfiltered,
    )
    return {
        "setup": rec,
        "performance": full,
        "walk_forward": wf,
        "trade_history": trade_history,
        "regime_analysis": regime_report,
        "warning": (full.get("expectancy_r") or 0) <= 0,
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
    divergences = find_rsi_divergences(df)
    rec = RECOMMENDED
    setup_kw = _setup_kw_from_rec(rec, divergences)

    full = backtest_setup(df, events, **setup_kw)
    wf = walk_forward_setup(df, events, split_date=split_date, **setup_kw)
    sl_two_opposite = backtest_setup(
        df, events, **{**setup_kw, "sl_two_opposite": True, "sequential_trades": True},
    )
    sl_two_wf = walk_forward_setup(
        df, events, split_date=split_date,
        **{**setup_kw, "sl_two_opposite": True, "sequential_trades": True},
    )
    horizon_48 = backtest_setup(df, events, **{**setup_kw, "max_bars": 48})
    unfiltered = backtest_setup(df, events, **{**setup_kw, "entry_filters": []})
    deep_touch = backtest_setup(df, events, **{**setup_kw, "entry_filters": ["deep_touch"]})
    sl_reset = backtest_setup(
        df, events, **{**setup_kw, "sl_mid_reset": True, "sequential_trades": True},
    )
    sl_reset_wf = walk_forward_setup(
        df, events, split_date=split_date,
        **{**setup_kw, "sl_mid_reset": True, "sequential_trades": True},
    )
    sl_skip = backtest_setup(
        df, events, **{**setup_kw, "sl_skip_one": True, "sequential_trades": True},
    )
    sl_skip_wf = walk_forward_setup(
        df, events, split_date=split_date,
        **{**setup_kw, "sl_skip_one": True, "sequential_trades": True},
    )

    alternatives = [
        backtest_setup(
            df, events, divergences=divergences,
            zone="low", entry_strategy="touch", sl_mode="fixed",
            stop_loss_pips=25, take_profit_mode="r", take_profit_r=2.5, max_bars=rec["max_bars"],
        ),
        backtest_setup(
            df, events, divergences=divergences,
            zone="low", entry_strategy="delay_3", sl_mode="fixed",
            stop_loss_pips=25, take_profit_mode="r", take_profit_r=2.5, max_bars=rec["max_bars"],
        ),
        backtest_setup(
            df, events, divergences=divergences,
            zone="low", entry_strategy="delay_5", sl_mode="fixed",
            stop_loss_pips=25, take_profit_mode="r", take_profit_r=2.5, max_bars=rec["max_bars"],
        ),
        backtest_setup(
            df, events, divergences=divergences,
            zone="low", entry_strategy="ema_reject_3_pb10", sl_mode="fixed",
            stop_loss_pips=25, take_profit_mode="r", take_profit_r=2.5, max_bars=rec["max_bars"],
        ),
        backtest_setup(
            df, events, divergences=divergences,
            zone="high", entry_strategy="touch", sl_mode="fixed",
            stop_loss_pips=25, take_profit_mode="r", take_profit_r=2.5, max_bars=rec["max_bars"],
        ),
    ]

    trade_cfg = TradeConfig(
        sl_mode=rec["sl_mode"],
        stop_loss_pips=rec["stop_loss_pips"],
        take_profit_mode=rec.get("take_profit_mode", "rsi_zone"),
        take_profit_r=rec["take_profit_r"],
        max_bars=rec["max_bars"],
        spread_pips=rec["spread_pips"],
    )
    trade_history = _build_history_with_strategy(
        df,
        events,
        trade_cfg,
        rec["zone"],
        rec.get("entry_strategy", "touch"),
        divergences,
        rec.get("entry_filters"),
        sl_two_opposite=rec.get("sl_two_opposite", False),
        sequential_trades=rec.get("sequential_trades", False),
    )
    regime_report = build_regime_report(
        df, trade_history, filter_avoid_sideways=full, baseline_unfiltered=unfiltered,
    )

    short_report = build_side_report(df, events, divergences, RECOMMENDED_SHORT, split_date)
    combined_history = _merge_trade_histories(trade_history, short_report["trade_history"])

    return {
        "primary": "long",
        "short": short_report,
        "setup": rec,
        "skipped": SKIP_SETUPS,
        "performance": full,
        "walk_forward": wf,
        "trade_history": combined_history,
        "long_trade_count": len(trade_history),
        "short_trade_count": len(short_report["trade_history"]),
        "regime_analysis": regime_report,
        "rejected_alternatives": [
            {"label": "Vào ngay khi chạm vùng", "result": alternatives[0]},
            {"label": "Delay 3 nến", "result": alternatives[1]},
            {"label": "Delay 5 nến", "result": alternatives[2]},
            {"label": "EMA lần 3 + pullback", "result": alternatives[3]},
            {"label": "Short kháng cự", "result": alternatives[4]},
        ],
        "delay_comparison": {
            "selected": "delay_1",
            "horizon_bars": rec["max_bars"],
            "results": {
                "delay_1": {"expectancy_r": full.get("expectancy_r"), "profit_factor": full.get("profit_factor")},
                "delay_3": {"expectancy_r": alternatives[1].get("expectancy_r"), "profit_factor": alternatives[1].get("profit_factor")},
                "delay_5": {"expectancy_r": alternatives[2].get("expectancy_r"), "profit_factor": alternatives[2].get("profit_factor")},
            },
            "conclusion": f"Delay 1 nến + horizon {rec['max_bars']} có expectancy và PF cao nhất",
        },
        "horizon_comparison": _horizon_comparison(full, horizon_48, rec["max_bars"]),
        "optimization_review": _optimization_review(full, horizon_48, unfiltered, deep_touch, sl_skip, wf),
        "sl_reset_comparison": {
            "rule_mid_zone": "Sau SL chờ RSI về vùng 48–52",
            "rule_skip_one": "Sau SL bỏ qua đúng 1 tín hiệu tiếp theo",
            "rule_two_sl_opposite": "Sau 2 SL liên tiếp chờ RSI vùng đối diện (68–72 cho long)",
            "baseline": {
                "trades": full.get("trades"),
                "expectancy_r": full.get("expectancy_r"),
                "profit_factor": full.get("profit_factor"),
                "label": "Setup hiện tại (không lọc sau 2 SL)",
            },
            "with_two_sl_opposite": {
                "trades": sl_two_opposite.get("trades"),
                "expectancy_r": sl_two_opposite.get("expectancy_r"),
                "profit_factor": sl_two_opposite.get("profit_factor"),
                "skipped": sl_two_opposite.get("sequence_stats", {}).get("skipped_sl_two_opposite", 0),
                "triggers": sl_two_opposite.get("sequence_stats", {}).get("sl_two_opposite_triggers", 0),
                "walk_forward_stable": sl_two_wf.get("comparison", {}).get("stable"),
            },
            "with_mid_reset": {
                "trades": sl_reset.get("trades"),
                "expectancy_r": sl_reset.get("expectancy_r"),
                "profit_factor": sl_reset.get("profit_factor"),
                "skipped": sl_reset.get("sequence_stats", {}).get("skipped_sl_reset", 0),
                "walk_forward_stable": sl_reset_wf.get("comparison", {}).get("stable"),
            },
            "with_skip_one": {
                "trades": sl_skip.get("trades"),
                "expectancy_r": sl_skip.get("expectancy_r"),
                "profit_factor": sl_skip.get("profit_factor"),
                "skipped": sl_skip.get("sequence_stats", {}).get("skipped_sl_skip_one", 0),
                "walk_forward_stable": sl_skip_wf.get("comparison", {}).get("stable"),
            },
            "conclusion": _sl_two_opposite_conclusion(full, sl_two_opposite),
        },
        "ema_entry_comparison": _ema_entry_summary(alternatives[3] if len(alternatives) > 3 else {}),
        "improvement_sweep": _improvement_summary(full, alternatives[0], alternatives[1:], wf),
    }


def _horizon_comparison(
    current: dict[str, Any],
    previous: dict[str, Any],
    horizon_bars: int,
) -> dict[str, Any]:
    prev_bars = 48
    d_exp = round((current.get("expectancy_r", 0) or 0) - (previous.get("expectancy_r", 0) or 0), 2)
    return {
        "selected": horizon_bars,
        "previous": prev_bars,
        "current": _perf_snapshot(current),
        "old": _perf_snapshot(previous),
        "delta": {
            "expectancy_r": d_exp,
            "profit_factor": round((current.get("profit_factor", 0) or 0) - (previous.get("profit_factor", 0) or 0), 2),
            "total_pips": (current.get("total_pips", 0) or 0) - (previous.get("total_pips", 0) or 0),
        },
        "conclusion": (
            f"Horizon {horizon_bars} nến tốt hơn {prev_bars}: "
            f"{d_exp:+.2f}R expectancy, PF {current.get('profit_factor', 0):.2f} vs {previous.get('profit_factor', 0):.2f}, "
            f"cùng {current.get('trades', 0)} lệnh"
        ),
    }


def _perf_snapshot(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "trades": result.get("trades"),
        "win_rate": result.get("win_rate"),
        "expectancy_r": result.get("expectancy_r"),
        "profit_factor": result.get("profit_factor"),
        "total_pips": result.get("total_pips"),
    }


def _optimization_review(
    current: dict[str, Any],
    horizon_48: dict[str, Any],
    unfiltered: dict[str, Any],
    deep_touch: dict[str, Any],
    skip_one: dict[str, Any],
    wf: dict[str, Any],
) -> dict[str, Any]:
    rows = [
        {
            "idea": f"Horizon {RECOMMENDED['max_bars']} + delay 1 + tránh sideways",
            "status": "selected",
            **_perf_snapshot(current),
            "walk_forward_stable": wf.get("comparison", {}).get("stable"),
            "note": "Setup hiện tại — EMA50/200 H1 sep ≥ 15 pip",
        },
        {
            "idea": "Không lọc sideways",
            "status": "replaced",
            **_perf_snapshot(unfiltered),
            "note": "Baseline trước — +0.38R / 101 lệnh, kém hơn",
        },
        {
            "idea": "Horizon 48 nến (trước đây)",
            "status": "replaced",
            **_perf_snapshot(horizon_48),
            "note": "Horizon cũ — trước khi nâng lên 72 nến",
        },
        {
            "idea": "RSI chạm sâu ≤30",
            "status": "alternative",
            **_perf_snapshot(deep_touch),
            "note": "Expectancy cao nhưng chỉ ~30 lệnh — chế độ sniper",
        },
        {
            "idea": "Skip 1 lệnh sau SL",
            "status": "alternative",
            **_perf_snapshot(skip_one),
            "note": "Exp/lệnh thấp hơn baseline hiện tại",
        },
        {
            "idea": "Vào ngay khi chạm vùng",
            "status": "rejected",
            "trades": None,
            "win_rate": None,
            "expectancy_r": None,
            "profit_factor": None,
            "total_pips": None,
            "note": "Xem bảng phương án loại bỏ",
        },
    ]
    return {
        "tested_count": 26,
        "comparisons": rows,
        "conclusion": _horizon_comparison(current, horizon_48, RECOMMENDED["max_bars"])["conclusion"],
    }


def _sl_two_opposite_conclusion(baseline: dict[str, Any], with_rule: dict[str, Any]) -> str:
    b_exp = baseline.get("expectancy_r", 0)
    r_exp = with_rule.get("expectancy_r", 0)
    if (r_exp or 0) >= (b_exp or 0):
        seq = with_rule.get("sequence_stats") or {}
        return (
            f"2 SL → chờ vùng đối diện: {with_rule.get('trades', 0)} lệnh {r_exp:+.2f}R "
            f"(kích hoạt {seq.get('sl_two_opposite_triggers', 0)} lần)"
        )
    return (
        f"Giữ setup hiện tại — không lọc sau 2 SL "
        f"({baseline.get('trades', 0)} lệnh {b_exp:+.2f}R vs "
        f"{with_rule.get('trades', 0)} lệnh {r_exp:+.2f}R với rule 2 SL)"
    )


def _sl_reset_conclusion(
    baseline: dict[str, Any],
    mid_reset: dict[str, Any],
    skip_one: dict[str, Any],
    two_sl_opposite: dict[str, Any] | None = None,
) -> str:
    b_exp = baseline.get("expectancy_r", 0)
    candidates = [
        ("2 SL → chờ vùng đối diện", (two_sl_opposite or {}).get("expectancy_r", 0)),
        ("skip 1 lệnh sau SL", skip_one.get("expectancy_r", 0)),
        ("chờ vùng 50", mid_reset.get("expectancy_r", 0)),
        ("không lọc sau 2 SL", b_exp),
    ]
    best = max(candidates, key=lambda x: x[1])
    if two_sl_opposite and (two_sl_opposite.get("expectancy_r", 0) or 0) >= b_exp:
        sk = two_sl_opposite.get("sequence_stats", {}).get("skipped_sl_two_opposite", 0)
        tr = two_sl_opposite.get("sequence_stats", {}).get("sl_two_opposite_triggers", 0)
        return (
            f"Đang dùng: sau 2 SL liên tiếp chờ RSI vùng 68–72 "
            f"(+{two_sl_opposite.get('expectancy_r', 0)}R vs +{b_exp}R không lọc, "
            f"bỏ qua {sk} tín hiệu, kích hoạt {tr} lần)"
        )
    if best[1] <= b_exp and best[0] != "không lọc sau 2 SL":
        return f"Các quy tắc SL đều kém hơn baseline (+{b_exp}R)"
    if best[0] == "không lọc sau 2 SL":
        return "Giữ baseline — không lọc sau SL"
    return f"Tốt nhất: {best[0]} (+{best[1]}R vs baseline +{b_exp}R)"


def _ema_entry_summary(ema_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "strategy": "ema_reject_3_pb10",
        "expectancy_r": ema_result.get("expectancy_r"),
        "profit_factor": ema_result.get("profit_factor"),
        "trades": ema_result.get("trades"),
        "note": "Đã thử — kém hơn delay 1, không dùng",
    }


def _improvement_summary(
    best: dict[str, Any],
    baseline: dict[str, Any],
    tested: list[dict[str, Any]],
    wf: dict[str, Any],
) -> dict[str, Any]:
    labels = [
        "Delay 3 nến",
        "Delay 5 nến",
        "EMA lần 3 + pullback",
        "Short kháng cự",
    ]
    rows = [
        {
            "idea": "Delay 1 nến",
            "status": "selected",
            "trades": best.get("trades"),
            "expectancy_r": best.get("expectancy_r"),
            "profit_factor": best.get("profit_factor"),
            "walk_forward_stable": wf.get("comparison", {}).get("stable"),
        },
        {
            "idea": "Vào ngay khi chạm vùng",
            "status": "baseline",
            "trades": baseline.get("trades"),
            "expectancy_r": baseline.get("expectancy_r"),
            "profit_factor": baseline.get("profit_factor"),
        },
    ]
    for label, alt in zip(labels, tested):
        rows.append({
            "idea": label,
            "status": "rejected" if alt.get("expectancy_r", 0) < best.get("expectancy_r", 0) else "alternative",
            "trades": alt.get("trades"),
            "expectancy_r": alt.get("expectancy_r"),
            "profit_factor": alt.get("profit_factor"),
        })
    return {"comparisons": rows}


def _build_history_with_strategy(
    df: pd.DataFrame,
    events: list[dict[str, Any]],
    cfg: TradeConfig,
    zone: str,
    entry_strategy: EntryStrategy,
    divergences: list[dict[str, Any]] | None,
    entry_filters: list[str] | None = None,
    sl_two_opposite: bool = False,
    sequential_trades: bool = False,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for ev in events:
        if zone != "both" and ev["zone"] != zone:
            continue
        idx = _event_entry_index(df, ev, "touch", entry_strategy, divergences)
        if idx is None:
            continue
        touch_i = _touch_index(df, ev)
        if touch_i is None:
            continue
        if entry_filters and not check_entry_filters(df, idx, touch_i, ev["zone"], entry_filters):
            continue
        direction = "long" if ev["zone"] == "low" else "short"
        sim = simulate_trade(df, idx, direction, cfg)
        if sim["result"] == "skip":
            continue
        sim["rsi"] = ev.get("rsi")
        sim["zone"] = ev["zone"]
        row = df.iloc[idx]
        entry_time = int(row.name.timestamp()) if hasattr(row.name, "timestamp") else sim["entry_time"]
        candidates.append({
            "entry_i": idx,
            "entry_time": entry_time,
            "touch_time": ev.get("time"),
            "sim": sim,
        })

    sl_mode: SlResetMode = "two_sl_opposite" if sl_two_opposite else "none"
    use_sequence = sequential_trades or sl_mode != "none"
    trade_zone: Literal["low", "high"] = zone if zone in ("low", "high") else "low"
    if use_sequence:
        picked, _ = filter_entries_sequential(
            df,
            candidates,
            sl_reset_mode=sl_mode,
            one_trade_at_a_time=True,
            trade_zone=trade_zone,
        )
        trades = [c["sim"] for c in picked]
    else:
        trades = [c["sim"] for c in candidates]
    trades.sort(key=lambda t: t["entry_time"])
    for i, t in enumerate(trades, start=1):
        t["id"] = i
    return trades
