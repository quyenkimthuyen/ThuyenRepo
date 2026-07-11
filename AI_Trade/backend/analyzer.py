from __future__ import annotations

import json
import re
from datetime import datetime, timezone
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


MIN_SETUP_SAMPLES_FOR_DISABLE = 5
MIN_SETUP_WIN_RATE = 0.38


def _compute_alignment_report(
    labeled: list[dict[str, Any]],
    strategy: dict[str, Any],
    df: pd.DataFrame,
) -> dict[str, Any]:
    from .strategy_registry import infer_setup_tags

    aligned = 0
    unclassified = 0
    mismatched: list[dict[str, Any]] = []

    for s in labeled:
        entry_time = pd.Timestamp(s["entry_time"])
        if entry_time.tz is None:
            entry_time = entry_time.tz_localize("UTC")
        idx = df.index.get_indexer([entry_time], method="nearest")[0]
        inferred = infer_setup_tags(df, idx, s["direction"], strategy)
        inferred_setup = inferred.get("setup")
        recorded = s.get("strategy_setup")

        if inferred_setup and inferred_setup not in ("unclassified", None):
            if recorded == inferred_setup or not recorded:
                aligned += 1
            else:
                mismatched.append(
                    {
                        "entry_time": s["entry_time"],
                        "direction": s["direction"],
                        "recorded": recorded,
                        "inferred": inferred_setup,
                    }
                )
        else:
            unclassified += 1
            if recorded and recorded != "unclassified":
                mismatched.append(
                    {
                        "entry_time": s["entry_time"],
                        "direction": s["direction"],
                        "recorded": recorded,
                        "inferred": None,
                    }
                )

    total = len(labeled) or 1
    return {
        "total": len(labeled),
        "aligned": aligned,
        "unclassified": unclassified,
        "mismatched_count": len(mismatched),
        "ratio": round(aligned / total, 3),
        "mismatched_samples": mismatched[:8],
    }


def _generate_recommendations(
    train_stats: dict[str, Any],
    alignment: dict[str, Any],
    strategy: dict[str, Any],
) -> list[dict[str, str]]:
    recs: list[dict[str, str]] = []
    by_setup = train_stats.get("by_setup") or {}

    for setup_id, counts in sorted(by_setup.items()):
        if setup_id in ("unclassified", None):
            continue
        total = int(counts.get("total", 0))
        if total < MIN_SETUP_SAMPLES_FOR_DISABLE:
            if total > 0:
                recs.append(
                    {
                        "level": "info",
                        "action": "collect_more",
                        "target": setup_id,
                        "message": f"Setup「{setup_id}」chỉ có {total} mẫu — label thêm để đánh giá.",
                    }
                )
            continue
        wr = counts.get("win", 0) / total
        if wr < MIN_SETUP_WIN_RATE:
            recs.append(
                {
                    "level": "warn",
                    "action": "disable_setup",
                    "target": setup_id,
                    "message": f"Tắt setup「{setup_id}」— win rate label {wr:.0%} ({counts.get('win')}/{total}).",
                }
            )
        elif wr >= 0.55:
            recs.append(
                {
                    "level": "ok",
                    "action": "keep_setup",
                    "target": setup_id,
                    "message": f"Giữ setup「{setup_id}」— win rate label tốt {wr:.0%}.",
                }
            )

    ratio = float(alignment.get("ratio") or 0)
    if ratio < 0.55 and alignment.get("total", 0) >= 5:
        recs.insert(
            0,
            {
                "level": "warn",
                "action": "improve_labels",
                "target": "label",
                "message": (
                    f"Chỉ {ratio:.0%} setup khớp rule chiến lược — "
                    "label lại các nến không đúng setup đã chọn."
                ),
            },
        )
    elif ratio >= 0.75:
        recs.insert(
            0,
            {
                "level": "ok",
                "action": "labels_good",
                "target": "label",
                "message": f"{ratio:.0%} setup khớp rule — dữ liệu label nhất quán.",
            },
        )

    win_rate = float(train_stats.get("win_rate") or 0)
    if win_rate < 0.45:
        recs.append(
            {
                "level": "warn",
                "action": "review_sl_tp",
                "target": "risk",
                "message": "Win rate label train thấp — xem lại SL/TP hoặc tiêu chí chọn nến.",
            }
        )

    setups_cfg = strategy.get("setups") or {}
    disabled = [k for k, v in setups_cfg.items() if v.get("enabled") is False]
    if disabled:
        recs.append(
            {
                "level": "info",
                "action": "disabled_applied",
                "target": ",".join(disabled),
                "message": f"Đã tắt setup yếu: {', '.join(disabled)}.",
            }
        )

    return recs


