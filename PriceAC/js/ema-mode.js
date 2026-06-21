/* EMA 50/200 psychology: Elliott time structure + regime filter + weekly refinement. */
var EmaPsychologyEngine = (() => {
  const EMA_FAST = 50;
  const EMA_SLOW = 200;
  const TREND_LOOKBACK_DAYS = 20;
  const TREND_THRESHOLD = 0.01;
  const EMA_SLOPE_THRESHOLD = 0.004;
  const DRAWDOWN_LOOKBACK_DAYS = 156 * 7;
  const GOLDEN_CROSS_LOOKBACK_DAYS = 56;
  const REGIME_CONFIRM_WEEKS = 2;
  const LOW_CONFIDENCE_THRESHOLD = 55;
  const RSI_PERIOD = 14;

  const POSITIVE_ZONES = new Set([
    "Disbelief",
    "Hope",
    "Optimism",
    "Belief",
    "Euphoria",
    "Complacency"
  ]);

  const NEGATIVE_ZONES = new Set([
    "Anxiety",
    "Denial",
    "Panic",
    "Capitulation"
  ]);

  const WAVE_BULL = {
    1: "Hope",
    2: "Optimism",
    3: "Belief",
    4: "Complacency",
    5: "Euphoria",
    A: "Anxiety",
    B: "Denial",
    C: "Panic"
  };

  const WAVE_BEAR = {
    1: "Disbelief",
    2: "Denial",
    3: "Panic",
    4: "Anxiety",
    5: "Denial",
    A: "Anxiety",
    B: "Denial",
    C: "Panic"
  };

  const WAVE_ACCUMULATION = {
    1: "Disbelief",
    2: "Hope",
    3: "Optimism",
    4: "Hope",
    5: "Belief",
    A: "Anxiety",
    B: "Disbelief",
    C: "Capitulation"
  };

  const WAVE_DISTRIBUTION = {
    1: "Complacency",
    2: "Anxiety",
    3: "Denial",
    4: "Anxiety",
    5: "Denial",
    A: "Anxiety",
    B: "Denial",
    C: "Panic"
  };

  const getClose = (point) => point.close ?? point.price;

  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

  const computeEmaSeries = (daily, period) => {
    const series = new Array(daily.length).fill(null);

    if (daily.length < period) {
      return series;
    }

    const multiplier = 2 / (period + 1);
    let ema = 0;

    for (let index = 0; index < period; index += 1) {
      ema += getClose(daily[index]);
    }

    ema /= period;
    series[period - 1] = ema;

    for (let index = period; index < daily.length; index += 1) {
      ema = getClose(daily[index]) * multiplier + ema * (1 - multiplier);
      series[index] = ema;
    }

    return series;
  };

  const computeRsiSeries = (series, period = RSI_PERIOD) => {
    const output = new Array(series.length).fill(null);

    if (series.length <= period) {
      return output;
    }

    let gainSum = 0;
    let lossSum = 0;

    for (let index = 1; index <= period; index += 1) {
      const change = getClose(series[index]) - getClose(series[index - 1]);
      if (change >= 0) {
        gainSum += change;
      } else {
        lossSum -= change;
      }
    }

    let avgGain = gainSum / period;
    let avgLoss = lossSum / period;
    output[period] = avgLoss === 0 ? 100 : 100 - (100 / (1 + avgGain / avgLoss));

    for (let index = period + 1; index < series.length; index += 1) {
      const change = getClose(series[index]) - getClose(series[index - 1]);
      const gain = change > 0 ? change : 0;
      const loss = change < 0 ? -change : 0;
      avgGain = (avgGain * (period - 1) + gain) / period;
      avgLoss = (avgLoss * (period - 1) + loss) / period;
      output[index] = avgLoss === 0 ? 100 : 100 - (100 / (1 + avgGain / avgLoss));
    }

    return output;
  };

  const buildWeeklyRsiLookup = (daily) => {
    const weekly = PsychologyEngine.aggregateSeries(daily, "1W");
    const rsi = computeRsiSeries(weekly);
    const lookup = new Map();

    weekly.forEach((point, index) => {
      if (rsi[index] !== null) {
        lookup.set(point.date, rsi[index]);
      }
    });

    return lookup;
  };

  const findDailyIndexOnOrBefore = (daily, date) => {
    for (let index = daily.length - 1; index >= 0; index -= 1) {
      if (daily[index].date <= date) {
        return index;
      }
    }

    return -1;
  };

  const findWeeklyRsi = (lookup, daily, date) => {
    const index = findDailyIndexOnOrBefore(daily, date);
    if (index < 0) {
      return null;
    }

    for (let cursor = index; cursor >= 0; cursor -= 1) {
      const weekStart = PsychologyEngine.getWeekStart(daily[cursor].date);
      if (lookup.has(weekStart)) {
        return lookup.get(weekStart);
      }
    }

    return null;
  };

  const detectRecentCross = (ema50, ema200, index, lookbackDays) => {
    const start = Math.max(1, index - lookbackDays);
    let golden = false;
    let death = false;

    for (let cursor = start; cursor <= index; cursor += 1) {
      if (ema50[cursor] === null || ema200[cursor] === null
        || ema50[cursor - 1] === null || ema200[cursor - 1] === null) {
        continue;
      }

      const wasBelow = ema50[cursor - 1] <= ema200[cursor - 1];
      const isAbove = ema50[cursor] > ema200[cursor];
      const wasAbove = ema50[cursor - 1] >= ema200[cursor - 1];
      const isBelow = ema50[cursor] < ema200[cursor];

      if (wasBelow && isAbove) {
        golden = true;
      }

      if (wasAbove && isBelow) {
        death = true;
      }
    }

    return { goldenCrossRecent: golden, deathCrossRecent: death };
  };

  const buildContext = (daily, ema50, ema200, weeklyRsiLookup, date) => {
    const index = findDailyIndexOnOrBefore(daily, date);

    if (index < EMA_SLOW - 1 || ema50[index] === null || ema200[index] === null) {
      return { ready: false };
    }

    const close = getClose(daily[index]);
    const fast = ema50[index];
    const slow = ema200[index];
    const aboveEma50 = close > fast;
    const aboveEma200 = close > slow;
    const aboveBoth = aboveEma50 && aboveEma200;
    const belowEma50 = close < fast;
    const belowEma200 = close < slow;

    const trendStart = Math.max(0, index - TREND_LOOKBACK_DAYS);
    const startPrice = getClose(daily[trendStart]);
    const trendPct = startPrice > 0 ? (close - startPrice) / startPrice : 0;
    const emaSlope = ema50[trendStart] > 0
      ? (fast - ema50[trendStart]) / ema50[trendStart]
      : 0;

    const trendUp = trendPct > TREND_THRESHOLD || emaSlope > EMA_SLOPE_THRESHOLD;
    const trendDown = trendPct < -TREND_THRESHOLD || emaSlope < -EMA_SLOPE_THRESHOLD;

    const drawdownStart = Math.max(0, index - DRAWDOWN_LOOKBACK_DAYS);
    let peak = 0;
    for (let cursor = drawdownStart; cursor <= index; cursor += 1) {
      peak = Math.max(peak, getClose(daily[cursor]));
    }

    const drawdown = peak > 0 ? (close - peak) / peak : 0;
    const crosses = detectRecentCross(ema50, ema200, index, GOLDEN_CROSS_LOOKBACK_DAYS);
    const rsiWeekly = findWeeklyRsi(weeklyRsiLookup, daily, date);

    return {
      ready: true,
      close,
      ema50: fast,
      ema200: slow,
      aboveEma50,
      aboveEma200,
      aboveBoth,
      belowEma50,
      belowEma200,
      betweenAccumulation: aboveEma50 && belowEma200,
      betweenDistribution: belowEma50 && aboveEma200,
      trendUp,
      trendDown,
      trendPct,
      emaSlope,
      drawdown,
      rsiWeekly,
      ...crosses
    };
  };

  const classifyEmaRegime = (context) => {
    if (!context.ready) {
      return "unknown";
    }

    if (context.belowEma50 && context.belowEma200 && context.trendDown) {
      return "strong_bear";
    }

    if (context.aboveBoth && context.trendUp && !context.trendDown) {
      return "strong_bull";
    }

    if (context.betweenAccumulation || context.goldenCrossRecent) {
      return "accumulation";
    }

    if (context.betweenDistribution || context.deathCrossRecent) {
      return "distribution";
    }

    if (context.aboveBoth) {
      return "strong_bull";
    }

    if (context.belowEma50 && context.belowEma200) {
      return "strong_bear";
    }

    if (context.trendUp && !context.trendDown) {
      return "accumulation";
    }

    if (context.trendDown && !context.trendUp) {
      return "distribution";
    }

    return "neutral";
  };

  const resolvePolarity = (regime) => {
    switch (regime) {
      case "strong_bull":
        return { allowPositive: true, allowNegative: false, soft: false };
      case "strong_bear":
        return { allowPositive: false, allowNegative: true, soft: false };
      case "accumulation":
        return { allowPositive: true, allowNegative: false, soft: true };
      case "distribution":
        return { allowPositive: false, allowNegative: true, soft: true };
      default:
        return { allowPositive: true, allowNegative: true, soft: true };
    }
  };

  const pickWaveZone = (waveId, regime, macroRegime) => {
    if (regime === "accumulation") {
      return WAVE_ACCUMULATION[waveId] || "Disbelief";
    }

    if (regime === "distribution") {
      return WAVE_DISTRIBUTION[waveId] || "Anxiety";
    }

    const table = macroRegime === "bear" ? WAVE_BEAR : WAVE_BULL;
    return table[waveId] || "Observing";
  };

  const zoneAllowed = (zone, polarity) => {
    if (zone === "Observing") {
      return true;
    }

    const positive = POSITIVE_ZONES.has(zone);
    const negative = NEGATIVE_ZONES.has(zone);

    if (polarity.allowPositive && positive) {
      return true;
    }

    if (polarity.allowNegative && negative) {
      return true;
    }

    if (!polarity.soft) {
      return false;
    }

    if (polarity.allowPositive && !polarity.allowNegative && negative) {
      return false;
    }

    if (polarity.allowNegative && !polarity.allowPositive && positive) {
      return false;
    }

    return true;
  };

  const applyRsiGate = (zone, context, elliottConfidence) => {
    if (context.rsiWeekly === null || elliottConfidence >= LOW_CONFIDENCE_THRESHOLD) {
      return zone;
    }

    if (context.rsiWeekly >= 70 && POSITIVE_ZONES.has(zone)) {
      return zone === "Euphoria" || zone === "Belief" ? "Complacency" : zone;
    }

    if (context.rsiWeekly <= 30 && context.drawdown <= -0.20) {
      if (zone === "Panic" || zone === "Anxiety") {
        return "Disbelief";
      }

      if (zone === "Capitulation") {
        return "Disbelief";
      }
    }

    return zone;
  };

  const resolveZone = (waveId, prevZone, context, options = {}) => {
    const {
      elliottZone = null,
      macroRegime = "bull",
      elliottConfidence = 50
    } = options;

    if (!context.ready) {
      return { zone: "Observing", weight: 0, confidence: 0 };
    }

    const regime = classifyEmaRegime(context);
    const polarity = resolvePolarity(regime);

    if (prevZone === "Panic" && context.belowEma50 && !context.trendUp) {
      return {
        zone: "Capitulation",
        weight: 22,
        confidence: elliottConfidence
      };
    }

    if (context.drawdown <= -0.35 && context.belowEma50 && context.trendDown) {
      return {
        zone: prevZone === "Panic" ? "Capitulation" : "Panic",
        weight: 20,
        confidence: elliottConfidence
      };
    }

    if (context.goldenCrossRecent && (waveId === "1" || waveId === "2")) {
      return {
        zone: macroRegime === "bear" ? "Disbelief" : "Hope",
        weight: 18,
        confidence: elliottConfidence
      };
    }

    let zone = pickWaveZone(waveId, regime, macroRegime);

    if (polarity.soft && elliottZone && zoneAllowed(elliottZone, polarity)) {
      zone = elliottZone;
    } else if (!zoneAllowed(zone, polarity)) {
      if (polarity.allowPositive && !polarity.allowNegative) {
        zone = POSITIVE_ZONES.has(zone) ? zone : "Hope";
      } else if (polarity.allowNegative && !polarity.allowPositive) {
        zone = NEGATIVE_ZONES.has(zone) ? zone : "Anxiety";
      } else if (elliottZone && zoneAllowed(elliottZone, polarity)) {
        zone = elliottZone;
      } else {
        zone = "Observing";
      }
    }

    zone = applyRsiGate(zone, context, elliottConfidence);

    let confidence = elliottConfidence;
    if (regime === "neutral") {
      confidence = Math.min(confidence, 52);
    }

    if (confidence < LOW_CONFIDENCE_THRESHOLD && regime === "neutral" && zone !== "Observing") {
      if (!elliottZone || !zoneAllowed(elliottZone, polarity)) {
        zone = "Observing";
        confidence = Math.min(confidence, 48);
      }
    }

    return {
      zone,
      weight: 18,
      confidence: Math.round(confidence)
    };
  };

  const formatEmaLabel = (context, regime) => {
    if (!context.ready) {
      return "EMA · chờ đủ dữ liệu";
    }

    const labels = {
      strong_bull: "bull mạnh",
      strong_bear: "bear mạnh",
      accumulation: "tích lũy",
      distribution: "phân phối",
      neutral: "trung lập"
    };

    const position = context.aboveBoth
      ? "trên EMA50/200"
      : context.belowEma50 && context.belowEma200
        ? "dưới EMA50/200"
        : context.betweenAccumulation
          ? "trên EMA50 · dưới EMA200"
          : context.betweenDistribution
            ? "dưới EMA50 · trên EMA200"
            : "giữa EMA";
    const trend = context.trendUp ? "tăng" : context.trendDown ? "giảm" : "ngang";
    const dd = context.drawdown <= -0.20
      ? ` · DD ${Math.round(context.drawdown * 100)}%`
      : "";

    return `EMA · ${labels[regime] || "—"} · ${position} · ${trend}${dd}`;
  };

  const getWeeklyCheckpoints = (daily, startDate, endDate) => {
    const byWeek = new Map();

    daily
      .filter((point) => point.date >= startDate && point.date <= endDate)
      .forEach((point) => {
        byWeek.set(PsychologyEngine.getWeekStart(point.date), point.date);
      });

    return [...byWeek.values()].sort((left, right) => left.localeCompare(right));
  };

  const splitRegionByEmaRegime = (region, daily, ema50, ema200, weeklyRsiLookup) => {
    const checkpoints = getWeeklyCheckpoints(daily, region.startDate, region.endDate);

    if (checkpoints.length <= 1) {
      return [region];
    }

    const segments = [];
    let segmentStart = region.startDate;
    let activeRegime = null;
    let pendingRegime = null;
    let pendingWeeks = 0;

    checkpoints.forEach((date, index) => {
      const context = buildContext(daily, ema50, ema200, weeklyRsiLookup, date);
      const regime = classifyEmaRegime(context);

      if (regime === "unknown") {
        return;
      }

      if (activeRegime === null) {
        activeRegime = regime;
        return;
      }

      if (regime === activeRegime) {
        pendingRegime = null;
        pendingWeeks = 0;
        return;
      }

      if (regime === pendingRegime) {
        pendingWeeks += 1;
      } else {
        pendingRegime = regime;
        pendingWeeks = 1;
      }

      if (pendingWeeks >= REGIME_CONFIRM_WEEKS) {
        const prevDate = checkpoints[index - 1] || date;
        segments.push({
          ...region,
          startDate: segmentStart,
          endDate: prevDate
        });
        segmentStart = date;
        activeRegime = pendingRegime;
        pendingRegime = null;
        pendingWeeks = 0;
      }
    });

    segments.push({
      ...region,
      startDate: segmentStart,
      endDate: region.endDate
    });

    return segments.filter((segment) => segment.startDate <= segment.endDate);
  };

  const applyEmaRulesToRegions = (regions, daily) => {
    const ema50 = computeEmaSeries(daily, EMA_FAST);
    const ema200 = computeEmaSeries(daily, EMA_SLOW);
    const weeklyRsiLookup = buildWeeklyRsiLookup(daily);
    let prevZone = null;
    const output = [];

    regions.forEach((region) => {
      const pieces = splitRegionByEmaRegime(region, daily, ema50, ema200, weeklyRsiLookup);

      pieces.forEach((piece) => {
        const context = buildContext(daily, ema50, ema200, weeklyRsiLookup, piece.endDate);
        const regime = classifyEmaRegime(context);
        const psych = resolveZone(piece.waveId, prevZone, context, {
          elliottZone: piece.zone,
          macroRegime: piece.macroRegime || "bull",
          elliottConfidence: piece.confidence ?? 50
        });
        prevZone = psych.zone;

        output.push({
          ...piece,
          zone: psych.zone,
          confidence: psych.confidence ?? piece.confidence ?? 50,
          lowConfidence: (psych.confidence ?? piece.confidence ?? 50) < LOW_CONFIDENCE_THRESHOLD,
          elliottLabel: piece.elliottLabel
            ? `${piece.elliottLabel} · ${formatEmaLabel(context, regime)}`
            : formatEmaLabel(context, regime),
          emaContext: {
            regime,
            aboveBoth: context.aboveBoth,
            belowEma50: context.belowEma50,
            belowEma200: context.belowEma200,
            trendUp: context.trendUp,
            trendDown: context.trendDown,
            drawdown: context.drawdown,
            rsiWeekly: context.rsiWeekly,
            ema50: context.ema50,
            ema200: context.ema200
          }
        });
      });
    });

    return output;
  };

  const buildPsychologyCache = (fullSeries) => {
    const base = PsychologyEngine.buildPsychologyCache(fullSeries, { model: "elliott" });

    if (!base) {
      return null;
    }

    const daily = PsychologyEngine.aggregateSeries(fullSeries, "1D")
      .slice(-PsychologyEngine.TEN_YEAR_DAYS);
    const regions = applyEmaRulesToRegions(base.regions, daily);
    const latestRegion = ElliottEngine.findRegionForDate(regions, base.rangeEnd);

    return {
      ...base,
      model: "ema",
      regionCount: regions.length,
      regions,
      summary: {
        ...PsychologyEngine.getSummaryFromRegion(latestRegion),
        emaLabel: latestRegion?.emaContext
          ? formatEmaLabel(
            buildContext(
              daily,
              computeEmaSeries(daily, EMA_FAST),
              computeEmaSeries(daily, EMA_SLOW),
              buildWeeklyRsiLookup(daily),
              base.rangeEnd
            ),
            latestRegion.emaContext.regime
          )
          : null
      }
    };
  };

  const validateRegionRules = (region, context) => {
    if (!context?.ready || region.zone === "Observing") {
      return true;
    }

    const regime = classifyEmaRegime(context);
    const polarity = resolvePolarity(regime);
    const isPositive = POSITIVE_ZONES.has(region.zone);
    const isNegative = NEGATIVE_ZONES.has(region.zone);

    if (!polarity.soft) {
      if (polarity.allowPositive && !polarity.allowNegative && isNegative) {
        return false;
      }

      if (polarity.allowNegative && !polarity.allowPositive && isPositive) {
        return false;
      }
    }

    if (regime === "strong_bear" && isPositive) {
      return false;
    }

    if (regime === "strong_bull" && isNegative) {
      return false;
    }

    return true;
  };

  return {
    EMA_FAST,
    EMA_SLOW,
    LOW_CONFIDENCE_THRESHOLD,
    POSITIVE_ZONES,
    NEGATIVE_ZONES,
    computeEmaSeries,
    buildContext,
    classifyEmaRegime,
    resolveZone,
    splitRegionByEmaRegime,
    applyEmaRulesToRegions,
    buildPsychologyCache,
    validateRegionRules
  };
})();
