"""High-WR mean reversion — designed so edge can survive ~2 pip spreads."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Params:
  bb_win: int = 20
  bb_k: float = 2.0
  rsi_lo: float = 30.0
  rsi_hi: float = 70.0
  atr_sl_mult: float = 1.0
  rr: float = 1.8
  min_atr_pct: float = 0.00012
  max_trades_per_day: int = 3
  require_london: bool = True
  lookback: int = 0  # compat: not daily

  def key(self) -> str:
    return (
      f"bb{self.bb_win}k{self.bb_k:.1f}_rsi{self.rsi_lo:.0f}-{self.rsi_hi:.0f}"
      f"_sl{self.atr_sl_mult:.1f}_rr{self.rr:.1f}_d{self.max_trades_per_day}"
      f"_lon{int(self.require_london)}"
    )

  def to_dict(self) -> dict:
    return asdict(self)


def param_grid() -> list[Params]:
  grid: list[Params] = []
  for bb_win in (16, 24):
    for bb_k in (1.8, 2.2):
      for rsi_lo, rsi_hi in ((28, 72), (35, 65)):
        for atr_sl in (0.9, 1.2):
          for rr in (1.6, 2.0, 2.4):
            for max_day in (2, 3):
              for london in (True, False):
                grid.append(
                  Params(
                    bb_win=bb_win,
                    bb_k=bb_k,
                    rsi_lo=rsi_lo,
                    rsi_hi=rsi_hi,
                    atr_sl_mult=atr_sl,
                    rr=rr,
                    max_trades_per_day=max_day,
                    require_london=london,
                  )
                )
  return grid


def generate_signals(feat: pd.DataFrame, params: Params) -> pd.Series:
  mid = feat["close"].rolling(params.bb_win, min_periods=params.bb_win).mean()
  std = feat["close"].rolling(params.bb_win, min_periods=params.bb_win).std(ddof=0)
  upper = mid + params.bb_k * std
  lower = mid - params.bb_k * std
  vol_ok = feat["atr_pct"] >= params.min_atr_pct
  sess = (feat["london"] == 1) if params.require_london else pd.Series(True, index=feat.index)

  # Fade extremes back to mean — only when RSI confirms exhaustion
  long_setup = (feat["close"] < lower) & (feat["rsi"] <= params.rsi_lo) & vol_ok & sess
  short_setup = (feat["close"] > upper) & (feat["rsi"] >= params.rsi_hi) & vol_ok & sess
  # Avoid strong opposing trend
  long_setup &= feat["ema_fast"] >= feat["ema_slow"] * 0.998
  short_setup &= feat["ema_fast"] <= feat["ema_slow"] * 1.002

  sig = pd.Series(0, index=feat.index, dtype=int)
  sig = sig.mask(long_setup.fillna(False), 1)
  sig = sig.mask(short_setup.fillna(False), -1)
  return sig.fillna(0).astype(int)
