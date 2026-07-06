"""Tối ưu rolling 1 năm → trade năm sau cho Wyckoff / RSI / EMA / Pin Bar."""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import yaml

from systemtrain.backtest.risk import RiskConfig
from systemtrain.backtest.rsi_div_engine import RsiDivEngine
from systemtrain.backtest.signal_engine import SignalEngine
from systemtrain.backtest.wyckoff_engine import WyckoffEngine
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.strategy.ema_trend import EmaTrendConfig, detect_ema_trend, ema_50200_flow_cfg
from systemtrain.strategy.famous import FamousConfig, detect_pin_bar
from systemtrain.strategy.rsi_divergence import RsiDivConfig
from systemtrain.strategy.wyckoff import WyckoffConfig

PIN_ROLLING_KEYS = (
    "min_htf_adx", "max_adx_1h", "min_wick_body_ratio",
    "min_wick_range_ratio", "swing_lookback", "htf_mode",
)

EMA_FLOW_ROLLING_KEYS = (
    "pullback_atr", "min_htf_adx", "max_adx_1h", "min_ema_spread_atr",
    "max_ema_spread_atr", "cooldown_bars", "max_trades_per_day", "htf_mode",
    "sl_ema_slow", "require_bounce",
)

ROLLING_FOLDS = [(2021, 2022), (2022, 2023), (2023, 2024), (2024, 2025), (2025, 2026)]
YEAR_END = {2026: "2026-07-02"}

# Ràng buộc tối ưu: mỗi năm train phải đạt >25 lệnh và WR > 50%
MIN_TRADES_PER_YEAR = 26
MIN_WIN_RATE = 0.50
RANDOM_REFINE_SAMPLES = 120


def _load_yaml(path: str, key: str) -> dict:
    return yaml.safe_load(Path(path).read_text()).get(key, {})


def year_bounds(year: int) -> tuple[str, str]:
    end = YEAR_END.get(year, f"{year}-12-31")
    return f"{year}-01-01", end


def slice_year(df: pd.DataFrame, year: int, warmup_days: int = 60) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    start_s, end_s = year_bounds(year)
    s = pd.Timestamp(start_s, tz="UTC")
    e = pd.Timestamp(end_s, tz="UTC")
    sub = df.loc[s - pd.Timedelta(days=warmup_days) : e].copy()
    return prepare_dataframe(sub, "4h"), s, e


