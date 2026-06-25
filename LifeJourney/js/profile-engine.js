/**
 * Thinking profile score evolution engine.
 */
const ProfileEngine = (() => {
  const DEFAULT_PROFILE = {
    ownership: 50,
    growth: 50,
    victim: 20,
    resilience: 50,
    optimism: 50,
    emotional_stability: 50,
    self_awareness: 50,
  };

  const STABLE_EMOTIONS = new Set(['calm', 'curious', 'hopeful']);
  const VOLATILE_EMOTIONS = new Set(['angry', 'frustrated', 'sad']);

  function clamp(val, min = 0, max = 100) {
    return Math.max(min, Math.min(max, Math.round(val)));
  }

  function evolveProfile(currentProfile, entry, patternScores) {
    const p = { ...currentProfile };
    const decay = 0.92;
    const learningRate = 0.15;

    for (const key of Object.keys(DEFAULT_PROFILE)) {
      p[key] = p[key] * decay + DEFAULT_PROFILE[key] * (1 - decay);
    }

    const ps = patternScores || entry.patterns?.scores || {};

    if (ps.ownership) p.ownership += ps.ownership * learningRate * 8;
    if (ps.growth) p.growth += ps.growth * learningRate * 8;
    if (ps.victim) p.victim += ps.victim * learningRate * 6;
    if (ps.opportunity) p.optimism += ps.opportunity * learningRate * 7;
    if (ps.fear) p.emotional_stability -= ps.fear * learningRate * 5;
    if (ps.catastrophic) p.emotional_stability -= ps.catastrophic * learningRate * 6;
    if (ps.fixed) p.resilience -= ps.fixed * learningRate * 5;
    if (ps.growth) p.resilience += ps.growth * learningRate * 4;

    const emotion = (entry.emotion || '').toLowerCase();
    if (STABLE_EMOTIONS.has(emotion)) {
      p.emotional_stability += 3;
      p.optimism += 2;
    }
    if (VOLATILE_EMOTIONS.has(emotion)) {
      p.emotional_stability -= 2;
    }

    if (entry.reflection?.learned?.length > 20) p.self_awareness += 4;
    if (entry.reflection?.differently?.length > 20) p.self_awareness += 3;
    if (entry.reflection?.surprised?.length > 10) p.self_awareness += 2;

    p.victim = Math.min(p.victim, 80);

    for (const key of Object.keys(p)) {
      p[key] = clamp(p[key]);
    }

    return p;
  }

  function recalculateFromTimeline(timeline) {
    let profile = { ...DEFAULT_PROFILE };
    for (const entry of timeline) {
      profile = evolveProfile(profile, entry, entry.patterns?.scores);
    }
    return profile;
  }

  function getRadarData(profile) {
    return {
      labels: ['ownership', 'growth', 'resilience', 'optimism', 'self_awareness', 'emotional_stability'],
      values: [
        profile.ownership,
        profile.growth,
        profile.resilience,
        profile.optimism,
        profile.self_awareness,
        profile.emotional_stability,
      ],
    };
  }

  function getEmotionTrends(timeline) {
    const trends = {};
    for (const entry of timeline) {
      const em = entry.emotion || 'unknown';
      if (!trends[em]) trends[em] = { count: 0, dates: [] };
      trends[em].count++;
      trends[em].dates.push(entry.timestamp);
    }
    return trends;
  }

  function getEmotionOverTime(timeline) {
    const buckets = {};
    for (const entry of timeline) {
      const date = (entry.timestamp || '').slice(0, 10);
      if (!date) continue;
      if (!buckets[date]) buckets[date] = {};
      const em = entry.emotion || 'unknown';
      buckets[date][em] = (buckets[date][em] || 0) + 1;
    }
    return buckets;
  }

  return {
    DEFAULT_PROFILE,
    evolveProfile,
    recalculateFromTimeline,
    getRadarData,
    getEmotionTrends,
    getEmotionOverTime,
  };
})();
