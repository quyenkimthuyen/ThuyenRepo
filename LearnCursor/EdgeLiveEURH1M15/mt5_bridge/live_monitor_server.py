"""Local HTTP chart endpoint for smooth browser-side MT5 updates."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from mt5_bridge.protocol import (
  BRIDGE_DIR,
  BRIDGE_SIM_DIR,
  bar_path,
  bars_path,
  connection_path,
  decision_path,
  read_json,
)
from mt5_bridge.trade_journal import load_trades
from runtime_profiles import get_profile, profile_for_dir, profile_for_port

DEFAULT_MONITOR_PORT = get_profile("M15", "live").monitor_port  # 8765
SIM_MONITOR_PORT = get_profile("M15", "sim").monitor_port  # 8876
H1_MONITOR_PORT = get_profile("H1", "live").monitor_port  # 8865
H1_SIM_MONITOR_PORT = get_profile("H1", "sim").monitor_port  # 8877
SIM_MONITOR_PORTS = (SIM_MONITOR_PORT, H1_SIM_MONITOR_PORT)


def monitor_port_for(tf: str, mode: str = "live") -> int:
  return int(get_profile(tf, mode).monitor_port)


_CHART_SERVERS: dict[int, ThreadingHTTPServer] = {}
_CHART_SERVER_LOCKS: dict[int, threading.Lock] = {}


def _chart_server_lock(port: int) -> threading.Lock:
  return _CHART_SERVER_LOCKS.setdefault(port, threading.Lock())


def _plotly_js_path() -> Path:
  import plotly
  return Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"


def _parse_broker_bar_time(value):
  import pandas as pd
  if value is None or value == "":
    return None
  s = str(value).strip()
  for candidate in (s.replace("-", ".")[:19], s[:19].replace(".", "-")):
    ts = pd.to_datetime(candidate, errors="coerce")
    if not pd.isna(ts):
      if getattr(ts, "tzinfo", None) is not None:
        ts = ts.tz_localize(None)
      return ts
  return None


_SIM_CACHE_FRAME = None
_SIM_CACHE_MTIME = None


_SIM_CACHE_TF: str | None = None


def _cached_broker_ohlc(tf: str | None = None):
  """Load MT5 parquet once per mtime — chart poll must not re-read 40k bars every second."""
  global _SIM_CACHE_FRAME, _SIM_CACHE_MTIME, _SIM_CACHE_TF
  import pandas as pd

  from mt5_bridge.history_sync import cache_path_for, load_mt5_cache, utc_to_broker_time

  cache_path = cache_path_for(tf)
  try:
    mtime = cache_path.stat().st_mtime if cache_path.exists() else None
  except OSError:
    mtime = None
  if (
    _SIM_CACHE_FRAME is not None
    and mtime is not None
    and mtime == _SIM_CACHE_MTIME
    and tf == _SIM_CACHE_TF
  ):
    return _SIM_CACHE_FRAME.copy()
  cache = load_mt5_cache(tf)
  _SIM_CACHE_TF = tf
  if cache is None or cache.empty:
    _SIM_CACHE_FRAME = None
    _SIM_CACHE_MTIME = mtime
    return None
  frame = cache.copy()
  frame.index = pd.DatetimeIndex([utc_to_broker_time(ts) for ts in frame.index])
  frame = frame[~frame.index.duplicated(keep="last")].sort_index()
  _SIM_CACHE_FRAME = frame
  _SIM_CACHE_MTIME = mtime
  return frame.copy()


def build_sim_snapshot(bridge_dir: Path | None = None, *, max_bars: int = 672) -> dict:
  """OHLC from MT5 cache in sim from/to, clipped to EA cursor — for smooth iframe chart."""
  import pandas as pd

  from mt5_bridge.ea_simulator import load_sim_state, sync_state_from_ea

  sim_dir = Path(bridge_dir) if bridge_dir else BRIDGE_SIM_DIR
  profile = profile_for_dir(sim_dir)
  tf = profile.tf if profile else None
  try:
    st = sync_state_from_ea(sim_dir, persist=False)
  except Exception:
    st = load_sim_state(sim_dir)
  from mt5_bridge.protocol import read_sim_control
  ctrl = read_sim_control(sim_dir) or {}
  date_from = st.get("date_from") or ctrl.get("from")
  date_to = st.get("date_to") or ctrl.get("to")
  ea_status = str(ctrl.get("ea_status") or st.get("ea_status") or "idle")
  enabled = bool(ctrl.get("enabled"))
  last_bar = ctrl.get("last_bar") or st.get("last_bar") or ""
  if enabled or ea_status == "running":
    status = "running"
  elif ea_status == "paused" or st.get("status") == "paused":
    status = "paused"
  elif ea_status == "completed":
    status = "completed"
  else:
    status = "idle"
    last_bar = ""  # preview full from/to window

  cache = _cached_broker_ohlc(tf)
  bars: list[dict] = []
  connection: dict = read_json(connection_path(sim_dir)) or {}

  if cache is not None and not cache.empty:
    frame = cache

    def _bound(s):
      if not s:
        return None
      raw = str(s).strip().replace(".", "-")
      try:
        return pd.Timestamp(raw[:10])
      except Exception:
        return _parse_broker_bar_time(s)

    t0, t1 = _bound(date_from), _bound(date_to)
    if t0 is not None:
      frame = frame.loc[frame.index >= t0.normalize()]
    if t1 is not None:
      end = t1.normalize() + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
      frame = frame.loc[frame.index <= end]

    last_ts = _parse_broker_bar_time(last_bar) if last_bar else None
    # Only use live bar.json as cursor while feed is active
    if last_ts is None and status in ("running", "paused"):
      bar = read_json(bar_path(sim_dir)) or {}
      last_ts = _parse_broker_bar_time(bar.get("bar_time") or bar.get("time"))

    if status in ("running", "paused"):
      if last_ts is not None:
        frame = frame.loc[frame.index <= last_ts]
      else:
        frame = frame.iloc[0:0]
    # idle/completed: full window (then tail)

    limit = max(96, int(max_bars))
    if len(frame) > limit:
      frame = frame.tail(limit) if status in ("running", "paused", "completed") else frame.head(limit)

    for ts, row in frame.iterrows():
      bars.append({
        "time": ts.strftime("%Y.%m.%d %H:%M"),
        "open": float(row["Open"]),
        "high": float(row["High"]),
        "low": float(row["Low"]),
        "close": float(row["Close"]),
        "tick_volume": float(row["Volume"]) if "Volume" in row.index else 0.0,
      })
    if bars:
      last = bars[-1]
      close = float(last["close"])
      # Prefer historical bar spread (HistoryFeed). connection.json still carries
      # live SYMBOL_SPREAD / bid-ask from the terminal (~39) which is misleading on sim.
      bar_live = read_json(bar_path(sim_dir)) or {}
      try:
        spr = int(
          bar_live.get("spread_points")
          if bar_live.get("spread_points") is not None
          else (connection.get("spread_points") or 0)
        )
      except (TypeError, ValueError):
        spr = 0
      point = 0.00001
      try:
        if bar_live.get("point") is not None:
          point = float(bar_live["point"])
        elif connection.get("point") is not None:
          point = float(connection["point"])
      except (TypeError, ValueError):
        point = 0.00001
      connection = {
        **connection,
        "connected": True,
        "bid": close,
        "ask": round(close + spr * point, 5) if spr > 0 else close,
        "spread_points": spr,
        "positions": connection.get("positions") or 0,
        "terminal_trade_allowed": True,
        "account_trade_allowed": True,
        "server_time": last["time"],
        "bar": {**last, "spread_points": spr},
      }

  if not bars:
    # Fallback: EA bars.json (may be incomplete)
    hist = read_json(bars_path(sim_dir)) or {}
    bars = list(hist.get("bars") or [])[-max(96, int(max_bars)):]

  raw_trades = load_trades(sim_dir)
  trades = []
  # Visible candle window (broker wall-clock)
  chart_t0 = _parse_broker_bar_time(bars[0]["time"]) if bars else None
  chart_t1 = _parse_broker_bar_time(bars[-1]["time"]) if bars else None
  win_end = _bound(date_to)
  if win_end is not None:
    win_end = win_end.normalize() + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

  for t in raw_trades:
    tc = dict(t)
    # Chart needs real entry — never invent from exit (orphan closes break Plotly)
    if tc.get("entry_px") is None:
      continue
    try:
      ep = float(tc["entry_px"])
      sl = float(tc["sl"]) if tc.get("sl") is not None else None
      tp = float(tc["tp"]) if tc.get("tp") is not None else None
    except (TypeError, ValueError):
      continue
    if sl is not None and abs(ep - sl) < 1e-9:
      continue  # zero-risk zone paints broken rectangles
    entry_raw = tc.get("entry_time") or tc.get("bar_time")
    if not entry_raw:
      continue
    tc["entry_time"] = entry_raw
    et = _parse_broker_bar_time(entry_raw)
    xt = _parse_broker_bar_time(tc.get("exit_time") or tc.get("exit"))
    # Wall-clock exit (EA close without bar_time) spans into "today" and wrecks overlays
    if et is not None and xt is not None:
      bad_exit = (
        xt < et
        or (xt - et) > pd.Timedelta(days=10)
        or (win_end is not None and xt > win_end + pd.Timedelta(days=1))
      )
      if bad_exit:
        tc.pop("exit_time", None)
        tc.pop("exit_px", None)
        xt = None
    # Skip trades whose entry is outside the visible candle window
    if chart_t0 is not None and chart_t1 is not None and et is not None:
      if et > chart_t1 or (xt is None and et < chart_t0 - pd.Timedelta(days=1)):
        # Keep if still open across window; drop if entirely before with no valid exit
        if xt is None and et < chart_t0:
          continue
    trades.append(tc)

  decision = read_json(decision_path(sim_dir)) or {}
  action = str(decision.get("action") or "").upper()
  signal_id = decision.get("signal_id")
  known = any(signal_id and t.get("signal_id") == signal_id for t in trades)
  if action in ("BUY", "SELL") and not known:
    entry = decision.get("entry")
    sl = decision.get("sl")
    tp = decision.get("tp")
    et = decision.get("entry_time") or decision.get("bar_time")
    if entry is not None and sl is not None and tp is not None and et:
      trades.append({
        "status": "SIGNAL",
        "signal_id": signal_id,
        "direction": action,
        "entry_time": et,
        "entry_px": entry,
        "sl": sl,
        "tp": tp,
        "strategy_name": decision.get("strategy_name"),
      })

  done = int(ctrl.get("bars_done") or st.get("bars_done") or 0)
  total = int(ctrl.get("bars_total") or st.get("bars_total") or 0)
  sim_out = {
    **st,
    "status": status,
    "ea_status": ea_status,
    "bars_done": done,
    "bars_total": total,
    "last_bar": last_bar or st.get("last_bar"),
    "date_from": date_from,
    "date_to": date_to,
  }
  return {
    "history": {"bars": bars, "source": "sim_cache"},
    "connection": connection,
    "connection_mtime": None,
    "trades": trades,
    "decision": decision,
    "sim": sim_out,
    "online": status in ("running", "paused", "completed") or bool(bars),
    "progress": f"{done}/{total}" if total else str(done),
  }


def _chart_html(max_bars: int, *, mode: str = "mt5", poll_ms: int = 2000, tf: str = "M15") -> str:
  paper_mode = mode == "paper"
  sim_mode = mode == "sim"
  tf_label = str(tf or "M15").upper()
  if sim_mode:
    chart_title = f"EURUSD {tf_label} · Simulate History Feed"
    labels = (
      "FEED", "QUOTE", "SPREAD", "PROGRESS", "FEED STATUS", "DECISION", "LAST BAR",
    )
    grid_cols = 7
    status_cells = f"""
    <div class="metric"><div class="label">{labels[0]}</div><div class="value" id="conn">WAITING</div></div>
    <div class="metric"><div class="label">{labels[1]}</div><div class="value" id="price">—</div></div>
    <div class="metric"><div class="label">{labels[2]}</div><div class="value" id="spread">—</div></div>
    <div class="metric"><div class="label">{labels[3]}</div><div class="value" id="positions">—</div></div>
    <div class="metric"><div class="label">{labels[4]}</div><div class="value" id="trading">—</div></div>
    <div class="metric"><div class="label">{labels[5]}</div><div class="value" id="decision">—</div></div>
    <div class="metric"><div class="label">{labels[6]}</div><div class="value" id="slots">—</div></div>
    """
    price_tag = "SIM"
    ui_rev = "mt5-sim-v3"
    snap_url = "/snapshot?mode=sim"
    note0 = "Simulate History Feed — status + chart cập nhật mượt (Plotly.react)."
  elif paper_mode:
    chart_title = f"EURUSD {tf_label} · Paper Trade"
    labels = ("PAPER ENGINE", "LAST PRICE", "DAY TRADES", "SLOTS LEFT", "SESSION")
    grid_cols = 5
    status_cells = f"""
    <div class="metric"><div class="label">{labels[0]}</div><div class="value" id="conn">WAITING</div></div>
    <div class="metric"><div class="label">{labels[1]}</div><div class="value" id="price">—</div></div>
    <div class="metric"><div class="label">{labels[2]}</div><div class="value" id="spread">—</div></div>
    <div class="metric"><div class="label">{labels[3]}</div><div class="value" id="positions">—</div></div>
    <div class="metric"><div class="label">{labels[4]}</div><div class="value" id="trading">—</div></div>
    """
    price_tag = "LIVE"
    ui_rev = "mt5-live"
    snap_url = "/snapshot"
    note0 = "Đang kết nối ForgeBridge EA…"
  else:
    chart_title = f"EURUSD {tf_label} · XM MT5 live"
    labels = (
      "EA", "BID / ASK", "SPREAD", "OPEN", "AutoTrade", "DECISION", "SLOTS",
    )
    grid_cols = 7
    status_cells = f"""
    <div class="metric"><div class="label">{labels[0]}</div><div class="value" id="conn">WAITING</div></div>
    <div class="metric"><div class="label">{labels[1]}</div><div class="value" id="price">—</div></div>
    <div class="metric"><div class="label">{labels[2]}</div><div class="value" id="spread">—</div></div>
    <div class="metric"><div class="label">{labels[3]}</div><div class="value" id="positions">—</div></div>
    <div class="metric"><div class="label">{labels[4]}</div><div class="value" id="trading">—</div></div>
    <div class="metric"><div class="label">{labels[5]}</div><div class="value" id="decision">—</div></div>
    <div class="metric"><div class="label">{labels[6]}</div><div class="value" id="slots">—</div></div>
    """
    price_tag = "LIVE"
    ui_rev = "mt5-live-v2"
    snap_url = "/snapshot"
    note0 = f"Đang kết nối ForgeBridge {tf_label}…"
  return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    html,body{{margin:0;background:#131722;color:#d1d4dc;font-family:Arial,sans-serif}}
    #status{{display:grid;grid-template-columns:repeat({grid_cols},minmax(90px,1fr));gap:8px;padding:8px 10px}}
    .metric{{background:#1e222d;border:1px solid #2a2e39;border-radius:6px;padding:7px 10px}}
    .label{{font-size:11px;color:#8b8f9a}} .value{{font-size:15px;font-weight:600;margin-top:3px}}
    #note{{font-size:11px;color:#8b8f9a;padding:0 12px 4px}} #chart{{height:585px}}
    .online{{color:#26a69a}} .offline{{color:#ef5350}} .flat{{color:#d1d4dc}} .signal{{color:#f7c948}}
  </style>
  <script src="/plotly.min.js"></script>
</head>
<body>
  <div id="status">
    {status_cells}
  </div>
  <div id="note">{note0}</div>
  <div id="chart"></div>
<script>
const MAX_BARS = {max_bars};
const PAPER_MODE = {str(paper_mode).lower()};
const SIM_MODE = {str(sim_mode).lower()};
const POLL_MS = {max(500, int(poll_ms))};
const SNAP_URL = "{snap_url}";
const PRICE_TAG = "{price_tag}";
const UI_REV = "{ui_rev}";
const COLORS = {{bg:"#131722", grid:"#363a45", text:"#d1d4dc", up:"#26a69a",
  down:"#ef5350", sl:"#f23645", tp:"#089981", live:"#f7c948"}};
let firstRender = true;

function mt5Time(value) {{
  if (!value) return null;
  const s = String(value).trim();
  // ISO / App journal: 2026-07-24T12:34:56+05:30
  const iso = s.match(/^(\\d{{4}})-(\\d{{2}})-(\\d{{2}})[T ](\\d{{2}}):(\\d{{2}})(?::(\\d{{2}}))?/);
  if (iso) return iso[1]+"-"+iso[2]+"-"+iso[3]+"T"+iso[4]+":"+iso[5]+":"+(iso[6]||"00");
  // MT5: 2026.07.24 12:34[:56]
  const p = s.split(/\\s+/);
  const d = (p[0]||"").replaceAll(".","-");
  if (!/^\\d{{4}}-\\d{{2}}-\\d{{2}}$/.test(d)) return null;
  let t = p[1] || "00:00:00";
  if (t.split(":").length === 2) t += ":00";
  return d + "T" + t;
}}
function setText(id, text, cls="") {{
  const el=document.getElementById(id);
  if (!el) return;
  el.textContent=text; el.className="value "+cls;
}}
function tradeLayers(trades, start, end) {{
  // Same drawing style as Paper Trade (_add_order_overlays):
  // risk/reward zones · SL/TP lines + labels · ENTRY ▲▼ · EXIT ✕ · OPEN badge
  const out=[], shapes=[], annotations=[];
  const ENTRY_BLUE = "#2962ff";
  for (const t of (trades || [])) {{
    try {{
    const et = mt5Time(t.entry_time || t.bar_time || t.signal_time);
    const ep = Number(t.entry_px != null ? t.entry_px : t.entry);
    if (!et || !Number.isFinite(ep) || ep <= 0) continue;
    const xt = mt5Time(t.exit_time || t.exit);
    const lineEnd = xt || end;
    if (!start || !end || lineEnd < start || et > end) continue;
    const dir = String(t.direction || t.dir || "").toUpperCase();
    const isLong = dir === "BUY" || dir === "LONG";
    const status = String(t.status || "CLOSED").toUpperCase();
    const signal = status === "SIGNAL";
    const lineStart = et < start ? start : et;
    const sl = Number(t.sl), tp = Number(t.tp);
    if (Number.isFinite(sl) && Math.abs(sl - ep) < 1e-9) continue;
    const lineDash = signal ? "dash" : "dot";
    const riskFill = signal ? "rgba(255,193,7,0.08)" : "rgba(242,54,69,0.12)";
    const rewFill = signal ? "rgba(255,193,7,0.06)" : "rgba(8,153,129,0.10)";
    const slColor = signal ? "#ffc107" : COLORS.sl;
    const tpColor = signal ? "#ffc107" : COLORS.tp;

    if (Number.isFinite(sl) && Number.isFinite(tp)) {{
      shapes.push({{
        type:"rect", xref:"x", yref:"y", x0:lineStart, x1:lineEnd,
        y0:isLong ? sl : ep, y1:isLong ? ep : sl,
        fillcolor:riskFill, line:{{width:0}}, layer:"below"
      }});
      shapes.push({{
        type:"rect", xref:"x", yref:"y", x0:lineStart, x1:lineEnd,
        y0:isLong ? ep : tp, y1:isLong ? tp : ep,
        fillcolor:rewFill, line:{{width:0}}, layer:"below"
      }});
      for (const [px, label, color] of [[sl,"SL",slColor],[tp,"TP",tpColor]]) {{
        out.push({{
          type:"scatter", mode:"lines", x:[lineStart, lineEnd], y:[px, px],
          line:{{color:color, width:1.5, dash:lineDash}}, showlegend:false,
          hovertemplate:label+": %{{y:.5f}}<extra></extra>",
          xaxis:"x", yaxis:"y"
        }});
        annotations.push({{
          xref:"x", yref:"y", x:lineEnd, y:px,
          text:label+" "+px.toFixed(5), showarrow:false,
          font:{{size:9, color:color}}, xanchor:"left", xshift:4
        }});
      }}
    }}

    if (signal) {{
      const st = mt5Time(t.signal_time) || et;
      if (st >= start) out.push({{
        type:"scatter", mode:"markers+text", x:[st], y:[ep],
        marker:{{symbol:"diamond", size:16, color:"#ffc107",
          line:{{width:2, color:"white"}}}},
        text:["🔔 SIGNAL"],
        textposition:isLong ? "top center" : "bottom center",
        textfont:{{size:10, color:"#ffc107"}},
        hovertemplate:"Tín hiệu "+dir+"<br>%{{x}}<br>Entry dự kiến: "+ep.toFixed(5)+
          "<br>SL: "+(Number.isFinite(sl)?sl.toFixed(5):"—")+
          "<br>TP: "+(Number.isFinite(tp)?tp.toFixed(5):"—")+"<extra></extra>",
        showlegend:false, xaxis:"x", yaxis:"y"
      }});
      if (et >= start) out.push({{
        type:"scatter", mode:"markers+text", x:[et], y:[ep],
        marker:{{symbol:"circle-open", size:12, color:"#ffc107", line:{{width:2}}}},
        text:["ENTRY? "+ep.toFixed(5)], textposition:"middle right",
        textfont:{{size:9, color:"#ffc107"}},
        hovertemplate:"Entry dự kiến<br>%{{x}} @ %{{y:.5f}}<extra></extra>",
        showlegend:false, xaxis:"x", yaxis:"y"
      }});
    }} else if (et >= start) {{
      const mColor = isLong ? COLORS.up : COLORS.down;
      out.push({{
        type:"scatter", mode:"markers+text", x:[et], y:[ep],
        marker:{{symbol:isLong ? "triangle-up" : "triangle-down", size:14,
          color:mColor, line:{{width:1, color:"white"}}}},
        text:["ENTRY "+ep.toFixed(5)],
        textposition:isLong ? "top center" : "bottom center",
        textfont:{{size:9, color:ENTRY_BLUE}},
        hovertemplate:"Entry<br>%{{x}}<br>"+dir+" @ %{{y:.5f}}<br>SL: "+
          (Number.isFinite(sl)?sl.toFixed(5):"—")+"<br>TP: "+
          (Number.isFinite(tp)?tp.toFixed(5):"—")+"<extra></extra>",
        showlegend:false, xaxis:"x", yaxis:"y"
      }});
    }}

    const xp = Number(t.exit_px);
    if (!signal && status === "CLOSED" && xt && xt >= start && Number.isFinite(xp)) {{
      const reason = t.reason || "";
      const rVal = Number(t.r);
      const exitColor = (Number.isFinite(rVal) && rVal > 0) ? COLORS.tp : COLORS.sl;
      out.push({{
        type:"scatter", mode:"markers+text", x:[xt], y:[xp],
        marker:{{symbol:"x", size:10, color:exitColor, line:{{width:2}}}},
        text:["EXIT "+xp.toFixed(5)+(reason ? " ("+reason+")" : "")],
        textposition:"bottom center",
        textfont:{{size:9, color:exitColor}},
        hovertemplate:"Exit: %{{y:.5f}}<br>R="+(t.r != null ? t.r : "—")+"<extra></extra>",
        showlegend:false, xaxis:"x", yaxis:"y"
      }});
    }} else if (status === "OPEN") {{
      annotations.push({{
        xref:"x", yref:"y", x:et, y:ep, text:"● OPEN",
        showarrow:true, arrowhead:2,
        font:{{size:10, color:"#ffeb3b"}},
        bgcolor:"rgba(0,0,0,0.6)", bordercolor:"#ffeb3b"
      }});
    }}
    }} catch (e) {{ /* skip bad trade overlay */ }}
  }}
  return {{traces:out, shapes, annotations}};
}}
async function refresh() {{
  try {{
    const response=await fetch(SNAP_URL,{{cache:"no-store"}});
    if (!response.ok) throw new Error("HTTP "+response.status);
    const snap=await response.json(), conn=snap.connection || {{}};
    let rows=((snap.history || {{}}).bars || []).slice();
    if (conn.bar) rows.push(conn.bar);
    const byTime=new Map();
    for (const r of rows) byTime.set(r.time,r);
    rows=Array.from(byTime.values()).sort((a,b)=>String(a.time).localeCompare(String(b.time))).slice(-MAX_BARS);
    if (!rows.length) throw new Error(SIM_MODE ? "Chưa có nến Simulate (chọn from/to hoặc Start feed)" : "Chưa có bars.json");

    const age=Math.max(0,(Date.now()/1000)-Number(snap.connection_mtime || 0));
    const state=snap.state || {{}};
    let online, allowed;
    if (PAPER_MODE) {{
      online=Boolean(snap.online);
      const last=rows[rows.length-1];
      setText("conn",online?"READY":"WAITING",online?"online":"offline");
      setText("price",Number(last.close).toFixed(5));
      setText("spread",(state.day_trades_taken ?? "—")+"/"+(state.strategy?.max_trades_per_day ?? "—"));
      setText("positions",state.slots_remaining ?? "—");
      allowed=Boolean(state.in_session);
      setText("trading",allowed?"ACTIVE":"OFF",allowed?"online":"offline");
      document.getElementById("note").textContent=
        "Giá live EA "+(conn.server_time || "—")+" · Paper snapshot "+(state.updated_at || "—");
    }} else if (SIM_MODE) {{
      const sim=snap.sim || {{}};
      const st=String(sim.status || "idle");
      online=Boolean(snap.online) || st==="running" || st==="paused" || st==="completed";
      const last=rows[rows.length-1];
      const bid=conn.bid!=null?Number(conn.bid):Number(last.close);
      const ask=conn.ask!=null?Number(conn.ask):bid;
      const spr=conn.spread_points!=null?conn.spread_points:"—";
      setText("conn",online?"ONLINE":"OFFLINE", online?"online":"offline");
      setText("price",bid.toFixed(5)+" / "+ask.toFixed(5));
      setText("spread",spr!=="—"?spr+" pts":"—");
      setText("positions",snap.progress || ((sim.bars_done||0)+"/"+(sim.bars_total||"—")));
      setText("trading",st.toUpperCase(), online?"online":"offline");
      const decision=snap.decision || {{}};
      const action=String(decision.action || "FLAT").toUpperCase();
      let dcls="flat";
      if (action==="BUY" || action==="SELL") dcls="signal";
      else if (action==="HOLD") dcls="online";
      setText("decision",action,dcls);
      setText("slots",sim.last_bar || last.time || "—");
      document.getElementById("note").textContent=
        "Simulate "+(sim.date_from||"?")+" → "+(sim.date_to||"?")+
        " · EA "+(sim.ea_status||st)+
        " · cursor "+(sim.last_bar || last.time || "—")+
        " · reason "+(decision.reason||"—")+
        " · "+rows.length+" nến";
    }} else {{
      // File mtime can lag on synced folders — allow 30s before OFFLINE
      online=Boolean(conn.connected) && age<=30;
      const stale=Boolean(conn.connected) && age>30;
      setText("conn",online?"ONLINE":(stale?"STALE":"OFFLINE"),online?"online":"offline");
      setText("price",(conn.bid ?? "—")+" / "+(conn.ask ?? "—"));
      setText("spread",conn.spread_points!=null?conn.spread_points+" pts":"—");
      setText("positions",conn.positions ?? "—");
      allowed=Boolean(conn.terminal_trade_allowed && conn.account_trade_allowed);
      setText("trading",allowed?"ON":"OFF",allowed?"online":"offline");
      const decision=snap.decision || {{}};
      const action=String(decision.action || "—").toUpperCase();
      const reason=String(decision.reason || "—");
      let dcls="flat";
      if (action==="BUY" || action==="SELL") dcls="signal";
      else if (action==="HOLD") dcls="online";
      else if (!online) dcls="offline";
      setText("decision",action,dcls);
      setText("slots",decision.slots_remaining ?? "—");
      let note="Heartbeat "+age.toFixed(1)+"s · MT5 "+(conn.server_time || "—")+
        " · reason "+reason+
        " · strategy "+(decision.strategy_name || "—");
      if (!online) {{
        note += " · Kiểm tra chart EA đang chạy + AutoTrading (Algo) bật";
      }}
      document.getElementById("note").textContent=note;
    }}

    const x=rows.map(r=>mt5Time(r.time));
    const candle={{type:"candlestick",x,open:rows.map(r=>r.open),high:rows.map(r=>r.high),
      low:rows.map(r=>r.low),close:rows.map(r=>r.close),
      increasing:{{line:{{color:COLORS.up}},fillcolor:COLORS.up}},
      decreasing:{{line:{{color:COLORS.down}},fillcolor:COLORS.down}},
      showlegend:false,xaxis:"x",yaxis:"y"}};
    const volume={{type:"bar",x,y:rows.map(r=>r.tick_volume || 0),
      marker:{{color:rows.map(r=>Number(r.close)>=Number(r.open)?COLORS.up:COLORS.down)}},
      opacity:.45,showlegend:false,xaxis:"x2",yaxis:"y2"}};
    const trade=tradeLayers(snap.trades,x[0],x[x.length-1]);
    const traces=[candle,volume,...trade.traces];
    const mid=(Number(conn.bid)+Number(conn.ask))/2;
    const shapes=[...trade.shapes];
    const annotations=[...trade.annotations];
    if (Number.isFinite(mid)) {{
      shapes.push({{type:"line",xref:"paper",x0:0,x1:1,yref:"y",
        y0:mid,y1:mid,line:{{color:COLORS.live,width:1,dash:"dash"}}}});
      annotations.push({{xref:"paper",x:1,yref:"y",y:mid,
        text:PRICE_TAG+" "+mid.toFixed(5),showarrow:false,xanchor:"left",
        font:{{color:COLORS.live,size:10}}}});
    }}
    const layout={{
      title:{{text:"{chart_title}",font:{{size:14,color:COLORS.text}},x:.01}},
      paper_bgcolor:COLORS.bg,plot_bgcolor:COLORS.bg,font:{{color:COLORS.text,size:11}},
      margin:{{l:8,r:96,t:42,b:28}},showlegend:false,hovermode:"x unified",
      uirevision:UI_REV,dragmode:"pan",shapes,annotations,
      xaxis:{{domain:[0,1],anchor:"y",rangeslider:{{visible:false}},showticklabels:false,
        gridcolor:COLORS.grid,rangebreaks:[{{bounds:["sat","mon"]}}]}},
      yaxis:{{domain:[.22,1],side:"right",gridcolor:COLORS.grid,title:"Price"}},
      xaxis2:{{domain:[0,1],anchor:"y2",matches:"x",gridcolor:COLORS.grid,
        rangebreaks:[{{bounds:["sat","mon"]}}]}},
      yaxis2:{{domain:[0,.16],side:"right",gridcolor:COLORS.grid,title:"Vol"}}
    }};
    await Plotly.react("chart",traces,layout,{{displaylogo:false,responsive:true,scrollZoom:true}});
    firstRender=false;
  }} catch (err) {{
    document.getElementById("note").textContent="Lỗi chart: "+err.message;
    setText("conn","OFFLINE","offline");
  }}
}}
refresh();
setInterval(refresh,POLL_MS);
</script>
</body></html>"""


