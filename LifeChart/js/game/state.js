export function createInitialState() {
  return {
    age: 18,
    week: 1,
    health: 100,
    wealth: 100,
    happiness: 100,
    knowledge: 0,
    relationships: 50,
    confidence: 50,
    reputation: 50,
    energy: 100,
    timeCapital: 168,
    money: 1000,
    portfolio: {
      career: 40,
      learning: 20,
      health: 20,
      family: 10,
      fun: 10,
    },
    emotions: {
      fear: 20,
      greed: 20,
      stress: 20,
      confidence: 50,
      discipline: 50,
    },
    openTrades: [],
    closedTrades: [],
    journal: [],
    history: [],
    peaks: {
      health: 100,
      wealth: 100,
      happiness: 100,
      knowledge: 0,
      relationships: 50,
      confidence: 50,
    },
    drawdowns: {},
    currentEvent: null,
    eventHistory: [],
    weekTrades: [],
    totalDecisions: 0,
    winStreak: 0,
    loseStreak: 0,
    archetype: null,
    gameOver: false,
  };
}

export function clamp(val, min = 0, max = 100) {
  return Math.max(min, Math.min(max, val));
}

export function applyStatChange(state, changes, multiplier = 1) {
  const statMap = {
    health: 'health',
    wealth: 'wealth',
    happiness: 'happiness',
    knowledge: 'knowledge',
    relationships: 'relationships',
    confidence: 'confidence',
    reputation: 'reputation',
    energy: 'energy',
    money: 'money',
    stress: null,
    discipline: null,
    fear: null,
    greed: null,
  };

  for (const [key, value] of Object.entries(changes)) {
    if (value === 0 || value === undefined) continue;

    const adjusted = Math.round(value * multiplier);

    if (key === 'money') {
      state.money = Math.max(0, state.money + adjusted);
      state.wealth = clamp(state.wealth + adjusted * 0.1);
    } else if (key === 'stress' || key === 'discipline' || key === 'fear' || key === 'greed') {
      state.emotions[key] = clamp(state.emotions[key] + adjusted);
    } else if (statMap[key]) {
      const statKey = statMap[key];
      if (statKey === 'knowledge') {
        state[statKey] = Math.max(0, state[statKey] + adjusted);
      } else {
        state[statKey] = clamp(state[statKey] + adjusted);
      }
    }
  }

  updatePeaks(state);
  updateDrawdowns(state);
}

function updatePeaks(state) {
  for (const key of ['health', 'wealth', 'happiness', 'knowledge', 'relationships', 'confidence']) {
    if (state[key] > state.peaks[key]) {
      state.peaks[key] = state[key];
    }
  }
}

export function updateDrawdowns(state) {
  const drawdownKeys = ['health', 'wealth', 'happiness', 'knowledge', 'relationships', 'confidence'];
  state.drawdowns = {};

  for (const key of drawdownKeys) {
    const peak = state.peaks[key];
    if (peak > 0 && state[key] < peak) {
      const dd = Math.round(((peak - state[key]) / peak) * 100);
      if (dd >= 5) {
        state.drawdowns[key] = dd;
      }
    }
  }
}

export function recordHistory(state) {
  state.history.push({
    week: state.week,
    age: state.age,
    health: state.health,
    wealth: state.wealth,
    happiness: state.happiness,
    knowledge: state.knowledge,
    relationships: state.relationships,
    confidence: state.confidence,
    money: state.money,
  });
}
