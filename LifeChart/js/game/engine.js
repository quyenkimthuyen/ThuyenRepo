import { applyStatChange, clamp, recordHistory } from './state.js';
import { pickRandomEvent } from '../data/events.js';

export function canAffordTrade(state, trade, event) {
  const energyMult = event?.energyCostMultiplier || 1;
  const timeCost = Math.max(0, trade.cost.time || 0);
  const energyCost = Math.max(0, (trade.cost.energy || 0) * energyMult);
  const moneyCost = trade.cost.money || 0;

  return (
    state.timeCapital >= timeCost &&
    state.energy >= energyCost &&
    state.money >= moneyCost
  );
}

export function getEventModifier(event, category) {
  if (!event?.modifiers) return 1;
  return event.modifiers[category] || 1;
}

export function executeTrade(state, trade, reason, emotion, event) {
  const energyMult = event?.energyCostMultiplier || 1;
  const catMod = getEventModifier(event, trade.category);
  const successPenalty = event?.successRatePenalty || 0;
  const adjustedRate = clamp(trade.successRate * catMod - successPenalty, 0.05, 0.99);

  state.timeCapital -= Math.max(0, trade.cost.time || 0);
  if (trade.cost.time < 0) {
    state.timeCapital += Math.abs(trade.cost.time);
  }
  state.energy -= Math.max(0, (trade.cost.energy || 0) * energyMult);
  if (trade.cost.energy < 0) {
    state.energy = clamp(state.energy + Math.abs(trade.cost.energy));
  }
  state.money -= trade.cost.money || 0;

  const success = Math.random() < adjustedRate;
  const openTrade = {
    id: `${trade.id}_${Date.now()}`,
    tradeId: trade.id,
    title: trade.title,
    category: trade.category,
    weekOpened: state.week,
    weeksRemaining: trade.delay,
    successRate: adjustedRate,
    reward: { ...trade.reward },
    risk: { ...trade.risk },
    success,
    reason,
    emotion,
    resolved: trade.delay === 0,
  };

  if (trade.delay === 0) {
    resolveTradeImmediate(state, openTrade, catMod, event);
    state.closedTrades.unshift(openTrade);
    updateStreaks(state, success);
  } else {
    state.openTrades.push(openTrade);
  }

  state.weekTrades.push(openTrade);
  state.totalDecisions++;

  const journalEntry = {
    week: state.week,
    decision: trade.title,
    reason: reason || '(không ghi)',
    outcome: trade.delay === 0
      ? (success ? 'Thành công' : 'Thất bại')
      : `Đang chờ ${trade.delay} tuần`,
    emotion,
    category: trade.category,
    successRate: adjustedRate,
  };
  state.journal.unshift(journalEntry);

  updateEmotionsAfterTrade(state, trade, success, emotion);

  return { success, openTrade, adjustedRate };
}

function resolveTradeImmediate(state, trade, catMod, event) {
  const wealthMult = event?.wealthBonus || 1;
  if (trade.success) {
    const rewards = { ...trade.reward };
    if (rewards.wealth) rewards.wealth = Math.round(rewards.wealth * catMod * wealthMult);
    applyStatChange(state, rewards, catMod);
  } else {
    applyStatChange(state, trade.risk, 1);
    state.happiness = clamp(state.happiness - 3);
  }
  trade.outcome = trade.success ? 'success' : 'fail';
}

export function processOpenTrades(state, event) {
  const resolved = [];

  for (const trade of state.openTrades) {
    trade.weeksRemaining--;
    if (trade.weeksRemaining <= 0) {
      const catMod = getEventModifier(event, trade.category);
      const wealthMult = event?.wealthBonus || 1;

      if (trade.success) {
        const rewards = { ...trade.reward };
        if (rewards.wealth) rewards.wealth = Math.round(rewards.wealth * catMod * wealthMult);
        applyStatChange(state, rewards, catMod);
      } else {
        applyStatChange(state, trade.risk, 1);
        state.happiness = clamp(state.happiness - 3);
      }

      trade.resolved = true;
      trade.outcome = trade.success ? 'success' : 'fail';
      trade.weekResolved = state.week;
      state.closedTrades.unshift(trade);
      resolved.push(trade);
      updateStreaks(state, trade.success);

      const journalUpdate = state.journal.find(
        j => j.week === trade.weekOpened && j.decision === trade.title && j.outcome.startsWith('Đang chờ')
      );
      if (journalUpdate) {
        journalUpdate.outcome = trade.success ? 'Thành công (trễ)' : 'Thất bại (trễ)';
      }
    }
  }

  state.openTrades = state.openTrades.filter(t => !t.resolved);
  return resolved;
}