def start_live_monitor_server(
  bridge_dir: Path,
  port: int = DEFAULT_MONITOR_PORT,
) -> ThreadingHTTPServer:
  bridge_dir = Path(bridge_dir)
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
        query = parse_qs(parsed.query)
        mode = (query.get("mode") or ["live"])[0].lower()
        try:
          max_bars = max(96, min(1344, int((query.get("bars") or ["672"])[0])))
        except (TypeError, ValueError):
          max_bars = 672
        if mode == "sim":
          payload = build_sim_snapshot(bridge_dir, max_bars=max_bars)
          self._send(
            200,
            json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"),
            "application/json; charset=utf-8",
          )
          return
        conn_file = connection_path(bridge_dir)
        trades = load_trades(bridge_dir)
        decision = read_json(decision_path(bridge_dir)) or {}
        action = str(decision.get("action") or "").upper()
        signal_id = decision.get("signal_id")
        known_signal = any(
          signal_id and trade.get("signal_id") == signal_id
          for trade in trades
        )
        if action in ("BUY", "SELL") and not known_signal:
          trades.append({
            "status": "SIGNAL",
            "signal_id": signal_id,
            "direction": action,
            "entry_time": decision.get("entry_time") or decision.get("bar_time"),
            "entry_px": decision.get("entry"),
            "sl": decision.get("sl"),
            "tp": decision.get("tp"),
            "strategy_name": decision.get("strategy_name"),
          })
        payload = {
          "history": read_json(bars_path(bridge_dir)) or {},
          "connection": read_json(conn_file) or {},
          "connection_mtime": conn_file.stat().st_mtime if conn_file.exists() else None,
          "trades": trades,
          "decision": decision,
        }
        self._send(
          200,
          json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"),
          "application/json; charset=utf-8",
        )
        return
      if parsed.path in ("/", "/chart"):
        query = parse_qs(parsed.query)
        mode = (query.get("mode") or ["mt5"])[0].lower()
        if mode not in ("mt5", "live", "sim", "paper"):
          mode = "mt5"
        if mode == "live":
          mode = "mt5"
        try:
          max_bars = max(96, min(1344, int((query.get("bars") or ["672"])[0])))
        except (TypeError, ValueError):
          max_bars = 672
        poll_ms = 2000 if mode == "sim" else 2000
        profile = profile_for_dir(bridge_dir)
        tf_label = profile.tf if profile else "M15"
        self._send(
          200,
          _chart_html(
            max_bars, mode=mode, poll_ms=poll_ms, tf=tf_label,
          ).encode("utf-8"),
          "text/html; charset=utf-8",
        )
        return
      self._send(404, b"not found", "text/plain")

    def log_message(self, _format: str, *_args) -> None:
      return

  class ReusableServer(ThreadingHTTPServer):
    allow_reuse_address = True

  server = ReusableServer(("0.0.0.0", int(port)), Handler)
  thread = threading.Thread(
    target=server.serve_forever,
    name="mt5-live-monitor-http",
    daemon=True,
  )
  thread.start()
  return server


