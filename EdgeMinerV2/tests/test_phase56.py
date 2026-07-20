"""Phase 5/6 tests — guardrails, broker stub, paper journal."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from forexforge.broker import BrokerOrder, StubBroker
from forexforge.contracts import CostModel, JobKind, MetricsPack, Report, RunSpec
from forexforge.guardrails import MAX_EPOCHS_PER_ERA, can_promote_profile, check_epoch_limit
from forexforge.kb_profiles import create_profile, register_profile
from forexforge.paper_sim import JOURNAL_PATH, load_journal, run_paper_tick
from forexforge.data_loader import _normalize_ohlcv

FIXTURE = Path(__file__).parent / "fixtures" / "sample_h1.parquet"


def test_broker_stub():
  b = StubBroker()
  fill = b.place_market(BrokerOrder(symbol="EURUSD", side="BUY", volume=0.01))
  assert fill.status == "ACCEPTED_STUB"
  assert fill.order_id.startswith("stub-")


def test_promote_requires_holdout(tmp_path, monkeypatch):
  monkeypatch.setattr("forexforge.paths.LEARNING_DIR", tmp_path / "learning")
  monkeypatch.setattr("forexforge.knowledge_base.LEARNING_DIR", tmp_path / "learning")
  monkeypatch.setattr("forexforge.knowledge_base.KNOWLEDGE_PATH", tmp_path / "learning" / "knowledge.json")
  monkeypatch.setattr("forexforge.kb_profiles.LEARNING_DIR", tmp_path / "learning")
  monkeypatch.setattr("forexforge.kb_profiles.PROFILES_DIR", tmp_path / "learning" / "kb_profiles")
  monkeypatch.setattr(
    "forexforge.kb_profiles.SNAPSHOTS_DIR", tmp_path / "learning" / "kb_profiles" / "snapshots",
  )
  monkeypatch.setattr(
    "forexforge.kb_profiles.INDEX_PATH", tmp_path / "learning" / "kb_profiles" / "index.json",
  )
  monkeypatch.setattr(
    "forexforge.kb_profiles.KNOWLEDGE_PATH", tmp_path / "learning" / "knowledge.json",
  )
  create_profile("era_ok", "ok")
  register_profile("era_ok", "ok", "2022-01-01", "2023-12-31", epochs=2)
  v = can_promote_profile("era_ok", oos_from="2024-01-01", holdout_report=None)
  assert v.ok is False
  assert any("Hold-out" in r for r in v.reasons)

  holdout = Report(
    spec=RunSpec(kind=JobKind.BACKTEST, use_kb=True, kb_profile="era_ok"),
    holdout_forward={
      "months": 3,
      "metrics": {"total_r": 5.0, "n_trades": 10},
    },
  )
  v2 = can_promote_profile("era_ok", oos_from="2024-01-01", holdout_report=holdout)
  assert v2.ok is True


def test_epoch_limit_constant():
  assert MAX_EPOCHS_PER_ERA == 8


def test_paper_tick_writes_journal(tmp_path, monkeypatch):
  raw = pd.read_parquet(FIXTURE)
  df = _normalize_ohlcv(raw)
  # Point paper to temp journal and stub monitor data path via monkeypatch load
  journal = tmp_path / "paper_journal.jsonl"
  state = tmp_path / "paper_state.json"
  monkeypatch.setattr("forexforge.paper_sim.JOURNAL_PATH", journal)
  monkeypatch.setattr("forexforge.paper_sim.STATE_PATH", state)
  monkeypatch.setattr("forexforge.paper_sim.load_eurusd_h1", lambda *a, **k: df)
  mon = run_paper_tick(use_kb=False, spread_pips=1.0, slippage_pips=0.3)
  assert "error" not in mon or mon.get("week_start")
  assert journal.exists()
  events = load_journal(10)
  # load_journal uses module JOURNAL_PATH — rebind already done
  assert len(events) >= 1