function updateStreaks(state, success) {
  if (success) {
    state.winStreak++;
    state.loseStreak = 0;
  } else {
    state.loseStreak++;
    state.winStreak = 0;
  }
}

function updateEmotionsAfterTrade(state, trade, success, emotion) {
  const e = state.emotions;

  if (success) {
    e.confidence = clamp(e.confidence + 3);
    e.fear = clamp(e.fear - 2);
    if (state.winStreak >= 3) {
      e.greed = clamp(e.greed + 5);
    }
  } else {
    e.fear = clamp(e.fear + 5);
    e.confidence = clamp(e.confidence - 4);
    e.stress = clamp(e.stress + 3);
  }

  if (trade.category === 'fun' && trade.delay === 0) {
    e.greed = clamp(e.greed + 2);
  }
  if (trade.category === 'learning' || trade.category === 'health') {
    e.discipline = clamp(e.discipline + 2);
  }

  const emotionEffects = {
    confident: () => { e.confidence = clamp(e.confidence + 2); },
    fearful: () => { e.fear = clamp(e.fear + 3); },
    excited: () => { e.greed = clamp(e.greed + 3); },
    stressed: () => { e.stress = clamp(e.stress + 4); },
    calm: () => { e.stress = clamp(e.stress - 2); e.discipline = clamp(e.discipline + 1); },
    greedy: () => { e.greed = clamp(e.greed + 5); },
    disciplined: () => { e.discipline = clamp(e.discipline + 3); },
  };

  if (emotionEffects[emotion]) emotionEffects[emotion]();
}

export function advanceWeek(state) {
  recordHistory(state);

  const resolved = processOpenTrades(state, state.currentEvent);

  if (state.currentEvent) {
    state.currentEvent.weeksRemaining--;
    if (state.currentEvent.weeksRemaining <= 0) {
      state.eventHistory.push(state.currentEvent);
      state.currentEvent = null;
    }
  }

  if (!state.currentEvent && Math.random() < 0.35) {
    const excludeIds = state.eventHistory.slice(-3).map(e => e.id);
    const event = pickRandomEvent(excludeIds);
    state.currentEvent = {
      ...event,
      weeksRemaining: event.duration,
      startedWeek: state.week,
    };
  }

  state.week++;
  if (state.week % 52 === 1 && state.week > 1) {
    state.age++;
  }

  state.timeCapital = 168;
  state.energy = clamp(state.energy + 30);
  state.money += Math.round(state.wealth * 0.5 + state.knowledge * 0.2);
  state.weekTrades = [];

  checkGameOver(state);

  return resolved;
}

function checkGameOver(state) {
  if (state.health <= 0 || state.happiness <= 0) {
    state.gameOver = true;
  }
  if (state.age >= 80) {
    state.gameOver = true;
  }
}

export function getWeeklyTradeOptions(allTrades, state, count = 6) {
  const usedIds = new Set([
    ...state.weekTrades.map(t => t.tradeId),
    ...state.closedTrades.slice(0, 10).map(t => t.tradeId),
  ]);

  const available = allTrades.filter(t => !usedIds.has(t.id));
  const shuffled = [...available].sort(() => Math.random() - 0.5);

  const portfolio = state.portfolio;
  const weighted = shuffled.sort((a, b) => {
    const weightA = portfolio[a.category] || 10;
    const weightB = portfolio[b.category] || 10;
    return weightB - weightA + (Math.random() - 0.5) * 20;
  });

  return weighted.slice(0, count);
}

export function normalizePortfolio(portfolio) {
  const total = Object.values(portfolio).reduce((s, v) => s + v, 0);
  if (total === 0) return portfolio;
  const normalized = {};
  for (const [key, val] of Object.entries(portfolio)) {
    normalized[key] = Math.round((val / total) * 100);
  }
  const diff = 100 - Object.values(normalized).reduce((s, v) => s + v, 0);
  if (diff !== 0) {
    const maxKey = Object.entries(normalized).sort((a, b) => b[1] - a[1])[0][0];
    normalized[maxKey] += diff;
  }
  return normalized;
}
