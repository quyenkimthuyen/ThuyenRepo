"""Local browser-side Paper chart server (no Streamlit chart reruns)."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd

from data_loader import CACHE_PATH
from mt5_bridge.history_sync import utc_to_broker_time
from mt5_bridge.live_monitor_server import _chart_html, _plotly_js_path
from mt5_bridge.protocol import bars_path, connection_path, read_json
from paper_background import STATE_PATH, load_saved_state

DEFAULT_PAPER_MONITOR_PORT = 8766
_snapshot_lock = threading.Lock()
_snapshot_key: tuple | None = None
_snapshot_cache: dict | None = None


def _broker_clock(value):
  if value in (None, ""):
    return value
  try:
    return utc_to_broker_time(value).strftime("%Y-%m-%d %H:%M:%S")
  except (TypeError, ValueError):
    return value


def _broker_trade_times(trade: dict) -> dict:
  out = dict(trade)
  for key in ("time", "bar_time", "signal_time", "entry_time", "exit_time", "entry", "exit"):
    if key in out:
      out[key] = _broker_clock(out[key])
  return out


def _paper_snapshot() -> dict:
  global _snapshot_key, _snapshot_cache
  state = load_saved_state() or {}
  cache_mtime = CACHE_PATH.stat().st_mtime if CACHE_PATH.exists() else None
  live_bars_path = bars_path()
  live_connection_path = connection_path()
  bars_mtime = live_bars_path.stat().st_mtime if live_bars_path.exists() else None
  connection_mtime = (
    live_connection_path.stat().st_mtime if live_connection_path.exists() else None
  )
  key = (state.get("updated_at"), cache_mtime, bars_mtime, connection_mtime)
  with _snapshot_lock:
    if key == _snapshot_key and _snapshot_cache is not None:
      return _snapshot_cache

  rows: list[dict] = []
  if CACHE_PATH.exists():
    frame = pd.read_parquet(CACHE_PATH)
    frame.index = pd.to_datetime(frame.index, utc=True).tz_convert(None)
    chart_to = pd.Timestamp(state.get("chart_to") or state.get("last_bar") or frame.index[-1])
    frame = frame.loc[:chart_to].tail(1344)
    for timestamp, row in frame.iterrows():
      rows.append({
        "time": _broker_clock(timestamp),
        "open": float(row["Open"]),
        "high": float(row["High"]),
        "low": float(row["Low"]),
        "close": float(row["Close"]),
        "tick_volume": float(row.get("Volume", 0)),
      })

  live_history = read_json(live_bars_path) or {}
  live_connection = read_json(live_connection_path) or {}
  if not isinstance(live_history.get("bars"), list):
    live_history = {}
  last = rows[-1] if rows else {}
  last_close = last.get("close")
  history = live_history or {
    "symbol": "EURUSD",
    "updated_at": state.get("updated_at"),
    "period": "M15",
    "bars": rows,
  }
  connection = live_connection or {
    "connected": bool(state and rows),
    "server_time": _broker_clock(state.get("last_bar")),
    "bid": last_close,
    "ask": last_close,
    "bar": last or None,
  }
  payload = {
    "history": history,
    "connection": connection,
    "connection_mtime": connection_mtime or (
      STATE_PATH.stat().st_mtime if STATE_PATH.exists() else None
    ),
    "trades": [_broker_trade_times(row) for row in (state.get("orders") or [])],
    "state": state,
    "online": bool(
      state and history.get("bars") and connection.get("connected", True)
      and not state.get("error")
    ),
  }
  with _snapshot_lock:
    _snapshot_key = key
    _snapshot_cache = payload
  return payload


def start_paper_live_monitor_server(
  port: int = DEFAULT_PAPER_MONITOR_PORT,
) -> ThreadingHTTPServer:
  plotly_js = _plotly_js_path()

  class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, content_type: str) -> None:
      self.send_response(code)
      self.send_header("Content-Type", content_type)
      self.send_header("Content-Length", str(len(body)))
      self.send_header("Cache-Control", "no-store")
      self.send_header("X-Content-Type-Options", "nosniff")
      self.end_headers()
      self.wfile.write(body)

    def do_GET(self) -> None:
      parsed = urlparse(self.path)
      if parsed.path == "/health":
        self._send(200, b"ok", "text/plain; charset=utf-8")
        return
      if parsed.path == "/plotly.min.js":
        try:
          self._send(200, plotly_js.read_bytes(), "text/javascript; charset=utf-8")
        except OSError:
          self._send(404, b"plotly.js not found", "text/plain")
        return
      if parsed.path == "/snapshot":
        try:
          body = json.dumps(_paper_snapshot(), ensure_ascii=False).encode("utf-8")
          self._send(200, body, "application/json; charset=utf-8")
        except Exception as exc:
          body = json.dumps({"error": str(exc)}).encode("utf-8")
          self._send(500, body, "application/json; charset=utf-8")
        return
      if parsed.path in ("/", "/chart"):
        query = parse_qs(parsed.query)
        try:
          max_bars = max(96, min(1344, int((query.get("bars") or ["672"])[0])))
        except (TypeError, ValueError):
          max_bars = 672
        try:
          from paper_service import load_config
          default_poll = float(load_config().get("poll_sec", 2.0))
          poll_sec = max(
            0.5, min(30.0, float((query.get("poll") or [default_poll])[0])),
          )
        except (TypeError, ValueError):
          poll_sec = 2.0
        self._send(
          200,
          _chart_html(max_bars, mode="paper", poll_ms=int(poll_sec * 1000)).encode("utf-8"),
          "text/html; charset=utf-8",
        )
        return
      self._send(404, b"not found", "text/plain")

    def log_message(self, _format: str, *_args) -> None:
      return

  class ReusableServer(ThreadingHTTPServer):
    allow_reuse_address = True

  server = ReusableServer(("127.0.0.1", int(port)), Handler)
  thread = threading.Thread(
    target=server.serve_forever,
    name="paper-live-monitor-http",
    daemon=True,
  )
  thread.start()
  return server
