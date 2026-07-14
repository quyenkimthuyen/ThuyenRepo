"""RSI zone touch statistics & reversal probability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd

from .divergence import find_rsi_divergences, summarize_divergences
from .trade_backtest import TradeConfig, backtest_entries


DEFAULT_BANDS = {
    "low": (28.0, 32.0),
    "mid": (48.0, 52.0),
    "high": (68.0, 72.0),
}


@dataclass
class ZoneConfig:
    low: tuple[float, float] = DEFAULT_BANDS["low"]
    mid: tuple[float, float] = DEFAULT_BANDS["mid"]
    high: tuple[float, float] = DEFAULT_BANDS["high"]
    horizon_bars: int = 24
    min_reversal_pips: float = 20.0
    cooldown_bars: int = 12
    exit_lookahead_bars: int = 48
    sl_mode: Literal["fixed", "atr"] = "fixed"
    stop_loss_pips: float = 20.0
    stop_loss_atr_mult: float = 1.0
    take_profit_r: float = 2.0
    spread_pips: float = 1.0

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "ZoneConfig":
        if not d:
            return cls()
        cfg = cls()
        for key in ("low", "mid", "high"):
            if key in d and d[key]:
                lo, hi = d[key]
                setattr(cfg, key, (float(lo), float(hi)))
        for key in ("horizon_bars", "cooldown_bars", "exit_lookahead_bars"):
            if key in d and d[key] is not None:
                setattr(cfg, key, int(d[key]))
        for key in ("min_reversal_pips", "stop_loss_pips", "stop_loss_atr_mult", "take_profit_r", "spread_pips"):
            if key in d and d[key] is not None:
                setattr(cfg, key, float(d[key]))
        if "sl_mode" in d and d["sl_mode"] in ("fixed", "atr"):
            cfg.sl_mode = d["sl_mode"]
        return cfg


def in_band(value: float, band: tuple[float, float]) -> bool:
    return band[0] <= value <= band[1]


def _pip_move(price_delta: float) -> float:
    return abs(price_delta) * 10_000


def _zone_touch_events(
    df: pd.DataFrame,
    zone: str,
    band: tuple[float, float],
    cooldown: int,
) -> list[int]:
    """Return bar indices where RSI first enters the zone."""
    rsi = df["rsi14_h4"].to_numpy(dtype=float)
    events: list[int] = []
    last = -cooldown - 1
    for i in range(1, len(rsi)):
        if np.isnan(rsi[i]) or np.isnan(rsi[i - 1]):
            continue
        entered = in_band(rsi[i], band) and not in_band(rsi[i - 1], band)
        touched = False
        if zone == "low":
            touched = in_band(rsi[i], band) and rsi[i - 1] > band[1]
        elif zone == "high":
            touched = in_band(rsi[i], band) and rsi[i - 1] < band[0]
        if (entered or touched) and i - last > cooldown:
            events.append(i)
            last = i
    return events


def _measure_reversal(
    df: pd.DataFrame,
    i: int,
    direction: str,
    horizon: int,
    min_pips: float,
) -> dict[str, Any]:
    """Measure if price reversed after RSI zone touch at bar i."""
    if i >= len(df) - 1:
        return {"reversed": False, "move_pips": 0.0, "bars_to_extreme": None}

    row = df.iloc[i]
    close = float(row["close"])
    fwd = df.iloc[i + 1 : i + 1 + horizon]
    if fwd.empty:
        return {"reversed": False, "move_pips": 0.0, "bars_to_extreme": None}

    if direction == "bullish":
        move = float(fwd["high"].max()) - close
        bars = int(fwd["high"].values.argmax()) + 1
        adverse = close - float(fwd["low"].min())
        mfe = move
        mae = adverse
    else:
        move = close - float(fwd["low"].min())
        bars = int(fwd["low"].values.argmin()) + 1
        adverse = float(fwd["high"].max()) - close
        mfe = move
        mae = adverse

    move_pips = _pip_move(move)
    mae_pips = _pip_move(mae)
    mfe_pips = _pip_move(mfe)
    reversed_ok = move_pips >= min_pips and move > adverse
    return {
        "reversed": bool(reversed_ok),
        "move_pips": round(move_pips, 1),
        "mae_pips": round(mae_pips, 1),
        "mfe_pips": round(mfe_pips, 1),
        "bars_to_extreme": bars,
        "adverse_pips": round(mae_pips, 1),
    }


def _find_exit_after_touch(
    df: pd.DataFrame,
    touch_i: int,
    zone: str,
    band: tuple[float, float],
    max_bars: int,
) -> dict[str, Any] | None:
    """First bar after touch where RSI exits the zone (entry trigger)."""
    rsi = df["rsi14_h4"].to_numpy(dtype=float)
    lo, hi = band
    end = min(len(rsi) - 1, touch_i + max_bars)

    for j in range(touch_i + 1, end + 1):
        if np.isnan(rsi[j]) or np.isnan(rsi[j - 1]):
            continue
        cur, prev = float(rsi[j]), float(rsi[j - 1])
        was_in = any(in_band(float(rsi[k]), band) for k in range(touch_i, j) if not np.isnan(rsi[k]))
        if not was_in:
            continue
        if zone == "low" and prev <= hi and cur > hi:
            return {"exit_i": j, "bars_to_exit": j - touch_i}
        if zone == "high" and prev >= lo and cur < lo:
            return {"exit_i": j, "bars_to_exit": j - touch_i}
    return None


def _bar_timestamp(df: pd.DataFrame, i: int) -> int:
    row = df.iloc[i]
    if hasattr(row.name, "timestamp"):
        return int(row.name.timestamp())
    return int(row["timestamp"] // 1000)


def analyze_zone_touches(df: pd.DataFrame, cfg: ZoneConfig | None = None) -> dict[str, Any]:
    cfg = cfg or ZoneConfig()
    pip = cfg.min_reversal_pips / 10_000
    _ = pip  # reserved for future ATR-based threshold

    zones = {
        "low": {"band": cfg.low, "reversal_dir": "bullish", "label": "Hỗ trợ (28–32)"},
        "high": {"band": cfg.high, "reversal_dir": "bearish", "label": "Kháng cự (68–72)"},
        "mid": {"band": cfg.mid, "reversal_dir": "neutral", "label": "Vùng 50 (48–52)"},
    }

    all_events: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}

    for zone_id, meta in zones.items():
        band = meta["band"]
        indices = _zone_touch_events(df, zone_id, band, cfg.cooldown_bars)
        events: list[dict[str, Any]] = []

        for i in indices:
            row = df.iloc[i]
            ts = _bar_timestamp(df, i)
            rsi_val = float(row["rsi14_h4"])
            trend_up = bool(row.get("trend_up", False))
            h4_up = bool(row.get("h4_trend_up", False))

            rev_touch = {"reversed": False, "move_pips": 0.0, "mae_pips": 0.0, "mfe_pips": 0.0}
            if meta["reversal_dir"] != "neutral":
                rev_touch = _measure_reversal(df, i, meta["reversal_dir"], cfg.horizon_bars, cfg.min_reversal_pips)

            exit_info: dict[str, Any] | None = None
            rev_exit = {"reversed": False, "move_pips": 0.0, "mae_pips": 0.0, "mfe_pips": 0.0}
            if zone_id != "mid":
                exit_info = _find_exit_after_touch(df, i, zone_id, band, cfg.exit_lookahead_bars)
                if exit_info and meta["reversal_dir"] != "neutral":
                    rev_exit = _measure_reversal(
                        df,
                        exit_info["exit_i"],
                        meta["reversal_dir"],
                        cfg.horizon_bars,
                        cfg.min_reversal_pips,
                    )

            aligned = (zone_id == "low" and trend_up) or (zone_id == "high" and not trend_up)

            ev: dict[str, Any] = {
                "time": ts,
                "zone": zone_id,
                "rsi": round(rsi_val, 1),
                "close": float(row["close"]),
                "reversed": rev_touch["reversed"],
                "move_pips": rev_touch.get("move_pips", 0),
                "mae_pips": rev_touch.get("mae_pips", 0),
                "mfe_pips": rev_touch.get("mfe_pips", 0),
                "bars_to_extreme": rev_touch.get("bars_to_extreme"),
                "trend_up": trend_up,
                "h4_trend_up": h4_up,
                "ema_aligned": aligned,
                "exit_signal": exit_info is not None,
                "bars_to_exit": exit_info["bars_to_exit"] if exit_info else None,
                "exit_reversed": rev_exit["reversed"] if exit_info else False,
                "exit_move_pips": rev_exit.get("move_pips", 0) if exit_info else 0,
                "exit_mae_pips": rev_exit.get("mae_pips", 0) if exit_info else 0,
                "exit_mfe_pips": rev_exit.get("mfe_pips", 0) if exit_info else 0,
                "exit_bars_to_extreme": rev_exit.get("bars_to_extreme") if exit_info else None,
            }
            if exit_info:
                exit_row = df.iloc[exit_info["exit_i"]]
                ev["exit_time"] = _bar_timestamp(df, exit_info["exit_i"])
                ev["exit_rsi"] = round(float(exit_row["rsi14_h4"]), 1)
                ev["exit_close"] = float(exit_row["close"])
            events.append(ev)
            all_events.append(ev)

        reversed_n = sum(1 for e in events if e["reversed"])
        exit_events = [e for e in events if e["exit_signal"]]
        exit_reversed_n = sum(1 for e in exit_events if e["exit_reversed"])
        aligned_rev = sum(1 for e in events if e["reversed"] and e["ema_aligned"])
        aligned_n = sum(1 for e in events if e["ema_aligned"])
        exit_aligned = [e for e in exit_events if e["ema_aligned"]]
        exit_aligned_rev = sum(1 for e in exit_aligned if e["exit_reversed"])

        trade_events = [e for e in events if meta["reversal_dir"] != "neutral"]
        exit_trade = exit_events

        summary[zone_id] = {
            "label": meta["label"],
            "band": list(band),
            "touches": len(events),
            "reversals": reversed_n,
            "reversal_rate": round(reversed_n / len(events) * 100, 1) if events else 0.0,
            "avg_move_pips": round(
                float(np.mean([e["move_pips"] for e in events if e.get("move_pips")])) if events and meta["reversal_dir"] != "neutral" else 0.0,
                1,
            ),
            "with_ema_alignment": aligned_n,
            "reversal_when_aligned": aligned_rev,
            "aligned_reversal_rate": round(aligned_rev / aligned_n * 100, 1) if aligned_n else 0.0,
            "exit_signals": len(exit_events),
            "exit_reversals": exit_reversed_n,
            "exit_reversal_rate": round(exit_reversed_n / len(exit_events) * 100, 1) if exit_events else 0.0,
            "avg_exit_move_pips": round(
                float(np.mean([e["exit_move_pips"] for e in exit_events])) if exit_events and meta["reversal_dir"] != "neutral" else 0.0,
                1,
            ),
            "avg_bars_to_exit": round(
                float(np.mean([e["bars_to_exit"] for e in exit_events if e["bars_to_exit"] is not None])) if exit_events else 0.0,
                1,
            ),
            "exit_aligned_reversal_rate": round(exit_aligned_rev / len(exit_aligned) * 100, 1) if exit_aligned else 0.0,
            "avg_mae_pips": round(float(np.mean([e["mae_pips"] for e in trade_events])) if trade_events else 0.0, 1),
            "avg_mfe_pips": round(float(np.mean([e["mfe_pips"] for e in trade_events])) if trade_events else 0.0, 1),
            "avg_exit_mae_pips": round(float(np.mean([e["exit_mae_pips"] for e in exit_trade])) if exit_trade else 0.0, 1),
            "avg_exit_mfe_pips": round(float(np.mean([e["exit_mfe_pips"] for e in exit_trade])) if exit_trade else 0.0, 1),
        }

    # Combined conditions for trade setup probability
    conditions = _build_condition_matrix(df, cfg, all_events)

    trade_cfg = TradeConfig(
        sl_mode=cfg.sl_mode,
        stop_loss_pips=cfg.stop_loss_pips,
        stop_loss_atr_mult=cfg.stop_loss_atr_mult,
        take_profit_r=cfg.take_profit_r,
        max_bars=cfg.horizon_bars,
        spread_pips=cfg.spread_pips,
    )
    backtest = {
        "touch": backtest_entries(df, all_events, trade_cfg, entry_mode="touch"),
        "exit": backtest_entries(df, all_events, trade_cfg, entry_mode="exit"),
    }
    mae_mfe = _build_mae_mfe_report(all_events, cfg)
    divergences = find_rsi_divergences(
        df,
        horizon_bars=cfg.horizon_bars,
        min_reversal_pips=cfg.min_reversal_pips,
    )

    return {
        "zones": summary,
        "events": all_events,
        "conditions": conditions,
        "backtest": backtest,
        "mae_mfe": mae_mfe,
        "divergence_stats": summarize_divergences(divergences),
        "config": {
            "horizon_bars": cfg.horizon_bars,
            "min_reversal_pips": cfg.min_reversal_pips,
            "cooldown_bars": cfg.cooldown_bars,
            "exit_lookahead_bars": cfg.exit_lookahead_bars,
            "sl_mode": cfg.sl_mode,
            "stop_loss_pips": cfg.stop_loss_pips,
            "stop_loss_atr_mult": cfg.stop_loss_atr_mult,
            "take_profit_r": cfg.take_profit_r,
            "spread_pips": cfg.spread_pips,
            "bands": {k: list(getattr(cfg, k)) for k in ("low", "mid", "high")},
        },
    }


def _build_condition_matrix(
    df: pd.DataFrame,
    cfg: ZoneConfig,
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Rank conditions that improve reversal odds at RSI zones."""
    low_events = [e for e in events if e["zone"] == "low"]
    high_events = [e for e in events if e["zone"] == "high"]

    def rate(subset: list[dict[str, Any]], key: str = "reversed") -> float:
        if not subset:
            return 0.0
        return sum(1 for e in subset if e[key]) / len(subset) * 100

    low_exit = [e for e in low_events if e["exit_signal"]]
    high_exit = [e for e in high_events if e["exit_signal"]]

    rows = [
        {
            "condition": "Chạm vùng hỗ trợ RSI (28–32) — vào ngay khi chạm",
            "samples": len(low_events),
            "reversal_rate": round(rate(low_events), 1),
            "note": "Entry tại nến chạm vùng",
        },
        {
            "condition": "Hỗ trợ + thoát vùng (RSI > 32 sau chạm)",
            "samples": len(low_exit),
            "reversal_rate": round(rate(low_exit, "exit_reversed"), 1),
            "note": "Entry khi RSI rời vùng quá bán — trigger thực tế",
        },
        {
            "condition": "+ EMA50 > EMA200 (xu hướng H1 tăng)",
            "samples": sum(1 for e in low_events if e["ema_aligned"]),
            "reversal_rate": round(rate([e for e in low_events if e["ema_aligned"]]), 1),
            "note": "Lọc long theo xu hướng H1 (entry chạm vùng)",
        },
        {
            "condition": "+ H4 trend up (EMA50 H4 > EMA200 H4)",
            "samples": sum(1 for e in low_events if e["h4_trend_up"]),
            "reversal_rate": round(rate([e for e in low_events if e["h4_trend_up"]]), 1),
            "note": "Khung lớn cùng chiều long (entry chạm vùng)",
        },
        {
            "condition": "Chạm vùng kháng cự RSI (68–72) — vào ngay khi chạm",
            "samples": len(high_events),
            "reversal_rate": round(rate(high_events), 1),
            "note": "Entry tại nến chạm vùng",
        },
        {
            "condition": "Kháng cự + thoát vùng (RSI < 68 sau chạm)",
            "samples": len(high_exit),
            "reversal_rate": round(rate(high_exit, "exit_reversed"), 1),
            "note": "Entry khi RSI rời vùng quá mua",
        },
        {
            "condition": "+ EMA50 < EMA200 (xu hướng H1 giảm)",
            "samples": sum(1 for e in high_events if e["ema_aligned"]),
            "reversal_rate": round(rate([e for e in high_events if e["ema_aligned"]]), 1),
            "note": "Lọc short theo xu hướng H1 (entry chạm vùng)",
        },
        {
            "condition": "+ H4 trend down",
            "samples": sum(1 for e in high_events if not e["h4_trend_up"]),
            "reversal_rate": round(rate([e for e in high_events if not e["h4_trend_up"]]), 1),
            "note": "Khung lớn cùng chiều short (entry chạm vùng)",
        },
        {
            "condition": f"Đảo chiều trong {cfg.horizon_bars} nến H1 (≥{cfg.min_reversal_pips} pip)",
            "samples": len([e for e in events if e["zone"] != "mid"]),
            "reversal_rate": round(rate([e for e in events if e["zone"] != "mid"]), 1),
            "note": "Tiêu chí đo lường — entry chạm vùng",
        },
        {
            "condition": f"Thoát vùng trong {cfg.exit_lookahead_bars} nến sau chạm",
            "samples": len(low_exit) + len(high_exit),
            "reversal_rate": round(
                (sum(1 for e in low_exit + high_exit if e["exit_reversed"]) / (len(low_exit) + len(high_exit)) * 100)
                if low_exit or high_exit
                else 0.0,
                1,
            ),
            "note": "So sánh entry thoát vùng vs chạm vùng",
        },
    ]
    rows.extend(_build_combined_conditions(low_events, high_events))
    return rows


