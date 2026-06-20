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
      2: { zone: "Anxiety", weight: 16 },
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
      4: { zone: "Anger", weight: 12 },
      5: { zone: "Capitulation", weight: 22 },
      A: { zone: "Hope", weight: 14 },
      B: { zone: "Disbelief", weight: 16 },
      C: { zone: "Optimism", weight: 12 }
    }
  };

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

  const BULLISH_ZONES = new Set([
    "Hope",
    "Optimism",
    "Belief",
    "Thrill",
    "Euphoria",
    "Complacency"
  ]);

  const DOWN_LEG_BULLISH_REMAP = {
    Hope: "Disbelief",
    Optimism: "Denial",
    Belief: "Panic",
    Thrill: "Anxiety",
    Euphoria: "Capitulation",
    Complacency: "Denial"
  };

  const UP_LEG_BEARISH_REMAP = {
    Panic: "Denial",
    Capitulation: "Disbelief",
    Depression: "Hope",
    Anger: "Denial",
    Anxiety: "Denial"
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
    const lookbackWeeks = 78;
    const startIndex = Math.max(0, index - lookbackWeeks);
    const start = getClose(weeklySeries[startIndex]);
    const last = getClose(weeklySeries[index]);
    const recentWindow = weeklySeries.slice(Math.max(0, index - 51), index + 1);
    const recentHigh = recentWindow.length
      ? Math.max(...recentWindow.map(getClose))
      : last;
    const drawdownFromHigh = recentHigh > 0 ? (last - recentHigh) / recentHigh : 0;

    if (drawdownFromHigh <= -0.18) {
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

  const alignPsychologyToLeg = (direction, waveId, legUp, psych) => {
    if (!psych?.zone) {
      return psych;
    }

    const shouldBeUp = isImpulseUpLeg(direction, waveId);
    if (legUp === shouldBeUp) {
      return psych;
    }

    if (!legUp && BULLISH_ZONES.has(psych.zone)) {
      return {
        ...psych,
        zone: DOWN_LEG_BULLISH_REMAP[psych.zone] || "Anxiety"
      };
    }

    if (legUp && UP_LEG_BEARISH_REMAP[psych.zone]) {
      return {
        ...psych,
        zone: UP_LEG_BEARISH_REMAP[psych.zone]
      };
    }

    return psych;
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
      const legUp = chain[index + 1].price > chain[index].price;
      const psych = alignPsychologyToLeg(
        direction,
        waveId,
        legUp,
        WAVE_PSYCHOLOGY[direction][waveId]
      );

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
