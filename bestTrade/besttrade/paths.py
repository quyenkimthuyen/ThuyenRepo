"""Resolve paths to SystemTrain sibling project."""

from __future__ import annotations

import sys
from pathlib import Path

BESTTRADE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BESTTRADE_ROOT.parent
SYSTEMTRAIN_ROOT = REPO_ROOT / "systemtrain"


def ensure_systemtrain_on_path() -> Path:
    root = SYSTEMTRAIN_ROOT
    if not root.is_dir():
        raise FileNotFoundError(
            f"SystemTrain not found at {root}. "
            "BestTrade requires the systemtrain project as a sibling directory."
        )
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root
