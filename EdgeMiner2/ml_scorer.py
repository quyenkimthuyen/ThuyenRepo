"""ML probability scorer — train on forward labels, filter signals."""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from feature_engine import FeatureMatrix

ML_FEATURES = [
  "rsi", "adx", "bb_pos", "bb_width_pct", "atr_pct", "zscore_20",
  "price_vs_ema21", "price_vs_ema50", "ema_slope_8", "ema_slope_21",
  "macd_hist", "roc_5", "body_ratio", "htf_trend", "bb_width",
  "lower_wick_ratio", "upper_wick_ratio", "ema_stack_bull", "ema_stack_bear",
  "sweep_low_fade", "sweep_high_fade", "pullback_long", "pullback_short",
  "squeeze_break_up", "squeeze_break_dn", "range_buy", "range_sell",
  "overlap_session", "asia_session", "london_open",
  "regime_trending", "regime_ranging", "regime_high_vol", "regime_low_vol",
  # Price-action / confluence upgrade
  "rejection_bull", "rejection_bear",
  "displacement_bull", "displacement_bear",
  "structure_break_up", "structure_break_dn",
  "session_vwap_dist", "swing_strength",
  "confluence_long", "confluence_short",
]


class MLScorer:
  def __init__(self):
    self.long_model: LogisticRegression | None = None
    self.short_model: LogisticRegression | None = None
    self.scaler = StandardScaler()
    self.feat_names = ML_FEATURES
    self._X_cache: np.ndarray | None = None
    self._prob_long: np.ndarray | None = None
    self._prob_short: np.ndarray | None = None
    self._fm_n: int | None = None

  def _reset_cache(self):
    self._X_cache = None
    self._prob_long = None
    self._prob_short = None
    self._fm_n = None

  def _build_X(self, fm: FeatureMatrix) -> np.ndarray:
    cols = []
    for name in self.feat_names:
      try:
        v = fm.get(name)
      except (KeyError, AttributeError):
        v = np.zeros(fm.n)
      if len(v) != fm.n:
        raise ValueError(f"Feature {name} length {len(v)} != fm.n {fm.n}")
      cols.append(np.nan_to_num(v, nan=0.0))
    base = np.column_stack(cols)
    # Lightweight PA interactions (still linear-model friendly)
    idx = {name: i for i, name in enumerate(self.feat_names)}

    def col(name: str) -> np.ndarray:
      return base[:, idx[name]]

    extras = [
      col("htf_trend") * col("rsi"),
      col("htf_trend") * col("ema_slope_21"),
      col("confluence_long") * col("adx"),
      col("confluence_short") * col("adx"),
      col("session_vwap_dist") * col("bb_pos"),
      col("rejection_bull") * col("sweep_low_fade"),
      col("rejection_bear") * col("sweep_high_fade"),
    ]
    return np.column_stack([base, *extras])

  def get_X(self, fm: FeatureMatrix) -> np.ndarray:
    if self._X_cache is not None and self._fm_n != fm.n:
      self._reset_cache()
    if self._X_cache is None:
      self._X_cache = self._build_X(fm)
      self._fm_n = fm.n
    return self._X_cache

  def _fit_side(self, Xs: np.ndarray, y: np.ndarray) -> LogisticRegression | None:
    wins = int(y.sum())
    losses = int(len(y) - wins)
    if wins < 15 or losses < 15:
      return None
    # Slightly stronger L2 when sample-rich to curb overfit on PA interactions
    c = 0.35 if (wins >= 40 and losses >= 40 and Xs.shape[0] >= 200) else 0.5
    model = LogisticRegression(
      max_iter=400, class_weight="balanced", C=c, solver="lbfgs",
    )
    model.fit(Xs, y)
    return model

  def fit(
    self, fm: FeatureMatrix, start: int, end: int,
    long_wins: np.ndarray, short_wins: np.ndarray,
  ) -> bool:
    from strategy_miner import _align_array

    if len(long_wins) != fm.n:
      long_wins = _align_array(long_wins, fm.n)
    if len(short_wins) != fm.n:
      short_wins = _align_array(short_wins, fm.n)

    X_all = self.get_X(fm)
    if X_all.shape[0] != fm.n:
      self._reset_cache()
      X_all = self.get_X(fm)
    if X_all.shape[0] != fm.n:
      return False

    mask = np.zeros(fm.n, dtype=bool)
    mask[start:end] = True
    mask[:fm.warmup] = False

    X = X_all[mask]
    yl = long_wins[mask]
    ys = short_wins[mask]

    if len(X) < 80:
      return False

    self.scaler.fit(X)
    Xs = self.scaler.transform(X)

    self.long_model = self._fit_side(Xs, yl)
    self.short_model = self._fit_side(Xs, ys)

    # Precompute probabilities for entire series
    X_all_s = self.scaler.transform(X_all)
    self._prob_long = np.full(fm.n, 0.5)
    self._prob_short = np.full(fm.n, 0.5)
    if self.long_model is not None:
      self._prob_long = self.long_model.predict_proba(X_all_s)[:, 1]
    if self.short_model is not None:
      self._prob_short = self.short_model.predict_proba(X_all_s)[:, 1]

    return self.long_model is not None or self.short_model is not None

  def prob_long(self, fm: FeatureMatrix, i: int) -> float:
    if self._prob_long is not None:
      return float(self._prob_long[i])
    return 0.5

  def prob_short(self, fm: FeatureMatrix, i: int) -> float:
    if self._prob_short is not None:
      return float(self._prob_short[i])
    return 0.5
