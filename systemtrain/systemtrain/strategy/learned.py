"""Convert mined setups to executable strategy genes."""

from __future__ import annotations

from systemtrain.learn.setup_miner import LearnedSetup
from systemtrain.strategy.dsl import StrategyGene


def learned_to_gene(setup: LearnedSetup) -> StrategyGene:
    return StrategyGene(
        long_entry=None,
        short_entry=None,
        direction=setup.direction,
        session_start=setup.session_start,
        session_end=setup.session_end,
        cooldown_bars=setup.cooldown_bars,
        max_trades_per_day=setup.max_trades_per_day,
        sl_atr_mult=setup.sl_atr_mult,
        atr_period=setup.atr_period,
        learned_setup=setup.to_dict(),
    )
