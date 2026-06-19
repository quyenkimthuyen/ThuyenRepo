/* Psychology engine: converts simple market inputs into educational probabilities. */
const PsychologyEngine = (() => {
  const cycle = [
    "Disbelief",
    "Hope",
    "Optimism",
    "Belief",
    "Thrill",
    "Euphoria",
    "Complacency",
    "Anxiety",
    "Denial",
    "Panic",
    "Capitulation",
    "Anger",
    "Depression"
  ];

  const RSI_PERIOD = 14;
  const PSYCHOLOGY_WINDOW = 30;

  const zoneColors = {
    Hope: "#3b82f6",
    Optimism: "#10b981",
    Belief: "#059669",
    Thrill: "#84cc16",
    Euphoria: "#f59e0b",
    Complacency: "#eab308",
    Anxiety: "#f97316",
    Panic: "#ef4444",
    Capitulation: "#b91c1c",
    Disbelief: "#64748b",
    Observing: "#475569"
  };

  const zoneBackgroundAlpha = 0.18;

  const zoneLabelsVi = {
    Hope: "Hy vọng",
    Optimism: "Lạc quan",
    Belief: "Niềm tin",
    Thrill: "Hưng phấn",
    Euphoria: "Hưng phấn cực độ",
    Complacency: "Chủ quan",
    Anxiety: "Lo âu",
    Panic: "Hoảng loạn",
    Capitulation: "Bỏ cuộc",
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

  const aggregateSeries = (series, interval) => {
    if (!series || !series.length) {
      return [];
    }

    const normalized = series.map(normalizeCandle);
    if (interval === "1D") {
      return normalized;
    }

    const buckets = new Map();

    normalized.forEach((candle) => {
      const key = interval === "1W" ? getWeekStart(candle.date) : candle.date.slice(0, 7);
      const existing = buckets.get(key);

      if (!existing) {
        buckets.set(key, { ...candle });
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

  const normalizeScores = (scores) => {
    const total = Object.values(scores).reduce((sum, value) => sum + value, 0) || 1;
    return Object.fromEntries(
      Object.entries(scores)
        .map(([key, value]) => [key, Math.round((value / total) * 100)])
        .sort((a, b) => b[1] - a[1])
    );
  };

  const calculateTrend = (series) => {
    if (!series || series.length < 2) {
      return 0;
    }

    const first = series[0].close ?? series[0].price;
    const last = series[series.length - 1].close ?? series[series.length - 1].price;
    return ((last - first) / first) * 100;
  };

  const getClose = (point) => point.close ?? point.price;

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
    const weekly = aggregateSeries(fullSeries, "1W");
    const monthly = aggregateSeries(fullSeries, "1M");

    const dailyRsi = buildRsiSeries(daily);
    const weeklyRsi = buildRsiSeries(weekly);
    const monthlyRsi = buildRsiSeries(monthly);

    return {
      daily: dailyRsi,
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

  const calculateVolume = (series) => {
    if (!series || series.length < 2) {
      return 50;
    }

    const volatility = series.slice(1).reduce((sum, point, index) => {
      const previous = series[index].close ?? series[index].price;
      const current = point.close ?? point.price;
      return sum + Math.abs((current - previous) / previous);
    }, 0) / (series.length - 1);

    return Math.round(clamp(45 + volatility * 1000, 35, 88));
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

  const evaluate = (fullSeries, visibleSeries = fullSeries) => {
    const dailySeries = aggregateSeries(fullSeries, "1D");
    const weeklySeries = aggregateSeries(fullSeries, "1W");
    const monthlySeries = aggregateSeries(fullSeries, "1M");

    const rsiDaily = calculateRsi(dailySeries);
    const rsiWeekly = calculateRsi(weeklySeries);
    const rsiMonthly = calculateRsi(monthlySeries);
    const rsiBlend = Math.round((rsiDaily + rsiWeekly + rsiMonthly) / 3);

    const trend = calculateTrend(visibleSeries);
    const volume = calculateVolume(visibleSeries);

    const scores = {
      Hope: 18 + clamp(trend, -10, 12) * 0.9 + (rsiDaily < 45 ? 10 : 0) + (rsiWeekly < 45 ? 6 : 0),
      Optimism: 30 + clamp(trend, 0, 18) * 1.8
        + (rsiDaily >= 48 && rsiDaily <= 64 ? 8 : 0)
        + (rsiWeekly >= 48 && rsiWeekly <= 64 ? 8 : 0),
      Belief: 24 + clamp(trend, 2, 25) * 1.15 + (volume > 55 ? 8 : 0) + (rsiMonthly >= 50 && rsiMonthly <= 68 ? 6 : 0),
      Thrill: 14 + clamp(trend, 6, 30) * 1.05
        + (rsiDaily > 66 ? 10 : 0)
        + (rsiWeekly > 66 ? 8 : 0),
      Euphoria: 8 + clamp(trend, 12, 35) * 1.2 + (rsiBlend > 72 ? 16 : 0),
      Complacency: 10 + (rsiBlend > 70 ? 14 : 0) + (rsiMonthly > 72 ? 8 : 0),
      Anxiety: 12 + (trend < -4 ? 18 : 0) + (volume > 70 ? 8 : 0) + (rsiBlend < 35 ? 10 : 0),
      Panic: 8 + (trend < -10 ? 20 : 0) + (rsiBlend < 28 ? 14 : 0),
      Capitulation: 6 + (trend < -16 ? 18 : 0) + (rsiBlend < 22 ? 12 : 0),
      Disbelief: 10 + (trend < 0 && trend > -6 ? 12 : 0) + (rsiBlend >= 35 && rsiBlend <= 48 ? 8 : 0)
    };

    const probabilities = normalizeScores(scores);
    const topZone = Object.entries(probabilities)[0] || ["Observing", 0];

    return {
      trend: Number(trend.toFixed(2)),
      rsi: rsiBlend,
      rsiByInterval: {
        daily: rsiDaily,
        weekly: rsiWeekly,
        monthly: rsiMonthly
      },
      volume,
      possibleZone: topZone[0],
      confidence: topZone[1],
      probabilities
    };
  };

  const buildPsychologyTimeline = (visibleSeries, windowSize = PSYCHOLOGY_WINDOW) => {
    if (!visibleSeries || !visibleSeries.length) {
      return [];
    }

    return visibleSeries.map((point, index) => {
      const slice = visibleSeries.slice(Math.max(0, index - windowSize + 1), index + 1);
      const evaluation = evaluate(slice, slice);

      return {
        date: point.date,
        zone: evaluation.possibleZone,
        color: zoneColors[evaluation.possibleZone] || zoneColors.Observing,
        label: zoneLabelsVi[evaluation.possibleZone] || zoneLabelsVi.Observing,
        confidence: evaluation.confidence
      };
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
        segments.push({
          zone: currentZone,
          color: timeline[index - 1]?.color || zoneColors.Observing,
          points: [...points]
        });
        currentZone = zone;
        points = [visibleSeries[index - 1], visibleSeries[index]];
        continue;
      }

      points.push(visibleSeries[index]);
    }

    segments.push({
      zone: currentZone,
      color: timeline[timeline.length - 1]?.color || zoneColors.Observing,
      points
    });

    return segments;
  };

  const renderPsychologyLegend = (container) => {
    const featuredZones = [
      "Hope",
      "Optimism",
      "Belief",
      "Thrill",
      "Euphoria",
      "Complacency",
      "Anxiety",
      "Panic",
      "Capitulation",
      "Disbelief"
    ];

    container.innerHTML = featuredZones.map((zone) => `
      <span class="psych-legend-item" style="--zone-color: ${zoneColors[zone]}">
        ${zoneLabelsVi[zone]}
      </span>
    `).join("");
  };

  const renderRsiPanel = (container, snapshot) => {
    const {
      date = "—",
      priceText = "—",
      psychologyZone = null,
      psychologyLabel = null,
      rsiByInterval = {},
      isHover = false
    } = snapshot;

    const items = [
      { key: "daily", label: "Ngày", value: rsiByInterval.daily },
      { key: "weekly", label: "Tuần", value: rsiByInterval.weekly },
      { key: "monthly", label: "Tháng", value: rsiByInterval.monthly }
    ];

    container.innerHTML = `
      <article class="crosshair-meta ${isHover ? "active" : ""}">
        <div>
          <span>Thời điểm</span>
          <strong id="crosshair-date">${date}</strong>
        </div>
        <div>
          <span>Giá</span>
          <strong id="crosshair-price">${priceText}</strong>
        </div>
        ${psychologyZone ? `
        <div>
          <span>Tâm lý thị trường</span>
          <strong class="psych-zone-value" style="color: ${zoneColors[psychologyZone] || zoneColors.Observing}">
            ${psychologyLabel || psychologyZone}
          </strong>
        </div>
        ` : ""}
      </article>
      ${items.map((item) => `
        <article class="rsi-card ${rsiTone(item.value ?? 50)}">
          <span>RSI ${item.label}</span>
          <strong>${item.value ?? "—"}</strong>
          <small>Chu kỳ ${RSI_PERIOD}</small>
        </article>
      `).join("")}
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
        <h3>${zone}</h3>
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
        <span>${zone}</span>
        <div class="probability-track"><span style="width: ${value}%"></span></div>
        <strong>${value}%</strong>
      </div>
      `).join("")}
    `;
  };

  return {
    cycle,
    zoneColors,
    zoneBackgroundAlpha,
    zoneLabelsVi,
    aggregateSeries,
    normalizeCandle,
    buildMultiFrameRsi,
    buildPsychologyTimeline,
    buildPsychologySegments,
    filterRsiByRange,
    evaluate,
    renderPsychologyLegend,
    renderRsiPanel,
    renderCycle,
    renderProbabilities
  };
})();
