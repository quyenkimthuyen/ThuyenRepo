/**
 * Compare AI signal scores with simulation outcomes; suggest weight tweaks.
 * @module scoring/ScoreCalibration
 */

import { composeScoreFromFactors, scoreToGrade } from './SignalScoreEngine.js';
import { getDefaultScoringWeights, normalizeScoringWeights } from './ScoringWeights.js';

/** @typedef {import('../simulation/TradeSimulator.js').TradeResult} TradeResult */
/** @typedef {import('./SignalScoreEngine.js').ScoredSignal} ScoredSignal */
/** @typedef {import('./SignalScoreEngine.js').ScoreFactors} ScoreFactors */

/**
 * @typedef {Object} JoinedScoreTrade
 * @property {TradeResult} trade
 * @property {ScoredSignal} signal
 * @property {number} score
 * @property {ScoreFactors} factors
 */

/**
 * @typedef {Object} ScoreBucketSummary
 * @property {string} label
 * @property {number} min
 * @property {number} max
 * @property {number} trades
 * @property {number} wins
 * @property {number} winRate
 * @property {number} avgProfit
 * @property {number} netProfit
 */

/**
 * @typedef {Object} FactorDiscrimination
 * @property {string} factor
 * @property {number} avgWin
 * @property {number} avgLoss
 * @property {number} delta
 */

/**
 * @typedef {Object} ScoreCalibrationReport
 * @property {boolean} matched
 * @property {string} [reason]
 * @property {number} [matchedTrades]
 * @property {number} [skippedTrades]
 * @property {ScoreBucketSummary[]} [buckets]
 * @property {FactorDiscrimination[]} [factors]
 * @property {number} [scoreProfitCorrelation]
 * @property {number} [highScoreWinRate]
 * @property {number} [lowScoreWinRate]
 * @property {number} [minScoreCutoffUsed]
 */

/** @type {Array<{ label: string, min: number, max: number }>} */
export const SCORE_BUCKETS = [
  { label: 'A (80+)', min: 80, max: 100 },
  { label: 'B (65–79)', min: 65, max: 79 },
  { label: 'C (50–64)', min: 50, max: 64 },
  { label: 'D/F (<50)', min: 0, max: 49 },
];

/**
 * @param {import('../scoring/ScoringEngine.js').ScoredSignalSet|null} scoredSet
 * @param {import('../simulation/SimulationEngine.js').SimulationResult|null} simResult
 * @returns {boolean}
 */
export function calibrationContextsMatch(scoredSet, simResult) {
  if (!scoredSet || !simResult) return false;
  return scoredSet.strategyId === simResult.strategyId
    && scoredSet.symbol === simResult.symbol
    && scoredSet.timeframe === simResult.timeframe;
}

/**
 * @param {TradeResult[]} trades
 * @param {ScoredSignal[]} signals
 * @returns {JoinedScoreTrade[]}
 */
export function joinTradesWithScores(trades, signals) {
  const byId = new Map(signals.map((s) => [s.id, s]));
  /** @type {JoinedScoreTrade[]} */
  const rows = [];

  for (const trade of trades) {
    const signal = byId.get(trade.signalId);
    const factors = signal?.scoreBreakdown?.factors;
    if (!signal || !factors) continue;
    rows.push({
      trade,
      signal,
      score: signal.scoreBreakdown?.score ?? signal.confidence,
      factors,
    });
  }

  return rows;
}

/**
 * @param {number[]} xs
 * @param {number[]} ys
 * @returns {number}
 */
export function pearsonCorrelation(xs, ys) {
  if (xs.length !== ys.length || xs.length < 2) return 0;
  const n = xs.length;
  const meanX = xs.reduce((s, v) => s + v, 0) / n;
  const meanY = ys.reduce((s, v) => s + v, 0) / n;
  let num = 0;
  let denX = 0;
  let denY = 0;
  for (let i = 0; i < n; i++) {
    const dx = xs[i] - meanX;
    const dy = ys[i] - meanY;
    num += dx * dy;
    denX += dx * dx;
    denY += dy * dy;
  }
  const den = Math.sqrt(denX * denY);
  return den > 0 ? num / den : 0;
}

/**
 * @param {JoinedScoreTrade[]} rows
 * @returns {ScoreBucketSummary[]}
 */
export function summarizeByScoreBucket(rows) {
  return SCORE_BUCKETS.map((bucket) => {
    const inBucket = rows.filter((r) => r.score >= bucket.min && r.score <= bucket.max);
    const wins = inBucket.filter((r) => r.trade.outcome === 'win').length;
    const netProfit = inBucket.reduce((s, r) => s + r.trade.profit, 0);
    const trades = inBucket.length;
    return {
      label: bucket.label,
      min: bucket.min,
      max: bucket.max,
      trades,
      wins,
      winRate: trades ? (wins / trades) * 100 : 0,
      avgProfit: trades ? netProfit / trades : 0,
      netProfit,
    };
  });
}

/**
 * @param {JoinedScoreTrade[]} rows
 * @returns {FactorDiscrimination[]}
 */
export function summarizeFactorDiscrimination(rows) {
  const wins = rows.filter((r) => r.trade.outcome === 'win');
  const losses = rows.filter((r) => r.trade.outcome === 'loss');
  if (wins.length === 0 || losses.length === 0) return [];

  const keys = Object.keys(wins[0].factors);
  return keys.map((factor) => {
    const avgWin = wins.reduce((s, r) => s + r.factors[/** @type {keyof ScoreFactors} */ (factor)], 0) / wins.length;
    const avgLoss = losses.reduce((s, r) => s + r.factors[/** @type {keyof ScoreFactors} */ (factor)], 0) / losses.length;
    return {
      factor,
      avgWin,
      avgLoss,
      delta: avgWin - avgLoss,
    };
  }).sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
}

