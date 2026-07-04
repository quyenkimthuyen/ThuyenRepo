from __future__ import annotations

import pandas as pd


def check_quality(df: pd.DataFrame, max_gap_minutes: int = 30) -> dict:
    """Basic OHLCV quality checks."""
    issues: list[str] = []
    for col in ["open", "high", "low", "close"]:
        if (df[col] <= 0).any():
            issues.append(f"Non-positive values in {col}")
    invalid_hl = (df["high"] < df["low"]).sum()
    if invalid_hl:
        issues.append(f"{invalid_hl} bars with high < low")
    invalid_oc = ((df["high"] < df["open"]) | (df["high"] < df["close"])).sum()
    if invalid_oc:
        issues.append(f"{invalid_oc} bars with high below open/close")
    gaps = df.index.to_series().diff().dropna()
    large_gaps = gaps[gaps > pd.Timedelta(minutes=max_gap_minutes)]
    return {
        "bars": len(df),
        "start": str(df.index.min()),
        "end": str(df.index.max()),
        "large_gaps": len(large_gaps),
        "issues": issues,
        "ok": len(issues) == 0,
    }
