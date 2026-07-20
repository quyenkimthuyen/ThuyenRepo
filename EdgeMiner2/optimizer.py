"""Walk-forward optimizer — KB profile-aware."""
from __future__ import annotations

from typing import Optional

from feature_engine import FeatureMatrix
from kb_profiles import DEFAULT_PROFILE_ID, LATEST_SNAPSHOT, load_kb, resolve_kb_path
from knowledge_base import KnowledgeBase
from meta_learner import mine_strategy_learning
from strategy_miner import mine_strategy, MinedStrategy

TARGET_TRADES_PER_WEEK = 2.0

_active_profile_id: str | None = None
_active_snapshot: int | str | None = None
_kb_instances: dict[str, KnowledgeBase] = {}


def set_kb_profile(profile_id: str | None, snapshot_epoch: int | str | None = None) -> None:
  global _active_profile_id, _active_snapshot
  _active_profile_id = profile_id or DEFAULT_PROFILE_ID
  _active_snapshot = snapshot_epoch


def get_active_kb_profile_id() -> str:
  return _active_profile_id or DEFAULT_PROFILE_ID


def get_active_kb_snapshot() -> int | str | None:
  return _active_snapshot


def _cache_key(profile_id: str, snapshot_epoch: int | str | None) -> str:
  snap = snapshot_epoch if snapshot_epoch not in (None, LATEST_SNAPSHOT, "latest") else LATEST_SNAPSHOT
  return f"{profile_id}@{snap}"


def get_knowledge_base(
  profile_id: str | None = None,
  snapshot_epoch: int | str | None = None,
) -> KnowledgeBase:
  pid = profile_id or _active_profile_id or DEFAULT_PROFILE_ID
  snap = snapshot_epoch if snapshot_epoch is not None else _active_snapshot
  key = _cache_key(pid, snap)
  if key not in _kb_instances:
    _kb_instances[key] = load_kb(pid, snap)
  return _kb_instances[key]


def reset_kb_cache() -> None:
  _kb_instances.clear()


def optimize_on_window(
  fm: FeatureMatrix,
  train_start_idx: int,
  train_end_idx: int,
  use_learning: bool = True,
  as_of=None,
  kb: KnowledgeBase | None = None,
) -> Optional[MinedStrategy]:
  if use_learning:
    kb = kb or get_knowledge_base()
    return mine_strategy_learning(
      fm, train_start_idx, train_end_idx, kb, as_of=as_of,
    )
  return mine_strategy(fm, train_start_idx, train_end_idx)
