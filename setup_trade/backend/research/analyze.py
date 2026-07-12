from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from backend.core.config import PERIODS_PATH, load_json
from backend.core.folds import require_label_period
from backend.data.labels import list_setups
from backend.indicators import add_indicators
from backend.data.loader import load_candles, slice_period
from backend.strategy.rsi_ema_v1.engine import RsiEmaV1Strategy


def _label_outcome_stats(setups: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_setup: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"trades": 0, "wins": 0, "pnl": 0.0, "long": 0, "short": 0}
    )
    for s in setups:
        sid = s.get("setup_id") or "unknown"
        by_setup[sid]["trades"] += 1
        by_setup[sid][s.get("direction", "long")] += 1
        outcome = s.get("outcome") or {}
        pnl = float(outcome.get("pnl_pips", 0))
        by_setup[sid]["pnl"] += pnl
        if outcome.get("win"):
            by_setup[sid]["wins"] += 1

    stats: dict[str, dict[str, Any]] = {}
    for sid, raw in by_setup.items():
        n = raw["trades"]
        stats[sid] = {
            "trades": n,
            "wins": raw["wins"],
            "win_rate": round(raw["wins"] / n, 3) if n else 0.0,
            "total_pips": round(raw["pnl"], 1),
            "expectancy_pips": round(raw["pnl"] / n, 2) if n else 0.0,
            "long": raw["long"],
            "short": raw["short"],
        }
    return stats


def _recommendations(
    by_setup: dict[str, dict[str, Any]],
    *,
    min_samples: int = 5,
    wr_threshold: float = 0.38,
) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    for sid, s in by_setup.items():
        if s["trades"] < min_samples:
            recs.append(
                {
                    "setup_id": sid,
                    "action": "keep",
                    "reason": f"Chưa đủ mẫu ({s['trades']} < {min_samples})",
                    "samples": s["trades"],
                    "win_rate": s["win_rate"],
                }
            )
            continue
        if s["win_rate"] < wr_threshold:
            recs.append(
                {
                    "setup_id": sid,
                    "action": "disable",
                    "reason": f"WR {s['win_rate']:.1%} < {wr_threshold:.0%} trên {s['trades']} mẫu",
                    "samples": s["trades"],
                    "win_rate": s["win_rate"],
                }
            )
        else:
            recs.append(
                {
                    "setup_id": sid,
                    "action": "keep",
                    "reason": f"WR {s['win_rate']:.1%} đạt ngưỡng",
                    "samples": s["trades"],
                    "win_rate": s["win_rate"],
                }
            )
    return recs


def analyze_alignment(label_period: str) -> dict[str, Any]:
    setups = list_setups(period=label_period)
    if not setups:
        return {"alignment_ratio": 0.0, "total": 0, "aligned": 0, "by_setup": {}}

    df = add_indicators(slice_period(load_candles(), label_period))
    strategy = RsiEmaV1Strategy()
    aligned = 0
    by_setup_align: dict[str, dict[str, int]] = {}

    for s in setups:
        sid = s.get("setup_id") or "unknown"
        by_setup_align.setdefault(sid, {"total": 0, "aligned": 0})
        by_setup_align[sid]["total"] += 1
        if s.get("discretionary_override"):
            continue
        ts = pd.Timestamp(s["entry_time"])
        gate = strategy.validate_label(df, ts, s["direction"], s.get("setup_id"))
        if gate["valid"]:
            aligned += 1
            by_setup_align[sid]["aligned"] += 1

    total = len([s for s in setups if not s.get("discretionary_override")])
    return {
        "alignment_ratio": round(aligned / total, 3) if total else 0.0,
        "total": total,
        "aligned": aligned,
        "by_setup": {
            k: {**v, "ratio": round(v["aligned"] / v["total"], 3) if v["total"] else 0}
            for k, v in by_setup_align.items()
        },
    }


def analyze_period(label_period: str, *, apply_disable: bool = False) -> dict[str, Any]:
    require_label_period(label_period)
    cfg = load_json(PERIODS_PATH)
    rules = cfg.get("rules") or {}
    target = int(rules.get("target_setups_per_label_year", 50))
    min_align = float(rules.get("min_label_alignment_ratio", 0.7))

    setups = list_setups(period=label_period)
    alignment = analyze_alignment(label_period)
    by_setup = _label_outcome_stats(setups)
    recommendations = _recommendations(by_setup)

    applied = None
    if apply_disable:
        from backend.strategy.rsi_ema_v1.store import apply_setup_recommendations

        applied = apply_setup_recommendations(recommendations)

    return {
        "status": "ok",
        "label_period": label_period,
        "label_count": len(setups),
        "target_setups": target,
        "target_met": len(setups) >= target,
        "alignment": alignment,
        "alignment_ok": alignment["alignment_ratio"] >= min_align,
        "min_alignment_required": min_align,
        "by_setup": by_setup,
        "recommendations": recommendations,
        "applied_disable": applied,
        "warnings": _warnings(len(setups), target, alignment["alignment_ratio"], min_align),
    }


def _warnings(count: int, target: int, align: float, min_align: float) -> list[str]:
    msgs: list[str] = []
    if count < target:
        msgs.append(f"Cần thêm {target - count} setup để đạt mục tiêu {target}/năm")
    if count < 50:
        msgs.append("Dưới 50 lệnh — ý nghĩa thống kê hạn chế")
    if align < min_align:
        msgs.append(f"Alignment {align:.1%} < {min_align:.0%} — cần label lại hoặc kiểm tra gate")
    return msgs
