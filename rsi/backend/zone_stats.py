"""RSI zone touch statistics & reversal probability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


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

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "ZoneConfig":
        if not d:
            return cls()
        cfg = cls()
        for key in ("low", "mid", "high"):
            if key in d and d[key]:
                lo, hi = d[key]
                setattr(cfg, key, (float(lo), float(hi)))
        for key in ("horizon_bars", "cooldown_bars"):
            if key in d and d[key] is not None:
                setattr(cfg, key, int(d[key]))
        if "min_reversal_pips" in d and d["min_reversal_pips"] is not None:
            cfg.min_reversal_pips = float(d["min_reversal_pips"])
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
    else:
        move = close - float(fwd["low"].min())
        bars = int(fwd["low"].values.argmin()) + 1
        adverse = float(fwd["high"].max()) - close

    move_pips = _pip_move(move)
    reversed_ok = move_pips >= min_pips and move > adverse
    return {
        "reversed": bool(reversed_ok),
        "move_pips": round(move_pips, 1),
        "bars_to_extreme": bars,
        "adverse_pips": round(_pip_move(adverse), 1),
    }


def _exit_zone_signal(df: pd.DataFrame, i: int, zone: str, band: tuple[float, float], lookback: int) -> bool:
    """RSI exited zone — classic setup trigger."""
    rsi = df["rsi14_h4"].to_numpy(dtype=float)
    if i < 1:
        return False
    cur, prev = float(rsi[i]), float(rsi[i - 1])
    if np.isnan(cur) or np.isnan(prev):
        return False
    lo, hi = band
    start = max(0, i - lookback)
    was_in = any(in_band(float(rsi[j]), band) for j in range(start, i) if not np.isnan(rsi[j]))
    if zone == "low":
        return was_in and prev <= hi and cur > hi
    return was_in and prev >= lo and cur < lo


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
            ts = int(row.name.timestamp()) if hasattr(row.name, "timestamp") else int(row["timestamp"] // 1000)
            rsi_val = float(row["rsi14_h4"])
            trend_up = bool(row.get("trend_up", False))
            h4_up = bool(row.get("h4_trend_up", False))

            rev = {"reversed": False, "move_pips": 0.0}
            if meta["reversal_dir"] != "neutral":
                rev = _measure_reversal(df, i, meta["reversal_dir"], cfg.horizon_bars, cfg.min_reversal_pips)

            exit_sig = _exit_zone_signal(df, i, zone_id, band, lookback=80) if zone_id != "mid" else False
            aligned = (zone_id == "low" and trend_up) or (zone_id == "high" and not trend_up)

            ev = {
                "time": ts,
                "zone": zone_id,
                "rsi": round(rsi_val, 1),
                "close": float(row["close"]),
                "reversed": rev["reversed"],
                "move_pips": rev.get("move_pips", 0),
                "bars_to_extreme": rev.get("bars_to_extreme"),
                "trend_up": trend_up,
                "h4_trend_up": h4_up,
                "ema_aligned": aligned,
                "exit_signal": exit_sig,
            }
            events.append(ev)
            all_events.append(ev)

        reversed_n = sum(1 for e in events if e["reversed"])
        aligned_rev = sum(1 for e in events if e["reversed"] and e["ema_aligned"])
        aligned_n = sum(1 for e in events if e["ema_aligned"])
        exit_n = sum(1 for e in events if e["exit_signal"])

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
            "exit_signals": exit_n,
        }

    # Combined conditions for trade setup probability
    conditions = _build_condition_matrix(df, cfg, all_events)

    return {
        "zones": summary,
        "events": all_events,
        "conditions": conditions,
        "config": {
            "horizon_bars": cfg.horizon_bars,
            "min_reversal_pips": cfg.min_reversal_pips,
            "cooldown_bars": cfg.cooldown_bars,
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

    def rate(subset: list[dict[str, Any]]) -> float:
        if not subset:
            return 0.0
        return sum(1 for e in subset if e["reversed"]) / len(subset) * 100

    rows = [
        {
            "condition": "Chạm vùng hỗ trợ RSI (28–32)",
            "samples": len(low_events),
            "reversal_rate": round(rate(low_events), 1),
            "note": "Giá thường bật lên sau khi RSI H4 vào vùng quá bán",
        },
        {
            "condition": "+ EMA50 > EMA200 (xu hướng H1 tăng)",
            "samples": sum(1 for e in low_events if e["ema_aligned"]),
            "reversal_rate": round(rate([e for e in low_events if e["ema_aligned"]]), 1),
            "note": "Lọc long theo xu hướng H1",
        },
        {
            "condition": "+ H4 trend up (EMA50 H4 > EMA200 H4)",
            "samples": sum(1 for e in low_events if e["h4_trend_up"]),
            "reversal_rate": round(rate([e for e in low_events if e["h4_trend_up"]]), 1),
            "note": "Khung lớn cùng chiều long",
        },
        {
            "condition": "Chạm vùng kháng cự RSI (68–72)",
            "samples": len(high_events),
            "reversal_rate": round(rate(high_events), 1),
            "note": "Giá thường giảm sau khi RSI H4 vào vùng quá mua",
        },
        {
            "condition": "+ EMA50 < EMA200 (xu hướng H1 giảm)",
            "samples": sum(1 for e in high_events if e["ema_aligned"]),
            "reversal_rate": round(rate([e for e in high_events if e["ema_aligned"]]), 1),
            "note": "Lọc short theo xu hướng H1",
        },
        {
            "condition": "+ H4 trend down",
            "samples": sum(1 for e in high_events if not e["h4_trend_up"]),
            "reversal_rate": round(rate([e for e in high_events if not e["h4_trend_up"]]), 1),
            "note": "Khung lớn cùng chiều short",
        },
        {
            "condition": f"Đảo chiều trong {cfg.horizon_bars} nến H1 (≥{cfg.min_reversal_pips} pip)",
            "samples": len([e for e in events if e["zone"] != "mid"]),
            "reversal_rate": round(rate([e for e in events if e["zone"] != "mid"]), 1),
            "note": "Tiêu chí đo lường đảo chiều",
        },
    ]
    return rows
