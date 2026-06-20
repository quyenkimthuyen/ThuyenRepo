/* Chart module: loads sample market JSON and renders Lightweight Charts when available. */
const MarketChart = (() => {
  const assetFiles = {
    bitcoin: "data/bitcoin.json",
    ethereum: "data/ethereum.json",
    gold: "data/gold.json",
    sp500: "data/sp500.json"
  };

  const assetLabels = {
    bitcoin: "Bitcoin",
    ethereum: "Ethereum",
    gold: "Vàng",
    sp500: "S&P 500"
  };

  const getVisibleData = () => RangeUtils.buildVisibleSeries(
    getFullData(),
    currentRange,
    currentInterval,
    PsychologyEngine.aggregateSeries
  );

  const sanitizeVisibleData = (data) => RangeUtils.sanitizeSeries(
    data.filter((point) => Number.isFinite(point.close ?? point.price))
  );

  let chart;
  let lineSeries;
  let candleSeries;
  let rsiChart;
  let signalChart;
  let rsiTwoDaySeries;
  let rsiWeeklySeries;
  let rsiMonthlySeries;
  let rsiGuideSeries;
  let signalScoreSeries;
  let signalGuideSeries;
  let psychologyBackgroundSeries = [];
  let elliottWaveSeries = null;
  let volumeHistogramSeries = null;
  let atrUpperSeries = null;
  let atrLowerSeries = null;
  let currentElliottMarkers = [];
  let currentAsset = "bitcoin";
  let currentRange = "1M";
  let currentInterval = "1D";
  let currentChartMode = "line";
  let marketData = {};
  let onMarketUpdate = () => {};
  let chartSnapshot = {
    visibleData: [],
    rsiSeries: { twoDay: [], weekly: [], monthly: [] },
    signalSeries: [],
    marketSnapshot: null,
    psychologyTimeline: []
  };
  let hoverIndex = {
    priceByDate: new Map(),
    rsiTwoDayByDate: new Map(),
    rsiWeeklyByDate: new Map(),
    rsiMonthlyByDate: new Map(),
    signalByDate: new Map(),
    signalGradeByDate: new Map(),
    psychologyByDate: new Map(),
    orderedDates: []
  };
  let psychologyCaches = {};
  let isPsychologyAnalyzing = false;
  let isUpdatingPrices = false;
  let syncingCrosshair = false;
  let syncingTimeScale = false;
  let pendingFitFrame = null;
  const rsiVisibility = {
    twoDay: true,
    weekly: true,
    monthly: true
  };
  let elliottOverlayVisible = false;
  let simLastOverlayDate = null;
  let simLastSignalRenderAt = 0;
  let signalChartBindingsAttached = false;

  const isSimulationPlayback = () => typeof ProSimulation !== "undefined"
    && AppMode.isSimulation()
    && ProSimulation.isActive()
    && ProSimulation.isPlaying();

  const generateFallbackData = (asset) => {
    const start = new Date("2026-01-01T00:00:00");
    const profiles = {
      bitcoin: { base: 100000, wave: 3400, long: 5200, drift: 155, open: 420, high: 680, low: 720 },
      ethereum: { base: 3500, wave: 120, long: 180, drift: 5.5, open: 14, high: 22, low: 24 },
      gold: { base: 3300, wave: 65, long: 90, drift: 3.2, open: 8, high: 12, low: 14 },
      sp500: { base: 5500, wave: 45, long: 70, drift: 2.8, open: 6, high: 10, low: 11 }
    };
    const profile = profiles[asset] || profiles.bitcoin;
    const data = [];

    for (let index = 0; index < 3650; index += 1) {
      const date = new Date(start);
      date.setDate(start.getDate() + index);
      const wave = Math.sin(index / 8) * profile.wave;
      const longerWave = Math.cos(index / 21) * profile.long;
      const drift = index * profile.drift;
      const close = Math.round((profile.base + drift + wave + longerWave) * 100) / 100;
      const open = Math.round((close - profile.open) * 100) / 100;
      const high = Math.round((close + profile.high) * 100) / 100;
      const low = Math.round((close - profile.low) * 100) / 100;

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
      const data = await response.json();
      const array = Array.isArray(data) ? data : (data.prices || data.data || []);
      return MarketDataService.applyPatches(asset, array);
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
    psychologyCaches = Object.fromEntries(
      Object.keys(assetFiles).map((asset) => {
        const cache = PsychologyEngine.loadPsychologyCache(asset);
        return [
          asset,
          PsychologyEngine.isPsychologyCacheValid(cache, marketData[asset] || [])
            ? cache
            : null
        ];
      })
    );
  };

  const getActivePsychologyCache = () => {
    if (AppMode.isSimulation() && typeof ProSimulation !== "undefined") {
      return ProSimulation.getPsychologyCache();
    }

    return psychologyCaches[currentAsset] || null;
  };

  const buildSimulationPsychologyCache = (cursorDate) => PsychologyEngine.buildWalkForwardPsychologyCache(
    marketData[currentAsset] || [],
    cursorDate,
    {
      enrichCache: (cache, clipped) => ProAnalysis.enrichPsychologyCache(cache, clipped),
      applyConfidenceGate: true,
      minConfidence: PsychologyEngine.SIM_MIN_CONFIDENCE
    }
  );

  const getElliottOverlayCache = () => {
    const cache = getActivePsychologyCache();
    if (!cache) {
      return null;
    }

    return AppMode.usesProAnalysis()
      ? ProAnalysis.enrichPsychologyCache(cache, getFullData())
      : cache;
  };

  const getProjectedPsychologyTimeline = (visibleData) => {
    const cache = getActivePsychologyCache();
    return cache ? PsychologyEngine.projectPsychologyToSeries(cache, visibleData) : [];
  };

  const getFullData = () => {
    const raw = marketData[currentAsset] || [];
    const cutoff = typeof ProSimulation !== "undefined" ? ProSimulation.getCutoffDate() : null;

    if (!cutoff) {
      return raw;
    }

    return raw.filter((point) => point.date <= cutoff);
  };

  const toRsiLineData = (data) => data.map((point) => ({
    time: point.date,
    value: point.value
  }));

  const toLineData = (data) => data.map((point) => ({
    time: point.date,
    value: point.close ?? point.price
  }));

  const clearChartCrosshairs = () => {
    if (chart) {
      chart.clearCrosshairPosition();
    }

    if (rsiChart) {
      rsiChart.clearCrosshairPosition();
    }

    if (signalChart) {
      signalChart.clearCrosshairPosition();
    }
  };

  const safeSetCrosshairPosition = (targetChart, value, time, series) => {
    if (!targetChart || !series || !Number.isFinite(value) || !time) {
      return;
    }

    try {
      targetChart.setCrosshairPosition(value, time, series);
    } catch (error) {
      targetChart.clearCrosshairPosition();
    }
  };

  const scheduleFitChartsToVisibleData = () => {
    if (!chart) {
      return;
    }

    if (pendingFitFrame) {
      cancelAnimationFrame(pendingFitFrame);
    }

    pendingFitFrame = requestAnimationFrame(() => {
      pendingFitFrame = null;
      fitChartsToVisibleData();
    });
  };

  const getSyncedSubCharts = () => [rsiChart, signalChart].filter(Boolean);

  const resetSyncedTimeScales = () => {
    if (!chart) {
      return;
    }

    syncingTimeScale = true;
    try {
      chart.timeScale().resetTimeScale();
      getSyncedSubCharts().forEach((targetChart) => {
        targetChart.timeScale().resetTimeScale();
      });
    } finally {
      syncingTimeScale = false;
    }
  };
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

  const updatePsychologyStatus = (message, isBusy = false) => {
    const status = document.querySelector("#psychology-status");
    const button = document.querySelector("#analyze-psychology");

    if (status) {
      status.textContent = message;
      status.classList.toggle("busy", isBusy);
    }

    if (button) {
      button.disabled = isBusy;
      button.textContent = isBusy ? "Đang phân tích..." : "Phân tích 10 năm";
      button.hidden = AppMode.isSimulation();
    }
  };

  const formatCacheStatus = (cache) => {
    if (AppMode.isSimulation() && typeof ProSimulation !== "undefined" && ProSimulation.isPrewarming?.()) {
      const status = ProSimulation.getStatus();
      return `Giả lập · đang chuẩn bị ${status.prewarmProgress}/${status.prewarmTotal} tuần...`;
    }

    if (!cache) {
      if (AppMode.isSimulation()) {
        return "Giả lập · chọn khoảng thời gian và Áp dụng — pre-run phân tích theo tuần";
      }

      return "Chưa có bản đồ — bấm Phân tích 10 năm để xây dựng từ nến tuần";
    }

    const analyzedAt = PsychologyEngine.formatAnalyzedAt(cache.analyzedAt);
    if (AppMode.isSimulation()) {
      return `Giả lập · ${cache.weekCount} tuần · ${cache.regionCount} giai đoạn · cập nhật ${cache.rangeEnd}`;
    }

    return `Đã lưu · ${cache.weekCount} tuần · ${cache.regionCount} giai đoạn${analyzedAt ? ` · ${analyzedAt}` : ""}`;
  };

  const syncPsychologyStatus = () => {
    updatePsychologyStatus(formatCacheStatus(getActivePsychologyCache()), false);
  };

  const runPsychologyAnalysis = async () => {
    if (AppMode.isSimulation()) {
      return;
    }
    if (isPsychologyAnalyzing) {
      return;
    }

    const fullData = getFullData();
    if (!fullData.length) {
      updatePsychologyStatus("Không có dữ liệu để phân tích");
      return;
    }

    isPsychologyAnalyzing = true;
    updatePsychologyStatus("Đang phân tích 10 năm dữ liệu tuần...", true);

    try {
      const cache = await PsychologyEngine.buildPsychologyCacheAsync(
        fullData,
        (progress) => {
          updatePsychologyStatus(`Đang phân tích 10 năm... ${Math.round(progress * 100)}%`, true);
        }
      );

      if (!cache) {
        updatePsychologyStatus("Không đủ dữ liệu (cần tối thiểu ~1 tháng)");
        return;
      }

      psychologyCaches[currentAsset] = cache;
      PsychologyEngine.savePsychologyCache(currentAsset, cache);
      render();
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
    const rsiTwoDay = rsiDateKey ? hoverIndex.rsiTwoDayByDate.get(rsiDateKey) : null;
    const rsiWeekly = rsiDateKey ? hoverIndex.rsiWeeklyByDate.get(rsiDateKey) : null;
    const rsiMonthly = rsiDateKey ? hoverIndex.rsiMonthlyByDate.get(rsiDateKey) : null;
    const psychology = rsiDateKey ? hoverIndex.psychologyByDate.get(rsiDateKey) : null;
    const fallback = chartSnapshot.marketSnapshot || {};
    const latestPsychology = chartSnapshot.psychologyTimeline?.at(-1);

    return {
      date: rsiDateKey || priceDateKey || "—",
      priceText: formatPriceText(candle),
      psychologyZone: psychology?.zone || latestPsychology?.zone || fallback.zone || null,
      psychologyLabel: psychology?.label || latestPsychology?.label || fallback.label || null,
      psychologyConfidence: psychology?.confidence ?? latestPsychology?.confidence ?? fallback.confidence ?? null,
      elliottLabel: psychology?.elliottLabel
        || latestPsychology?.elliottLabel
        || fallback.elliottLabel
        || null,
      rsiByInterval: {
        twoDay: rsiTwoDay ?? fallback.rsiByInterval?.twoDay,
        weekly: rsiWeekly ?? fallback.rsiByInterval?.weekly,
        monthly: rsiMonthly ?? fallback.rsiByInterval?.monthly
      },
      rsiIntervalLabels: fallback.rsiIntervalLabels,
      proSignalScore: AppMode.usesProAnalysis()
        ? (rsiDateKey ? hoverIndex.signalByDate.get(rsiDateKey) : fallback.proSignalScore)
        : null,
      proSignalGrade: AppMode.usesProAnalysis()
        ? (rsiDateKey ? hoverIndex.signalGradeByDate.get(rsiDateKey) : fallback.proSignalGrade)
        : null,
      isHover
    };
  };

  const rebuildHoverIndex = (visibleData, rsiSeries, psychologyTimeline, signalSeries = []) => {
    hoverIndex.priceByDate = new Map(visibleData.map((point) => [point.date, point]));
    hoverIndex.rsiTwoDayByDate = new Map(rsiSeries.twoDay.map((point) => [point.date, point.value]));
    hoverIndex.rsiWeeklyByDate = new Map(rsiSeries.weekly.map((point) => [point.date, point.value]));
    hoverIndex.rsiMonthlyByDate = new Map(rsiSeries.monthly.map((point) => [point.date, point.value]));
    hoverIndex.signalByDate = new Map(signalSeries.map((point) => [point.date, point.value]));
    hoverIndex.signalGradeByDate = new Map(signalSeries.map((point) => [point.date, point.grade]));
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
    const simDate = typeof ProSimulation !== "undefined" && ProSimulation.isActive()
      ? ProSimulation.getCutoffDate()
      : null;
    const priceDateKey = simDate
      || hoverIndex.orderedDates[hoverIndex.orderedDates.length - 1]
      || null;
    const rsiDateKey = simDate
      || chartSnapshot.rsiSeries.twoDay[chartSnapshot.rsiSeries.twoDay.length - 1]?.date
      || priceDateKey;

    return { rsiDateKey, priceDateKey };
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
      if (source !== "signal" && signalChart) {
        signalChart.clearCrosshairPosition();
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
    const rsiTarget = pickRsiCrosshairValue(rsiDateKey);
    const signalValue = hoverIndex.signalByDate.get(rsiDateKey);

    if (source === "price" && rsiChart && rsiTarget.series && Number.isFinite(rsiTarget.value)) {
      safeSetCrosshairPosition(rsiChart, rsiTarget.value, param.time, rsiTarget.series);
    }

    if (source === "price" && signalChart && signalScoreSeries && Number.isFinite(signalValue)) {
      safeSetCrosshairPosition(signalChart, signalValue, param.time, signalScoreSeries);
    }

    if (source === "rsi" && chart && Number.isFinite(close)) {
      const activeSeries = currentChartMode === "candle" ? candleSeries : lineSeries;
      safeSetCrosshairPosition(chart, close, param.time, activeSeries);
    }

    if (source === "rsi" && signalChart && signalScoreSeries && Number.isFinite(signalValue)) {
      safeSetCrosshairPosition(signalChart, signalValue, param.time, signalScoreSeries);
    }

    if (source === "signal" && chart && Number.isFinite(close)) {
      const activeSeries = currentChartMode === "candle" ? candleSeries : lineSeries;
      safeSetCrosshairPosition(chart, close, param.time, activeSeries);
    }

    if (source === "signal" && rsiChart && rsiTarget.series && Number.isFinite(rsiTarget.value)) {
      safeSetCrosshairPosition(rsiChart, rsiTarget.value, param.time, rsiTarget.series);
    }

    syncingCrosshair = false;
  };

  const bindCrosshairSync = () => {
    if (chart) {
      chart.subscribeCrosshairMove((param) => handleCrosshairMove("price", param));
    }

    if (rsiChart) {
      rsiChart.subscribeCrosshairMove((param) => handleCrosshairMove("rsi", param));
    }

    if (signalChart) {
      signalChart.subscribeCrosshairMove((param) => handleCrosshairMove("signal", param));
    }
  };

  const getVisibleRsiSeries = () => {
    const visibleData = getVisibleData();
    const fullData = getFullData();

    if (AppMode.usesProAnalysis()) {
      return ProAnalysis.alignRsiForPro(fullData, visibleData);
    }

    const multi = PsychologyEngine.buildMultiFrameRsi(fullData);
    return PsychologyEngine.alignRsiToVisible(visibleData, multi);
  };

  const getVisibleSignalSeries = () => {
    const visibleData = getVisibleData();
    const cache = getActivePsychologyCache();

    if (!AppMode.usesProAnalysis() || !cache?.regions?.length || !visibleData.length) {
      return [];
    }

    return ProAnalysis.buildSignalScoreSeries(
      cache,
      getFullData(),
      visibleData,
      psychologyCaches,
      marketData,
      currentAsset
    );
  };

  const clearSignalChart = () => {
    if (signalScoreSeries) {
      signalScoreSeries.setData([]);
    }
    if (signalGuideSeries) {
      signalGuideSeries.setData([]);
    }

    const signalContainer = document.querySelector("#signal-chart");
    if (signalContainer && !signalChart) {
      signalContainer.innerHTML = "";
    }

    syncSignalChartVisibility(false);
  };
  const syncSignalChartVisibility = (hasSeries) => {
    const block = document.querySelector("#signal-chart-block");
    const stack = document.querySelector(".chart-stack");
    const show = AppMode.usesProAnalysis() && hasSeries;

    if (block) {
      block.hidden = !show;
    }

    if (stack) {
      stack.classList.toggle("has-signal", show);
    }

    if (show) {
      scheduleSignalChartLayout();
    }
  };

  const syncChartTimeScales = () => {
    if (!chart || syncingTimeScale) {
      return;
    }

    const range = chart.timeScale().getVisibleLogicalRange();
    if (!range) {
      return;
    }

    syncingTimeScale = true;
    try {
      getSyncedSubCharts().forEach((targetChart) => {
        targetChart.timeScale().setVisibleLogicalRange(range);
      });
    } finally {
      syncingTimeScale = false;
    }
  };

  const fitChartsToVisibleData = () => {
    if (!chart) {
      return;
    }

    syncingTimeScale = true;
    try {
      chart.timeScale().fitContent();
      syncChartTimeScales();
    } finally {
      syncingTimeScale = false;
    }
  };

  const pickRsiCrosshairValue = (dateKey) => {
    if (rsiVisibility.twoDay) {
      const value = hoverIndex.rsiTwoDayByDate.get(dateKey);
      if (Number.isFinite(value)) {
        return { series: rsiTwoDaySeries, value };
      }
    }

    if (rsiVisibility.weekly) {
      const value = hoverIndex.rsiWeeklyByDate.get(dateKey);
      if (Number.isFinite(value)) {
        return { series: rsiWeeklySeries, value };
      }
    }

    if (rsiVisibility.monthly) {
      const value = hoverIndex.rsiMonthlyByDate.get(dateKey);
      if (Number.isFinite(value)) {
        return { series: rsiMonthlySeries, value };
      }
    }

    return { series: null, value: null };
  };

  const bindChartTimeScale = (targetChart) => {
    if (!chart || !targetChart) {
      return;
    }

    targetChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (syncingTimeScale || !range) {
        return;
      }

      syncingTimeScale = true;
      try {
        if (targetChart !== chart) {
          chart.timeScale().setVisibleLogicalRange(range);
        }
        getSyncedSubCharts().forEach((peer) => {
          if (peer !== targetChart) {
            peer.timeScale().setVisibleLogicalRange(range);
          }
        });
      } finally {
        syncingTimeScale = false;
      }
    });
  };

  const bindTimeScaleSync = () => {
    bindChartTimeScale(chart);
    bindChartTimeScale(rsiChart);
    bindChartTimeScale(signalChart);
  };

  const attachSignalChartBindings = () => {
    if (!signalChart || signalChartBindingsAttached) {
      return;
    }

    bindChartTimeScale(signalChart);
    signalChart.subscribeCrosshairMove((param) => handleCrosshairMove("signal", param));
    signalChartBindingsAttached = true;
  };

  const resizeSignalChart = () => {
    const container = document.querySelector("#signal-chart");
    if (!signalChart || !container) {
      return false;
    }

    const width = container.clientWidth;
    const height = container.clientHeight;
    if (width < 1 || height < 1) {
      return false;
    }

    signalChart.applyOptions({ width, height });
    return true;
  };

  const scheduleSignalChartLayout = () => {
    const attempt = (retriesLeft = 3) => {
      if (resizeSignalChart()) {
        if (!syncingTimeScale) {
          syncChartTimeScales();
        }
        return;
      }

      if (retriesLeft > 0 && typeof requestAnimationFrame === "function") {
        requestAnimationFrame(() => attempt(retriesLeft - 1));
      }
    };

    if (typeof requestAnimationFrame === "function") {
      requestAnimationFrame(() => attempt());
    } else {
      attempt();
    }
  };

  const ensureSignalChart = () => {
    const container = document.querySelector("#signal-chart");
    if (!container || !window.LightweightCharts) {
      return false;
    }

    if (!signalChart) {
      createSignalChart(container);
      attachSignalChartBindings();
    }

    return Boolean(signalChart);
  };

  const updatePriceStatus = (message, isBusy = false) => {
    const status = document.querySelector("#price-update-status");
    if (!status) {
      return;
    }

    status.textContent = message;
    status.classList.toggle("busy", isBusy);
  };

  const runPriceUpdate = async () => {
    if (isUpdatingPrices) {
      return;
    }

    const currentSeries = getFullData();
    if (!currentSeries.length) {
      updatePriceStatus("Không có dữ liệu để cập nhật");
      return;
    }

    isUpdatingPrices = true;
    updatePriceStatus("Đang tải giá mới nhất...", true);

    const button = document.querySelector("#update-prices");
    if (button) {
      button.disabled = true;
    }

    try {
      const result = await MarketDataService.updateAsset(currentAsset, currentSeries);
      marketData[currentAsset] = result.series;

      const cache = psychologyCaches[currentAsset];
      if (cache && !PsychologyEngine.isPsychologyCacheValid(cache, result.series)) {
        psychologyCaches[currentAsset] = null;
        PsychologyEngine.clearPsychologyCache(currentAsset);
      }

      render();

      const addedText = result.added > 0 ? ` · +${result.added} ngày mới` : " · cập nhật nến gần nhất";
      updatePriceStatus(`Giá đến ${result.updatedTo}${addedText}`, false);
    } catch (error) {
      console.error(error);
      updatePriceStatus("Không tải được giá — kiểm tra mạng hoặc thử lại", false);
    } finally {
      isUpdatingPrices = false;
      if (button) {
        button.disabled = false;
      }
    }
  };

  const bindPriceUpdateControls = () => {
    const button = document.querySelector("#update-prices");
    if (!button) {
      return;
    }

    button.addEventListener("click", () => {
      runPriceUpdate();
    });
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
    if (!visibleData.length) {
      return { top: 1, base: 0 };
    }

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

  const clearAtrBands = () => {
    if (atrUpperSeries && chart) {
      chart.removeSeries(atrUpperSeries);
      atrUpperSeries = null;
    }

    if (atrLowerSeries && chart) {
      chart.removeSeries(atrLowerSeries);
      atrLowerSeries = null;
    }
  };

  const renderAtrBands = (visibleData) => {
    clearAtrBands();

    if (!AppMode.isPro() || !chart || !visibleData.length) {
      return;
    }

    const bands = ProAnalysis.buildAtrBands(visibleData);
    if (!bands.upper.length) {
      return;
    }

    atrUpperSeries = chart.addLineSeries({
      color: "rgba(91, 156, 245, 0.28)",
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dotted,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false
    });
    atrLowerSeries = chart.addLineSeries({
      color: "rgba(251, 113, 133, 0.28)",
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dotted,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false
    });
    atrUpperSeries.setData(bands.upper);
    atrLowerSeries.setData(bands.lower);
  };

  const clearVolumeHistogram = () => {
    if (volumeHistogramSeries && chart) {
      chart.removeSeries(volumeHistogramSeries);
      volumeHistogramSeries = null;
    }
  };

  const renderVolumeProxy = (visibleData) => {
    clearVolumeHistogram();

    if (!AppMode.isPro() || !chart || !visibleData.length) {
      return;
    }

    volumeHistogramSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "volume-proxy"
    });

    chart.priceScale("volume-proxy").applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 }
    });

    volumeHistogramSeries.setData(ProAnalysis.buildVolumeProxySeries(visibleData));
  };

  const clearElliottOverlay = () => {
    if (elliottWaveSeries && chart) {
      chart.removeSeries(elliottWaveSeries);
      elliottWaveSeries = null;
    }

    currentElliottMarkers = [];

    if (lineSeries) {
      lineSeries.setMarkers([]);
    }

    if (candleSeries) {
      candleSeries.setMarkers([]);
    }
  };

  const applyElliottMarkers = () => {
    if (!currentElliottMarkers.length) {
      return;
    }

    const activeSeries = currentChartMode === "candle" ? candleSeries : lineSeries;
    const inactiveSeries = currentChartMode === "candle" ? lineSeries : candleSeries;

    if (inactiveSeries) {
      inactiveSeries.setMarkers([]);
    }

    if (activeSeries) {
      activeSeries.setMarkers(currentElliottMarkers);
    }
  };

  const renderElliottOverlay = (visibleData) => {
    clearElliottOverlay();

    if (!elliottOverlayVisible || !chart || !visibleData.length) {
      return;
    }

    const cache = getElliottOverlayCache();
    if (!cache) {
      return;
    }

    const overlay = ElliottEngine.buildVisibleWaveOverlay(cache, visibleData, {
      validatedOnly: AppMode.usesProAnalysis()
    });
    if (!overlay?.points?.length) {
      return;
    }

    elliottWaveSeries = chart.addLineSeries({
      color: "#f0b45c",
      lineWidth: 2,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false
    });
    elliottWaveSeries.setData(overlay.points);
    currentElliottMarkers = overlay.markers || [];
    applyElliottMarkers();
  };

  const formatElliottChipLabel = (elliottLabel) => {
    if (!elliottLabel) {
      return "Elliott";
    }

    return elliottLabel
      .replace(/^Sóng\s+/, "")
      .replace(/\s+tăng$/, " ↑")
      .replace(/\s+giảm$/, " ↓");
  };

  const syncElliottChip = (marketSnapshot = chartSnapshot.marketSnapshot) => {
    const chip = document.querySelector("#elliott-chip");
    if (!chip) {
      return;
    }

    const hasCache = Boolean(getActivePsychologyCache());
    chip.disabled = !hasCache;
    chip.classList.toggle("active", elliottOverlayVisible && hasCache);
    chip.setAttribute("aria-pressed", String(elliottOverlayVisible && hasCache));

    if (!hasCache) {
      chip.textContent = "Elliott";
      chip.classList.remove("has-wave");
      chip.title = "Bật/tắt sóng Elliott · cần Phân tích 10 năm";
      return;
    }

    const label = marketSnapshot?.elliottLabel;
    chip.textContent = formatElliottChipLabel(label);
    chip.classList.toggle("has-wave", Boolean(label));
    chip.title = elliottOverlayVisible
      ? `Đang hiển thị sóng Elliott${label ? ` · ${label}` : ""}`
      : `Bật sóng Elliott trên biểu đồ${label ? ` · hiện tại: ${label}` : ""}`;
  };

  const ensurePriceSeries = () => {
    if (!chart || lineSeries) {
      return;
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
  };

  const updatePriceSeriesData = (visibleData) => {
    ensurePriceSeries();

    if (!lineSeries || !candleSeries || !visibleData.length) {
      return;
    }

    const clean = sanitizeVisibleData(visibleData);
    lineSeries.setData(toLineData(clean));
    candleSeries.setData(toCandleData(clean));
    applyChartMode();
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
    const clean = sanitizeVisibleData(visibleData);

    if (!clean.length) {
      clearPsychologyBackgrounds();
      clearElliottOverlay();
      clearVolumeHistogram();
      clearAtrBands();
      return;
    }

    const segments = timeline.length
      ? PsychologyEngine.buildPsychologySegments(clean, timeline)
      : [];
    const bounds = getPriceBounds(clean);

    clearPsychologyBackgrounds();
    updatePriceSeriesData(clean);

    if (segments.length && chart) {
      renderPsychologyBackgrounds(segments, bounds);
    }

    renderElliottOverlay(clean);
    renderVolumeProxy(clean);
    renderAtrBands(clean);
  };

  const updateSimulationChart = (visibleData, psychologyTimeline) => {
    if (!chart || !visibleData.length) {
      return;
    }

    const clean = sanitizeVisibleData(visibleData);
    updatePriceSeriesData(clean);

    const lastDate = clean[clean.length - 1]?.date;
    if (!lastDate || lastDate === simLastOverlayDate) {
      return;
    }

    simLastOverlayDate = lastDate;
    const segments = psychologyTimeline.length
      ? PsychologyEngine.buildPsychologySegments(clean, psychologyTimeline)
      : [];

    clearPsychologyBackgrounds();
    if (segments.length) {
      renderPsychologyBackgrounds(segments, getPriceBounds(clean));
    }

    renderElliottOverlay(clean);
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

    const dateToIndex = new Map(visibleData.map((point, index) => [point.date, index]));
    const cache = getElliottOverlayCache();
    const elliottOverlay = elliottOverlayVisible && cache
      ? ElliottEngine.buildVisibleWaveOverlay(cache, visibleData, {
        validatedOnly: AppMode.usesProAnalysis()
      })
      : null;

    const elliottZigzag = elliottOverlay?.points?.length
      ? elliottOverlay.points.map((point) => {
        const index = dateToIndex.get(point.time)
          ?? visibleData.findIndex((row) => row.date >= point.time);
        const safeIndex = index >= 0 ? index : visibleData.length - 1;
        return `${indexToX(safeIndex, visibleData.length)},${priceToY(point.value)}`;
      }).join(" ")
      : "";

    const elliottLabels = elliottOverlay?.markers?.map((marker) => {
      const index = dateToIndex.get(marker.time) ?? 0;
      const price = elliottOverlay.pivots.find((pivot) => pivot.date === marker.time)?.price ?? min;
      const x = indexToX(index, visibleData.length);
      const y = priceToY(price) + (marker.position === "belowBar" ? 14 : -10);

      return `
        <text x="${x}" y="${y}" fill="#f0b45c" font-size="11" font-weight="700" text-anchor="middle">${marker.text}</text>
      `;
    }).join("") || "";

    container.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Fallback price chart with psychology zones">
        ${zoneRects}
        ${elliottZigzag ? `<polyline points="${elliottZigzag}" fill="none" stroke="#f0b45c" stroke-width="2" stroke-dasharray="6 4"></polyline>` : ""}
        <polyline points="${points}" fill="none" stroke="#e2e8f0" stroke-width="2"></polyline>
        ${elliottLabels}
        <text x="16" y="30" fill="#8ea0b7" font-size="13">Lightweight Charts unavailable. Showing static fallback.</text>
      </svg>
    `;
  };

  const applyRsiVisibility = () => {
    if (!rsiTwoDaySeries) {
      return;
    }

    rsiTwoDaySeries.applyOptions({ visible: rsiVisibility.twoDay });
    rsiWeeklySeries.applyOptions({ visible: rsiVisibility.weekly });
    rsiMonthlySeries.applyOptions({ visible: rsiVisibility.monthly });
  };

  const syncRsiToggleButtons = () => {
    document.querySelectorAll(".rsi-toggle").forEach((button) => {
      const key = button.dataset.rsi;
      const isOn = Boolean(rsiVisibility[key]);
      button.classList.toggle("active", isOn);
      button.setAttribute("aria-pressed", String(isOn));
    });
  };

  const ensureRsiSeries = () => {
    if (!rsiChart || rsiTwoDaySeries) {
      return;
    }

    const rsiSeriesOptions = {
      lineWidth: 2,
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: true,
      autoscaleInfoProvider: () => ({
        priceRange: { minValue: 0, maxValue: 100 }
      })
    };

    rsiTwoDaySeries = rsiChart.addLineSeries({
      ...rsiSeriesOptions,
      color: "#5b9cf5"
    });
    rsiWeeklySeries = rsiChart.addLineSeries({
      ...rsiSeriesOptions,
      color: "#3dd68c"
    });
    rsiMonthlySeries = rsiChart.addLineSeries({
      ...rsiSeriesOptions,
      color: "#f0b45c"
    });

    rsiGuideSeries = rsiChart.addLineSeries({
      color: "transparent",
      lineWidth: 0,
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      autoscaleInfoProvider: () => ({
        priceRange: { minValue: 0, maxValue: 100 }
      })
    });

    rsiGuideSeries.createPriceLine({
      price: 70,
      color: "rgba(255, 159, 90, 0.6)",
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      axisLabelVisible: true,
      title: "70"
    });
    rsiGuideSeries.createPriceLine({
      price: 30,
      color: "rgba(91, 156, 245, 0.6)",
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      axisLabelVisible: true,
      title: "30"
    });

    applyRsiVisibility();
  };

  const updateRsiGuideData = (rsiSeries) => {
    if (!rsiGuideSeries) {
      return;
    }

    const anchor = rsiSeries.twoDay.length
      ? rsiSeries.twoDay
      : rsiSeries.weekly.length
        ? rsiSeries.weekly
        : rsiSeries.monthly;

    rsiGuideSeries.setData(anchor.map((point) => ({
      time: point.date,
      value: 50
    })));
  };

  const updateRsiSeriesData = (rsiSeries) => {
    ensureRsiSeries();

    if (!rsiTwoDaySeries) {
      return;
    }

    rsiTwoDaySeries.setData(toRsiLineData(rsiSeries.twoDay));
    rsiWeeklySeries.setData(toRsiLineData(rsiSeries.weekly));
    rsiMonthlySeries.setData(toRsiLineData(rsiSeries.monthly));
    updateRsiGuideData(rsiSeries);
    applyRsiVisibility();
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
        vertLines: { color: "rgba(148, 163, 184, 0.06)" },
        horzLines: { color: "rgba(148, 163, 184, 0.06)" }
      },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal
      },
      rightPriceScale: {
        borderColor: "rgba(148, 163, 184, 0.2)",
        minimumWidth: 72
      },
      timeScale: {
        borderColor: "rgba(148, 163, 184, 0.2)",
        timeVisible: false
      },
      handleScroll: true,
      handleScale: true
    });

    ensureRsiSeries();

    new ResizeObserver(() => {
      rsiChart.applyOptions({
        width: container.clientWidth,
        height: container.clientHeight
      });
    }).observe(container);
  };

  const drawFallbackRsiChart = (container, rsiSeries) => {
    const width = Math.max(container.clientWidth, 320);
    const height = Math.max(container.clientHeight, 140);
    const seriesList = [
      { key: "twoDay", color: "#5b9cf5", label: "2D" },
      { key: "weekly", color: "#3dd68c", label: "Tuần" },
      { key: "monthly", color: "#f0b45c", label: "Tháng" }
    ].filter((item) => rsiVisibility[item.key]);

    const toPoints = (series) => series.map((point, index) => {
      const x = (index / Math.max(series.length - 1, 1)) * width;
      const y = height - (point.value / 100) * (height - 24) - 12;
      return `${x},${y}`;
    }).join(" ");

    container.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Biểu đồ RSI">
        <line x1="0" y1="${height * 0.3}" x2="${width}" y2="${height * 0.3}" stroke="rgba(255, 159, 90, 0.55)" stroke-dasharray="5 4"></line>
        <line x1="0" y1="${height * 0.7}" x2="${width}" y2="${height * 0.7}" stroke="rgba(91, 156, 245, 0.55)" stroke-dasharray="5 4"></line>
        <text x="6" y="${height * 0.3 - 4}" fill="rgba(255, 159, 90, 0.8)" font-size="11">70</text>
        <text x="6" y="${height * 0.7 - 4}" fill="rgba(91, 156, 245, 0.8)" font-size="11">30</text>
        ${seriesList.map((item) => `
          <polyline points="${toPoints(rsiSeries[item.key])}" fill="none" stroke="${item.color}" stroke-width="2"></polyline>
        `).join("")}
      </svg>
    `;
  };

  const ensureSignalSeries = () => {
    if (!signalChart || signalScoreSeries) {
      return;
    }

    const seriesOptions = {
      lineWidth: 2,
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: true,
      autoscaleInfoProvider: () => ({
        priceRange: { minValue: 0, maxValue: 100 }
      })
    };

    signalScoreSeries = signalChart.addLineSeries({
      ...seriesOptions,
      color: "#f0b45c"
    });

    signalGuideSeries = signalChart.addLineSeries({
      color: "transparent",
      lineWidth: 0,
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      autoscaleInfoProvider: () => ({
        priceRange: { minValue: 0, maxValue: 100 }
      })
    });

    [
      { price: 80, color: "rgba(61, 214, 140, 0.55)", title: "A" },
      { price: 65, color: "rgba(91, 156, 245, 0.55)", title: "B" },
      { price: 50, color: "rgba(255, 159, 90, 0.55)", title: "C" }
    ].forEach((line) => {
      signalGuideSeries.createPriceLine({
        price: line.price,
        color: line.color,
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Dashed,
        axisLabelVisible: true,
        title: line.title
      });
    });
  };

  const updateSignalGuideData = (signalSeries) => {
    if (!signalGuideSeries || !signalSeries.length) {
      return;
    }

    signalGuideSeries.setData(signalSeries.map((point) => ({
      time: point.date,
      value: 50
    })));
  };

  const updateSignalSeriesData = (signalSeries) => {
    if (!signalSeries.length) {
      return;
    }

    if (!ensureSignalChart()) {
      return;
    }

    ensureSignalSeries();
    signalScoreSeries.setData(toRsiLineData(signalSeries));
    updateSignalGuideData(signalSeries);
    scheduleSignalChartLayout();
  };

  const createSignalChart = (container) => {
    if (!window.LightweightCharts) {
      return;
    }

    signalChart = LightweightCharts.createChart(container, {
      layout: {
        background: { color: "#08131e" },
        textColor: "#8ea0b7"
      },
      grid: {
        vertLines: { color: "rgba(148, 163, 184, 0.06)" },
        horzLines: { color: "rgba(148, 163, 184, 0.06)" }
      },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal
      },
      rightPriceScale: {
        borderColor: "rgba(148, 163, 184, 0.2)",
        minimumWidth: 72
      },
      timeScale: {
        borderColor: "rgba(148, 163, 184, 0.2)",
        timeVisible: false
      },
      handleScroll: true,
      handleScale: true
    });

    ensureSignalSeries();

    new ResizeObserver(() => {
      signalChart.applyOptions({
        width: container.clientWidth,
        height: container.clientHeight
      });
    }).observe(container);
  };

  const drawFallbackSignalChart = (container, signalSeries) => {
    const width = Math.max(container.clientWidth, 320);
    const height = Math.max(container.clientHeight, 120);
    const toPoints = signalSeries.map((point, index) => {
      const x = (index / Math.max(signalSeries.length - 1, 1)) * width;
      const y = height - (point.value / 100) * (height - 24) - 12;
      return `${x},${y}`;
    }).join(" ");

    container.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Biểu đồ Pro Signal Score">
        <line x1="0" y1="${height * 0.2}" x2="${width}" y2="${height * 0.2}" stroke="rgba(61, 214, 140, 0.55)" stroke-dasharray="5 4"></line>
        <line x1="0" y1="${height * 0.35}" x2="${width}" y2="${height * 0.35}" stroke="rgba(91, 156, 245, 0.55)" stroke-dasharray="5 4"></line>
        <line x1="0" y1="${height * 0.5}" x2="${width}" y2="${height * 0.5}" stroke="rgba(255, 159, 90, 0.55)" stroke-dasharray="5 4"></line>
        <text x="6" y="${height * 0.2 - 4}" fill="rgba(61, 214, 140, 0.8)" font-size="11">80 A</text>
        <text x="6" y="${height * 0.35 - 4}" fill="rgba(91, 156, 245, 0.8)" font-size="11">65 B</text>
        <text x="6" y="${height * 0.5 - 4}" fill="rgba(255, 159, 90, 0.8)" font-size="11">50 C</text>
        <polyline points="${toPoints}" fill="none" stroke="#f0b45c" stroke-width="2"></polyline>
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
    applyElliottMarkers();
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
        borderColor: "rgba(148, 163, 184, 0.2)",
        minimumWidth: 72
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

  const render = () => {
    const container = document.querySelector("#chart");
    const visibleData = sanitizeVisibleData(getVisibleData());
    const simPlaying = isSimulationPlayback();
    const psychologyCache = getActivePsychologyCache();
    const fullData = getFullData();
    const psychologyTimeline = getProjectedPsychologyTimeline(visibleData);
    let marketSnapshot;
    let rsiSeries;
    let signalSeries;

    if (simPlaying) {
      rsiSeries = getVisibleRsiSeries();
      const now = Date.now();
      if (now - simLastSignalRenderAt >= 600) {
        signalSeries = getVisibleSignalSeries();
        simLastSignalRenderAt = now;
      } else {
        signalSeries = chartSnapshot.signalSeries || [];
      }

      marketSnapshot = {
        ...(chartSnapshot.marketSnapshot || {}),
        simulation: ProSimulation.getStatus(),
        appMode: AppMode.getMode()
      };
    } else {
      simLastOverlayDate = null;
      simLastSignalRenderAt = 0;

      marketSnapshot = PsychologyEngine.buildMarketSnapshot(
        psychologyCache,
        fullData,
        visibleData
      );
      const basicAdvice = InvestmentAdvisor.buildRecommendation(
        psychologyCache,
        fullData,
        marketSnapshot
      );
      const crossAsset = psychologyCache && !AppMode.isSimulation()
        ? ProAnalysis.buildCrossAssetMatrix(psychologyCaches, marketData, currentAsset)
        : null;
      const proAdvice = psychologyCache
        ? ProAnalysis.buildProRecommendation(psychologyCache, fullData, marketSnapshot, visibleData, crossAsset)
        : { hasAdvice: false };
      const modeComparison = AppMode.isSimulation()
        ? null
        : ProAnalysis.buildModeComparison(basicAdvice, proAdvice);
      rsiSeries = getVisibleRsiSeries();
      signalSeries = getVisibleSignalSeries();

      if (AppMode.usesProAnalysis() && psychologyCache) {
        marketSnapshot = ProAnalysis.enhanceMarketSnapshot(
          marketSnapshot,
          psychologyCache,
          fullData,
          visibleData,
          crossAsset,
          proAdvice
        );
        const lastSignal = signalSeries.at(-1);
        marketSnapshot.proSignalScore = lastSignal?.value ?? null;
        marketSnapshot.proSignalGrade = lastSignal?.grade ?? null;
      }

      marketSnapshot.investment = AppMode.isPro()
        ? proAdvice
        : AppMode.isBasic()
          ? basicAdvice
          : { hasAdvice: false };
      marketSnapshot.modeComparison = modeComparison;
      marketSnapshot.appMode = AppMode.getMode();
      marketSnapshot.crossAsset = crossAsset;
      marketSnapshot.basicInvestment = basicAdvice;
      marketSnapshot.proInvestment = proAdvice;
      marketSnapshot.simulation = typeof ProSimulation !== "undefined"
        ? ProSimulation.getStatus()
        : { active: false };
    }

    chartSnapshot = {
      visibleData,
      rsiSeries,
      signalSeries,
      marketSnapshot,
      psychologyTimeline
    };
    rebuildHoverIndex(visibleData, rsiSeries, psychologyTimeline, signalSeries);
    clearChartCrosshairs();

    if (chart && visibleData.length) {
      if (simPlaying) {
        updateSimulationChart(visibleData, psychologyTimeline);
      } else {
        mountPriceSeries(visibleData, psychologyTimeline);
        resetSyncedTimeScales();
        scheduleFitChartsToVisibleData();
      }
    } else if (!chart) {
      drawFallbackChart(container, visibleData, psychologyTimeline);
    }

    const rsiContainer = document.querySelector("#rsi-chart");
    if (rsiChart && visibleData.length) {
      updateRsiSeriesData(rsiSeries);
    } else if (rsiContainer) {
      drawFallbackRsiChart(rsiContainer, rsiSeries);
    }

    const signalContainer = document.querySelector("#signal-chart");
    if (!AppMode.usesProAnalysis()) {
      clearSignalChart();
    } else if (signalSeries.length > 0) {
      syncSignalChartVisibility(true);
      if (window.LightweightCharts) {
        updateSignalSeriesData(signalSeries);
      } else if (signalContainer) {
        drawFallbackSignalChart(signalContainer, signalSeries);
      }
    } else {
      syncSignalChartVisibility(false);
      if (signalContainer && !signalChart) {
        signalContainer.innerHTML = "";
      }
    }

    const { rsiDateKey, priceDateKey } = getLatestPanelKeys();
    renderCrosshairPanel(rsiDateKey, priceDateKey, false);

    if (!psychologyTimeline.length) {
      const legend = document.querySelector("#psychology-legend");
      if (legend) {
        legend.innerHTML = "";
      }
    } else {
      PsychologyEngine.renderPsychologyLegend(document.querySelector("#psychology-legend"));
    }

    if (!simPlaying) {
      onMarketUpdate(marketSnapshot);
    }

    syncPsychologyStatus();
    syncElliottChip(marketSnapshot);
  };

  const setAsset = (asset) => {
    currentAsset = asset;
    if (typeof ProSimulation !== "undefined") {
      ProSimulation.onContextChange();
    } else {
      render();
    }
  };

  const setRange = (range) => {
    if (!RangeUtils.isValidRangeKey(range)) {
      return;
    }

    currentRange = range;
    if (typeof ProSimulation !== "undefined" && ProSimulation.isActive()) {
      ProSimulation.rebuildTimeline(true);
    } else {
      render();
    }
  };

  const setInterval = (interval) => {
    currentInterval = interval;
    if (typeof ProSimulation !== "undefined") {
      ProSimulation.onContextChange();
    } else {
      render();
    }
  };

  const setChartMode = (mode) => {
    currentChartMode = mode;
    render();
  };

  const setRsiLineVisible = (key, visible) => {
    if (!Object.prototype.hasOwnProperty.call(rsiVisibility, key)) {
      return;
    }

    rsiVisibility[key] = visible;

    const enabledCount = Object.values(rsiVisibility).filter(Boolean).length;
    if (enabledCount === 0) {
      rsiVisibility[key] = true;
    }

    applyRsiVisibility();
    syncRsiToggleButtons();

    const rsiContainer = document.querySelector("#rsi-chart");
    if (!rsiChart && rsiContainer) {
      drawFallbackRsiChart(rsiContainer, chartSnapshot.rsiSeries);
    }
  };

  const toggleRsiLine = (key) => {
    setRsiLineVisible(key, !rsiVisibility[key]);
  };

  const toggleElliottOverlay = () => {
    if (!getActivePsychologyCache()) {
      return;
    }

    elliottOverlayVisible = !elliottOverlayVisible;
    render();
  };

  const bindElliottControls = () => {
    const chip = document.querySelector("#elliott-chip");
    if (!chip) {
      return;
    }

    chip.addEventListener("click", () => {
      toggleElliottOverlay();
    });
  };

  const init = async (marketUpdateHandler) => {
    onMarketUpdate = marketUpdateHandler;
    await loadAllData();
    createChart(document.querySelector("#chart"));
    createRsiChart(document.querySelector("#rsi-chart"));
    bindTimeScaleSync();
    bindCrosshairSync();
    bindPsychologyControls();
    bindPriceUpdateControls();
    bindElliottControls();
    AppMode.onChange(() => {
      if (typeof ProSimulation !== "undefined") {
        ProSimulation.onModeChange();
      }
      render();
    });
    if (typeof ProSimulation !== "undefined") {
      ProSimulation.init({
        getContext: () => ({
          fullData: marketData[currentAsset] || [],
          interval: currentInterval,
          hasCache: Boolean(psychologyCaches[currentAsset])
        }),
        refreshPsychology: (cursorDate) => buildSimulationPsychologyCache(cursorDate),
        getBaselineCache: () => {
          const raw = marketData[currentAsset] || [];
          const saved = psychologyCaches[currentAsset];
          if (saved?.regions?.length) {
            return saved;
          }

          return PsychologyEngine.buildPsychologyCache(raw);
        },
        onFrame: () => {
          render();
        }
      });
    }
    syncRsiToggleButtons();
    updatePriceStatus("");
    render();
  };

  return {
    init,
    setAsset,
    setRange,
    setInterval,
    setChartMode,
    toggleRsiLine,
    setRsiLineVisible,
    toggleElliottOverlay,
    runPsychologyAnalysis,
    runPriceUpdate,
    getCurrentData: getVisibleData
  };
})();
