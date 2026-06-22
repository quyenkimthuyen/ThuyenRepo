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
