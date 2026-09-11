"""Now watch table: one row per enabled model, live actions first."""
from __future__ import annotations

import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
if str(LIVE) not in sys.path:
  sys.path.insert(0, str(LIVE))

from desk_snapshot import inspect_model_label, now_watch_rows, short_watch_name  # noqa: E402


def test_watch_lists_every_model_not_just_primary():
  snap = {
    "health_detail": {
      "books": [
        {
          "symbol": "EURUSD",
          "timeframe": "M15",
          "last": 1.16779,
          "bar_time": "2026.08.20 17:15",
          "models": [
            {
              "model_id": "tm_a",
              "label": "EURUSD M15 · WR50R53.7DD7.9",
              "action": "FLAT",
              "reason": "no_signal",
              "bar_time": "2026.08.20 17:15",
              "magic": 20263001,
            },
            {
              "model_id": "tm_b",
              "label": "EURUSD M15 · WR57.1R66.4DD3.9",
              "action": "SELL",
              "reason": "signal",
              "bar_time": "2026.08.20 17:15",
              "magic": 20263003,
            },
          ],
        },
        {
          "symbol": "GBPUSD",
          "timeframe": "M15",
          "last": 1.35412,
          "bar_time": "2026.08.20 17:15",
          "models": [
            {
              "model_id": "tm_c",
              "label": "GBPUSD M15 · WR49R47.5DD5",
              "action": "HOLD",
              "reason": "position_open",
              "bar_time": "2026.08.20 17:15",
              "magic": 20263008,
            },
          ],
        },
      ]
    },
    "decisions": [
      {
        "model_id": "tm_b",
        "action": "SELL",
        "entry": 1.16810,
        "sl": 1.16900,
        "tp": 1.16450,
      }
    ],
  }
  rows = now_watch_rows(snap)
  assert [r["model_id"] for r in rows] == ["tm_b", "tm_c", "tm_a"]
  assert rows[0]["action"] == "SELL"
  assert rows[0]["tone"] == "short"
  assert "SL" in rows[0]["levels"]
  assert rows[0]["last"] == "1.16779"
  assert rows[1]["action"] == "HOLD"
  assert rows[1]["tone"] == "hold"
  assert rows[2]["reason"] == "no_signal"
  assert rows[0]["model"] == "EURUSD M15 · WR57.1R66.4DD3.9"
  assert rows[1]["model"] == "GBPUSD M15 · WR49R47.5DD5"
  assert rows[2]["model"] == "EURUSD M15 · WR50R53.7DD7.9"


def test_watch_day_slots_taken_over_max():
  snap = {
    "health_detail": {
      "books": [
        {
          "symbol": "EURUSD",
          "timeframe": "M15",
          "bar_time": "2026.08.20 17:15",
          "models": [
            {
              "model_id": "tm_full",
              "label": "EURUSD M15 · A",
              "action": "FLAT",
              "max_trades_per_day": 2,
              "bar_time": "2026.08.20 17:15",
            },
            {
              "model_id": "tm_one",
              "label": "EURUSD M15 · B",
              "action": "HOLD",
              "max_trades_per_day": 2,
              "bar_time": "2026.08.20 17:15",
            },
            {
              "model_id": "tm_none",
              "label": "EURUSD M15 · C",
              "action": "FLAT",
              "reason": "no_slots",
              "max_trades_per_day": 2,
              "bar_time": "2026.08.20 17:15",
            },
            {
              "model_id": "tm_over",
              "label": "EURUSD M15 · D",
              "action": "FLAT",
              "max_trades_per_day": 2,
              "bar_time": "2026.08.20 17:15",
            },
          ],
        }
      ]
    },
    "decisions": [
      {"model_id": "tm_full", "action": "FLAT", "slots_remaining": 2},
      {"model_id": "tm_one", "action": "HOLD"},
      {"model_id": "tm_none", "action": "FLAT", "reason": "no_slots", "slots_remaining": 0},
    ],
    "open_trades": [
      {
        "model_id": "tm_one",
        "status": "OPEN",
        "entry_time": "2026.08.20 12:00",
      },
    ],
    "journal_trades": [
      {
        "model_id": "tm_none",
        "status": "CLOSED",
        "entry_time": "2026.08.20 08:00",
      },
      {
        "model_id": "tm_none",
        "status": "CLOSED",
        "entry_time": "2026.08.20 10:00",
      },
      {
        "model_id": "tm_over",
        "status": "CLOSED",
        "entry_time": "2026.08.20 07:30",
      },
      {
        "model_id": "tm_over",
        "status": "CLOSED",
        "entry_time": "2026.08.20 09:15",
      },
      {
        "model_id": "tm_over",
        "status": "CLOSED",
        "entry_time": "2026.08.20 18:15",
      },
    ],
  }
  by_id = {r["model_id"]: r for r in now_watch_rows(snap)}
  assert by_id["tm_full"]["day_slots"] == "0/2"
  assert by_id["tm_one"]["day_slots"] == "1/2"
  assert by_id["tm_none"]["day_slots"] == "2/2"
  assert by_id["tm_over"]["day_slots"] == "3/2"
  assert by_id["tm_over"]["day_full"] is True
  assert by_id["tm_full"]["day_full"] is False
  assert by_id["tm_full"]["day_hits"] == []
  assert [h["time"] for h in by_id["tm_one"]["day_hits"]] == ["2026.08.20 12:00"]
  assert len(by_id["tm_over"]["day_hits"]) == 3


def test_short_watch_name():
  assert short_watch_name("EURUSD M15 · WR57.1R66.4DD3.9", "EURUSD") == "EUR WR57.1"
  assert short_watch_name("GBPUSD M15 · WR43.9R29.5DD5.2", "GBPUSD") == "GBP WR43.9"


def test_watch_fallback_without_health_books():
  snap = {
    "models": [
      {"model_id": "tm_a", "label": "EURUSD M15 · A", "symbol": "EURUSD", "magic": 1},
      {"model_id": "tm_b", "label": "EURUSD M15 · B", "symbol": "EURUSD", "magic": 2},
    ],
    "decisions": [
      {"model_id": "tm_a", "action": "FLAT", "reason": "no_signal", "bar_time": "2026.08.20 10:00"},
      {"model_id": "tm_b", "action": "BUY", "reason": "signal", "bar_time": "2026.08.20 10:00", "entry": 1.1},
    ],
    "bar": {"close": 1.12},
  }
  rows = now_watch_rows(snap)
  assert len(rows) == 2
  assert rows[0]["action"] == "BUY"
  assert rows[1]["action"] == "FLAT"


def test_inspect_model_label_uses_period_count():
  row = {
    "model": "EURUSD M15 · WR57.6R102.7DD5.8",
    "period_counts": {"today": 1, "week": 3, "month": 8, "all": 12},
  }
  assert inspect_model_label(row) == "EURUSD M15 · WR57.6R102.7DD5.8 · D(1)"
  assert inspect_model_label(row, period="week") == "EURUSD M15 · WR57.6R102.7DD5.8 · W(3)"
  assert inspect_model_label(row, period="month") == "EURUSD M15 · WR57.6R102.7DD5.8 · M(8)"
  assert inspect_model_label(row, period="all") == "EURUSD M15 · WR57.6R102.7DD5.8 · ALL(12)"
  assert inspect_model_label({"model": "GBP WR45.6", "period_n": 3}, period="week") == "GBP WR45.6 · W(3)"
  assert inspect_model_label({"model": "EUR WR50", "period_n": 0}, period="month") == "EUR WR50 · M(0)"
  assert inspect_model_label({"model": "EUR WR50"}) == "EUR WR50"
