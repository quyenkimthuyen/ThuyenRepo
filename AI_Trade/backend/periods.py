"""Period registry — train years, backtest years, multi-year slices."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .data_service import load_splits


def resolve_period(period: str) -> str:
    cfg = load_splits()
    legacy = cfg.get("legacy_map") or {}
    return legacy.get(period, period)


def period_config(period: str) -> dict[str, Any]:
    period = resolve_period(period)
    periods = load_splits()["periods"]
    if period not in periods:
        raise KeyError(period)
    return periods[period]


def period_kind(period: str) -> str:
    return period_config(period).get("kind", "backtest")


def is_train_period(period: str) -> bool:
    return period_kind(period) == "train"


def is_backtest_period(period: str) -> bool:
    return period_kind(period) == "backtest"


def list_periods(*, kind: str | None = None) -> list[dict[str, Any]]:
    splits = load_splits()
    out: list[dict[str, Any]] = []
    for pid, cfg in splits["periods"].items():
        if kind and cfg.get("kind") != kind:
            continue
        out.append(
            {
                "id": pid,
                "kind": cfg.get("kind"),
                "year": cfg.get("year"),
                "label": cfg.get("label"),
                "from": cfg.get("from"),
                "to": cfg.get("to"),
            }
        )
    out.sort(key=lambda p: (p.get("kind") or "", p.get("year") or 0))
    return out


def default_train_period() -> str:
    return resolve_period(load_splits().get("defaults", {}).get("train", "train_2022"))


def default_backtest_periods() -> list[str]:
    raw = load_splits().get("defaults", {}).get("backtest", ["bt_2023"])
    return [resolve_period(p) for p in raw]


def period_bounds(period: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    cfg = period_config(period)
    start = pd.Timestamp(cfg["from"], tz="UTC")
    end = pd.Timestamp(cfg["to"], tz="UTC") + pd.Timedelta(hours=23, minutes=59)
    return start, end


def timestamp_in_period(ts: pd.Timestamp, period: str) -> bool:
    if ts.tz is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    start, end = period_bounds(period)
    return start <= ts <= end


def period_for_timestamp(ts: pd.Timestamp) -> str | None:
    """Map timestamp to a period id; prefer train if ranges overlap."""
    if ts.tz is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")

    matches: list[str] = []
    splits = load_splits()["periods"]
    for name, cfg in splits.items():
        start = pd.Timestamp(cfg["from"], tz="UTC")
        end = pd.Timestamp(cfg["to"], tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        if start <= ts <= end:
            matches.append(name)

    if not matches:
        return None

    train_matches = [m for m in matches if splits[m].get("kind") == "train"]
    if train_matches:
        return sorted(train_matches)[0]
    return sorted(matches)[0]


def periods_grouped_for_api() -> dict[str, Any]:
    splits = load_splits()
    train = list_periods(kind="train")
    backtest = list_periods(kind="backtest")
    return {
        "train": train,
        "backtest": backtest,
        "defaults": {
            "train": default_train_period(),
            "backtest": default_backtest_periods(),
        },
        "legacy_map": splits.get("legacy_map", {}),
    }


def normalize_backtest_periods(periods: list[str] | str | None) -> list[str]:
    if not periods:
        return default_backtest_periods()
    if isinstance(periods, str):
        parts = [p.strip() for p in periods.replace(";", ",").split(",") if p.strip()]
    else:
        parts = [resolve_period(p) for p in periods]
    out: list[str] = []
    for p in parts:
        p = resolve_period(p)
        if p.startswith("bt_") or is_backtest_period(p):
            if p not in out:
                out.append(p)
            continue
        # allow "2023" shorthand
        if p.isdigit() and len(p) == 4:
            candidate = f"bt_{p}"
            if candidate in load_splits()["periods"]:
                if candidate not in out:
                    out.append(candidate)
    return out or default_backtest_periods()


def normalize_setup_period(period: str | None) -> str:
    return resolve_period(period or "train")


def filter_setups_for_train(
    setups: list[dict[str, Any]],
    train_period: str | None = None,
) -> list[dict[str, Any]]:
    target = resolve_period(train_period or default_train_period())
    return [s for s in setups if normalize_setup_period(s.get("period")) == target]


def period_exists(period: str) -> bool:
    period = resolve_period(period)
    return period in load_splits()["periods"]


def backtest_label(period_ids: list[str]) -> str:
    years = []
    for pid in period_ids:
        try:
            years.append(str(period_config(pid).get("year", pid)))
        except KeyError:
            years.append(pid)
    return " · ".join(years) if years else "Backtest"
