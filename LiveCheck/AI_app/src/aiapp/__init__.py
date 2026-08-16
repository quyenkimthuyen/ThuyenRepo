"""AIEdge — protocol-first training & trading lab.

Design pillars:
1. Locked train / validate / test calendar (test never used for selection).
2. Realistic spread/slip from broker observations.
3. Tiny search space; select by robust_score on validate.
4. Compare harness vs TrainApp on the same locked test window.
"""
from __future__ import annotations

__version__ = "1.0.0"