def _apply_setup_recommendations(strategy: dict[str, Any], train_stats: dict[str, Any]) -> list[str]:
    """Tắt setup có win rate label quá thấp."""
    applied: list[str] = []
    by_setup = train_stats.get("by_setup") or {}
    setups = strategy.setdefault("setups", {})
    for setup_id, counts in by_setup.items():
        if setup_id in ("unclassified", None):
            continue
        total = int(counts.get("total", 0))
        if total < MIN_SETUP_SAMPLES_FOR_DISABLE:
            continue
        wr = counts.get("win", 0) / total
        if wr < MIN_SETUP_WIN_RATE and setup_id in setups:
            setups[setup_id]["enabled"] = False
            applied.append(setup_id)
    return applied


def analyze_patterns(
    min_setups: int = 5,
    train_period: str | None = None,
    strategy_id: str | None = None,
) -> dict[str, Any]:
    from .periods import default_train_period, filter_setups_for_train, period_config, resolve_period
    from .data_service import load_candles
    from .indicators import add_indicators
    from .labels import retag_all_setups
    from .strategy_registry import (
        build_strategy,
        default_strategy_id,
        resolve_strategy_id,
        rule_mode_for,
        strategy_description,
    )

    train_period = resolve_period(train_period or default_train_period())
    strategy_id = resolve_strategy_id(strategy_id or default_strategy_id())
    retag_all_setups(strategy_id=strategy_id)
    setups = load_setups()
    train = filter_setups_for_train(setups, train_period)
    labeled = [s for s in train if s.get("result") in ("win", "loss")]

    if len(labeled) < min_setups:
        return {
            "status": "insufficient_data",
            "message": f"Cần ít nhất {min_setups} setup train (win/loss). Hiện có {len(labeled)}.",
            "setup_count": len(train),
            "labeled_outcomes": len(labeled),
            "strategy_id": strategy_id,
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

    strategy = build_strategy(strategy_id, train_period, train_stats=train_stats)
    disabled = _apply_setup_recommendations(strategy, train_stats)
    df = add_indicators(load_candles())
    alignment = _compute_alignment_report(labeled, strategy, df)
    recommendations = _generate_recommendations(train_stats, alignment, strategy)

    strategy.update(
        {
            "strategy_id": strategy_id,
            "train_year": period_config(train_period).get("year"),
            "source_setups": len(train),
            "win_rate_train": round(win_rate, 3),
            "avg_rr_train": round(avg_rr, 2),
            "bar_annotation_count": len(load_bar_annotations()),
            "setups_description": strategy_description(strategy_id),
            "alignment": alignment,
            "recommendations": recommendations,
            "disabled_setups": disabled,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    save_strategy(strategy, train_period=train_period, strategy_id=strategy_id)

    return {
        "status": "ok",
        "strategy_id": strategy_id,
        "train_period": train_period,
        "train_year": period_config(train_period).get("year"),
        "pipeline_flow": strategy["pipeline_flow"],
        "pipeline": pipeline_status(),
        "setup_count": len(train),
        "labeled_outcomes": len(labeled),
        "win_rate_train": round(win_rate, 3),
        "avg_rr_train": round(avg_rr, 2),
        "rule_mode": rule_mode_for(strategy_id),
        "strategy": strategy,
        "train_stats": train_stats,
        "setups_description": strategy_description(strategy_id),
        "tag_insights": {"tags": tag_rows},
        "alignment": alignment,
        "recommendations": recommendations,
        "disabled_setups": disabled,
        "strategy_path": str(strategy_path_for(strategy_id, train_period)),
    }


def train_df_rr(setups: list[dict[str, Any]]) -> float:
    vals = [s.get("planned_rr", 0) for s in setups if s.get("planned_rr")]
    return float(np.mean(vals)) if vals else 2.0


def strategy_path_for(
    strategy_id: str | None = None,
    train_period: str | None = None,
) -> Path:
    from .periods import default_train_period, resolve_period
    from .strategy_registry import default_strategy_id, resolve_strategy_id

    period = resolve_period(train_period or default_train_period())
    sid = resolve_strategy_id(strategy_id or default_strategy_id())
    return STRATEGY_PATH.parent / sid / f"{period}.json"


def _legacy_strategy_path(train_period: str) -> Path:
    return STRATEGY_PATH.parent / f"{train_period}.json"


def save_strategy(
    strategy: dict[str, Any],
    *,
    train_period: str | None = None,
    strategy_id: str | None = None,
) -> Path:
    from .strategy_registry import resolve_strategy_id

    period = strategy.get("train_period") or train_period
    sid = resolve_strategy_id(strategy_id or strategy)
    path = strategy_path_for(sid, period) if period else STRATEGY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    strategy["strategy_id"] = sid
    path.write_text(json.dumps(strategy, indent=2), encoding="utf-8")
    STRATEGY_PATH.write_text(json.dumps(strategy, indent=2), encoding="utf-8")
    return path


def list_strategies() -> list[dict[str, Any]]:
    from .periods import period_config, resolve_period
    from .strategy_registry import list_strategy_types, resolve_strategy_id

    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    if STRATEGY_PATH.parent.exists():
        for path in sorted(STRATEGY_PATH.parent.rglob("*.json")):
            if path.name == "latest.json":
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            period = resolve_period(data.get("train_period") or path.stem)
            sid = resolve_strategy_id(data)
            key = f"{sid}:{period}"
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "strategy_id": sid,
                    "train_period": period,
                    "train_year": data.get("train_year") or period_config(period).get("year"),
                    "rule_mode": data.get("rule_mode"),
                    "path": str(path),
                    "win_rate_train": data.get("win_rate_train"),
                    "source_setups": data.get("source_setups"),
                    "updated_at": path.stat().st_mtime,
                }
            )

    for path in sorted(STRATEGY_PATH.parent.glob("train_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        period = resolve_period(data.get("train_period") or path.stem)
        sid = resolve_strategy_id(data.get("strategy_id") or "rsi_h4")
        key = f"{sid}:{period}"
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "strategy_id": sid,
                "train_period": period,
                "train_year": data.get("train_year") or period_config(period).get("year"),
                "rule_mode": data.get("rule_mode"),
                "path": str(path),
                "win_rate_train": data.get("win_rate_train"),
                "source_setups": data.get("source_setups"),
                "updated_at": path.stat().st_mtime,
            }
        )

    for meta in list_strategy_types():
        sid = meta["id"]
        if not any(s["strategy_id"] == sid for s in out):
            out.append(
                {
                    "strategy_id": sid,
                    "train_period": None,
                    "train_year": None,
                    "rule_mode": meta.get("rule_mode"),
                    "path": None,
                    "win_rate_train": None,
                    "source_setups": None,
                    "updated_at": None,
                    "catalog_only": True,
                }
            )

    out.sort(key=lambda s: (s.get("strategy_id") or "", s.get("train_year") or 0))
    return out


def load_strategy(
    train_period: str | None = None,
    strategy_id: str | None = None,
) -> dict[str, Any] | None:
    from .periods import default_train_period, resolve_period
    from .strategy_registry import default_strategy_id, resolve_strategy_id

    sid = resolve_strategy_id(strategy_id or default_strategy_id())
    if train_period:
        period = resolve_period(train_period)
        path = strategy_path_for(sid, period)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        legacy = _legacy_strategy_path(period)
        if legacy.exists():
            data = json.loads(legacy.read_text(encoding="utf-8"))
            if resolve_strategy_id(data) == sid or not data.get("strategy_id"):
                return data
    if STRATEGY_PATH.exists():
        data = json.loads(STRATEGY_PATH.read_text(encoding="utf-8"))
        if train_period:
            period = resolve_period(train_period)
            if resolve_strategy_id(data) == sid and resolve_period(data.get("train_period", "")) == period:
                return data
        elif resolve_strategy_id(data) == sid:
            return data
    return None
