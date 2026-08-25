"""Journal timestamps mix MT5 bar (no seconds) and broker (with seconds)."""
from __future__ import annotations

from analytics import trades_json_to_df
from gui.bridge_model_monitor import live_trades_to_analytics_df


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
