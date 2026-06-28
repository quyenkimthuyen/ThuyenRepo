/**
 * Shared candle pattern and level zone helpers per STRATEGY_SPECIFICATION.md §2.
 * @module strategy/helpers/CandlePatterns
 */

import { getPipSize, pipsToPrice } from '../../utils/pip.js';

/** Default retest zone tolerance in pips (§2.4). */
export const RETEST_TOLERANCE_PIPS = 2;

/** Stop-loss buffer in pips (§2.6). */
export const SL_BUFFER_PIPS = 1;

/**
 * @typedef {import('../../data/Candle.js').Candle} Candle
 */

/**
 * @param {Candle} candle
 * @returns {number}
 */
export function getCandleRange(candle) {
  return candle.high - candle.low;
}

/**
 * @param {Candle} candle
 * @param {string} symbol
 * @returns {boolean}
 */
export function isDoji(candle, symbol) {
  return getCandleRange(candle) < 0.5 * getPipSize(symbol);
}

/**
 * Bullish confirmation candle (§2.5).
 * @param {Candle} candle
 * @param {string} symbol
 * @returns {boolean}
 */
export function isBullishConfirmation(candle, symbol) {
  if (isDoji(candle, symbol)) return false;
  const range = getCandleRange(candle);
  const bullishCloseZone = candle.low + 0.6 * range;
  return candle.close > candle.open && candle.close >= bullishCloseZone;
}

/**
 * Bearish confirmation candle (§2.5).
 * @param {Candle} candle
 * @param {string} symbol
 * @returns {boolean}
 */
export function isBearishConfirmation(candle, symbol) {
  if (isDoji(candle, symbol)) return false;
  const range = getCandleRange(candle);
  const bearishCloseZone = candle.low + 0.4 * range;
  return candle.close < candle.open && candle.close <= bearishCloseZone;
}

/**
 * Price touches a level zone (§2.4).
 * @param {Candle} candle
 * @param {number} level
 * @param {number} tolerancePips
 * @param {string} symbol
 * @returns {boolean}
 */
export function touchesZone(candle, level, tolerancePips, symbol) {
  const zoneUpper = level + pipsToPrice(tolerancePips, symbol);
  const zoneLower = level - pipsToPrice(tolerancePips, symbol);
  return candle.low <= zoneUpper && candle.high >= zoneLower;
}

/**
 * @param {Candle} candle
 * @returns {{ upper: number, lower: number, range: number }}
 */
export function getWicks(candle) {
  const bodyTop = Math.max(candle.open, candle.close);
  const bodyBottom = Math.min(candle.open, candle.close);
  return {
    upper: candle.high - bodyTop,
    lower: bodyBottom - candle.low,
    range: getCandleRange(candle),
  };
}

/**
 * Body size as fraction of total range.
 * @param {Candle} candle
 * @returns {number}
 */
export function bodyRatio(candle) {
  const range = getCandleRange(candle);
  if (range <= 0) return 0;
  return Math.abs(candle.close - candle.open) / range;
}

/**
 * @param {number} level
 * @param {number} tolerancePips
 * @param {string} symbol
 * @returns {{ upper: number, lower: number }}
 */
export function getLevelZone(level, tolerancePips, symbol) {
  const tol = pipsToPrice(tolerancePips, symbol);
  return { upper: level + tol, lower: level - tol };
}

/**
 * Inside bar: child range fully within mother range.
 * @param {Candle} child
 * @param {Candle} mother
 * @returns {boolean}
 */
export function isInsideBar(child, mother) {
  return child.high < mother.high && child.low > mother.low;
}

/**
 * Pin bar rejection pattern (wick dominant, small body).
 * @param {Candle} candle
 * @param {'long'|'short'} direction — long = hammer at support, short = shooting star at resistance
 * @param {number} minWickRatio
 * @param {number} maxBodyRatio
 * @returns {boolean}
 */
export function isPinBar(candle, direction, minWickRatio, maxBodyRatio) {
  const wicks = getWicks(candle);
  if (wicks.range <= 0) return false;
  if (bodyRatio(candle) > maxBodyRatio) return false;

  if (direction === 'long') {
    return wicks.lower / wicks.range >= minWickRatio;
  }
  return wicks.upper / wicks.range >= minWickRatio;
}
