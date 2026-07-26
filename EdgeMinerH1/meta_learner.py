"""
Meta-learner — optimize có nhớ: epoch sau tốt hơn epoch trước.
"""
from __future__ import annotations

import hashlib
import random
import threading
from typing import Optional

import numpy as np

from knowledge_base import KnowledgeBase, rule_key
from evolution import evolve_population, apply_kb_rule_weights, mutate_genome
from ml_scorer import MLScorer, ML_FEATURES
from strategy import compute_metrics
from strategy_miner import (
  MinedStrategy, Rule, mine_strategy, generate_signals_mined, backtest_mined,
  score_strategy_metrics, _label_outcomes, _mine_threshold_rules, _mine_binary_rules,
  _count_matching_rules, CONTINUOUS_FEATURES, BINARY_LONG, BINARY_SHORT,
  _weeks_in_window,
)

_DETERMINISM_LOCK = threading.RLock()


def get_matched_rule_keys(fm, strat: MinedStrategy, bar_idx: int, direction: int) -> list[str]:
  rules = strat.long_rules if direction == 1 else strat.short_rules
  keys = []
  for r in rules:
    v = fm.get(r.feature)[bar_idx]
    if np.isnan(v):
      continue
    ok = (r.op == "eq1" and v > 0.5) or (r.op == "gt" and v > r.threshold) or (r.op == "lt" and v < r.threshold)
    if ok:
      keys.append(rule_key(r.feature, r.direction, r.op, r.threshold))
  return keys


def _fit_ml_with_experience(
  fm, train_start, train_end, long_wins, short_wins, kb: KnowledgeBase, as_of=None,
) -> MLScorer:
  """Train ML trên train window + kinh nghiệm KB chỉ trước as_of (chống leakage)."""
  ml = MLScorer()
  ml.fit(fm, train_start, train_end, long_wins, short_wins)

  cutoff = as_of if as_of is not None else fm.index[train_start]
  extra_samples = kb.ml_samples_before(cutoff)
  if len(extra_samples) < 30:
    return ml

  # Bổ sung mẫu từ KB vào training (meta-learning across epochs)
  try:
    X_extra, yl_extra, ys_extra = [], [], []
    for sample in extra_samples:
      row = [sample["features"].get(f, 0.0) for f in ML_FEATURES]
      X_extra.append(row)
      yl_extra.append(sample["long_win"])
      ys_extra.append(sample["short_win"])
    if len(X_extra) >= 30:
      from sklearn.linear_model import LogisticRegression
      from strategy_miner import _align_array
      if len(long_wins) != fm.n:
        long_wins = _align_array(long_wins, fm.n)
      if len(short_wins) != fm.n:
        short_wins = _align_array(short_wins, fm.n)
      X_all = ml.get_X(fm)
      if X_all.shape[0] != fm.n:
        return ml
      mask = np.zeros(fm.n, dtype=bool)
      mask[train_start:train_end] = True
      mask[:fm.warmup] = False
      X_train = X_all[mask]
      yl = long_wins[mask]
      ys = short_wins[mask]
      X_comb = np.vstack([X_train, np.array(X_extra)])
      yl_comb = np.concatenate([yl, np.array(yl_extra)])
      ys_comb = np.concatenate([ys, np.array(ys_extra)])
      ml.scaler.fit(X_comb)
      Xs = ml.scaler.transform(X_comb)
      if yl_comb.sum() >= 10:
        ml.long_model = LogisticRegression(max_iter=300, class_weight="balanced", C=0.5)
        ml.long_model.fit(Xs, yl_comb)
      if ys_comb.sum() >= 10:
        ml.short_model = LogisticRegression(max_iter=300, class_weight="balanced", C=0.5)
        ml.short_model.fit(Xs, ys_comb)
      X_all_s = ml.scaler.transform(X_all)
      ml._prob_long = ml.long_model.predict_proba(X_all_s)[:, 1] if ml.long_model else np.full(fm.n, 0.5)
      ml._prob_short = ml.short_model.predict_proba(X_all_s)[:, 1] if ml.short_model else np.full(fm.n, 0.5)
  except Exception:
    pass
  return ml


def _evaluate_genome(fm, strat: MinedStrategy, train_start, train_end, weeks, target_tpw=2.0) -> tuple[float, dict]:
  span = train_end - train_start
  split = train_start + int(span * 0.65)
  sig = generate_signals_mined(fm, strat, train_start, train_end)
  fit_trades = backtest_mined(fm, strat, sig, train_start, split)
  val_trades = backtest_mined(fm, strat, sig, split, train_end)
  comb = compute_metrics(fit_trades + val_trades)
  s = score_strategy_metrics(comb, weeks, target_tpw)
  val_m = compute_metrics(val_trades)
  if val_m["n_trades"] >= 2 and val_m["total_r"] < -4:
    s -= 80
  return s, comb


