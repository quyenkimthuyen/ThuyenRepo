/**
 * Convert internal candles to Lightweight Charts format.
 * @module chart/CandleAdapter
 */

/**
 * @typedef {import('../data/Candle.js').Candle} Candle
 */

/**
 * @typedef {Object} ChartCandle
 * @property {number} time - UTCTimestamp in seconds
 * @property {number} open
 * @property {number} high
 * @property {number} low
 * @property {number} close
 */

/**
 * Convert a single candle to Lightweight Charts format.
 * @param {Candle} candle
 * @returns {ChartCandle}
 */
export function toChartCandle(candle) {
  return {
    time: Math.floor(candle.timestamp / 1000),
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
  };
}

/**
 * Convert an array of candles.
 * @param {Candle[]} candles
 * @returns {ChartCandle[]}
 */
export function toChartCandles(candles) {
  return candles.map(toChartCandle);
}

/**
 * Convert chart time (seconds) back to epoch ms.
 * @param {number} time
 * @returns {number}
 */
export function chartTimeToMs(time) {
  return time * 1000;
}
