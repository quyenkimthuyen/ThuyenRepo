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
      1: { zone: "Disbelief", weight: 16 },
      2: { zone: "Denial", weight: 16 },
      3: { zone: "Panic", weight: 18 },
      4: { zone: "Anxiety", weight: 14 },
      5: { zone: "Denial", weight: 14 },
      A: { zone: "Anxiety", weight: 14 },
      B: { zone: "Denial", weight: 16 },
      C: { zone: "Panic", weight: 18 }
    }
  };

  // Quy luật chu trình tâm lý — Bỏ cuộc đến sau Hoảng loạn khi giá không tăng thêm.
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

  // Chỉ giữ swing lớn nhất trên khung tuần (macro Elliott).
  const MAJOR_DEVIATION_LOOKBACK_WEEKS = 52;
  const MAJOR_DEVIATION_MULTIPLIER = 3.8;
  const MAJOR_DEVIATION_MIN = 12;
  const MAJOR_DEVIATION_MAX = 35;
  const MAJOR_LEG_MIN_RANGE_PCT = 0.08;
  const MAJOR_MIN_WEEKS_BETWEEN = 3;

  const buildMajorWeeklyDeviation = (weeklySeries) => {
    if (weeklySeries.length < 4) {
      return MAJOR_DEVIATION_MIN;
    }

    let total = 0;
    let count = 0;
    const end = weeklySeries.length - 1;
    const start = Math.max(1, end - MAJOR_DEVIATION_LOOKBACK_WEEKS);

    for (let index = start; index <= end; index += 1) {
      const previous = getClose(weeklySeries[index - 1]);
      if (!previous) {
        continue;
      }

      total += Math.abs((getClose(weeklySeries[index]) - previous) / previous) * 100;
      count += 1;
    }

    const average = count ? total / count : 8;
    return clamp(average * MAJOR_DEVIATION_MULTIPLIER, MAJOR_DEVIATION_MIN, MAJOR_DEVIATION_MAX);
  };

  const weeksBetween = (weeklySeries, leftIndex, rightIndex) => {
    if (leftIndex < 0 || rightIndex < 0 || leftIndex >= weeklySeries.length || rightIndex >= weeklySeries.length) {
      return 0;
    }

    return Math.abs(rightIndex - leftIndex);
  };

  const filterMajorSwings = (swings, weeklySeries, minLegPctOfRange = MAJOR_LEG_MIN_RANGE_PCT) => {
    if (swings.length < 3 || weeklySeries.length < 3) {
      return swings;
    }

    const closes = weeklySeries.map(getClose);
    const range = Math.max(...closes) - Math.min(...closes);
    if (range <= 0) {
      return swings;
    }

    const minLeg = range * minLegPctOfRange;
    let filtered = [...swings];
    let changed = true;

    while (changed && filtered.length > 2) {
      changed = false;

      for (let index = 1; index < filtered.length - 1; index += 1) {
        const legBefore = Math.abs(filtered[index].price - filtered[index - 1].price);
        const legAfter = Math.abs(filtered[index + 1].price - filtered[index].price);
        const spanWeeks = weeksBetween(weeklySeries, filtered[index - 1].index, filtered[index + 1].index);
        const minorPivot = Math.min(legBefore, legAfter) < minLeg
          || spanWeeks < MAJOR_MIN_WEEKS_BETWEEN;

        if (minorPivot) {
          filtered.splice(index, 1);
          changed = true;
          break;
        }
      }
    }

    return filtered;
  };

  const detectMajorWeeklySwings = (weeklySeries) => {
    const deviation = buildMajorWeeklyDeviation(weeklySeries);
    const swings = detectSwings(weeklySeries, deviation);
    return filterMajorSwings(swings, weeklySeries);
  };

  const WAVE_SEQUENCE = ["1", "2", "3", "4", "5", "A", "B", "C"];

  // Ngưỡng hiệu chỉnh trên dữ liệu tuần Bitcoin (tài sản tham chiếu).
  const REGIME_LOOKBACK_WEEKS = 78;
  const REGIME_BEAR_DRAWDOWN = -0.18;
  const STRONG_LEG_RATIO = 1.12;
  const SIDEWAYS_LEG_CHANGE = 0.03;
  const SIDEWAYS_RANGE_PCT = 8;
  const CAPITULATION_FLAT_CHANGE = 0.05;
  const CAPITULATION_MIN_WEEKS = 4;
  const BULLISH_ZONES = new Set(["Hope", "Optimism", "Belief", "Euphoria"]);
  const BEARISH_ZONES = new Set(["Anxiety", "Denial", "Panic", "Capitulation"]);
  const IMPULSE_WAVES = new Set(["1", "3", "5"]);
  const CORRECTIVE_WAVES = new Set(["2", "4"]);
  const BULL_IMPULSE_NEGATIVE = BEARISH_ZONES;
  const BEAR_IMPULSE_POSITIVE = new Set(["Hope", "Optimism", "Belief", "Euphoria", "Complacency"]);
  const BEAR_CORRECTIVE_BULLISH = new Set(["Hope", "Optimism", "Belief", "Euphoria"]);
  const BULL_CORRECTIVE_STRONG_BULL = new Set(["Belief", "Euphoria"]);
  const DEFAULT_BULL_IMPULSE = { 1: "Hope", 3: "Belief", 5: "Euphoria" };
  const DEFAULT_BEAR_IMPULSE = { 1: "Disbelief", 3: "Panic", 5: "Denial" };
  const DEFAULT_BEAR_CORRECTIVE = { 2: "Denial", 4: "Anxiety" };
  const DEFAULT_BULL_CORRECTIVE = { 2: "Anxiety", 4: "Complacency" };
  const STRONG_BULL_UP_LEG = 0.10;
  const BULL_UP_ZONE_BY_WAVE = {
    1: "Hope",
    2: "Optimism",
    3: "Belief",
    4: "Complacency",
    5: "Euphoria",
    A: "Hope",
    B: "Optimism",
    C: "Belief"
  };

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
    const strongLeg = prevLeg > 0 ? legSize / prevLeg >= STRONG_LEG_RATIO : false;
    const legLow = Math.min(startPrice, endPrice, minPrice);
    const recoveryFromLow = legLow > 0 ? (endPrice - legLow) / legLow : 0;
    const hasRecovery = legChange < -0.008 && recoveryFromLow >= 0.03;
    const sideways = (
      Math.abs(legChange) < SIDEWAYS_LEG_CHANGE
      && rangePct < SIDEWAYS_RANGE_PCT
      && slice.length >= CAPITULATION_MIN_WEEKS
    );
    const tailCount = Math.min(CAPITULATION_MIN_WEEKS, slice.length);
    const tailSlice = slice.slice(-tailCount);
    const tailStart = getClose(tailSlice[0]);
    const tailEnd = getClose(tailSlice[tailSlice.length - 1]);
    const hasFlatTail = (
      tailSlice.length >= 3
      && tailStart > 0
      && Math.abs((tailEnd - tailStart) / tailStart) < SIDEWAYS_LEG_CHANGE
    );

    return {
      legUp: legChange > 0.008,
      legDown: legChange < -0.008,
      legFlat: Math.abs(legChange) <= 0.008,
      legChange,
      strongLeg,
      hasRecovery,
      hasFlatTail,
      sideways,
      rangePct,
      durationWeeks: slice.length,
      endIndex: endIdx
    };
  };

  const applyLegDirectionGuard = (psych, waveId, leg) => {
    if (!psych?.zone || !leg.legDown || !BULLISH_ZONES.has(psych.zone)) {
      return psych;
    }

    const downMap = {
      Hope: "Denial",
      Optimism: "Anxiety",
      Belief: "Panic",
      Euphoria: "Anxiety"
    };

    return {
      ...psych,
      zone: downMap[psych.zone] || "Anxiety"
    };
  };

  const isPostPanicConsolidation = (leg, prevZone) => {
    if (prevZone !== "Panic") {
      return false;
    }

    return (
      leg.sideways
      || leg.hasFlatTail
      || (leg.legFlat && !leg.legUp)
      || (Math.abs(leg.legChange) < CAPITULATION_FLAT_CHANGE && !leg.legUp)
    );
  };

  const resolvePsychologyByWaveLaw = (waveId, leg, prevZone, macroRegime = "bull") => {
    if (isPostPanicConsolidation(leg, prevZone)) {
      return { zone: "Capitulation", weight: 22 };
    }

    if (leg.sideways || (waveId === "1" && leg.legFlat && leg.durationWeeks >= CAPITULATION_MIN_WEEKS)) {
      return { zone: "Disbelief", weight: 16 };
    }

    let psych;

    switch (waveId) {
      case "1":
        if (prevZone === "Panic" && leg.legChange < 0.10) {
          psych = { zone: "Capitulation", weight: 22 };
          break;
        }

        if (macroRegime === "bear") {
          psych = leg.legUp
            ? { zone: "Disbelief", weight: 14 }
            : { zone: "Disbelief", weight: 16 };
          break;
        }

        psych = leg.legUp
          ? { zone: "Hope", weight: 18 }
          : { zone: "Disbelief", weight: 14 };
        break;

      case "2":
        if (macroRegime === "bear") {
          psych = leg.legUp
            ? { zone: "Denial", weight: 16 }
            : { zone: "Anxiety", weight: 14 };
          break;
        }

        psych = leg.legUp
          ? { zone: "Optimism", weight: 16 }
          : { zone: "Anxiety", weight: 14 };
        break;

      case "3":
        if (macroRegime === "bear") {
          psych = leg.legDown
            ? { zone: "Panic", weight: 20 }
            : { zone: "Denial", weight: 14 };
          break;
        }

        psych = leg.legUp
          ? { zone: "Belief", weight: 22 }
          : { zone: "Anxiety", weight: 14 };
        break;

      case "4":
        if (macroRegime === "bear") {
          psych = leg.legUp
            ? { zone: "Denial", weight: 14 }
            : { zone: "Anxiety", weight: 14 };
          break;
        }

        if (leg.legDown && leg.hasRecovery) {
          psych = { zone: "Complacency", weight: 16 };
          break;
        }

        psych = leg.legDown
          ? { zone: "Anxiety", weight: 14 }
          : { zone: "Optimism", weight: 14 };
        break;

      case "5":
        if (macroRegime === "bear") {
          psych = leg.legUp
            ? { zone: "Denial", weight: 14 }
            : { zone: "Anxiety", weight: 14 };
          break;
        }

        if (leg.legUp && leg.strongLeg) {
          psych = { zone: "Euphoria", weight: 22 };
          break;
        }

        psych = leg.legUp
          ? { zone: "Belief", weight: 18 }
          : { zone: "Complacency", weight: 14 };
        break;

      case "A":
        psych = leg.legDown
          ? { zone: "Anxiety", weight: 14 }
          : { zone: "Denial", weight: 14 };
        break;

      case "B":
        psych = { zone: "Denial", weight: 16 };
        break;

      case "C":
        if (leg.legDown) {
          if (leg.hasFlatTail || (leg.recoveryFromLow >= 0.04 && leg.legChange <= -0.10 && !leg.strongLeg)) {
            psych = { zone: "Capitulation", weight: 22 };
            break;
          }

          psych = {
            zone: "Panic",
            weight: leg.strongLeg ? 22 : 18
          };
          break;
        }

        psych = { zone: "Denial", weight: 14 };
        break;

      default:
        psych = { zone: "Disbelief", weight: 12 };
    }

    return applyLegDirectionGuard(psych, waveId, leg);
  };

  const inferCorrectionPhase = (weeklySeries, leg, prevZone, prevRegions) => {
    const endIdx = leg.endIndex ?? weeklySeries.length - 1;
    const recentWindow = weeklySeries.slice(Math.max(0, endIdx - 51), endIdx + 1);
    const recentHigh = recentWindow.length
      ? Math.max(...recentWindow.map(getClose))
      : getClose(weeklySeries[endIdx]);
    const drawdown = recentHigh > 0
      ? (getClose(weeklySeries[endIdx]) - recentHigh) / recentHigh
      : 0;

    if (drawdown <= -0.15) {
      return true;
    }

    if (["Anxiety", "Denial", "Panic", "Capitulation"].includes(prevZone)) {
      return true;
    }

    const recentCutoff = weeklySeries[Math.max(0, endIdx - 26)]?.date;
    return prevRegions.some((region) => (
      ["Anxiety", "Denial", "Panic", "Capitulation", "Complacency", "Euphoria"].includes(region.zone)
      && (!recentCutoff || region.endDate >= recentCutoff)
    ));
  };

  const applyCorrectionPhaseGuard = (psych, leg, prevZone, inCorrection) => {
    if (!inCorrection || !leg.legUp || !BULLISH_ZONES.has(psych.zone)) {
      return psych;
    }

    if (prevZone === "Panic" || prevZone === "Capitulation") {
      return {
        ...psych,
        zone: leg.legChange < 0.10 ? "Capitulation" : "Hope"
      };
    }

    return { ...psych, zone: "Denial" };
  };

  const applyBullUptrendGuard = (psych, leg, macroRegime, waveId) => {
    if (
      macroRegime !== "bull"
      || !leg.legUp
      || leg.legChange < STRONG_BULL_UP_LEG
      || !psych?.zone
      || !BEARISH_ZONES.has(psych.zone)
    ) {
      return psych;
    }

    return {
      ...psych,
      zone: BULL_UP_ZONE_BY_WAVE[waveId] || "Hope"
    };
  };

  const resolveBullImpulseZone = (waveId, leg) => {
    if (waveId === "5" && leg?.legUp && !leg?.strongLeg) {
      return "Belief";
    }

    if (waveId === "5" && leg?.legUp && leg?.strongLeg) {
      return "Euphoria";
    }

    return DEFAULT_BULL_IMPULSE[waveId] || "Hope";
  };

  const enforceWavePsychologyLaw = (psych, waveId, macroRegime, leg = null) => {
    if (!psych?.zone || !waveId) {
      return psych;
    }

    const macro = macroRegime === "bear" ? "bear" : "bull";
    let zone = psych.zone;

    if (IMPULSE_WAVES.has(waveId)) {
      if (macro === "bull" && BULL_IMPULSE_NEGATIVE.has(zone)) {
        zone = resolveBullImpulseZone(waveId, leg);
      }

      if (macro === "bear" && BEAR_IMPULSE_POSITIVE.has(zone)) {
        zone = DEFAULT_BEAR_IMPULSE[waveId] || "Disbelief";
      }
    }

    if (CORRECTIVE_WAVES.has(waveId)) {
      if (macro === "bear" && BEAR_CORRECTIVE_BULLISH.has(zone)) {
        zone = DEFAULT_BEAR_CORRECTIVE[waveId] || "Denial";
      }

      if (macro === "bull" && BULL_CORRECTIVE_STRONG_BULL.has(zone)) {
        zone = DEFAULT_BULL_CORRECTIVE[waveId] || "Anxiety";
      }
    }

    if (zone === psych.zone) {
      return psych;
    }

    return { ...psych, zone };
  };

  const applyCapitulationTails = (weeklySeries, regions, chain) => {
    const output = [];

    regions.forEach((region, index) => {
      const prev = output.at(-1);
      const leg = measureLeg(weeklySeries, chain, index);

      if (region.zone === "Panic" && leg.durationWeeks > CAPITULATION_MIN_WEEKS + 1) {
        const tailWeeks = Math.min(
          CAPITULATION_MIN_WEEKS,
          Math.max(2, Math.floor(leg.durationWeeks / 3))
        );
        const tailStartIdx = Math.max(
          (chain[index].index ?? 0) + 1,
          leg.endIndex - tailWeeks + 1
        );
        const tailStartDate = weeklySeries[tailStartIdx]?.date;

        if (tailStartDate && tailStartDate > region.startDate && tailStartDate < region.endDate) {
          const panicEndDate = weeklySeries[tailStartIdx - 1]?.date || tailStartDate;
          output.push({ ...region, endDate: panicEndDate });
          output.push({
            ...region,
            zone: "Capitulation",
            startDate: tailStartDate
          });
          return;
        }
      }

      if (prev?.zone === "Panic" && region.zone !== "Capitulation") {
        const rise = chain[index].price > 0 && chain[index - 1]?.price
          ? (chain[index + 1]?.price ?? chain[index].price) - chain[index].price
          : 0;
        const risePct = chain[index].price > 0 ? rise / chain[index].price : 0;

        if (risePct < 0.10 && !leg.legUp) {
          output.push({ ...region, zone: "Capitulation" });
          return;
        }
      }

      output.push(region);
    });

    return output;
  };

  const resolvePsychologyFromLaw = (weeklySeries, chain, index, prevZone = null, prevRegions = []) => {
    const waveId = WAVE_SEQUENCE[index % WAVE_SEQUENCE.length];
    const leg = measureLeg(weeklySeries, chain, index);
    const endIndex = chain[index + 1].index ?? weeklySeries.length - 1;
    const macroRegime = inferRegimeAtIndex(weeklySeries, endIndex);
    const inCorrection = inferCorrectionPhase(weeklySeries, leg, prevZone, prevRegions);
    let psych = resolvePsychologyByWaveLaw(waveId, leg, prevZone, macroRegime);
    psych = applyCorrectionPhaseGuard(psych, leg, prevZone, inCorrection);
    psych = applyBullUptrendGuard(psych, leg, macroRegime, waveId);
    psych = applyLegDirectionGuard(psych, waveId, leg);
    return enforceWavePsychologyLaw(psych, waveId, macroRegime, leg);
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

    if (waveId === "3" && index >= 2) {
      const wave1Leg = Math.abs(chain[index].price - chain[index - 1].price);
      const wave3Leg = Math.abs(chain[index + 1].price - chain[index].price);
      if (wave3Leg < wave1Leg * 0.9) {
        score -= 16;
      }
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
    let regions = [];

    for (let index = 0; index < chain.length - 1; index += 1) {
      const waveId = WAVE_SEQUENCE[index % WAVE_SEQUENCE.length];
      const endIndex = chain[index + 1].index ?? weeklySeries.length - 1;
      const direction = inferRegimeAtIndex(weeklySeries, endIndex);
      const directionLabel = direction === "bull" ? "tăng" : "giảm";
      const prevZone = regions.length ? regions[regions.length - 1].zone : null;
      const psych = resolvePsychologyFromLaw(weeklySeries, chain, index, prevZone, regions);

      regions.push({
        startDate: chain[index].date,
        endDate: chain[index + 1].date,
        zone: psych.zone,
        waveId,
        macroRegime: direction,
        elliottLabel: `${WAVE_LABELS_VI[waveId]} ${directionLabel}`,
        confidence: scoreRegionConfidence(chain, index)
      });
    }

    if (regions.length) {
      regions = applyCapitulationTails(weeklySeries, regions, chain);
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
    const deviation = buildMajorWeeklyDeviation(weeklySeries);
    const swings = detectMajorWeeklySwings(weeklySeries);
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
    detectMajorWeeklySwings,
    filterMajorSwings,
    buildSwingCache,
    buildWeeklyDeviation,
    buildMajorWeeklyDeviation,
    buildFullCoverageRegions,
    clipRegionsToRange,
    findRegionForDate,
    buildWeeklyPsychologyModel,
    analyzeAt,
    buildVisibleWaveOverlay,
    annotateRegionsWithValidation,
    validateWaveLeg,
    formatWaveMarkerText,
    enforceWavePsychologyLaw,
    IMPULSE_WAVES,
    CORRECTIVE_WAVES
  };
})();
