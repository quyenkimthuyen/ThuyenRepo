/**
 * Monte Carlo simulation — bootstrap trade sequences for risk distribution.
 * @module optimizer/MonteCarloEngine
 */

import { buildEquityCurve, calcMaxDrawdown } from '../statistics/EquityCurve.js';

/** @typedef {import('../simulation/TradeSimulator.js').TradeResult} TradeResult */

/**
 * @typedef {Object} MonteCarloIteration
 * @property {number} finalBalance
 * @property {number} netProfit
 * @property {number} maxDrawdown
 * @property {number} maxDrawdownPercent
 */

/**
 * @typedef {Object} MonteCarloPercentiles
 * @property {MonteCarloIteration} p5
 * @property {MonteCarloIteration} p50
 * @property {MonteCarloIteration} p95
 */

/**
 * @typedef {Object} MonteCarloResult
 * @property {number} iterations
 * @property {number} tradeCount
 * @property {number} initialBalance
 * @property {MonteCarloPercentiles} percentiles
 * @property {number} ruinRate
 * @property {number} durationMs
 */

/**
 * Fisher-Yates shuffle in place.
 * @param {TradeResult[]} arr
 */
function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
}

/**
 * @param {MonteCarloIteration[]} sorted
 * @param {number} pct
 * @returns {MonteCarloIteration}
 */
function percentile(sorted, pct) {
  const idx = Math.min(sorted.length - 1, Math.floor((pct / 100) * sorted.length));
  return sorted[idx];
}

/**
 * Run Monte Carlo by shuffling trade order.
 * @param {TradeResult[]} trades
 * @param {number} initialBalance
 * @param {number} [iterations=1000]
 * @returns {MonteCarloResult}
 */
export function runMonteCarlo(trades, initialBalance, iterations = 1000) {
  const start = performance.now();
  const closed = trades.filter((t) => t.outcome !== 'open' && t.outcome !== 'expired');

  if (closed.length === 0) {
    throw new Error('No closed trades for Monte Carlo simulation.');
  }

  /** @type {MonteCarloIteration[]} */
  const results = [];
  let ruinCount = 0;

  for (let i = 0; i < iterations; i++) {
    const shuffled = [...closed];
    shuffle(shuffled);

    const curve = buildEquityCurve(shuffled, initialBalance);
    const dd = calcMaxDrawdown(curve);
    const netProfit = shuffled.reduce((s, t) => s + t.profit, 0);
    const finalBalance = initialBalance + netProfit;

    if (finalBalance <= initialBalance * 0.5) ruinCount += 1;

    results.push({
      finalBalance,
      netProfit,
      maxDrawdown: dd.maxDrawdown,
      maxDrawdownPercent: dd.maxDrawdownPercent,
    });
  }

  const byBalance = [...results].sort((a, b) => a.finalBalance - b.finalBalance);

  return {
    iterations,
    tradeCount: closed.length,
    initialBalance,
    percentiles: {
      p5: percentile(byBalance, 5),
      p50: percentile(byBalance, 50),
      p95: percentile(byBalance, 95),
    },
    ruinRate: (ruinCount / iterations) * 100,
    durationMs: Math.round(performance.now() - start),
  };
}
