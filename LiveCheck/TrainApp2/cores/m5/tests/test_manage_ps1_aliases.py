"""BUG-12: manage.ps1 must not silently map gbp → only G23."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MANAGE = ROOT / "manage.ps1"


def test_manage_ps1_rejects_ambiguous_gbp_alias():
  text = MANAGE.read_text(encoding="utf-8")
  assert 'gbp = "g23"' not in text
  assert 'gbpusd = "g23"' not in text
  assert "ambiguous" in text.lower() or "Ambiguous" in text
  assert 'gbp15 = "g23"' in text
  assert 'gbp5 = "g33"' in text


def test_manage_ps1_rejects_ambiguous_eur_alias():
  """R-04: eur/eurusd must not silently map only to E21."""
  text = MANAGE.read_text(encoding="utf-8")
  assert 'eur = "e21"' not in text
  assert 'eurusd = "e21"' not in text
  assert "E21=M15 vs E31=M5" in text or "e21 or e31" in text
  assert 'eur15 = "e21"' in text
  assert 'eur5 = "e31"' in text
