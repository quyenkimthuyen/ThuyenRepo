/**
 * Wyckoff trading-range helpers — consolidation bounds, spring, UTAD.
 * @module strategy/helpers/WyckoffRange
 */

import { pipsToPrice, priceToPips } from '../../utils/pip.js';
import {
  isBullishConfirmation,
  isBearishConfirmation,
  getWicks,
  touchesZone,
} from './CandlePatterns.js';

/**
 * @typedef {import('../../data/Candle.js').Candle} Candle
 * @typedef {{ rangeHigh: number, rangeLow: number }} TradingRange
 */

/**
 * Horizontal range from prior bars only (no lookahead).
 * @param {Candle[]} candles
 * @param {number} index
 * @param {number} lookback
 * @returns {TradingRange|null}
 */
export function getTradingRange(candles, index, lookback) {
  if (index < lookback) return null;

  let rangeHigh = -Infinity;
  let rangeLow = Infinity;

  for (let j = index - lookback; j < index; j++) {
    rangeHigh = Math.max(rangeHigh, candles[j].high);
    rangeLow = Math.min(rangeLow, candles[j].low);
  }

  if (!Number.isFinite(rangeHigh) || !Number.isFinite(rangeLow)) return null;
  return { rangeHigh, rangeLow };
}

/**
 * @param {number} rangeHigh
 * @param {number} rangeLow
 * @param {string} symbol
 * @returns {number}
 */
export function rangeWidthPips(rangeHigh, rangeLow, symbol) {
  return priceToPips(rangeHigh - rangeLow, symbol);
}

/**
 * Fraction of closes that stayed inside the range (consolidation quality).
 * @param {Candle[]} candles
 * @param {number} index
 * @param {number} lookback
 * @param {number} rangeHigh
 * @param {number} rangeLow
 * @returns {number}
 */
export function closeInsideRatio(candles, index, lookback, rangeHigh, rangeLow) {
  let inside = 0;
  for (let j = index - lookback; j < index; j++) {
    const close = candles[j].close;
    if (close >= rangeLow && close <= rangeHigh) inside++;
  }
  return lookback > 0 ? inside / lookback : 0;
}

/**
 * @param {Candle[]} candles
 * @param {number} index
 * @param {number} lookback
 * @param {number} rangeHigh
 * @param {number} rangeLow
 * @param {number} minInsideRatio
 * @returns {boolean}
 */
export function isConsolidationRange(
  candles, index, lookback, rangeHigh, rangeLow, minInsideRatio
) {
  return closeInsideRatio(candles, index, lookback, rangeHigh, rangeLow) >= minInsideRatio;
}

/**
 * Wyckoff spring: sweep below range support, close back inside range.
 * @param {Candle} candle
 * @param {number} rangeLow
 * @param {number} sweepPips
 * @param {number} pip
 * @param {number} minWickRatio
 * @param {string} symbol
 * @returns {boolean}
 */
export function isWyckoffSpring(candle, rangeLow, sweepPips, pip, minWickRatio, symbol) {
  if (candle.low > rangeLow - sweepPips * pip) return false;
  if (candle.close <= rangeLow) return false;

  const wicks = getWicks(candle);
  if (wicks.range <= 0 || wicks.lower / wicks.range < minWickRatio) return false;
  if (!isBullishConfirmation(candle, symbol)) return false;

  return true;
}

/**
 * Wyckoff UTAD: sweep above range resistance, close back inside range.
 * @param {Candle} candle
 * @param {number} rangeHigh
 * @param {number} sweepPips
 * @param {number} pip
 * @param {number} minWickRatio
 * @param {string} symbol
 * @returns {boolean}
 */
export function isWyckoffUtad(candle, rangeHigh, sweepPips, pip, minWickRatio, symbol) {
  if (candle.high < rangeHigh + sweepPips * pip) return false;
  if (candle.close >= rangeHigh) return false;

  const wicks = getWicks(candle);
  if (wicks.range <= 0 || wicks.upper / wicks.range < minWickRatio) return false;
  if (!isBearishConfirmation(candle, symbol)) return false;

  return true;
}

/**
 * Secondary test of spring support — higher low, touch zone, bullish confirm.
 * @param {Candle} candle
 * @param {number} rangeLow
 * @param {number} springLow
 * @param {number} tolerancePips
 * @param {number} pip
 * @param {number} minWickRatio
 * @param {string} symbol
 * @returns {boolean}
 */
export function isWyckoffSpringTest(
  candle, rangeLow, springLow, tolerancePips, pip, minWickRatio, symbol
) {
  if (!touchesZone(candle, rangeLow, tolerancePips, symbol)) return false;
  if (candle.low <= springLow + pip * 0.5) return false;

  const wicks = getWicks(candle);
  if (wicks.range <= 0 || wicks.lower / wicks.range < minWickRatio) return false;
  if (!isBullishConfirmation(candle, symbol)) return false;

  return true;
}

/**
 * Secondary test after UTAD — lower high, touch zone, bearish confirm.
 * @param {Candle} candle
 * @param {number} rangeHigh
 * @param {number} utadHigh
 * @param {number} tolerancePips
 * @param {number} pip
 * @param {number} minWickRatio
 * @param {string} symbol
 * @returns {boolean}
 */
export function isWyckoffUtadTest(
  candle, rangeHigh, utadHigh, tolerancePips, pip, minWickRatio, symbol
) {
  if (!touchesZone(candle, rangeHigh, tolerancePips, symbol)) return false;
  if (candle.high >= utadHigh - pip * 0.5) return false;

  const wicks = getWicks(candle);
  if (wicks.range <= 0 || wicks.upper / wicks.range < minWickRatio) return false;
  if (!isBearishConfirmation(candle, symbol)) return false;

  return true;
}
