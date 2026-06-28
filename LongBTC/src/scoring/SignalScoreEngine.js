/**
 * AI signal scoring engine — composite 0–100 score with factor breakdown.
 * @module scoring/SignalScoreEngine
 */

import { Config } from '../core/Config.js';
import {
  scoreTrend,
  scoreMomentum,
  scoreLocation,
  scoreVolatility,
  scorePriceActionQuality,
  scoreRR,
  scoreSession,
  scoreSpread,
} from './ScoreFactors.js';
import { getScoringWeights } from './ScoringWeights.js';

/** @typedef {import('../strategy/Signal.js').Signal} Signal */
/** @typedef {import('../data/Candle.js').Candle} Candle */

/**
 * @typedef {Object} ScoreFactors
 * @property {number} trend
 * @property {number} momentum
 * @property {number} location
 * @property {number} volatility
 * @property {number} priceActionQuality
 * @property {number} rr
 * @property {number} session
 * @property {number} spread
 */

/**
 * @typedef {Object} SignalScore
 * @property {number} score
 * @property {'A'|'B'|'C'|'D'|'F'} grade
 * @property {ScoreFactors} factors
 */

/**
 * @typedef {Signal & { scoreBreakdown?: SignalScore }} ScoredSignal
 */

/**
 * Resolve bar index for a signal within candle array.
 * @param {Signal} signal
 * @param {Candle[]} candles
 * @returns {number}
 */
export function resolveSignalBarIndex(signal, candles) {
  if (signal.screenshotPosition?.candleIndex != null) {
    return Math.min(signal.screenshotPosition.candleIndex, candles.length - 1);
  }

  for (let i = 0; i < candles.length; i++) {
    if (candles[i].timestamp === signal.time) return i;
    if (candles[i].timestamp > signal.time) return Math.max(0, i - 1);
  }

  return Math.max(0, candles.length - 1);
}

/**
 * Map numeric score to letter grade.
 * @param {number} score
 * @returns {'A'|'B'|'C'|'D'|'F'}
 */
export function scoreToGrade(score) {
  if (score >= 80) return 'A';
  if (score >= 65) return 'B';
  if (score >= 50) return 'C';
  if (score >= 35) return 'D';
  return 'F';
}

/**
 * @param {ScoreFactors} factors
 * @param {Record<string, number>} weights
 * @returns {number}
 */
export function composeScoreFromFactors(factors, weights) {
  let totalWeight = 0;
  let weighted = 0;
  for (const [key, weight] of Object.entries(weights)) {
    const value = factors[/** @type {keyof ScoreFactors} */ (key)];
    if (typeof value !== 'number') continue;
    weighted += value * weight;
    totalWeight += weight;
  }
  return Math.round(weighted / (totalWeight || 1));
}

/**
 * Compute weighted AI score for a single signal.
 * @param {Signal} signal
 * @param {Candle[]} candles
 * @param {number} [spreadPips]
 * @param {Record<string, number>} [weights]
 * @returns {SignalScore}
 */
export function scoreSignal(signal, candles, spreadPips, weights) {
  const spread = spreadPips ?? Config.SIMULATION.SPREAD_PIPS;
  const index = resolveSignalBarIndex(signal, candles);

  /** @type {ScoreFactors} */
  const factors = {
    trend: scoreTrend(candles, index, signal.direction),
    momentum: scoreMomentum(candles, index, signal.direction, signal.pair),
    location: scoreLocation(signal),
    volatility: scoreVolatility(candles, index, signal.pair),
    priceActionQuality: scorePriceActionQuality(candles, index, signal.direction),
    rr: scoreRR(signal.rr),
    session: scoreSession(signal.time),
    spread: scoreSpread(spread),
  };

  const activeWeights = weights ?? getScoringWeights();
  let totalWeight = 0;
  let weighted = 0;

  for (const [key, weight] of Object.entries(activeWeights)) {
    const value = factors[/** @type {keyof ScoreFactors} */ (key)];
    weighted += value * weight;
    totalWeight += weight;
  }

  const score = Math.round(weighted / (totalWeight || 1));

  return {
    score,
    grade: scoreToGrade(score),
    factors,
  };
}

/**
 * Score a batch of signals.
 * @param {Signal[]} signals
 * @param {Candle[]} candles
 * @param {number} [spreadPips]
 * @returns {ScoredSignal[]}
 */
export function scoreSignalsBatch(signals, candles, spreadPips) {
  return signals.map((signal) => {
    const breakdown = scoreSignal(signal, candles, spreadPips);
    return {
      ...signal,
      confidence: breakdown.score,
      scoreBreakdown: breakdown,
    };
  });
}

/**
 * Filter signals by minimum AI score.
 * @param {ScoredSignal[]} signals
 * @param {number} minScore
 * @returns {ScoredSignal[]}
 */
export function filterByMinScore(signals, minScore) {
  return signals.filter((s) => (s.scoreBreakdown?.score ?? s.confidence) >= minScore);
}
