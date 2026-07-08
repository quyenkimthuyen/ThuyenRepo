"""Services cho UI — backtest, optimize, load config."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import copy

import pandas as pd
import yaml

from systemtrain.config import Config
from systemtrain.backtest.engine import Trade
from systemtrain.live.data_feed import load_live_buffer
from systemtrain.live.paper_account import PaperTrade
from systemtrain.live.replay_runner import (
    ReplaySession,
    build_replay_engines,
    cursor_bar_time,
    init_replay_session,
    load_replay_dataframe,
    replay_to_end,
    seek_replay,
    step_replay,
    visible_replay_df,
)
from systemtrain.live.signal_runner import run_paper_once
from systemtrain.live.store import load_journal, load_session, reset_session
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.optimize.rolling_year import metrics_in_window, slice_year
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.orchestrator.rolling_production import (
    ACTIVE_PATH,
    HISTORY_DIR,
    backtest_state_on_year,
    backtest_trade_year,
    build_engines_from_state,
    current_trade_year,
    ensure_active_state,
    fill_missing_strategies,
    history_path,
    history_path_for_train_year,
    load_active_state,
    load_state_for_year,
    load_state_for_train_year,
    optimize_for_train_year,
    optimize_for_trade_year,
    save_active_state,
    save_state_for_year,
    save_state_for_train_year,
    state_from_fixed,
    state_from_fixed_train_year,
    train_year_for,
)
from systemtrain.ui.meta import STRATEGIES


def load_price_data() -> pd.DataFrame:
    config = Config.load()
    return to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")


def config_with_risk(sl_pct: float | None = None, min_rr: float | None = None) -> Config:
    config = Config.load()
    if sl_pct is not None or min_rr is not None:
        config = copy.deepcopy(config)
    if sl_pct is not None:
        config.risk["sl_pct"] = float(sl_pct)
    if min_rr is not None:
        config.risk["min_rr"] = float(min_rr)
    return config


def get_rolling_state(trade_year: int | None = None) -> dict[str, Any]:
    trade_year = trade_year or current_trade_year()
    state = load_state_for_year(trade_year)
    if state:
        return state
    active = load_active_state()
    if active and active.get("trade_year") == trade_year:
        return fill_missing_strategies(active)
    if active and active.get("train_year") == train_year_for(trade_year):
        return fill_missing_strategies({**active, "trade_year": trade_year})
    return ensure_active_state(trade_year)


def get_config_state(trade_year: int, equity: float = 1000.0) -> dict[str, Any]:
    """Load config cho tab Cấu hình — không tự chạy optimize."""
    state = load_state_for_year(trade_year)
    if state:
        return state
    return state_from_fixed(trade_year, equity)


def get_train_config_state(train_year: int, equity: float = 1000.0) -> dict[str, Any]:
    """Load config keyed by train year — không tự optimize."""
    state = load_state_for_train_year(train_year)
    if state:
        return state
    return state_from_fixed_train_year(train_year, equity)


def config_year_saved(trade_year: int) -> bool:
    if history_path(trade_year).exists():
        return True
    active = load_active_state()
    return active is not None and active.get("trade_year") == trade_year


def config_train_year_saved(train_year: int) -> bool:
    state = load_state_for_train_year(train_year)
    return state is not None and state.get("mode") != "fixed"


def merge_params(state: dict[str, Any], overrides: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Ghi đè param từ UI vào bản copy state."""
    import copy
    out = copy.deepcopy(state)
    for sname, params in overrides.items():
        if sname in out.get("strategies", {}):
            out["strategies"][sname]["params"] = {**out["strategies"][sname]["params"], **params}
    return out


def run_strategy_backtest(
    strategy: str,
    state: dict[str, Any],
    year: int,
    equity: float = 1000.0,
    sl_pct: float | None = None,
    min_rr: float | None = None,
) -> tuple[dict[str, Any], list, pd.DataFrame]:
    config = config_with_risk(sl_pct, min_rr)
    df_1h = load_price_data()
    period_df, ts, te = slice_year(df_1h, year)
    engines = dict(build_engines_from_state(state, config, equity))
    engine = engines[strategy]
    result = engine.run(period_df)
    closed = [t for t in result.trades if t.is_closed and ts <= t.entry_time <= te]
    metrics = metrics_in_window(result, ts, te, equity)
    return metrics, closed, period_df


def run_all_backtest(
    state: dict[str, Any],
    year: int,
    equity: float = 1000.0,
    sl_pct: float | None = None,
    min_rr: float | None = None,
) -> dict[str, Any]:
    config = config_with_risk(sl_pct, min_rr)
    df_1h = load_price_data()
    fake = {**state, "trade_year": year}
    period_df, ts, te = slice_year(df_1h, year)
    out: dict[str, Any] = {"year": year, "strategies": {}, "combined": 0.0}
    for sname, engine in build_engines_from_state(fake, config, equity):
        m = metrics_in_window(engine.run(period_df), ts, te, equity)
        out["strategies"][sname] = m
        out["combined"] += m.get("total_return", 0)
    return out


