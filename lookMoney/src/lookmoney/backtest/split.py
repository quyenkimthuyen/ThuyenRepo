"""Temporal train/test split for fair strategy development."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TemporalSplit:
    """1 year develop + 2 years out-of-sample from dataset start."""

    data_start: pd.Timestamp
    develop_start: pd.Timestamp
    develop_end: pd.Timestamp
    oos_end: pd.Timestamp
    develop_years: float
    oos_years: float

    @classmethod
    def from_config(cls, df: pd.DataFrame, config: dict) -> TemporalSplit:
        v = config.get("validation", {})
        develop_years = float(v.get("develop_years", 1))
        oos_years = float(v.get("oos_years", 2))
        return cls.from_data(df, develop_years=develop_years, oos_years=oos_years)

    @classmethod
    def from_data(
        cls,
        df: pd.DataFrame,
        *,
        develop_years: float = 1,
        oos_years: float = 2,
    ) -> TemporalSplit:
        if df.empty:
            raise ValueError("Cannot build temporal split from empty dataframe")

        data_start = pd.Timestamp(df.index[0])
        develop_start = data_start
        develop_end = data_start + pd.DateOffset(years=develop_years)
        oos_end = develop_end + pd.DateOffset(years=oos_years)

        return cls(
            data_start=data_start,
            develop_start=develop_start,
            develop_end=develop_end,
            oos_end=oos_end,
            develop_years=develop_years,
            oos_years=oos_years,
        )

    def clip_to_data(self, df: pd.DataFrame) -> TemporalSplit:
        """Cap OOS end at last available bar."""
        last = pd.Timestamp(df.index[-1])
        oos_end = min(self.oos_end, last)
        return TemporalSplit(
            data_start=self.data_start,
            develop_start=self.develop_start,
            develop_end=self.develop_end,
            oos_end=oos_end,
            develop_years=self.develop_years,
            oos_years=self.oos_years,
        )

    def develop_df(self, df: pd.DataFrame) -> pd.DataFrame:
        end = min(self.develop_end, pd.Timestamp(df.index[-1]))
        return df.loc[self.data_start:end]

    def oos_df(self, df: pd.DataFrame, *, include_warmup: bool = True) -> pd.DataFrame:
        """OOS window; optional warmup from develop period for indicators only."""
        start = self.data_start if include_warmup else self.develop_end
        end = min(self.oos_end, pd.Timestamp(df.index[-1]))
        return df.loc[start:end]

    def summary(self) -> str:
        return (
            f"Develop: {self.develop_start.date()} → {self.develop_end.date()} "
            f"({self.develop_years:g}y, tune strategy here)\n"
            f"OOS:     {self.develop_end.date()} → {self.oos_end.date()} "
            f"({self.oos_years:g}y, blind test — params frozen)"
        )
