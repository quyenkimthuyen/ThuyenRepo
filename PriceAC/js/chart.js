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
  let rsiChart;
  let rsiDailySeries;
  let rsiWeeklySeries;
  let rsiMonthlySeries;
  let currentAsset = "bitcoin";
  let currentRange = "1M";
  let currentInterval = "1D";
  let currentChartMode = "line";
  let marketData = {};
  let onEvaluation = () => {};
  let chartSnapshot = {
    visibleData: [],
    rsiSeries: { daily: [], weekly: [], monthly: [] },
    evaluation: null
  };
  let hoverIndex = {
    priceByDate: new Map(),
    rsiDailyByDate: new Map(),
    rsiWeeklyByDate: new Map(),
    rsiMonthlyByDate: new Map(),
    orderedDates: []
  };
  let syncingCrosshair = false;

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

  const toRsiLineData = (data) => data.map((point) => ({
    time: point.date,
    value: point.value
  }));

  const getVisibleDateRange = () => {
    const visibleData = getVisibleData();
    if (!visibleData.length) {
      return null;
    }

    return {
      start: visibleData[0].date,
      end: visibleData[visibleData.length - 1].date
    };
  };

  const formatNumber = (value) => {
    if (!Number.isFinite(value)) {
      return "—";
    }

    return value.toLocaleString("en-US", {
      minimumFractionDigits: value >= 100 ? 0 : 2,
      maximumFractionDigits: value >= 100 ? 2 : 4
    });
  };

  const timeToKey = (time) => {
    if (typeof time === "string") {
      return time;
    }

    if (time && time.year) {
      const month = String(time.month).padStart(2, "0");
      const day = String(time.day).padStart(2, "0");
      return `${time.year}-${month}-${day}`;
    }

    return null;
  };

  const findNearestDate = (timeKey) => {
    const dates = hoverIndex.orderedDates;
    if (!dates.length || !timeKey) {
      return null;
    }

    if (hoverIndex.priceByDate.has(timeKey)) {
      return timeKey;
    }

    let nearest = dates[0];
    for (let index = 0; index < dates.length; index += 1) {
      const date = dates[index];
      if (date <= timeKey) {
        nearest = date;
      }
      if (date > timeKey) {
        break;
      }
    }

    return nearest;
  };

  const formatPriceText = (candle) => {
    if (!candle) {
      return "—";
    }

    const close = candle.close ?? candle.price;
    if (currentChartMode !== "candle") {
      return formatNumber(close);
    }

    return `O ${formatNumber(candle.open ?? close)} · H ${formatNumber(candle.high ?? close)} · L ${formatNumber(candle.low ?? close)} · C ${formatNumber(close)}`;
  };

  const buildPanelSnapshot = (rsiDateKey, priceDateKey, isHover = false) => {
    const candle = priceDateKey ? hoverIndex.priceByDate.get(priceDateKey) : null;
    const rsiDaily = rsiDateKey ? hoverIndex.rsiDailyByDate.get(rsiDateKey) : null;
    const rsiWeekly = rsiDateKey ? hoverIndex.rsiWeeklyByDate.get(rsiDateKey) : null;
    const rsiMonthly = rsiDateKey ? hoverIndex.rsiMonthlyByDate.get(rsiDateKey) : null;
    const fallback = chartSnapshot.evaluation?.rsiByInterval || {};

    return {
      date: rsiDateKey || priceDateKey || "—",
      priceText: formatPriceText(candle),
      rsiByInterval: {
        daily: rsiDaily ?? fallback.daily,
        weekly: rsiWeekly ?? fallback.weekly,
        monthly: rsiMonthly ?? fallback.monthly
      },
      isHover
    };
  };

  const rebuildHoverIndex = (visibleData, rsiSeries) => {
    hoverIndex.priceByDate = new Map(visibleData.map((point) => [point.date, point]));
    hoverIndex.rsiDailyByDate = new Map(rsiSeries.daily.map((point) => [point.date, point.value]));
    hoverIndex.rsiWeeklyByDate = new Map(rsiSeries.weekly.map((point) => [point.date, point.value]));
    hoverIndex.rsiMonthlyByDate = new Map(rsiSeries.monthly.map((point) => [point.date, point.value]));
    hoverIndex.orderedDates = visibleData.map((point) => point.date);
  };

  const renderCrosshairPanel = (rsiDateKey, priceDateKey, isHover = false) => {
    PsychologyEngine.renderRsiPanel(
      document.querySelector("#rsi-panel"),
      buildPanelSnapshot(rsiDateKey, priceDateKey, isHover)
    );
  };

  const getLatestPanelKeys = () => {
    const priceDateKey = hoverIndex.orderedDates[hoverIndex.orderedDates.length - 1] || null;
    const rsiDateKey = chartSnapshot.rsiSeries.daily[chartSnapshot.rsiSeries.daily.length - 1]?.date
      || priceDateKey;

    return { rsiDateKey, priceDateKey };
  };

  const setSyncedCrosshair = (targetChart, targetSeries, time, price) => {
    if (!targetChart || !targetSeries || !Number.isFinite(price)) {
      return;
    }

    targetChart.setCrosshairPosition(price, time, targetSeries);
  };

  const handleCrosshairMove = (source, param) => {
    if (syncingCrosshair) {
      return;
    }

    if (!param.time) {
      const { rsiDateKey, priceDateKey } = getLatestPanelKeys();
      renderCrosshairPanel(rsiDateKey, priceDateKey, false);
      if (source !== "price" && chart) {
        chart.clearCrosshairPosition();
      }
      if (source !== "rsi" && rsiChart) {
        rsiChart.clearCrosshairPosition();
      }
      return;
    }

    const rsiDateKey = timeToKey(param.time);
    const priceDateKey = findNearestDate(rsiDateKey);
    if (!rsiDateKey) {
      return;
    }

    renderCrosshairPanel(rsiDateKey, priceDateKey, true);

    syncingCrosshair = true;

    const candle = priceDateKey ? hoverIndex.priceByDate.get(priceDateKey) : null;
    const close = candle?.close ?? candle?.price;
    const rsiDaily = hoverIndex.rsiDailyByDate.get(rsiDateKey);

    if (source === "price" && rsiChart && rsiDailySeries && Number.isFinite(rsiDaily)) {
      setSyncedCrosshair(rsiChart, rsiDailySeries, param.time, rsiDaily);
    }

    if (source === "rsi" && chart && Number.isFinite(close)) {
      const activeSeries = currentChartMode === "candle" ? candleSeries : lineSeries;
      setSyncedCrosshair(chart, activeSeries, param.time, close);
    }

    syncingCrosshair = false;
  };

  const bindCrosshairSync = () => {
    if (!chart || !rsiChart) {
      return;
    }

    chart.subscribeCrosshairMove((param) => handleCrosshairMove("price", param));
    rsiChart.subscribeCrosshairMove((param) => handleCrosshairMove("rsi", param));
  };

  const getVisibleRsiSeries = () => {
    const range = getVisibleDateRange();
    const multi = PsychologyEngine.buildMultiFrameRsi(getFullData());

    if (!range) {
      return multi;
    }

    return {
      daily: PsychologyEngine.filterRsiByRange(multi.daily, range.start, range.end),
      weekly: PsychologyEngine.filterRsiByRange(multi.weekly, range.start, range.end),
      monthly: PsychologyEngine.filterRsiByRange(multi.monthly, range.start, range.end)
    };
  };

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

  const addRsiGuides = (series) => {
    series.createPriceLine({
      price: 70,
      color: "rgba(244, 184, 96, 0.45)",
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      axisLabelVisible: true,
      title: ""
    });
    series.createPriceLine({
      price: 30,
      color: "rgba(96, 165, 250, 0.45)",
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      axisLabelVisible: true,
      title: ""
    });
  };

  const createRsiChart = (container) => {
    if (!window.LightweightCharts) {
      return;
    }

    rsiChart = LightweightCharts.createChart(container, {
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
        borderColor: "rgba(148, 163, 184, 0.2)",
        scaleMargins: {
          top: 0.12,
          bottom: 0.08
        }
      },
      timeScale: {
        borderColor: "rgba(148, 163, 184, 0.2)",
        timeVisible: true
      },
      handleScroll: true,
      handleScale: true
    });

    rsiDailySeries = rsiChart.addLineSeries({
      color: "#60a5fa",
      lineWidth: 2,
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: true,
      autoscaleInfoProvider: () => ({
        priceRange: { minValue: 0, maxValue: 100 }
      })
    });
    rsiWeeklySeries = rsiChart.addLineSeries({
      color: "#74d99f",
      lineWidth: 2,
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: true,
      autoscaleInfoProvider: () => ({
        priceRange: { minValue: 0, maxValue: 100 }
      })
    });
    rsiMonthlySeries = rsiChart.addLineSeries({
      color: "#f4b860",
      lineWidth: 2,
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: true,
      autoscaleInfoProvider: () => ({
        priceRange: { minValue: 0, maxValue: 100 }
      })
    });

    addRsiGuides(rsiDailySeries);

    new ResizeObserver(() => {
      rsiChart.applyOptions({
        width: container.clientWidth,
        height: container.clientHeight
      });
    }).observe(container);
  };

  const drawFallbackRsiChart = (container, rsiSeries) => {
    const width = Math.max(container.clientWidth, 320);
    const height = Math.max(container.clientHeight, 180);
    const seriesList = [
      { key: "daily", color: "#60a5fa", label: "Ngày" },
      { key: "weekly", color: "#74d99f", label: "Tuần" },
      { key: "monthly", color: "#f4b860", label: "Tháng" }
    ];

    const toPoints = (series) => series.map((point, index) => {
      const x = (index / Math.max(series.length - 1, 1)) * width;
      const y = height - (point.value / 100) * (height - 28) - 14;
      return `${x},${y}`;
    }).join(" ");

    container.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Fallback RSI chart">
        <line x1="0" y1="${height * 0.3}" x2="${width}" y2="${height * 0.3}" stroke="rgba(244, 184, 96, 0.25)" stroke-dasharray="4 4"></line>
        <line x1="0" y1="${height * 0.7}" x2="${width}" y2="${height * 0.7}" stroke="rgba(96, 165, 250, 0.25)" stroke-dasharray="4 4"></line>
        ${seriesList.map((item) => `
          <polyline points="${toPoints(rsiSeries[item.key])}" fill="none" stroke="${item.color}" stroke-width="2"></polyline>
        `).join("")}
      </svg>
    `;
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
    const rsiContainer = document.querySelector("#rsi-chart");
    const visibleData = getVisibleData();
    const evaluation = PsychologyEngine.evaluate(getFullData(), visibleData);
    const rsiSeries = getVisibleRsiSeries();

    chartSnapshot = { visibleData, rsiSeries, evaluation };
    rebuildHoverIndex(visibleData, rsiSeries);

    if (lineSeries && candleSeries) {
      lineSeries.setData(toLineData(visibleData));
      candleSeries.setData(toCandleData(visibleData));
      applyChartMode();
      chart.timeScale().fitContent();
    } else {
      drawFallbackChart(container, visibleData);
    }

    if (rsiDailySeries && rsiWeeklySeries && rsiMonthlySeries) {
      rsiDailySeries.setData(toRsiLineData(rsiSeries.daily));
      rsiWeeklySeries.setData(toRsiLineData(rsiSeries.weekly));
      rsiMonthlySeries.setData(toRsiLineData(rsiSeries.monthly));
      rsiChart.timeScale().fitContent();
    } else {
      drawFallbackRsiChart(rsiContainer, rsiSeries);
    }

    const { rsiDateKey, priceDateKey } = getLatestPanelKeys();
    renderCrosshairPanel(rsiDateKey, priceDateKey, false);
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
    createRsiChart(document.querySelector("#rsi-chart"));
    bindCrosshairSync();
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
