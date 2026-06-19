/* Elliott Wave on weekly candles: swing detection and psychology regions. */
const ElliottEngine = (() => {
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

  const buildWaveRegions = (weeklySeries, swings) => {
    const seriesStart = weeklySeries[0].date;
    const seriesEnd = weeklySeries[weeklySeries.length - 1].date;
    const cycle = inferCycle(swings);
    const waveSequence = ["1", "2", "3", "4", "5", "A", "B", "C"];

    if (!cycle) {
      return [{
        startDate: seriesStart,
        endDate: seriesEnd,
        zone: "Observing",
        waveId: null,
        elliottLabel: "Chưa xác định sóng tuần",
        confidence: 0
      }];
    }

    const { pivots, direction, score } = cycle;
    const regions = [];
    const directionLabel = direction === "bull" ? "tăng" : "giảm";

    if (pivots[0].date > seriesStart) {
      const waveId = "1";
      const psych = WAVE_PSYCHOLOGY[direction][waveId];
      regions.push({
        startDate: seriesStart,
        endDate: pivots[0].date,
        zone: psych.zone,
        waveId,
        elliottLabel: `${WAVE_LABELS_VI[waveId]} ${directionLabel}`,
        confidence: clamp(score, 0, 100)
      });
    }

    pivots.forEach((pivot, index) => {
      const waveId = waveSequence[Math.min(index, waveSequence.length - 1)];
      const psych = WAVE_PSYCHOLOGY[direction][waveId];
      const endDate = index + 1 < pivots.length ? pivots[index + 1].date : seriesEnd;

      regions.push({
        startDate: pivot.date,
        endDate,
        zone: psych.zone,
        waveId,
        elliottLabel: `${WAVE_LABELS_VI[waveId]} ${directionLabel}`,
        confidence: clamp(score + 8, 0, 100)
      });
    });

    return regions;
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

    const direct = regions.find((region) => date >= region.startDate && date <= region.endDate);
    if (direct) {
      return direct;
    }

    let fallback = regions[0];
    regions.forEach((region) => {
      if (region.startDate <= date) {
        fallback = region;
      }
    });

    return fallback;
  };

  const buildWeeklyPsychologyModel = (weeklySeries) => {
    const deviation = buildWeeklyDeviation(weeklySeries);
    const swings = detectSwings(weeklySeries, deviation);
    const regions = buildWaveRegions(weeklySeries, swings);

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

  return {
    WAVE_LABELS_VI,
    WAVE_PSYCHOLOGY,
    detectSwings,
    buildSwingCache,
    buildWeeklyDeviation,
    buildWaveRegions,
    findRegionForDate,
    buildWeeklyPsychologyModel,
    analyzeAt
  };
})();
