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
  "overlap_session",
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

  def _build_X(self, fm: FeatureMatrix) -> np.ndarray:
    cols = []
    for name in self.feat_names:
      v = fm.get(name)
      cols.append(np.nan_to_num(v, nan=0.0))
    return np.column_stack(cols)

  def get_X(self, fm: FeatureMatrix) -> np.ndarray:
    if self._X_cache is None:
      self._X_cache = self._build_X(fm)
    return self._X_cache

  def fit(
    self, fm: FeatureMatrix, start: int, end: int,
    long_wins: np.ndarray, short_wins: np.ndarray,
  ) -> bool:
    X_all = self.get_X(fm)
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

    # Long model — cần đủ mẫu thắng/thua
    if yl.sum() >= 15 and (len(yl) - yl.sum()) >= 15:
      self.long_model = LogisticRegression(
        max_iter=300, class_weight="balanced", C=0.5, solver="lbfgs",
      )
      self.long_model.fit(Xs, yl)

    if ys.sum() >= 15 and (len(ys) - ys.sum()) >= 15:
      self.short_model = LogisticRegression(
        max_iter=300, class_weight="balanced", C=0.5, solver="lbfgs",
      )
      self.short_model.fit(Xs, ys)

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
