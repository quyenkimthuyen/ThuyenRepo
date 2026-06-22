/**
 * Candle sampling for high-performance chart rendering.
 * @module performance/CandleSampler
 */

import { Config } from '../core/Config.js';

/** @typedef {import('../data/Candle.js').Candle} Candle */

/**
 * Limit candles passed to chart renderer.
 * @param {Candle[]} candles
 * @param {number} [maxBars]
 * @returns {Candle[]}
 */
export function limitChartCandles(candles, maxBars = Config.PERFORMANCE.MAX_CHART_RENDER_BARS) {
  if (candles.length <= maxBars) return candles;
  return candles.slice(candles.length - maxBars);
}

/**
 * Uniformly sample candles to a target count (for overview mode).
 * @param {Candle[]} candles
 * @param {number} targetCount
 * @returns {Candle[]}
 */
export function uniformSample(candles, targetCount) {
  if (candles.length <= targetCount) return candles;

  const step = candles.length / targetCount;
  /** @type {Candle[]} */
  const result = [];

  for (let i = 0; i < targetCount; i++) {
    result.push(candles[Math.floor(i * step)]);
  }

  return result;
}

/**
 * Check if dataset exceeds worker offload threshold.
 * @param {number} candleCount
 * @returns {boolean}
 */
export function shouldUseWorker(candleCount) {
  return candleCount >= Config.PERFORMANCE.WORKER_THRESHOLD;
}
