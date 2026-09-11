"""manage.sh is M15-only (e21 / g23); M5 aliases are rejected."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANAGE = ROOT / "manage.sh"


def test_manage_sh_is_m15_only():
  text = MANAGE.read_text(encoding="utf-8")
  assert 'APPS=(e21 g23)' in text
  assert 'eur|eurusd) echo "e21"' in text
  assert 'gbp|gbpusd) echo "g23"' in text
  assert "M5 desk" in text
  assert "only runs M15" in text
  assert '[e31]=' not in text
  assert '[g33]=' not in text
