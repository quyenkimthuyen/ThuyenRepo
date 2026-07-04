#!/usr/bin/env python3
"""Backtest chiến lược production trên giai đoạn lịch sử (vd. 2021–2022)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

from systemtrain.backtest.risk import RiskConfig
from systemtrain.backtest.rsi_div_engine import RsiDivEngine
from systemtrain.backtest.signal_engine import SignalEngine
from systemtrain.backtest.wyckoff_engine import WyckoffEngine
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.strategy.ema_trend import EmaTrendConfig, detect_ema_trend
from systemtrain.strategy.famous import FamousConfig, detect_pin_bar
from systemtrain.strategy.rsi_divergence import RsiDivConfig
from systemtrain.strategy.wyckoff import WyckoffConfig


def _load_yaml_cfg(path: Path, key: str) -> dict:
    raw = yaml.safe_load(path.read_text()) or {}
    return raw.get(key, raw)


def _build_engines(equity: float, bt: dict, pip: float):
    w_raw = _load_yaml_cfg(Path("config/wyckoff.yaml"), "wyckoff")
    w_raw.pop("preset", None)
    wcfg = WyckoffConfig.from_dict(w_raw)
    rcfg = RsiDivConfig.from_dict(_load_yaml_cfg(Path("config/rsi_divergence.yaml"), "rsi_divergence"))
    pin_raw = _load_yaml_cfg(Path("config/pin_bar.yaml"), "pin_bar")
    pcfg = FamousConfig(**{k: v for k, v in pin_raw.items() if k in FamousConfig.__dataclass_fields__})
    ema_raw = _load_yaml_cfg(Path("config/ema_trend.yaml"), "ema_trend")
    ecfg = EmaTrendConfig(**{k: v for k, v in ema_raw.items() if k in EmaTrendConfig.__dataclass_fields__})

    spread = bt.get("spread_pips", 0.5)
    slip = bt.get("slippage_pips", 0.3)
    return [
        ("Wyckoff", WyckoffEngine(RiskConfig(0.02, wcfg.rr, 0.30, 10), wcfg, equity, spread, slip, pip)),
        ("RSI Divergence", RsiDivEngine(RiskConfig(0.02, rcfg.rr, 0.30, 10), rcfg, equity, spread, slip, pip)),
        ("Pin Bar Elite", SignalEngine(RiskConfig(0.02, 2.0, 0.30, 10), detect_pin_bar, pcfg, equity, spread, slip, pip)),
        ("EMA 50/200", SignalEngine(RiskConfig(0.02, 2.0, 0.30, 10), detect_ema_trend, ecfg, equity, spread, slip, pip)),
    ]


def _slice_period(df: pd.DataFrame, start: str, end: str, warmup_days: int = 30) -> pd.DataFrame:
    s = pd.Timestamp(start, tz="UTC")
    e = pd.Timestamp(end, tz="UTC")
    warm = s - pd.Timedelta(days=warmup_days)
    return df.loc[warm:e].copy()


def _print_row(name: str, period: str, m: dict, equity: float) -> None:
    end_eq = equity * (1 + m.get("total_return", 0))
    print(
        f"  {name:<16} {period:<14} {m.get('trade_count', 0):>3} lệnh | "
        f"WR {m.get('win_rate', 0):>5.1%} | PF {m.get('profit_factor', 0):>5.2f} | "
        f"{m.get('total_return', 0):>+6.1%} | ${end_eq:.2f}"
    )


def _metrics_from_trades(trades: list, equity: float) -> dict:
    if not trades:
        return {"trade_count": 0, "win_rate": 0.0, "profit_factor": 0.0, "total_return": 0.0}
    pnls = [t.pnl for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    pf = gross_profit / gross_loss if gross_loss > 0 else 0.0
    bal = equity
    for p in pnls:
        bal += p
    return {
        "trade_count": len(trades),
        "win_rate": len(wins) / len(trades),
        "profit_factor": pf,
        "total_return": (bal - equity) / equity,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Test production strategies on historical period")
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default="2022-12-31")
    args = parser.parse_args()

    config = Config.load()
    raw = TrainingPipeline(config).load_data()
    df_1h = to_entry_timeframe(raw, "1h")
    period_df = _slice_period(df_1h, args.start, args.end)
    period_df = prepare_dataframe(period_df, "4h")

    # Chỉ tính metric trong khoảng test (bỏ warmup)
    test_start = pd.Timestamp(args.start, tz="UTC")
    test_end = pd.Timestamp(args.end, tz="UTC")

    bt = config.backtest
    pip = config.pip_size
    engines = _build_engines(args.equity, bt, pip)

    print("=" * 78)
    print(f"  HISTORICAL TEST — {args.start} → {args.end} | EURUSD 1H")
    print("=" * 78)
    print("  Config giữ nguyên (tối ưu trên 2023–2026) — không re-train")
    print(f"  Vốn: ${args.equity:,.0f} | SL 2%/lệnh")
    print("=" * 78)
    print(f"  {'Chiến lược':<16} {'Giai đoạn':<14} {'':>3}   {'WR':>7}   {'PF':>5}   {'Return':>7}")
    print("  " + "-" * 74)

    report: dict = {"period": {"start": args.start, "end": args.end}, "strategies": {}}
    total_ret = 0.0

    for name, engine in engines:
        result = engine.run(period_df)
        closed = [t for t in result.trades if t.is_closed and test_start <= t.entry_time <= test_end]
        m = _metrics_from_trades(closed, args.equity)
        _print_row(name, f"{args.start[:4]}", m, args.equity)
        report["strategies"][name] = m
        total_ret += m.get("total_return", 0)

    print("\n  " + "-" * 74)
    print(f"  Tổng (cộng độc lập): {total_ret:+.1%} → ${args.equity * (1 + total_ret):.2f}")
    print("=" * 78)

    out = Path("output/production_hist_report.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"Saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
