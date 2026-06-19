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
    "5Y": 365 * 5,
    "10Y": Number.MAX_SAFE_INTEGER
  };

  const isElliottPsychologyRange = () => PsychologyEngine.supportsElliottWeeklyPsychology(currentRange);

  let chart;
  let lineSeries;
  let candleSeries;
  let rsiChart;
  let rsiDailySeries;
  let rsiWeeklySeries;
  let rsiMonthlySeries;
  let psychologyBackgroundSeries = [];
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
    psychologyByDate: new Map(),
    orderedDates: []
  };
  let syncingCrosshair = false;
  let psychologyTimeline = [];
  let psychologyAnalysisKey = null;
  let isPsychologyAnalyzing = false;

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

  const getAnalysisKey = (visibleData) => {
    if (!visibleData.length) {
      return null;
    }

    return [
      currentAsset,
      currentRange,
      currentInterval,
      visibleData[0].date,
      visibleData[visibleData.length - 1].date
    ].join("|");
  };

  const updatePsychologyStatus = (message, isBusy = false) => {
    const status = document.querySelector("#psychology-status");
    const button = document.querySelector("#analyze-psychology");
    const allowed = isElliottPsychologyRange();

    if (status) {
      status.textContent = message;
      status.classList.toggle("busy", isBusy);
    }

    if (button) {
      button.disabled = isBusy || !allowed;
      button.textContent = isBusy
        ? "Đang phân tích sóng tuần..."
        : "Phân tích Elliott (khung tuần)";
    }
  };

  const invalidatePsychologyAnalysis = (message) => {
    psychologyTimeline = [];
    psychologyAnalysisKey = null;
    const defaultMessage = isElliottPsychologyRange()
      ? "Bấm phân tích để tô vùng tâm lý theo sóng Elliott tuần"
      : "Chọn phạm vi 5Y hoặc 10Y để phân tích sóng Elliott";
    updatePsychologyStatus(message || defaultMessage, false);
  };

  const applyPsychologyResult = (visibleData, timeline) => {
    psychologyTimeline = timeline;
    psychologyAnalysisKey = getAnalysisKey(visibleData);
    chartSnapshot.psychologyTimeline = timeline;
    rebuildHoverIndex(visibleData, chartSnapshot.rsiSeries, timeline);

    if (chart) {
      mountPriceSeries(visibleData, timeline);
      chart.timeScale().fitContent();
    } else {
      drawFallbackChart(document.querySelector("#chart"), visibleData, timeline);
    }

    PsychologyEngine.renderPsychologyLegend(document.querySelector("#psychology-legend"));
    updatePsychologyStatus(`Đã phân tích ${timeline.length} điểm · sóng Elliott tuần`, false);

    const { rsiDateKey, priceDateKey } = getLatestPanelKeys();
    renderCrosshairPanel(rsiDateKey, priceDateKey, false);
  };

  const runPsychologyAnalysis = async () => {
    if (isPsychologyAnalyzing) {
      return;
    }

    const visibleData = getVisibleData();
    if (!visibleData.length) {
      updatePsychologyStatus("Không có dữ liệu trong vùng đang xem");
      return;
    }

    if (!isElliottPsychologyRange()) {
      updatePsychologyStatus("Chỉ hỗ trợ phân tích Elliott cho phạm vi 5Y và 10Y");
      return;
    }

    isPsychologyAnalyzing = true;
    updatePsychologyStatus("Đang gộp nến tuần và đếm sóng Elliott...", true);

    try {
      const timeline = await PsychologyEngine.buildElliottWeeklyTimelineAsync(
        getFullData(),
        visibleData,
        (progress) => {
          updatePsychologyStatus(`Đang phân tích sóng tuần... ${Math.round(progress * 100)}%`, true);
        }
      );

      applyPsychologyResult(visibleData, timeline);
    } catch (error) {
      console.error(error);
      updatePsychologyStatus("Phân tích thất bại — thử lại");
    } finally {
      isPsychologyAnalyzing = false;
    }
  };

  const bindPsychologyControls = () => {
    const button = document.querySelector("#analyze-psychology");
    if (!button) {
      return;
    }

    button.addEventListener("click", () => {
      runPsychologyAnalysis();
    });
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
    const psychology = rsiDateKey ? hoverIndex.psychologyByDate.get(rsiDateKey) : null;
    const fallback = chartSnapshot.evaluation?.rsiByInterval || {};
    const latestPsychology = chartSnapshot.psychologyTimeline?.at(-1);

    return {
      date: rsiDateKey || priceDateKey || "—",
      priceText: formatPriceText(candle),
      psychologyZone: psychology?.zone || latestPsychology?.zone || chartSnapshot.evaluation?.possibleZone,
      psychologyLabel: psychology?.label || latestPsychology?.label,
      psychologyConfidence: psychology?.confidence ?? latestPsychology?.confidence ?? chartSnapshot.evaluation?.confidence,
      elliottLabel: psychology?.elliottLabel
        || latestPsychology?.elliottLabel
        || chartSnapshot.evaluation?.features?.elliott?.label
        || null,
      rsiByInterval: {
        daily: rsiDaily ?? fallback.daily,
        weekly: rsiWeekly ?? fallback.weekly,
        monthly: rsiMonthly ?? fallback.monthly
      },
      isHover
    };
  };

  const rebuildHoverIndex = (visibleData, rsiSeries, psychologyTimeline) => {
    hoverIndex.priceByDate = new Map(visibleData.map((point) => [point.date, point]));
    hoverIndex.rsiDailyByDate = new Map(rsiSeries.daily.map((point) => [point.date, point.value]));
    hoverIndex.rsiWeeklyByDate = new Map(rsiSeries.weekly.map((point) => [point.date, point.value]));
    hoverIndex.rsiMonthlyByDate = new Map(rsiSeries.monthly.map((point) => [point.date, point.value]));
    hoverIndex.psychologyByDate = new Map(psychologyTimeline.map((point) => [point.date, point]));
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

  const hexToRgba = (hex, alpha) => {
    const normalized = hex.replace("#", "");
    const value = Number.parseInt(normalized, 16);
    const red = (value >> 16) & 255;
    const green = (value >> 8) & 255;
    const blue = value & 255;
    return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
  };

  const getPriceBounds = (visibleData) => {
    const prices = visibleData.map((point) => point.close ?? point.price);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const padding = Math.max((maxPrice - minPrice) * 0.04, maxPrice * 0.002);

    return {
      top: maxPrice + padding,
      base: minPrice - padding
    };
  };

  const clearPsychologyBackgrounds = () => {
    psychologyBackgroundSeries.forEach((series) => chart.removeSeries(series));
    psychologyBackgroundSeries = [];
  };

  const removePriceSeries = () => {
    clearPsychologyBackgrounds();

    if (lineSeries) {
      chart.removeSeries(lineSeries);
      lineSeries = null;
    }

    if (candleSeries) {
      chart.removeSeries(candleSeries);
      candleSeries = null;
    }
  };

  const renderPsychologyBackgrounds = (segments, bounds) => {
    segments.forEach((segment) => {
      const start = segment.points[0].date;
      const end = segment.points[segment.points.length - 1].date;
      const fill = hexToRgba(segment.color, PsychologyEngine.zoneBackgroundAlpha);

      const series = chart.addAreaSeries({
        baseValue: bounds.base,
        topColor: fill,
        bottomColor: fill,
        lineColor: "transparent",
        lineWidth: 0,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false
      });

      series.setData([
        { time: start, value: bounds.top },
        { time: end, value: bounds.top }
      ]);

      psychologyBackgroundSeries.push(series);
    });
  };

  const mountPriceSeries = (visibleData, timeline = []) => {
    const segments = timeline.length
      ? PsychologyEngine.buildPsychologySegments(visibleData, timeline)
      : [];
    const bounds = getPriceBounds(visibleData);

    removePriceSeries();

    if (segments.length) {
      renderPsychologyBackgrounds(segments, bounds);
    }

    lineSeries = chart.addLineSeries({
      color: "#e2e8f0",
      lineWidth: 2,
      priceLineColor: "rgba(226, 232, 240, 0.35)"
    });

    candleSeries = chart.addCandlestickSeries({
      upColor: "#74d99f",
      downColor: "#fb7185",
      borderVisible: false,
      wickUpColor: "#74d99f",
      wickDownColor: "#fb7185"
    });

    lineSeries.setData(toLineData(visibleData));
    candleSeries.setData(toCandleData(visibleData));
    applyChartMode();
  };

  const drawFallbackChart = (container, visibleData, psychologyTimeline) => {
    const prices = visibleData.map((point) => point.close ?? point.price);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const width = Math.max(container.clientWidth, 320);
    const height = Math.max(container.clientHeight, 280);
    const segments = PsychologyEngine.buildPsychologySegments(visibleData, psychologyTimeline);
    const chartTop = 18;
    const chartHeight = height - 36;

    const priceToY = (price) => chartTop + chartHeight - ((price - min) / Math.max(max - min, 1)) * chartHeight;
    const indexToX = (index, total) => (index / Math.max(total - 1, 1)) * width;

    const zoneRects = segments.map((segment) => {
      const startIndex = visibleData.findIndex((point) => point.date === segment.points[0].date);
      const endIndex = visibleData.findIndex((point) => point.date === segment.points[segment.points.length - 1].date);
      const x = indexToX(startIndex, visibleData.length);
      const rectWidth = Math.max(indexToX(endIndex, visibleData.length) - x, 1);

      return `
        <rect
          x="${x}"
          y="${chartTop}"
          width="${rectWidth}"
          height="${chartHeight}"
          fill="${hexToRgba(segment.color, PsychologyEngine.zoneBackgroundAlpha)}"
        ></rect>
      `;
    }).join("");

    const points = visibleData.map((point, index) => {
      const x = indexToX(index, visibleData.length);
      const y = priceToY(point.close ?? point.price);
      return `${x},${y}`;
    }).join(" ");

    container.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Fallback price chart with psychology zones">
        ${zoneRects}
        <polyline points="${points}" fill="none" stroke="#e2e8f0" stroke-width="2"></polyline>
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

    chartSnapshot = {
      visibleData,
      rsiSeries,
      evaluation,
      psychologyTimeline
    };
    rebuildHoverIndex(visibleData, rsiSeries, psychologyTimeline);

    if (chart) {
      mountPriceSeries(visibleData, psychologyTimeline);
      chart.timeScale().fitContent();
    } else {
      drawFallbackChart(container, visibleData, psychologyTimeline);
    }

    if (!psychologyTimeline.length) {
      const legend = document.querySelector("#psychology-legend");
      if (legend) {
        legend.innerHTML = "";
      }
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
    onEvaluation(evaluation);

    const nextKey = getAnalysisKey(visibleData);
    if (psychologyAnalysisKey && nextKey !== psychologyAnalysisKey) {
      psychologyTimeline = [];
      psychologyAnalysisKey = null;
    }

    if (!psychologyTimeline.length) {
      updatePsychologyStatus(
        isElliottPsychologyRange()
          ? "Bấm phân tích để tô vùng tâm lý theo sóng Elliott tuần"
          : "Chọn phạm vi 5Y hoặc 10Y để phân tích sóng Elliott",
        false
      );
    } else {
      updatePsychologyStatus(`Đã phân tích ${psychologyTimeline.length} điểm · sóng Elliott tuần`, false);
    }
  };

  const setAsset = (asset) => {
    currentAsset = asset;
    invalidatePsychologyAnalysis();
    render();
  };

  const setRange = (range) => {
    currentRange = range;
    invalidatePsychologyAnalysis();
    render();
  };

  const setInterval = (interval) => {
    currentInterval = interval;
    invalidatePsychologyAnalysis();
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
    bindPsychologyControls();
    invalidatePsychologyAnalysis();
    render();
  };

  return {
    init,
    setAsset,
    setRange,
    setInterval,
    setChartMode,
    runPsychologyAnalysis,
    getCurrentData: getVisibleData
  };
})();