def run_all_strategies_backtest(
    state: dict[str, Any],
    year: int,
    equity: float = 1000.0,
    sl_pct: float | None = None,
    min_rr: float | None = None,
) -> tuple[dict[str, dict[str, Any]], pd.DataFrame]:
    """Backtest tất cả chiến lược — trả về metrics + trades từng CL."""
    config = config_with_risk(sl_pct, min_rr)
    df_1h = load_price_data()
    fake = {**state, "trade_year": year}
    period_df, ts, te = slice_year(df_1h, year)
    out: dict[str, dict[str, Any]] = {}
    for sname, engine in build_engines_from_state(fake, config, equity):
        result = engine.run(period_df)
        closed = [t for t in result.trades if t.is_closed and ts <= t.entry_time <= te]
        metrics = metrics_in_window(result, ts, te, equity)
        out[sname] = {"metrics": metrics, "trades": closed}
    return out, period_df


def run_train_config_backtest(
    state: dict[str, Any],
    trade_year: int,
    equity: float = 1000.0,
    sl_pct: float | None = None,
    min_rr: float | None = None,
) -> dict[str, Any]:
    config = config_with_risk(sl_pct, min_rr)
    return backtest_state_on_year(state, trade_year, config, equity)


def run_train_config_backtests(
    state: dict[str, Any],
    trade_years: list[int],
    equity: float = 1000.0,
    sl_pct: float | None = None,
    min_rr: float | None = None,
) -> dict[int, dict[str, Any]]:
    config = config_with_risk(sl_pct, min_rr)
    df_1h = load_price_data()
    return {
        year: backtest_state_on_year(state, year, config, equity, df_1h=df_1h)
        for year in trade_years
    }


def optimize_trade_year(trade_year: int, equity: float = 1000.0, sl_pct: float | None = None, min_rr: float | None = None) -> dict[str, Any]:
    state = optimize_for_trade_year(trade_year, config=config_with_risk(sl_pct, min_rr), equity=equity)
    if sl_pct is not None:
        state["risk_sl_pct"] = float(sl_pct)
    if min_rr is not None:
        state["risk_min_rr"] = float(min_rr)
    save_active_state(state)
    return state


def optimize_train_year(train_year: int, equity: float = 1000.0, sl_pct: float | None = None, min_rr: float | None = None) -> dict[str, Any]:
    state = optimize_train_year_candidate(train_year, equity=equity, sl_pct=sl_pct, min_rr=min_rr)
    save_state_for_train_year(state, train_year)
    return state


def optimize_train_year_candidate(train_year: int, equity: float = 1000.0, sl_pct: float | None = None, min_rr: float | None = None) -> dict[str, Any]:
    """Tạo candidate config nhưng chưa lưu, dùng cho multi-run search."""
    state = optimize_for_train_year(train_year, config=config_with_risk(sl_pct, min_rr), equity=equity)
    if sl_pct is not None:
        state["risk_sl_pct"] = float(sl_pct)
    if min_rr is not None:
        state["risk_min_rr"] = float(min_rr)
    return state


def load_base_yaml(strategy: str) -> dict[str, Any]:
    path = STRATEGIES[strategy]["base_config"]
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    key = list(raw.keys())[0] if len(raw) == 1 else strategy
    return raw.get(key, raw)


def load_history_years() -> list[int]:
    hist = Path("config/rolling/history")
    if not hist.exists():
        return []
    years = []
    for p in hist.glob("*.yaml"):
        try:
            years.append(int(p.stem))
        except ValueError:
            pass
    return sorted(years)


def load_history_train_years() -> list[int]:
    hist = Path("config/rolling/history")
    if not hist.exists():
        return []
    years: set[int] = set()
    for p in hist.glob("*.yaml"):
        try:
            raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            if "train_year" in raw:
                years.add(int(raw["train_year"]))
            else:
                years.add(int(p.stem))
        except (ValueError, TypeError):
            pass
    return sorted(years)


def load_history_year(year: int) -> dict[str, Any] | None:
    p = Path(f"config/rolling/history/{year}.yaml")
    if not p.exists():
        return None
    state = yaml.safe_load(p.read_text(encoding="utf-8"))
    return fill_missing_strategies(state) if state else None


def load_history_train_year(train_year: int) -> dict[str, Any] | None:
    return load_state_for_train_year(train_year)


def save_params_to_active(state: dict[str, Any]) -> None:
    save_active_state(state)


def save_params_for_year(
    state: dict[str, Any],
    trade_year: int,
    *,
    set_active: bool = False,
) -> Path:
    """Lưu param chỉnh sửa vào history/{năm}.yaml."""
    from datetime import datetime, timezone
    import copy
    out = copy.deepcopy(state)
    out["trade_year"] = trade_year
    out["train_year"] = train_year_for(trade_year)
    if not out.get("optimized_at"):
        out["optimized_at"] = datetime.now(timezone.utc).isoformat()
    out["saved_manually"] = True
    return save_state_for_year(out, trade_year, set_active=set_active)


