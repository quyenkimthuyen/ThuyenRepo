/* Pro mode: walk-forward ranking, Elliott validation, risk plan, cross-asset matrix. */
var ProAnalysis = (() => {
  const WALK_FORWARD_TRAIN_RATIO = 0.7;
  const MIN_TEST_REGIONS = 2;
  const RSI_PERIOD = 14;
  const TEN_YEAR_DAYS = 365 * 10;

  const ASSET_LABELS = {
    bitcoin: "Bitcoin",
    ethereum: "Ethereum",
    gold: "Vàng",
    sp500: "S&P 500"
  };

  const POSITION_BY_STANCE = {
    accumulate: { label: "25–40% NAV" },
    hold: { label: "10–25% NAV" },
    wait: { label: "0–10% NAV" },
    reduce: { label: "Giảm 30–50% hoặc hedge" }
  };

  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

  const getClose = (point) => point?.close ?? point?.price ?? 0;

  const buildRsiSeries = (series, period = RSI_PERIOD) => {
    if (!series?.length) {
      return [];
    }

    const values = [];
    let avgGain = 0;
    let avgLoss = 0;

    for (let index = 1; index < series.length; index += 1) {
      const change = getClose(series[index]) - getClose(series[index - 1]);
      const gain = change > 0 ? change : 0;
      const loss = change < 0 ? -change : 0;

      if (index < period) {
        avgGain += gain;
        avgLoss += loss;
        if (index === period - 1) {
          avgGain /= period;
          avgLoss /= period;
          const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
          values.push({ date: series[index].date, value: clamp(100 - 100 / (1 + rs), 0, 100) });
        }
        continue;
      }

      avgGain = (avgGain * (period - 1) + gain) / period;
      avgLoss = (avgLoss * (period - 1) + loss) / period;
      const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
      values.push({ date: series[index].date, value: clamp(100 - 100 / (1 + rs), 0, 100) });
    }

    return values;
  };

  const alignDailyRsi = (fullSeries, visibleSeries) => {
    const daily = PsychologyEngine.aggregateSeries(fullSeries, "1D");
    const dailyRsi = buildRsiSeries(daily);
    const byDate = new Map(dailyRsi.map((point) => [point.date, point.value]));
    let lastValue = 50;

    return visibleSeries.map((point) => {
      if (byDate.has(point.date)) {
        lastValue = byDate.get(point.date);
      } else {
        for (let index = dailyRsi.length - 1; index >= 0; index -= 1) {
          if (dailyRsi[index].date <= point.date) {
            lastValue = dailyRsi[index].value;
            break;
          }
        }
      }

      return { date: point.date, value: lastValue };
    });
  };

  const alignRsiForPro = (fullSeries, visibleSeries) => {
    const multi = PsychologyEngine.buildMultiFrameRsi(fullSeries);
    const aligned = PsychologyEngine.alignRsiToVisible(visibleSeries, multi);
    return {
      ...aligned,
      twoDay: alignDailyRsi(fullSeries, visibleSeries)
    };
  };

  const enrichPsychologyCache = (cache, fullSeries) => {
    if (!cache?.regions?.length) {
      return cache;
    }

    const daily = PsychologyEngine.aggregateSeries(fullSeries, "1D").slice(-TEN_YEAR_DAYS);
    const weekly = PsychologyEngine.aggregateSeries(daily, "1W");
    const model = ElliottEngine.buildWeeklyPsychologyModel(weekly, {
      rangeStart: cache.rangeStart,
      rangeEnd: cache.rangeEnd
    });
    const regions = ElliottEngine.annotateRegionsWithValidation(weekly, cache.regions, model.swings);
    const latestRegion = ElliottEngine.findRegionForDate(regions, cache.rangeEnd);

    return {
      ...cache,
      regions,
      summary: {
        zone: latestRegion.zone,
        label: PsychologyEngine.zoneLabelsVi[latestRegion.zone] || latestRegion.zone,
        confidence: latestRegion.confidence,
        elliottLabel: latestRegion.elliottLabel,
        elliottWave: latestRegion.waveId,
        elliottValidated: latestRegion.elliottValidated,
        validationNote: latestRegion.validationNote
      }
    };
  };

  const splitRegionsForWalkForward = (regions) => {
    const sorted = [...regions].sort((left, right) => left.startDate.localeCompare(right.startDate));

    if (sorted.length < 4) {
      return { train: sorted, test: [], splitDate: null };
    }

    const splitIndex = Math.max(1, Math.floor(sorted.length * WALK_FORWARD_TRAIN_RATIO));
    const splitDate = sorted[splitIndex]?.startDate || null;

    return {
      splitDate,
      train: sorted.slice(0, splitIndex),
      test: sorted.slice(splitIndex)
    };
  };

  const buildWalkForwardRanking = (cache, fullSeries) => {
    const { train, test, splitDate } = splitRegionsForWalkForward(cache.regions);
    const testCache = { ...cache, regions: test };
    const testRanking = test.length >= MIN_TEST_REGIONS
      ? InvestmentAdvisor.buildZoneRanking(testCache, fullSeries)
      : null;

    return {
      splitDate,
      trainRegionCount: train.length,
      testRegionCount: test.length,
      testRanking,
      usesOutOfSample: Boolean(testRanking)
    };
  };

  const computeAtr = (series, period = 14) => {
    if (!series?.length || series.length < period + 1) {
      return null;
    }

    let sum = 0;
    for (let index = series.length - period; index < series.length; index += 1) {
      const high = series[index].high ?? getClose(series[index]);
      const low = series[index].low ?? getClose(series[index]);
      const prevClose = getClose(series[index - 1]);
      const tr = Math.max(high - low, Math.abs(high - prevClose), Math.abs(low - prevClose));
      sum += tr;
    }

    return sum / period;
  };

  const buildRiskPlan = (stance, visibleData) => {
    const atr = computeAtr(visibleData) ?? 0;
    const close = getClose(visibleData.at(-1));
    const atrPct = close ? (atr / close) * 100 : 0;
    const isDefensive = stance === "reduce" || stance === "wait";
    const invalidation = isDefensive ? close + 2 * atr : close - 2 * atr;

    return {
      positionLabel: POSITION_BY_STANCE[stance]?.label || POSITION_BY_STANCE.wait.label,
      invalidationPrice: Number(invalidation.toFixed(2)),
      horizonWeeks: 8,
      atrPct: Number(atrPct.toFixed(2)),
      note: "Invalidation theo 2×ATR(14) trên khung đang xem · không phải lời khuyên tài chính"
    };
  };

  const computeVolumeProxy = (visibleData) => {
    if (!visibleData?.length) {
      return 50;
    }

    const returns = [];
    for (let index = 1; index < visibleData.length; index += 1) {
      const prev = getClose(visibleData[index - 1]);
      const curr = getClose(visibleData[index]);
      if (prev) {
        returns.push(Math.abs((curr - prev) / prev));
      }
    }

    const avg = returns.length
      ? returns.reduce((sum, value) => sum + value, 0) / returns.length
      : 0;

    return Math.round(clamp(35 + avg * 1200, 30, 98));
  };

  const buildVolumeProxySeries = (visibleData) => visibleData.map((point, index) => {
    const slice = visibleData.slice(Math.max(0, index - 13), index + 1);
    const proxy = computeVolumeProxy(slice);
    return {
      time: point.date,
      value: proxy,
      color: proxy >= 65 ? "rgba(251, 113, 133, 0.45)" : "rgba(91, 156, 245, 0.35)"
    };
  });

  const buildDataQualityNotes = (fullSeries, cache) => {
    const daily = PsychologyEngine.aggregateSeries(fullSeries, "1D");
    const spanYears = daily.length / 365;
    const notes = [];

    if (spanYears < 8) {
      notes.push(`Lịch sử ~${spanYears.toFixed(1)} năm — walk-forward có thể thiếu mẫu`);
    }

    if (cache?.dataEndDate && daily.at(-1)?.date !== cache.dataEndDate) {
      notes.push("Cache tâm lý có thể cũ hơn giá mới nhất — nên phân tích lại");
    }

    notes.push("Dữ liệu Yahoo/CORS · không có volume thật (dùng proxy biến động)");

    return notes;
  };

  const findIndexOnOrAfter = (series, date) => {
    for (let index = 0; index < series.length; index += 1) {
      if (series[index].date >= date) {
        return index;
      }
    }

    return -1;
  };

  const forwardReturnPct = (series, startIndex, weeks = 8) => {
    const endIndex = Math.min(startIndex + weeks * 7, series.length - 1);
    if (startIndex < 0 || endIndex <= startIndex) {
      return null;
    }

    const startPrice = getClose(series[startIndex]);
    const endPrice = getClose(series[endIndex]);
    if (!startPrice) {
      return null;
    }

    return ((endPrice - startPrice) / startPrice) * 100;
  };

  const movingAverage = (series, period, endIndex = series.length - 1) => {
    if (endIndex < period - 1) {
      return null;
    }

    let sum = 0;
    for (let index = endIndex - period + 1; index <= endIndex; index += 1) {
      sum += getClose(series[index]);
    }

    return sum / period;
  };

  const buildMacroContext = (fullSeries) => {
    const daily = PsychologyEngine.aggregateSeries(fullSeries, "1D");
    return buildMacroContextFromDaily(daily);
  };

  const buildMacroContextFromDaily = (daily) => {
    if (daily.length < 60) {
      return null;
    }

    const endIndex = daily.length - 1;
    const close = getClose(daily[endIndex]);
    const ma50 = movingAverage(daily, 50, endIndex);
    const ma200 = movingAverage(daily, 200, endIndex);
    const lookback = Math.min(252, daily.length - 1);
    const swingHigh = Math.max(...daily.slice(endIndex - lookback, endIndex + 1).map(getClose));
    const drawdown = swingHigh > 0 ? ((close - swingHigh) / swingHigh) * 100 : 0;
    const volRecent = [];
    for (let index = Math.max(1, endIndex - 19); index <= endIndex; index += 1) {
      const prev = getClose(daily[index - 1]);
      if (prev) {
        volRecent.push(Math.abs((getClose(daily[index]) - prev) / prev));
      }
    }
    const volBaseline = [];
    for (let index = Math.max(1, endIndex - 59); index <= endIndex; index += 1) {
      const prev = getClose(daily[index - 1]);
      if (prev) {
        volBaseline.push(Math.abs((getClose(daily[index]) - prev) / prev));
      }
    }
    const recentVol = volRecent.length
      ? volRecent.reduce((sum, value) => sum + value, 0) / volRecent.length
      : 0;
    const baseVol = volBaseline.length
      ? volBaseline.reduce((sum, value) => sum + value, 0) / volBaseline.length
      : recentVol;
    const volRatio = baseVol > 0 ? recentVol / baseVol : 1;
    const volatilityRegime = volRatio >= 1.25 ? "cao" : volRatio <= 0.8 ? "thấp" : "bình thường";

    return {
      close: Number(close.toFixed(2)),
      drawdown: Number(drawdown.toFixed(1)),
      aboveMa50: ma50 ? close > ma50 : null,
      aboveMa200: ma200 ? close > ma200 : null,
      goldenCross: ma50 && ma200 ? ma50 > ma200 : null,
      volatilityRegime,
      summary: [
        `Drawdown ${drawdown.toFixed(1)}% từ đỉnh ~1 năm`,
        ma50 && ma200
          ? (close > ma200 ? "Trên MA200" : "Dưới MA200")
          : null,
        `Biến động ${volatilityRegime}`
      ].filter(Boolean).join(" · ")
    };
  };

  const buildWalkForwardDetail = (cache, fullSeries, zone) => {
    const { train, test, splitDate } = splitRegionsForWalkForward(cache.regions);
    const trainStats = InvestmentAdvisor.buildHistoricalZoneStats({ ...cache, regions: train }, fullSeries);
    const testStats = InvestmentAdvisor.buildHistoricalZoneStats({ ...cache, regions: test }, fullSeries);
    const trainZone = trainStats.find((item) => item.zone === zone) || null;
    const testZone = testStats.find((item) => item.zone === zone) || null;
    const edge = trainZone && testZone
      ? Number((testZone.avgForward - trainZone.avgForward).toFixed(2))
      : null;

    return {
      splitDate,
      trainRegionCount: train.length,
      testRegionCount: test.length,
      trainZone,
      testZone,
      edge,
      generalizes: testZone ? testZone.avgForward > 0 && testZone.winRate >= 50 : null
    };
  };

  const buildHistoricalAnalogs = (cache, fullSeries, zone, limit = 3) => {
    const { test } = splitRegionsForWalkForward(cache.regions);
    const daily = PsychologyEngine.aggregateSeries(fullSeries, "1D");
    const analogs = test
      .filter((region) => region.zone === zone)
      .slice(-limit)
      .map((region) => {
        const startIndex = findIndexOnOrAfter(daily, region.startDate);
        const forward = forwardReturnPct(daily, startIndex);

        return {
          date: region.startDate,
          elliottLabel: region.elliottLabel,
          forwardReturn: forward === null ? null : Number(forward.toFixed(2)),
          validated: region.elliottValidated
        };
      })
      .filter((item) => item.forwardReturn !== null);

    const avgForward = analogs.length
      ? Number((analogs.reduce((sum, item) => sum + item.forwardReturn, 0) / analogs.length).toFixed(2))
      : null;

    return { items: analogs, avgForward, sampleCount: analogs.length };
  };

  const buildScenarios = (visibleData, stance, riskPlan) => {
    const close = getClose(visibleData.at(-1));
    const atr = computeAtr(visibleData) ?? close * 0.02;
    const isDefensive = stance === "reduce" || stance === "wait";
    const bullTarget = Number((close + atr * 1.8).toFixed(2));
    const baseTarget = Number((close + (isDefensive ? -atr * 0.4 : atr * 0.6)).toFixed(2));
    const risk = Math.abs(close - riskPlan.invalidationPrice) || atr * 2;
    const reward = Math.abs(bullTarget - close);
    const riskReward = risk > 0 ? Number((reward / risk).toFixed(2)) : null;

    return {
      bullTarget,
      baseTarget,
      invalidation: riskPlan.invalidationPrice,
      riskReward,
      horizonWeeks: riskPlan.horizonWeeks
    };
  };

  const buildProSignalScore = (enriched, walkForwardDetail, macro, crossAsset, snapshot, stance) => {
    const rsi1d = snapshot.rsiByInterval?.twoDay ?? snapshot.rsi ?? 50;
    const factors = [];

    factors.push({
      id: "elliott",
      label: "Elliott xác thực",
      pass: enriched.summary.elliottValidated === true,
      weight: 20,
      detail: enriched.summary.validationNote || enriched.summary.elliottLabel
    });

    const testZone = walkForwardDetail.testZone;
    factors.push({
      id: "oos",
      label: "Out-of-sample",
      pass: Boolean(testZone && testZone.samples >= MIN_TEST_REGIONS && testZone.avgForward > 0),
      weight: 20,
      detail: testZone
        ? `${testZone.samples} mẫu · TB +${testZone.avgForward}% / 8 tuần`
        : "Chưa đủ mẫu test"
    });

    const rsiPass = stance === "accumulate"
      ? rsi1d < 65
      : stance === "reduce"
        ? rsi1d > 55
        : rsi1d >= 35 && rsi1d <= 65;
    factors.push({
      id: "rsi",
      label: "RSI 1D khớp stance",
      pass: rsiPass,
      weight: 15,
      detail: `RSI 1D = ${Math.round(rsi1d)}`
    });

    const macroPass = stance === "accumulate"
      ? macro?.aboveMa200 === true
      : stance === "reduce"
        ? macro?.aboveMa200 === false || (macro?.drawdown ?? 0) > -8
        : true;
    factors.push({
      id: "macro",
      label: "Bối cảnh vĩ mô",
      pass: macroPass,
      weight: 15,
      detail: macro?.summary || "Thiếu dữ liệu MA"
    });

    const currentRow = crossAsset?.rows?.find((row) => row.isCurrent);
    const alignedAssets = crossAsset?.rows?.filter((row) => row.stance === stance).length ?? 0;
    factors.push({
      id: "cross",
      label: "Đa tài sản",
      pass: alignedAssets >= 2 || currentRow?.stance === stance,
      weight: 15,
      detail: `${alignedAssets}/4 tài sản cùng hướng ${stance}`
    });

    factors.push({
      id: "edge",
      label: "Walk-forward edge",
      pass: walkForwardDetail.edge === null ? false : walkForwardDetail.edge >= 0,
      weight: 15,
      detail: walkForwardDetail.edge === null
        ? "Chưa tính được edge"
        : `Test vs train: ${walkForwardDetail.edge >= 0 ? "+" : ""}${walkForwardDetail.edge}%`
    });

    const score = factors.reduce((sum, factor) => sum + (factor.pass ? factor.weight : 0), 0);
    const grade = score >= 80 ? "A" : score >= 65 ? "B" : score >= 50 ? "C" : "D";

    return {
      score,
      grade,
      label: grade === "A" ? "Tín hiệu mạnh" : grade === "B" ? "Khả thi" : grade === "C" ? "Yếu" : "Tránh",
      factors
    };
  };

  const buildProBrief = (cache, fullSeries, snapshot, visibleData, crossAsset, stance) => {
    const enriched = enrichPsychologyCache(cache, fullSeries);
    const walkForwardDetail = buildWalkForwardDetail(enriched, fullSeries, enriched.summary.zone);
    const macro = buildMacroContext(fullSeries);
    const analogs = buildHistoricalAnalogs(enriched, fullSeries, enriched.summary.zone);
    const riskPlan = buildRiskPlan(stance, visibleData.length ? visibleData : fullSeries.slice(-90));
    const scenarios = buildScenarios(visibleData.length ? visibleData : fullSeries.slice(-90), stance, riskPlan);
    const signal = buildProSignalScore(
      enriched,
      walkForwardDetail,
      macro,
      crossAsset,
      snapshot,
      stance
    );

    return {
      signal,
      macro,
      walkForwardDetail,
      analogs,
      scenarios,
      riskPlan
    };
  };

  const buildAtrBands = (series, period = 14, multiplier = 2) => {
    if (!series?.length) {
      return { upper: [], lower: [] };
    }

    const upper = [];
    const lower = [];

    series.forEach((point, index) => {
      const slice = series.slice(0, index + 1);
      const atr = computeAtr(slice, period) ?? 0;
      const close = getClose(point);
      upper.push({ time: point.date, value: Number((close + multiplier * atr).toFixed(4)) });
      lower.push({ time: point.date, value: Number((close - multiplier * atr).toFixed(4)) });
    });

    return { upper, lower };
  };

  const resolveDailyIndex = (daily, date) => {
    for (let index = daily.length - 1; index >= 0; index -= 1) {
      if (daily[index].date <= date) {
        return index;
      }
    }

    return -1;
  };

  const resolveRsiValue = (rsiByDate, daily, date) => {
    const index = resolveDailyIndex(daily, date);
    if (index < 0) {
      return 50;
    }

    return rsiByDate.get(daily[index].date) ?? 50;
  };

  const buildEnrichedCaches = (psychologyCaches, marketData) => Object.fromEntries(
    Object.keys(psychologyCaches).map((asset) => {
      const cache = psychologyCaches[asset];
      const series = marketData[asset] || [];
      return [
        asset,
        cache?.regions?.length && series.length
          ? enrichPsychologyCache(cache, series)
          : null
      ];
    })
  );

  const buildCrossAssetAtDate = (enrichedByAsset, currentAsset, date) => {
    const rows = Object.entries(enrichedByAsset).map(([asset, enriched]) => {
      if (!enriched) {
        return null;
      }

      const region = ElliottEngine.findRegionForDate(enriched.regions, date);
      const profile = InvestmentAdvisor.ZONE_EXPERT[region.zone]
        || InvestmentAdvisor.ZONE_EXPERT.Observing;

      return {
        asset,
        stance: profile.stance,
        isCurrent: asset === currentAsset
      };
    }).filter(Boolean);

    const stanceCounts = rows.reduce((acc, row) => {
      acc[row.stance] = (acc[row.stance] || 0) + 1;
      return acc;
    }, {});

    return {
      rows,
      dominantStance: Object.entries(stanceCounts).sort((left, right) => right[1] - left[1])[0]?.[0] || null
    };
  };

  const buildSignalScoreAtDate = (
    enrichedCache,
    fullSeries,
    date,
    daily,
    rsiByDate,
    enrichedByAsset,
    currentAsset
  ) => {
    const region = ElliottEngine.findRegionForDate(enrichedCache.regions, date);
    const zone = region?.zone || "Observing";
    const stance = InvestmentAdvisor.ZONE_EXPERT[zone]?.stance || "wait";
    const dailyIndex = resolveDailyIndex(daily, date);
    const dailySlice = dailyIndex >= 0 ? daily.slice(0, dailyIndex + 1) : daily;
    const completedRegions = enrichedCache.regions.filter((item) => item.endDate < date);
    const walkForwardDetail = buildWalkForwardDetail(
      { ...enrichedCache, regions: completedRegions },
      fullSeries,
      zone
    );
    const macro = buildMacroContextFromDaily(dailySlice);
    const rsi1d = resolveRsiValue(rsiByDate, daily, date);
    const crossAsset = buildCrossAssetAtDate(enrichedByAsset, currentAsset, date);
    const snapshot = {
      zone,
      label: PsychologyEngine.zoneLabelsVi[zone] || zone,
      rsi: rsi1d,
      rsiByInterval: { twoDay: rsi1d, weekly: 50, monthly: 50 }
    };

    return buildProSignalScore(
      {
        summary: {
          zone,
          elliottValidated: region?.elliottValidated,
          validationNote: region?.validationNote
        }
      },
      walkForwardDetail,
      macro,
      crossAsset,
      snapshot,
      stance
    );
  };

  const buildSignalScoreSeries = (
    cache,
    fullSeries,
    visibleData,
    psychologyCaches,
    marketData,
    currentAsset
  ) => {
    if (!cache?.regions?.length || !visibleData?.length) {
      return [];
    }

    const enrichedCache = enrichPsychologyCache(cache, fullSeries);
    const daily = PsychologyEngine.aggregateSeries(fullSeries, "1D");
    const rsiByDate = new Map(buildRsiSeries(daily).map((point) => [point.date, point.value]));
    const enrichedByAsset = buildEnrichedCaches(psychologyCaches, marketData);
    const step = visibleData.length > 420 ? Math.ceil(visibleData.length / 420) : 1;
    let lastScore = 50;
    let lastGrade = "C";

    return visibleData.map((point, index) => {
      const shouldCompute = index % step === 0 || index === visibleData.length - 1;

      if (shouldCompute) {
        const signal = buildSignalScoreAtDate(
          enrichedCache,
          fullSeries,
          point.date,
          daily,
          rsiByDate,
          enrichedByAsset,
          currentAsset
        );
        lastScore = signal.score;
        lastGrade = signal.grade;
      }

      return {
        date: point.date,
        value: lastScore,
        grade: lastGrade
      };
    });
  };

  const buildCrossAssetMatrix = (psychologyCaches, marketData, currentAsset) => {
    const rows = Object.keys(psychologyCaches).map((asset) => {
      const cache = psychologyCaches[asset];
      const series = marketData[asset] || [];

      if (!cache?.summary || !series.length) {
        return {
          asset,
          label: ASSET_LABELS[asset] || asset,
          zone: null,
          stance: null,
          isCurrent: asset === currentAsset
        };
      }

      const enriched = enrichPsychologyCache(cache, series);
      const profile = InvestmentAdvisor.ZONE_EXPERT[enriched.summary.zone]
        || InvestmentAdvisor.ZONE_EXPERT.Observing;

      return {
        asset,
        label: ASSET_LABELS[asset] || asset,
        zone: enriched.summary.zone,
        zoneLabel: enriched.summary.label,
        color: PsychologyEngine.zoneColors[enriched.summary.zone],
        stance: profile.stance,
        stanceLabel: { accumulate: "Tích lũy", hold: "Nắm giữ", wait: "Chờ", reduce: "Giảm" }[profile.stance],
        elliottValidated: enriched.summary.elliottValidated,
        isCurrent: asset === currentAsset
      };
    });

    const stanceCounts = rows.reduce((acc, row) => {
      if (row.stance) {
        acc[row.stance] = (acc[row.stance] || 0) + 1;
      }
      return acc;
    }, {});

    const dominantStance = Object.entries(stanceCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || null;

    return {
      rows,
      dominantStance,
      correlationNote: dominantStance === "reduce"
        ? "Nhiều tài sản ở vùng giảm rủi ro — hạn chế tăng beta tổng thể"
        : dominantStance === "accumulate"
          ? "Nhiều tài sản ở vùng tích lũy — cơ hội phân bổ nhưng cần kiểm soát tương quan"
          : "Tín hiệu đa tài sản chưa đồng nhất"
    };
  };

  const refineProAction = (snapshot, profile, walkForward) => {
    const rsi = snapshot.rsi ?? 50;
    let action = profile.action;
    let detail = `Vùng ${snapshot.label || snapshot.zone} · độ khớp mô hình ${snapshot.confidence ?? 0}%`;

    if (snapshot.elliottValidated === false) {
      action = "Chờ xác thực sóng Elliott trước khi tăng vị thế";
      detail += ` · ${snapshot.validationNote || "Sóng chưa xác thực"}`;
    }

    if (walkForward?.usesOutOfSample) {
      detail += ` · Xếp hạng từ ${walkForward.testRegionCount} giai đoạn out-of-sample`;
    } else {
      detail += " · Chưa đủ mẫu out-of-sample, dùng expert + in-sample";
    }

    if (profile.stance === "accumulate" && rsi > 68) {
      action = "Chờ điều chỉnh — RSI 1D cao";
    }

    if (profile.stance === "reduce" && (rsi > 70 || (snapshot.trend ?? 0) > 8)) {
      action = "Giảm vị thế — RSI/xu hướng quá nóng";
    }

    return {
      action,
      detail,
      stance: profile.stance,
      stanceLabel: { accumulate: "Tích lũy", hold: "Nắm giữ", wait: "Chờ đợi", reduce: "Giảm vị thế" }[profile.stance]
    };
  };

  const buildProRecommendation = (cache, fullSeries, snapshot, visibleData = [], crossAsset = null) => {
    if (!cache?.regions?.length || !fullSeries?.length) {
      return { hasAdvice: false, mode: "pro" };
    }

    const enrichedCache = enrichPsychologyCache(cache, fullSeries);
    const walkForward = buildWalkForwardRanking(enrichedCache, fullSeries);
    const ranking = walkForward.testRanking || InvestmentAdvisor.buildZoneRanking(enrichedCache, fullSeries);
    const currentZone = enrichedCache.summary?.zone || snapshot?.zone || "Observing";
    const currentProfile = InvestmentAdvisor.ZONE_EXPERT[currentZone]
      || InvestmentAdvisor.ZONE_EXPERT.Observing;
    const currentRank = ranking.all.find((item) => item.zone === currentZone) || {
      zone: currentZone,
      label: PsychologyEngine.zoneLabelsVi[currentZone] || currentZone,
      color: PsychologyEngine.zoneColors[currentZone],
      safety: currentProfile.safety,
      effectiveness: currentProfile.effectiveness,
      composite: Math.round(currentProfile.safety * 0.45 + currentProfile.effectiveness * 0.55),
      samples: 0
    };

    const proSnapshot = {
      ...snapshot,
      zone: currentZone,
      label: enrichedCache.summary.label,
      confidence: enrichedCache.summary.confidence,
      elliottLabel: enrichedCache.summary.elliottLabel,
      elliottValidated: enrichedCache.summary.elliottValidated,
      validationNote: enrichedCache.summary.validationNote
    };

    const current = refineProAction(proSnapshot, currentProfile, walkForward);
    const riskPlan = buildRiskPlan(current.stance, visibleData.length ? visibleData : fullSeries.slice(-90));
    const walkForwardDetail = buildWalkForwardDetail(enrichedCache, fullSeries, currentZone);
    const macro = buildMacroContext(fullSeries);
    const analogs = buildHistoricalAnalogs(enrichedCache, fullSeries, currentZone);
    const scenarios = buildScenarios(
      visibleData.length ? visibleData : fullSeries.slice(-90),
      current.stance,
      riskPlan
    );
    const signal = buildProSignalScore(
      enrichedCache,
      walkForwardDetail,
      macro,
      crossAsset,
      proSnapshot,
      current.stance
    );

    return {
      hasAdvice: true,
      mode: "pro",
      rankingSource: walkForward.usesOutOfSample ? "out-of-sample" : "in-sample-fallback",
      walkForward,
      walkForwardDetail,
      signal,
      macro,
      analogs,
      scenarios,
      currentZone,
      currentLabel: currentRank.label,
      currentColor: currentRank.color,
      currentSafety: currentRank.safety,
      currentEffectiveness: currentRank.effectiveness,
      action: current.action,
      actionDetail: current.detail,
      stance: current.stance,
      stanceLabel: current.stanceLabel,
      safestZone: ranking.safest,
      mostEffectiveZone: ranking.mostEffective,
      topAccumulateZones: ranking.topAccumulate.slice(0, 3),
      avoidZones: ranking.avoid.slice(0, 2),
      zoneRanking: ranking.all,
      riskPlan,
      elliottValidated: enrichedCache.summary.elliottValidated,
      validationNote: enrichedCache.summary.validationNote
    };
  };

  const buildModeComparison = (basicAdvice, proAdvice) => {
    if (!basicAdvice?.hasAdvice || !proAdvice?.hasAdvice) {
      return null;
    }

    const sameStance = basicAdvice.stance === proAdvice.stance;

    return {
      basicAction: basicAdvice.action,
      basicStance: basicAdvice.stanceLabel,
      proAction: proAdvice.action,
      proStance: proAdvice.stanceLabel,
      sameStance,
      rankingSource: proAdvice.rankingSource,
      testSamples: proAdvice.walkForward?.testRegionCount ?? 0,
      splitDate: proAdvice.walkForward?.splitDate,
      elliottValidated: proAdvice.elliottValidated,
      proScore: proAdvice.signal?.score ?? null,
      proGrade: proAdvice.signal?.grade ?? null,
      proScoreLabel: proAdvice.signal?.label ?? null,
      note: sameStance
        ? `Hai mode đồng ý · Pro score ${proAdvice.signal?.score ?? "—"}/100 (${proAdvice.signal?.grade ?? "—"})`
        : `Khác biệt · Pro score ${proAdvice.signal?.score ?? "—"}/100 — walk-forward + Elliott + macro`
    };
  };

  const enhanceMarketSnapshot = (snapshot, cache, fullSeries, visibleData, crossAsset = null, proAdvice = null) => {
    const enriched = enrichPsychologyCache(cache, fullSeries);
    const daily = PsychologyEngine.aggregateSeries(fullSeries, "1D");
    const dailyRsi = buildRsiSeries(daily);
    const lastDailyRsi = dailyRsi.at(-1)?.value ?? snapshot.rsiByInterval?.twoDay ?? 50;

    return {
      ...snapshot,
      zone: enriched.summary.zone,
      label: enriched.summary.label,
      confidence: enriched.summary.confidence,
      confidenceLabel: "độ khớp mô hình",
      elliottLabel: enriched.summary.elliottLabel,
      elliottValidated: enriched.summary.elliottValidated,
      validationNote: enriched.summary.validationNote,
      rsi: Math.round((lastDailyRsi + (snapshot.rsiByInterval?.weekly ?? 50) + (snapshot.rsiByInterval?.monthly ?? 50)) / 3),
      rsiByInterval: {
        twoDay: lastDailyRsi,
        weekly: snapshot.rsiByInterval?.weekly ?? 50,
        monthly: snapshot.rsiByInterval?.monthly ?? 50
      },
      rsiIntervalLabels: { twoDay: "1D", weekly: "T", monthly: "Th" },
      rsiNote: "RSI 1D chuẩn (Pro) thay cho 2D",
      volumeProxy: computeVolumeProxy(visibleData),
      dataQuality: buildDataQualityNotes(fullSeries, cache),
      proBrief: proAdvice
        ? {
          signal: proAdvice.signal,
          macro: proAdvice.macro,
          walkForwardDetail: proAdvice.walkForwardDetail,
          analogs: proAdvice.analogs,
          scenarios: proAdvice.scenarios,
          riskPlan: proAdvice.riskPlan
        }
        : buildProBrief(
          cache,
          fullSeries,
          snapshot,
          visibleData,
          crossAsset,
          InvestmentAdvisor.ZONE_EXPERT[enriched.summary.zone]?.stance || "wait"
        )
    };
  };

  const renderProBrief = (container, brief) => {
    if (!container) {
      return;
    }

    if (!brief?.signal) {
      container.innerHTML = "";
      container.hidden = true;
      return;
    }

    const factorChips = brief.signal.factors.map((factor) => `
      <span class="pro-factor ${factor.pass ? "is-pass" : "is-fail"}" title="${factor.detail}">
        ${factor.pass ? "✓" : "✗"} ${factor.label}
      </span>
    `).join("");

    const analogRows = brief.analogs?.items?.length
      ? brief.analogs.items.map((item) => `
        <span class="pro-analog">
          ${item.date} · <em>${item.forwardReturn > 0 ? "+" : ""}${item.forwardReturn}%</em>
        </span>
      `).join("")
      : "<span class='pro-analog'>Chưa có analog OOS cho vùng này</span>";

    container.hidden = false;
    container.innerHTML = `
      <div class="pro-brief-panel">
        <div class="pro-score-block">
          <div class="pro-score-ring" style="--score: ${brief.signal.score}">
            <strong>${brief.signal.score}</strong>
            <span>${brief.signal.grade}</span>
          </div>
          <div>
            <p class="pro-brief-kicker">Pro Signal Score</p>
            <h2 class="pro-brief-title">${brief.signal.label}</h2>
            <p class="pro-brief-macro">${brief.macro?.summary || ""}</p>
          </div>
        </div>
        <div class="pro-factor-list">${factorChips}</div>
        <div class="pro-brief-grid">
          <article>
            <span>Kịch bản 8 tuần</span>
            <strong>Lên ${brief.scenarios?.bullTarget ?? "—"}</strong>
            <small>R:R ≈ ${brief.scenarios?.riskReward ?? "—"} · invalidation ${brief.scenarios?.invalidation ?? "—"}</small>
          </article>
          <article>
            <span>Walk-forward</span>
            <strong>${brief.walkForwardDetail?.testZone?.avgForward != null ? `${brief.walkForwardDetail.testZone.avgForward > 0 ? "+" : ""}${brief.walkForwardDetail.testZone.avgForward}%` : "—"}</strong>
            <small>Test ${brief.walkForwardDetail?.testRegionCount ?? 0} giai đoạn · edge ${brief.walkForwardDetail?.edge ?? "—"}%</small>
          </article>
          <article>
            <span>Analog lịch sử (OOS)</span>
            <strong>${brief.analogs?.avgForward != null ? `${brief.analogs.avgForward > 0 ? "+" : ""}${brief.analogs.avgForward}%` : "—"}</strong>
            <div class="pro-analog-list">${analogRows}</div>
          </article>
        </div>
      </div>
    `;
  };

  const renderModeComparison = (container, comparison, appMode) => {
    if (!container) {
      return;
    }

    if (!comparison) {
      container.innerHTML = "";
      container.hidden = true;
      return;
    }

    container.hidden = false;
    container.innerHTML = `
      <div class="mode-compare-panel">
        <header class="mode-compare-head">
          <div>
            <p class="mode-compare-kicker">So sánh mode</p>
            <h2 class="mode-compare-title">Basic vs Pro · đang xem: <strong>${appMode === "pro" ? "Pro" : "Basic"}</strong></h2>
          </div>
          <span class="mode-compare-badge ${comparison.sameStance ? "is-match" : "is-diff"}">
            ${comparison.sameStance ? "Đồng thuận" : "Khác biệt"}
          </span>
        </header>
        <div class="mode-compare-grid">
          <article class="mode-compare-card mode-compare-card--basic">
            <span class="mode-compare-label">Basic</span>
            <strong>${comparison.basicStance}</strong>
            <p>${comparison.basicAction}</p>
            <small>In-sample 8 tuần + expert · Elliott heuristic</small>
          </article>
          <article class="mode-compare-card mode-compare-card--pro">
            <span class="mode-compare-label">Pro</span>
            <strong>${comparison.proStance}</strong>
            <p>${comparison.proAction}</p>
            <small>
              Score ${comparison.proScore ?? "—"}/100 (${comparison.proGrade ?? "—"})
              · ${comparison.rankingSource === "out-of-sample"
    ? `OOS ${comparison.testSamples} giai đoạn`
    : "Fallback in-sample"}
            </small>
          </article>
        </div>
        <p class="mode-compare-note">${comparison.note}</p>
      </div>
    `;
  };

  const renderProPanel = (container, advice, crossAsset = null) => {
    if (!container) {
      return;
    }

    if (!advice?.hasAdvice) {
      container.innerHTML = `
        <div class="investment-panel investment-panel--empty investment-panel--pro">
          <p class="investment-kicker">Khuyến nghị Pro</p>
          <p class="investment-empty">Bấm <strong>Phân tích 10 năm</strong> để kích hoạt walk-forward, xác thực Elliott và khung rủi ro.</p>
        </div>
      `;
      return;
    }

    const zoneCard = (item, metricLabel, metricValue) => `
      <article class="investment-zone-card" style="--zone-color: ${item.color}">
        <span class="investment-zone-name">${item.label}</span>
        <strong class="investment-zone-metric">${metricValue}</strong>
        <small>${metricLabel}${item.samples ? ` · ${item.samples} giai đoạn` : ""}${advice.rankingSource === "out-of-sample" ? " · OOS" : ""}</small>
      </article>
    `;

    const rankingRows = advice.zoneRanking
      .filter((item) => item.stance === "accumulate" || item.stance === "hold")
      .slice(0, 5)
      .map((item) => `
        <div class="investment-rank-row">
          <span class="investment-rank-dot" style="background: ${item.color}"></span>
          <span class="investment-rank-name">${item.label}</span>
          <span class="investment-rank-bar" aria-hidden="true">
            <i style="width: ${item.composite}%; background: ${item.color}"></i>
          </span>
          <span class="investment-rank-score">${item.composite}</span>
        </div>
      `).join("");

    const crossAssetRows = crossAsset?.rows?.filter((row) => row.zone).map((row) => `
      <div class="cross-asset-row ${row.isCurrent ? "is-current" : ""}">
        <span>${row.label}</span>
        <span class="cross-asset-zone" style="color: ${row.color}">${row.zoneLabel}</span>
        <span class="cross-asset-stance">${row.stanceLabel}</span>
        ${row.elliottValidated === false ? '<span class="cross-asset-warn">!</span>' : ""}
      </div>
    `).join("") || "";

    const factorRows = advice.signal?.factors?.map((factor) => `
      <div class="pro-factor-row ${factor.pass ? "is-pass" : "is-fail"}">
        <span>${factor.pass ? "✓" : "✗"} ${factor.label}</span>
        <em>${factor.detail}</em>
      </div>
    `).join("") || "";

    const wf = advice.walkForwardDetail;
    const analogItems = advice.analogs?.items?.map((item) => `
      <span class="pro-analog">${item.date}: ${item.forwardReturn > 0 ? "+" : ""}${item.forwardReturn}%</span>
    `).join("") || "<span class='pro-analog'>Không có analog OOS</span>";

    container.innerHTML = `
      <div class="investment-panel investment-panel--pro">
        <header class="investment-head">
          <div>
            <p class="investment-kicker">Khuyến nghị Pro</p>
            <h2 class="investment-title">Score ${advice.signal?.score ?? "—"}/100 · ${advice.signal?.label ?? "—"}</h2>
          </div>
          <span class="investment-stance investment-stance--${advice.stance}">${advice.stanceLabel}</span>
        </header>

        <article class="investment-action-card">
          <span class="investment-label">Hành động hiện tại</span>
          <strong style="color: ${advice.currentColor}">${advice.action}</strong>
          <p>${advice.actionDetail}</p>
          <div class="investment-current-metrics">
            <span>An toàn <em>${advice.currentSafety}</em></span>
            <span>Hiệu quả <em>${advice.currentEffectiveness}</em></span>
            <span>Độ khớp mô hình <em>${advice.elliottValidated === false ? "thấp" : "ổn"}</em></span>
          </div>
        </article>

        <article class="investment-risk-card">
          <span class="investment-label">Kế hoạch rủi ro</span>
          <div class="investment-risk-grid">
            <div><span>Vị thế gợi ý</span><strong>${advice.riskPlan.positionLabel}</strong></div>
            <div><span>Invalidation</span><strong>${advice.riskPlan.invalidationPrice}</strong></div>
            <div><span>Chân trời</span><strong>${advice.riskPlan.horizonWeeks} tuần</strong></div>
            <div><span>ATR%</span><strong>${advice.riskPlan.atrPct}%</strong></div>
          </div>
          <p class="investment-note">${advice.riskPlan.note}</p>
        </article>

        <section class="investment-section">
          <h3>Đồng thuận tín hiệu (6 yếu tố)</h3>
          <div class="pro-factor-rows">${factorRows}</div>
        </section>

        <section class="investment-section">
          <h3>Kịch bản &amp; R:R (8 tuần)</h3>
          <div class="investment-risk-grid">
            <div><span>Mục tiêu lạc quan</span><strong>${advice.scenarios?.bullTarget ?? "—"}</strong></div>
            <div><span>Kịch bản cơ sở</span><strong>${advice.scenarios?.baseTarget ?? "—"}</strong></div>
            <div><span>R:R</span><strong>${advice.scenarios?.riskReward ?? "—"}</strong></div>
            <div><span>Macro</span><strong>${advice.macro?.drawdown ?? "—"}%</strong></div>
          </div>
        </section>

        <section class="investment-section">
          <h3>Walk-forward minh bạch (train vs test)</h3>
          <div class="wf-compare-grid">
            <article>
              <span>Train (in-sample)</span>
              <strong>${wf?.trainZone?.avgForward != null ? `${wf.trainZone.avgForward > 0 ? "+" : ""}${wf.trainZone.avgForward}%` : "—"}</strong>
              <small>${wf?.trainZone?.samples ?? 0} mẫu · win ${wf?.trainZone?.winRate ?? "—"}%</small>
            </article>
            <article>
              <span>Test (out-of-sample)</span>
              <strong>${wf?.testZone?.avgForward != null ? `${wf.testZone.avgForward > 0 ? "+" : ""}${wf.testZone.avgForward}%` : "—"}</strong>
              <small>${wf?.testZone?.samples ?? 0} mẫu · edge ${wf?.edge ?? "—"}%</small>
            </article>
          </div>
        </section>

        <section class="investment-section">
          <h3>Analog lịch sử (chỉ tập test)</h3>
          <div class="pro-analog-list">${analogItems}</div>
          <p class="investment-note">TB analog OOS: ${advice.analogs?.avgForward != null ? `${advice.analogs.avgForward > 0 ? "+" : ""}${advice.analogs.avgForward}%` : "—"}</p>
        </section>

        <div class="investment-highlight-grid">
          ${zoneCard(advice.safestZone, "An toàn (OOS)", advice.safestZone.safety)}
          ${zoneCard(advice.mostEffectiveZone, "Hiệu quả (OOS)", advice.mostEffectiveZone.effectiveness)}
        </div>

        ${crossAssetRows ? `
        <section class="investment-section">
          <h3>Ma trận đa tài sản</h3>
          <div class="cross-asset-list">${crossAssetRows}</div>
          <p class="investment-note">${crossAsset.correlationNote}</p>
        </section>
        ` : ""}

        <section class="investment-section">
          <h3>Xếp hạng vùng (walk-forward)</h3>
          <div class="investment-rank-list">${rankingRows}</div>
          <p class="investment-note">
            Pro xếp hạng từ ${advice.rankingSource === "out-of-sample" ? "tập test out-of-sample" : "fallback in-sample"}.
            Không phải lời khuyên tài chính chính thức.
          </p>
        </section>
      </div>
    `;
  };

  return {
    alignRsiForPro,
    alignDailyRsi,
    enrichPsychologyCache,
    buildWalkForwardRanking,
    buildWalkForwardDetail,
    buildProSignalScore,
    buildMacroContext,
    buildHistoricalAnalogs,
    buildScenarios,
    buildProBrief,
    buildAtrBands,
    buildSignalScoreSeries,
    buildRiskPlan,
    buildVolumeProxySeries,
    buildCrossAssetMatrix,
    buildProRecommendation,
    buildModeComparison,
    enhanceMarketSnapshot,
    renderProBrief,
    renderModeComparison,
    renderProPanel
  };
})();
