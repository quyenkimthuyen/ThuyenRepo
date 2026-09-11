"""BUG-06: risk_cap interprocess lock must not proceed unlocked on timeout."""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

LIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVE))

from file_lock import interprocess_lock  # noqa: E402


def test_interprocess_lock_raises_on_timeout(tmp_path):
  lock_path = tmp_path / "risk_cap.lock"
  held = threading.Event()
  release = threading.Event()

  def holder():
    with interprocess_lock(lock_path, timeout_sec=5.0):
      held.set()
      release.wait(timeout=5.0)

  t = threading.Thread(target=holder, daemon=True)
  t.start()
  assert held.wait(timeout=2.0)
  with pytest.raises(TimeoutError):
    with interprocess_lock(lock_path, timeout_sec=0.3):
      pass
  release.set()
  t.join(timeout=2.0)
