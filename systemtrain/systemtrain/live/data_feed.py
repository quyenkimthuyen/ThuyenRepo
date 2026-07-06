from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from systemtrain.config import Config
from systemtrain.data.ingest import load_parquet, save_parquet
from systemtrain.data.timeframes import to_entry_timeframe


def _closed_1h_bars(df_1h: pd.DataFrame, as_of: datetime | None = None) -> pd.DataFrame:
    if df_1h.empty:
        return df_1h
    now = as_of or datetime.now(timezone.utc)
    cutoff = pd.Timestamp(now).floor("h")
    if cutoff.tzinfo is None:
        cutoff = cutoff.tz_localize("UTC")
    else:
        cutoff = cutoff.tz_convert("UTC")
    return df_1h[df_1h.index < cutoff].copy()


def load_cached_15m(config: Config | None = None) -> pd.DataFrame:
    config = config or Config.load()
    data_dir = Path(config.data.get("data_dir", "data/store"))
    parquet_path = data_dir / "eurusd_15m.parquet"
    if not parquet_path.exists():
        from systemtrain.data.ingest import ensure_data

        return ensure_data(data_dir, years=config.data.get("years", 3), prefer_real=True)
    return load_parquet(parquet_path)


def refresh_recent_15m(
    config: Config | None = None,
    *,
    lookback_days: int = 7,
) -> pd.DataFrame:
    """Refresh recent Dukascopy data and merge it into the local cache."""
    import dukascopy_python
    from dukascopy_python.instruments import INSTRUMENT_FX_MAJORS_EUR_USD

    config = config or Config.load()
    data_dir = Path(config.data.get("data_dir", "data/store"))
    parquet_path = data_dir / "eurusd_15m.parquet"
    cached = load_cached_15m(config)
    end = datetime.now(timezone.utc).replace(tzinfo=None)
    cached_last = cached.index.max()
    start_ts = max(
        pd.Timestamp(end - timedelta(days=lookback_days), tz="UTC"),
        cached_last - pd.Timedelta(days=2),
    )
    recent = dukascopy_python.fetch(
        INSTRUMENT_FX_MAJORS_EUR_USD,
        dukascopy_python.INTERVAL_MIN_15,
        dukascopy_python.OFFER_SIDE_BID,
        start_ts.to_pydatetime().replace(tzinfo=None),
        end,
    )
    if recent is None or len(recent) == 0:
        return cached
    from systemtrain.data.ingest import _normalize_ohlcv

    recent = _normalize_ohlcv(recent)
    merged = pd.concat([cached, recent]).sort_index()
    merged = merged[~merged.index.duplicated(keep="last")]
    save_parquet(merged, parquet_path)
    return merged


def load_live_buffer(
    *,
    refresh: bool = False,
    warmup_days: int = 90,
    max_bars: int = 3000,
    config: Config | None = None,
) -> pd.DataFrame:
    """Return closed 1H bars with enough warmup for live signal evaluation."""
    config = config or Config.load()
    df_15m = refresh_recent_15m(config) if refresh else load_cached_15m(config)
    df_1h = to_entry_timeframe(df_15m, config.entry_timeframe or "1h")
    df_1h = _closed_1h_bars(df_1h)
    if warmup_days > 0 and not df_1h.empty:
        start = df_1h.index.max() - pd.Timedelta(days=warmup_days)
        df_1h = df_1h[df_1h.index >= start]
    if max_bars > 0 and len(df_1h) > max_bars:
        df_1h = df_1h.iloc[-max_bars:].copy()
    return df_1h

