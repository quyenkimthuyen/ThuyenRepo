from __future__ import annotations

import pandas as pd

from systemtrain.data.htf import add_htf_features
from systemtrain.indicators.library import compute_indicator
from systemtrain.learn.features import add_learning_features
from systemtrain.strategy.indicator_pool import INDICATOR_POOL


def indicator_column_key(spec: dict) -> str:
    name = spec["name"]
    params = sorted((k, v) for k, v in spec.items() if k != "name")
    param_str = "_".join(f"{k}{v}" for k, v in params)
    return f"__ind_{name}_{param_str}" if param_str else f"__ind_{name}"


def prepare_dataframe(df: pd.DataFrame, htf_rule: str = "4h") -> pd.DataFrame:
    """Precompute 4H HTF filter, learning features, and standard indicators."""
    out = add_htf_features(df, htf_rule=htf_rule)
    out = add_learning_features(out)

    specs: list[dict] = []
    for name, params in INDICATOR_POOL:
        specs.append({"name": name, **params})
    for period in (10, 14, 20):
        specs.append({"name": "atr", "period": period})

    seen: set[str] = set()
    for spec in specs:
        key = indicator_column_key(spec)
        if key in seen:
            continue
        seen.add(key)
        out[key] = compute_indicator(df, spec["name"], {k: v for k, v in spec.items() if k != "name"})
    return out
