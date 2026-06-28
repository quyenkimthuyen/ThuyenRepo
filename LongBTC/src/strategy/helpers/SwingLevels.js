/**
 * Swing high/low level detection per STRATEGY_SPECIFICATION.md §2.3.
 * @module strategy/helpers/SwingLevels
 */

/**
 * @typedef {import('../../data/Candle.js').Candle} Candle
 */

/**
 * Swing high at bar index — max high in [index - lookback, index - 1].
 * @param {Candle[]} candles
 * @param {number} index
 * @param {number} lookback
 * @returns {number|null}
 */
export function swingHigh(candles, index, lookback) {
  if (index < lookback) return null;

  let max = -Infinity;
  for (let j = index - lookback; j < index; j++) {
    if (candles[j].high > max) max = candles[j].high;
  }

  return max === -Infinity ? null : max;
}

/**
 * Swing low at bar index — min low in [index - lookback, index - 1].
 * @param {Candle[]} candles
 * @param {number} index
 * @param {number} lookback
 * @returns {number|null}
 */
export function swingLow(candles, index, lookback) {
  if (index < lookback) return null;

  let min = Infinity;
  for (let j = index - lookback; j < index; j++) {
    if (candles[j].low < min) min = candles[j].low;
  }

  return min === Infinity ? null : min;
}