/**
 * @param {JoinedScoreTrade[]} rows
 * @param {Record<string, number>} weights
 * @returns {number}
 */
export function calibrationFitness(rows, weights) {
  if (rows.length < 4) return 0;

  const scored = rows.map((row) => ({
    score: composeScoreFromFactors(row.factors, weights),
    win: row.trade.outcome === 'win',
    profit: row.trade.profit,
  }));

  const sorted = [...scored].sort((a, b) => a.score - b.score);
  const mid = Math.max(1, Math.floor(sorted.length / 2));
  const low = sorted.slice(0, mid);
  const high = sorted.slice(mid);

  const wrHigh = high.filter((r) => r.win).length / high.length;
  const wrLow = low.filter((r) => r.win).length / low.length;
  const corr = pearsonCorrelation(
    scored.map((r) => r.score),
    scored.map((r) => r.profit)
  );

  return (wrHigh - wrLow) + corr * 0.15;
}

/**
 * @param {import('../scoring/ScoringEngine.js').ScoredSignalSet|null} scoredSet
 * @param {import('../simulation/SimulationEngine.js').SimulationResult|null} simResult
 * @param {number} [minScoreCutoff=65]
 * @returns {ScoreCalibrationReport}
 */
export function buildCalibrationReport(scoredSet, simResult, minScoreCutoff = 65) {
  if (!calibrationContextsMatch(scoredSet, simResult)) {
    return {
      matched: false,
      reason: 'Ch?y Simulation (Ctrl+4) cùng Strategy / Symbol / TF v?i l?n scan g?n nh?t.',
    };
  }

  const joined = joinTradesWithScores(simResult.trades, scoredSet.signals);
  if (joined.length === 0) {
    return {
      matched: false,
      reason: 'Không ghép ???c l?nh v?i ?i?m AI — th? scan + simulation l?i.',
    };
  }

  const buckets = summarizeByScoreBucket(joined);
  const factors = summarizeFactorDiscrimination(joined);
  const scores = joined.map((r) => r.score);
  const profits = joined.map((r) => r.trade.profit);
  const high = joined.filter((r) => r.score >= minScoreCutoff);
  const low = joined.filter((r) => r.score < minScoreCutoff);

  return {
    matched: true,
    matchedTrades: joined.length,
    skippedTrades: simResult.trades.length - joined.length,
    buckets,
    factors,
    scoreProfitCorrelation: pearsonCorrelation(scores, profits),
    highScoreWinRate: high.length
      ? (high.filter((r) => r.trade.outcome === 'win').length / high.length) * 100
      : 0,
    lowScoreWinRate: low.length
      ? (low.filter((r) => r.trade.outcome === 'win').length / low.length) * 100
      : 0,
    minScoreCutoffUsed: minScoreCutoff,
  };
}

/**
 * @typedef {Object} WeightSuggestion
 * @property {Record<string, number>} weights
 * @property {number} fitness
 * @property {number} baselineFitness
 * @property {string} [note]
 */

/**
 * Greedy search for weights that separate wins from losses better.
 * @param {JoinedScoreTrade[]} rows
 * @param {Record<string, number>} [baseWeights]
 * @returns {WeightSuggestion}
 */
export function suggestScoringWeights(rows, baseWeights = getDefaultScoringWeights()) {
  if (rows.length < 10) {
    return {
      weights: { ...baseWeights },
      fitness: calibrationFitness(rows, baseWeights),
      baselineFitness: calibrationFitness(rows, baseWeights),
      note: 'C?n ?10 l?nh kh?p ?i?m AI ?? g?i ý tr?ng s? ?áng tin.',
    };
  }

  let best = normalizeScoringWeights({ ...baseWeights });
  let bestFitness = calibrationFitness(rows, best);
  const baselineFitness = bestFitness;
  const keys = Object.keys(best);
  const steps = [0.03, 0.05, 0.08];

  for (let round = 0; round < 30; round++) {
    let improved = false;
    for (const key of keys) {
      for (const step of steps) {
        for (const dir of [1, -1]) {
          const candidate = normalizeScoringWeights({
            ...best,
            [key]: Math.max(0.02, best[key] + dir * step),
          });
          const fitness = calibrationFitness(rows, candidate);
          if (fitness > bestFitness + 0.0001) {
            best = candidate;
            bestFitness = fitness;
            improved = true;
          }
        }
      }
    }
    if (!improved) break;
  }

  return {
    weights: best,
    fitness: bestFitness,
    baselineFitness,
    note: bestFitness > baselineFitness
      ? 'Tr?ng s? g?i ý tách l?nh th?ng/thua t?t h?n m?c ??nh trên sample này — v?n c?n Walk Forward.'
      : 'M?c ??nh ?ã ?n trên sample này; t?ng s? l?nh ho?c ??i period tr??c khi áp d?ng.',
  };
}

/**
 * @param {import('../scoring/ScoringEngine.js').ScoredSignalSet} scoredSet
 * @param {import('../simulation/SimulationEngine.js').SimulationResult} simResult
 * @param {Record<string, number>} [baseWeights]
 * @returns {WeightSuggestion}
 */
export function suggestWeightsFromSimulation(scoredSet, simResult, baseWeights) {
  const joined = joinTradesWithScores(simResult.trades, scoredSet.signals);
  return suggestScoringWeights(joined, baseWeights);
}
