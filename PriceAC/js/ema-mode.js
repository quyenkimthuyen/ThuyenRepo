/* EMA 50/200 psychology mode: trend + EMA position gate bullish/bearish zones. */
var EmaPsychologyEngine = (() => {
  const EMA_FAST = 50;
  const EMA_SLOW = 200;
  const TREND_LOOKBACK_DAYS = 20;
  const TREND_THRESHOLD = 0.01;
  const EMA_SLOPE_THRESHOLD = 0.004;

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

  const WAVE_POSITIVE = {
    1: "Hope",
    2: "Optimism",
    3: "Belief",
    4: "Complacency",
    5: "Euphoria"
  };

  const WAVE_NEGATIVE = {
    1: "Disbelief",
    2: "Denial",
    3: "Panic",
    4: "Anxiety",
    5: "Denial",
    A: "Anxiety",
    B: "Denial",
    C: "Panic"
  };

  const getClose = (point) => point.close ?? point.price;

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

  const findDailyIndexOnOrBefore = (daily, date) => {
    for (let index = daily.length - 1; index >= 0; index -= 1) {
      if (daily[index].date <= date) {
        return index;
      }
    }

    return -1;
  };

  const buildContext = (daily, ema50, ema200, date) => {
    const index = findDailyIndexOnOrBefore(daily, date);

    if (index < EMA_SLOW - 1 || ema50[index] === null || ema200[index] === null) {
      return {
        ready: false,
        aboveBoth: false,
        belowEma50: false,
        trendUp: false,
        trendDown: false
      };
    }

    const close = getClose(daily[index]);
    const fast = ema50[index];
    const slow = ema200[index];
    const aboveEma50 = close > fast;
    const aboveEma200 = close > slow;
    const aboveBoth = aboveEma50 && aboveEma200;
    const belowEma50 = close < fast;

    const trendStart = Math.max(0, index - TREND_LOOKBACK_DAYS);
    const startPrice = getClose(daily[trendStart]);
    const trendPct = startPrice > 0 ? (close - startPrice) / startPrice : 0;
    const emaSlope = ema50[trendStart] > 0
      ? (fast - ema50[trendStart]) / ema50[trendStart]
      : 0;

    const trendUp = trendPct > TREND_THRESHOLD || emaSlope > EMA_SLOPE_THRESHOLD;
    const trendDown = trendPct < -TREND_THRESHOLD || emaSlope < -EMA_SLOPE_THRESHOLD;

    return {
      ready: true,
      close,
      ema50: fast,
      ema200: slow,
      aboveEma50,
      aboveEma200,
      aboveBoth,
      belowEma50,
      trendUp,
      trendDown,
      trendPct,
      emaSlope
    };
  };

  const defaultPositive = () => "Hope";
  const defaultNegative = () => "Anxiety";

  const clampZone = (zone, allowPositive, allowNegative) => {
    if (allowPositive && !allowNegative) {
      return POSITIVE_ZONES.has(zone) ? zone : defaultPositive();
    }

    if (allowNegative && !allowPositive) {
      return NEGATIVE_ZONES.has(zone) ? zone : defaultNegative();
    }

    return zone;
  };

  const resolvePolarity = (context) => {
    if (!context.ready) {
      return { allowPositive: false, allowNegative: false };
    }

    if (context.belowEma50) {
      return { allowPositive: false, allowNegative: true };
    }

    if (context.aboveBoth && context.trendUp && !context.trendDown) {
      return { allowPositive: true, allowNegative: false };
    }

    if (context.trendUp && !context.trendDown) {
      return { allowPositive: true, allowNegative: false };
    }

    if (context.trendDown && !context.trendUp) {
      return { allowPositive: false, allowNegative: true };
    }

    if (context.aboveBoth) {
      return { allowPositive: true, allowNegative: false };
    }

    return { allowPositive: false, allowNegative: false };
  };

  const resolveZone = (waveId, prevZone, context) => {
    if (!context.ready) {
      return { zone: "Observing", weight: 0 };
    }

    if (prevZone === "Panic" && context.belowEma50 && !context.trendUp) {
      return { zone: "Capitulation", weight: 22 };
    }

    const { allowPositive, allowNegative } = resolvePolarity(context);

    if (!allowPositive && !allowNegative) {
      return { zone: "Observing", weight: 0 };
    }

    let base;

    if (allowPositive && !allowNegative) {
      base = WAVE_POSITIVE[waveId] || defaultPositive();
    } else if (allowNegative && !allowPositive) {
      base = WAVE_NEGATIVE[waveId] || defaultNegative();
    } else {
      base = context.belowEma50
        ? (WAVE_NEGATIVE[waveId] || defaultNegative())
        : (WAVE_POSITIVE[waveId] || defaultPositive());
    }

    return {
      zone: clampZone(base, allowPositive, allowNegative),
      weight: 18
    };
  };

  const formatEmaLabel = (context) => {
    if (!context.ready) {
      return "EMA · chờ đủ dữ liệu";
    }

    const position = context.aboveBoth
      ? "trên EMA50/200"
      : context.belowEma50
        ? "dưới EMA50"
        : "giữa EMA50–200";
    const trend = context.trendUp ? "xu hướng tăng" : context.trendDown ? "xu hướng giảm" : "đi ngang";

    return `EMA · ${position} · ${trend}`;
  };

  const applyEmaRulesToRegions = (regions, daily) => {
    const ema50 = computeEmaSeries(daily, EMA_FAST);
    const ema200 = computeEmaSeries(daily, EMA_SLOW);
    let prevZone = null;

    return regions.map((region) => {
      const context = buildContext(daily, ema50, ema200, region.endDate);
      const psych = resolveZone(region.waveId, prevZone, context);
      prevZone = psych.zone;

      return {
        ...region,
        zone: psych.zone,
        elliottLabel: region.elliottLabel
          ? `${region.elliottLabel} · ${formatEmaLabel(context)}`
          : formatEmaLabel(context),
        emaContext: {
          aboveBoth: context.aboveBoth,
          belowEma50: context.belowEma50,
          trendUp: context.trendUp,
          trendDown: context.trendDown,
          ema50: context.ema50,
          ema200: context.ema200
        }
      };
    });
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
          ? formatEmaLabel(latestRegion.emaContext)
          : null
      }
    };
  };

  const validateRegionRules = (region, context) => {
    if (!context?.ready || region.zone === "Observing") {
      return true;
    }

    const isPositive = POSITIVE_ZONES.has(region.zone);
    const isNegative = NEGATIVE_ZONES.has(region.zone);

    if (context.belowEma50 && isPositive) {
      return false;
    }

    if (context.aboveBoth && isNegative) {
      return false;
    }

    if (context.trendUp && !context.trendDown && isNegative) {
      return false;
    }

    if (context.trendDown && !context.trendUp && isPositive) {
      return false;
    }

    return true;
  };

  return {
    EMA_FAST,
    EMA_SLOW,
    POSITIVE_ZONES,
    NEGATIVE_ZONES,
    computeEmaSeries,
    buildContext,
    resolveZone,
    applyEmaRulesToRegions,
    buildPsychologyCache,
    validateRegionRules
  };
})();
