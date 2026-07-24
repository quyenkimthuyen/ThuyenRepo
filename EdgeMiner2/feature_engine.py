"""Rich causal feature matrix for adaptive strategy mining."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from indicators import ema, rsi, atr, adx, bollinger_bands, macd
from mt5_bridge import history_sync


@dataclass(frozen=True)
class FeatureProfile:
  """Indicator periods behind the stable public feature names."""

  atr_period: int
  rsi_period: int
  adx_period: int
  ema_fast: int
  ema_slow: int
  ema_trend: int
  ema_long: int
  bb_period: int
  zscore_period: int
  roc_period: int
  sweep_period: int
  percentile_period: int
  warmup: int
  causal_h4: bool = True
  broker_sessions: bool = True


FEATURE_PROFILES = {
  "legacy": FeatureProfile(
    atr_period=14, rsi_period=14, adx_period=14,
    ema_fast=8, ema_slow=21, ema_trend=50, ema_long=200,
    bb_period=20, zscore_period=20, roc_period=5, sweep_period=20,
    percentile_period=50, warmup=120, causal_h4=False, broker_sessions=False,
  ),
  "current": FeatureProfile(
    atr_period=14, rsi_period=14, adx_period=14,
    ema_fast=8, ema_slow=21, ema_trend=50, ema_long=200,
    bb_period=20, zscore_period=20, roc_period=5, sweep_period=20,
    percentile_period=50, warmup=120,
  ),
  "m15_native": FeatureProfile(
    atr_period=28, rsi_period=28, adx_period=28,
    ema_fast=16, ema_slow=48, ema_trend=96, ema_long=384,
    bb_period=40, zscore_period=40, roc_period=12, sweep_period=40,
    percentile_period=100, warmup=400,
  ),
}
_PROFILE_ALIASES = {"existing": "current", "slower": "m15_native"}


def get_feature_profile(name: str) -> FeatureProfile:
  """Resolve a selectable feature profile, including friendly aliases."""
  resolved = _PROFILE_ALIASES.get(name, name)
  try:
    return FEATURE_PROFILES[resolved]
  except KeyError as exc:
    choices = ", ".join(sorted(FEATURE_PROFILES))
    raise ValueError(f"Unknown feature profile {name!r}; choose one of: {choices}") from exc


class FeatureMatrix:
  """Precompute normalized features once. All causal (no look-ahead)."""

  def __init__(self, df: pd.DataFrame, profile: str = "current"):
    self.df = df
    self.index = df.index
    self.n = len(df)
    self.profile_name = _PROFILE_ALIASES.get(profile, profile)
    self.profile = get_feature_profile(profile)
    self.close = df["Close"].values.astype(np.float64)
    self.open = df["Open"].values.astype(np.float64)
    self.high = df["High"].values.astype(np.float64)
    self.low = df["Low"].values.astype(np.float64)
    self.utc_hours = df.index.hour.values
    broker_index = pd.DatetimeIndex([
      history_sync.utc_to_broker_time(timestamp) for timestamp in df.index
    ])
    self.broker_hours = broker_index.hour.values
    self.hours = (
      self.broker_hours if self.profile.broker_sessions else self.utc_hours
    )
    self.atr = atr(
      df["High"], df["Low"], df["Close"], self.profile.atr_period
    ).values

    self.features: dict[str, np.ndarray] = {}
    self._build()

  def _pct_rank(self, arr: np.ndarray, window: int) -> np.ndarray:
    s = pd.Series(arr)
    return s.rolling(window, min_periods=window // 2).apply(
      lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min() + 1e-12), raw=False
    ).values

  def _zscore(self, arr: np.ndarray, window: int) -> np.ndarray:
    s = pd.Series(arr)
    m = s.rolling(window, min_periods=window // 2).mean()
    std = s.rolling(window, min_periods=window // 2).std()
    return ((s - m) / std.replace(0, np.nan)).values

  def _build(self):
    c, o, h, l = self.close, self.open, self.high, self.low
    n = self.n
    p = self.profile

    # --- Trend ---
    e8 = ema(self.df["Close"], p.ema_fast).values
    e21 = ema(self.df["Close"], p.ema_slow).values
    e50 = ema(self.df["Close"], p.ema_trend).values
    e200 = ema(self.df["Close"], p.ema_long).values
    self.features["ema_slope_8"] = np.concatenate([[np.nan], np.diff(e8) / (self.atr[1:] + 1e-12)])
    self.features["ema_slope_21"] = np.concatenate([[np.nan], np.diff(e21) / (self.atr[1:] + 1e-12)])
    self.features["price_vs_ema21"] = (c - e21) / (self.atr + 1e-12)
    self.features["price_vs_ema50"] = (c - e50) / (self.atr + 1e-12)
    self.features["ema_stack_bull"] = ((e8 > e21) & (e21 > e50)).astype(float)
    self.features["ema_stack_bear"] = ((e8 < e21) & (e21 < e50)).astype(float)

    if p.causal_h4:
      # Label each H4 aggregate at its close. Thus an M15 bar can only inherit
      # an H4 value after all M15 bars in that H4 candle have closed.
      h4 = self.df.resample("4h", closed="left", label="right").agg(
        {"Close": "last"}
      ).dropna()
    else:
      # Compatibility for already-deployed feature-schema-v2 models.
      h4 = self.df.resample("4h").agg({"Close": "last"}).dropna()
    h4_e50 = ema(h4["Close"], p.ema_trend).values
    h4_e200 = ema(h4["Close"], p.ema_long).values
    h4_trend = np.where(h4_e50 > h4_e200, 1.0, np.where(h4_e50 < h4_e200, -1.0, 0.0))
    self.features["htf_trend"] = pd.Series(h4_trend, index=h4.index).reindex(
      self.df.index, method="ffill"
    ).fillna(0).values

    # --- Momentum ---
    self.features["rsi"] = rsi(self.df["Close"], p.rsi_period).values
    self.features["rsi_slope"] = np.concatenate([[np.nan], np.diff(self.features["rsi"])])
    m_line, s_line, hist = macd(self.df["Close"])
    self.features["macd_hist"] = hist.values / (self.atr + 1e-12)
    self.features["macd_cross_up"] = ((hist > 0) & (hist.shift(1) <= 0)).astype(float).values
    self.features["macd_cross_dn"] = ((hist < 0) & (hist.shift(1) >= 0)).astype(float).values
    roc = pd.Series(c).pct_change(p.roc_period).values * 100
    self.features["roc_5"] = roc / (roc[~np.isnan(roc)].std() + 1e-12) if np.any(~np.isnan(roc)) else roc

    # --- Volatility / Regime ---
    self.features["adx"] = adx(
      self.df["High"], self.df["Low"], self.df["Close"], p.adx_period
    ).values
    self.features["atr_pct"] = self._pct_rank(self.atr, p.percentile_period)
    bb_u, bb_m, bb_l = bollinger_bands(self.df["Close"], p.bb_period, 2.0)
    bb_u, bb_m, bb_l = bb_u.values, bb_m.values, bb_l.values
    self.features["bb_width"] = (bb_u - bb_l) / (bb_m + 1e-12)
    self.features["bb_width_pct"] = self._pct_rank(
      self.features["bb_width"], p.percentile_period
    )
    self.features["bb_pos"] = (c - bb_l) / (bb_u - bb_l + 1e-12)  # 0=lower, 1=upper
    self.features["zscore_20"] = self._zscore(c, p.zscore_period)

    # --- Candle microstructure ---
    body = np.abs(c - o)
    rng = h - l + 1e-12
    self.features["body_ratio"] = body / rng
    self.features["bull_candle"] = (c > o).astype(float)
    self.features["bear_candle"] = (c < o).astype(float)
    upper_wick = h - np.maximum(c, o)
    lower_wick = np.minimum(c, o) - l
    self.features["upper_wick_ratio"] = upper_wick / rng
    self.features["lower_wick_ratio"] = lower_wick / rng
    self.features["engulf_bull"] = ((c > o) & (np.roll(c, 1) < np.roll(o, 1)) &
                                    (c > np.roll(o, 1)) & (o < np.roll(c, 1))).astype(float)
    self.features["engulf_bear"] = ((c < o) & (np.roll(c, 1) > np.roll(o, 1)) &
                                    (c < np.roll(o, 1)) & (o > np.roll(c, 1))).astype(float)
    self.features["engulf_bull"][:3] = 0
    self.features["engulf_bear"][:3] = 0

    # --- Liquidity sweep (false breakout) ---
    sweep_min_periods = p.sweep_period // 2
    rh20 = pd.Series(h).rolling(
      p.sweep_period, min_periods=sweep_min_periods
    ).max().shift(1).values
    rl20 = pd.Series(l).rolling(
      p.sweep_period, min_periods=sweep_min_periods
    ).min().shift(1).values
    self.features["sweep_high_fade"] = ((h > rh20) & (c < rh20) & ~np.isnan(rh20)).astype(float)
    self.features["sweep_low_fade"] = ((l < rl20) & (c > rl20) & ~np.isnan(rl20)).astype(float)

    # --- Squeeze breakout ---
    squeeze = self.features["bb_width_pct"] < 0.25
    self.features["squeeze_break_up"] = (squeeze & (c > bb_u) & (self.features["htf_trend"] >= 0)).astype(float)
    self.features["squeeze_break_dn"] = (squeeze & (c < bb_l) & (self.features["htf_trend"] <= 0)).astype(float)

    # --- Session ---
    self.features["london_session"] = ((self.hours >= 8) & (self.hours < 16)).astype(float)
    self.features["ny_session"] = ((self.hours >= 13) & (self.hours < 21)).astype(float)
    self.features["overlap_session"] = ((self.hours >= 13) & (self.hours < 16)).astype(float)

    # --- Regime / session (v4 — đa dạng hoá mine, không tăng max rules) ---
    self.features["asia_session"] = ((self.hours >= 0) & (self.hours < 8)).astype(float)
    self.features["london_open"] = ((self.hours >= 8) & (self.hours < 11)).astype(float)
    adx_v = self.features["adx"]
    self.features["regime_trending"] = (adx_v >= 25).astype(float)
    self.features["regime_ranging"] = (adx_v < 20).astype(float)
    self.features["regime_high_vol"] = (self.features["atr_pct"] > 0.65).astype(float)
    self.features["regime_low_vol"] = (self.features["atr_pct"] < 0.35).astype(float)

    # --- Pullback in trend ---
    self.features["pullback_long"] = (
      (self.features["htf_trend"] > 0) & (self.features["ema_stack_bull"] > 0) &
      (l <= e21 * 1.001) & (c > e21) & (self.features["rsi"] > 35) & (self.features["rsi"] < 55)
    ).astype(float)
    self.features["pullback_short"] = (
      (self.features["htf_trend"] < 0) & (self.features["ema_stack_bear"] > 0) &
      (h >= e21 * 0.999) & (c < e21) & (self.features["rsi"] < 65) & (self.features["rsi"] > 45)
    ).astype(float)

    # --- Mean reversion in range ---
    ranging = self.features["adx"] < 22
    self.features["range_buy"] = (ranging & (self.features["bb_pos"] < 0.1) & (self.features["rsi"] < 35)).astype(float)
    self.features["range_sell"] = (ranging & (self.features["bb_pos"] > 0.9) & (self.features["rsi"] > 65)).astype(float)

    self.feature_names = list(self.features.keys())
    self.warmup = p.warmup

  def get(self, name: str) -> np.ndarray:
    return self.features[name]

  def slice_valid(self, start: int, end: int) -> dict[str, np.ndarray]:
    """Return features for [start, end) with warmup respected."""
    s = max(start, self.warmup)
    return {k: v[s:end] for k, v in self.features.items()}
