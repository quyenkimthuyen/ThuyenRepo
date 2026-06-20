/* Investment recommendations from psychology zones + 10Y historical calibration. */
var InvestmentAdvisor = (() => {
  const FORWARD_WEEKS = 8;
  const MIN_SAMPLES = 2;

  const ZONE_EXPERT = {
    Capitulation: { safety: 94, effectiveness: 90, stance: "accumulate", action: "Tích lũy mạnh" },
    Depression: { safety: 90, effectiveness: 86, stance: "accumulate", action: "Tích lũy từng phần" },
    Disbelief: { safety: 86, effectiveness: 82, stance: "accumulate", action: "Bắt đầu vị thế nhỏ" },
    Panic: { safety: 80, effectiveness: 78, stance: "accumulate", action: "Mua thăm dò, chia lệnh" },
    Anger: { safety: 74, effectiveness: 70, stance: "accumulate", action: "Chỉ mua khi xác nhận đáy" },
    Hope: { safety: 76, effectiveness: 92, stance: "accumulate", action: "Vùng vàng tích lũy" },
    Optimism: { safety: 68, effectiveness: 88, stance: "hold", action: "Giữ vị thế, thêm có kiểm soát" },
    Belief: { safety: 58, effectiveness: 82, stance: "hold", action: "Theo xu hướng, tránh đu đỉnh" },
    Anxiety: { safety: 52, effectiveness: 48, stance: "wait", action: "Quan sát, chờ tín hiệu rõ" },
    Denial: { safety: 45, effectiveness: 42, stance: "wait", action: "Không mua thêm, siết stop" },
    Thrill: { safety: 28, effectiveness: 38, stance: "reduce", action: "Chốt lời một phần" },
    Complacency: { safety: 32, effectiveness: 35, stance: "reduce", action: "Giảm đòn bẩy, bảo vệ lợi nhuận" },
    Euphoria: { safety: 18, effectiveness: 22, stance: "reduce", action: "Giảm rủi ro, tránh FOMO" },
    Observing: { safety: 50, effectiveness: 50, stance: "wait", action: "Chờ phân tích đủ dữ liệu" }
  };

  const STANCE_LABELS = {
    accumulate: "Tích lũy",
    hold: "Nắm giữ",
    wait: "Chờ đợi",
    reduce: "Giảm vị thế"
  };

  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

  const getClose = (point) => point.close ?? point.price;

  const getExpertProfile = (zone) => ZONE_EXPERT[zone] || ZONE_EXPERT.Observing;

  const findIndexOnOrAfter = (series, date) => {
    for (let index = 0; index < series.length; index += 1) {
      if (series[index].date >= date) {
        return index;
      }
    }

    return -1;
  };

  const forwardReturnPct = (series, startIndex, weeks = FORWARD_WEEKS) => {
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

  const maxDrawdownPct = (series, startIndex, weeks = FORWARD_WEEKS) => {
    const endIndex = Math.min(startIndex + weeks * 7, series.length - 1);
    if (startIndex < 0 || endIndex <= startIndex) {
      return null;
    }

    const entry = getClose(series[startIndex]);
    if (!entry) {
      return null;
    }

    let peak = entry;
    let maxDrawdown = 0;

    for (let index = startIndex; index <= endIndex; index += 1) {
      const price = getClose(series[index]);
      peak = Math.max(peak, price);
      const drawdown = ((price - peak) / peak) * 100;
      maxDrawdown = Math.min(maxDrawdown, drawdown);
    }

    return maxDrawdown;
  };

  const buildHistoricalZoneStats = (cache, fullSeries) => {
    const daily = PsychologyEngine.aggregateSeries(fullSeries, "1D");
    const stats = new Map();

    cache.regions.forEach((region) => {
      const startIndex = findIndexOnOrAfter(daily, region.startDate);
      const forward = forwardReturnPct(daily, startIndex);
      const drawdown = maxDrawdownPct(daily, startIndex);

      if (forward === null) {
        return;
      }

      const bucket = stats.get(region.zone) || {
        zone: region.zone,
        samples: 0,
        forwardTotal: 0,
        positiveCount: 0,
        drawdownTotal: 0
      };

      bucket.samples += 1;
      bucket.forwardTotal += forward;
      bucket.positiveCount += forward > 0 ? 1 : 0;
      bucket.drawdownTotal += drawdown ?? 0;
      stats.set(region.zone, bucket);
    });

    return [...stats.values()].map((bucket) => {
      const winRate = bucket.samples ? (bucket.positiveCount / bucket.samples) * 100 : 0;
      const avgForward = bucket.samples ? bucket.forwardTotal / bucket.samples : 0;
      const avgDrawdown = bucket.samples ? bucket.drawdownTotal / bucket.samples : 0;
      const histSafety = clamp(55 + winRate * 0.35 + avgDrawdown * 0.9, 0, 100);
      const histEffectiveness = clamp(50 + avgForward * 1.4 + winRate * 0.2, 0, 100);

      return {
        zone: bucket.zone,
        samples: bucket.samples,
        avgForward: Number(avgForward.toFixed(2)),
        winRate: Number(winRate.toFixed(1)),
        avgDrawdown: Number(avgDrawdown.toFixed(2)),
        histSafety: Number(histSafety.toFixed(1)),
        histEffectiveness: Number(histEffectiveness.toFixed(1))
      };
    });
  };

  const blendScore = (expert, historical, key) => {
    if (!historical || historical.samples < MIN_SAMPLES) {
      return expert[key];
    }

    const histKey = key === "safety" ? "histSafety" : "histEffectiveness";
    return Math.round(expert[key] * 0.35 + historical[histKey] * 0.65);
  };

  const buildZoneRanking = (cache, fullSeries) => {
    const historical = buildHistoricalZoneStats(cache, fullSeries);
    const histByZone = new Map(historical.map((item) => [item.zone, item]));
    const zones = [...new Set([
      ...Object.keys(ZONE_EXPERT),
      ...historical.map((item) => item.zone)
    ])];

    const ranked = zones.map((zone) => {
      const expert = getExpertProfile(zone);
      const hist = histByZone.get(zone);
      const safety = blendScore(expert, hist, "safety");
      const effectiveness = blendScore(expert, hist, "effectiveness");
      const composite = Math.round(safety * 0.45 + effectiveness * 0.55);

      return {
        zone,
        label: PsychologyEngine.zoneLabelsVi[zone] || zone,
        color: PsychologyEngine.zoneColors[zone] || PsychologyEngine.zoneColors.Observing,
        stance: expert.stance,
        stanceLabel: STANCE_LABELS[expert.stance],
        action: expert.action,
        safety,
        effectiveness,
        composite,
        samples: hist?.samples ?? 0,
        avgForward: hist?.avgForward ?? null,
        winRate: hist?.winRate ?? null
      };
    }).sort((left, right) => right.composite - left.composite);

    const accumulateZones = ranked
      .filter((item) => item.stance === "accumulate")
      .sort((left, right) => right.composite - left.composite);

    const safest = [...ranked].sort((left, right) => right.safety - left.safety)[0];
    const mostEffective = [...ranked].sort((left, right) => right.effectiveness - left.effectiveness)[0];
    const avoid = ranked
      .filter((item) => item.stance === "reduce")
      .sort((left, right) => left.safety - right.safety);

    return {
      all: ranked,
      safest,
      mostEffective,
      topAccumulate: accumulateZones,
      avoid
    };
  };

  const refineCurrentAction = (snapshot, profile) => {
    const rsi = snapshot.rsi ?? 50;
    const trend = snapshot.trend ?? 0;
    let action = profile.action;
    let detail = `Vùng ${snapshot.label || PsychologyEngine.zoneLabelsVi[snapshot.zone] || snapshot.zone} · khớp sóng ${snapshot.confidence ?? 0}%`;

    if (profile.stance === "accumulate") {
      if (rsi > 68) {
        action = "Chờ điều chỉnh rồi mới tích lũy";
        detail += " · RSI đang cao, tránh đu đỉnh";
      } else if (rsi < 38 && trend < 0) {
        action = "Ưu tiên tích lũy — fear đang định giá";
        detail += " · RSI thấp trong vùng tích lũy";
      }
    }

    if (profile.stance === "reduce") {
      if (rsi > 70 || trend > 8) {
        action = "Giảm vị thế — rủi ro đu đỉnh cao";
        detail += " · Xu hướng và RSI báo quá nóng";
      }
    }

    if (profile.stance === "wait" && rsi < 35) {
      action = "Theo dõi sát — có thể sớm chuyển sang tích lũy";
    }

    return { action, detail, stance: profile.stance, stanceLabel: STANCE_LABELS[profile.stance] };
  };

  const buildRecommendation = (cache, fullSeries, snapshot) => {
    if (!cache?.regions?.length || !fullSeries?.length) {
      return { hasAdvice: false };
    }

    const ranking = buildZoneRanking(cache, fullSeries);
    const currentZone = snapshot?.zone || "Observing";
    const currentProfile = getExpertProfile(currentZone);
    const currentRank = ranking.all.find((item) => item.zone === currentZone)
      || {
        ...getExpertProfile(currentZone),
        zone: currentZone,
        label: PsychologyEngine.zoneLabelsVi[currentZone] || currentZone,
        color: PsychologyEngine.zoneColors[currentZone],
        safety: currentProfile.safety,
        effectiveness: currentProfile.effectiveness,
        composite: Math.round(currentProfile.safety * 0.45 + currentProfile.effectiveness * 0.55)
      };

    const current = refineCurrentAction(
      { ...snapshot, zone: currentZone, label: snapshot?.label || currentRank.label },
      currentProfile
    );

    return {
      hasAdvice: true,
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
      zoneRanking: ranking.all.filter((item) => item.samples >= MIN_SAMPLES || ZONE_EXPERT[item.zone])
    };
  };

  const renderPanel = (container, advice) => {
    if (!container) {
      return;
    }

    if (!advice?.hasAdvice) {
      container.innerHTML = `
        <div class="investment-panel investment-panel--empty">
          <p class="investment-kicker">Khuyến nghị đầu tư</p>
          <p class="investment-empty">Bấm <strong>Phân tích 10 năm</strong> để xây bản đồ vùng tâm lý và nhận gợi ý vùng an toàn / hiệu quả.</p>
        </div>
      `;
      return;
    }

    const zoneCard = (item, metricLabel, metricValue) => `
      <article class="investment-zone-card" style="--zone-color: ${item.color}">
        <span class="investment-zone-name">${item.label}</span>
        <strong class="investment-zone-metric">${metricValue}</strong>
        <small>${metricLabel}${item.samples ? ` · ${item.samples} giai đoạn` : ""}</small>
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

    container.innerHTML = `
      <div class="investment-panel">
        <header class="investment-head">
          <div>
            <p class="investment-kicker">Khuyến nghị đầu tư</p>
            <h2 class="investment-title">Gợi ý theo vùng tâm lý · 10 năm</h2>
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
          </div>
        </article>

        <div class="investment-highlight-grid">
          ${zoneCard(advice.safestZone, "Điểm an toàn", advice.safestZone.safety)}
          ${zoneCard(advice.mostEffectiveZone, "Điểm hiệu quả", advice.mostEffectiveZone.effectiveness)}
        </div>

        <section class="investment-section">
          <h3>Vùng tích lũy ưu tiên (an toàn + hiệu quả)</h3>
          <div class="investment-chip-list">
            ${advice.topAccumulateZones.map((item) => `
              <span class="investment-chip" style="--zone-color: ${item.color}">
                ${item.label}
                <em>${item.composite}</em>
              </span>
            `).join("")}
          </div>
        </section>

        ${advice.avoidZones.length ? `
        <section class="investment-section investment-section--warn">
          <h3>Nên hạn chế mua thêm</h3>
          <div class="investment-chip-list">
            ${advice.avoidZones.map((item) => `
              <span class="investment-chip investment-chip--warn" style="--zone-color: ${item.color}">
                ${item.label}
              </span>
            `).join("")}
          </div>
        </section>
        ` : ""}

        <section class="investment-section">
          <h3>Xếp hạng vùng (tích lũy / nắm giữ)</h3>
          <div class="investment-rank-list">${rankingRows}</div>
          <p class="investment-note">Điểm tổng hợp từ lịch sử 8 tuần sau khi vào vùng + mô hình chuyên gia. Không phải lời khuyên tài chính chính thức.</p>
        </section>
      </div>
    `;
  };

  return {
    ZONE_EXPERT,
    buildHistoricalZoneStats,
    buildZoneRanking,
    buildRecommendation,
    renderPanel
  };
})();
