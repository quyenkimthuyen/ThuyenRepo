/* Elliott Wave helper: swing detection and wave-to-psychology mapping. */
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

  const detectSwings = (series, deviationPct = 4) => {
    if (!series || series.length < 3) {
      return [];
    }

    const threshold = Math.max(deviationPct, 2.5) / 100;
    const swings = [];
    let direction = "seekHigh";
    let anchor = {
      index: 0,
      date: series[0].date,
      price: getClose(series[0]),
      type: "low"
    };
    let extreme = { ...anchor };

    for (let index = 1; index < series.length; index += 1) {
      const price = getClose(series[index]);

      if (direction === "seekHigh") {
        if (price >= extreme.price) {
          extreme = { index, date: series[index].date, price, type: "high" };
          continue;
        }

        if ((extreme.price - price) / extreme.price >= threshold) {
          swings.push({ ...extreme });
          anchor = { index, date: series[index].date, price, type: "low" };
          extreme = { ...anchor };
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
        anchor = { index, date: series[index].date, price, type: "high" };
        extreme = { ...anchor };
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

      let score = 10;
      const impulseLegs = direction === "bull"
        ? [legs[0], legs[2], legs[4]].filter(Boolean)
        : [legs[0], legs[2], legs[4]].filter(Boolean);

      if (impulseLegs.length >= 2 && legs[1]) {
        const wave2Retrace = retraceRatio(legs[0], legs[1]);
        if (wave2Retrace > 0.12 && wave2Retrace < 0.78) {
          score += 8;
        }
      }

      if (impulseLegs.length === 3) {
        const shortest = Math.min(...impulseLegs);
        const longest = Math.max(...impulseLegs);
        if (impulseLegs[1] !== shortest) {
          score += 10;
        }
        if (longest === impulseLegs[1]) {
          score += 8;
        }
      }

      if (slice.length >= 5) {
        score += 6;
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

  const resolveWaveId = (cycle, endIndex, close) => {
    const { pivots, direction } = cycle;
    const lastPivot = pivots[pivots.length - 1];
    let waveIndex = pivots.length;

    if (lastPivot.index < endIndex) {
      waveIndex = pivots.length;
    }

    const waveSequence = ["1", "2", "3", "4", "5", "A", "B", "C"];
    const waveId = waveSequence[Math.min(Math.max(waveIndex - 1, 0), waveSequence.length - 1)];
    const psychology = WAVE_PSYCHOLOGY[direction][waveId];
    const inProgress = lastPivot.index < endIndex;
    const progress = inProgress
      ? clamp(((close - lastPivot.price) / Math.max(lastPivot.price, 1)) * 100, -35, 35)
      : 0;

    return {
      waveId,
      direction,
      psychology,
      confidence: clamp(cycle.score + (inProgress ? 4 : 0), 0, 100),
      label: `${WAVE_LABELS_VI[waveId]} ${direction === "bull" ? "tăng" : "giảm"}`,
      inProgress,
      progress,
      pivotCount: pivots.length
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

    return resolveWaveId(cycle, endIndex, close);
  };

  const buildSwingCache = (series, deviationPct = 4) => detectSwings(series, deviationPct);

  return {
    WAVE_LABELS_VI,
    WAVE_PSYCHOLOGY,
    detectSwings,
    buildSwingCache,
    analyzeAt
  };
})();
