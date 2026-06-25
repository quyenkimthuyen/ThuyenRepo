/**
 * LocalStorage persistence layer for Cognitive Mirror.
 */
const Storage = (() => {
  const KEY = 'cognitive_mirror_life_journey';

  const defaultState = () => ({
    language: 'vi',
    currentStage: null,
    simulationStage: null,
    usedEventIds: [],
    timeline: [],
    thinkingProfile: {
      ownership: 50,
      growth: 50,
      victim: 20,
      resilience: 50,
      optimism: 50,
      emotional_stability: 50,
      self_awareness: 50,
    },
    patternHistory: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  });

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return defaultState();
      const data = JSON.parse(raw);
      return { ...defaultState(), ...data };
    } catch {
      return defaultState();
    }
  }

  function save(state) {
    state.updatedAt = new Date().toISOString();
    localStorage.setItem(KEY, JSON.stringify(state));
  }

  function reset() {
    localStorage.removeItem(KEY);
    return defaultState();
  }

  function addTimelineEntry(state, entry) {
    state.timeline.push(entry);
    save(state);
    return state;
  }

  function markEventUsed(state, eventId) {
    if (!state.usedEventIds.includes(eventId)) {
      state.usedEventIds.push(eventId);
    }
    save(state);
  }

  function updateProfile(state, profile) {
    state.thinkingProfile = profile;
    save(state);
  }

  function setLanguage(state, lang) {
    state.language = lang;
    save(state);
  }

  function setStage(state, stageId) {
    state.currentStage = stageId;
    state.simulationStage = null;
    save(state);
  }

  function setSimulationStage(state, stageId) {
    state.simulationStage = stageId;
    save(state);
  }

  function clearSimulation(state) {
    state.simulationStage = null;
    save(state);
  }

  function exportData(state) {
    return JSON.stringify(state, null, 2);
  }

  function importData(json) {
    const data = JSON.parse(json);
    const merged = { ...defaultState(), ...data };
    save(merged);
    return merged;
  }

  function getStats(state) {
    const real = state.timeline.filter((e) => !e.simulation);
    const simulated = state.timeline.length - real.length;
    return {
      totalEntries: state.timeline.length,
      realEntries: real.length,
      simulatedEntries: simulated,
      eventsExplored: state.usedEventIds.length,
      daysActive: new Set(state.timeline.map((e) => (e.timestamp || '').slice(0, 10))).size,
    };
  }

  return {
    load,
    save,
    reset,
    addTimelineEntry,
    markEventUsed,
    updateProfile,
    setLanguage,
    setStage,
    setSimulationStage,
    clearSimulation,
    exportData,
    importData,
    getStats,
  };
})();
