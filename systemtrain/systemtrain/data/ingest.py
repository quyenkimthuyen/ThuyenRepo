from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

REQUIRED_COLUMNS = ["open", "high", "low", "close"]


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Dukascopy or CSV dataframe to standard OHLCV index."""
    out = df.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        for col in ("timestamp", "datetime", "time", "date"):
            if col in out.columns:
                out[col] = pd.to_datetime(out[col], utc=True)
                out = out.set_index(col)
                break
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")

    out.columns = [c.lower().strip() for c in out.columns]
    rename = {}
    for c in out.columns:
        if c in ("o", "open"):
            rename[c] = "open"
        elif c in ("h", "high"):
            rename[c] = "high"
        elif c in ("l", "low"):
            rename[c] = "low"
        elif c in ("c", "close"):
            rename[c] = "close"
        elif c in ("v", "vol", "volume"):
            rename[c] = "volume"
    out = out.rename(columns=rename)

    for col in REQUIRED_COLUMNS:
        if col not in out.columns:
            raise ValueError(f"Missing column: {col}")
    if "volume" not in out.columns:
        out["volume"] = 0.0

    out = out.sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out[REQUIRED_COLUMNS + ["volume"]].astype(
        {"open": float, "high": float, "low": float, "close": float, "volume": float}
    )


def load_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    df = pd.read_csv(path)
    df.columns = [c.lower().strip() for c in df.columns]
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
        df = df.set_index("datetime")
    elif "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp")
    elif "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], utc=True)
        df = df.set_index("time")
    elif "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.set_index("date")
    else:
        df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0], utc=True)
        df = df.set_index(df.columns[0])
    return _normalize_ohlcv(df)


def download_eurusd_15m_dukascopy(
    years: int = 3,
    end: datetime | None = None,
    chunk_months: int = 1,
    on_progress: Callable | None = None,
) -> pd.DataFrame:
    """Download EURUSD 15m OHLCV from Dukascopy (UTC)."""
    import dukascopy_python
    from dukascopy_python.instruments import INSTRUMENT_FX_MAJORS_EUR_USD

    end = end or datetime.now(timezone.utc).replace(tzinfo=None)
    start = end - timedelta(days=365 * years)

    chunks: list[pd.DataFrame] = []
    cursor = start
    total_months = years * 12 + 1
    done = 0

    while cursor < end:
        chunk_end = min(cursor + timedelta(days=31 * chunk_months), end)
        if on_progress:
            on_progress(cursor, chunk_end, done, total_months)

        part = dukascopy_python.fetch(
            INSTRUMENT_FX_MAJORS_EUR_USD,
            dukascopy_python.INTERVAL_MIN_15,
            dukascopy_python.OFFER_SIDE_BID,
            cursor,
            chunk_end,
        )
        if part is not None and len(part) > 0:
            chunks.append(_normalize_ohlcv(part))

        cursor = chunk_end
        done += chunk_months

    if not chunks:
        raise RuntimeError("No data downloaded from Dukascopy")

    df = pd.concat(chunks).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def save_parquet(df: pd.DataFrame, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return path


def save_csv(df: pd.DataFrame, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    out.insert(0, "datetime", out.index)
    out.to_csv(path, index=False)
    return path


def load_parquet(path: str | Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    return _normalize_ohlcv(df)


def ensure_data(
    data_dir: str | Path,
    years: int = 3,
    force_regenerate: bool = False,
    prefer_real: bool = True,
) -> pd.DataFrame:
    """Load cached EURUSD 15m data; download from Dukascopy if missing."""
    data_dir = Path(data_dir)
    parquet_path = data_dir / "eurusd_15m.parquet"
    csv_path = data_dir / "eurusd_15m.csv"

    if parquet_path.exists() and not force_regenerate:
        return load_parquet(parquet_path)
    if csv_path.exists() and not force_regenerate:
        df = load_csv(csv_path)
        save_parquet(df, parquet_path)
        return df

    if prefer_real:
        df = download_eurusd_15m_dukascopy(years=years)
        save_parquet(df, parquet_path)
        save_csv(df, csv_path)
        return df

    from systemtrain.data.synthetic import generate_synthetic_eurusd

    df = generate_synthetic_eurusd(years=years)
    save_parquet(df, parquet_path)
    return df
