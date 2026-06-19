/* Chart module: loads sample market JSON and renders Lightweight Charts when available. */
const MarketChart = (() => {
  const assetFiles = {
    bitcoin: "data/bitcoin.json",
    gold: "data/gold.json"
  };

  const assetLabels = {
    bitcoin: "Bitcoin",
    gold: "Gold"
  };

  const rangeLengths = {
    "1D": 2,
    "1W": 7,
    "1M": 30,
    "3M": 90,
    "1Y": 365,
    "10Y": Number.MAX_SAFE_INTEGER
  };

  let chart;
  let lineSeries;
  let candleSeries;
  let currentAsset = "bitcoin";
  let currentRange = "1M";
  let currentInterval = "1D";
  let currentChartMode = "line";
  let marketData = {};
  let onEvaluation = () => {};

  const generateFallbackData = (asset) => {
    const start = new Date("2026-01-01T00:00:00");
    const base = asset === "bitcoin" ? 100000 : 3300;
    const data = [];

    for (let index = 0; index < 3650; index += 1) {
      const date = new Date(start);
      date.setDate(start.getDate() + index);
      const wave = Math.sin(index / 8) * (asset === "bitcoin" ? 3400 : 65);
      const longerWave = Math.cos(index / 21) * (asset === "bitcoin" ? 5200 : 90);
      const drift = index * (asset === "bitcoin" ? 155 : 3.2);
      const close = Math.round((base + drift + wave + longerWave) * 100) / 100;
      const open = Math.round((close - (asset === "bitcoin" ? 420 : 8)) * 100) / 100;
      const high = Math.round((close + (asset === "bitcoin" ? 680 : 12)) * 100) / 100;
      const low = Math.round((close - (asset === "bitcoin" ? 720 : 14)) * 100) / 100;

      data.push({
        date: date.toISOString().slice(0, 10),
        open,
        high,
        low,
        price: close
      });
    }

    return data;
  };

  const loadJson = async (asset) => {
    try {
      const response = await fetch(assetFiles[asset]);
      if (!response.ok) {
        throw new Error(`Unable to load ${asset}`);
      }
      return response.json();
    } catch (error) {
      console.info("Using generated fallback data", error);
      return generateFallbackData(asset);
    }
  };

  const loadAllData = async () => {
    const entries = await Promise.all(
      Object.keys(assetFiles).map(async (asset) => [asset, await loadJson(asset)])
    );
    marketData = Object.fromEntries(entries);
  };

  const getFullData = () => marketData[currentAsset] || [];

  const getVisibleData = () => {
    const aggregated = PsychologyEngine.aggregateSeries(getFullData(), currentInterval);
    return aggregated.slice(-rangeLengths[currentRange]);
  };

  const toLineData = (data) => data.map((point) => ({
    time: point.date,
    value: point.close ?? point.price
  }));

  const toCandleData = (data) => data.map((point) => ({
    time: point.date,
    open: point.open ?? point.price,
    high: point.high ?? point.price,
    low: point.low ?? point.price,
    close: point.close ?? point.price
  }));

  const drawFallbackChart = (container, data) => {
    const prices = data.map((point) => point.close ?? point.price);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const width = Math.max(container.clientWidth, 320);
    const height = Math.max(container.clientHeight, 280);
    const points = data.map((point, index) => {
      const x = (index / Math.max(data.length - 1, 1)) * width;
      const price = point.close ?? point.price;
      const y = height - ((price - min) / Math.max(max - min, 1)) * (height - 36) - 18;
      return `${x},${y}`;
    }).join(" ");

    container.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Fallback price line">
        <defs>
          <linearGradient id="lineGradient" x1="0" x2="1">
            <stop offset="0%" stop-color="#60a5fa"></stop>
            <stop offset="100%" stop-color="#74d99f"></stop>
          </linearGradient>
        </defs>
        <polyline points="${points}" fill="none" stroke="url(#lineGradient)" stroke-width="3"></polyline>
        <text x="16" y="30" fill="#8ea0b7" font-size="13">Lightweight Charts unavailable. Showing static fallback.</text>
      </svg>
    `;
  };

  const applyChartMode = () => {
    if (!lineSeries || !candleSeries) {
      return;
    }

    const showCandles = currentChartMode === "candle";
    lineSeries.applyOptions({ visible: !showCandles });
    candleSeries.applyOptions({ visible: showCandles });
  };

  const createChart = (container) => {
    if (!window.LightweightCharts) {
      return;
    }

    chart = LightweightCharts.createChart(container, {
      layout: {
        background: { color: "#08131e" },
        textColor: "#8ea0b7"
      },
      grid: {
        vertLines: { color: "rgba(148, 163, 184, 0.08)" },
        horzLines: { color: "rgba(148, 163, 184, 0.08)" }
      },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal
      },
      rightPriceScale: {
        borderColor: "rgba(148, 163, 184, 0.2)"
      },
      timeScale: {
        borderColor: "rgba(148, 163, 184, 0.2)",
        timeVisible: true
      },
      handleScroll: true,
      handleScale: true
    });

    lineSeries = chart.addLineSeries({
      color: "#74d99f",
      lineWidth: 3,
      priceLineColor: "rgba(116, 217, 159, 0.4)"
    });

    candleSeries = chart.addCandlestickSeries({
      upColor: "#74d99f",
      downColor: "#fb7185",
      borderVisible: false,
      wickUpColor: "#74d99f",
      wickDownColor: "#fb7185"
    });

    applyChartMode();

    new ResizeObserver(() => {
      chart.applyOptions({
        width: container.clientWidth,
        height: container.clientHeight
      });
    }).observe(container);
  };

  const renderMarketMap = (evaluation) => {
    const mapContainer = document.querySelector("#market-map");
    const companionAssets = [
      {
        asset: assetLabels[currentAsset],
        trend: `${evaluation.trend > 0 ? "+" : ""}${evaluation.trend}%`,
        zone: evaluation.possibleZone,
        confidence: evaluation.confidence
      },
      {
        asset: currentAsset === "bitcoin" ? "Gold" : "Bitcoin",
        trend: currentAsset === "bitcoin" ? "+4.8%" : "+12.4%",
        zone: currentAsset === "bitcoin" ? "Belief" : "Optimism",
        confidence: 58
      },
      {
        asset: "S&P500",
        trend: "+3.1%",
        zone: "Complacency",
        confidence: 49
      },
      {
        asset: "USD",
        trend: "-1.4%",
        zone: "Fear",
        confidence: 44
      }
    ];

    mapContainer.innerHTML = companionAssets.map((item) => `
      <article class="asset-card">
        <div class="asset-meta">${item.trend} trend</div>
        <h3>${item.asset}</h3>
        <strong>${item.zone}</strong>
        <div class="asset-meta">Possible Zone</div>
        <div class="confidence-track" aria-label="Confidence ${item.confidence}%">
          <span style="width: ${item.confidence}%"></span>
        </div>
        <div class="asset-meta">Confidence: ${item.confidence}%</div>
      </article>
    `).join("");
  };

  const render = () => {
    const container = document.querySelector("#chart");
    const visibleData = getVisibleData();
    const evaluation = PsychologyEngine.evaluate(getFullData(), visibleData);

    if (lineSeries && candleSeries) {
      lineSeries.setData(toLineData(visibleData));
      candleSeries.setData(toCandleData(visibleData));
      applyChartMode();
      chart.timeScale().fitContent();
    } else {
      drawFallbackChart(container, visibleData);
    }

    PsychologyEngine.renderRsiPanel(document.querySelector("#rsi-panel"), evaluation.rsiByInterval);
    renderMarketMap(evaluation);
    onEvaluation(evaluation);
  };

  const setAsset = (asset) => {
    currentAsset = asset;
    render();
  };

  const setRange = (range) => {
    currentRange = range;
    render();
  };

  const setInterval = (interval) => {
    currentInterval = interval;
    render();
  };

  const setChartMode = (mode) => {
    currentChartMode = mode;
    render();
  };

  const init = async (evaluationHandler) => {
    onEvaluation = evaluationHandler;
    await loadAllData();
    createChart(document.querySelector("#chart"));
    render();
  };

  return {
    init,
    setAsset,
    setRange,
    setInterval,
    setChartMode,
    getCurrentData: getVisibleData
  };
})();
