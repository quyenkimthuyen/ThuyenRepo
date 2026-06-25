const GameState = {
  createNew() {
    return {
      character: {
        health: 100,
        wealth: 100,
        happiness: 100,
        knowledge: 100,
        relationships: 100,
        age: 18,
        energy: 100
      },
      day: 1,
      decisions: [],
      timeline: [],
      flags: {},
      pendingConsequences: [],
      usedEventIds: [],
      personality: {
        shortTerm: 0,
        longTerm: 0,
        riskHigh: 0,
        riskLow: 0,
        learning: 0,
        avoidance: 0,
        relationship: 0,
        total: 0
      },
      reflections: [],
      lastReportDay: 0
    };
  },

  clampStat(value) {
    return Math.max(0, Math.min(150, Math.round(value)));
  },

  applyEffects(character, effects) {
    if (!effects) return;
    const keys = ['health', 'wealth', 'happiness', 'knowledge', 'relationships', 'energy'];
    keys.forEach((key) => {
      if (effects[key] !== undefined) {
        character[key] = this.clampStat(character[key] + effects[key]);
      }
    });
  },

  addTimelineEntry(state, entry) {
    state.timeline.unshift({
      day: state.day,
      ...entry,
      timestamp: Date.now()
    });
    if (state.timeline.length > 100) {
      state.timeline.pop();
    }
  }
};
