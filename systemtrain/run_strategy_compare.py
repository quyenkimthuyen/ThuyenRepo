#!/usr/bin/env python3
"""So sánh phiên bản tốt nhất: Learned (strict 4H) vs Wyckoff (stack 4H) + RR sweep."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

import yaml

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.backtest.metrics import compute_metrics
from systemtrain.backtest.risk import RiskConfig
from systemtrain.backtest.wyckoff_engine import WyckoffEngine
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.split import split_train_oos
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.learn.features import HTF_LONG_FILTERS, HTF_SHORT_FILTERS
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.strategy.dsl import StrategyGene
from systemtrain.strategy.wyckoff import WyckoffConfig
from systemtrain.validate.registry import StrategyRegistry

RR_SWEEP = [1.5, 2.0, 2.5, 3.0]


def _load_wyckoff_cfg() -> WyckoffConfig:
    path = Path("config/wyckoff.yaml")
    if path.exists():
        raw = yaml.safe_load(path.read_text()) or {}
        return WyckoffConfig.from_dict(raw.get("wyckoff", raw))
    return WyckoffConfig(use_htf_filter=True, htf_mode="stack")


def _load_learned_gene() -> StrategyGene:
    registry = StrategyRegistry(Path("output/strategies.db"))
    rows = registry.list_strategies()
    if not rows:
        raise FileNotFoundError("Chưa có learned strategy. Chạy: python run_test.py --full")
    gene = StrategyGene.from_dict(json.loads(rows[0]["gene_json"]))
    if gene.learned_setup:
        gene.learned_setup["htf_long_filter"] = [list(x) for x in HTF_LONG_FILTERS]
        gene.learned_setup["htf_short_filter"] = [list(x) for x in HTF_SHORT_FILTERS]
    return gene


def _metrics_row(name: str, period: str, m: dict, equity: float, target_rr: float) -> dict:
    profit = equity * m.get("total_return", 0)
    return {
        "strategy": name,
        "period": period,
        "trades": m.get("trade_count", 0),
        "win_rate": m.get("win_rate", 0),
        "profit_factor": m.get("profit_factor", 0),
        "target_rr": target_rr,
        "realized_rr": m.get("realized_rr", 0),
        "total_return": m.get("total_return", 0),
        "profit_usd": profit,
        "end_equity": equity + profit,
        "max_drawdown": m.get("max_drawdown", 0),
        "avg_win": m.get("avg_win", 0),
        "avg_loss": m.get("avg_loss", 0),
        "expectancy": m.get("expectancy", 0),
        "halted": m.get("halted", False),
    }


def _print_table(rows: list[dict], equity: float) -> None:
    hdr = (
        f"  {'Chiến lược':<12} {'Giai đoạn':<12} {'Lệnh':>4} {'WR':>6} {'PF':>5} "
        f"{'RR tgt':>6} {'RR thực':>7} {'Return':>7} {'Lợi nhuận':>10} {'MaxDD':>6}"
    )
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for r in rows:
        print(
            f"  {r['strategy']:<12} {r['period']:<12} {r['trades']:>4} "
            f"{r['win_rate']:>5.1%} {r['profit_factor']:>5.2f} "
            f"{r['target_rr']:>6.1f} {r['realized_rr']:>7.2f} "
            f"{r['total_return']:>+6.1%} ${r['profit_usd']:>+9.2f} {r['max_drawdown']:>5.1%}"
        )


def _rr_sweep_learned(oos_df, gene: StrategyGene, equity: float, bt: dict, pip: float) -> list[dict]:
    rows = []
    for rr in RR_SWEEP:
        risk = RiskConfig(0.02, rr, 0.30, 10)
        engine = BacktestEngine(risk, equity, bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip)
        m = compute_metrics(engine.run(oos_df, gene))
        rows.append({"rr": rr, **_metrics_row("Learned", "OOS sweep", m, equity, rr)})
    return rows


def _rr_sweep_wyckoff(oos_df, base_cfg: WyckoffConfig, equity: float, bt: dict, pip: float) -> list[dict]:
    rows = []
    for rr in RR_SWEEP:
        wcfg = WyckoffConfig(**{**base_cfg.to_dict(), "rr": rr})
        engine = WyckoffEngine(RiskConfig(0.02, rr, 0.30, 10), wcfg, equity,
                               bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip)
        m = engine.run(oos_df).metrics
        rows.append({"rr": rr, **_metrics_row("Wyckoff", "OOS sweep", m, equity, rr)})
    return rows


def _print_rr_sweep(title: str, rows: list[dict]) -> None:
    print(f"\n  ── {title} ──")
    print(f"  {'RR':>5} {'Lệnh':>5} {'WR':>6} {'PF':>5} {'RR thực':>8} {'Return':>7} {'Lợi nhuận':>10}")
    print("  " + "-" * 52)
    for r in rows:
        print(
            f"  {r['rr']:>5.1f} {r['trades']:>5} {r['win_rate']:>5.1%} "
            f"{r['profit_factor']:>5.2f} {r['realized_rr']:>8.2f} "
            f"{r['total_return']:>+6.1%} ${r['profit_usd']:>+9.2f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--equity", type=float, default=1000.0)
    args = parser.parse_args()

    config = Config.load()
    df = to_entry_timeframe(TrainingPipeline(config).load_data(), config.timeframe or "1h")
    train_df, oos_df = split_train_oos(df, config.data.get("train_years", 1), config.data.get("oos_years", 2))
    htf = getattr(config, "htf_timeframe", "4h")
    train_df = prepare_dataframe(train_df, htf)
    oos_df = prepare_dataframe(oos_df, htf)
    bt = config.backtest
    pip = config.pip_size

    gene = _load_learned_gene()
    wcfg = _load_wyckoff_cfg()
    learned_rr = config.risk.get("min_rr", 2.0)

    learned_engine = BacktestEngine(
        RiskConfig(0.02, learned_rr, 0.30, 10), args.equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip,
    )
    wyckoff_engine = WyckoffEngine(
        RiskConfig(0.02, wcfg.rr, 0.30, 10), wcfg, args.equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip,
    )

    print("=" * 82)
    print("  SO SÁNH CHIẾN LƯỢC TỐT NHẤT — EURUSD 1H + filter 4H")
    print("=" * 82)
    print(f"  Learned : Monday filter | 4H strict (close vs EMA50) | RR≥{learned_rr}")
    print(f"  Wyckoff : Failed break  | 4H stack  (EMA21/50)       | RR={wcfg.rr}")
    print(f"  Vốn     : ${args.equity:,.0f} | SL 2%/lệnh | Spread {bt.get('spread_pips', 0.5)} pip")
    print("=" * 82)

    main_rows = [
        _metrics_row("Learned", "Train 1 năm", compute_metrics(learned_engine.run(train_df, gene)), args.equity, learned_rr),
        _metrics_row("Learned", "OOS 2 năm", compute_metrics(learned_engine.run(oos_df, gene)), args.equity, learned_rr),
        _metrics_row("Wyckoff", "Train 1 năm", wyckoff_engine.run(train_df).metrics, args.equity, wcfg.rr),
        _metrics_row("Wyckoff", "OOS 2 năm", wyckoff_engine.run(oos_df).metrics, args.equity, wcfg.rr),
    ]
    _print_table(main_rows, args.equity)

    learned_sweep = _rr_sweep_learned(oos_df, gene, args.equity, bt, pip)
    wyckoff_sweep = _rr_sweep_wyckoff(oos_df, wcfg, args.equity, bt, pip)
    _print_rr_sweep("RR SWEEP — Learned (OOS 2 năm)", learned_sweep)
    _print_rr_sweep("RR SWEEP — Wyckoff (OOS 2 năm)", wyckoff_sweep)

    best_l = max(learned_sweep, key=lambda x: x["total_return"])
    best_w = max(wyckoff_sweep, key=lambda x: x["total_return"])
    l_oos = main_rows[1]
    w_oos = main_rows[3]

    print("\n" + "=" * 82)
    print("  TÓM TẮT OOS (RR mặc định 2.0)")
    print(f"    Learned : {l_oos['trades']} lệnh | WR {l_oos['win_rate']:.1%} | "
          f"RR {l_oos['realized_rr']:.2f} | {l_oos['total_return']:+.1%} (${l_oos['profit_usd']:+.2f})")
    print(f"    Wyckoff : {w_oos['trades']} lệnh | WR {w_oos['win_rate']:.1%} | "
          f"RR {w_oos['realized_rr']:.2f} | {w_oos['total_return']:+.1%} (${w_oos['profit_usd']:+.2f})")
    print(f"\n  RR tốt nhất OOS:")
    print(f"    Learned RR={best_l['rr']} → {best_l['total_return']:+.1%} (${best_l['profit_usd']:+.2f})")
    print(f"    Wyckoff RR={best_w['rr']} → {best_w['total_return']:+.1%} (${best_w['profit_usd']:+.2f})")
    print("=" * 82)

    report = {
        "equity": args.equity,
        "learned_config": {"filter": "strict", "target_rr": learned_rr},
        "wyckoff_config": wcfg.to_dict(),
        "main": main_rows,
        "rr_sweep": {"learned": learned_sweep, "wyckoff": wyckoff_sweep},
        "best_rr_oos": {"learned": best_l, "wyckoff": best_w},
    }
    out = Path("output/strategy_compare_report.json")
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
