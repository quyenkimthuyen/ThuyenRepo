/**
 * Entry, SL, TP calculation helpers.
 * @module strategy/helpers/TradeLevels
 */

import { pipsToPrice } from '../../utils/pip.js';
import { SL_BUFFER_PIPS } from './CandlePatterns.js';

/**
 * @param {number} entry
 * @param {number} sl
 * @param {number} rr
 * @returns {{ entry: number, sl: number, tp: number }}
 */
export function buildLongLevels(entry, sl, rr) {
  const risk = entry - sl;
  return { entry, sl, tp: entry + rr * risk };
}

/**
 * @param {number} entry
 * @param {number} sl
 * @param {number} rr
 * @returns {{ entry: number, sl: number, tp: number }}
 */
export function buildShortLevels(entry, sl, rr) {
  const risk = sl - entry;
  return { entry, sl, tp: entry - rr * risk };
}

/**
 * Apply SL buffer below a raw level (long).
 * @param {number} rawSl
 * @param {string} symbol
 * @returns {number}
 */
export function slBufferBelow(rawSl, symbol) {
  return rawSl - pipsToPrice(SL_BUFFER_PIPS, symbol);
}

/**
 * Apply SL buffer above a raw level (short).
 * @param {number} rawSl
 * @param {string} symbol
 * @returns {number}
 */
export function slBufferAbove(rawSl, symbol) {
  return rawSl + pipsToPrice(SL_BUFFER_PIPS, symbol);
}