def ensure_chart_server(
  bridge_dir: Path | None = None,
  port: int | None = None,
  *,
  tf: str | None = None,
  mode: str = "live",
) -> bool:
  """Start chart HTTP server once for a given TF × mode (or an explicit port).

  Use SIM_MONITOR_PORT/H1_SIM_MONITOR_PORT for Simulate (avoids stale Live
  process reporting mode=live data). ``tf``/``mode`` are an alternative to
  passing ``port`` explicitly — they resolve via runtime_profiles.
  """
  import urllib.request

  if port is None:
    port = get_profile(tf or "M15", mode).monitor_port
  port = int(port)
  is_sim = port in SIM_MONITOR_PORTS
  profile = profile_for_port(port)
  default_dir = profile.bridge_dir if profile else (BRIDGE_SIM_DIR if is_sim else BRIDGE_DIR)
  lock = _chart_server_lock(port)

  def _healthy() -> bool:
    try:
      with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.4) as r:
        return r.read() == b"ok"
    except Exception:
      return False

  if _healthy() and not is_sim:
    return True
  # For sim ports: if something answers but lacks mode=sim, still try; prefer our process
  with lock:
    if is_sim:
      # Always prefer a server we started on this SIM port (fresh code)
      if _CHART_SERVERS.get(port) is not None and _healthy():
        return True
      if _healthy():
        # Probe sim snapshot
        try:
          with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/snapshot?mode=sim&bars=48", timeout=1.0
          ) as r:
            data = json.loads(r.read().decode("utf-8"))
          if "sim" in data or (data.get("history") or {}).get("source") == "sim_cache":
            return True
        except Exception:
          pass
      try:
        _CHART_SERVERS[port] = start_live_monitor_server(
          Path(bridge_dir) if bridge_dir else default_dir,
          port=port,
        )
      except OSError:
        pass
      return _healthy()

    if _healthy():
      return True
    try:
      _CHART_SERVERS[port] = start_live_monitor_server(
        Path(bridge_dir) if bridge_dir else default_dir,
        port=port,
      )
    except OSError:
      pass
    return _healthy()
