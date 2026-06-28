/**
 * EMA calculation helper — no lookahead, uses candles[0..index].
 * @module strategy/helpers/EmaHelper
 */

/**
 * @typedef {import('../../data/Candle.js').Candle} Candle
 */

/**
 * Calculate EMA at the last candle of the array.
 * @param {Candle[]} candles - Visible candles ending at target bar
 * @param {number} period
 * @returns {number|null}
 */
export function emaAt(candles, period) {
  if (candles.length < period) return null;

  const k = 2 / (period + 1);
  let ema = candles[0].close;

  for (let i = 1; i < candles.length; i++) {
    ema = candles[i].close * k + ema * (1 - k);
  }

  return ema;
}

/**
 * Get EMA value at a specific index using only prior candles.
 * @param {Candle[]} candles
 * @param {number} index
 * @param {number} period
 * @returns {number|null}
 */
export function emaAtIndex(candles, index, period) {
  if (index < period - 1) return null;
  return emaAt(candles.slice(0, index + 1), period);
}

/**
 * Count higher closes in window [start..end].
 * @param {Candle[]} candles
 * @param {number} start
 * @param {number} end
 * @returns {number}
 */
export function countHigherCloses(candles, start, end) {
  let count = 0;
  for (let i = start; i <= end; i++) {
    if (i > 0 && candles[i].close > candles[i - 1].close) count++;
  }
  return count;
}

/**
 * Count lower closes in window [start..end].
 * @param {Candle[]} candles
 * @param {number} start
 * @param {number} end
 * @returns {number}
 */
export function countLowerCloses(candles, start, end) {
  let count = 0;
  for (let i = start; i <= end; i++) {
    if (i > 0 && candles[i].close < candles[i - 1].close) count++;
  }
  return count;
}

/**
 * Dual-EMA trend: fast above slow, rising fast EMA, price on trend side, momentum window.
 * @param {Candle[]} candles
 * @param {number} index
 * @param {{ fastPeriod?: number, slowPeriod?: number, trendBars?: number }} [options]
 * @returns {'up'|'down'|'none'}
 */
export function detectEmaDualTrend(candles, index, options = {}) {
  const fastPeriod = options.fastPeriod ?? 20;
  const slowPeriod = options.slowPeriod ?? 50;
  const trendBars = options.trendBars ?? 5;

  const emaFast = emaAtIndex(candles, index, fastPeriod);
  const emaSlow = emaAtIndex(candles, index, slowPeriod);
  const emaFastPrev = emaAtIndex(candles, index - trendBars, fastPeriod);

  if (emaFast === null || emaSlow === null || emaFastPrev === null) return 'none';

  const minCount = Math.ceil(trendBars * 0.6);
  const windowStart = index - trendBars + 1;

  const higherCloses = countHigherCloses(candles, windowStart, index);
  const lowerCloses = countLowerCloses(candles, windowStart, index);

  if (
    emaFast > emaSlow &&
    emaFast > emaFastPrev &&
    candles[index].close > emaSlow &&
    higherCloses >= minCount
  ) {
    return 'up';
  }

  if (
    emaFast < emaSlow &&
    emaFast < emaFastPrev &&
    candles[index].close < emaSlow &&
    lowerCloses >= minCount
  ) {
    return 'down';
  }

  return 'none';
}
