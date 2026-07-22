"""Local HTTP chart endpoint for smooth browser-side MT5 updates."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from mt5_bridge.protocol import bars_path, connection_path, read_json
from mt5_bridge.trade_journal import load_trades

DEFAULT_MONITOR_PORT = 8765


def _plotly_js_path() -> Path:
  import plotly
  return Path(plotly.__file__).resolve().parent / "package_data" / "plotly.min.js"


def _chart_html(max_bars: int) -> str:
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
    <div class="metric"><div class="label">EA CONNECTION</div><div class="value" id="conn">WAITING</div></div>
    <div class="metric"><div class="label">BID / ASK</div><div class="value" id="price">—</div></div>
    <div class="metric"><div class="label">SPREAD</div><div class="value" id="spread">—</div></div>
    <div class="metric"><div class="label">OPEN POSITIONS</div><div class="value" id="positions">—</div></div>
    <div class="metric"><div class="label">ALGO TRADING</div><div class="value" id="trading">—</div></div>
  </div>
  <div id="note">Đang kết nối ForgeBridge EA…</div>
  <div id="chart"></div>
<script>
const MAX_BARS = {max_bars};
const COLORS = {{bg:"#131722", grid:"#363a45", text:"#d1d4dc", up:"#26a69a",
  down:"#ef5350", sl:"#f23645", tp:"#089981", live:"#f7c948"}};
let firstRender = true;

function mt5Time(value) {{
  if (!value) return null;
  const p = String(value).trim().split(" ");
  return p[0].replaceAll(".","-") + "T" + (p[1] || "00:00") +
    ((p[1] || "").split(":").length === 2 ? ":00" : "");
}}
function setText(id, text, cls="") {{
  const el=document.getElementById(id); el.textContent=text; el.className="value "+cls;
}}
function tradeTraces(trades, start, end) {{
  const out=[];
  for (const t of (trades || [])) {{
    const et=mt5Time(t.entry_time || t.entry), ep=Number(t.entry_px);
    if (!et || !Number.isFinite(ep)) continue;
    const xt=mt5Time(t.exit_time || t.exit), lineEnd=xt || end;
    if (lineEnd < start || et > end) continue;
    const dir=String(t.direction || t.dir || "").toUpperCase();
    const buy=dir==="BUY" || dir==="LONG", color=buy?COLORS.up:COLORS.down;
    if (et >= start) out.push({{
      type:"scatter",mode:"markers+text",x:[et],y:[ep],
      marker:{{symbol:buy?"triangle-up":"triangle-down",size:13,color}},
      text:[dir+" "+ep.toFixed(5)],textposition:buy?"top center":"bottom center",
      textfont:{{size:9,color}},hovertemplate:dir+"<br>%{{x}} @ %{{y:.5f}}<extra></extra>",
      showlegend:false,xaxis:"x",yaxis:"y"
    }});
    for (const [value,label,lineColor] of [[t.sl,"SL",COLORS.sl],[t.tp,"TP",COLORS.tp]]) {{
      const px=Number(value); if (!Number.isFinite(px)) continue;
      out.push({{
        type:"scatter",mode:"lines",x:[et<start?start:et,lineEnd],y:[px,px],
        line:{{color:lineColor,width:1.2,dash:"dot"}},showlegend:false,
        hovertemplate:label+": %{{y:.5f}}<extra></extra>",xaxis:"x",yaxis:"y"
      }});
    }}
    const xp=Number(t.exit_px);
    if (xt && xt>=start && Number.isFinite(xp)) out.push({{
      type:"scatter",mode:"markers+text",x:[xt],y:[xp],
      marker:{{symbol:"x",size:11,color:Number(t.r)>0?COLORS.tp:COLORS.sl}},
      text:["EXIT "+xp.toFixed(5)],textposition:"bottom center",textfont:{{size:9}},
      showlegend:false,xaxis:"x",yaxis:"y",
      hovertemplate:"Exit<br>%{{x}} @ %{{y:.5f}}<extra></extra>"
    }});
  }}
  return out;
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
    const online=Boolean(conn.connected) && age<=10;
    setText("conn",online?"ONLINE":"OFFLINE",online?"online":"offline");
    setText("price",(conn.bid ?? "—")+" / "+(conn.ask ?? "—"));
    setText("spread",conn.spread_points!=null?conn.spread_points+" points":"—");
    setText("positions",conn.positions ?? "—");
    const allowed=Boolean(conn.terminal_trade_allowed && conn.account_trade_allowed);
    setText("trading",allowed?"ON":"OFF",allowed?"online":"offline");
    document.getElementById("note").textContent=
      "Heartbeat "+age.toFixed(1)+"s · MT5 server "+(conn.server_time || "—")+
      " · cập nhật trực tiếp, không reload chart";

    const x=rows.map(r=>mt5Time(r.time));
    const candle={{type:"candlestick",x,open:rows.map(r=>r.open),high:rows.map(r=>r.high),
      low:rows.map(r=>r.low),close:rows.map(r=>r.close),
      increasing:{{line:{{color:COLORS.up}},fillcolor:COLORS.up}},
      decreasing:{{line:{{color:COLORS.down}},fillcolor:COLORS.down}},
      showlegend:false,xaxis:"x",yaxis:"y"}};
    const volume={{type:"bar",x,y:rows.map(r=>r.tick_volume || 0),
      marker:{{color:rows.map(r=>Number(r.close)>=Number(r.open)?COLORS.up:COLORS.down)}},
      opacity:.45,showlegend:false,xaxis:"x2",yaxis:"y2"}};
    const traces=[candle,volume,...tradeTraces(snap.trades,x[0],x[x.length-1])];
    const mid=(Number(conn.bid)+Number(conn.ask))/2;
    const shapes=Number.isFinite(mid)?[{{type:"line",xref:"paper",x0:0,x1:1,yref:"y",
      y0:mid,y1:mid,line:{{color:COLORS.live,width:1,dash:"dash"}}}}]:[];
    const annotations=Number.isFinite(mid)?[{{xref:"paper",x:1,yref:"y",y:mid,
      text:"LIVE "+mid.toFixed(5),showarrow:false,xanchor:"left",font:{{color:COLORS.live,size:10}}}}]:[];
    const layout={{
      title:{{text:"EURUSD H1 · XM MT5 live",font:{{size:14,color:COLORS.text}},x:.01}},
      paper_bgcolor:COLORS.bg,plot_bgcolor:COLORS.bg,font:{{color:COLORS.text,size:11}},
      margin:{{l:8,r:76,t:42,b:28}},showlegend:false,hovermode:"x unified",
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
setInterval(refresh,2000);
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
        payload = {
          "history": read_json(bars_path(bridge_dir)) or {},
          "connection": read_json(conn_file) or {},
          "connection_mtime": conn_file.stat().st_mtime if conn_file.exists() else None,
          "trades": load_trades(bridge_dir),
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
