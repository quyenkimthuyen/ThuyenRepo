"""Unit tests — cost model + causal windows + leakage hard block."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from forexforge.contracts import RunSpec
from forexforge.data_loader import get_train_window_indices
from forexforge.execution import adjust_entry_price, adjust_exit_price, round_trip_cost_pips
from forexforge.kb_profiles import create_profile, register_profile
from forexforge.leakage import LeakageError, assert_no_leakage, check_kb_leakage


FIXTURE = Path(__file__).parent / "fixtures" / "sample_h1.parquet"


def test_round_trip_cost():
  assert round_trip_cost_pips(1.0, 0.3) == pytest.approx(1.6)


def test_entry_exit_worse_for_trader():
  raw = 1.10000
  long_entry = adjust_entry_price(raw, 1, 1.0, 0.3)
  short_entry = adjust_entry_price(raw, -1, 1.0, 0.3)
  assert long_entry > raw
  assert short_entry < raw
  long_exit = adjust_exit_price(raw, 1, 1.0, 0.3)
  short_exit = adjust_exit_price(raw, -1, 1.0, 0.3)
  assert long_exit < raw
  assert short_exit > raw


def test_train_window_exclusive_as_of():
  df = pd.read_parquet(FIXTURE)
  as_of = pd.Timestamp("2023-04-01")
  start, end = get_train_window_indices(df, as_of, months=3)
  assert start is not None
  assert df.index[end - 1] < as_of
  assert df.index[start] >= as_of - pd.DateOffset(months=3)


def test_leakage_hard_block(tmp_path, monkeypatch):
  monkeypatch.setattr("forexforge.paths.LEARNING_DIR", tmp_path / "learning")
  monkeypatch.setattr("forexforge.knowledge_base.LEARNING_DIR", tmp_path / "learning")
  monkeypatch.setattr("forexforge.knowledge_base.KNOWLEDGE_PATH", tmp_path / "learning" / "knowledge.json")
  monkeypatch.setattr(
    "forexforge.kb_profiles.LEARNING_DIR", tmp_path / "learning",
  )
  monkeypatch.setattr(
    "forexforge.kb_profiles.PROFILES_DIR", tmp_path / "learning" / "kb_profiles",
  )
  monkeypatch.setattr(
    "forexforge.kb_profiles.SNAPSHOTS_DIR", tmp_path / "learning" / "kb_profiles" / "snapshots",
  )
  monkeypatch.setattr(
    "forexforge.kb_profiles.INDEX_PATH", tmp_path / "learning" / "kb_profiles" / "index.json",
  )
  monkeypatch.setattr(
    "forexforge.kb_profiles.KNOWLEDGE_PATH", tmp_path / "learning" / "knowledge.json",
  )

  create_profile("era_leak", "leak test")
  register_profile("era_leak", "leak test", "2022-01-01", "2024-06-01", epochs=1)

  check = check_kb_leakage("era_leak", date(2024, 1, 1))
  assert check.ok is False
  assert "LEAKAGE BLOCK" in check.message

  with pytest.raises(LeakageError):
    assert_no_leakage("era_leak", "2024-01-01")

  ok = check_kb_leakage("era_leak", date(2024, 7, 1))
  assert ok.ok is True


def test_runspec_dates():
  spec = RunSpec(oos_from="2024-01-01", oos_to="2024-12-31", use_kb=False)
  assert spec.oos_from == date(2024, 1, 1)
  assert spec.oos_to_str() == "2024-12-31"
