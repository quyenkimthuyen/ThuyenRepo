"""Walk-forward optimizer — uses learning KB when available."""
from typing import Optional

from feature_engine import FeatureMatrix
from knowledge_base import KnowledgeBase
from meta_learner import mine_strategy_learning
from strategy_miner import mine_strategy, MinedStrategy

TARGET_TRADES_PER_WEEK = 2.0
_kb: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
  global _kb
  if _kb is None:
    _kb = KnowledgeBase()
  return _kb


def optimize_on_window(
  fm: FeatureMatrix,
  train_start_idx: int,
  train_end_idx: int,
  use_learning: bool = True,
  as_of=None,
) -> Optional[MinedStrategy]:
  if use_learning:
    return mine_strategy_learning(
      fm, train_start_idx, train_end_idx, get_knowledge_base(), as_of=as_of,
    )
  return mine_strategy(fm, train_start_idx, train_end_idx, TARGET_TRADES_PER_WEEK)
