from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text

from .config import STRATEGY_PATH
from .labels import load_setups
from .tags import infer_tags
from .rsi_h4_strategy import TAG_BREAK_RETEST, TAG_EXTREME_BOUNCE
from .tag_matcher import (
    DEFAULT_MIN_SIMILARITY,
    build_feature_stats,
    build_setup_index,
    build_tag_signatures,
)
from .pipeline import PIPELINE_FLOW, pipeline_status
from .bar_annotations import annotations_as_learning_samples, load_bar_annotations
from .detection_config import load_bar_detection_config
from .sequence_tags import build_sequence_signatures

MIN_TAGGED_RATIO = 0.5
MIN_TAG_SAMPLES = 2
MIN_TAG_DIRECTION_SAMPLES = 2
MIN_TAG_WIN_RATE = 0.45


def _json_float(value: Any, digits: int = 3) -> float | None:
    """Return a JSON-safe rounded float; pandas can produce NaN for empty groups."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(num):
        return None
    return round(num, digits)


def _feature_frame(setups: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for s in setups:
        if s.get("result") not in ("win", "loss"):
            continue
        f = s.get("features") or {}
        tags = infer_tags(s)
        rows.append(
            {
                "win": 1 if s["result"] == "win" else 0,
                "direction_long": 1 if s["direction"] == "long" else 0,
                "dist_ema50_pips": float(f.get("dist_ema50_pips", 0)),
                "dist_ema50_abs": abs(float(f.get("dist_ema50_pips", 0))),
                "h4_trend_up": 1 if f.get("h4_trend_up", f.get("trend_up")) else 0,
                "trend_up": 1 if f.get("trend_up") else 0,
                "close_above_ema50": 1 if f.get("close_above_ema50") else 0,
                "close_above_ema200": 1 if f.get("close_above_ema200") else 0,
                "planned_rr": float(s.get("planned_rr", 2)),
                "tags": ",".join(sorted(tags)),
            }
        )
    return pd.DataFrame(rows)


def _slice_direction(df: pd.DataFrame, direction: str) -> pd.DataFrame:
    mask = 1 if direction == "long" else 0
    return df[df["direction_long"] == mask]


def _best_bool_threshold(wins: pd.DataFrame, losses: pd.DataFrame, col: str) -> bool | None:
    if wins.empty and losses.empty:
        return None
    best_val = None
    best_score = -1.0
    for val in (0, 1):
        w = int((wins[col] == val).sum()) if not wins.empty else 0
        l = int((losses[col] == val).sum()) if not losses.empty else 0
        total = w + l
        if total < 2:
            continue
        score = w / total
        if score > best_score:
            best_score = score
            best_val = bool(val)
    if best_score < 0.52:
        return None
    return best_val


def _loss_exclusions(wins: pd.DataFrame, losses: pd.DataFrame) -> list[dict[str, Any]]:
    exclusions: list[dict[str, Any]] = []
    if losses.empty:
        return exclusions

    if not wins.empty:
        w_dist = float(wins["dist_ema50_abs"].mean())
        l_dist = float(losses["dist_ema50_abs"].mean())
        if l_dist > w_dist * 1.25 and len(losses) >= 2:
            threshold = round((w_dist + l_dist) / 2, 1)
            exclusions.append(
                {
                    "feature": "dist_ema50_abs",
                    "op": ">",
                    "value": threshold,
                    "reason": "loss thường xa EMA50 hơn win",
                }
            )

    return exclusions


def _rules_for_direction(subset: pd.DataFrame, direction: str) -> dict[str, Any]:
    wins = subset[subset["win"] == 1]
    losses = subset[subset["win"] == 0]

    if wins.empty:
        return {"enabled": False, "reason": f"Không có setup {direction} thắng trong train"}

    trend_up = _best_bool_threshold(wins, losses, "trend_up")
    above50 = _best_bool_threshold(wins, losses, "close_above_ema50")
    above200 = _best_bool_threshold(wins, losses, "close_above_ema200")

    rule: dict[str, Any] = {
        "enabled": True,
        "exclude": _loss_exclusions(wins, losses),
    }
    if direction == "long":
        rule["h4_rsi_above"] = 50
    else:
        rule["h4_rsi_below"] = 50
    if trend_up is not None:
        rule["trend_up"] = trend_up if direction == "long" else (not trend_up)
    if above50 is not None:
        rule["close_above_ema50"] = above50 if direction == "long" else (not above50)
    if above200 is not None:
        rule["close_above_ema200"] = above200

    if not wins.empty:
        dist_cap = float(wins["dist_ema50_abs"].quantile(0.75)) + 8
        if losses.empty or dist_cap < float(losses["dist_ema50_abs"].quantile(0.25)):
            rule["max_dist_ema50_pips"] = round(dist_cap, 1)

    return rule


def _rules_from_win_loss(df: pd.DataFrame) -> dict[str, Any]:
    rules: dict[str, Any] = {}
    for direction in ("long", "short"):
        subset = _slice_direction(df, direction)
        if subset.empty:
            rules[direction] = {"enabled": False, "reason": "Không có setup"}
            continue
        rules[direction] = _rules_for_direction(subset, direction)
    return rules


def _tag_coverage(setups: list[dict[str, Any]]) -> dict[str, Any]:
    labeled = [s for s in setups if s.get("result") in ("win", "loss")]
    tagged = [s for s in labeled if infer_tags(s)]
    total = len(labeled)
    tagged_count = len(tagged)
    return {
        "total": total,
        "tagged": tagged_count,
        "untagged": total - tagged_count,
        "ratio": round(tagged_count / total, 3) if total else 0.0,
    }


def _setups_for_tag(setups: list[dict[str, Any]], tag: str) -> list[dict[str, Any]]:
    return [
        s
        for s in setups
        if tag in infer_tags(s) and s.get("result") in ("win", "loss")
    ]


def _build_tag_profiles(
    train: list[dict[str, Any]], tag_info: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    avoid = set(tag_info.get("avoid_tags", []))

    for row in tag_info.get("tags", []):
        tag = row["tag"]
        base = {
            "tag": tag,
            "win_rate": row["win_rate"],
            "total": row["total"],
            "win": row["win"],
            "loss": row["loss"],
        }

        if tag in avoid:
            profiles[tag] = {
                **base,
                "enabled": False,
                "reason": "Win rate quá thấp — không dùng profile này",
            }
            continue

        if row["total"] < MIN_TAG_SAMPLES:
            profiles[tag] = {
                **base,
                "enabled": False,
                "reason": f"Cần ≥{MIN_TAG_SAMPLES} setup cho tag '{tag}'",
            }
            continue

        if row["win_rate"] < MIN_TAG_WIN_RATE and row["total"] >= MIN_TAG_SAMPLES:
            profiles[tag] = {
                **base,
                "enabled": False,
                "reason": f"Win rate tag '{tag}' dưới {int(MIN_TAG_WIN_RATE * 100)}%",
            }
            continue

        tag_setups = _setups_for_tag(train, tag)
        tag_df = _feature_frame(tag_setups)
        direction_rules: dict[str, Any] = {}
        for direction in ("long", "short"):
            subset = _slice_direction(tag_df, direction)
            if len(subset) < MIN_TAG_DIRECTION_SAMPLES:
                direction_rules[direction] = {
                    "enabled": False,
                    "reason": f"Cần ≥{MIN_TAG_DIRECTION_SAMPLES} setup {direction}",
                }
                continue
            if subset[subset["win"] == 1].empty:
                direction_rules[direction] = {
                    "enabled": False,
                    "reason": f"Không có win {direction} cho tag '{tag}'",
                }
                continue
            rule = _rules_for_direction(subset, direction)
            rule["tag"] = tag
            direction_rules[direction] = rule

        enabled = any(r.get("enabled") for r in direction_rules.values())
        profiles[tag] = {
            **base,
            "enabled": enabled,
            "reason": None if enabled else f"Chưa đủ setup theo hướng cho tag '{tag}'",
            "rules": direction_rules,
            "risk": compute_risk_from_labels(tag_setups),
        }

    return profiles


def _enabled_tag_profiles(profiles: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [p for p in profiles.values() if p.get("enabled")]


def _resolve_rule_mode(
    coverage: dict[str, Any],
    profiles: dict[str, dict[str, Any]],
    signatures: dict[str, dict[str, Any]],
) -> str:
    if coverage["ratio"] >= MIN_TAGGED_RATIO and len(signatures) >= 1:
        return "similarity"
    if coverage["ratio"] < MIN_TAGGED_RATIO:
        return "global"
    if not _enabled_tag_profiles(profiles):
        return "global"
    return "tag_driven"


def _tag_insights(setups: list[dict[str, Any]]) -> dict[str, Any]:
    stats: dict[str, dict[str, int]] = {}
    for s in setups:
        if s.get("result") not in ("win", "loss"):
            continue
        for tag in infer_tags(s):
            bucket = stats.setdefault(tag, {"win": 0, "loss": 0, "total": 0})
            bucket["total"] += 1
            bucket[s["result"]] += 1

    rows = []
    for tag, c in sorted(stats.items(), key=lambda x: -x[1]["total"]):
        wr = c["win"] / c["total"] if c["total"] else 0
        rows.append(
            {
                "tag": tag,
                "win": c["win"],
                "loss": c["loss"],
                "total": c["total"],
                "win_rate": round(wr, 3),
            }
        )

    preferred = [r["tag"] for r in rows if r["total"] >= 2 and r["win_rate"] >= 0.55]
    avoid = [r["tag"] for r in rows if r["total"] >= 2 and r["win_rate"] <= 0.35]
    return {"tags": rows, "preferred_tags": preferred, "avoid_tags": avoid}


def _apply_tag_constraints(
    rules: dict[str, Any], setups: list[dict[str, Any]], tag_info: dict[str, Any]
) -> dict[str, Any]:
    preferred = tag_info.get("preferred_tags", [])
    if not preferred:
        return rules

    for direction in ("long", "short"):
        dr = rules.get(direction, {})
        if not dr.get("enabled"):
            continue
        tagged_wins = [
            s
            for s in setups
            if s.get("direction") == direction
            and s.get("result") == "win"
            and any(t in infer_tags(s) for t in preferred)
        ]
        if len(tagged_wins) < 2:
            continue

        dists = [
            abs(float(s["features"]["dist_ema50_pips"]))
            for s in tagged_wins
            if s.get("features")
        ]
        if dists:
            cap = round(float(np.percentile(dists, 75)) + 5, 1)
            dr["max_dist_ema50_pips"] = min(dr.get("max_dist_ema50_pips", cap), cap)
            dr["preferred_tags"] = preferred

    return rules


def compute_risk_from_labels(setups: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for s in setups:
        if s.get("result") not in ("win", "loss"):
            continue
        f = s.get("features") or {}
        atr = float(f.get("atr14") or 0)
        if atr <= 0:
            continue
        entry = float(s["entry_price"])
        sl = float(s["stop_loss"])
        sl_dist = abs(entry - sl)
        rows.append(
            {
                "direction": s["direction"],
                "sl_atr_mult": sl_dist / atr,
                "planned_rr": float(s.get("planned_rr") or 2),
            }
        )

    if not rows:
        return {
            "mode": "from_labels",
            "default": {"sl_atr_mult": 1.0, "target_rr": 2.0, "tp_atr_mult": 2.0},
        }

    frame = pd.DataFrame(rows)
    default_sl = float(frame["sl_atr_mult"].median())
    default_rr = max(2.5, float(frame["planned_rr"].median()))

    risk: dict[str, Any] = {
        "mode": "from_labels",
        "default": {
            "sl_atr_mult": round(default_sl, 3),
            "target_rr": round(default_rr, 2),
            "tp_atr_mult": round(default_sl * default_rr, 3),
        },
    }

    for direction in ("long", "short"):
        sub = frame[frame["direction"] == direction]
        if len(sub) < 2:
            continue
        sl_m = float(sub["sl_atr_mult"].median())
        rr_m = max(2.5, float(sub["planned_rr"].median()))
        risk[direction] = {
            "sl_atr_mult": round(sl_m, 3),
            "target_rr": round(rr_m, 2),
            "tp_atr_mult": round(sl_m * rr_m, 3),
        }

    return risk


def analyze_patterns(min_setups: int = 5, train_period: str | None = None) -> dict[str, Any]:
    from .periods import default_train_period, filter_setups_for_train, period_config, resolve_period
    from .labels import retag_all_setups
    from .rsi_h4_strategy import build_strategy, strategy_description
    from .indicators import add_indicators
    from .data_service import load_candles

    train_period = resolve_period(train_period or default_train_period())
    retag_all_setups()
    setups = load_setups()
    train = filter_setups_for_train(setups, train_period)
    labeled = [s for s in train if s.get("result") in ("win", "loss")]

    if len(labeled) < min_setups:
        return {
            "status": "insufficient_data",
            "message": f"Cần ít nhất {min_setups} setup train (win/loss). Hiện có {len(labeled)}.",
            "setup_count": len(train),
            "labeled_outcomes": len(labeled),
        }

    win_rate = float(sum(1 for s in labeled if s["result"] == "win") / len(labeled))
    avg_rr = float(train_df_rr(train))

    by_setup: dict[str, dict[str, int]] = {}
    by_tag: dict[str, dict[str, int]] = {}
    for s in labeled:
        st = s.get("strategy_setup") or "unclassified"
        by_setup.setdefault(st, {"win": 0, "loss": 0, "total": 0})
        by_setup[st]["total"] += 1
        by_setup[st][s["result"]] += 1
        for tag in s.get("tags") or []:
            by_tag.setdefault(tag, {"win": 0, "loss": 0, "total": 0})
            by_tag[tag]["total"] += 1
            by_tag[tag][s["result"]] += 1

    tag_rows = []
    for tag, counts in sorted(by_tag.items()):
        wr = counts["win"] / counts["total"] if counts["total"] else 0
        tag_rows.append({"tag": tag, "win_rate": round(wr, 3), **counts})

    train_stats = {
        "win_rate": round(win_rate, 3),
        "avg_rr": round(avg_rr, 2),
        "by_setup": by_setup,
        "by_tag": tag_rows,
    }

    strategy = build_strategy(train_period, train_stats=train_stats)
    strategy.update(
        {
            "train_year": period_config(train_period).get("year"),
            "source_setups": len(train),
            "win_rate_train": round(win_rate, 3),
            "avg_rr_train": round(avg_rr, 2),
            "bar_annotation_count": len(load_bar_annotations()),
            "setups_description": strategy_description(),
        }
    )

    save_strategy(strategy, train_period=train_period)

    return {
        "status": "ok",
        "train_period": train_period,
        "train_year": period_config(train_period).get("year"),
        "pipeline_flow": strategy["pipeline_flow"],
        "pipeline": pipeline_status(),
        "setup_count": len(train),
        "labeled_outcomes": len(labeled),
        "win_rate_train": round(win_rate, 3),
        "avg_rr_train": round(avg_rr, 2),
        "rule_mode": "rsi_h4",
        "strategy": strategy,
        "train_stats": train_stats,
        "setups_description": strategy_description(),
        "tag_insights": {"tags": tag_rows, "preferred_tags": [TAG_BREAK_RETEST, TAG_EXTREME_BOUNCE]},
        "strategy_path": str(STRATEGY_PATH),
    }


def train_df_rr(setups: list[dict[str, Any]]) -> float:
    vals = [s.get("planned_rr", 0) for s in setups if s.get("planned_rr")]
    return float(np.mean(vals)) if vals else 2.0


def strategy_path_for(train_period: str | None = None) -> Path:
    from .periods import default_train_period, resolve_period

    period = resolve_period(train_period or default_train_period())
    return STRATEGY_PATH.parent / f"{period}.json"


def save_strategy(strategy: dict[str, Any], *, train_period: str | None = None) -> Path:
    period = strategy.get("train_period") or train_period
    path = strategy_path_for(period) if period else STRATEGY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(strategy, indent=2), encoding="utf-8")
    STRATEGY_PATH.write_text(json.dumps(strategy, indent=2), encoding="utf-8")
    return path


def list_strategies() -> list[dict[str, Any]]:
    from .periods import default_train_period, period_config, resolve_period

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(STRATEGY_PATH.parent.glob("*.json")):
        if path.name == "latest.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        period = data.get("train_period") or path.stem
        period = resolve_period(period)
        if period in seen:
            continue
        seen.add(period)
        out.append(
            {
                "train_period": period,
                "train_year": data.get("train_year") or period_config(period).get("year"),
                "path": str(path),
                "win_rate_train": data.get("win_rate_train"),
                "source_setups": data.get("source_setups"),
                "updated_at": path.stat().st_mtime,
            }
        )
    out.sort(key=lambda s: s.get("train_year") or 0)
    if not out and STRATEGY_PATH.exists():
        data = json.loads(STRATEGY_PATH.read_text(encoding="utf-8"))
        period = resolve_period(data.get("train_period") or default_train_period())
        out.append(
            {
                "train_period": period,
                "train_year": data.get("train_year"),
                "path": str(STRATEGY_PATH),
                "win_rate_train": data.get("win_rate_train"),
                "source_setups": data.get("source_setups"),
                "updated_at": STRATEGY_PATH.stat().st_mtime,
            }
        )
    return out


def load_strategy(train_period: str | None = None) -> dict[str, Any] | None:
    from .periods import default_train_period, resolve_period

    if train_period:
        path = strategy_path_for(train_period)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    if STRATEGY_PATH.exists():
        return json.loads(STRATEGY_PATH.read_text(encoding="utf-8"))
    return None
