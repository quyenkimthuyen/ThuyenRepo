from __future__ import annotations

import pandas as pd


def split_train_oos(
    df: pd.DataFrame,
    train_years: int = 1,
    oos_years: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split chronologically: first `train_years` for training, next `oos_years` for OOS."""
    if df.empty:
        raise ValueError("Empty dataframe")
    start = df.index.min()
    train_end = start + pd.DateOffset(years=train_years)
    oos_end = train_end + pd.DateOffset(years=oos_years)
    train = df.loc[start:train_end]
    oos = df.loc[train_end:oos_end]
    # Exclude boundary overlap
    oos = oos.iloc[1:] if len(oos) > 1 else oos
    if train.empty or oos.empty:
        raise ValueError(
            f"Insufficient data for split. train={len(train)} oos={len(oos)} "
            f"(need {train_years}+{oos_years} years)"
        )
    return train, oos


def slice_period(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return df.loc[start:end].copy()
