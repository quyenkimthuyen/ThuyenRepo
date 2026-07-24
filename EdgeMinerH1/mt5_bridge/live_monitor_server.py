"""Local HTTP chart endpoint for smooth browser-side MT5 updates."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from mt5_bridge.protocol import bars_path, connection_path, decision_path, read_json
from mt5_bridge.trade_journal import load_trades

DEFAULT_MONITOR_PORT = 8865


def _plotly_js_path() -> Path:
  import plotly
  return Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"


def _chart_html(max_bars: int, *, mode: str = "mt5", poll_ms: int = 2000) -> str:
  paper_mode = mode == "paper"
  chart_title = "EURUSD H1 · Paper Trade" if paper_mode else "EURUSD H1 · XM MT5 live"
  labels = (
    ("PAPER ENGINE", "LAST PRICE", "WEEK TRADES", "SLOTS LEFT", "SESSION")
    if paper_mode else
    ("EA CONNECTION", "BID / ASK", "SPREAD", "OPEN POSITIONS", "ALGO TRADING")
  )
  return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    html,body{{margin:0;background:#131722;color:#d1d4dc;font-family:Arial,sans-serif}}
    #status{{display:grid;grid-template-columns:repeat(5,minmax(110px,1fr));gap:8px;padding:8px 10px}}
    .metric{{background:#1e222d;border:1px solid #2a2e39;border-radius:6px;padding:7px 10px}}
    .label{{font-size:11px;color:#8b8f9a}} .value{{font-size:16px;font-weight:600;margin-top:3px}}
    #note{{font-size:11px;color:#8b8f9a;padding:0 12px 4px}} #chart{{height:585px}}
    .online{{color:#26a69a}} .offline{{color:#ef5350}}
  </style>
  <script src="/plotly.min.js"></script>
</head>
<body>
  <div id="status">
    <div class="metric"><div class="label">{labels[0]}</div><div class="value" id="conn">WAITING</div></div>
    <div class="metric"><div class="label">{labels[1]}</div><div class="value" id="price">—</div></div>
    <div class="metric"><div class="label">{labels[2]}</div><div class="value" id="spread">—</div></div>
    <div class="metric"><div class="label">{labels[3]}</div><div class="value" id="positions">—</div></div>
    <div class="metric"><div class="label">{labels[4]}</div><div class="value" id="trading">—</div></div>
  </div>
  <div id="note">Đang kết nối ForgeBridge EA…</div>
  <div id="chart"></div>
<script>
const MAX_BARS = {max_bars};
const PAPER_MODE = {str(paper_mode).lower()};
const POLL_MS = {max(500, int(poll_ms))};
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
  const el=document.getElementById(id); el.textContent=text; el.className="value "+cls;
}}
function tradeLayers(trades, start, end) {{
  // Same drawing style as Paper Trade (_add_order_overlays):
  // risk/reward zones · SL/TP lines + labels · ENTRY ▲▼ · EXIT ✕ · OPEN badge
  const out=[], shapes=[], annotations=[];
  const ENTRY_BLUE = "#2962ff";
  for (const t of (trades || [])) {{
    const et = mt5Time(t.entry_time || t.entry || t.signal_time);
    const ep = Number(t.entry_px != null ? t.entry_px : t.entry);
    if (!et || !Number.isFinite(ep)) continue;
    const xt = mt5Time(t.exit_time || t.exit);
    const lineEnd = xt || end;
    if (lineEnd < start || et > end) continue;
    const dir = String(t.direction || t.dir || "").toUpperCase();
    const isLong = dir === "BUY" || dir === "LONG";
    const status = String(t.status || "CLOSED").toUpperCase();
    const signal = status === "SIGNAL";
    const lineStart = et < start ? start : et;
    const sl = Number(t.sl), tp = Number(t.tp);
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
  }}
  return {{traces:out, shapes, annotations}};
}}
async function refresh() {{
  try {{
    const response=await fetch("/snapshot",{{cache:"no-store"}});
    if (!response.ok) throw new Error("HTTP "+response.status);
    const snap=await response.json(), conn=snap.connection || {{}};
    let rows=((snap.history || {{}}).bars || []).slice();
    if (conn.bar) rows.push(conn.bar);
    const byTime=new Map();
    for (const r of rows) byTime.set(r.time,r);
    rows=Array.from(byTime.values()).sort((a,b)=>String(a.time).localeCompare(String(b.time))).slice(-MAX_BARS);
    if (!rows.length) throw new Error("Chưa có bars.json");

    const age=Math.max(0,(Date.now()/1000)-Number(snap.connection_mtime || 0));
    const state=snap.state || {{}};
    let online, allowed;
    if (PAPER_MODE) {{
      online=Boolean(snap.online);
      const last=rows[rows.length-1];
      setText("conn",online?"READY":"WAITING",online?"online":"offline");
      setText("price",Number(last.close).toFixed(5));
      setText("spread",(state.week_trades_taken ?? "—")+"/"+(state.strategy?.max_trades_per_week ?? "—"));
      setText("positions",state.slots_remaining ?? "—");
      allowed=Boolean(state.in_session);
      setText("trading",allowed?"ACTIVE":"OFF",allowed?"online":"offline");
      document.getElementById("note").textContent=
        "Giá live EA "+(conn.server_time || "—")+" · Paper snapshot "+(state.updated_at || "—");
    }} else {{
      online=Boolean(conn.connected) && age<=10;
      setText("conn",online?"ONLINE":"OFFLINE",online?"online":"offline");
      setText("price",(conn.bid ?? "—")+" / "+(conn.ask ?? "—"));
      setText("spread",conn.spread_points!=null?conn.spread_points+" points":"—");
      setText("positions",conn.positions ?? "—");
      allowed=Boolean(conn.terminal_trade_allowed && conn.account_trade_allowed);
      setText("trading",allowed?"ON":"OFF",allowed?"online":"offline");
      document.getElementById("note").textContent=
        "Heartbeat "+age.toFixed(1)+"s · MT5 server "+(conn.server_time || "—")+
        " · cập nhật trực tiếp, không reload chart";
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
        text:"LIVE "+mid.toFixed(5),showarrow:false,xanchor:"left",
        font:{{color:COLORS.live,size:10}}}});
    }}
    const layout={{
      title:{{text:"{chart_title}",font:{{size:14,color:COLORS.text}},x:.01}},
      paper_bgcolor:COLORS.bg,plot_bgcolor:COLORS.bg,font:{{color:COLORS.text,size:11}},
      margin:{{l:8,r:96,t:42,b:28}},showlegend:false,hovermode:"x unified",
      uirevision:"mt5-live",dragmode:"pan",shapes,annotations,
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
        try:
          max_bars = max(24, min(336, int((query.get("bars") or ["168"])[0])))
        except (TypeError, ValueError):
          max_bars = 168
        self._send(
          200,
          _chart_html(max_bars).encode("utf-8"),
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
    name="mt5-live-monitor-http",
    daemon=True,
  )
  thread.start()
  return server
