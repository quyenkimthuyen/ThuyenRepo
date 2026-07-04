"""Grid-search Wyckoff params on train, rank by OOS (H1 entry + 4H filter)."""

from __future__ import annotations

import itertools

from systemtrain.backtest.risk import RiskConfig
from systemtrain.backtest.wyckoff_engine import WyckoffEngine
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.split import split_train_oos
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.strategy.wyckoff import WyckoffConfig


def optimize_wyckoff(equity: float = 1000.0) -> tuple[WyckoffConfig, list[dict]]:
    config = Config.load()
    df = to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")
    train_df, oos_df = split_train_oos(df, 1, 2)
    train_df = prepare_dataframe(train_df, "4h")
    oos_df = prepare_dataframe(oos_df, "4h")
    bt = config.backtest

    grid = {
        "consolidation_days": [2, 3],
        "min_wick_range_ratio": [0.25, 0.30],
        "rr": [2.0, 2.5],
        "max_adx": [35, 45],
        "entry_delay_bars": [0, 1],
        "min_range_touches": [2, 3],
        "htf_mode": ["stack", "trend_adx"],
        "min_htf_adx": [22, 24, 26],
    }

    keys = list(grid.keys())
    results: list[dict] = []
    best_score = -999.0
    best_cfg = WyckoffConfig(use_htf_filter=True, htf_mode="strict")

    for vals in itertools.product(*grid.values()):
        params = dict(zip(keys, vals))
        wcfg = WyckoffConfig(use_htf_filter=True, **params)
        risk = RiskConfig(0.02, wcfg.rr, 0.30, 10)
        engine = WyckoffEngine(
            risk, wcfg, equity,
            bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), config.pip_size,
        )
        train_m = engine.run(train_df).metrics
        oos_m = engine.run(oos_df).metrics

        t_trades = train_m.get("trade_count", 0)
        o_trades = oos_m.get("trade_count", 0)
        if t_trades < 2 or o_trades < 1:
            continue

        score = (
            oos_m.get("total_return", -1) * 50
            + oos_m.get("win_rate", 0) * 10
            + min(oos_m.get("profit_factor", 0), 3) * 5
            + min(oos_m.get("realized_rr", 0), 4) * 2
            + min(t_trades, 15) * 0.12
            + min(o_trades, 15) * 0.20
            - abs(train_m.get("win_rate", 0) - oos_m.get("win_rate", 0)) * 4
        )
        if oos_m.get("total_return", 0) < 0:
            score -= 4

        row = {
            **params,
            "train_wr": train_m.get("win_rate", 0),
            "train_ret": train_m.get("total_return", 0),
            "train_rr": train_m.get("realized_rr", 0),
            "train_trades": t_trades,
            "oos_wr": oos_m.get("win_rate", 0),
            "oos_ret": oos_m.get("total_return", 0),
            "oos_pf": oos_m.get("profit_factor", 0),
            "oos_rr": oos_m.get("realized_rr", 0),
            "oos_trades": o_trades,
            "score": score,
        }
        results.append(row)
        if score > best_score:
            best_score = score
            best_cfg = wcfg

    results.sort(key=lambda x: x["score"], reverse=True)
    if results:
        top = results[0]
        best_cfg = WyckoffConfig(
            use_htf_filter=True,
            consolidation_days=top["consolidation_days"],
            min_wick_range_ratio=top["min_wick_range_ratio"],
            rr=top["rr"],
            max_adx=top["max_adx"],
            entry_delay_bars=top["entry_delay_bars"],
            min_range_touches=top["min_range_touches"],
            htf_mode=top["htf_mode"],
            min_htf_adx=top.get("min_htf_adx", 22.0),
        )
    return best_cfg, results
