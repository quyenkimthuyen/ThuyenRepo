"""Simulate ForgeBridge EA over historical bars via the same file protocol.

Isolated from live EA: writes to mt5/bridge_sim/ and data/mt5_sim_eurusd_m15.parquet.
Orchestrator: write bar/fill JSON → BridgeEngine.process cycle → trades.json.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from mt5_bridge.engine import BridgeEngine, _fmt_bar
from mt5_bridge.history_sync import MT5_CACHE_PATH, utc_to_broker_time
from mt5_bridge.models import get_model_run_params, resolve_model
from mt5_bridge.protocol import (
  BRIDGE_SIM_DIR,
  DEFAULT_MAGIC,
  DEFAULT_TIMEFRAME,
  INSTANCE_ID,
  atomic_write_json,
  bar_path,
  bars_path,
  connection_path,
  decision_path,
  ensure_bridge_dir,
  fill_path,
  status_path,
  utc_now_iso,
)
from mt5_bridge.trade_journal import clear_trades
from run_backtest import REPORT_DIR

ROOT = Path(__file__).resolve().parents[1]
SIM_CACHE_PATH = ROOT / "data" / "mt5_sim_eurusd_m15.parquet"
SIM_STATE_PATH = REPORT_DIR / "mt5_bridge_sim_state.json"

ProgressCb = Callable[[dict[str, Any]], None]


@dataclass
class SimConfig:
  date_from: str
  date_to: str
  delay_ms: int = 0
  model_id: str | None = None
  risk_pct: float = 1.0
  spread_pips: float | None = None
  slippage_pips: float | None = None
  bridge_dir: Path = field(default_factory=lambda: BRIDGE_SIM_DIR)
  mt5_cache: Path = field(default_factory=lambda: SIM_CACHE_PATH)
  clear_journal: bool = True


@dataclass
class _OpenPos:
  signal_id: str
  action: str  # BUY | SELL
  entry: float
  sl: float
  tp: float | None
  ticket: int
  bars_held: int = 0
  max_hold_bars: int = 96
  trail_activate_r: float | None = None
  trail_distance_r: float | None = None
  risk_dist: float = 0.0
  open_time: str = ""


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _pip_size(digits: int = 5) -> float:
  return 0.0001 if digits >= 4 else 0.01


def write_sim_state(update: dict[str, Any]) -> dict:
  REPORT_DIR.mkdir(parents=True, exist_ok=True)
  cur: dict[str, Any] = {}
  if SIM_STATE_PATH.exists():
    try:
      cur = json.loads(SIM_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
      cur = {}
  cur.update(update)
  cur["updated_at"] = _now()
  tmp = SIM_STATE_PATH.with_suffix(".tmp")
  tmp.write_text(json.dumps(cur, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  tmp.replace(SIM_STATE_PATH)
  return cur


def load_sim_state() -> dict[str, Any]:
  if not SIM_STATE_PATH.exists():
    return {"status": "idle"}
  try:
    return json.loads(SIM_STATE_PATH.read_text(encoding="utf-8"))
  except Exception:
    return {"status": "idle"}


def build_bar_payload(
  ts: pd.Timestamp,
  row: pd.Series,
  *,
  magic: int = DEFAULT_MAGIC,
  digits: int = 5,
) -> dict[str, Any]:
  broker = utc_to_broker_time(ts)
  t_str = broker.strftime("%Y.%m.%d %H:%M")
  point = 10 ** (-digits)
  return {
    "symbol": "EURUSD",
    "period": DEFAULT_TIMEFRAME,
    "instance_id": INSTANCE_ID,
    "magic": int(magic),
    "time": t_str,
    "bar_time": t_str,
    "time_msc": int(broker.timestamp() * 1000),
    "open": float(row["Open"]),
    "high": float(row["High"]),
    "low": float(row["Low"]),
    "close": float(row["Close"]),
    "volume": float(row.get("Volume") or 0),
    "tick_volume": float(row.get("Volume") or 0),
    "spread_points": 20,
    "digits": digits,
    "point": point,
    "account": "SIM",
    "server": "SimulateEA",
  }


def write_connection_stub(
  bridge_dir: Path,
  bar: dict,
  *,
  bid: float | None = None,
  ask: float | None = None,
) -> None:
  close = float(bar["close"])
  pip = _pip_size(int(bar.get("digits") or 5))
  bid = close if bid is None else bid
  ask = (close + pip) if ask is None else ask
  atomic_write_json(connection_path(bridge_dir), {
    "symbol": "EURUSD",
    "period": DEFAULT_TIMEFRAME,
    "instance_id": INSTANCE_ID,
    "magic": DEFAULT_MAGIC,
    "connected": True,
    "trade_allowed": True,
    "account": "SIM",
    "server": "SimulateEA",
    "bid": bid,
    "ask": ask,
    "spread_points": int(round((ask - bid) / float(bar.get("point") or 1e-5))),
    "updated_at": utc_now_iso(),
    "positions": 0,
    "bar": {
      "time": bar.get("time"),
      "open": bar.get("open"),
      "high": bar.get("high"),
      "low": bar.get("low"),
      "close": bar.get("close"),
    },
  })


def _identity_fill_base() -> dict[str, Any]:
  return {
    "symbol": "EURUSD",
    "period": DEFAULT_TIMEFRAME,
    "instance_id": INSTANCE_ID,
    "magic": DEFAULT_MAGIC,
    "ok": True,
    "account": "SIM",
    "server": "SimulateEA",
  }


def make_open_fill(
  decision: dict,
  *,
  entry_px: float,
  ticket: int,
  lots: float = 0.01,
  fill_time: str | None = None,
) -> dict[str, Any]:
  action = str(decision.get("action") or "").upper()
  return {
    **_identity_fill_base(),
    "event": "open",
    "action": action,
    "signal_id": decision.get("signal_id"),
    "ticket": ticket,
    "price": float(entry_px),
    "sl": decision.get("sl"),
    "tp": decision.get("tp"),
    "lots": lots,
    "detail": "opened",
    "reason": "sim_open",
    "manual": False,
    "source": "simulate_ea",
    "time": fill_time or utc_now_iso(),
    "bar_time": decision.get("bar_time"),
  }


def make_close_fill(
  pos: _OpenPos,
  *,
  exit_px: float,
  reason: str,
  fill_time: str | None = None,
) -> dict[str, Any]:
  return {
    **_identity_fill_base(),
    "event": "close",
    "action": pos.action,
    "signal_id": pos.signal_id,
    "ticket": pos.ticket,
    "price": float(exit_px),
    "sl": pos.sl,
    "tp": pos.tp,
    "lots": 0.01,
    "detail": reason,
    "reason": reason,
    "manual": False,
    "source": "simulate_ea",
    "time": fill_time or utc_now_iso(),
    "profit": None,
  }


def make_modify_fill(pos: _OpenPos, *, fill_time: str | None = None) -> dict[str, Any]:
  return {
    **_identity_fill_base(),
    "event": "modify",
    "action": pos.action,
    "signal_id": pos.signal_id,
    "ticket": pos.ticket,
    "price": pos.entry,
    "sl": pos.sl,
    "tp": pos.tp,
    "lots": 0.01,
    "detail": "ea_trail",
    "reason": "ea_trail",
    "manual": False,
    "source": "simulate_ea",
    "time": fill_time or utc_now_iso(),
  }


class PositionBook:
  """Minimal EA-like open/close using bar OHLC + optional trail."""

  def __init__(self):
    self.pos: _OpenPos | None = None
    self.pending_decision: dict | None = None
    self._ticket = 900000

  def schedule_open(self, decision: dict) -> None:
    action = str(decision.get("action") or "").upper()
    if action not in ("BUY", "SELL"):
      return
    if decision.get("sl") is None:
      return
    self.pending_decision = decision

  def try_open_at_bar(
    self,
    bar_ts: pd.Timestamp,
    row: pd.Series,
    *,
    spread_pips: float,
    slip_pips: float,
  ) -> dict | None:
    if self.pos is not None or not self.pending_decision:
      return None
    d = self.pending_decision
    self.pending_decision = None
    action = str(d.get("action") or "").upper()
    pip = _pip_size()
    pad = (spread_pips + slip_pips) * pip
    open_px = float(row["Open"])
    entry = open_px + pad if action == "BUY" else open_px - pad
    sl = float(d["sl"])
    tp = float(d["tp"]) if d.get("tp") is not None else None
    risk = abs(entry - sl)
    if risk <= 0:
      return None
    self._ticket += 1
    broker_t = utc_to_broker_time(bar_ts).strftime("%Y.%m.%d %H:%M")
    self.pos = _OpenPos(
      signal_id=str(d.get("signal_id") or ""),
      action=action,
      entry=entry,
      sl=sl,
      tp=tp,
      ticket=self._ticket,
      max_hold_bars=int(d.get("max_hold_bars") or 96),
      trail_activate_r=(
        float(d["trail_activate_r"]) if d.get("trail_activate_r") is not None else None
      ),
      trail_distance_r=(
        float(d["trail_distance_r"]) if d.get("trail_distance_r") is not None else None
      ),
      risk_dist=risk,
      open_time=broker_t,
    )
    return make_open_fill(d, entry_px=entry, ticket=self._ticket, fill_time=_now())

  def _unrealized_r(self, price: float) -> float:
    assert self.pos is not None
    if self.pos.action == "BUY":
      return (price - self.pos.entry) / self.pos.risk_dist
    return (self.pos.entry - price) / self.pos.risk_dist

  def _apply_trail(self, row: pd.Series) -> dict | None:
    pos = self.pos
    if not pos or pos.trail_activate_r is None or pos.trail_distance_r is None:
      return None
    # Favorable extreme this bar
    fav = float(row["High"]) if pos.action == "BUY" else float(row["Low"])
    ur = self._unrealized_r(fav)
    if ur < pos.trail_activate_r:
      return None
    if pos.action == "BUY":
      new_sl = fav - pos.trail_distance_r * pos.risk_dist
      if new_sl > pos.sl:
        pos.sl = new_sl
        return make_modify_fill(pos)
    else:
      new_sl = fav + pos.trail_distance_r * pos.risk_dist
      if new_sl < pos.sl:
        pos.sl = new_sl
        return make_modify_fill(pos)
    return None

  def manage_bar(self, row: pd.Series) -> list[dict]:
    """Return fill events (modify/close) for this bar. Does not open."""
    fills: list[dict] = []
    if self.pos is None:
      return fills
    mod = self._apply_trail(row)
    if mod:
      fills.append(mod)
    pos = self.pos
    assert pos is not None
    hi, lo, close = float(row["High"]), float(row["Low"]), float(row["Close"])
    pos.bars_held += 1
    exit_px = None
    reason = None
    if pos.action == "BUY":
      if lo <= pos.sl:
        exit_px, reason = pos.sl, "sl"
      elif pos.tp is not None and hi >= pos.tp:
        exit_px, reason = pos.tp, "tp"
    else:
      if hi >= pos.sl:
        exit_px, reason = pos.sl, "sl"
      elif pos.tp is not None and lo <= pos.tp:
        exit_px, reason = pos.tp, "tp"
    if exit_px is None and pos.bars_held >= pos.max_hold_bars:
      exit_px, reason = close, "max_hold"
    if exit_px is not None and reason:
      fills.append(make_close_fill(pos, exit_px=exit_px, reason=reason))
      self.pos = None
    return fills


def seed_sim_cache(date_from: pd.Timestamp, cache_path: Path) -> int:
  """Copy live parquet bars strictly before date_from into sim cache."""
  if not MT5_CACHE_PATH.exists():
    raise FileNotFoundError(f"Missing live MT5 cache: {MT5_CACHE_PATH}")
  src = pd.read_parquet(MT5_CACHE_PATH)
  src.index = pd.to_datetime(src.index, utc=True).tz_convert(None)
  src = src.sort_index()[~src.index.duplicated(keep="last")]
  seed = src.loc[src.index < date_from]
  if seed.empty:
    # Still allow sim if from is early — seed with empty frame columns
    seed = src.iloc[0:0].copy()
  cache_path.parent.mkdir(parents=True, exist_ok=True)
  seed.to_parquet(cache_path)
  return len(seed)


def _slice_bars(df: pd.DataFrame, date_from: pd.Timestamp, date_to: pd.Timestamp) -> pd.DataFrame:
  end = date_to + pd.Timedelta(days=1)
  out = df.loc[(df.index >= date_from) & (df.index < end)]
  return out


def run_simulation(
  cfg: SimConfig,
  *,
  on_progress: ProgressCb | None = None,
  stop_event: threading.Event | None = None,
  pause_event: threading.Event | None = None,
) -> dict[str, Any]:
  """
  Run Simulate EA loop.
  Returns summary dict; updates SIM_STATE_PATH throughout.
  """
  stop_event = stop_event or threading.Event()
  model = resolve_model(cfg.model_id)
  params = get_model_run_params(model, cfg.model_id)
  spread = float(
    cfg.spread_pips if cfg.spread_pips is not None else params.get("spread_pips") or 1.0
  )
  slip = float(
    cfg.slippage_pips if cfg.slippage_pips is not None else params.get("slippage_pips") or 0.3
  )
  model_id = (model or {}).get("id") or cfg.model_id or ""

  date_from = pd.Timestamp(cfg.date_from)
  date_to = pd.Timestamp(cfg.date_to)
  bridge_dir = ensure_bridge_dir(Path(cfg.bridge_dir))
  cache_path = Path(cfg.mt5_cache)

  write_sim_state({
    "status": "starting",
    "date_from": str(date_from.date()),
    "date_to": str(date_to.date()),
    "model_id": model_id,
    "bridge_dir": str(bridge_dir),
    "bars_done": 0,
    "bars_total": 0,
    "progress": 0.0,
    "last_bar": None,
    "n_fills": 0,
    "error": None,
  })

  if not MT5_CACHE_PATH.exists():
    raise FileNotFoundError("Cần data/mt5_eurusd_m15.parquet để simulate.")

  full = pd.read_parquet(MT5_CACHE_PATH)
  full.index = pd.to_datetime(full.index, utc=True).tz_convert(None)
  full = full.sort_index()[~full.index.duplicated(keep="last")]
  colmap = {}
  for c in full.columns:
    cl = str(c).lower()
    if cl == "open":
      colmap[c] = "Open"
    elif cl == "high":
      colmap[c] = "High"
    elif cl == "low":
      colmap[c] = "Low"
    elif cl == "close":
      colmap[c] = "Close"
    elif cl in ("volume", "tick_volume", "tickvolume"):
      colmap[c] = "Volume"
  full = full.rename(columns=colmap)
  for need in ("Open", "High", "Low", "Close"):
    if need not in full.columns:
      raise ValueError(f"Parquet thiếu cột {need}")
  if "Volume" not in full.columns:
    full["Volume"] = 0.0
  full = full[["Open", "High", "Low", "Close", "Volume"]]

  bars = _slice_bars(full, date_from, date_to)
  if bars.empty:
    raise ValueError(f"Không có nến trong [{date_from.date()} → {date_to.date()}]")

  n_seed = seed_sim_cache(date_from, cache_path)
  if cfg.clear_journal:
    clear_trades(bridge_dir)

  engine = BridgeEngine(
    model_id=model_id,
    risk_pct=float(cfg.risk_pct),
    mt5_cache=cache_path,
  )
  engine.load()

  from mt5_bridge.background import _cycle

  book = PositionBook()
  last_bar_fp = None
  last_fill_fp = None
  n_fills = 0
  total = len(bars)
  index_list = list(bars.index)

  write_sim_state({
    "status": "running",
    "bars_total": total,
    "seed_bars": n_seed,
    "progress": 0.0,
  })

  try:
    for i, ts in enumerate(index_list):
      if stop_event.is_set():
        write_sim_state({"status": "stopped", "bars_done": i})
        break
      while pause_event is not None and pause_event.is_set() and not stop_event.is_set():
        write_sim_state({"status": "paused", "bars_done": i, "last_bar": _fmt_bar(ts)})
        time.sleep(0.2)

      row = bars.loc[ts]

      # 1) Open pending from previous decision at this bar's open
      open_fill = book.try_open_at_bar(ts, row, spread_pips=spread, slip_pips=slip)
      if open_fill:
        # Stamp historical bar time so journal months align with OOS compare
        open_fill["time"] = utc_to_broker_time(ts).isoformat()
        atomic_write_json(fill_path(bridge_dir), open_fill)
        last_bar_fp, last_fill_fp = _cycle(engine, bridge_dir, last_bar_fp, last_fill_fp)
        n_fills += 1

      # 2) Manage open position on this bar
      manage_fills = book.manage_bar(row)
      for mf in manage_fills:
        mf["time"] = utc_to_broker_time(ts).isoformat()
        atomic_write_json(fill_path(bridge_dir), mf)
        last_bar_fp, last_fill_fp = _cycle(engine, bridge_dir, last_bar_fp, last_fill_fp)
        n_fills += 1

      # 3) Emit closed bar like EA
      bar = build_bar_payload(ts, row)
      atomic_write_json(bar_path(bridge_dir), bar)
      write_connection_stub(bridge_dir, bar)
      # Keep a short bars.json tail for charts pointing at sim dir
      tail = bars.iloc[max(0, i - 200): i + 1]
      atomic_write_json(bars_path(bridge_dir), {
        "symbol": "EURUSD",
        "period": DEFAULT_TIMEFRAME,
        "updated_at": utc_now_iso(),
        "bars": [
          {
            "time": utc_to_broker_time(t).strftime("%Y.%m.%d %H:%M"),
            "open": float(tail.loc[t, "Open"]),
            "high": float(tail.loc[t, "High"]),
            "low": float(tail.loc[t, "Low"]),
            "close": float(tail.loc[t, "Close"]),
            "tick_volume": float(tail.loc[t, "Volume"] if "Volume" in tail.columns else 0),
          }
          for t in tail.index
        ],
      })

      last_bar_fp, last_fill_fp = _cycle(engine, bridge_dir, last_bar_fp, last_fill_fp)
      decision = engine._last_decision if isinstance(engine._last_decision, dict) else None
      if decision and str(decision.get("action") or "").upper() in ("BUY", "SELL"):
        # Only schedule if flat (EA would skip if already in position)
        if book.pos is None and book.pending_decision is None:
          book.schedule_open(decision)

      prog = {
        "status": "running",
        "bars_done": i + 1,
        "bars_total": total,
        "progress": round((i + 1) / total, 4),
        "last_bar": bar.get("bar_time"),
        "last_action": (decision or {}).get("action"),
        "n_fills": n_fills,
        "open_position": book.pos.action if book.pos else None,
      }
      write_sim_state(prog)
      if on_progress:
        on_progress(prog)

      if cfg.delay_ms > 0:
        time.sleep(cfg.delay_ms / 1000.0)

    # Force-close leftover at end
    if book.pos is not None and index_list:
      last_row = bars.loc[index_list[-1]]
      close_fill = make_close_fill(
        book.pos, exit_px=float(last_row["Close"]), reason="sim_end",
      )
      book.pos = None
      atomic_write_json(fill_path(bridge_dir), close_fill)
      _cycle(engine, bridge_dir, last_bar_fp, last_fill_fp)
      n_fills += 1

    summary = {
      "status": "completed" if not stop_event.is_set() else "stopped",
      "bars_done": total if not stop_event.is_set() else load_sim_state().get("bars_done"),
      "bars_total": total,
      "progress": 1.0 if not stop_event.is_set() else load_sim_state().get("progress"),
      "n_fills": n_fills,
      "bridge_dir": str(bridge_dir),
      "model_id": model_id,
      "date_from": str(date_from.date()),
      "date_to": str(date_to.date()),
      "error": None,
    }
    write_sim_state(summary)
    atomic_write_json(status_path(bridge_dir), {
      "state": "sim_done",
      "updated_at": utc_now_iso(),
      "model_id": model_id,
      **{k: summary[k] for k in ("bars_done", "n_fills") if k in summary},
    })
    return summary
  except Exception as e:
    write_sim_state({"status": "error", "error": str(e)})
    raise