def _build_combined_conditions(
    low_events: list[dict[str, Any]],
    high_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """AND-combined filters ranked by exit-entry reversal rate."""

    def rate_exit(subset: list[dict[str, Any]]) -> tuple[float, int]:
        exit_only = [e for e in subset if e.get("exit_signal")]
        if not exit_only:
            return 0.0, 0
        pct = sum(1 for e in exit_only if e["exit_reversed"]) / len(exit_only) * 100
        return round(pct, 1), len(exit_only)

    def rate_touch(subset: list[dict[str, Any]]) -> tuple[float, int]:
        if not subset:
            return 0.0, 0
        pct = sum(1 for e in subset if e["reversed"]) / len(subset) * 100
        return round(pct, 1), len(subset)

    combos: list[dict[str, Any]] = [
        {
            "group": "Long — entry thoát vùng",
            "condition": "Hỗ trợ + thoát vùng",
            "filter": lambda e: e.get("exit_signal"),
            "events": low_events,
            "use_exit": True,
        },
        {
            "group": "Long — entry thoát vùng",
            "condition": "+ H4 trend up",
            "filter": lambda e: e.get("exit_signal") and e.get("h4_trend_up"),
            "events": low_events,
            "use_exit": True,
        },
        {
            "group": "Long — entry thoát vùng",
            "condition": "+ EMA H1 aligned",
            "filter": lambda e: e.get("exit_signal") and e.get("ema_aligned"),
            "events": low_events,
            "use_exit": True,
        },
        {
            "group": "Long — entry thoát vùng",
            "condition": "+ H4 up + EMA H1 aligned",
            "filter": lambda e: e.get("exit_signal") and e.get("h4_trend_up") and e.get("ema_aligned"),
            "events": low_events,
            "use_exit": True,
        },
        {
            "group": "Short — entry thoát vùng",
            "condition": "Kháng cự + thoát vùng",
            "filter": lambda e: e.get("exit_signal"),
            "events": high_events,
            "use_exit": True,
        },
        {
            "group": "Short — entry thoát vùng",
            "condition": "+ H4 trend down",
            "filter": lambda e: e.get("exit_signal") and not e.get("h4_trend_up"),
            "events": high_events,
            "use_exit": True,
        },
        {
            "group": "Short — entry thoát vùng",
            "condition": "+ EMA H1 aligned",
            "filter": lambda e: e.get("exit_signal") and e.get("ema_aligned"),
            "events": high_events,
            "use_exit": True,
        },
        {
            "group": "Short — entry thoát vùng",
            "condition": "+ H4 down + EMA H1 aligned",
            "filter": lambda e: e.get("exit_signal") and not e.get("h4_trend_up") and e.get("ema_aligned"),
            "events": high_events,
            "use_exit": True,
        },
        {
            "group": "Long — entry chạm vùng",
            "condition": "Hỗ trợ + H4 up + EMA aligned",
            "filter": lambda e: e.get("h4_trend_up") and e.get("ema_aligned"),
            "events": low_events,
            "use_exit": False,
        },
        {
            "group": "Short — entry chạm vùng",
            "condition": "Kháng cự + H4 down + EMA aligned",
            "filter": lambda e: not e.get("h4_trend_up") and e.get("ema_aligned"),
            "events": high_events,
            "use_exit": False,
        },
    ]

    rows: list[dict[str, Any]] = []
    for c in combos:
        subset = [e for e in c["events"] if c["filter"](e)]
        if c["use_exit"]:
            pct, n = rate_exit(subset)
            note = f"{c['group']} — đo tại entry thoát vùng"
        else:
            pct, n = rate_touch(subset)
            note = f"{c['group']} — đo tại entry chạm vùng"
        rows.append({
            "condition": c["condition"],
            "samples": n,
            "reversal_rate": pct,
            "note": note,
            "group": c["group"],
            "combined": True,
        })
    return rows


def _build_mae_mfe_report(events: list[dict[str, Any]], cfg: ZoneConfig) -> dict[str, Any]:
    """MAE/MFE aggregates — helps pick stop-loss distance."""
    sl_candidates = [15, 20, 25, 30]
    trade_events = [e for e in events if e["zone"] in ("low", "high")]
    exit_events = [e for e in trade_events if e.get("exit_signal")]

    def agg(subset: list[dict[str, Any]], mae_key: str, mfe_key: str) -> dict[str, float]:
        if not subset:
            return {"avg_mae": 0.0, "avg_mfe": 0.0, "median_mae": 0.0, "median_mfe": 0.0}
        mae_vals = [e[mae_key] for e in subset]
        mfe_vals = [e[mfe_key] for e in subset]
        return {
            "avg_mae": round(float(np.mean(mae_vals)), 1),
            "avg_mfe": round(float(np.mean(mfe_vals)), 1),
            "median_mae": round(float(np.median(mae_vals)), 1),
            "median_mfe": round(float(np.median(mfe_vals)), 1),
        }

    def sl_survival(subset: list[dict[str, Any]], mae_key: str, sl: float) -> float:
        if not subset:
            return 0.0
        survived = sum(1 for e in subset if e[mae_key] <= sl)
        return round(survived / len(subset) * 100, 1)

    touch_agg = agg(trade_events, "mae_pips", "mfe_pips")
    exit_agg = agg(exit_events, "exit_mae_pips", "exit_mfe_pips")

    return {
        "horizon_bars": cfg.horizon_bars,
        "touch": {
            **touch_agg,
            "samples": len(trade_events),
            "sl_survival": {str(sl): sl_survival(trade_events, "mae_pips", sl) for sl in sl_candidates},
        },
        "exit": {
            **exit_agg,
            "samples": len(exit_events),
            "sl_survival": {str(sl): sl_survival(exit_events, "exit_mae_pips", sl) for sl in sl_candidates},
        },
        "sl_candidates": sl_candidates,
    }
