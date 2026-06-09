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

  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

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

    const first = series[0].price;
    const last = series[series.length - 1].price;
    return ((last - first) / first) * 100;
  };

  const calculateRsi = (series) => {
    if (!series || series.length < 15) {
      return 50;
    }

    const recent = series.slice(-15);
    let gains = 0;
    let losses = 0;

    for (let index = 1; index < recent.length; index += 1) {
      const change = recent[index].price - recent[index - 1].price;
      if (change >= 0) {
        gains += change;
      } else {
        losses += Math.abs(change);
      }
    }

    if (losses === 0) {
      return 72;
    }

    const rs = gains / losses;
    return Math.round(100 - 100 / (1 + rs));
  };

  const calculateVolume = (series) => {
    if (!series || series.length < 2) {
      return 50;
    }

    const volatility = series.slice(1).reduce((sum, point, index) => {
      const previous = series[index].price;
      return sum + Math.abs((point.price - previous) / previous);
    }, 0) / (series.length - 1);

    return Math.round(clamp(45 + volatility * 1000, 35, 88));
  };

  const evaluate = (series) => {
    const trend = calculateTrend(series);
    const rsi = calculateRsi(series);
    const volume = calculateVolume(series);

    const scores = {
      Hope: 18 + clamp(trend, -10, 12) * 0.9 + (rsi < 45 ? 12 : 0),
      Optimism: 30 + clamp(trend, 0, 18) * 1.8 + (rsi >= 48 && rsi <= 64 ? 12 : 0),
      Belief: 24 + clamp(trend, 2, 25) * 1.15 + (volume > 55 ? 8 : 0),
      Thrill: 14 + clamp(trend, 6, 30) * 1.05 + (rsi > 66 ? 18 : 0),
      Complacency: 10 + (rsi > 70 ? 12 : 0),
      Anxiety: 12 + (trend < -4 ? 18 : 0) + (volume > 70 ? 8 : 0)
    };

    const probabilities = normalizeScores(scores);
    const topZone = Object.entries(probabilities)[0] || ["Observing", 0];

    return {
      trend: Number(trend.toFixed(2)),
      rsi,
      volume,
      possibleZone: topZone[0],
      confidence: topZone[1],
      probabilities
    };
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
    evaluate,
    renderCycle,
    renderProbabilities
  };
})();
