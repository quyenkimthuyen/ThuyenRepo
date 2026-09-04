"""Journal timestamps mix MT5 bar (no seconds) and broker (with seconds)."""
from __future__ import annotations

from analytics import trades_json_to_df, weekly_breakdown
from gui.bridge_model_monitor import live_trades_to_analytics_df, build_weekly_series_figure


def test_trades_json_mixes_minute_and_second_mt5_stamps():
  df = trades_json_to_df(
    [
      {"entry": "2026.08.25 16:45", "exit": "2026.08.25 17:06:33", "r": -1.0},
      {"entry": "2026.08.25 17:08:27", "exit": "2026.08.25 18:35:21", "r": -1.18},
    ]
  )
  assert len(df) == 2
  assert df["entry"].iloc[0] == pd_ts("2026-08-25 16:45:00")
  assert df["entry"].iloc[1] == pd_ts("2026-08-25 17:08:27")


def test_live_monitor_maps_mixed_journal_entry_times():
  df = live_trades_to_analytics_df(
    [
      {
        "status": "CLOSED",
        "r": -1.0,
        "entry_time": "2026.08.25 16:45",
        "exit_time": "2026.08.25 17:06:33",
        "direction": "SELL",
      },
      {
        "status": "CLOSED",
        "r": -1.18,
        "entry_time": "2026.08.25 17:08:27",
        "exit_time": "2026.08.25 18:35:21",
        "direction": "SELL",
      },
    ]
  )
  assert len(df) == 2
  assert str(df["entry"].iloc[0])[:16] == "2026-08-25 16:45"


def pd_ts(s: str):
  import pandas as pd
  return pd.Timestamp(s)


def test_weekly_breakdown_monday_week_start():
  df = trades_json_to_df(
    [
      {"entry": "2026.08.24 08:00", "r": 1.0},
      {"entry": "2026.08.26 10:15", "r": -1.0},
      {"entry": "2026.08.31 07:00", "r": 2.0},
    ]
  )
  w = weekly_breakdown(df)
  assert list(w["week"]) == ["2026-08-24", "2026-08-31"]
  assert list(w["n_trades"]) == [2, 1]
  assert list(w["total_r"]) == [0.0, 2.0]
  assert list(w["cum_r"]) == [0.0, 2.0]


def test_weekly_series_figure():
  w = weekly_breakdown(
    trades_json_to_df(
      [
        {"entry": "2026.08.24 08:00", "r": 1.0},
        {"entry": "2026.08.31 07:00", "r": -0.5},
      ]
    )
  )
  fig = build_weekly_series_figure(w, title="Tuần", series_name="Live Auto")
  assert fig is not None
  assert len(fig.data) == 2
  assert list(fig.data[0].x) == ["2026-08-24", "2026-08-31"]
