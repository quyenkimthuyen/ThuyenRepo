/* Psychology engine: historical price features + indicator rules for market psychology zones. */
var PsychologyEngine = (() => {
  const UNIFIED_CYCLE_ZONES = [
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

  const cycle = UNIFIED_CYCLE_ZONES;

  const RSI_PERIOD = 14;
  const MA_FAST = 20;
  const MA_MID = 50;
  const MA_SLOW = 200;
  const SWING_LOOKBACK = 120;
  const MIN_HISTORY = 60;

  const zoneColors = {
    Hope: "#5B9FFF",
    Optimism: "#3DDBA8",
    Belief: "#34D399",
    Thrill: "#B8E986",
    Euphoria: "#FFC857",
    Complacency: "#FFE066",
    Anxiety: "#FF9F5A",
    Denial: "#E879F9",
    Panic: "#FF6B6B",
    Capitulation: "#E53E3E",
    Anger: "#B794F6",
    Depression: "#718096",
    Disbelief: "#A0AEC0",
    Observing: "#4A5568"
  };

  const zoneBackgroundAlpha = 0.32;
  const LOW_CONFIDENCE_THRESHOLD = 55;

  const zoneAlphaForConfidence = (confidence) => {
    if (confidence == null || confidence < LOW_CONFIDENCE_THRESHOLD) {
      return zoneBackgroundAlpha * 0.42;
    }

    return zoneBackgroundAlpha * (0.58 + (confidence / 100) * 0.42);
  };

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

  const MS_PER_DAY = 86400000;

  const parseDateMs = (dateStr) => new Date(`${dateStr}T12:00:00Z`).getTime();

  const get2DayBucketStart = (dateStr, originDateStr) => {
    const originMs = parseDateMs(originDateStr);
    const dateMs = parseDateMs(dateStr);
    const dayOffset = Math.floor((dateMs - originMs) / MS_PER_DAY);
    const bucketStartOffset = Math.floor(dayOffset / 2) * 2;
    const bucketMs = originMs + bucketStartOffset * MS_PER_DAY;

    return new Date(bucketMs).toISOString().slice(0, 10);
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
    const originDate = normalized[0].date;

    normalized.forEach((candle) => {
      let key;
      if (interval === "2D") {
        key = get2DayBucketStart(candle.date, originDate);
      } else if (interval === "1W") {
        key = getWeekStart(candle.date);
      } else {
        key = candle.date.slice(0, 7);
      }

      const existing = buckets.get(key);

      if (!existing) {
        buckets.set(key, { ...candle, date: key });
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
    const twoDay = aggregateSeries(fullSeries, "2D");
    const weekly = aggregateSeries(fullSeries, "1W");
    const monthly = aggregateSeries(fullSeries, "1M");
    const originDate = daily[0]?.date;

    const twoDayRsi = buildRsiSeries(twoDay);
    const weeklyRsi = buildRsiSeries(weekly);
    const monthlyRsi = buildRsiSeries(monthly);

    return {
      twoDay: alignHigherTimeframeRsi(
        daily,
        twoDayRsi,
        (date) => get2DayBucketStart(date, originDate)
      ),
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

  const resolveRsiAtDate = (series, date) => {
    if (!series?.length) {
      return null;
    }

    const direct = series.find((point) => point.date === date);
    if (direct) {
      return direct.value;
    }

    let value = null;
    series.forEach((point) => {
      if (point.date <= date) {
        value = point.value;
      }
    });

    return value;
  };

  const alignRsiToVisible = (visibleSeries, multiRsi) => {
    if (!visibleSeries?.length) {
      return { twoDay: [], weekly: [], monthly: [] };
    }

    const buildAligned = (source) => {
      let lastValue = 50;

      return visibleSeries.map((point) => {
        const resolved = resolveRsiAtDate(source, point.date);
        if (resolved !== null) {
          lastValue = resolved;
        }

        return { date: point.date, value: lastValue };
      });
    };

    return {
      twoDay: buildAligned(multiRsi.twoDay),
      weekly: buildAligned(multiRsi.weekly),
      monthly: buildAligned(multiRsi.monthly)
    };
  };

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
      Capitulation: 14
        + (drawdown < -30 ? 24 : 0)
        + (drawdown < -24 ? 20 : 0)
        + (rsiDaily < 28 ? 18 : 0)
        + (rsiDaily < 24 ? 20 : 0)
        + (trend60 < -18 ? 16 : 0)
        + (trend20 < -10 ? 16 : 0)
        + (recovery < 12 ? 10 : 0)
        + (volRatio > 1.25 ? 12 : 0),

      Panic: 10
        + (deepPullback ? 18 : 0)
        + (drawdown < -20 && drawdown >= -34 ? 12 : 0)
        + (rsiDaily < 32 ? 16 : 0)
        + (rsiDaily >= 24 && rsiDaily <= 38 ? 8 : 0)
        + (trend20 < -8 ? 18 : 0)
        + (volRatio > 1.35 ? 14 : 0),

      Denial: 12
        + (drawdown <= -10 && drawdown > -24 ? 16 : 0)
        + (rsiDaily >= 35 && rsiDaily <= 52 ? 10 : 0)
        + (trend20 < 0 && trend60 > 0 ? 14 : 0)
        + (trend20 > 0 && trend60 < 0 ? 10 : 0)
        + (aboveMa200 ? 8 : 0),

      Anxiety: 12
        + (moderatePullback ? 18 : 0)
        + (rsiDaily >= 38 && rsiDaily <= 55 ? 8 : 0)
        + (trend20 < -3 ? 12 : 0)
        + (trend60 < -8 ? 8 : 0)
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

      Euphoria: 12
        + (nearHigh ? 10 : 0)
        + (drawdown > -4 ? 12 : 0)
        + (rsiDaily >= 64 && rsiDaily <= 78 ? 12 : 0)
        + (rsiDaily > 72 || rsiWeekly > 68 ? 18 : 0)
        + (trend20 > 8 ? 14 : 0)
        + (trend20 > 12 ? 10 : 0)
        + (farFromLow ? 8 : 0)
        + (volRatio > 1.05 ? 6 : 0),

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
      `RSI ${features.rsiDaily}/${features.rsiWeekly}/${features.rsiMonthly} (2D/T/Th)`,
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

    const multi = buildMultiFrameRsi(fullSeries);

    return {
      trend: Number(trend.toFixed(2)),
      rsi: Math.round(
        ((multi.twoDay.at(-1)?.value ?? 50)
          + (multi.weekly.at(-1)?.value ?? 50)
          + (multi.monthly.at(-1)?.value ?? 50)) / 3
      ),
      rsiByInterval: {
        twoDay: multi.twoDay.at(-1)?.value ?? 50,
        weekly: multi.weekly.at(-1)?.value ?? 50,
        monthly: multi.monthly.at(-1)?.value ?? 50
      },
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

  const TEN_YEAR_DAYS = 365 * 10;
  const PSYCHOLOGY_CACHE_PREFIX = "priceac.psychology.v3.";
  const PSYCHOLOGY_CACHE_VERSION = 13;
  const REFERENCE_ASSET = "bitcoin";

  const getCacheStorageKey = (asset, model = "elliott") => (
    model === "ema"
      ? `${PSYCHOLOGY_CACHE_PREFIX}ema.${asset}`
      : `${PSYCHOLOGY_CACHE_PREFIX}${asset}`
  );

  const getTenYearDailySlice = (fullSeries) => {
    const daily = aggregateSeries(fullSeries, "1D");
    return daily.slice(-TEN_YEAR_DAYS);
  };

  const regionToTimelinePoint = (date, region) => ({
    date,
    zone: region.zone,
    color: zoneColors[region.zone] || zoneColors.Observing,
    label: zoneLabelsVi[region.zone] || zoneLabelsVi.Observing,
    confidence: region.confidence,
    lowConfidence: (region.confidence ?? 100) < LOW_CONFIDENCE_THRESHOLD || region.zone === "Observing",
    elliottLabel: region.elliottLabel,
    elliottWave: region.waveId
  });

  const getSummaryFromRegion = (region) => ({
    zone: region.zone,
    label: zoneLabelsVi[region.zone] || zoneLabelsVi.Observing,
    confidence: region.confidence,
    elliottLabel: region.elliottLabel,
    elliottWave: region.waveId
  });

  const getPsychologyZoneAtDate = (cache, date) => {
    if (!cache?.regions?.length || !date) {
      return null;
    }

    if (date < cache.rangeStart || date > cache.rangeEnd) {
      return null;
    }

    return ElliottEngine.findRegionForDate(cache.regions, date)?.zone || null;
  };

  const comparePsychologyAtDate = (walkForwardCache, baselineCache, date) => {
    const walkForwardZone = getPsychologyZoneAtDate(walkForwardCache, date);
    const baselineZone = getPsychologyZoneAtDate(baselineCache, date);
    const comparable = Boolean(walkForwardZone && baselineZone);

    return {
      date,
      walkForwardZone,
      baselineZone,
      comparable,
      match: comparable && walkForwardZone === baselineZone
    };
  };

  const zoneCycleDistance = (leftZone, rightZone) => {
    const leftIndex = cycle.indexOf(leftZone);
    const rightIndex = cycle.indexOf(rightZone);

    if (leftIndex < 0 || rightIndex < 0) {
      return null;
    }

    return Math.abs(leftIndex - rightIndex);
  };

  const SIM_MIN_CONFIDENCE = 60;
  const SIM_DAILY_BLEND_MIN_CONFIDENCE = 58;
  const SIM_HYSTERESIS_WEEKS = 2;

  const cloneCache = (cache, regions, summary) => ({
    ...cache,
    regions,
    summary: summary || cache.summary
  });

  const applyConfidenceGateToCache = (cache, minConfidence = SIM_MIN_CONFIDENCE) => {
    if (!cache?.regions?.length) {
      return cache;
    }

    const regions = cache.regions.map((region) => {
      if ((region.confidence ?? 0) < minConfidence) {
        return {
          ...region,
          zone: "Observing",
          label: zoneLabelsVi.Observing
        };
      }

      return region;
    });
    const activeRegion = ElliottEngine.findRegionForDate(regions, cache.rangeEnd) || regions.at(-1);

    return cloneCache(cache, regions, {
      ...cache.summary,
      zone: activeRegion.zone,
      label: zoneLabelsVi[activeRegion.zone] || zoneLabelsVi.Observing,
      confidence: activeRegion.confidence
    });
  };

  const overrideZoneAtDate = (cache, date, zone, patch = {}) => {
    if (!cache?.regions?.length || !date || !zone) {
      return cache;
    }

    const regions = cache.regions.map((region) => {
      if (date < region.startDate || date > region.endDate) {
        return region;
      }

      return {
        ...region,
        zone,
        label: zoneLabelsVi[zone] || zoneLabelsVi.Observing,
        confidence: patch.confidence ?? region.confidence
      };
    });
    const activeRegion = ElliottEngine.findRegionForDate(regions, cache.rangeEnd) || regions.at(-1);

    return cloneCache(cache, regions, {
      ...cache.summary,
      zone: activeRegion.zone,
      label: zoneLabelsVi[activeRegion.zone] || zoneLabelsVi.Observing,
      confidence: activeRegion.confidence,
      elliottLabel: activeRegion.elliottLabel,
      elliottWave: activeRegion.waveId,
      elliottValidated: activeRegion.elliottValidated,
      validationNote: activeRegion.validationNote
    });
  };

  const blendDailyPsychologyAtDate = (cache, clippedSeries, asOfDate) => {
    if (!cache?.regions?.length) {
      return cache;
    }

    const daily = aggregateSeries(clippedSeries, "1D");
    const endIndex = daily.findIndex((point) => point.date === asOfDate);
    if (endIndex < MIN_HISTORY - 1) {
      return cache;
    }

    const classification = classifyPsychology(daily, endIndex);
    const elliottZone = getPsychologyZoneAtDate(cache, asOfDate);
    const dailyZone = classification.possibleZone;
    if (!elliottZone || !dailyZone || dailyZone === elliottZone) {
      return cache;
    }

    const distance = zoneCycleDistance(elliottZone, dailyZone);
    const region = ElliottEngine.findRegionForDate(cache.regions, asOfDate);
    if (region?.elliottValidated === true) {
      return cache;
    }

    const lowElliottConfidence = (region?.confidence ?? 0) < 65;

    if (
      distance !== null
      && distance <= 2
      && (lowElliottConfidence || classification.confidence >= SIM_DAILY_BLEND_MIN_CONFIDENCE)
    ) {
      return overrideZoneAtDate(cache, asOfDate, dailyZone, {
        confidence: Math.round(((region?.confidence ?? 50) + classification.confidence) / 2)
      });
    }

    return cache;
  };

  const buildEmaWalkForwardDisplayCache = (fullSeries, options = {}) => {
    if (typeof EmaPsychologyEngine === "undefined") {
      return null;
    }

    const daily = aggregateSeries(fullSeries, "1D");
    const tenYearSlice = getTenYearDailySlice(fullSeries);

    if (tenYearSlice.length < 28) {
      return null;
    }

    const rangeStart = tenYearSlice[0].date;
    const rangeEnd = tenYearSlice[tenYearSlice.length - 1].date;
    const checkpoints = buildWeeklyWalkForwardCheckpoints(
      daily,
      rangeStart,
      rangeEnd,
      options.useWeekEnd !== false
    );

    if (!checkpoints.length) {
      return EmaPsychologyEngine.buildPsychologyCache(fullSeries);
    }

    let frozenRegions = [];
    let displayCache = null;
    const hysteresis = createSimulationHysteresisState();
    const hysteresisWeeks = options.hysteresisWeeks ?? SIM_HYSTERESIS_WEEKS;

    checkpoints.forEach(({ asOfDate }) => {
      const clipped = fullSeries.filter((point) => point.date <= asOfDate);
      let cache = EmaPsychologyEngine.buildPsychologyCache(clipped);

      if (!cache) {
        return;
      }

      if (typeof options.enrichCache === "function") {
        cache = options.enrichCache(cache, clipped) || cache;
      }

      displayCache = applySimulationHysteresis(cache, asOfDate, hysteresis, hysteresisWeeks);
      frozenRegions = mergeFrozenPsychologyRegions(frozenRegions, displayCache, asOfDate);
    });

    const composed = composeSimulationPsychologyCache(displayCache, frozenRegions, rangeEnd);

    if (!composed) {
      return null;
    }

    return {
      ...composed,
      version: PSYCHOLOGY_CACHE_VERSION,
      model: "ema",
      dataEndDate: rangeEnd,
      walkForwardDisplay: true,
      analyzedAt: new Date().toISOString()
    };
  };

  const buildEmaWalkForwardDisplayCacheAsync = (fullSeries, onProgress = () => {}, options = {}) => new Promise((resolve, reject) => {
    try {
      const daily = aggregateSeries(fullSeries, "1D");
      const tenYearSlice = getTenYearDailySlice(fullSeries);

      if (tenYearSlice.length < 28) {
        resolve(null);
        return;
      }

      const rangeStart = tenYearSlice[0].date;
      const rangeEnd = tenYearSlice[tenYearSlice.length - 1].date;
      const checkpoints = buildWeeklyWalkForwardCheckpoints(
        daily,
        rangeStart,
        rangeEnd,
        options.useWeekEnd !== false
      );

      if (!checkpoints.length) {
        resolve(EmaPsychologyEngine.buildPsychologyCache(fullSeries));
        return;
      }

      let frozenRegions = [];
      let displayCache = null;
      const hysteresis = createSimulationHysteresisState();
      const hysteresisWeeks = options.hysteresisWeeks ?? SIM_HYSTERESIS_WEEKS;
      let index = 0;

      const step = () => {
        if (index >= checkpoints.length) {
          try {
            const composed = composeSimulationPsychologyCache(displayCache, frozenRegions, rangeEnd);
            if (!composed) {
              resolve(null);
              return;
            }

            resolve({
              ...composed,
              version: PSYCHOLOGY_CACHE_VERSION,
              model: "ema",
              dataEndDate: rangeEnd,
              walkForwardDisplay: true,
              analyzedAt: new Date().toISOString()
            });
          } catch (error) {
            reject(error);
          }
          return;
        }

        const { asOfDate } = checkpoints[index];
        const clipped = fullSeries.filter((point) => point.date <= asOfDate);
        let cache = EmaPsychologyEngine.buildPsychologyCache(clipped);

        if (cache) {
          if (typeof options.enrichCache === "function") {
            cache = options.enrichCache(cache, clipped) || cache;
          }

          displayCache = applySimulationHysteresis(cache, asOfDate, hysteresis, hysteresisWeeks);
          frozenRegions = mergeFrozenPsychologyRegions(frozenRegions, displayCache, asOfDate);
        }

        index += 1;
        onProgress(index / checkpoints.length);
        setTimeout(step, 0);
      };

      step();
    } catch (error) {
      reject(error);
    }
  });

  const buildUnifiedPsychologyCache = (fullSeries, options = {}) => {
    const asOfDate = options.asOfDate ?? options.cursorDate ?? null;

    if (
      options.model === "ema"
      && !asOfDate
      && options.walkForwardDisplay !== false
      && typeof EmaPsychologyEngine !== "undefined"
    ) {
      return buildEmaWalkForwardDisplayCache(fullSeries, options);
    }

    const clipped = asOfDate
      ? fullSeries.filter((point) => point.date <= asOfDate)
      : fullSeries;

    if (options.model === "ema" && typeof EmaPsychologyEngine !== "undefined") {
      let cache = EmaPsychologyEngine.buildPsychologyCache(clipped);

      if (!cache) {
        return null;
      }

      if (typeof options.enrichCache === "function") {
        cache = options.enrichCache(cache, clipped) || cache;
      }

      return cache;
    }

    let cache = buildPsychologyCache(clipped);

    if (!cache) {
      return null;
    }

    if (typeof options.enrichCache === "function") {
      cache = options.enrichCache(cache, clipped) || cache;
    }

    if (options.applyConfidenceGate === true) {
      cache = applyConfidenceGateToCache(cache, options.minConfidence ?? SIM_MIN_CONFIDENCE);
    }

    if (options.applyDailyBlend === true) {
      cache = blendDailyPsychologyAtDate(cache, clipped, cache.rangeEnd);
    }

    return cache;
  };

  const buildWalkForwardPsychologyCache = (fullSeries, asOfDate, options = {}) => (
    buildUnifiedPsychologyCache(fullSeries, { ...options, asOfDate })
  );

  const createSimulationHysteresisState = () => ({
    stableZone: null,
    pendingZone: null,
    pendingWeeks: 0
  });

  const applySimulationHysteresis = (
    cache,
    asOfDate,
    hysteresisState,
    weeksRequired = SIM_HYSTERESIS_WEEKS
  ) => {
    if (!cache || !asOfDate || !hysteresisState) {
      return cache;
    }

    const rawZone = getPsychologyZoneAtDate(cache, asOfDate);
    if (!rawZone) {
      return cache;
    }

    if (!hysteresisState.stableZone) {
      hysteresisState.stableZone = rawZone;
      hysteresisState.pendingZone = null;
      hysteresisState.pendingWeeks = 0;
      return cache;
    }

    if (rawZone === hysteresisState.stableZone) {
      hysteresisState.pendingZone = null;
      hysteresisState.pendingWeeks = 0;
      return cache;
    }

    if (rawZone === hysteresisState.pendingZone) {
      hysteresisState.pendingWeeks += 1;
    } else {
      hysteresisState.pendingZone = rawZone;
      hysteresisState.pendingWeeks = 1;
    }

    if (hysteresisState.pendingWeeks >= weeksRequired) {
      hysteresisState.stableZone = rawZone;
      hysteresisState.pendingZone = null;
      hysteresisState.pendingWeeks = 0;
      return cache;
    }

    return overrideZoneAtDate(cache, asOfDate, hysteresisState.stableZone);
  };

  const getFrozenRegionsEnd = (frozenRegions) => (
    frozenRegions.length ? frozenRegions[frozenRegions.length - 1].endDate : null
  );

  const nextCalendarDate = (date) => {
    const parsed = new Date(`${date}T12:00:00Z`);
    parsed.setUTCDate(parsed.getUTCDate() + 1);
    return parsed.toISOString().slice(0, 10);
  };

  const mergeFrozenPsychologyRegions = (frozenRegions, cache, asOfDate) => {
    if (!cache?.regions?.length || !asOfDate) {
      return frozenRegions;
    }

    const merged = [...frozenRegions];
    let frozenEnd = getFrozenRegionsEnd(merged);
    const sorted = [...cache.regions].sort((left, right) => (
      left.startDate.localeCompare(right.startDate)
    ));

    sorted.forEach((region) => {
      if (region.endDate > asOfDate) {
        return;
      }

      if (frozenEnd && region.endDate <= frozenEnd) {
        return;
      }

      let startDate = region.startDate;
      if (frozenEnd && startDate <= frozenEnd) {
        startDate = nextCalendarDate(frozenEnd);
      }

      if (startDate > region.endDate) {
        return;
      }

      merged.push({
        ...region,
        startDate,
        endDate: region.endDate
      });
      frozenEnd = region.endDate;
    });

    return merged;
  };

  const buildSimulationActiveRegion = (cache, cursorDate, frozenRegions) => {
    if (!cache?.regions?.length || !cursorDate) {
      return null;
    }

    const region = ElliottEngine.findRegionForDate(cache.regions, cursorDate);
    if (!region) {
      return null;
    }

    const frozenEnd = getFrozenRegionsEnd(frozenRegions);
    let startDate = region.startDate;
    if (frozenEnd && startDate <= frozenEnd) {
      startDate = nextCalendarDate(frozenEnd);
    }

    if (startDate > cursorDate) {
      return null;
    }

    const endDate = region.endDate > cursorDate ? cursorDate : region.endDate;
    if (startDate > endDate) {
      return null;
    }

    return {
      ...region,
      startDate,
      endDate
    };
  };

  const composeSimulationPsychologyCache = (baseCache, frozenRegions, cursorDate) => {
    if (!baseCache || !cursorDate) {
      return baseCache;
    }

    const activeRegion = buildSimulationActiveRegion(baseCache, cursorDate, frozenRegions);
    const regions = activeRegion
      ? [...frozenRegions, activeRegion]
      : [...frozenRegions];

    if (!regions.length) {
      return {
        ...baseCache,
        rangeStart: baseCache.rangeStart,
        rangeEnd: cursorDate,
        regionCount: 0
      };
    }

    const active = ElliottEngine.findRegionForDate(regions, cursorDate) || regions.at(-1);

    return {
      ...cloneCache(baseCache, regions, {
        ...getSummaryFromRegion(active),
        zone: active.zone,
        label: zoneLabelsVi[active.zone] || zoneLabelsVi.Observing,
        confidence: active.confidence,
        elliottLabel: active.elliottLabel,
        elliottWave: active.waveId
      }),
      rangeStart: regions[0].startDate,
      rangeEnd: cursorDate,
      regionCount: regions.length
    };
  };

  const resolveWalkForwardCache = (fullSeries, asOfDate, pipeline = {}) => {
    const mode = pipeline.mode || "enhanced";
    if (mode === "legacy") {
      const clipped = fullSeries.filter((point) => point.date <= asOfDate);
      if (pipeline.model === "ema") {
        return buildUnifiedPsychologyCache(clipped, { model: "ema" });
      }

      return buildPsychologyCache(clipped);
    }

    let cache = buildWalkForwardPsychologyCache(fullSeries, asOfDate, pipeline);
    if (cache && pipeline.hysteresisState && (pipeline.hysteresisWeeks ?? SIM_HYSTERESIS_WEEKS) > 0) {
      cache = applySimulationHysteresis(
        cache,
        asOfDate,
        pipeline.hysteresisState,
        pipeline.hysteresisWeeks ?? SIM_HYSTERESIS_WEEKS
      );
    }

    return cache;
  };

  const summarizeComparisonEntries = (entries, relaxedDistance = 2) => {
    const comparable = entries.filter((entry) => entry.comparable);
    const matched = comparable.filter((entry) => entry.match);
    const relaxedMatched = comparable.filter((entry) => entry.relaxedMatch);
    const mismatchPairs = {};

    comparable
      .filter((entry) => !entry.match)
      .forEach((entry) => {
        const key = `${entry.walkForwardZone}->${entry.baselineZone}`;
        mismatchPairs[key] = (mismatchPairs[key] || 0) + 1;
      });

    const toPercent = (count) => (
      comparable.length ? Math.round((count / comparable.length) * 1000) / 10 : null
    );

    return {
      totalWeeks: entries.length,
      comparableWeeks: comparable.length,
      matchedWeeks: matched.length,
      relaxedMatchedWeeks: relaxedMatched.length,
      accuracyPercent: toPercent(matched.length),
      relaxedAccuracyPercent: toPercent(relaxedMatched.length),
      errorPercent: comparable.length
        ? Math.round(((comparable.length - matched.length) / comparable.length) * 1000) / 10
        : null,
      mismatchPairs: Object.entries(mismatchPairs)
        .sort((left, right) => right[1] - left[1])
        .map(([pair, count]) => ({ pair, count }))
    };
  };

  const buildWeeklyWalkForwardCheckpoints = (dailySeries, startDate, endDate, useWeekEnd = true) => {
    const byWeek = new Map();

    dailySeries
      .filter((point) => point.date >= startDate && point.date <= endDate)
      .forEach((point) => {
        const weekKey = getWeekStart(point.date);
        if (useWeekEnd) {
          byWeek.set(weekKey, point.date);
          return;
        }

        if (!byWeek.has(weekKey)) {
          byWeek.set(weekKey, point.date);
        }
      });

    return [...byWeek.entries()].map(([weekKey, asOfDate]) => ({ weekKey, asOfDate }));
  };

  const buildComparisonEntries = (fullSeries, baseline, checkpoints, pipeline = {}) => {
    const relaxedDistance = pipeline.relaxedDistance ?? 2;
    const hysteresisState = pipeline.applyHysteresis
      ? createSimulationHysteresisState()
      : null;
    const activePipeline = {
      ...pipeline,
      hysteresisState
    };

    return checkpoints.map(({ weekKey, asOfDate }) => {
      const walkForwardCache = resolveWalkForwardCache(fullSeries, asOfDate, activePipeline);
      const comparison = comparePsychologyAtDate(walkForwardCache, baseline, asOfDate);
      const distance = comparison.comparable
        ? zoneCycleDistance(comparison.walkForwardZone, comparison.baselineZone)
        : null;

      return {
        weekKey,
        asOfDate,
        ...comparison,
        cycleDistance: distance,
        relaxedMatch: comparison.comparable && distance !== null && distance <= relaxedDistance
      };
    });
  };

  const buildWalkForwardAccuracyReport = (fullSeries, options = {}) => {
    const daily = aggregateSeries(fullSeries, "1D");
    if (daily.length < 28) {
      return null;
    }

    const baseline = options.model === "ema"
      ? buildUnifiedPsychologyCache(fullSeries, { model: "ema", walkForwardDisplay: false })
      : buildPsychologyCache(fullSeries);
    if (!baseline) {
      return null;
    }

    const minHistoryDays = options.minHistoryDays ?? 365;
    const relaxedDistance = options.relaxedDistance ?? 2;
    const startIndex = Math.min(Math.max(minHistoryDays, 0), daily.length - 1);
    const startDate = options.startDate ?? daily[startIndex]?.date;
    const endDate = options.endDate ?? daily.at(-1).date;

    if (!startDate || !endDate || startDate > endDate) {
      return null;
    }

    const checkpoints = buildWeeklyWalkForwardCheckpoints(
      daily,
      startDate,
      endDate,
      options.useWeekEnd !== false
    );
    const legacyCheckpoints = options.includeLegacyWeekStart
      ? buildWeeklyWalkForwardCheckpoints(daily, startDate, endDate, false)
      : checkpoints;

    const legacyEntries = buildComparisonEntries(fullSeries, baseline, legacyCheckpoints, {
      mode: "legacy",
      model: options.model,
      relaxedDistance
    });
    const enhancedEntries = buildComparisonEntries(fullSeries, baseline, checkpoints, {
      mode: "enhanced",
      model: options.model,
      relaxedDistance,
      enrichCache: options.enrichCache,
      applyConfidenceGate: options.applyConfidenceGate,
      applyDailyBlend: options.applyDailyBlend,
      hysteresisWeeks: options.hysteresisWeeks ?? SIM_HYSTERESIS_WEEKS,
      minConfidence: options.minConfidence ?? SIM_MIN_CONFIDENCE
    });

    const legacy = summarizeComparisonEntries(legacyEntries, relaxedDistance);
    const enhanced = summarizeComparisonEntries(enhancedEntries, relaxedDistance);

    return {
      startDate,
      endDate,
      minHistoryDays,
      relaxedDistance,
      legacy,
      enhanced,
      improvement: {
        accuracyDelta: enhanced.accuracyPercent !== null && legacy.accuracyPercent !== null
          ? Math.round((enhanced.accuracyPercent - legacy.accuracyPercent) * 10) / 10
          : null,
        relaxedAccuracyDelta: enhanced.relaxedAccuracyPercent !== null && legacy.relaxedAccuracyPercent !== null
          ? Math.round((enhanced.relaxedAccuracyPercent - legacy.relaxedAccuracyPercent) * 10) / 10
          : null,
        errorDelta: legacy.errorPercent !== null && enhanced.errorPercent !== null
          ? Math.round((legacy.errorPercent - enhanced.errorPercent) * 10) / 10
          : null
      },
      totalWeeks: enhanced.totalWeeks,
      comparableWeeks: enhanced.comparableWeeks,
      matchedWeeks: enhanced.matchedWeeks,
      relaxedMatchedWeeks: enhanced.relaxedMatchedWeeks,
      accuracyPercent: enhanced.accuracyPercent,
      relaxedAccuracyPercent: enhanced.relaxedAccuracyPercent,
      errorPercent: enhanced.errorPercent,
      mismatchPairs: enhanced.mismatchPairs,
      entries: enhancedEntries
    };
  };

  const buildPsychologyCache = (fullSeries, options = {}) => {
    if (options.model === "ema" && typeof EmaPsychologyEngine !== "undefined") {
      return EmaPsychologyEngine.buildPsychologyCache(fullSeries);
    }

    const dailyTenYear = getTenYearDailySlice(fullSeries);

    if (dailyTenYear.length < 28) {
      return null;
    }

    const rangeStart = dailyTenYear[0].date;
    const rangeEnd = dailyTenYear[dailyTenYear.length - 1].date;
    const weekly = aggregateSeries(dailyTenYear, "1W");
    const model = ElliottEngine.buildWeeklyPsychologyModel(weekly, {
      rangeStart,
      rangeEnd
    });
    const latestRegion = ElliottEngine.findRegionForDate(model.regions, rangeEnd);

    return {
      version: PSYCHOLOGY_CACHE_VERSION,
      model: "elliott",
      rangeStart,
      rangeEnd,
      dataEndDate: rangeEnd,
      weekCount: weekly.length,
      regionCount: model.regions.length,
      regions: model.regions,
      swings: model.swings,
      pivots: model.pivots,
      weekly,
      summary: getSummaryFromRegion(latestRegion),
      analyzedAt: new Date().toISOString()
    };
  };

  const buildPsychologyCacheAsync = (fullSeries, onProgress = () => {}, options = {}) => {
    const asOfDate = options.asOfDate ?? options.cursorDate ?? null;

    if (
      options.model === "ema"
      && !asOfDate
      && options.walkForwardDisplay !== false
    ) {
      return buildEmaWalkForwardDisplayCacheAsync(fullSeries, onProgress, options);
    }

    return new Promise((resolve, reject) => {
      setTimeout(() => {
        try {
          onProgress(0.2);
          const cache = buildUnifiedPsychologyCache(fullSeries, options);
          onProgress(1);
          resolve(cache);
        } catch (error) {
          reject(error);
        }
      }, 0);
    });
  };

  const isPsychologyCacheValid = (cache, fullSeries, model = "elliott") => {
    if (!cache || cache.version !== PSYCHOLOGY_CACHE_VERSION || !cache.regions?.length) {
      return false;
    }

    const cacheModel = cache.model || "elliott";
    if (cacheModel !== model) {
      return false;
    }

    if (cacheModel === "elliott" && (!cache.pivots?.length || !cache.swings?.length)) {
      return false;
    }

    const daily = aggregateSeries(fullSeries, "1D");
    const latestDate = daily.at(-1)?.date;
    return Boolean(latestDate && cache.dataEndDate === latestDate);
  };

  const savePsychologyCache = (asset, cache, model = "elliott") => {
    if (!cache) {
      return;
    }

    try {
      localStorage.setItem(getCacheStorageKey(asset, model), JSON.stringify(cache));
    } catch (error) {
      console.warn("Không lưu được phân tích tâm lý", error);
    }
  };

  const loadPsychologyCache = (asset, model = "elliott") => {
    try {
      const raw = localStorage.getItem(getCacheStorageKey(asset, model));
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      console.warn("Không đọc được phân tích đã lưu", error);
      return null;
    }
  };

  const clearPsychologyCache = (asset, model = "elliott") => {
    try {
      localStorage.removeItem(getCacheStorageKey(asset, model));
    } catch (error) {
      console.warn("Không xóa được phân tích đã lưu", error);
    }
  };

  const projectPsychologyToSeries = (cache, visibleSeries) => {
    if (!cache?.regions?.length || !visibleSeries?.length) {
      return [];
    }

    return visibleSeries.map((point) => {
      if (point.date < cache.rangeStart || point.date > cache.rangeEnd) {
        return observingPoint(point.date);
      }

      return regionToTimelinePoint(
        point.date,
        ElliottEngine.findRegionForDate(cache.regions, point.date)
      );
    });
  };

  const buildMarketMetrics = (fullSeries, visibleSeries) => {
    const visible = aggregateSeries(visibleSeries, "1D");
    const multi = buildMultiFrameRsi(fullSeries);
    const rsiByInterval = {
      twoDay: multi.twoDay.at(-1)?.value ?? 50,
      weekly: multi.weekly.at(-1)?.value ?? 50,
      monthly: multi.monthly.at(-1)?.value ?? 50
    };

    return {
      trend: Number(calculateTrend(visible).toFixed(2)),
      rsi: Math.round((rsiByInterval.twoDay + rsiByInterval.weekly + rsiByInterval.monthly) / 3),
      rsiByInterval
    };
  };

  const buildMarketSnapshot = (cache, fullSeries, visibleSeries) => {
    const metrics = buildMarketMetrics(fullSeries, visibleSeries);

    if (!cache) {
      return {
        ...metrics,
        hasAnalysis: false
      };
    }

    return {
      ...metrics,
      hasAnalysis: true,
      analyzedAt: cache.analyzedAt,
      weekCount: cache.weekCount,
      regionCount: cache.regionCount,
      rangeStart: cache.rangeStart,
      rangeEnd: cache.rangeEnd,
      ...cache.summary
    };
  };

  const formatAnalyzedAt = (isoDate) => {
    if (!isoDate) {
      return "";
    }

    const date = new Date(isoDate);
    if (Number.isNaN(date.getTime())) {
      return "";
    }

    return date.toLocaleString("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

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
        const prevPoint = timeline[index - 1];
        segments.push({
          zone: currentZone,
          color: prevPoint?.color || zoneColors.Observing,
          opacity: zoneAlphaForConfidence(prevPoint?.confidence),
          lowConfidence: prevPoint?.lowConfidence,
          points: [...points]
        });
        currentZone = zone;
        points = [visibleSeries[index - 1], visibleSeries[index]];
        continue;
      }

      points.push(visibleSeries[index]);
    }

    const lastPoint = timeline[timeline.length - 1];
    segments.push({
      zone: currentZone,
      color: lastPoint?.color || zoneColors.Observing,
      opacity: zoneAlphaForConfidence(lastPoint?.confidence),
      lowConfidence: lastPoint?.lowConfidence,
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
      <p class="psychology-legend-note">Bản đồ 10 năm (nến tuần) — mỗi giai đoạn gắn một sóng Elliott và vùng tâm lý</p>
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

    const intervalLabels = snapshot.rsiIntervalLabels || {
      twoDay: "2D",
      weekly: "T",
      monthly: "Th"
    };

    const items = [
      { key: "twoDay", label: intervalLabels.twoDay, value: rsiByInterval.twoDay },
      { key: "weekly", label: intervalLabels.weekly, value: rsiByInterval.weekly },
      { key: "monthly", label: intervalLabels.monthly, value: rsiByInterval.monthly }
    ];

    container.innerHTML = `
      <div class="hover-bar ${isHover ? "is-active" : ""}">
        <div class="hover-fields">
          <div class="hover-field">
            <span>Thời điểm</span>
            <strong id="crosshair-date">${date}</strong>
          </div>
          <div class="hover-field">
            <span>Giá</span>
            <strong id="crosshair-price">${priceText}</strong>
          </div>
          ${psychologyZone ? `
          <div class="hover-field hover-field--zone">
            <span>Tâm lý</span>
            <strong class="psych-zone-value" style="color: ${zoneColors[psychologyZone] || zoneColors.Observing}">
              ${psychologyLabel || psychologyZone}
            </strong>
          </div>
          ` : ""}
          ${elliottLabel ? `
          <div class="hover-field">
            <span>Sóng</span>
            <strong class="elliott-value">${elliottLabel}</strong>
          </div>
          ` : ""}
        </div>
        <div class="rsi-inline" aria-label="RSI đa khung">
          ${items.map((item) => `
            <span class="rsi-pill ${rsiTone(item.value ?? 50)} ${item.key}">
              <em>${item.label}</em> ${item.value ?? "—"}
            </span>
          `).join("")}
        </div>
      </div>
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
    SIM_MIN_CONFIDENCE,
    SIM_DAILY_BLEND_MIN_CONFIDENCE,
    SIM_HYSTERESIS_WEEKS,
    UNIFIED_CYCLE_ZONES,
    cycle,
    zoneColors,
    zoneBackgroundAlpha,
    zoneAlphaForConfidence,
    LOW_CONFIDENCE_THRESHOLD,
    zoneLabelsVi,
    TEN_YEAR_DAYS,
    REFERENCE_ASSET,
    aggregateSeries,
    normalizeCandle,
    getWeekStart,
    buildMultiFrameRsi,
    alignRsiToVisible,
    buildPsychologyCache,
    buildUnifiedPsychologyCache,
    buildEmaWalkForwardDisplayCache,
    buildPsychologyCacheAsync,
    getPsychologyZoneAtDate,
    comparePsychologyAtDate,
    zoneCycleDistance,
    buildWeeklyWalkForwardCheckpoints,
    buildWalkForwardPsychologyCache,
    buildWalkForwardAccuracyReport,
    applyConfidenceGateToCache,
    blendDailyPsychologyAtDate,
    createSimulationHysteresisState,
    applySimulationHysteresis,
    mergeFrozenPsychologyRegions,
    composeSimulationPsychologyCache,
    resolveWalkForwardCache,
    SIM_MIN_CONFIDENCE,
    SIM_HYSTERESIS_WEEKS,
    projectPsychologyToSeries,
    buildMarketMetrics,
    buildMarketSnapshot,
    isPsychologyCacheValid,
    getSummaryFromRegion,
    savePsychologyCache,
    loadPsychologyCache,
    clearPsychologyCache,
    formatAnalyzedAt,
    buildPsychologySegments,
    filterRsiByRange,
    renderPsychologyLegend,
    renderRsiPanel
  };
})();
