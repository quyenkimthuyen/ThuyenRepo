"""manage.ps1 is M15-only (e21 / g23); M5 aliases are rejected."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANAGE = ROOT / "manage.ps1"


def test_manage_ps1_is_m15_only():
  text = MANAGE.read_text(encoding="utf-8")
  assert '$Apps = @("e21", "g23")' in text
  assert 'eur = "e21"' in text
  assert 'gbp = "g23"' in text
  assert "M5 desk" in text
  assert "only runs M15" in text
  assert 'e31 = @{ Port' not in text
  assert 'g33 = @{ Port' not in text