def mine_strategy_learning(
  fm, train_start, train_end, kb: KnowledgeBase, target_tpw: float = 2.0,
  as_of=None, *, update_kb: bool = True,
) -> Optional[MinedStrategy]:
  """Run evolution reproducibly for a given KB snapshot and train window."""
  raw_seed = (
    f"{kb.path.resolve()}|{kb.epoch_count}|{train_start}|{train_end}|"
    f"{as_of if as_of is not None else ''}"
  )
  seed = int(hashlib.sha256(raw_seed.encode("utf-8")).hexdigest()[:8], 16)
  with _DETERMINISM_LOCK:
    py_state = random.getstate()
    np_state = np.random.get_state()
    random.seed(seed)
    np.random.seed(seed)
    try:
      return _mine_strategy_learning_impl(
        fm, train_start, train_end, kb, target_tpw=target_tpw,
        as_of=as_of, update_kb=update_kb,
      )
    finally:
      random.setstate(py_state)
      np.random.set_state(np_state)


def _mine_strategy_learning_impl(
  fm, train_start, train_end, kb: KnowledgeBase, target_tpw: float = 2.0,
  as_of=None, *, update_kb: bool = True,
) -> Optional[MinedStrategy]:
  """
  Optimize có nhớ:
    1. Thử genomes từ KB (elite + đột biến) — NHANH
    2. Nếu chưa đủ tốt → mine mới + thêm vào KB
    3. Rules được boost theo rule_stats lịch sử
  """
  weeks = _weeks_in_window(train_start, train_end)
  best: Optional[MinedStrategy] = None
  best_score = -1e9

  # Chuẩn bị ML + rules cơ bản (dùng chung)
  rr, atr_m = 2.5, 0.95
  if kb.genomes:
    top = kb.top_genomes(1)[0]
    rr, atr_m = top.get("rr_ratio", 2.5), top.get("atr_mult_sl", 0.95)

  long_wins, short_wins = _label_outcomes(fm, train_start, train_end, rr, atr_m)
  ml = _fit_ml_with_experience(fm, train_start, train_end, long_wins, short_wins, kb, as_of=as_of)

  # --- Phase 1: Đánh giá genomes từ KB (evolution) ---
  candidates: list[dict] = []
  if kb.genomes:
    candidates.extend(evolve_population(kb, n_offspring=10))
    candidates.extend(kb.top_genomes(3))

  for g in candidates:
    strat = kb.dict_to_strategy(g)
    strat.ml_scorer = ml
    strat = apply_kb_rule_weights(strat, kb, as_of=as_of)
    s, comb = _evaluate_genome(fm, strat, train_start, train_end, weeks, target_tpw)
    if comb["n_trades"] >= 2 and s > best_score:
      best_score, best = s, strat

  # --- Phase 2: Nếu KB chưa có gì tốt, mine mới ---
  if best_score < 50 or best is None:
    fresh = mine_strategy(fm, train_start, train_end, target_tpw)
    if fresh:
      fresh.ml_scorer = ml
      fresh = apply_kb_rule_weights(fresh, kb, as_of=as_of)
      s, comb = _evaluate_genome(fm, fresh, train_start, train_end, weeks, target_tpw)
      if s > best_score:
        best_score, best = s, fresh

  # --- Phase 3: Đột biến nhẹ quanh best ---
  if best is not None:
    g = kb.genome_to_dict(best, best_score)
    for _ in range(6):
      mutant_g = mutate_genome(g, rate=0.15)
      mutant = kb.dict_to_strategy(mutant_g)
      mutant.ml_scorer = ml
      mutant = apply_kb_rule_weights(mutant, kb, as_of=as_of)
      s, comb = _evaluate_genome(fm, mutant, train_start, train_end, weeks, target_tpw)
      if comb["n_trades"] >= 2 and s > best_score:
        best_score, best = s, mutant

  if best is not None and update_kb:
    kb.add_genome(best, best_score)

  return best


def record_trade_learning(
  kb: KnowledgeBase, fm, strat: MinedStrategy,
  entry_bar_idx: int, direction: int, r_multiple: float,
):
  """Ghi nhận kết quả lệnh → cập nhật rule stats + ML experience."""
  keys = get_matched_rule_keys(fm, strat, entry_bar_idx, direction)
  entry_time = fm.index[entry_bar_idx]
  kb.record_rule_outcomes(keys, r_multiple, entry_time=entry_time)

  feat_row = {f: float(fm.get(f)[entry_bar_idx]) for f in ML_FEATURES if not np.isnan(fm.get(f)[entry_bar_idx])}
  long_w = 1 if direction == 1 and r_multiple > 0 else 0
  short_w = 1 if direction == -1 and r_multiple > 0 else 0
  kb.add_ml_sample(feat_row, long_w, short_w, entry_time=entry_time)
