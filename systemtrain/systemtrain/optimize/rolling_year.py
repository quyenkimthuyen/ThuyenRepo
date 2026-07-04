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
from systemtrain.strategy.ema_trend import EmaTrendConfig, detect_ema_trend
from systemtrain.strategy.famous import FamousConfig, detect_pin_bar
from systemtrain.strategy.rsi_divergence import RsiDivConfig
from systemtrain.strategy.wyckoff import WyckoffConfig

PIN_ROLLING_KEYS = (
    "min_htf_adx", "max_adx_1h", "min_wick_body_ratio",
    "min_wick_range_ratio", "swing_lookback", "htf_mode",
)

ROLLING_FOLDS = [(2021, 2022), (2022, 2023), (2023, 2024), (2024, 2025), (2025, 2026)]
YEAR_END = {2026: "2026-07-02"}


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


def train_score(m: dict[str, Any], min_trades: int = 2) -> float:
    n = m.get("trade_count", 0)
    if n < min_trades:
        return -999.0
    ret = m.get("total_return", 0)
    wr = m.get("win_rate", 0)
    pf = min(m.get("profit_factor", 0), 5.0)
    score = ret * 50 + wr * 12 + pf * 6 + min(n, 15) * 0.4
    if ret < 0:
        score -= 4
    if wr < 0.35:
        score -= 3
    return score


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
    best_score = -999.0
    best_params: dict[str, Any] = {}
    best_train: dict[str, Any] = {}

    for vals in itertools.product(*param_grid.values()):
        params = dict(zip(keys, vals))
        engine = build_engine(params)
        m = metrics_in_window(engine.run(train_df), train_s, train_e, equity)
        score = train_score(m)
        if score > best_score:
            best_score = score
            best_params = params
            best_train = m

    return best_params, best_train


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
        "min_htf_adx": [22.0, 24.0, 26.0, 28.0],
        "max_adx": [35.0, 40.0, 45.0],
        "consolidation_days": [2, 3],
        "htf_mode": ["strict", "stack"],
    }
    return _grid_search("wyckoff", build, grid, train_df, train_s, train_e, equity)


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
        "max_adx_1h": [30.0, 35.0],
        "min_rsi_diff": [2.5, 3.5, 4.0],
        "rsi_oversold": [40.0, 45.0],
        "rsi_overbought": [55.0, 60.0],
        "min_swing_gap": [10, 14],
    }
    return _grid_search("rsi", build, grid, train_df, train_s, train_e, equity)


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
        "min_htf_adx": [28.0, 30.0, 32.0],
        "max_adx_1h": [25.0, 26.0, 28.0],
        "pullback_atr": [0.38, 0.40, 0.42],
        "max_ema_spread_atr": [1.5, 2.0, 2.2],
    }
    return _grid_search("ema", build, grid, train_df, train_s, train_e, equity)


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
        "min_htf_adx": [22.0, 24.0, 26.0],
        "max_adx_1h": [25.0, 28.0, 30.0],
        "min_wick_body_ratio": [3.5, 4.0],
        "min_wick_range_ratio": [0.55, 0.58],
        "swing_lookback": [10, 12, 14],
        "htf_mode": ["strict", "stack"],
    }
    return _grid_search("pin", build, grid, train_df, train_s, train_e, equity)


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
        "Pin Bar Elite": {k: getattr(_base_pin(), k) for k in PIN_ROLLING_KEYS},
    }
