"""Market data from MetaTrader 5 terminal (demo or live)."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from lookmoney.data.fetcher import _normalize_ohlcv


def _require_mt5():
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise RuntimeError(
            "MetaTrader5 package not installed. Run: pip install MetaTrader5"
        ) from exc
    return mt5


def connect_mt5(mt5_cfg: dict) -> None:
    """Initialize MT5 terminal connection. Terminal must be open and logged in."""
    mt5 = _require_mt5()
    path = mt5_cfg.get("path")
    login = mt5_cfg.get("login")
    password = mt5_cfg.get("password")
    server = mt5_cfg.get("server")

    kwargs: dict = {}
    if path:
        kwargs["path"] = path
    if login:
        kwargs["login"] = int(login)
    if password:
        kwargs["password"] = password
    if server:
        kwargs["server"] = server

    if kwargs:
        ok = mt5.initialize(**kwargs)
    else:
        ok = mt5.initialize()

    if not ok:
        code, msg = mt5.last_error()
        raise RuntimeError(f"MT5 initialize failed [{code}]: {msg}")

    account = mt5.account_info()
    if account is None:
        raise RuntimeError("MT5 connected but no account info — log in to demo terminal first")
    print(
        f"MT5 connected: {account.login} @ {account.server} "
        f"({'demo' if account.trade_mode == 0 else 'real'}) balance={account.balance:.2f}"
    )


def disconnect_mt5() -> None:
    mt5 = _require_mt5()
    mt5.shutdown()


def resolve_symbol(symbol: str) -> str:
    mt5 = _require_mt5()
    candidates = [symbol, f"{symbol}.", f"{symbol}m", f"{symbol}i", f"{symbol}.pro"]
    for name in candidates:
        info = mt5.symbol_info(name)
        if info is None:
            continue
        if not info.visible:
            mt5.symbol_select(name, True)
        return name
    raise RuntimeError(f"Symbol not found in MT5: {symbol} (tried {candidates})")


def fetch_h1_bars(symbol: str, count: int = 500, mt5_cfg: Optional[dict] = None) -> pd.DataFrame:
    """Download H1 OHLCV from MT5."""
    mt5 = _require_mt5()
    mt5_cfg = mt5_cfg or {}
    sym = resolve_symbol(symbol)
    tf = mt5_cfg.get("timeframe", "H1").upper()
    timeframe = mt5.TIMEFRAME_H4 if tf == "H4" else mt5.TIMEFRAME_H1

    rates = mt5.copy_rates_from_pos(sym, timeframe, 0, count)
    if rates is None or len(rates) == 0:
        code, msg = mt5.last_error()
        raise RuntimeError(f"MT5 copy_rates_from_pos failed [{code}]: {msg}")

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("time")
    df = df.rename(columns={"tick_volume": "volume"})
    return _normalize_ohlcv(df)


def current_bid_ask(symbol: str) -> tuple[float, float]:
    mt5 = _require_mt5()
    sym = resolve_symbol(symbol)
    tick = mt5.symbol_info_tick(sym)
    if tick is None:
        raise RuntimeError(f"No tick for {sym}")
    return float(tick.bid), float(tick.ask)
