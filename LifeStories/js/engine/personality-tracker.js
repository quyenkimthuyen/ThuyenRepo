const PERSONALITY_TRAITS = [
  'ownership', 'empathy', 'assertiveness', 'responsibility',
  'curiosity', 'discipline', 'integrity', 'courage',
  'resilience', 'cooperation',
];

const TAG_TO_INSIGHT = {
  avoid_conflict: 'insight_avoid_conflict',
  short_term_gain: 'insight_short_term',
  assertiveness: 'insight_assertiveness',
  responsibility: 'insight_responsibility',
  empathy: 'insight_empathy',
  teaching: 'insight_teaching',
  avoidance: 'insight_avoidance',
  cooperation: 'insight_cooperation',
  courage: 'insight_courage',
  discipline: 'insight_discipline',
  curiosity: 'insight_curiosity',
  integrity: 'insight_integrity',
  resilience: 'insight_resilience',
};

function initPersonality(state) {
  if (!state.personality || Object.keys(state.personality).length === 0) {
    state.personality = {};
    PERSONALITY_TRAITS.forEach(t => { state.personality[t] = 0; });
  }
  if (!state.tagCounts) state.tagCounts = {};
  return state;
}

function applyPersonalityEffects(state, effects) {
  if (!effects) return;
  initPersonality(state);
  Object.entries(effects).forEach(([trait, delta]) => {
    if (state.personality[trait] !== undefined) {
      state.personality[trait] = Math.max(0, state.personality[trait] + delta);
    }
  });
}

function applyTags(state, tags) {
  if (!tags) return;
  if (!state.tagCounts) state.tagCounts = {};
  tags.forEach(tag => {
    state.tagCounts[tag] = (state.tagCounts[tag] || 0) + 1;
  });
}

function getTopTraits(state, limit = 5) {
  initPersonality(state);
  return Object.entries(state.personality)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .filter(([, v]) => v > 0);
}

function getInsights(state, limit = 4) {
  if (!state.tagCounts) return [];
  const sorted = Object.entries(state.tagCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .filter(([, count]) => count >= 2);

  return sorted.map(([tag]) => ({
    tag,
    text: t(TAG_TO_INSIGHT[tag] || `insight_${tag}`),
  })).filter(i => i.text && !i.text.startsWith('insight_'));
}

function getTraitPercentages(state) {
  initPersonality(state);
  const total = Object.values(state.personality).reduce((s, v) => s + v, 0) || 1;
  const result = {};
  PERSONALITY_TRAITS.forEach(trait => {
    result[trait] = Math.round((state.personality[trait] / total) * 100);
  });
  return result;
}
