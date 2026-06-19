/* Psychology engine: historical price features + indicator rules for market psychology zones. */
const PsychologyEngine = (() => {
  const cycle = [
    "Disbelief",
    "Hope",
    "Optimism",
    "Belief",
    "Thrill",
    "Euphoria",
    "Complacency",
    "Anxiety",
    "Denial",
    "Panic",
    "Capitulation",
    "Anger",
    "Depression"
  ];

  const RSI_PERIOD = 14;
  const MA_FAST = 20;
  const MA_MID = 50;
  const MA_SLOW = 200;
  const SWING_LOOKBACK = 120;
  const MIN_HISTORY = 60;

  const zoneColors = {
    Hope: "#3b82f6",
    Optimism: "#10b981",
    Belief: "#059669",
    Thrill: "#84cc16",
    Euphoria: "#f59e0b",
    Complacency: "#eab308",
    Anxiety: "#f97316",
    Denial: "#d946ef",
    Panic: "#ef4444",
    Capitulation: "#b91c1c",
    Anger: "#7c3aed",
    Depression: "#334155",
    Disbelief: "#64748b",
    Observing: "#475569"
  };

  const zoneBackgroundAlpha = 0.18;

  const zoneLabelsVi = {
    Hope: "Hy vọng",
    Optimism: "Lạc quan",
    Belief: "Niềm tin",
    Thrill: "Hưng phấn",
    Euphoria: "Hưng phấn cực độ",
    Complacency: "Chủ quan",
    Anxiety: "Lo âu",
    Denial: "Phủ nhận",
    Panic: "Hoảng loạn",
    Capitulation: "Bỏ cuộc",
    Anger: "Phẫn nộ",
    Depression: "Trầm cảm",
    Disbelief: "Nghi ngờ",
    Observing: "Quan sát"
  };

  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

  const normalizeCandle = (point) => ({
    date: point.date,
    open: point.open ?? point.price,
    high: point.high ?? point.price,
    low: point.low ?? point.price,
    close: point.close ?? point.price,
    price: point.close ?? point.price
  });

  const getWeekStart = (dateStr) => {
    const date = new Date(`${dateStr}T12:00:00`);
    const day = date.getUTCDay();
    const diff = day === 0 ? 6 : day - 1;
    date.setUTCDate(date.getUTCDate() - diff);
    return date.toISOString().slice(0, 10);
  };

  const aggregateSeries = (series, interval) => {
    if (!series || !series.length) {
      return [];
    }

    const normalized = series.map(normalizeCandle);
    if (interval === "1D") {
      return normalized;
    }

    const buckets = new Map();

    normalized.forEach((candle) => {
      const key = interval === "1W" ? getWeekStart(candle.date) : candle.date.slice(0, 7);
      const existing = buckets.get(key);

      if (!existing) {
        buckets.set(key, { ...candle });
        return;
      }

      existing.high = Math.max(existing.high, candle.high);
      existing.low = Math.min(existing.low, candle.low);
      existing.close = candle.close;
      existing.price = candle.close;
      existing.date = key.length === 7 ? `${key}-01` : key;
    });

    return Array.from(buckets.values()).sort((left, right) => left.date.localeCompare(right.date));
  };

  const getClose = (point) => point.close ?? point.price;

  const sma = (series, period, endIndex = series.length - 1) => {
    if (endIndex + 1 < period) {
      return null;
    }

    const start = endIndex + 1 - period;
    let total = 0;

    for (let index = start; index <= endIndex; index += 1) {
      total += getClose(series[index]);
    }

    return total / period;
  };

  const windowExtreme = (series, endIndex, period, field) => {
    const start = Math.max(0, endIndex + 1 - period);
    let value = field === "high"
      ? -Infinity
      : Infinity;

    for (let index = start; index <= endIndex; index += 1) {
      const pointValue = field === "high"
        ? series[index].high ?? getClose(series[index])
        : series[index].low ?? getClose(series[index]);

      value = field === "high"
        ? Math.max(value, pointValue)
        : Math.min(value, pointValue);
    }

    return value;
  };

  const roc = (series, period, endIndex = series.length - 1) => {
    if (endIndex < period) {
      return 0;
    }

    const last = getClose(series[endIndex]);
    const previous = getClose(series[endIndex - period]);
    return previous === 0 ? 0 : ((last - previous) / previous) * 100;
  };

  const averageAbsReturn = (series, period, endIndex = series.length - 1) => {
    if (endIndex < 1) {
      return 0;
    }

    const start = Math.max(1, endIndex + 1 - period);
    let total = 0;
    let count = 0;

    for (let index = start; index <= endIndex; index += 1) {
      const previous = getClose(series[index - 1]);
      if (previous === 0) {
        continue;
      }

      total += Math.abs((getClose(series[index]) - previous) / previous) * 100;
      count += 1;
    }

    return count ? total / count : 0;
  };

  const buildRsiSeries = (series, period = RSI_PERIOD) => {
    if (!series || series.length < period + 1) {
      return [];
    }

    const results = [];
    let avgGain = 0;
    let avgLoss = 0;

    for (let index = 1; index <= period; index += 1) {
      const change = getClose(series[index]) - getClose(series[index - 1]);
      if (change >= 0) {
        avgGain += change;
      } else {
        avgLoss += Math.abs(change);
      }
    }

    avgGain /= period;
    avgLoss /= period;

    const pushRsi = (index) => {
      const rsi = avgLoss === 0
        ? 100
        : Math.round(100 - 100 / (1 + avgGain / avgLoss));
      results.push({ date: series[index].date, value: rsi });
    };

    pushRsi(period);

    for (let index = period + 1; index < series.length; index += 1) {
      const change = getClose(series[index]) - getClose(series[index - 1]);
      const gain = change >= 0 ? change : 0;
      const loss = change < 0 ? Math.abs(change) : 0;
      avgGain = ((avgGain * (period - 1)) + gain) / period;
      avgLoss = ((avgLoss * (period - 1)) + loss) / period;
      pushRsi(index);
    }

    return results;
  };

  const alignHigherTimeframeRsi = (dailySeries, higherRsiSeries, getPeriodDate) => {
    const byPeriodDate = new Map(higherRsiSeries.map((point) => [point.date, point.value]));
    let current = null;

    return dailySeries.map((day) => {
      const periodDate = getPeriodDate(day.date);
      if (byPeriodDate.has(periodDate)) {
        current = byPeriodDate.get(periodDate);
      }

      return current === null ? null : { date: day.date, value: current };
    }).filter(Boolean);
  };

  const buildMultiFrameRsi = (fullSeries) => {
    const daily = aggregateSeries(fullSeries, "1D");
    const weekly = aggregateSeries(fullSeries, "1W");
    const monthly = aggregateSeries(fullSeries, "1M");

    const dailyRsi = buildRsiSeries(daily);
    const weeklyRsi = buildRsiSeries(weekly);
    const monthlyRsi = buildRsiSeries(monthly);

    return {
      daily: dailyRsi,
      weekly: alignHigherTimeframeRsi(daily, weeklyRsi, getWeekStart),
      monthly: alignHigherTimeframeRsi(daily, monthlyRsi, (date) => `${date.slice(0, 7)}-01`)
    };
  };

  const calculateRsi = (series, period = RSI_PERIOD) => {
    const built = buildRsiSeries(series, period);
    return built.length ? built[built.length - 1].value : 50;
  };

  const filterRsiByRange = (series, startDate, endDate) => series.filter(
    (point) => point.date >= startDate && point.date <= endDate
  );

  const calculateTrend = (series) => {
    if (!series || series.length < 2) {
      return 0;
    }

    const first = getClose(series[0]);
    const last = getClose(series[series.length - 1]);
    return first === 0 ? 0 : ((last - first) / first) * 100;
  };

  const computeFeatures = (dailySeries, endIndex = dailySeries.length - 1) => {
    if (!dailySeries.length || endIndex < 0) {
      return null;
    }

    const close = getClose(dailySeries[endIndex]);
    const swingHigh = windowExtreme(dailySeries, endIndex, SWING_LOOKBACK, "high");
    const swingLow = windowExtreme(dailySeries, endIndex, SWING_LOOKBACK, "low");
    const drawdown = swingHigh > 0 ? ((close - swingHigh) / swingHigh) * 100 : 0;
    const recovery = swingLow > 0 ? ((close - swingLow) / swingLow) * 100 : 0;
    const history = dailySeries.slice(0, endIndex + 1);
    const weekly = aggregateSeries(history, "1W");
    const monthly = aggregateSeries(history, "1M");

    const ma20 = sma(dailySeries, MA_FAST, endIndex);
    const ma50 = sma(dailySeries, MA_MID, endIndex);
    const ma200 = sma(dailySeries, MA_SLOW, endIndex);
    const ma50Prev = sma(dailySeries, MA_MID, Math.max(0, endIndex - 10));

    return {
      close,
      drawdown,
      recovery,
      trend20: roc(dailySeries, 20, endIndex),
      trend60: roc(dailySeries, 60, endIndex),
      volatility20: averageAbsReturn(dailySeries, 20, endIndex),
      volatility60: averageAbsReturn(dailySeries, 60, endIndex),
      rsiDaily: calculateRsi(history),
      rsiWeekly: calculateRsi(weekly),
      rsiMonthly: calculateRsi(monthly),
      priceVsMa20: ma20 ? ((close - ma20) / ma20) * 100 : 0,
      priceVsMa50: ma50 ? ((close - ma50) / ma50) * 100 : 0,
      priceVsMa200: ma200 ? ((close - ma200) / ma200) * 100 : 0,
      ma50Rising: ma50 !== null && ma50Prev !== null ? ma50 > ma50Prev : false,
      aboveMa50: ma50 !== null ? close > ma50 : false,
      aboveMa200: ma200 !== null ? close > ma200 : false,
      goldenStructure: ma50 !== null && ma200 !== null ? ma50 > ma200 : false,
      elliott: ElliottEngine.analyzeAt(
        dailySeries,
        ElliottEngine.buildSwingCache(
          history,
          clamp(averageAbsReturn(dailySeries, 60, endIndex) * 1.6, 3, 12)
        ),
        endIndex
      )
    };
  };

  const scorePsychologyZones = (features) => {
    if (!features) {
      return { scores: { Observing: 100 }, rsiBlend: 50, priceVsMa50: 0, priceVsMa200: 0 };
    }

    const {
      drawdown,
      recovery,
      trend20,
      trend60,
      volatility20,
      volatility60,
      rsiDaily,
      rsiWeekly,
      rsiMonthly,
      priceVsMa50,
      priceVsMa200,
      ma50Rising,
      aboveMa50,
      aboveMa200,
      goldenStructure
    } = features;

    const rsiBlend = Math.round((rsiDaily + rsiWeekly + rsiMonthly) / 3);
    const volRatio = volatility60 > 0 ? volatility20 / volatility60 : 1;
    const nearHigh = drawdown > -6;
    const moderatePullback = drawdown <= -6 && drawdown > -18;
    const deepPullback = drawdown <= -18;
    const farFromLow = recovery > 25;
    const risingFromLow = recovery > 12 && drawdown < -8;

    const scores = {
      Depression: 8
        + (drawdown < -30 ? 24 : 0)
        + (rsiDaily < 28 ? 18 : 0)
        + (trend60 < -18 ? 16 : 0)
        + (recovery < 12 ? 10 : 0),

      Capitulation: 6
        + (drawdown < -24 ? 20 : 0)
        + (rsiDaily < 24 ? 20 : 0)
        + (trend20 < -10 ? 16 : 0)
        + (volRatio > 1.25 ? 12 : 0),

      Anger: 8
        + (drawdown < -20 && drawdown >= -34 ? 16 : 0)
        + (rsiDaily >= 24 && rsiDaily <= 38 ? 12 : 0)
        + (trend60 < -8 ? 12 : 0)
        + (trend20 > 0 && trend60 < 0 ? 10 : 0),

      Panic: 8
        + (deepPullback ? 18 : 0)
        + (rsiDaily < 32 ? 16 : 0)
        + (trend20 < -8 ? 18 : 0)
        + (volRatio > 1.35 ? 14 : 0),

      Denial: 10
        + (drawdown <= -10 && drawdown > -24 ? 16 : 0)
        + (rsiDaily >= 35 && rsiDaily <= 52 ? 10 : 0)
        + (trend20 < 0 && trend60 > 0 ? 14 : 0)
        + (aboveMa200 ? 8 : 0),

      Anxiety: 12
        + (moderatePullback ? 18 : 0)
        + (rsiDaily >= 38 && rsiDaily <= 55 ? 8 : 0)
        + (trend20 < -3 ? 12 : 0)
        + (volRatio > 1.1 ? 8 : 0),

      Disbelief: 12
        + (risingFromLow ? 16 : 0)
        + (rsiDaily >= 34 && rsiDaily <= 48 ? 12 : 0)
        + (trend20 > 2 && trend60 < 0 ? 12 : 0)
        + (!aboveMa200 ? 8 : 0),

      Hope: 14
        + (drawdown > -18 && drawdown <= -6 ? 12 : 0)
        + (rsiDaily >= 40 && rsiDaily <= 56 ? 12 : 0)
        + (trend20 > 3 ? 14 : 0)
        + (ma50Rising ? 8 : 0),

      Optimism: 16
        + (drawdown > -12 ? 10 : 0)
        + (rsiDaily >= 48 && rsiDaily <= 62 ? 12 : 0)
        + (aboveMa50 ? 12 : 0)
        + (trend20 > 0 && trend60 > 0 ? 12 : 0),

      Belief: 18
        + (drawdown > -10 ? 8 : 0)
        + (rsiDaily >= 52 && rsiDaily <= 68 ? 10 : 0)
        + (aboveMa50 && aboveMa200 ? 14 : 0)
        + (goldenStructure ? 10 : 0)
        + (priceVsMa50 > 2 ? 8 : 0),

      Thrill: 12
        + (nearHigh ? 10 : 0)
        + (rsiDaily >= 64 && rsiDaily <= 78 ? 16 : 0)
        + (trend20 > 8 ? 14 : 0)
        + (volRatio > 1.05 ? 6 : 0),

      Euphoria: 10
        + (drawdown > -4 ? 12 : 0)
        + (rsiDaily > 72 || rsiWeekly > 68 ? 18 : 0)
        + (trend20 > 12 ? 14 : 0)
        + (farFromLow ? 8 : 0),

      Complacency: 12
        + (drawdown > -8 && drawdown <= -1 ? 12 : 0)
        + (rsiDaily >= 55 && rsiDaily <= 70 ? 10 : 0)
        + (Math.abs(trend20) < 4 ? 14 : 0)
        + (volatility20 < volatility60 * 0.85 ? 12 : 0)
        + (aboveMa50 ? 8 : 0)
    };

    const elliott = features.elliott;
    if (elliott?.psychology?.zone) {
      const elliottZone = elliott.psychology.zone;
      scores[elliottZone] = (scores[elliottZone] || 0) + elliott.psychology.weight;
      if (elliott.confidence >= 22) {
        scores[elliottZone] += 10;
      }
    }

    return { scores, rsiBlend, priceVsMa50, priceVsMa200, elliott };
  };

  const normalizeScores = (scores) => {
    const total = Object.values(scores).reduce((sum, value) => sum + value, 0) || 1;
    return Object.fromEntries(
      Object.entries(scores)
        .map(([key, value]) => [key, Math.round((value / total) * 100)])
        .sort((left, right) => right[1] - left[1])
    );
  };

  const classifyFromFeatures = (features) => {
    if (!features) {
      return {
        possibleZone: "Observing",
        confidence: 0,
        probabilities: { Observing: 100 },
        features: null,
        signals: []
      };
    }

    const scored = scorePsychologyZones(features);
    const probabilities = normalizeScores(scored.scores);
    const ranked = Object.entries(probabilities);
    const topZone = ranked[0] || ["Observing", 0];
    const runnerUp = ranked[1]?.[1] || 0;
    let confidence = clamp(topZone[1] + Math.max(0, topZone[1] - runnerUp) * 0.35, 0, 100);

    if (features.elliott?.psychology?.zone === topZone[0]) {
      confidence = clamp(confidence + Math.round((features.elliott.confidence || 0) * 0.2), 0, 100);
    }

    return {
      possibleZone: topZone[0],
      confidence: Math.round(confidence),
      probabilities,
      features,
      signals: buildSignals(features, topZone[0])
    };
  };

  const prepareDailyContext = (daily) => {
    const length = daily.length;
    const highs = daily.map((point) => point.high ?? getClose(point));
    const lows = daily.map((point) => point.low ?? getClose(point));
    const rsiDailyByDate = new Map(buildRsiSeries(daily).map((point) => [point.date, point.value]));
    const weekly = aggregateSeries(daily, "1W");
    const monthly = aggregateSeries(daily, "1M");
    const rsiWeeklyByDate = new Map(
      alignHigherTimeframeRsi(daily, buildRsiSeries(weekly), getWeekStart).map((point) => [point.date, point.value])
    );
    const rsiMonthlyByDate = new Map(
      alignHigherTimeframeRsi(daily, buildRsiSeries(monthly), (date) => `${date.slice(0, 7)}-01`)
        .map((point) => [point.date, point.value])
    );
    const avgVolatility = length > MIN_HISTORY
      ? averageAbsReturn(daily, 60, length - 1)
      : 4;
    const swingDeviation = clamp(avgVolatility * 1.6, 3, 12);
    const swings = ElliottEngine.buildSwingCache(daily, swingDeviation);
    const features = new Array(length);

    for (let endIndex = 0; endIndex < length; endIndex += 1) {
      const close = getClose(daily[endIndex]);
      const date = daily[endIndex].date;
      const swingStart = Math.max(0, endIndex + 1 - SWING_LOOKBACK);
      let swingHigh = -Infinity;
      let swingLow = Infinity;

      for (let index = swingStart; index <= endIndex; index += 1) {
        swingHigh = Math.max(swingHigh, highs[index]);
        swingLow = Math.min(swingLow, lows[index]);
      }

      const drawdown = swingHigh > 0 ? ((close - swingHigh) / swingHigh) * 100 : 0;
      const recovery = swingLow > 0 ? ((close - swingLow) / swingLow) * 100 : 0;
      const ma20 = sma(daily, MA_FAST, endIndex);
      const ma50 = sma(daily, MA_MID, endIndex);
      const ma200 = sma(daily, MA_SLOW, endIndex);
      const ma50Prev = sma(daily, MA_MID, Math.max(0, endIndex - 10));

      features[endIndex] = {
        close,
        drawdown,
        recovery,
        trend20: roc(daily, 20, endIndex),
        trend60: roc(daily, 60, endIndex),
        volatility20: averageAbsReturn(daily, 20, endIndex),
        volatility60: averageAbsReturn(daily, 60, endIndex),
        rsiDaily: rsiDailyByDate.get(date) ?? 50,
        rsiWeekly: rsiWeeklyByDate.get(date) ?? 50,
        rsiMonthly: rsiMonthlyByDate.get(date) ?? 50,
        priceVsMa20: ma20 ? ((close - ma20) / ma20) * 100 : 0,
        priceVsMa50: ma50 ? ((close - ma50) / ma50) * 100 : 0,
        priceVsMa200: ma200 ? ((close - ma200) / ma200) * 100 : 0,
        ma50Rising: ma50 !== null && ma50Prev !== null ? ma50 > ma50Prev : false,
        aboveMa50: ma50 !== null ? close > ma50 : false,
        aboveMa200: ma200 !== null ? close > ma200 : false,
        goldenStructure: ma50 !== null && ma200 !== null ? ma50 > ma200 : false,
        elliott: ElliottEngine.analyzeAt(daily, swings, endIndex)
      };
    }

    return {
      daily,
      features,
      indexByDate: new Map(daily.map((point, index) => [point.date, index]))
    };
  };

  const resolveDailyIndex = (context, date) => {
    if (context.indexByDate.has(date)) {
      return context.indexByDate.get(date);
    }

    for (let index = context.daily.length - 1; index >= 0; index -= 1) {
      if (context.daily[index].date <= date) {
        return index;
      }
    }

    return undefined;
  };

  const makeTimelinePoint = (date, classification) => ({
    date,
    zone: classification.possibleZone,
    color: zoneColors[classification.possibleZone] || zoneColors.Observing,
    label: zoneLabelsVi[classification.possibleZone] || zoneLabelsVi.Observing,
    confidence: classification.confidence,
    elliottLabel: classification.features?.elliott?.label || null,
    elliottWave: classification.features?.elliott?.waveId || null
  });

  const observingPoint = (date) => ({
    date,
    zone: "Observing",
    color: zoneColors.Observing,
    label: zoneLabelsVi.Observing,
    confidence: 0
  });

  const buildSignals = (features, zone) => {
    if (!features) {
      return [];
    }

    const signals = [
      `Drawdown ${features.drawdown.toFixed(1)}% so với đỉnh ${SWING_LOOKBACK} phiên`,
      `Phục hồi ${features.recovery.toFixed(1)}% từ đáy ${SWING_LOOKBACK} phiên`,
      `RSI ${features.rsiDaily}/${features.rsiWeekly}/${features.rsiMonthly} (N/T/Th)`,
      `Xu hướng 20/60 phiên: ${features.trend20.toFixed(1)}% / ${features.trend60.toFixed(1)}%`
    ];

    if (features.elliott?.label) {
      signals.push(`Elliott: ${features.elliott.label} → gợi ý ${zoneLabelsVi[features.elliott.psychology?.zone] || zone}`);
    }

    signals.push(`Vùng ưu tiên: ${zoneLabelsVi[zone] || zone}`);
    return signals;
  };

  const evaluate = (fullSeries, visibleSeries = fullSeries) => {
    const dailySeries = aggregateSeries(fullSeries, "1D");
    const visible = aggregateSeries(visibleSeries, "1D");
    const endIndex = dailySeries.length - 1;
    const features = endIndex + 1 >= MIN_HISTORY ? computeFeatures(dailySeries, endIndex) : null;
    const classification = classifyFromFeatures(features);
    const trend = calculateTrend(visible);

    return {
      trend: Number(trend.toFixed(2)),
      rsi: features ? Math.round((features.rsiDaily + features.rsiWeekly + features.rsiMonthly) / 3) : 50,
      rsiByInterval: features
        ? {
          daily: features.rsiDaily,
          weekly: features.rsiWeekly,
          monthly: features.rsiMonthly
        }
        : { daily: 50, weekly: 50, monthly: 50 },
      volume: features ? Math.round(clamp(40 + features.volatility20 * 12, 35, 95)) : 50,
      possibleZone: classification.possibleZone,
      confidence: classification.confidence,
      probabilities: classification.probabilities,
      signals: classification.signals,
      features
    };
  };

  const buildFeatureCache = (fullSeries) => {
    const daily = aggregateSeries(fullSeries, "1D");
    return prepareDailyContext(daily).features;
  };

  const classifyPsychology = (dailySeries, endIndex = dailySeries.length - 1) => {
    if (!dailySeries.length || endIndex + 1 < MIN_HISTORY) {
      return classifyFromFeatures(null);
    }

    const context = prepareDailyContext(dailySeries);
    return classifyFromFeatures(context.features[endIndex]);
  };

  const buildPsychologyTimeline = (fullSeries, visibleSeries, context = null) => {
    if (!visibleSeries || !visibleSeries.length) {
      return [];
    }

    const dailyContext = context || prepareDailyContext(aggregateSeries(fullSeries, "1D"));

    return visibleSeries.map((point) => {
      const endIndex = resolveDailyIndex(dailyContext, point.date);
      if (endIndex === undefined || endIndex + 1 < MIN_HISTORY) {
        return observingPoint(point.date);
      }

      return makeTimelinePoint(point.date, classifyFromFeatures(dailyContext.features[endIndex]));
    });
  };

  const ELLIOTT_WEEKLY_RANGES = ["5Y", "10Y"];

  const supportsElliottWeeklyPsychology = (range) => ELLIOTT_WEEKLY_RANGES.includes(range);

  const buildElliottWeeklyTimeline = (fullSeries, visibleSeries) => {
    if (!visibleSeries?.length) {
      return [];
    }

    const daily = aggregateSeries(fullSeries, "1D");
    const weekly = aggregateSeries(daily, "1W");
    const visibleEnd = visibleSeries[visibleSeries.length - 1].date;
    const weeklyForModel = weekly.filter((point) => point.date <= visibleEnd);
    const model = ElliottEngine.buildWeeklyPsychologyModel(
      weeklyForModel.length >= 8 ? weeklyForModel : weekly
    );

    return visibleSeries.map((point) => {
      const region = ElliottEngine.findRegionForDate(model.regions, point.date);

      return {
        date: point.date,
        zone: region.zone,
        color: zoneColors[region.zone] || zoneColors.Observing,
        label: zoneLabelsVi[region.zone] || zoneLabelsVi.Observing,
        confidence: region.confidence,
        elliottLabel: region.elliottLabel,
        elliottWave: region.waveId
      };
    });
  };

  const buildElliottWeeklyTimelineAsync = (fullSeries, visibleSeries, onProgress = () => {}) => new Promise((resolve, reject) => {
    const visible = visibleSeries || [];

    if (!visible.length) {
      resolve([]);
      return;
    }

    setTimeout(() => {
      try {
        onProgress(0.2);
        const timeline = buildElliottWeeklyTimeline(fullSeries, visible);
        onProgress(1);
        resolve(timeline);
      } catch (error) {
        reject(error);
      }
    }, 0);
  });

  const buildPsychologyTimelineAsync = (fullSeries, visibleSeries, onProgress = () => {}) => (
    buildElliottWeeklyTimelineAsync(fullSeries, visibleSeries, onProgress)
  );

  const buildPsychologySegments = (visibleSeries, timeline) => {
    if (!visibleSeries.length) {
      return [];
    }

    const segments = [];
    let currentZone = timeline[0]?.zone || "Observing";
    let points = [visibleSeries[0]];

    for (let index = 1; index < visibleSeries.length; index += 1) {
      const zone = timeline[index]?.zone || "Observing";

      if (zone !== currentZone) {
        segments.push({
          zone: currentZone,
          color: timeline[index - 1]?.color || zoneColors.Observing,
          points: [...points]
        });
        currentZone = zone;
        points = [visibleSeries[index - 1], visibleSeries[index]];
        continue;
      }

      points.push(visibleSeries[index]);
    }

    segments.push({
      zone: currentZone,
      color: timeline[timeline.length - 1]?.color || zoneColors.Observing,
      points
    });

    return segments;
  };

  const rsiTone = (value) => {
    if (value >= 70) {
      return "hot";
    }
    if (value <= 30) {
      return "cold";
    }
    return "neutral";
  };

  const renderPsychologyLegend = (container) => {
    const featuredZones = [
      "Disbelief",
      "Hope",
      "Optimism",
      "Belief",
      "Euphoria",
      "Complacency",
      "Anxiety",
      "Denial",
      "Panic",
      "Capitulation"
    ];

    container.innerHTML = `
      <p class="psychology-legend-note">Nền màu theo sóng Elliott trên khung tuần — chỉ phạm vi 5Y và 10Y</p>
      ${featuredZones.map((zone) => `
      <span class="psych-legend-item" style="--zone-color: ${zoneColors[zone]}">
        ${zoneLabelsVi[zone]}
      </span>
    `).join("")}`;
  };

  const renderRsiPanel = (container, snapshot) => {
    const {
      date = "—",
      priceText = "—",
      psychologyZone = null,
      psychologyLabel = null,
      psychologyConfidence = null,
      elliottLabel = null,
      rsiByInterval = {},
      isHover = false
    } = snapshot;

    const items = [
      { key: "daily", label: "Ngày", value: rsiByInterval.daily },
      { key: "weekly", label: "Tuần", value: rsiByInterval.weekly },
      { key: "monthly", label: "Tháng", value: rsiByInterval.monthly }
    ];

    container.innerHTML = `
      <article class="crosshair-meta ${isHover ? "active" : ""}">
        <div>
          <span>Thời điểm</span>
          <strong id="crosshair-date">${date}</strong>
        </div>
        <div>
          <span>Giá</span>
          <strong id="crosshair-price">${priceText}</strong>
        </div>
        ${psychologyZone ? `
        <div>
          <span>Tâm lý thị trường</span>
          <strong class="psych-zone-value" style="color: ${zoneColors[psychologyZone] || zoneColors.Observing}">
            ${psychologyLabel || psychologyZone}${psychologyConfidence ? ` · ${psychologyConfidence}%` : ""}
          </strong>
        </div>
        ` : ""}
        ${elliottLabel ? `
        <div>
          <span>Sóng Elliott</span>
          <strong class="elliott-value">${elliottLabel}</strong>
        </div>
        ` : ""}
      </article>
      ${items.map((item) => `
        <article class="rsi-card ${rsiTone(item.value ?? 50)}">
          <span>RSI ${item.label}</span>
          <strong>${item.value ?? "—"}</strong>
          <small>Chu kỳ ${RSI_PERIOD}</small>
        </article>
      `).join("")}
    `;
  };

  const renderCycle = (container, possibleZone) => {
    container.innerHTML = cycle.map((zone) => {
      const isPossible = zone === possibleZone;
      return `
        <div class="cycle-node ${isPossible ? "possible" : ""}">
          ${zone}
          ${isPossible ? "<span>Possible Zone</span>" : ""}
        </div>
      `;
    }).join("");
  };

  const renderProbabilities = (container, radarContainer, probabilities) => {
    const entries = Object.entries(probabilities).slice(0, 4);
    const center = 90;
    const maxRadius = 70;
    const polygonPoints = entries.map(([, value], index) => {
      const angle = (-90 + index * (360 / entries.length)) * Math.PI / 180;
      const radius = maxRadius * (value / 100);
      const x = center + Math.cos(angle) * radius;
      const y = center + Math.sin(angle) * radius;
      return `${x},${y}`;
    }).join(" ");

    container.innerHTML = entries.map(([zone, value]) => `
      <article class="psych-card">
        <h3>${zoneLabelsVi[zone] || zone}</h3>
        <strong>${value}%</strong>
        <div class="probability-track"><span style="width: ${value}%"></span></div>
      </article>
    `).join("");

    radarContainer.innerHTML = `
      <svg class="radar-svg" viewBox="0 0 180 180" role="img" aria-label="Radar style probability chart">
        <circle cx="90" cy="90" r="70"></circle>
        <circle cx="90" cy="90" r="46"></circle>
        <circle cx="90" cy="90" r="23"></circle>
        <line x1="90" y1="20" x2="90" y2="160"></line>
        <line x1="20" y1="90" x2="160" y2="90"></line>
        <polygon points="${polygonPoints}"></polygon>
      </svg>
      ${entries.map(([zone, value]) => `
      <div class="radar-row">
        <span>${zoneLabelsVi[zone] || zone}</span>
        <div class="probability-track"><span style="width: ${value}%"></span></div>
        <strong>${value}%</strong>
      </div>
      `).join("")}
    `;
  };

  return {
    cycle,
    zoneColors,
    zoneBackgroundAlpha,
    zoneLabelsVi,
    aggregateSeries,
    normalizeCandle,
    buildMultiFrameRsi,
    buildPsychologyTimeline,
    buildElliottWeeklyTimeline,
    buildElliottWeeklyTimelineAsync,
    buildPsychologyTimelineAsync,
    buildPsychologySegments,
    filterRsiByRange,
    computeFeatures,
    classifyPsychology,
    classifyFromFeatures,
    prepareDailyContext,
    supportsElliottWeeklyPsychology,
    ELLIOTT_WEEKLY_RANGES,
    evaluate,
    renderPsychologyLegend,
    renderRsiPanel,
    renderCycle,
    renderProbabilities
  };
})();
