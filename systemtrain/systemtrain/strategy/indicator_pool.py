"""Shared indicator definitions for strategy generation and precomputation."""

INDICATOR_POOL = [
    ("rsi", {"period": 14}),
    ("ema", {"period": 20}),
    ("ema", {"period": 50}),
    ("sma", {"period": 20}),
    ("atr", {"period": 14}),
    ("macd", {"fast": 12, "slow": 26, "signal": 9}),
    ("macd_signal", {"fast": 12, "slow": 26, "signal": 9}),
    ("bb_upper", {"period": 20, "std_mult": 2.0}),
    ("bb_lower", {"period": 20, "std_mult": 2.0}),
    ("stoch_k", {"k_period": 14, "d_period": 3}),
    ("adx", {"period": 14}),
    ("close", {}),
    ("high", {}),
    ("low", {}),
]
