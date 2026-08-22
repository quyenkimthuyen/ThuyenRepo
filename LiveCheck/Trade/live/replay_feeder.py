"""Linux EA emulator — feeds OHLC bars into bridge_sim_live_* and paper-fills.

Speaks the same file protocol as ForgeBridgeLiveSim HistoryFeed:
  bar.json / connection.json / bars.json / fill.json / ea_fills.jsonl / sim_control.json

Decision worker (mt5_bridge_service_live --sim) writes decision(s); this feeder
opens at next-bar open and manages SL/TP/trail/max_hold like the EA paper path.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from replay_paper import ReplayPaperBook

ProgressCb = Callable[[dict[str, Any]], None]


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _is_transient_win_lock(exc: BaseException) -> bool:
  """Windows file lock / share / access-denied while another reader holds the path."""
  if isinstance(exc, PermissionError):
    return True
  winerr = getattr(exc, "winerror", None)
  # 5=Access denied, 32=Sharing violation, 33=Lock violation
  if winerr in (5, 32, 33):
    return True
  errno = getattr(exc, "errno", None)
  return errno in (11, 13, 16)  # EAGAIN / EACCES / EBUSY


def _atomic_write(path: Path, data: Any, *, retries: int = 16) -> None:
  """Write JSON with Windows-safe replace + retry.

  Parallel decision workers / Explorer / AV often hold ``bar.json`` open;
  a single ``.tmp.replace()`` then raises WinError 5 and used to kill replay.
  """
  path.parent.mkdir(parents=True, exist_ok=True)
  payload = json.dumps(data, ensure_ascii=False, default=str) + "\n"
  last_exc: BaseException | None = None
  for attempt in range(max(1, int(retries))):
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.{time.time_ns()}.{attempt}.tmp")
    try:
      tmp.write_text(payload, encoding="utf-8")
      os.replace(str(tmp), str(path))
      return
    except OSError as exc:
      last_exc = exc
      try:
        tmp.unlink(missing_ok=True)
      except OSError:
        pass
      if not _is_transient_win_lock(exc):
        raise
      time.sleep(min(0.25, 0.01 * (attempt + 1)))
  # Last resort: non-atomic overwrite — keep replay alive.
  try:
    path.write_text(payload, encoding="utf-8")
    return
  except OSError as exc:
    last_exc = exc
  if last_exc:
    raise last_exc
  raise OSError(f"cannot write {path}")


def _append_jsonl(path: Path, row: dict) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  for attempt in range(8):
    try:
      with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
      return
    except OSError as exc:
      if not _is_transient_win_lock(exc) or attempt >= 7:
        raise
      time.sleep(0.02 * (attempt + 1))


def mt5_bar_time(ts: pd.Timestamp) -> str:
  """Match MT5 TimeToString format used by EA / BridgeEngine."""
  t = pd.Timestamp(ts).to_pydatetime()
  return t.strftime("%Y.%m.%d %H:%M")


def load_ohlc(
  parquet: Path,
  *,
  date_from: str,
  date_to: str,
) -> pd.DataFrame:
  df = pd.read_parquet(parquet)
  if not isinstance(df.index, pd.DatetimeIndex):
    # try common column
    for col in ("time", "Time", "datetime", "Date"):
      if col in df.columns:
        df = df.set_index(pd.to_datetime(df[col]))
        break
  if not isinstance(df.index, pd.DatetimeIndex):
    raise ValueError(f"OHLC parquet needs DatetimeIndex: {parquet}")
  cols = {c.lower(): c for c in df.columns}
  need = {}
  for key in ("open", "high", "low", "close"):
    if key not in cols:
      raise ValueError(f"missing column {key} in {parquet}")
    need[key] = cols[key]
  vol_col = cols.get("volume") or cols.get("tick_volume")
  out = pd.DataFrame({
    "open": df[need["open"]].astype(float),
    "high": df[need["high"]].astype(float),
    "low": df[need["low"]].astype(float),
    "close": df[need["close"]].astype(float),
    "volume": df[vol_col].astype(float) if vol_col else 0.0,
  }, index=df.index).sort_index()
  start = pd.Timestamp(date_from)
  end = pd.Timestamp(date_to) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
  out = out.loc[(out.index >= start) & (out.index <= end)]
  if out.empty:
    raise ValueError(f"No bars in {date_from}..{date_to} for {parquet}")
  return out


def _read_json(path: Path) -> Any:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def _write_sim_control(bridge_dir: Path, **fields: Any) -> None:
  path = bridge_dir / "sim_control.json"
  cur = _read_json(path) if path.exists() else {}
  if not isinstance(cur, dict):
    cur = {}
  cur.update(fields)
  cur["updated_at"] = _now()
  _atomic_write(path, cur)


def _write_connection(bridge_dir: Path, *, symbol: str, period: str, magic: int) -> None:
  _atomic_write(bridge_dir / "connection.json", {
    "ok": True,
    "online": True,
    "symbol": symbol,
    "period": period,
    "instance_id": "LIVE_SIM",
    "magic": magic,
    "source": "linux_replay",
    "updated_at": _now(),
    "account": 0,
  })


def _bar_spread_points(row: pd.Series) -> int:
  for key in ("spread_points", "spread"):
    if key not in getattr(row, "index", []):
      continue
    val = row.get(key)
    if val is None or (isinstance(val, float) and pd.isna(val)):
      continue
    try:
      pts = int(val)
    except (TypeError, ValueError):
      continue
    if pts > 0:
      return pts
  return 10


def _write_bar(
  bridge_dir: Path,
  *,
  symbol: str,
  period: str,
  magic: int,
  ts: pd.Timestamp,
  row: pd.Series,
) -> dict:
  bt = mt5_bar_time(ts)
  t_msc = int(pd.Timestamp(ts).timestamp() * 1000)
  bar = {
    "symbol": symbol,
    "period": period,
    "instance_id": "LIVE_SIM",
    "magic": magic,
    "time": bt,
    "bar_time": bt,
    "time_msc": t_msc,
    "open": float(row["open"]),
    "high": float(row["high"]),
    "low": float(row["low"]),
    "close": float(row["close"]),
    "volume": float(row.get("volume") or 0),
    "tick_volume": float(row.get("volume") or 0),
    "spread_points": _bar_spread_points(row),
    "digits": 5,
    "point": 0.00001,
    "account": 0,
  }
  _atomic_write(bridge_dir / "bar.json", bar)
  # short chart buffer for UI
  hist = _read_json(bridge_dir / "bars.json")
  bars = list(hist.get("bars") or []) if isinstance(hist, dict) else []
  bars.append(bar)
  bars = bars[-200:]
  _atomic_write(bridge_dir / "bars.json", {"updated_at": _now(), "bars": bars})
  return bar


def _emit_fill(bridge_dir: Path, fill: dict) -> None:
  _atomic_write(bridge_dir / "fill.json", fill)
  _append_jsonl(bridge_dir / "ea_fills.jsonl", fill)


def _model_roster(bridge_dir: Path) -> list[dict]:
  data = _read_json(bridge_dir / "models.json") or {}
  return list(data.get("models") or [])


def _wait_decisions(
  bridge_dir: Path,
  *,
  model_ids: list[str],
  bar_time: str,
  timeout_sec: float,
  poll_sec: float = 0.05,
) -> dict[str, dict]:
  """Wait until each model has a decision with matching bar_time (or timeout)."""
  deadline = time.time() + max(0.05, timeout_sec)
  found: dict[str, dict] = {}
  dec_dir = bridge_dir / "decisions"
  while time.time() < deadline and len(found) < len(model_ids):
    for mid in model_ids:
      if mid in found:
        continue
      path = dec_dir / f"{mid}.json"
      d = _read_json(path)
      if not isinstance(d, dict):
        # fallback shared decision.json for single-model
        if len(model_ids) == 1:
          d = _read_json(bridge_dir / "decision.json")
      if not isinstance(d, dict):
        continue
      bt = str(d.get("bar_time") or d.get("time") or "")
      if bt == bar_time:
        found[mid] = d
    if len(found) >= len(model_ids):
      break
    time.sleep(poll_sec)
  return found


def clear_replay_artifacts(bridge_dir: Path) -> None:
  for name in (
    "bar.json", "bars.json", "connection.json", "decision.json",
    "fill.json", "ea_fills.jsonl", "fills.jsonl", "command.json",
    "command_ack.json", "status.json",
  ):
    p = bridge_dir / name
    if p.exists():
      try:
        p.unlink()
      except OSError:
        pass
  dec = bridge_dir / "decisions"
  if dec.is_dir():
    for p in dec.glob("*.json"):
      try:
        p.unlink()
      except OSError:
        pass


def run_replay(
  *,
  bridge_dir: Path,
  parquet: Path,
  symbol: str,
  timeframe: str,
  date_from: str,
  date_to: str,
  delay_ms: int = 0,
  decision_timeout_sec: float = 8.0,
  clear: bool = True,
  on_progress: ProgressCb | None = None,
  stop_flag: Callable[[], bool] | None = None,
) -> dict[str, Any]:
  """Drive one book through historical bars at accelerated wall-clock pace."""
  bridge_dir = Path(bridge_dir)
  bridge_dir.mkdir(parents=True, exist_ok=True)
  (bridge_dir / "decisions").mkdir(exist_ok=True)

  request_id = uuid.uuid4().hex[:12]
  if clear:
    clear_replay_artifacts(bridge_dir)

  df = load_ohlc(parquet, date_from=date_from, date_to=date_to)
  roster = _model_roster(bridge_dir)
  if not roster:
    raise RuntimeError(f"No models in {bridge_dir / 'models.json'} — sync roster first")

  books: dict[str, ReplayPaperBook] = {}
  model_ids: list[str] = []
  primary_magic = int(roster[0].get("magic") or 20264001)
  for m in roster:
    mid = str(m.get("id") or "")
    if not mid:
      continue
    model_ids.append(mid)
    books[mid] = ReplayPaperBook(
      model_id=mid,
      magic=int(m["magic"]) if m.get("magic") is not None else None,
      symbol=symbol,
      period=timeframe,
    )

  _write_sim_control(
    bridge_dir,
    enabled=True,
    **{
      "from": date_from.replace("-", "."),
      "to": date_to.replace("-", "."),
      "delay_ms": int(delay_ms),
      "request_id": request_id,
      "ea_status": "running",
      "bars_done": 0,
      "bars_total": len(df),
      "last_bar": "",
      "error": "",
      "source": "linux_replay",
    },
  )
  _write_connection(bridge_dir, symbol=symbol, period=timeframe, magic=primary_magic)

  n_fills = 0
  sleep_sec = max(0.0, float(delay_ms) / 1000.0)
  started = time.time()

  for i, (ts, row) in enumerate(df.iterrows()):
    if stop_flag and stop_flag():
      _write_sim_control(bridge_dir, enabled=False, ea_status="stopped", error="stopped_by_user")
      break

    # 1) manage / open at this bar's open (pending from prior decision)
    for mid, book in books.items():
      for fill in book.on_bar(
        open_=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        bar_time=mt5_bar_time(ts),
        spread_points=_bar_spread_points(row),
      ):
        _emit_fill(bridge_dir, fill)
        n_fills += 1

    # 2) publish bar for decision worker
    bar = _write_bar(
      bridge_dir,
      symbol=symbol,
      period=timeframe,
      magic=primary_magic,
      ts=ts,
      row=row,
    )
    bt = bar["bar_time"]

    # 3) wait for per-model decisions matching this bar_time
    decisions = _wait_decisions(
      bridge_dir,
      model_ids=model_ids,
      bar_time=bt,
      timeout_sec=decision_timeout_sec,
    )
    for mid, d in decisions.items():
      books[mid].queue_decision(d)

    done = i + 1
    _write_sim_control(
      bridge_dir,
      ea_status="running",
      bars_done=done,
      bars_total=len(df),
      last_bar=bt,
      n_fills=n_fills,
    )
    if on_progress and (done == 1 or done == len(df) or done % 25 == 0):
      on_progress({
        "bars_done": done,
        "bars_total": len(df),
        "last_bar": bt,
        "n_fills": n_fills,
        "decisions": len(decisions),
        "ea_status": "running",
      })

    if sleep_sec > 0:
      time.sleep(sleep_sec)

  else:
    _write_sim_control(
      bridge_dir,
      enabled=False,
      ea_status="completed",
      bars_done=len(df),
      bars_total=len(df),
      n_fills=n_fills,
      error="",
    )

  elapsed = time.time() - started
  return {
    "status": "completed",
    "request_id": request_id,
    "bars_total": len(df),
    "n_fills": n_fills,
    "elapsed_sec": round(elapsed, 2),
    "bridge_dir": str(bridge_dir),
    "symbol": symbol,
    "timeframe": timeframe,
    "date_from": date_from,
    "date_to": date_to,
    "models": model_ids,
  }
