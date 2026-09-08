"""BUG-05: _find_open must not attach close/modify to an unrelated OPEN."""
from __future__ import annotations

from mt5_bridge.trade_journal import _find_open


def test_find_open_does_not_fallback_when_ticket_mismatches():
  trades = [
    {
      "id": "keep",
      "status": "OPEN",
      "ticket": 100,
      "signal_id": "sig_keep",
      "model_id": "tm_a",
      "magic": 1,
    },
  ]
  found = _find_open(
    trades,
    signal_id="sig_missing",
    ticket=999,
    model_id="tm_a",
    magic=1,
  )
  assert found is None


def test_find_open_matches_ticket_when_present():
  trades = [
    {"id": "a", "status": "OPEN", "ticket": 100, "signal_id": "sig_a", "model_id": "tm_a", "magic": 1},
    {"id": "b", "status": "OPEN", "ticket": 200, "signal_id": "sig_b", "model_id": "tm_a", "magic": 1},
  ]
  found = _find_open(trades, ticket=200, signal_id="sig_other", model_id="tm_a", magic=1)
  assert found is not None
  assert found["id"] == "b"


def test_find_open_fallback_allowed_without_ticket_or_signal():
  trades = [
    {"id": "only", "status": "OPEN", "ticket": 100, "signal_id": "sig_a", "model_id": "tm_a", "magic": 1},
  ]
  found = _find_open(trades, model_id="tm_a", magic=1)
  assert found is not None
  assert found["id"] == "only"


def test_find_open_rejects_wrong_model_id_even_when_magic_matches():
  """R-01: non-empty wrong model_id must not match via magic alone."""
  trades = [
    {"id": "a", "status": "OPEN", "ticket": 100, "signal_id": "sig_a", "model_id": "tm_a", "magic": 1},
  ]
  assert _find_open(trades, model_id="tm_b", magic=1) is None
  assert _find_open(trades, ticket=100, model_id="tm_b", magic=1) is None


def test_find_open_allows_legacy_empty_model_id_when_magic_matches():
  trades = [
    {"id": "legacy", "status": "OPEN", "ticket": 100, "signal_id": "sig_a", "model_id": "", "magic": 1},
  ]
  found = _find_open(trades, model_id="tm_a", magic=1)
  assert found is not None
  assert found["id"] == "legacy"
  assert _find_open(trades, model_id="tm_a", magic=2) is None
