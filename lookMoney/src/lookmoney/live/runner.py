"""Paper trading runner — poll H1 from MT5, simulate fills locally."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from lookmoney.backtest.causal import generate_signals_causal
from lookmoney.backtest.engine import (
    PIP_SIZE,
    OpenTrade,
    _apply_exit_price,
    _bar_hits_trade,
    _pnl,
)
from lookmoney.execution import mt5_data
from lookmoney.live.state import (
    OpenTradeState,
    PaperSession,
    PaperTradeRecord,
    append_signal_log,
    append_trade_log,
    load_session,
    save_session,
)
from lookmoney.risk.manager import RiskConfig, RiskManager
from lookmoney.strategies.registry import resolve_strategy


def _closed_bars(df: pd.DataFrame, now: Optional[pd.Timestamp] = None) -> pd.DataFrame:
    """Bars whose period has fully ended (exclude forming candle)."""
    now = now or pd.Timestamp.now(tz="UTC")
    hour_floor = now.floor("h")
    return df[df.index < hour_floor]


def _ts_iso(ts: pd.Timestamp) -> str:
    t = ts.tz_convert("UTC") if ts.tzinfo else ts.tz_localize("UTC")
    return t.isoformat()


def _open_from_state(st: OpenTradeState) -> OpenTrade:
    return OpenTrade(
        side=st.side,
        entry=st.entry,
        stop_loss=st.stop_loss,
        take_profit=st.take_profit,
        lots=st.lots,
        entry_time=pd.Timestamp(st.entry_time),
        risk_per_unit=abs(st.entry - st.stop_loss),
        reason=st.reason,
    )


def _state_from_open(trade: OpenTrade) -> OpenTradeState:
    return OpenTradeState(
        side=trade.side,
        entry=trade.entry,
        stop_loss=trade.stop_loss,
        take_profit=trade.take_profit,
        lots=trade.lots,
        entry_time=_ts_iso(trade.entry_time),
        reason=trade.reason,
    )


class PaperRunner:
    def __init__(self, config: dict, *, data_source: str = "mt5") -> None:
        self.config = config
        self.data_source = data_source
        paper = config.get("paper", {})
        self.state_path = Path(paper.get("state_path", "data/paper_state.json"))
        self.trades_path = Path(paper.get("trades_log", "data/paper_trades.csv"))
        self.signals_path = Path(paper.get("signals_log", "data/paper_signals.csv"))
        self.history_bars = int(paper.get("history_bars", 500))
        self.min_minute = int(paper.get("min_minute_after_hour", 2))
        self.initial = float(config["risk"]["initial_balance"])
        self.session = load_session(self.state_path, self.initial)
        self._mt5_connected = False

    def _connect_mt5_if_needed(self) -> None:
        if self.data_source != "mt5" or self._mt5_connected:
            return
        mt5_data.connect_mt5(self.config.get("mt5", {}))
        self._mt5_connected = True

    def _fetch_bars(self, csv_fallback: Optional[str] = None) -> pd.DataFrame:
        if self.data_source == "csv" and csv_fallback:
            from lookmoney.data.fetcher import load_csv

            return load_csv(csv_fallback)
        self._connect_mt5_if_needed()
        symbol = self.config.get("mt5", {}).get("symbol", "EURUSD")
        return mt5_data.fetch_h1_bars(symbol, self.history_bars, self.config.get("mt5"))

    def _risk_manager(self) -> RiskManager:
        return RiskManager(
            config=RiskConfig.from_dict(self.config["risk"]),
            state=self.session.to_risk_state(),
        )

    def _sync_risk(self, rm: RiskManager) -> None:
        self.session.sync_from_risk(rm.state)

    def _process_bar(
        self,
        ts: pd.Timestamp,
        bar: pd.Series,
        rm: RiskManager,
        open_trade: Optional[OpenTrade],
    ) -> tuple[Optional[OpenTrade], Optional[PaperTradeRecord]]:
        bt = self.config["backtest"]
        risk_cfg = rm.config
        day = ts.date() if hasattr(ts, "date") else datetime.fromisoformat(str(ts)[:10]).date()
        rm.maybe_resume(day)

        if open_trade is not None:
            exit_reason, exit_raw = _bar_hits_trade(bar, open_trade)
            if exit_reason:
                pnl = _pnl(open_trade, exit_raw, bt)
                planned = rm.state.balance * risk_cfg.risk_per_trade
                r_mult = pnl / planned if planned else 0.0
                rm.register_close(pnl, day)
                rec = PaperTradeRecord(
                    entry_time=_ts_iso(open_trade.entry_time),
                    exit_time=_ts_iso(ts),
                    side=open_trade.side,
                    entry=open_trade.entry,
                    exit=exit_raw,
                    lots=open_trade.lots,
                    pnl=pnl,
                    r_multiple=r_mult,
                    exit_reason=exit_reason,
                    reason=open_trade.reason,
                )
                self.session.trade_count += 1
                return None, rec
        return open_trade, None

    def _try_open(
        self,
        ts: pd.Timestamp,
        sig: pd.Series,
        rm: RiskManager,
        open_trade: Optional[OpenTrade],
    ) -> tuple[Optional[OpenTrade], Optional[str]]:
        if open_trade is not None:
            return open_trade, None

        bt = self.config["backtest"]
        day = ts.date()
        ok, block = rm.can_open_trade(
            day, sig["entry"], sig["stop_loss"], sig["take_profit"], sig["side"]
        )
        if not ok:
            return None, block

        lots = rm.position_size_lots(
            sig["entry"],
            sig["stop_loss"],
            pip_value_per_lot=bt["pip_value_per_lot"],
            pip_size=PIP_SIZE,
        )
        if lots <= 0:
            return None, "zero_lots"

        entry = _apply_exit_price(
            sig["entry"], sig["side"], is_entry=True, slippage_pips=bt["slippage_pips"]
        )
        trade = OpenTrade(
            side=sig["side"],
            entry=entry,
            stop_loss=sig["stop_loss"],
            take_profit=sig["take_profit"],
            lots=lots,
            entry_time=ts,
            risk_per_unit=abs(entry - sig["stop_loss"]),
            reason=sig["reason"],
        )
        rm.register_open()
        return trade, None

    def run_once(self, *, csv_fallback: Optional[str] = None, force: bool = False) -> dict:
        now = pd.Timestamp.now(tz="UTC")
        if not force and now.minute < self.min_minute:
            return {
                "status": "skipped",
                "reason": f"wait until :{self.min_minute:02d} past the hour for closed H1 bar",
            }

        df = self._fetch_bars(csv_fallback)
        closed = _closed_bars(df, now)
        if closed.empty:
            return {"status": "skipped", "reason": "no closed bars"}

        last_closed = closed.index[-1]
        if (
            self.session.last_processed_bar
            and last_closed <= pd.Timestamp(self.session.last_processed_bar)
        ):
            return {
                "status": "skipped",
                "reason": f"already processed through {self.session.last_processed_bar}",
                "last_bar": _ts_iso(last_closed),
            }

        # Causal signals on full history up to last closed bar
        mod = resolve_strategy(self.config)
        signals = generate_signals_causal(
            closed,
            self.config,
            trade_start=closed.index[0],
            trade_end=last_closed,
            strategy_mod=mod,
        )

        if self.session.last_processed_bar:
            start_after = pd.Timestamp(self.session.last_processed_bar)
            new_bars = closed[closed.index > start_after]
        else:
            # First run: only the latest closed bar (no historical catch-up)
            new_bars = closed.iloc[[-1]]

        rm = self._risk_manager()
        open_trade = (
            _open_from_state(self.session.open_trade) if self.session.open_trade else None
        )
        actions: list[str] = []

        for ts, bar in new_bars.iterrows():
            open_trade, closed_rec = self._process_bar(ts, bar, rm, open_trade)
            if closed_rec:
                append_trade_log(self.trades_path, closed_rec)
                actions.append(f"CLOSE {closed_rec.side} pnl={closed_rec.pnl:+.2f}")

            if ts in signals.index:
                open_trade, block = self._try_open(ts, signals.loc[ts], rm, open_trade)
                if open_trade and open_trade.entry_time == ts:
                    actions.append(
                        f"OPEN {open_trade.side} @ {open_trade.entry:.5f} "
                        f"SL={open_trade.stop_loss:.5f} TP={open_trade.take_profit:.5f}"
                    )
                    append_signal_log(
                        self.signals_path,
                        {
                            "time": _ts_iso(ts),
                            "action": "open",
                            "side": open_trade.side,
                            "entry": open_trade.entry,
                            "stop_loss": open_trade.stop_loss,
                            "take_profit": open_trade.take_profit,
                            "lots": open_trade.lots,
                            "reason": open_trade.reason,
                        },
                    )
                elif block:
                    append_signal_log(
                        self.signals_path,
                        {
                            "time": _ts_iso(ts),
                            "action": "blocked",
                            "side": signals.loc[ts]["side"],
                            "block_reason": block,
                            "reason": signals.loc[ts]["reason"],
                        },
                    )
                    actions.append(f"SIGNAL blocked: {block}")

        self._sync_risk(rm)
        self.session.open_trade = _state_from_open(open_trade) if open_trade else None
        self.session.last_processed_bar = _ts_iso(last_closed)
        save_session(self.state_path, self.session)

        if self._mt5_connected:
            mt5_data.disconnect_mt5()
            self._mt5_connected = False

        return {
            "status": "ok",
            "last_bar": _ts_iso(last_closed),
            "balance": self.session.balance,
            "open_trade": self.session.open_trade is not None,
            "halted": self.session.halted,
            "actions": actions,
            "trade_count": self.session.trade_count,
        }

    def status(self) -> dict:
        return {
            "balance": self.session.balance,
            "peak_balance": self.session.peak_balance,
            "trade_count": self.session.trade_count,
            "open_trade": self.session.open_trade,
            "halted": self.session.halted,
            "halt_reason": self.session.halt_reason,
            "last_processed_bar": self.session.last_processed_bar,
            "last_run": self.session.last_run,
        }
