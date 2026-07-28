from __future__ import annotations

import random
from pathlib import Path

import numpy as np

import meta_learner


class _FakeKb:
  path = Path("learning/kb_profiles/test.json")
  epoch_count = 4


def test_learning_optimizer_is_deterministic_and_restores_rng(monkeypatch):
  seen_update_flags: list[bool] = []

  def fake_impl(*args, update_kb=True, **kwargs):
    seen_update_flags.append(update_kb)
    return random.random(), float(np.random.random())

  monkeypatch.setattr(meta_learner, "_mine_strategy_learning_impl", fake_impl)
  py_state = random.getstate()
  np_state = np.random.get_state()
  first = meta_learner.mine_strategy_learning(
    object(), 10, 20, _FakeKb(), as_of="2026-07-20", update_kb=False,
  )
  second = meta_learner.mine_strategy_learning(
    object(), 10, 20, _FakeKb(), as_of="2026-07-20", update_kb=False,
  )

  assert first == second
  assert seen_update_flags == [False, False]
  assert random.getstate() == py_state
  after_np = np.random.get_state()
  assert after_np[0] == np_state[0]
  assert np.array_equal(after_np[1], np_state[1])
