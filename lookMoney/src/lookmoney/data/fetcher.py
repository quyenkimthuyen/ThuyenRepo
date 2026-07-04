"""Historical OHLCV data for EUR/USD."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf


COLUMNS = ["open", "high", "low", "close", "volume"]


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
    rename = {
        "adj_close": "close",
    }
    df = df.rename(columns=rename)
    keep = [c for c in COLUMNS if c in df.columns]
    out = df[keep].copy()
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    return out.sort_index()


def fetch_eurusd_h1(period: str = "730d") -> pd.DataFrame:
    """Download EUR/USD hourly bars via Yahoo Finance (EURUSD=X)."""
    ticker = yf.Ticker("EURUSD=X")
    df = ticker.history(period=period, interval="1h", auto_adjust=True)
    if df.empty:
        raise RuntimeError("No data returned for EURUSD=X. Check network or try again later.")
    return _normalize_ohlcv(df)


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load OHLCV from CSV with datetime index or 'datetime' column."""
    path = Path(path)
    df = pd.read_csv(path, parse_dates=True, index_col=0)
    df.index.name = None
    return _normalize_ohlcv(df)


def save_csv(df: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path)


def resample_ohlcv(df: pd.DataFrame, rule: str = "4h") -> pd.DataFrame:
    """Aggregate lower timeframe bars (e.g. H1 -> H4)."""
    out = (
        df.resample(rule)
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
    )
    return _normalize_ohlcv(out)


def load_eurusd_h4(path_h1: str | Path = "data/eurusd_h1.csv") -> pd.DataFrame:
    """Build H4 series from cached H1 CSV."""
    return resample_ohlcv(load_csv(path_h1), "4h")
