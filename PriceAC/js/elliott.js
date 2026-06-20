/* Elliott Wave on weekly candles: swing detection and psychology regions. */
var ElliottEngine = (() => {
  const WAVE_LABELS_VI = {
    1: "Sóng 1",
    2: "Sóng 2",
    3: "Sóng 3",
    4: "Sóng 4",
    5: "Sóng 5",
    A: "Sóng A",
    B: "Sóng B",
    C: "Sóng C"
  };

  const WAVE_PSYCHOLOGY = {
    bull: {
      1: { zone: "Hope", weight: 18 },
      2: { zone: "Optimism", weight: 16 },
      3: { zone: "Belief", weight: 22 },
      4: { zone: "Complacency", weight: 16 },
      5: { zone: "Euphoria", weight: 20 },
      A: { zone: "Anxiety", weight: 14 },
      B: { zone: "Denial", weight: 16 },
      C: { zone: "Panic", weight: 18 }
    },
    bear: {
      1: { zone: "Anxiety", weight: 14 },
      2: { zone: "Denial", weight: 16 },
      3: { zone: "Panic", weight: 20 },
      4: { zone: "Anxiety", weight: 12 },
      5: { zone: "Capitulation", weight: 22 },
      A: { zone: "Anxiety", weight: 14 },
      B: { zone: "Denial", weight: 16 },
      C: { zone: "Capitulation", weight: 22 }
    }
  };

  // Quy luật chu trình tâm lý thị trường (theo thứ tự):
  // Đi ngang → Nghi ngờ → Hy vọng → Lạc quan → Niềm tin → Hưng phấn cực độ
  // → Chủ quan → Lo âu → Phủ nhận → Hoảng loạn → Bỏ cuộc (đáy cực đoan)
  const PSYCHOLOGY_CYCLE_LAW = [
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

  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

  const getClose = (point) => point.close ?? point.price;

  const detectSwings = (series, deviationPct = 8) => {
    if (!series || series.length < 3) {
      return [];
    }

    const threshold = Math.max(deviationPct, 5) / 100;
    const swings = [];
    let direction = "seekHigh";
    let extreme = {
      index: 0,
      date: series[0].date,
      price: getClose(series[0]),
      type: "low"
    };

    for (let index = 1; index < series.length; index += 1) {
      const price = getClose(series[index]);

      if (direction === "seekHigh") {
        if (price >= extreme.price) {
          extreme = { index, date: series[index].date, price, type: "high" };
          continue;
        }

        if ((extreme.price - price) / extreme.price >= threshold) {
          swings.push({ ...extreme });
          extreme = { index, date: series[index].date, price, type: "low" };
          direction = "seekLow";
        }

        continue;
      }

      if (price <= extreme.price) {
        extreme = { index, date: series[index].date, price, type: "low" };
        continue;
      }

      if ((price - extreme.price) / extreme.price >= threshold) {
        swings.push({ ...extreme });
        extreme = { index, date: series[index].date, price, type: "high" };
        direction = "seekHigh";
      }
    }

    return swings;
  };

  const legSize = (fromPivot, toPivot) => Math.abs(toPivot.price - fromPivot.price);

  const retraceRatio = (priorLeg, correctionLeg) => {
    if (!priorLeg) {
      return 0;
    }

    return correctionLeg / priorLeg;
  };

  const inferCycle = (pivots) => {
    if (pivots.length < 4) {
      return null;
    }

    const candidates = [];

    for (let start = Math.max(0, pivots.length - 8); start < pivots.length - 3; start += 1) {
      const slice = pivots.slice(start);
      const direction = slice[0].type === "low" ? "bull" : "bear";
      const legs = [];

      for (let index = 1; index < slice.length; index += 1) {
        legs.push(legSize(slice[index - 1], slice[index]));
      }

      if (legs.length < 3) {
        continue;
      }

      let score = 12;
      const impulseLegs = [legs[0], legs[2], legs[4]].filter(Boolean);

      if (impulseLegs.length >= 2 && legs[1]) {
        const wave2Retrace = retraceRatio(legs[0], legs[1]);
        if (wave2Retrace > 0.12 && wave2Retrace < 0.78) {
          score += 10;
        }
      }

      if (impulseLegs.length === 3) {
        const shortest = Math.min(...impulseLegs);
        const longest = Math.max(...impulseLegs);
        if (impulseLegs[1] !== shortest) {
          score += 12;
        }
        if (longest === impulseLegs[1]) {
          score += 10;
        }
      }

      if (slice.length >= 5) {
        score += 8;
      }

      candidates.push({
        start,
        pivots: slice,
        direction,
        score
      });
    }

    candidates.sort((left, right) => right.score - left.score);
    return candidates[0] || null;
  };

  const buildWeeklyDeviation = (weeklySeries) => {
    if (weeklySeries.length < 4) {
      return 8;
    }

    let total = 0;
    let count = 0;
    const end = weeklySeries.length - 1;
    const start = Math.max(1, end - 25);

    for (let index = start; index <= end; index += 1) {
      const previous = getClose(weeklySeries[index - 1]);
      if (!previous) {
        continue;
      }

      total += Math.abs((getClose(weeklySeries[index]) - previous) / previous) * 100;
      count += 1;
    }

    const average = count ? total / count : 6;
    return clamp(average * 2.2, 6, 20);
  };

  const WAVE_SEQUENCE = ["1", "2", "3", "4", "5", "A", "B", "C"];

  // Ngưỡng regime/capitulation hiệu chỉnh trên dữ liệu tuần Bitcoin (tài sản tham chiếu).
  const REGIME_LOOKBACK_WEEKS = 78;
  const REGIME_BEAR_DRAWDOWN = -0.18;
  const CAPITULATION_MIN_DRAWDOWN = -0.25;

  const BULLISH_ZONES = new Set([
    "Hope",
    "Optimism",
    "Belief",
    "Euphoria"
  ]);

  const measureLeg = (weeklySeries, chain, index) => {
    const start = chain[index];
    const end = chain[index + 1];
    const startIdx = start.index ?? 0;
    const endIdx = end.index ?? weeklySeries.length - 1;
    const startPrice = start.price;
    const endPrice = end.price;
    const legChange = startPrice > 0 ? (endPrice - startPrice) / startPrice : 0;
    const slice = weeklySeries.slice(startIdx, endIdx + 1);
    const lows = slice.map((point) => point.low ?? getClose(point));
    const highs = slice.map((point) => point.high ?? getClose(point));
    const minPrice = lows.length ? Math.min(...lows) : Math.min(startPrice, endPrice);
    const maxPrice = highs.length ? Math.max(...highs) : Math.max(startPrice, endPrice);
    const rangePct = minPrice > 0 ? ((maxPrice - minPrice) / minPrice) * 100 : 0;
    const prevLeg = index > 0 ? Math.abs(chain[index].price - chain[index - 1].price) : 0;
    const legSize = Math.abs(endPrice - startPrice);
    const strongLeg = prevLeg > 0 ? legSize / prevLeg >= 1.12 : legSize > 0 && rangePct >= 12;
    const legLow = Math.min(startPrice, endPrice, minPrice);
    const recoveryFromLow = legLow > 0 ? (endPrice - legLow) / legLow : 0;
    const hasRecovery = legChange < -0.008 && recoveryFromLow >= 0.03;
    const sideways = Math.abs(legChange) < 0.03 && rangePct < 8 && slice.length >= 6;

    return {
      legUp: legChange > 0.008,
      legDown: legChange < -0.008,
      legFlat: Math.abs(legChange) <= 0.008,
      legChange,
      strongLeg,
      hasRecovery,
      sideways,
      rangePct,
      durationWeeks: slice.length,
      endIndex: endIdx
    };
  };

  const isCapitulationLeg = (weeklySeries, leg, regime) => {
    if (!leg.legDown) {
      return false;
    }

    const endIdx = leg.endIndex ?? weeklySeries.length - 1;
    const recentWindow = weeklySeries.slice(Math.max(0, endIdx - 51), endIdx + 1);
    const recentHigh = recentWindow.length
      ? Math.max(...recentWindow.map(getClose))
      : getClose(weeklySeries[endIdx]);
    const last = getClose(weeklySeries[endIdx]);
    const drawdownFromHigh = recentHigh > 0 ? (last - recentHigh) / recentHigh : 0;

    if (drawdownFromHigh > -0.20 && regime !== "bear") {
      return false;
    }

    return (
      leg.legChange <= -0.18
      || (drawdownFromHigh <= -0.40 && leg.legChange <= -0.08)
      || (drawdownFromHigh <= -0.30 && leg.strongLeg && leg.legChange <= -0.10)
      || (regime === "bear" && drawdownFromHigh <= CAPITULATION_MIN_DRAWDOWN && leg.legChange <= -0.12)
    );
  };

  const resolveDeclinePsychology = (waveId, leg, capitulation) => {
    if (capitulation) {
      return { zone: "Capitulation", weight: 22 };
    }

    if (leg.strongLeg || waveId === "3" || waveId === "5" || waveId === "C") {
      return { zone: "Panic", weight: 20 };
    }

    if (waveId === "2" || waveId === "B") {
      return { zone: "Denial", weight: 16 };
    }

    return { zone: "Anxiety", weight: 14 };
  };

  const resolveBearPsychology = (weeklySeries, waveId, leg) => {
    if (leg.sideways || leg.legFlat) {
      return { zone: "Disbelief", weight: 14 };
    }

    if (leg.legUp) {
      return { zone: "Denial", weight: 16 };
    }

    return resolveDeclinePsychology(waveId, leg, isCapitulationLeg(weeklySeries, leg, "bear"));
  };

  const resolveBullPsychology = (weeklySeries, waveId, leg, regime) => {
    if (waveId === "1" && leg.legUp) {
      return { zone: "Hope", weight: 18 };
    }

    if (waveId === "2") {
      return { zone: "Optimism", weight: 16 };
    }

    if (waveId === "3" && leg.legUp) {
      return { zone: "Belief", weight: 22 };
    }

    if (waveId === "4" && leg.legDown) {
      return { zone: "Complacency", weight: 16 };
    }

    if (waveId === "5" && leg.legUp) {
      return {
        zone: "Euphoria",
        weight: leg.strongLeg ? 22 : 20
      };
    }

    if (waveId === "A" && leg.legDown) {
      return { zone: "Anxiety", weight: 14 };
    }

    if (waveId === "B") {
      return { zone: "Denial", weight: 16 };
    }

    if (waveId === "C" && leg.legDown) {
      if (isCapitulationLeg(weeklySeries, leg, regime)) {
        return { zone: "Capitulation", weight: 22 };
      }

      return {
        zone: "Panic",
        weight: leg.strongLeg ? 22 : 18
      };
    }

    if (leg.legDown) {
      if (isCapitulationLeg(weeklySeries, leg, regime)) {
        return { zone: "Capitulation", weight: 22 };
      }

      if (leg.strongLeg) {
        return { zone: "Panic", weight: 18 };
      }

      return {
        zone: leg.hasRecovery ? "Complacency" : "Anxiety",
        weight: 14
      };
    }

    if (leg.legUp) {
      return {
        zone: leg.strongLeg ? "Euphoria" : "Hope",
        weight: 16
      };
    }

    return { zone: "Disbelief", weight: 12 };
  };

  const resolvePsychologyFromLaw = (weeklySeries, chain, index, regime) => {
    const waveId = WAVE_SEQUENCE[index % WAVE_SEQUENCE.length];
    const leg = measureLeg(weeklySeries, chain, index);

    if (leg.sideways || (index === 0 && leg.durationWeeks >= 8 && Math.abs(leg.legChange) < 0.06)) {
      return { zone: "Disbelief", weight: 16 };
    }

    if (regime === "bear") {
      return resolveBearPsychology(weeklySeries, waveId, leg);
    }

    return resolveBullPsychology(weeklySeries, waveId, leg, regime);
  };

  const inferMacroDirection = (weeklySeries) => {
    if (!weeklySeries.length) {
      return "bull";
    }

    return inferRegimeAtIndex(weeklySeries, weeklySeries.length - 1);
  };

  const inferRegimeAtIndex = (weeklySeries, endIndex) => {
    if (!weeklySeries.length) {
      return "bull";
    }

    const index = clamp(endIndex, 0, weeklySeries.length - 1);
    const lookbackWeeks = REGIME_LOOKBACK_WEEKS;
    const startIndex = Math.max(0, index - lookbackWeeks);
    const start = getClose(weeklySeries[startIndex]);
    const last = getClose(weeklySeries[index]);
    const recentWindow = weeklySeries.slice(Math.max(0, index - 51), index + 1);
    const recentHigh = recentWindow.length
      ? Math.max(...recentWindow.map(getClose))
      : last;
    const drawdownFromHigh = recentHigh > 0 ? (last - recentHigh) / recentHigh : 0;

    if (drawdownFromHigh <= REGIME_BEAR_DRAWDOWN) {
      return "bear";
    }

    if (drawdownFromHigh >= -0.04 && last >= start * 1.05) {
      return "bull";
    }

    if (last >= start * 1.08) {
      return "bull";
    }

    if (last <= start * 0.92) {
      return "bear";
    }

    return last >= start ? "bull" : "bear";
  };

  const isImpulseUpLeg = (direction, waveId) => {
    if (direction === "bull") {
      return ["1", "3", "5", "B"].includes(waveId);
    }

    return ["2", "4", "B"].includes(waveId);
  };

  const buildPivotChain = (weeklySeries, swings) => {
    const lastIndex = weeklySeries.length - 1;

    if (!swings.length) {
      const macro = inferMacroDirection(weeklySeries);
      return [
        {
          index: 0,
          date: weeklySeries[0].date,
          price: getClose(weeklySeries[0]),
          type: macro === "bull" ? "low" : "high"
        },
        {
          index: lastIndex,
          date: weeklySeries[lastIndex].date,
          price: getClose(weeklySeries[lastIndex]),
          type: macro === "bull" ? "high" : "low"
        }
      ];
    }

    const chain = [];
    const firstSwing = swings[0];

    if (firstSwing.index > 0) {
      chain.push({
        index: 0,
        date: weeklySeries[0].date,
        price: getClose(weeklySeries[0]),
        type: firstSwing.type === "high" ? "low" : "high"
      });
    }

    swings.forEach((swing) => chain.push(swing));

    const lastSwing = chain[chain.length - 1];
    if (lastSwing.index < lastIndex) {
      chain.push({
        index: lastIndex,
        date: weeklySeries[lastIndex].date,
        price: getClose(weeklySeries[lastIndex]),
        type: lastSwing.type === "high" ? "low" : "high"
      });
    }

    return chain;
  };

  const scoreRegionConfidence = (chain, index) => {
    if (chain.length < 2) {
      return 50;
    }

    const legSize = Math.abs(chain[index + 1].price - chain[index].price);
    const prevLeg = index > 0 ? Math.abs(chain[index].price - chain[index - 1].price) : null;
    const waveId = WAVE_SEQUENCE[index % WAVE_SEQUENCE.length];
    let score = 56;

    if (prevLeg && prevLeg > 0) {
      const ratio = legSize / prevLeg;

      if (waveId === "2" || waveId === "4" || waveId === "B") {
        if (ratio >= 0.32 && ratio <= 0.68) {
          score += 24;
        } else if (ratio >= 0.22 && ratio <= 0.82) {
          score += 12;
        }
      } else if (ratio >= 0.75 && ratio <= 2.4) {
        score += 20;
      } else if (ratio >= 0.45 && ratio <= 3) {
        score += 8;
      }
    } else {
      score += 10;
    }

    if (chain.length >= 8) {
      score += 8;
    } else if (chain.length >= 5) {
      score += 4;
    }

    return clamp(score, 40, 94);
  };

  const buildFullCoverageRegions = (weeklySeries, swings) => {
    const seriesStart = weeklySeries[0].date;
    const seriesEnd = weeklySeries[weeklySeries.length - 1].date;
    const chain = buildPivotChain(weeklySeries, swings);
    const regions = [];

    for (let index = 0; index < chain.length - 1; index += 1) {
      const waveId = WAVE_SEQUENCE[index % WAVE_SEQUENCE.length];
      const endIndex = chain[index + 1].index ?? weeklySeries.length - 1;
      const direction = inferRegimeAtIndex(weeklySeries, endIndex);
      const directionLabel = direction === "bull" ? "tăng" : "giảm";
      const psych = resolvePsychologyFromLaw(weeklySeries, chain, index, direction);

      regions.push({
        startDate: chain[index].date,
        endDate: chain[index + 1].date,
        zone: psych.zone,
        waveId,
        elliottLabel: `${WAVE_LABELS_VI[waveId]} ${directionLabel}`,
        confidence: scoreRegionConfidence(chain, index)
      });
    }

    if (!regions.length) {
      const direction = inferMacroDirection(weeklySeries);
      const waveId = "1";
      const psych = WAVE_PSYCHOLOGY[direction][waveId];
      const directionLabel = direction === "bull" ? "tăng" : "giảm";
      return [{
        startDate: seriesStart,
        endDate: seriesEnd,
        zone: psych.zone,
        waveId,
        elliottLabel: `${WAVE_LABELS_VI[waveId]} ${directionLabel}`,
        confidence: 50
      }];
    }

    return regions;
  };

  const clipRegionsToRange = (regions, startDate, endDate) => {
    if (!regions.length) {
      return regions;
    }

    const clipped = regions
      .map((region) => ({
        ...region,
        startDate: region.startDate < startDate ? startDate : region.startDate,
        endDate: region.endDate > endDate ? endDate : region.endDate
      }))
      .filter((region) => region.startDate <= region.endDate);

    if (!clipped.length) {
      return regions;
    }

    clipped[0].startDate = startDate;
    clipped[clipped.length - 1].endDate = endDate;
    return clipped;
  };

  const findRegionForDate = (regions, date) => {
    if (!regions.length) {
      return {
        zone: "Observing",
        waveId: null,
        elliottLabel: "Chưa xác định",
        confidence: 0
      };
    }

    for (let index = regions.length - 1; index >= 0; index -= 1) {
      if (date >= regions[index].startDate && date <= regions[index].endDate) {
        return regions[index];
      }
    }

    return regions[regions.length - 1];
  };

  const buildWeeklyPsychologyModel = (weeklySeries, options = {}) => {
    const { rangeStart, rangeEnd } = options;
    const deviation = buildWeeklyDeviation(weeklySeries);
    const swings = detectSwings(weeklySeries, deviation);
    let regions = buildFullCoverageRegions(weeklySeries, swings);

    if (rangeStart && rangeEnd) {
      regions = clipRegionsToRange(regions, rangeStart, rangeEnd);
    }

    return {
      weekly: weeklySeries,
      swings,
      regions,
      deviation
    };
  };

  const analyzeAt = (series, swings, endIndex) => {
    if (!series.length || endIndex < 2) {
      return {
        waveId: null,
        label: "Chưa đủ sóng",
        psychology: null,
        confidence: 0,
        direction: "unknown"
      };
    }

    const pivots = swings.filter((swing) => swing.index <= endIndex);
    const close = getClose(series[endIndex]);
    const cycle = inferCycle(pivots);

    if (!cycle) {
      return {
        waveId: null,
        label: "Đang hình thành sóng",
        psychology: null,
        confidence: 0,
        direction: "unknown"
      };
    }

    const waveSequence = ["1", "2", "3", "4", "5", "A", "B", "C"];
    const waveId = waveSequence[Math.min(Math.max(pivots.length - 1, 0), waveSequence.length - 1)];
    const psychology = WAVE_PSYCHOLOGY[cycle.direction][waveId];

    return {
      waveId,
      direction: cycle.direction,
      psychology,
      confidence: clamp(cycle.score, 0, 100),
      label: `${WAVE_LABELS_VI[waveId]} ${cycle.direction === "bull" ? "tăng" : "giảm"}`,
      inProgress: true,
      progress: 0,
      pivotCount: pivots.length
    };
  };

  const buildSwingCache = (series, deviationPct = 8) => detectSwings(series, deviationPct);

  const legSizeAt = (chain, legIndex) => {
    if (legIndex < 0 || legIndex >= chain.length - 1) {
      return 0;
    }

    return Math.abs(chain[legIndex + 1].price - chain[legIndex].price);
  };

  const validateWaveLeg = (chain, legIndex, waveId) => {
    if (legIndex < 1 || !chain[legIndex + 1]) {
      return { elliottValidated: false, validationNote: "Chưa đủ điểm xoay" };
    }

    const leg = legSizeAt(chain, legIndex);
    const prevLeg = legSizeAt(chain, legIndex - 1);

    if (!prevLeg) {
      return { elliottValidated: false, validationNote: "Chưa đủ sóng trước" };
    }

    const ratio = leg / prevLeg;

    if (waveId === "2" || waveId === "4" || waveId === "B") {
      const ok = ratio >= 0.24 && ratio <= 0.82;
      return {
        elliottValidated: ok,
        validationNote: ok ? "Hồi sóng trong chuẩn Elliott" : "Hồi sóng ngoài biên chuẩn"
      };
    }

    if (waveId === "3") {
      const leg1 = legSizeAt(chain, 0);
      const ok = leg >= leg1 * 0.85;
      return {
        elliottValidated: ok,
        validationNote: ok ? "Sóng 3 không ngắn nhất" : "Sóng 3 yếu so với sóng 1"
      };
    }

    if (waveId === "5") {
      const leg3 = legSizeAt(chain, legIndex - 2);
      const ok = leg <= leg3 * 1.25 || leg >= leg3 * 0.7;
      return {
        elliottValidated: ok,
        validationNote: ok ? "Sóng 5 trong biên độ hợp lý" : "Sóng 5 bất thường"
      };
    }

    return {
      elliottValidated: ratio >= 0.35 && ratio <= 2.8,
      validationNote: "Cấu trúc đang kiểm tra"
    };
  };

  const formatWaveMarkerText = (waveId) => {
    if (!waveId) {
      return "";
    }

    const label = WAVE_LABELS_VI[waveId] || `Sóng ${waveId}`;
    return label.replace(/^Sóng\s+/, "");
  };

  const annotateRegionsWithValidation = (weeklySeries, regions, swings) => {
    const chain = buildPivotChain(weeklySeries, swings);

    return regions.map((region, index) => {
      const validation = validateWaveLeg(chain, index, region.waveId);

      return {
        ...region,
        elliottValidated: validation.elliottValidated,
        validationNote: validation.validationNote,
        displayLabel: region.elliottLabel
      };
    });
  };

  const buildVisibleWaveOverlay = (cache, visibleSeries, options = {}) => {
    if (!cache?.regions?.length || !visibleSeries?.length) {
      return null;
    }

    const visibleStart = visibleSeries[0].date;
    const visibleEnd = visibleSeries[visibleSeries.length - 1].date;

    const priceAt = (date) => {
      const exact = visibleSeries.find((point) => point.date === date);
      if (exact) {
        return exact.close ?? exact.price;
      }

      let last = null;
      visibleSeries.forEach((point) => {
        if (point.date <= date) {
          last = point.close ?? point.price;
        }
      });

      return last;
    };

    const overlapping = cache.regions.filter(
      (region) => region.endDate >= visibleStart && region.startDate <= visibleEnd
    );

    if (!overlapping.length) {
      return null;
    }

    const boundaryDates = new Set([visibleStart, visibleEnd]);
    overlapping.forEach((region) => {
      if (region.startDate >= visibleStart && region.startDate <= visibleEnd) {
        boundaryDates.add(region.startDate);
      }
      if (region.endDate >= visibleStart && region.endDate <= visibleEnd) {
        boundaryDates.add(region.endDate);
      }
    });

    const pivots = [...boundaryDates]
      .sort((left, right) => left.localeCompare(right))
      .map((date) => ({
        date,
        price: priceAt(date),
        region: findRegionForDate(cache.regions, date)
      }))
      .filter((point) => Number.isFinite(point.price));

    if (pivots.length < 2) {
      return null;
    }

    const points = pivots.map((point) => ({
      time: point.date,
      value: point.price
    }));

    const markers = overlapping
      .filter((region) => region.startDate >= visibleStart && region.startDate <= visibleEnd && region.waveId)
      .filter((region) => !options.validatedOnly || region.elliottValidated)
      .map((region, index, regions) => {
        const price = priceAt(region.startDate);
        const prevPrice = index > 0 ? priceAt(regions[index - 1].startDate) : price;

        return {
          time: region.startDate,
          position: price >= prevPrice ? "belowBar" : "aboveBar",
          color: region.elliottValidated === false ? "rgba(240, 180, 92, 0.55)" : "#f0b45c",
          shape: "circle",
          text: formatWaveMarkerText(region.waveId)
        };
      });

    return { points, markers, pivots };
  };

  return {
    WAVE_LABELS_VI,
    WAVE_PSYCHOLOGY,
    PSYCHOLOGY_CYCLE_LAW,
    detectSwings,
    buildSwingCache,
    buildWeeklyDeviation,
    buildFullCoverageRegions,
    clipRegionsToRange,
    findRegionForDate,
    buildWeeklyPsychologyModel,
    analyzeAt,
    buildVisibleWaveOverlay,
    annotateRegionsWithValidation,
    validateWaveLeg,
    formatWaveMarkerText
  };
})();
