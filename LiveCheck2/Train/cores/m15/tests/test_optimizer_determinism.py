from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

import meta_learner


class _FakeKb:
  path = Path("learning/kb_profiles/test.json")
  epoch_count = 4


class _FakeFm:
  """Minimal stand-in carrying the bar index the seed reads."""

  profile_name = "current"

  def __init__(self, start: str, n: int = 4000):
    self.index = pd.date_range(start, periods=n, freq="15min")
    self.n = n


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


def test_learning_seed_survives_moving_the_repo():
  """Two checkouts of the same era must draw the same evolution.

  The seed used to hash the resolved KB path, so the identical era learned under
  /home/... and under C:\\Work\\... produced different KBs and the two were
  silently incomparable.
  """
  fm = _FakeFm("2025-01-01")

  class _Linux(_FakeKb):
    path = Path("/home/u/work/LiveCheck/TrainApp/runtime/e21/learning/kb_profiles/era_2025_full.json")

  class _Windows(_FakeKb):
    path = Path("C:/Work/ThuyenRepo/LiveCheck2/Train/runtime/e21/learning/kb_profiles/era_2025_full.json")

  a = meta_learner.learning_seed(fm, 96, 2016, _Linux(), as_of="2026-07-20")
  b = meta_learner.learning_seed(fm, 96, 2016, _Windows(), as_of="2026-07-20")
  assert a == b

  # Different profiles must still diverge, or every era would share one draw.
  class _Other(_FakeKb):
    path = Path("/somewhere/else/era_2025_h2.json")

  assert meta_learner.learning_seed(fm, 96, 2016, _Other(), as_of="2026-07-20") != a


def test_learning_seed_follows_the_calendar_window_not_the_bar_offset():
  """Widening the data cache must not reshuffle evolution.

  Backfilling the M15 cache 66k → 100k bars shifts every integer bar index, so a
  seed built from raw indices silently re-draws every genome for an unchanged
  calendar window.
  """
  narrow = _FakeFm("2025-01-01")
  # Same calendar window, but the frame now starts 100 bars earlier.
  wide = _FakeFm("2024-12-30")
  shift = wide.index.get_loc(narrow.index[0])

  same = meta_learner.learning_seed(
    wide, 96 + shift, 2016 + shift, _FakeKb(), as_of="2026-07-20",
  )
  assert same == meta_learner.learning_seed(
    narrow, 96, 2016, _FakeKb(), as_of="2026-07-20",
  )

  # A genuinely different window must still change the draw.
  assert meta_learner.learning_seed(
    narrow, 96, 3000, _FakeKb(), as_of="2026-07-20",
  ) != same


def test_seed_salt_draws_an_independent_sample(monkeypatch):
  """Reproducibility must not cost the ability to resample.

  One KB is a single draw from a high-variance process; the salt is what makes
  the spread measurable instead of assumed.
  """
  fm = _FakeFm("2025-01-01")
  base = meta_learner.learning_seed(fm, 96, 2016, _FakeKb(), as_of="2026-07-20")
  monkeypatch.setattr(meta_learner, "LEARNING_SEED_SALT", 1)
  salted = meta_learner.learning_seed(fm, 96, 2016, _FakeKb(), as_of="2026-07-20")
  assert salted != base
  monkeypatch.setattr(meta_learner, "LEARNING_SEED_SALT", 0)
  assert meta_learner.learning_seed(fm, 96, 2016, _FakeKb(), as_of="2026-07-20") == base