def save_params_for_train_year(
    state: dict[str, Any],
    train_year: int,
    *,
    set_active: bool = False,
) -> Path:
    """Lưu param chỉnh sửa vào history/{train_year}.yaml."""
    from datetime import datetime, timezone
    import copy
    out = copy.deepcopy(state)
    out["train_year"] = train_year
    out["default_trade_year"] = train_year + 1
    out["config_key"] = "train_year"
    out.pop("trade_year", None)
    if not out.get("optimized_at"):
        out["optimized_at"] = datetime.now(timezone.utc).isoformat()
    out["saved_manually"] = True
    return save_state_for_train_year(out, train_year, set_active=set_active)


def load_live_paper_state(limit: int = 200) -> dict[str, Any]:
    return {
        "session": load_session().to_dict(),
        "journal": load_journal(limit=limit),
    }


def refresh_live_paper(
    trade_year: int,
    strategies: list[str],
    equity: float = 1000.0,
    *,
    refresh_data: bool = False,
    warmup_days: int = 90,
) -> dict[str, Any]:
    return run_paper_once(
        trade_year=trade_year,
        strategies=strategies,
        equity=equity,
        refresh_data=refresh_data,
        warmup_days=warmup_days,
    )


def reset_live_paper(strategy: str | None = None) -> dict[str, Any]:
    return reset_session(strategy=strategy).to_dict()


def load_live_chart_data(warmup_days: int = 30, max_bars: int = 1000) -> pd.DataFrame:
    return load_live_buffer(refresh=False, warmup_days=warmup_days, max_bars=max_bars)


def replay_session_from_dict(data: dict[str, Any]) -> ReplaySession:
    return ReplaySession.from_dict(data)


def start_replay_session(
    *,
    trade_year: int,
    config_year: int,
    strategies: list[str],
    equity: float,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp | None = None,
    warmup_days: int = 60,
) -> tuple[dict[str, Any], pd.DataFrame]:
    session, df = init_replay_session(
        trade_year=trade_year,
        config_year=config_year,
        strategies=strategies,
        equity=equity,
        start_ts=start_ts,
        end_ts=end_ts,
        warmup_days=warmup_days,
    )
    return session.to_dict(), df


def load_replay_chart_df(session_dict: dict[str, Any], start_ts: pd.Timestamp) -> pd.DataFrame:
    session = ReplaySession.from_dict(session_dict)
    return load_replay_dataframe(
        session.trade_year,
        start_ts,
        warmup_days=session.warmup_days,
        end_ts=pd.Timestamp(session.end_bar),
    )


def advance_replay(
    session_dict: dict[str, Any],
    df: pd.DataFrame,
    *,
    steps: int = 1,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    session = ReplaySession.from_dict(session_dict)
    engines = build_replay_engines(session)
    events = step_replay(session, engines, df, steps=steps)
    return session.to_dict(), events


def finish_replay(
    session_dict: dict[str, Any],
    df: pd.DataFrame,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    session = ReplaySession.from_dict(session_dict)
    engines = build_replay_engines(session)
    events = replay_to_end(session, engines, df)
    return session.to_dict(), events


def scrub_replay(
    session_dict: dict[str, Any],
    df: pd.DataFrame,
    target_idx: int,
    *,
    strategies: list[str],
    equity: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    session = ReplaySession.from_dict(session_dict)
    engines = build_replay_engines(session, equity)
    fresh, events = seek_replay(
        session,
        session.config_year,
        strategies,
        equity,
        df,
        target_idx,
        engines=engines,
    )
    return fresh.to_dict(), events


def replay_visible_df(session_dict: dict[str, Any], df: pd.DataFrame) -> pd.DataFrame:
    return visible_replay_df(ReplaySession.from_dict(session_dict), df)


def replay_current_bar(session_dict: dict[str, Any], df: pd.DataFrame) -> str | None:
    return cursor_bar_time(ReplaySession.from_dict(session_dict), df)


def paper_trade_to_chart_trade(trade: dict[str, Any] | PaperTrade) -> Trade:
    data = trade.to_dict() if isinstance(trade, PaperTrade) else trade
    return Trade(
        direction=int(data["direction"]),
        entry_time=pd.Timestamp(data["entry_time"]),
        entry_price=float(data["entry_price"]),
        sl_price=float(data["sl_price"]),
        tp_price=float(data["tp_price"]),
        size=float(data["size"]),
        exit_time=pd.Timestamp(data["exit_time"]) if data.get("exit_time") else None,
        exit_price=float(data["exit_price"]) if data.get("exit_price") is not None else None,
        pnl=float(data.get("pnl", 0.0)),
        result=data.get("result", ""),
    )
