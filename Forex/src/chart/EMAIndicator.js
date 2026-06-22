/**
 * EMA (Exponential Moving Average) indicator calculator.
 * Only uses visible candles — no lookahead during replay.
 * @module chart/EMAIndicator
 */

/**
 * @typedef {import('../data/Candle.js').Candle} Candle
 */

/**
 * @typedef {Object} EmaPoint
 * @property {number} time - UTCTimestamp seconds
 * @property {number} value
 */

/**
 * Calculate EMA values for a candle array.
 * Returns null for indices before the period is filled.
 * @param {Candle[]} candles
 * @param {number} period
 * @returns {(number|null)[]}
 */
export function calculateEMA(candles, period) {
  if (candles.length === 0 || period < 1) return [];

  const k = 2 / (period + 1);
  const result = [];
  let ema = null;

  for (let i = 0; i < candles.length; i++) {
    if (i < period - 1) {
      result.push(null);
      continue;
    }

    if (ema === null) {
      let sum = 0;
      for (let j = 0; j < period; j++) {
        sum += candles[j].close;
      }
      ema = sum / period;
    } else {
      ema = candles[i].close * k + ema * (1 - k);
    }

    result.push(ema);
  }

  return result;
}

/**
 * Build Lightweight Charts line data from EMA values.
 * @param {Candle[]} candles
 * @param {number} period
 * @returns {EmaPoint[]}
 */
export function buildEmaLineData(candles, period) {
  const emaValues = calculateEMA(candles, period);
  const points = [];

  for (let i = 0; i < candles.length; i++) {
    if (emaValues[i] !== null) {
      points.push({
        time: Math.floor(candles[i].timestamp / 1000),
        value: emaValues[i],
      });
    }
  }

  return points;
}
