"""Rich causal feature matrix for adaptive strategy mining."""
import numpy as np
import pandas as pd

from indicators import ema, rsi, atr, adx, bollinger_bands, macd


class FeatureMatrix:
  """Precompute normalized features once. All causal (no look-ahead)."""

  def __init__(self, df: pd.DataFrame):
    self.df = df
    self.index = df.index
    self.n = len(df)
    self.close = df["Close"].values.astype(np.float64)
    self.open = df["Open"].values.astype(np.float64)
    self.high = df["High"].values.astype(np.float64)
    self.low = df["Low"].values.astype(np.float64)
    self.hours = df.index.hour.values
    self.atr = atr(df["High"], df["Low"], df["Close"], 14).values

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

    # --- Trend ---
    e8 = ema(self.df["Close"], 8).values
    e21 = ema(self.df["Close"], 21).values
    e50 = ema(self.df["Close"], 50).values
    e200 = ema(self.df["Close"], 200).values
    self.features["ema_slope_8"] = np.concatenate([[np.nan], np.diff(e8) / (self.atr[1:] + 1e-12)])
    self.features["ema_slope_21"] = np.concatenate([[np.nan], np.diff(e21) / (self.atr[1:] + 1e-12)])
    self.features["price_vs_ema21"] = (c - e21) / (self.atr + 1e-12)
    self.features["price_vs_ema50"] = (c - e50) / (self.atr + 1e-12)
    self.features["ema_stack_bull"] = ((e8 > e21) & (e21 > e50)).astype(float)
    self.features["ema_stack_bear"] = ((e8 < e21) & (e21 < e50)).astype(float)

    # H4 trend mapped to H1
    h4 = self.df.resample("4h").agg({"Close": "last"}).dropna()
    h4_e50 = ema(h4["Close"], 50).values
    h4_e200 = ema(h4["Close"], 200).values
    h4_trend = np.where(h4_e50 > h4_e200, 1.0, np.where(h4_e50 < h4_e200, -1.0, 0.0))
    self.features["htf_trend"] = pd.Series(h4_trend, index=h4.index).reindex(
      self.df.index, method="ffill"
    ).fillna(0).values

    # --- Momentum ---
    self.features["rsi"] = rsi(self.df["Close"], 14).values
    self.features["rsi_slope"] = np.concatenate([[np.nan], np.diff(self.features["rsi"])])
    m_line, s_line, hist = macd(self.df["Close"])
    self.features["macd_hist"] = hist.values / (self.atr + 1e-12)
    self.features["macd_cross_up"] = ((hist > 0) & (hist.shift(1) <= 0)).astype(float).values
    self.features["macd_cross_dn"] = ((hist < 0) & (hist.shift(1) >= 0)).astype(float).values
    roc = pd.Series(c).pct_change(5).values * 100
    self.features["roc_5"] = roc / (roc[~np.isnan(roc)].std() + 1e-12) if np.any(~np.isnan(roc)) else roc

    # --- Volatility / Regime ---
    self.features["adx"] = adx(self.df["High"], self.df["Low"], self.df["Close"], 14).values
    self.features["atr_pct"] = self._pct_rank(self.atr, 50)
    bb_u, bb_m, bb_l = bollinger_bands(self.df["Close"], 20, 2.0)
    bb_u, bb_m, bb_l = bb_u.values, bb_m.values, bb_l.values
    self.features["bb_width"] = (bb_u - bb_l) / (bb_m + 1e-12)
    self.features["bb_width_pct"] = self._pct_rank(self.features["bb_width"], 50)
    self.features["bb_pos"] = (c - bb_l) / (bb_u - bb_l + 1e-12)  # 0=lower, 1=upper
    self.features["zscore_20"] = self._zscore(c, 20)

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
    rh20 = pd.Series(h).rolling(20, min_periods=10).max().shift(1).values
    rl20 = pd.Series(l).rolling(20, min_periods=10).min().shift(1).values
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
    self.warmup = 120

  def get(self, name: str) -> np.ndarray:
    return self.features[name]

  def slice_valid(self, start: int, end: int) -> dict[str, np.ndarray]:
    """Return features for [start, end) with warmup respected."""
    s = max(start, self.warmup)
    return {k: v[s:end] for k, v in self.features.items()}