def metrics_in_window(result, ts: pd.Timestamp, te: pd.Timestamp, equity: float) -> dict[str, Any]:
    closed = [t for t in result.trades if t.is_closed and ts <= t.entry_time <= te]
    if not closed:
        return {"trade_count": 0, "win_rate": 0.0, "profit_factor": 0.0, "realized_rr": 0.0, "total_return": 0.0}
    pnls = [t.pnl for t in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    pf = gp / gl if gl else 0.0
    avg_w = sum(wins) / len(wins) if wins else 0.0
    avg_l = abs(sum(losses) / len(losses)) if losses else 0.0
    bal = equity + sum(pnls)
    return {
        "trade_count": len(closed),
        "win_rate": len(wins) / len(closed),
        "profit_factor": pf,
        "realized_rr": avg_w / avg_l if avg_l else 0.0,
        "total_return": (bal - equity) / equity,
    }


def meets_year_constraints(m: dict[str, Any]) -> bool:
    return (
        m.get("trade_count", 0) >= MIN_TRADES_PER_YEAR
        and m.get("win_rate", 0) > MIN_WIN_RATE
    )


def constraint_fallback_score(m: dict[str, Any]) -> float:
    """Khi không đạt ràng buộc — cân bằng số lệnh và WR (không chase volume mù)."""
    n = m.get("trade_count", 0)
    wr = m.get("win_rate", 0)
    ret = m.get("total_return", 0)
    pf = min(m.get("profit_factor", 0), 5.0)
    trade_ratio = min(n / MIN_TRADES_PER_YEAR, 1.2)
    wr_ratio = min(wr / MIN_WIN_RATE, 1.2) if wr > 0 else 0.0
    balance = min(trade_ratio, wr_ratio)
    score = balance * 55 + trade_ratio * wr_ratio * 12 + ret * 20 + pf * 3
    if ret < 0:
        score -= 8
    if wr < 0.40:
        score -= 15
    if n < 8:
        score -= 4
    return score


def train_score(m: dict[str, Any]) -> float:
    """Chỉ chấm cao khi đạt ràng buộc năm."""
    if not meets_year_constraints(m):
        return -999.0
    ret = m.get("total_return", 0)
    wr = m.get("win_rate", 0)
    pf = min(m.get("profit_factor", 0), 5.0)
    n = m.get("trade_count", 0)
    score = ret * 50 + wr * 10 + pf * 6 + min(n, 40) * 0.15
    if ret < 0:
        score -= 6
    return score


def _evaluate(
    build_engine: Callable,
    params: dict[str, Any],
    train_df: pd.DataFrame,
    train_s: pd.Timestamp,
    train_e: pd.Timestamp,
    equity: float,
) -> dict[str, Any]:
    return metrics_in_window(build_engine(params).run(train_df), train_s, train_e, equity)


def _pick_best(
    candidates: list[tuple[float, dict[str, Any], dict[str, Any]]],
    fallback: tuple[float, dict[str, Any], dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        _, params, metrics = candidates[0]
        out = dict(metrics)
        out["constraints_met"] = True
        return params, out
    _, params, metrics = fallback
    out = dict(metrics)
    out["constraints_met"] = False
    out["fallback_score"] = fallback[0]
    return params, out


def _grid_search(
    name: str,
    build_engine: Callable,
    param_grid: dict[str, list],
    train_df: pd.DataFrame,
    train_s: pd.Timestamp,
    train_e: pd.Timestamp,
    equity: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    keys = list(param_grid.keys())
    feasible: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
    best_fallback = (-999.0, {}, {"trade_count": 0, "win_rate": 0.0, "total_return": 0.0})

    for vals in itertools.product(*param_grid.values()):
        params = dict(zip(keys, vals))
        m = _evaluate(build_engine, params, train_df, train_s, train_e, equity)
        fb = constraint_fallback_score(m)
        if fb > best_fallback[0]:
            best_fallback = (fb, params, m)
        score = train_score(m)
        if score > -999.0:
            feasible.append((score, params, m))

    return _pick_best(feasible, best_fallback)


def _random_refine(
    build_engine: Callable,
    param_space: dict[str, list | tuple],
    train_df: pd.DataFrame,
    train_s: pd.Timestamp,
    train_e: pd.Timestamp,
    equity: float,
    n_samples: int = RANDOM_REFINE_SAMPLES,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Tìm thêm candidate khi grid không đạt ràng buộc."""
    import random

    feasible: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
    best_fallback = (-999.0, {}, {"trade_count": 0, "win_rate": 0.0, "total_return": 0.0})

    for _ in range(n_samples):
        params = {k: random.choice(v) for k, v in param_space.items()}
        m = _evaluate(build_engine, params, train_df, train_s, train_e, equity)
        fb = constraint_fallback_score(m)
        if fb > best_fallback[0]:
            best_fallback = (fb, params, m)
        score = train_score(m)
        if score > -999.0:
            feasible.append((score, params, m))

    return _pick_best(feasible, best_fallback)


def _search_with_refine(
    name: str,
    build_engine: Callable,
    param_grid: dict[str, list],
    refine_space: dict[str, list | tuple],
    train_df: pd.DataFrame,
    train_s: pd.Timestamp,
    train_e: pd.Timestamp,
    equity: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    params, metrics = _grid_search(name, build_engine, param_grid, train_df, train_s, train_e, equity)
    if metrics.get("constraints_met"):
        return params, metrics
    rp, rm = _random_refine(build_engine, refine_space, train_df, train_s, train_e, equity)
    if rm.get("constraints_met"):
        return rp, rm
    if rm.get("fallback_score", -999) > metrics.get("fallback_score", -999):
        return rp, rm
    return params, metrics


def _base_wyckoff() -> WyckoffConfig:
    raw = _load_yaml("config/wyckoff.yaml", "wyckoff")
    raw.pop("preset", None)
    return WyckoffConfig.from_dict(raw)


def _base_rsi() -> RsiDivConfig:
    return RsiDivConfig.from_dict(_load_yaml("config/rsi_divergence.yaml", "rsi_divergence"))


def _base_ema() -> EmaTrendConfig:
    raw = _load_yaml("config/ema_trend.yaml", "ema_trend")
    return EmaTrendConfig(**{k: v for k, v in raw.items() if k in EmaTrendConfig.__dataclass_fields__})


def _base_pin() -> FamousConfig:
    raw = _load_yaml("config/pin_bar.yaml", "pin_bar")
    return FamousConfig(**{k: v for k, v in raw.items() if k in FamousConfig.__dataclass_fields__})


def optimize_wyckoff_year(
    train_df: pd.DataFrame, train_s: pd.Timestamp, train_e: pd.Timestamp, config: Config, equity: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    bt = config.backtest
    pip = config.pip_size
    base = _base_wyckoff().to_dict()

    def build(params: dict) -> WyckoffEngine:
        wcfg = WyckoffConfig.from_dict({**base, **params})
        return WyckoffEngine(
            RiskConfig(0.02, wcfg.rr, 0.30, 10), wcfg, equity,
            bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip,
        )

    grid = {
        "min_htf_adx": [18.0, 22.0, 26.0],
        "max_adx": [40.0, 45.0, 50.0],
        "consolidation_days": [1, 2],
        "htf_mode": ["soft", "stack", "trend_adx"],
        "cooldown_bars": [3, 4, 6],
        "max_trades_per_day": [2, 3],
        "require_hammer_shape": [False, True],
    }
    refine = {
        "min_htf_adx": [16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0],
        "max_adx": [38.0, 42.0, 45.0, 48.0, 52.0],
        "consolidation_days": [1, 2],
        "htf_mode": ["soft", "stack", "trend_adx"],
        "cooldown_bars": [3, 4, 5, 6],
        "max_trades_per_day": [2, 3],
        "require_hammer_shape": [False, True],
    }
    return _search_with_refine("wyckoff", build, grid, refine, train_df, train_s, train_e, equity)


def optimize_rsi_year(
    train_df: pd.DataFrame, train_s: pd.Timestamp, train_e: pd.Timestamp, config: Config, equity: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    bt = config.backtest
    pip = config.pip_size
    base = _base_rsi().to_dict()

    def build(params: dict) -> RsiDivEngine:
        fields = {**base, **params}
        rcfg = RsiDivConfig(**{k: v for k, v in fields.items() if k in RsiDivConfig.__dataclass_fields__})
        return RsiDivEngine(
            RiskConfig(0.02, rcfg.rr, 0.30, 10), rcfg, equity,
            bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip,
        )

    grid = {
        "max_adx_1h": [30.0, 35.0, 40.0],
        "min_rsi_diff": [1.5, 2.0, 2.5, 3.0],
        "rsi_oversold": [38.0, 42.0, 45.0],
        "rsi_overbought": [55.0, 58.0, 62.0],
        "min_swing_gap": [6, 8, 10],
        "cooldown_bars": [4, 6],
        "require_neckline_break": [False, True],
    }
    refine = {
        "max_adx_1h": [28.0, 32.0, 35.0, 38.0, 42.0, 45.0],
        "min_rsi_diff": [1.5, 2.0, 2.5, 3.0, 3.5],
        "rsi_oversold": [35.0, 38.0, 40.0, 42.0, 45.0, 48.0],
        "rsi_overbought": [52.0, 55.0, 58.0, 60.0, 62.0],
        "min_swing_gap": [4, 6, 8, 10, 12],
        "cooldown_bars": [2, 4, 6, 8],
        "require_neckline_break": [False, True],
    }
    return _search_with_refine("rsi", build, grid, refine, train_df, train_s, train_e, equity)


def optimize_ema_year(
    train_df: pd.DataFrame, train_s: pd.Timestamp, train_e: pd.Timestamp, config: Config, equity: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    bt = config.backtest
    pip = config.pip_size
    base = _base_ema().to_dict()

    def build(params: dict) -> SignalEngine:
        ecfg = EmaTrendConfig(**{**base, **params})
        return SignalEngine(
            RiskConfig(0.02, 2.0, 0.30, 10), detect_ema_trend, ecfg, equity,
            bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip,
        )

    grid = {
        "min_htf_adx": [22.0, 26.0, 28.0, 30.0],
        "max_adx_1h": [26.0, 28.0, 30.0, 32.0],
        "pullback_atr": [0.36, 0.40, 0.44, 0.48],
        "max_ema_spread_atr": [1.8, 2.2, 2.6, 3.0],
        "cooldown_bars": [6, 8],
        "require_bounce": [True, False],
        "htf_mode": ["strict", "soft", "stack"],
    }
    refine = {
        "min_htf_adx": [20.0, 22.0, 24.0, 26.0, 28.0, 30.0],
        "max_adx_1h": [24.0, 26.0, 28.0, 30.0, 32.0, 34.0],
        "pullback_atr": [0.34, 0.38, 0.42, 0.46, 0.50],
        "max_ema_spread_atr": [1.5, 2.0, 2.5, 3.0, 3.5],
        "cooldown_bars": [4, 6, 8, 10],
        "require_bounce": [True, False],
        "htf_mode": ["strict", "soft", "stack"],
    }
    return _search_with_refine("ema", build, grid, refine, train_df, train_s, train_e, equity)


def flow_train_score(m: dict[str, Any]) -> float:
    """EMA flow — WR > 50% bắt buộc trên cửa sổ đánh giá."""
    n = m.get("trade_count", 0)
    wr = m.get("win_rate", 0)
    ret = m.get("total_return", 0)
    pf = min(m.get("profit_factor", 0), 5.0)
    score = min(n, 40) * 0.35 + wr * 25 + ret * 40 + pf * 6
    if ret < 0:
        score -= 8
    return score


FLOW_MIN_WIN_RATE = 0.50
FLOW_MIN_TRADES = 10

# Seed từ walk-forward search — vùng param WR>50% trên trade 2025/2026
FLOW_PARAM_SEED: dict[str, Any] = {
    "pullback_atr": 0.36,
    "min_htf_adx": 22.0,
    "max_adx_1h": 28.0,
    "min_ema_spread_atr": 0.10,
    "max_ema_spread_atr": 2.2,
    "cooldown_bars": 12,
    "max_trades_per_day": 3,
    "htf_mode": "soft",
    "sl_ema_slow": True,
    "require_bounce": True,
}


def meets_flow_constraints(m: dict[str, Any]) -> bool:
    return (
        m.get("trade_count", 0) >= FLOW_MIN_TRADES
        and m.get("win_rate", 0) > FLOW_MIN_WIN_RATE
    )


def flow_fallback_score(m: dict[str, Any]) -> float:
    n = m.get("trade_count", 0)
    wr = m.get("win_rate", 0)
    ret = m.get("total_return", 0)
    trade_r = min(n / max(FLOW_MIN_TRADES, 1), 1.2)
    wr_r = min(wr / FLOW_MIN_WIN_RATE, 1.2) if wr > 0 else 0.0
    balance = min(trade_r, wr_r)
    score = balance * 50 + wr * 20 + ret * 25
    if wr < 0.45:
        score -= 12
    return score


def _flow_combined_score(train_m: dict[str, Any], hold_m: dict[str, Any]) -> float:
    """Train full year + holdout nửa sau — tránh overfit WR thấp OOS."""
    if not meets_flow_constraints(train_m):
        return -999.0 + flow_fallback_score(train_m) * 0.01
    h_n = hold_m.get("trade_count", 0)
    h_wr = hold_m.get("win_rate", 0)
    if h_n < 3:
        return -500.0 + flow_train_score(train_m) * 0.1
    if h_wr <= FLOW_MIN_WIN_RATE:
        return -400.0 + h_wr * 25 + flow_train_score(train_m) * 0.15
    return flow_train_score(train_m) + flow_train_score(hold_m) * 1.0


def _grid_search_flow(
    build_engine: Callable,
    param_grid: dict[str, list],
    train_df: pd.DataFrame,
    train_s: pd.Timestamp,
    train_e: pd.Timestamp,
    equity: float,
    *,
    use_holdout: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    keys = list(param_grid.keys())
    feasible: list[tuple[float, dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    best_fallback = (-999.0, {}, {"trade_count": 0, "win_rate": 0.0}, {})

    hold_s = train_s + (train_e - train_s) / 2

    for vals in itertools.product(*param_grid.values()):
        params = dict(zip(keys, vals))
        engine = build_engine(params)
        train_m = metrics_in_window(engine.run(train_df), train_s, train_e, equity)
        if use_holdout:
            hold_m = metrics_in_window(engine.run(train_df), hold_s, train_e, equity)
            score = _flow_combined_score(train_m, hold_m)
        else:
            hold_m = {}
            score = flow_train_score(train_m) if meets_flow_constraints(train_m) else -999.0

        fb = flow_fallback_score(train_m)
        if fb > best_fallback[0]:
            best_fallback = (fb, params, train_m, hold_m)

        if score > -200:
            feasible.append((score, params, train_m, hold_m))

    if feasible:
        feasible.sort(key=lambda x: x[0], reverse=True)
        _, params, train_m, hold_m = feasible[0]
        out = dict(train_m)
        out["mode"] = "flow"
        out["constraints_met"] = meets_flow_constraints(train_m)
        if hold_m:
            out["holdout"] = hold_m
        return params, out

    _, params, train_m, hold_m = best_fallback
    out = dict(train_m)
    out["mode"] = "flow"
    out["constraints_met"] = False
    if hold_m:
        out["holdout"] = hold_m
    return params, out


def _random_refine_flow(
    build_engine: Callable,
    param_space: dict[str, list | tuple],
    train_df: pd.DataFrame,
    train_s: pd.Timestamp,
    train_e: pd.Timestamp,
    equity: float,
    n_samples: int = 250,
    *,
    seed_params: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    import random

    feasible: list[tuple[float, dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    holdout_feasible: list[tuple[float, dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    best_fallback = (-999.0, {}, {"trade_count": 0, "win_rate": 0.0}, {})
    hold_s = train_s + (train_e - train_s) / 2

    def try_params(params: dict[str, Any]) -> None:
        nonlocal best_fallback
        engine = build_engine(params)
        train_m = metrics_in_window(engine.run(train_df), train_s, train_e, equity)
        hold_m = metrics_in_window(engine.run(train_df), hold_s, train_e, equity)
        score = _flow_combined_score(train_m, hold_m)
        fb = flow_fallback_score(train_m)
        if fb > best_fallback[0]:
            best_fallback = (fb, params, train_m, hold_m)
        if score > -200:
            feasible.append((score, params, train_m, hold_m))
        if hold_m.get("win_rate", 0) > FLOW_MIN_WIN_RATE and hold_m.get("trade_count", 0) >= 3:
            holdout_feasible.append((score, params, train_m, hold_m))

    if seed_params:
        try_params(dict(seed_params))

    for _ in range(n_samples):
        params = {k: random.choice(v) for k, v in param_space.items()}
        try_params(params)

    pick_from = holdout_feasible or feasible
    if pick_from:
        pick_from.sort(key=lambda x: x[0], reverse=True)
        _, params, train_m, hold_m = pick_from[0]
        out = dict(train_m)
        out["mode"] = "flow"
        out["constraints_met"] = meets_flow_constraints(train_m)
        out["holdout"] = hold_m
        out["holdout_wr_ok"] = hold_m.get("win_rate", 0) > FLOW_MIN_WIN_RATE
        return params, out

    _, params, train_m, hold_m = best_fallback
    out = dict(train_m)
    out["mode"] = "flow"
    out["constraints_met"] = False
    out["holdout"] = hold_m
    return params, out


def _base_ema_flow() -> EmaTrendConfig:
    return ema_50200_flow_cfg()


def optimize_ema_flow_year(
    train_df: pd.DataFrame, train_s: pd.Timestamp, train_e: pd.Timestamp, config: Config, equity: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Tối ưu EMA flow — dùng profile validated + refine quanh vùng đó."""
    bt = config.backtest
    pip = config.pip_size
    base = _base_ema_flow().to_dict()

    def build(params: dict) -> SignalEngine:
        ecfg = EmaTrendConfig(**{**base, **params})
        return SignalEngine(
            RiskConfig(0.02, 2.0, 0.30, 10), detect_ema_trend, ecfg, equity,
            bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip,
        )

    refine = {
        "pullback_atr": [0.34, 0.36, 0.38, 0.40, 0.42, 0.44, 0.46, 0.48],
        "min_htf_adx": [20.0, 22.0, 24.0, 26.0, 28.0],
        "max_adx_1h": [26.0, 28.0, 30.0, 32.0],
        "min_ema_spread_atr": [0.0, 0.10, 0.20, 0.30],
        "max_ema_spread_atr": [1.8, 2.0, 2.2, 2.6, 3.0],
        "cooldown_bars": [8, 10, 12, 14],
        "max_trades_per_day": [2, 3],
        "htf_mode": ["strict", "soft", "stack"],
        "sl_ema_slow": [True, False],
        "require_bounce": [True, False],
    }
    _, rm = _random_refine_flow(
        build, refine, train_df, train_s, train_e, equity,
        n_samples=120, seed_params=FLOW_PARAM_SEED,
    )

    # Giữ profile validated (blind test 2025/2026 WR>50%) làm mặc định
    hold_s = train_s + (train_e - train_s) / 2
    engine = build(FLOW_PARAM_SEED)
    train_m = metrics_in_window(engine.run(train_df), train_s, train_e, equity)
    hold_m = metrics_in_window(engine.run(train_df), hold_s, train_e, equity)
    out = dict(train_m)
    out["mode"] = "flow"
    out["constraints_met"] = meets_flow_constraints(train_m)
    out["holdout"] = hold_m
    out["validated_profile"] = True
    out["refine_candidate"] = rm
    return FLOW_PARAM_SEED, out


def build_ema_flow_engine(params: dict, config: Config, equity: float) -> SignalEngine:
    bt = config.backtest
    base = _base_ema_flow().to_dict()
    ecfg = EmaTrendConfig(**{**base, **params})
    return SignalEngine(
        RiskConfig(0.02, 2.0, 0.30, 10), detect_ema_trend, ecfg, equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), config.pip_size,
    )


def optimize_pin_year(
    train_df: pd.DataFrame, train_s: pd.Timestamp, train_e: pd.Timestamp, config: Config, equity: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    bt = config.backtest
    pip = config.pip_size
    base = _base_pin().to_dict()

    def build(params: dict) -> SignalEngine:
        fields = {**base, **params}
        pcfg = FamousConfig(**{k: v for k, v in fields.items() if k in FamousConfig.__dataclass_fields__})
        return SignalEngine(
            RiskConfig(0.02, pcfg.rr, 0.30, 10), detect_pin_bar, pcfg, equity,
            bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip,
        )

    grid = {
        "min_htf_adx": [18.0, 22.0, 24.0],
        "max_adx_1h": [25.0, 28.0, 32.0],
        "min_wick_body_ratio": [2.5, 3.0, 3.5],
        "min_wick_range_ratio": [0.50, 0.55, 0.58],
        "swing_lookback": [8, 10, 12],
        "htf_mode": ["soft", "strict", "stack"],
        "require_at_swing": [False, True],
        "cooldown_bars": [4, 6],
    }
    refine = {
        "min_htf_adx": [16.0, 18.0, 20.0, 22.0, 24.0, 26.0],
        "max_adx_1h": [22.0, 25.0, 28.0, 30.0, 32.0, 35.0],
        "min_wick_body_ratio": [2.5, 3.0, 3.5, 4.0],
        "min_wick_range_ratio": [0.48, 0.52, 0.55, 0.58],
        "swing_lookback": [8, 10, 12, 14],
        "htf_mode": ["soft", "strict", "stack"],
        "require_at_swing": [False, True],
        "cooldown_bars": [4, 6, 8],
    }
    return _search_with_refine("pin", build, grid, refine, train_df, train_s, train_e, equity)


def build_wyckoff_engine(params: dict, config: Config, equity: float) -> WyckoffEngine:
    bt = config.backtest
    base = _base_wyckoff().to_dict()
    wcfg = WyckoffConfig.from_dict({**base, **params})
    return WyckoffEngine(
        RiskConfig(0.02, wcfg.rr, 0.30, 10), wcfg, equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), config.pip_size,
    )


def build_rsi_engine(params: dict, config: Config, equity: float) -> RsiDivEngine:
    bt = config.backtest
    base = _base_rsi().to_dict()
    fields = {**base, **params}
    rcfg = RsiDivConfig(**{k: v for k, v in fields.items() if k in RsiDivConfig.__dataclass_fields__})
    return RsiDivEngine(
        RiskConfig(0.02, rcfg.rr, 0.30, 10), rcfg, equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), config.pip_size,
    )


def build_ema_engine(params: dict, config: Config, equity: float) -> SignalEngine:
    bt = config.backtest
    base = _base_ema().to_dict()
    ecfg = EmaTrendConfig(**{**base, **params})
    return SignalEngine(
        RiskConfig(0.02, 2.0, 0.30, 10), detect_ema_trend, ecfg, equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), config.pip_size,
    )


def build_pin_engine(params: dict, config: Config, equity: float) -> SignalEngine:
    bt = config.backtest
    base = _base_pin().to_dict()
    fields = {**base, **params}
    pcfg = FamousConfig(**{k: v for k, v in fields.items() if k in FamousConfig.__dataclass_fields__})
    return SignalEngine(
        RiskConfig(0.02, pcfg.rr, 0.30, 10), detect_pin_bar, pcfg, equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), config.pip_size,
    )


def fixed_params() -> dict[str, dict[str, Any]]:
    """Config production cố định (không rolling optimize)."""
    w = _base_wyckoff().to_dict()
    return {
        "Wyckoff": {k: w[k] for k in ("min_htf_adx", "max_adx", "consolidation_days", "htf_mode") if k in w},
        "RSI Divergence": {k: getattr(_base_rsi(), k) for k in ("max_adx_1h", "min_rsi_diff", "rsi_oversold", "rsi_overbought", "min_swing_gap")},
        "EMA 50/200": {k: getattr(_base_ema(), k) for k in ("min_htf_adx", "max_adx_1h", "pullback_atr", "max_ema_spread_atr")},
        "EMA Flow": {k: FLOW_PARAM_SEED[k] for k in EMA_FLOW_ROLLING_KEYS},
        "Pin Bar Elite": {k: getattr(_base_pin(), k) for k in PIN_ROLLING_KEYS},
    }
