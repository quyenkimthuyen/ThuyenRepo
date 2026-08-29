"""R-02: thread worker must build engines on cfg bridge_dir, not import BRIDGE_DIR."""
from __future__ import annotations

import inspect

from mt5_bridge import background


def test_worker_builds_engines_on_cfg_bridge_dir():
  src = inspect.getsource(background._worker)
  assert "bridge_dir=BRIDGE_DIR" not in src
  assert "bridge_dir=bridge_dir" in src
