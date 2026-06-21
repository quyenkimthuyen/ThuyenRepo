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
      1: { zone: "Disbelief", weight: 18 },
      2: { zone: "Anxiety", weight: 16 },
      3: { zone: "Belief", weight: 22 },
      4: { zone: "Complacency", weight: 16 },
      5: { zone: "Euphoria", weight: 20 },
      A: { zone: "Anxiety", weight: 14 },
      B: { zone: "Hope", weight: 16 },
      C: { zone: "Panic", weight: 18 }
    },
    bear: {
      1: { zone: "Disbelief", weight: 16 },
      2: { zone: "Denial", weight: 16 },
      3: { zone: "Panic", weight: 18 },
      4: { zone: "Anxiety", weight: 14 },
      5: { zone: "Capitulation", weight: 18 },
      A: { zone: "Disbelief", weight: 14 },
      B: { zone: "Hope", weight: 16 },
      C: { zone: "Capitulation", weight: 18 }
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
  const getHigh = (point) => point.high ?? getClose(point);
  const getLow = (point) => point.low ?? getClose(point);

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
      price: getHigh(series[0]),
      type: "high"
    };

    for (let index = 0; index < series.length; index += 1) {
      const high = getHigh(series[index]);
      const low = getLow(series[index]);

      if (direction === "seekHigh") {
        if (high >= extreme.price) {
          extreme = { index, date: series[index].date, price: high, type: "high" };
        }

        if (extreme.price > 0 && (extreme.price - low) / extreme.price >= threshold) {
          swings.push({ ...extreme });
          extreme = { index, date: series[index].date, price: low, type: "low" };
          direction = "seekLow";
        }

        continue;
      }

      if (low <= extreme.price) {
        extreme = { index, date: series[index].date, price: low, type: "low" };
      }

      if (extreme.price > 0 && (high - extreme.price) / extreme.price >= threshold) {
        swings.push({ ...extreme });
        extreme = { index, date: series[index].date, price: high, type: "high" };
        direction = "seekHigh";
      }
    }

    return swings;
  };

  const normalizeSwingAlternation = (swings) => {
    if (!swings.length) {
      return swings;
    }

    const output = [{ ...swings[0] }];

    for (let index = 1; index < swings.length; index += 1) {
      const current = swings[index];
      const previous = output[output.length - 1];

      if (current.type === previous.type) {
        const keepCurrent = current.type === "high"
          ? current.price >= previous.price
          : current.price <= previous.price;

        output[output.length - 1] = keepCurrent ? { ...current } : { ...previous };
        continue;
      }

      output.push({ ...current });
    }

    return output;
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

  // Macro Elliott tuần — tối ưu cho Bitcoin chu kỳ ~4 năm (halving).
  const BTC_CYCLE_WEEKS = 208;
  const BTC_CYCLE_MIN_LOW_WEEKS = 52;
  const MACRO_EXTREMA_WINDOW = 26;
  const MACRO_MIN_LEG_PCT = 0.15;
  const MACRO_MIN_WEEKS = 8;
  const MACRO_MAX_PIVOTS_PER_CYCLE = 6;
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

  const detectLocalExtremaPivots = (weeklySeries, windowWeeks = MACRO_EXTREMA_WINDOW) => {
    if (!weeklySeries?.length || weeklySeries.length < windowWeeks + 2) {
      return [];
    }

    const half = Math.floor(windowWeeks / 2);
    const raw = [];

    for (let index = half; index < weeklySeries.length - half; index += 1) {
      let isHigh = true;
      let isLow = true;
      const high = getHigh(weeklySeries[index]);
      const low = getLow(weeklySeries[index]);

      for (let probe = index - half; probe <= index + half; probe += 1) {
        if (probe === index) {
          continue;
        }

        if (getHigh(weeklySeries[probe]) > high) {
          isHigh = false;
        }

        if (getLow(weeklySeries[probe]) < low) {
          isLow = false;
        }
      }

      if (isHigh) {
        raw.push({
          index,
          date: weeklySeries[index].date,
          price: high,
          type: "high"
        });
      } else if (isLow) {
        raw.push({
          index,
          date: weeklySeries[index].date,
          price: low,
          type: "low"
        });
      }
    }

    return normalizeSwingAlternation(raw);
  };

  const pruneCloseMacroPivots = (pivots, weeklySeries) => {
    if (pivots.length < 3) {
      return pivots;
    }

    let filtered = [...pivots];
    let changed = true;

    while (changed && filtered.length > 2) {
      changed = false;

      for (let index = 1; index < filtered.length - 1; index += 1) {
        const spanWeeks = weeksBetween(
          weeklySeries,
          filtered[index - 1].index,
          filtered[index + 1].index
        );
        const legBefore = Math.abs(filtered[index].price - filtered[index - 1].price);
        const legAfter = Math.abs(filtered[index + 1].price - filtered[index].price);
        const base = Math.max(filtered[index - 1].price, filtered[index + 1].price, 1);
        const minorLeg = Math.min(legBefore, legAfter) / base < MACRO_MIN_LEG_PCT;
        const tooClose = spanWeeks < MACRO_MIN_WEEKS * 2;

        if (minorLeg || tooClose) {
          filtered.splice(index, 1);
          changed = true;
          break;
        }
      }
    }

    return normalizeSwingAlternation(filtered);
  };

  const pruneFourYearBuckets = (
    pivots,
    weeklySeries,
    cycleWeeks = BTC_CYCLE_WEEKS,
    maxPerCycle = MACRO_MAX_PIVOTS_PER_CYCLE
  ) => {
    if (pivots.length <= maxPerCycle) {
      return pivots;
    }

    const tagged = pivots.map((pivot, order) => ({ ...pivot, order }));
    const origin = tagged[0].index;
    const buckets = new Map();

    tagged.forEach((pivot) => {
      const bucket = Math.floor((pivot.index - origin) / cycleWeeks);
      if (!buckets.has(bucket)) {
        buckets.set(bucket, []);
      }
      buckets.get(bucket).push(pivot);
    });

    const keep = new Set();

    buckets.forEach((bucketPivots) => {
      let current = [...bucketPivots];

      while (current.length > maxPerCycle && current.length > 2) {
        let removeAt = 1;
        let smallest = Infinity;

        for (let index = 1; index < current.length - 1; index += 1) {
          const bridge = Math.abs(current[index + 1].price - current[index - 1].price);
          if (bridge < smallest) {
            smallest = bridge;
            removeAt = index;
          }
        }

        current.splice(removeAt, 1);
      }

      current.forEach((pivot) => keep.add(pivot.order));
    });

    return pivots.filter((_, order) => keep.has(order));
  };

  const detectMajorWeeklySwings = (weeklySeries) => {
    let pivots = detectLocalExtremaPivots(weeklySeries, MACRO_EXTREMA_WINDOW);
    pivots = pruneCloseMacroPivots(pivots, weeklySeries);
    pivots = pruneFourYearBuckets(pivots, weeklySeries);
    return pivots;
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

    return normalizeSwingAlternation(filtered);
  };

  const findExtremePivot = (weeklySeries, fromIndex, toIndex, type) => {
    const pick = type === "high" ? getHigh : getLow;
    let best = {
      index: fromIndex,
      date: weeklySeries[fromIndex].date,
      price: pick(weeklySeries[fromIndex]),
      type
    };

    for (let index = fromIndex + 1; index <= toIndex; index += 1) {
      const price = pick(weeklySeries[index]);

      if (type === "high" ? price > best.price : price < best.price) {
        best = {
          index,
          date: weeklySeries[index].date,
          price,
          type
        };
      }
    }

    return best;
  };

  const findMacroCycleStarts = (chain) => {
    const starts = [];

    chain.forEach((pivot, index) => {
      if (pivot.type !== "low") {
        return;
      }

      if (!starts.length) {
        starts.push(index);
        return;
      }

      const lastStartIndex = starts[starts.length - 1];
      const gapWeeks = pivot.index - chain[lastStartIndex].index;

      if (gapWeeks >= BTC_CYCLE_MIN_LOW_WEEKS) {
        starts.push(index);
      }
    });

    return starts.length ? starts : [0];
  };

  const findCycleStartForLeg = (legIndex, cycleStarts) => {
    let cycleStart = cycleStarts[0];

    cycleStarts.forEach((candidate) => {
      if (candidate <= legIndex) {
        cycleStart = candidate;
      }
    });

    return cycleStart;
  };

  const findCycleStart = (chain) => findCycleStartForLeg(
    Math.max(0, chain.length - 2),
    findMacroCycleStarts(chain)
  );

  const waveIdForLeg = (legIndex, cycleStart) => {
    const offset = ((legIndex - cycleStart) % WAVE_SEQUENCE.length + WAVE_SEQUENCE.length) % WAVE_SEQUENCE.length;
    return WAVE_SEQUENCE[offset];
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
  const DEFAULT_BULL_IMPULSE = { 1: "Disbelief", 3: "Belief", 5: "Euphoria" };
  const DEFAULT_BEAR_IMPULSE = { 1: "Disbelief", 3: "Panic", 5: "Capitulation" };
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
      return { zone: "Capitulation", weight: 18 };
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
          ? { zone: "Disbelief", weight: 18 }
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
          ? { zone: "Anxiety", weight: 16 }
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
            : { zone: "Capitulation", weight: 18 };
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
        psych = { zone: macroRegime === "bear" ? "Hope" : "Hope", weight: 16 };
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

  const resolvePsychologyFromLaw = (weeklySeries, chain, index, prevZone = null, prevRegions = [], cycleStart = 0) => {
    const waveId = waveIdForLeg(index, cycleStart);
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

  const collapseAdjacentDatePivots = (chain) => {
    const output = [];

    chain.forEach((pivot) => {
      const previous = output[output.length - 1];
      if (previous?.date === pivot.date) {
        return;
      }

      output.push(pivot);
    });

    return output;
  };

  const buildPivotChain = (weeklySeries, swings) => {
    const lastIndex = weeklySeries.length - 1;

    if (!swings.length) {
      const macro = inferMacroDirection(weeklySeries);
      return [
        findExtremePivot(weeklySeries, 0, lastIndex, macro === "bull" ? "low" : "high"),
        findExtremePivot(weeklySeries, 0, lastIndex, macro === "bull" ? "high" : "low")
      ];
    }

    const normalized = normalizeSwingAlternation(swings);
    const chain = [];
    const firstSwing = normalized[0];

    if (firstSwing.index > 0) {
      chain.push(findExtremePivot(
        weeklySeries,
        0,
        Math.max(0, firstSwing.index - 1),
        firstSwing.type === "high" ? "low" : "high"
      ));
    }

    normalized.forEach((swing) => chain.push({ ...swing }));

    const lastSwing = chain[chain.length - 1];
    if (lastSwing.index < lastIndex) {
      const fromIndex = Math.min(lastSwing.index + 1, lastIndex);
      chain.push(findExtremePivot(
        weeklySeries,
        fromIndex,
        lastIndex,
        lastSwing.type === "high" ? "low" : "high"
      ));
    }

    return normalizeSwingAlternation(collapseAdjacentDatePivots(chain));
  };

  const scoreRegionConfidence = (chain, index, cycleStart = 0) => {
    if (chain.length < 2) {
      return 50;
    }

    const legSize = Math.abs(chain[index + 1].price - chain[index].price);
    const prevLeg = index > 0 ? Math.abs(chain[index].price - chain[index - 1].price) : null;
    const waveId = waveIdForLeg(index, cycleStart);
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
    const cycleStarts = findMacroCycleStarts(chain);
    let regions = [];

    for (let index = 0; index < chain.length - 1; index += 1) {
      const cycleStart = findCycleStartForLeg(index, cycleStarts);
      const waveId = waveIdForLeg(index, cycleStart);
      const endIndex = chain[index + 1].index ?? weeklySeries.length - 1;
      const direction = inferRegimeAtIndex(weeklySeries, endIndex);
      const directionLabel = direction === "bull" ? "tăng" : "giảm";
      const prevZone = regions.length ? regions[regions.length - 1].zone : null;
      const psych = resolvePsychologyFromLaw(weeklySeries, chain, index, prevZone, regions, cycleStart);

      regions.push({
        startDate: chain[index].date,
        endDate: chain[index + 1].date,
        zone: psych.zone,
        waveId,
        macroRegime: direction,
        elliottLabel: `${WAVE_LABELS_VI[waveId]} ${directionLabel}`,
        confidence: scoreRegionConfidence(chain, index, cycleStart)
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
    const pivots = buildPivotChain(weeklySeries, swings);
    let regions = buildFullCoverageRegions(weeklySeries, swings);

    if (rangeStart && rangeEnd) {
      regions = clipRegionsToRange(regions, rangeStart, rangeEnd);
    }

    return {
      weekly: weeklySeries,
      swings,
      pivots,
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

    const sourcePivots = cache.pivots?.length
      ? cache.pivots
      : (cache.swings?.length ? buildPivotChain(
        cache.weekly || [],
        cache.swings
      ) : null);

    if (!sourcePivots || sourcePivots.length < 2) {
      return null;
    }

    const visibleStart = visibleSeries[0].date;
    const visibleEnd = visibleSeries[visibleSeries.length - 1].date;
    const chain = [];
    const before = sourcePivots.filter((pivot) => pivot.date < visibleStart).at(-1);
    const inside = sourcePivots.filter((pivot) => pivot.date >= visibleStart && pivot.date <= visibleEnd);
    const after = sourcePivots.find((pivot) => pivot.date > visibleEnd);

    if (before) {
      chain.push(before);
    }

    chain.push(...inside);

    if (after) {
      chain.push(after);
    } else {
      const lastPivot = sourcePivots[sourcePivots.length - 1];
      if (lastPivot.date < visibleEnd) {
        const trailingType = lastPivot.type === "high" ? "low" : "high";
        let startIndex = 0;

        for (let index = 0; index < visibleSeries.length; index += 1) {
          if (visibleSeries[index].date > lastPivot.date) {
            startIndex = index;
            break;
          }
        }

        if (startIndex < visibleSeries.length) {
          chain.push(findExtremePivot(
            visibleSeries,
            startIndex,
            visibleSeries.length - 1,
            trailingType
          ));
        }
      }
    }

    const pivots = normalizeSwingAlternation(
      chain.sort((left, right) => left.date.localeCompare(right.date))
    );

    if (pivots.length < 2) {
      return null;
    }

    const points = pivots.map((pivot) => ({
      time: pivot.date,
      value: pivot.price
    }));

    const markerDates = new Set(
      sourcePivots
        .filter((pivot) => pivot.date >= visibleStart && pivot.date <= visibleEnd)
        .map((pivot) => pivot.date)
    );

    const markers = [];

    pivots.forEach((pivot) => {
      if (!markerDates.has(pivot.date)) {
        return;
      }

      const region = findRegionForDate(cache.regions, pivot.date);
      if (!region?.waveId) {
        return;
      }

      if (options.validatedOnly && region.elliottValidated === false) {
        return;
      }

      markers.push({
        time: pivot.date,
        position: pivot.type === "low" ? "belowBar" : "aboveBar",
        color: region.elliottValidated === false ? "rgba(240, 180, 92, 0.55)" : "#f0b45c",
        shape: "circle",
        text: formatWaveMarkerText(region.waveId)
      });
    });

    return { points, markers, pivots };
  };

  return {
    WAVE_LABELS_VI,
    WAVE_PSYCHOLOGY,
    PSYCHOLOGY_CYCLE_LAW,
    detectSwings,
    detectMajorWeeklySwings,
    detectLocalExtremaPivots,
    normalizeSwingAlternation,
    filterMajorSwings,
    buildPivotChain,
    findMacroCycleStarts,
    findCycleStart,
    findCycleStartForLeg,
    waveIdForLeg,
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
