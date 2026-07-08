"""Static Lightweight Charts template used by the Streamlit component."""

from __future__ import annotations


def build_chart_html(payload_json: str, *, height: int) -> str:
    """Return a self-contained HTML document for the chart iframe."""
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <script src="https://unpkg.com/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    :root {{
      --bg: #0b0f14;
      --panel: #131722;
      --panel-soft: #1e222d;
      --grid: rgba(54, 58, 69, 0.55);
      --border: #2a2e39;
      --text: #d1d4dc;
      --muted: #787b86;
      --bull: #089981;
      --bear: #f23645;
      --blue: #2962ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, "Segoe UI", Roboto, Arial, sans-serif;
      overflow: hidden;
    }}
    .terminal {{
      height: {height + 92}px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: linear-gradient(180deg, #111722 0%, #0b0f14 100%);
      overflow: hidden;
    }}
    .topbar {{
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 0 12px;
      border-bottom: 1px solid var(--border);
      background: rgba(19, 23, 34, 0.96);
    }}
    .identity {{
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }}
    .symbol {{
      font-size: 13px;
      font-weight: 700;
      letter-spacing: .08em;
      color: #f2f4f8;
      white-space: nowrap;
    }}
    .strategy {{
      font-size: 12px;
      color: var(--muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .stats {{
      display: flex;
      gap: 10px;
      color: var(--muted);
      font-size: 11px;
      white-space: nowrap;
    }}
    .stat strong {{ color: var(--text); font-weight: 600; }}
    .toolbar {{
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    button {{
      border: 1px solid var(--border);
      background: var(--panel-soft);
      color: var(--text);
      border-radius: 5px;
      height: 26px;
      padding: 0 9px;
      font-size: 11px;
      cursor: pointer;
    }}
    button:hover {{ border-color: var(--blue); color: #ffffff; }}
    .replaybar {{
      height: 34px;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0 10px;
      border-bottom: 1px solid var(--border);
      background: #0f141d;
    }}
    .replaybar input[type="range"] {{
      flex: 1;
      min-width: 140px;
      accent-color: var(--blue);
    }}
    .replaybar select {{
      height: 26px;
      border: 1px solid var(--border);
      border-radius: 5px;
      color: var(--text);
      background: var(--panel-soft);
      font-size: 11px;
    }}
    .replay-status {{
      width: 150px;
      color: var(--muted);
      font-size: 11px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .charts {{
      height: {height}px;
      display: grid;
      grid-template-rows: 1fr 145px;
      background: var(--panel);
    }}
    .main-chart, .pane-chart {{
      min-height: 0;
      position: relative;
    }}
    .pane-chart {{
      border-top: 1px solid var(--border);
    }}
    .hint {{
      height: 14px;
      padding: 0 10px;
      color: var(--muted);
      background: #0b0f14;
      font-size: 10px;
      line-height: 14px;
      border-top: 1px solid var(--border);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .empty {{
      display: grid;
      place-items: center;
      height: 100%;
      color: var(--muted);
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <div class="terminal">
    <div class="topbar">
      <div class="identity">
        <div class="symbol" id="symbol">EURUSD</div>
        <div class="strategy" id="strategy"></div>
      </div>
      <div class="stats">
        <span class="stat">Bars <strong id="bars">0</strong></span>
        <span class="stat">Trades <strong id="trades">0</strong></span>
        <span class="stat">P/L <strong id="pnl">$0</strong></span>
      </div>
      <div class="toolbar">
        <button data-range="120">120 bars</button>
        <button data-range="500">500 bars</button>
        <button data-range="all">Fit</button>
      </div>
    </div>
    <div class="replaybar">
      <button id="replay-toggle">Replay</button>
      <button id="replay-back">◀</button>
      <button id="replay-play">Play</button>
      <button id="replay-forward">▶</button>
      <input id="replay-range" type="range" min="0" value="0" />
      <select id="replay-speed">
        <option value="900">0.5x</option>
        <option value="500" selected>1x</option>
        <option value="250">2x</option>
        <option value="100">5x</option>
      </select>
      <span id="replay-status" class="replay-status">Replay off</span>
    </div>
    <div class="charts">
      <div id="price-chart" class="main-chart"></div>
      <div id="pane-chart" class="pane-chart"></div>
    </div>
    <div class="hint">Wheel: zoom · Drag: pan · Use Fit to reset · SL red dashed · TP green dashed</div>
  </div>

  <script>
    const payload = {payload_json};
    const LWC = window.LightweightCharts;
    const priceEl = document.getElementById("price-chart");
    const paneEl = document.getElementById("pane-chart");

    document.getElementById("symbol").textContent = payload.symbol || "EURUSD";
    document.getElementById("strategy").textContent = payload.title || payload.strategy || "";
    document.getElementById("bars").textContent = (payload.candles || []).length.toLocaleString();
    document.getElementById("trades").textContent = (payload.summary?.trades || 0).toLocaleString();
    document.getElementById("pnl").textContent = `${{payload.summary?.pnl >= 0 ? "+" : ""}}${{Number(payload.summary?.pnl || 0).toFixed(0)}}$`;

    const commonLayout = {{
      layout: {{
        background: {{ type: "solid", color: "#131722" }},
        textColor: "#d1d4dc",
        fontFamily: "Inter, Segoe UI, Roboto, Arial, sans-serif",
      }},
      grid: {{
        vertLines: {{ color: "rgba(54, 58, 69, 0.55)" }},
        horzLines: {{ color: "rgba(54, 58, 69, 0.55)" }},
      }},
      crosshair: {{
        mode: LWC.CrosshairMode.Normal,
        vertLine: {{ color: "#787b86", width: 1, style: LWC.LineStyle.Dashed, labelBackgroundColor: "#2a2e39" }},
        horzLine: {{ color: "#787b86", width: 1, style: LWC.LineStyle.Dashed, labelBackgroundColor: "#2a2e39" }},
      }},
      rightPriceScale: {{
        borderColor: "#2a2e39",
        scaleMargins: {{ top: 0.10, bottom: 0.18 }},
      }},
      timeScale: {{
        borderColor: "#2a2e39",
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 8,
        barSpacing: 8,
      }},
      handleScroll: {{ mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false }},
      handleScale: {{ axisPressedMouseMove: true, mouseWheel: true, pinch: true }},
    }};

    function showEmpty(message) {{
      priceEl.innerHTML = `<div class="empty">${{message}}</div>`;
      paneEl.style.display = "none";
    }}

    if (!LWC || !payload.candles || payload.candles.length === 0) {{
      showEmpty("No chart data available");
    }} else {{
      const priceChart = LWC.createChart(priceEl, {{
        ...commonLayout,
        width: priceEl.clientWidth,
        height: priceEl.clientHeight,
      }});
      const paneChart = LWC.createChart(paneEl, {{
        ...commonLayout,
        width: paneEl.clientWidth,
        height: paneEl.clientHeight,
        rightPriceScale: {{
          borderColor: "#2a2e39",
          scaleMargins: {{ top: 0.18, bottom: 0.12 }},
        }},
      }});

      const candleSeries = priceChart.addCandlestickSeries({{
        upColor: "#089981",
        downColor: "#f23645",
        borderUpColor: "#089981",
        borderDownColor: "#f23645",
        wickUpColor: "#089981",
        wickDownColor: "#f23645",
        priceFormat: {{ type: "price", precision: 5, minMove: 0.00001 }},
      }});
      candleSeries.setData(payload.candles);

      let volumeSeries = null;
      if (payload.volume && payload.volume.length) {{
        volumeSeries = priceChart.addHistogramSeries({{
          priceFormat: {{ type: "volume" }},
          priceScaleId: "",
          scaleMargins: {{ top: 0.82, bottom: 0 }},
        }});
        volumeSeries.setData(payload.volume);
      }}

      const overlaySeries = [];
      for (const overlay of payload.overlays || []) {{
        const series = priceChart.addLineSeries({{
          color: overlay.color,
          lineWidth: overlay.width || 1,
          lineStyle: overlay.style === "dashed" ? LWC.LineStyle.Dashed : LWC.LineStyle.Solid,
          priceLineVisible: false,
          lastValueVisible: false,
        }});
        series.setData(overlay.data || []);
        overlaySeries.push({{ series, data: overlay.data || [] }});
      }}

      const tradeLineSeries = [];
      for (const line of payload.trade_lines || []) {{
        const series = priceChart.addLineSeries({{
          color: line.color,
          lineWidth: line.width || 1,
          lineStyle: line.style === "dashed" ? LWC.LineStyle.Dashed : LWC.LineStyle.Dotted,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        }});
        series.setData(line.data || []);
        tradeLineSeries.push({{ series, data: line.data || [] }});
      }}

      candleSeries.setMarkers(payload.markers || []);

      const paneData = payload.indicator?.data?.length ? payload.indicator.data : payload.equity || [];
      const paneTitle = payload.indicator?.data?.length ? payload.indicator.name : "Equity";
      const paneColor = payload.indicator?.color || "#7e57c2";
      const paneSeries = paneChart.addLineSeries({{
        color: paneColor,
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
      }});
      paneSeries.setData(paneData);

      const allCandles = payload.candles || [];
      const allVolume = payload.volume || [];
      const allMarkers = payload.markers || [];
      const allPaneData = paneData || [];
      const replayToggle = document.getElementById("replay-toggle");
      const replayBack = document.getElementById("replay-back");
      const replayForward = document.getElementById("replay-forward");
      const replayPlay = document.getElementById("replay-play");
      const replayRange = document.getElementById("replay-range");
      const replaySpeed = document.getElementById("replay-speed");
      const replayStatus = document.getElementById("replay-status");
      let replayOn = false;
      let replayIndex = Math.max(0, allCandles.length - 1);
      let replayTimer = null;
      replayRange.max = Math.max(0, allCandles.length - 1);
      replayRange.value = replayIndex;

      function filterByTime(data, time) {{
        return (data || []).filter((point) => point.time <= time);
      }}

      function filterLineSegments(data, time) {{
        return (data || []).filter((point) => point.time <= time);
      }}

      function setReplayStatus() {{
        if (!replayOn) {{
          replayStatus.textContent = "Replay off";
          return;
        }}
        const item = allCandles[replayIndex];
        const label = item ? new Date(item.time * 1000).toISOString().slice(0, 16).replace("T", " ") : "";
        replayStatus.textContent = `${{replayIndex + 1}}/${{allCandles.length}} · ${{label}}`;
      }}

      function applyReplay(index, preserveRange = true) {{
        if (!allCandles.length) return;
        replayIndex = Math.max(0, Math.min(index, allCandles.length - 1));
        replayRange.value = replayIndex;
        const endTime = allCandles[replayIndex].time;
        const candles = replayOn ? allCandles.slice(0, replayIndex + 1) : allCandles;
        candleSeries.setData(candles);
        if (volumeSeries) volumeSeries.setData(replayOn ? filterByTime(allVolume, endTime) : allVolume);
        for (const item of overlaySeries) {{
          item.series.setData(replayOn ? filterByTime(item.data, endTime) : item.data);
        }}
        for (const item of tradeLineSeries) {{
          item.series.setData(replayOn ? filterLineSegments(item.data, endTime) : item.data);
        }}
        candleSeries.setMarkers(replayOn ? filterByTime(allMarkers, endTime) : allMarkers);
        paneSeries.setData(replayOn ? filterByTime(allPaneData, endTime) : allPaneData);
        setReplayStatus();
        if (!preserveRange) {{
          const from = Math.max(0, replayIndex - 120);
          priceChart.timeScale().setVisibleLogicalRange({{ from, to: replayIndex + 12 }});
        }}
      }}

      function stopReplayTimer() {{
        if (replayTimer) clearInterval(replayTimer);
        replayTimer = null;
        replayPlay.textContent = "Play";
      }}

      function startReplayTimer() {{
        stopReplayTimer();
        replayPlay.textContent = "Pause";
        replayTimer = setInterval(() => {{
          if (!replayOn || replayIndex >= allCandles.length - 1) {{
            stopReplayTimer();
            return;
          }}
          applyReplay(replayIndex + 1, false);
        }}, Number(replaySpeed.value));
      }}

      replayToggle.addEventListener("click", () => {{
        replayOn = !replayOn;
        replayToggle.textContent = replayOn ? "Exit Replay" : "Replay";
        stopReplayTimer();
        applyReplay(replayOn ? replayIndex : allCandles.length - 1, false);
      }});
      replayBack.addEventListener("click", () => {{
        replayOn = true;
        replayToggle.textContent = "Exit Replay";
        stopReplayTimer();
        applyReplay(replayIndex - 1, false);
      }});
      replayForward.addEventListener("click", () => {{
        replayOn = true;
        replayToggle.textContent = "Exit Replay";
        stopReplayTimer();
        applyReplay(replayIndex + 1, false);
      }});
      replayPlay.addEventListener("click", () => {{
        replayOn = true;
        replayToggle.textContent = "Exit Replay";
        if (replayTimer) stopReplayTimer();
        else startReplayTimer();
      }});
      replayRange.addEventListener("input", () => {{
        replayOn = true;
        replayToggle.textContent = "Exit Replay";
        stopReplayTimer();
        applyReplay(Number(replayRange.value), false);
      }});
      replaySpeed.addEventListener("change", () => {{
        if (replayTimer) startReplayTimer();
      }});

      let syncing = false;
      priceChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {{
        if (syncing || !range) return;
        syncing = true;
        paneChart.timeScale().setVisibleLogicalRange(range);
        syncing = false;
      }});
      paneChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {{
        if (syncing || !range) return;
        syncing = true;
        priceChart.timeScale().setVisibleLogicalRange(range);
        syncing = false;
      }});

      function fitAll() {{
        priceChart.timeScale().fitContent();
        paneChart.timeScale().fitContent();
      }}

      function showLastBars(count) {{
        const total = payload.candles.length;
        const from = Math.max(0, total - count);
        priceChart.timeScale().setVisibleLogicalRange({{ from, to: total + 8 }});
      }}

      document.querySelectorAll("button[data-range]").forEach((button) => {{
        button.addEventListener("click", () => {{
          const value = button.dataset.range;
          if (value === "all") fitAll();
          else showLastBars(Number(value));
        }});
      }});

      new ResizeObserver(() => {{
        priceChart.applyOptions({{ width: priceEl.clientWidth, height: priceEl.clientHeight }});
        paneChart.applyOptions({{ width: paneEl.clientWidth, height: paneEl.clientHeight }});
      }}).observe(document.querySelector(".charts"));

      fitAll();
    }}
  </script>
</body>
</html>
"""
