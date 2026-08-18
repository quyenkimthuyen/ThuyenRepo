"""BUG-08: seen-fill truncate must keep recent fingerprints, not lex-largest."""
from __future__ import annotations

import json

from mt5_bridge.background import _dump_seen_fills, _load_seen_fills, _remember_fill


def test_remember_fill_keeps_recent_not_lex_largest():
  seen: list[str] = []
  # Lex-small ids arrive first; lex-large later — truncate must drop oldest (aaa*),
  # not lexicographically small ones (sorted(...)[-N:] bug).
  for i in range(85):
    seen = _remember_fill(seen, f"aaa_{i:03d}", limit=80)
  seen = _remember_fill(seen, "zzz_new", limit=80)
  assert len(seen) == 80
  assert "aaa_000" not in seen
  assert "aaa_004" not in seen  # first five dropped
  assert "zzz_new" in seen
  assert seen[-1] == "zzz_new"


def test_dump_load_preserves_order_not_sorted():
  ordered = [f"b_{i}" for i in range(3)] + [f"a_{i}" for i in range(3)]
  dumped = _dump_seen_fills(ordered, limit=80)
  assert json.loads(dumped) == ordered
  assert _load_seen_fills(dumped) == ordered
  # Contrast: lex sort would rearrange
  assert json.loads(dumped) != sorted(ordered)
