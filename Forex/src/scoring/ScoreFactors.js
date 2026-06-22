/**
 * Individual AI signal score factors (0–100 each).
 * @module scoring/ScoreFactors
 */

import { getSession } from '../chart/SessionUtils.js';
import { emaAtIndex } from '../strategy/helpers/EmaHelper.js';
import { bodyRatio, getCandleRange, getWicks, isBullishConfirmation, isBearishConfirmation } from '../strategy/helpers/CandlePatterns.js';
import { priceToPips } from '../utils/pip.js';

/** @typedef {import('../data/Candle.js').Candle} Candle */
/** @typedef {import('../strategy/Signal.js').Signal} Signal */

/**
 * Score trend alignment via EMA20/EMA50 structure.
 * @param {Candle[]} candles
 * @param {number} index
 * @param {'long'|'short'} direction
 * @returns {number}
 */
export function scoreTrend(candles, index, direction) {
  const ema20 = emaAtIndex(candles, index, 20);
  const ema50 = emaAtIndex(candles, index, 50);
  if (ema20 === null || ema50 === null) return 50;

  const close = candles[index].close;
  if (direction === 'long') {
    if (close > ema20 && ema20 > ema50) return 100;
    if (close > ema20) return 70;
    if (close > ema50) return 40;
    return 20;
  }

  if (close < ema20 && ema20 < ema50) return 100;
  if (close < ema20) return 70;
  if (close < ema50) return 40;
  return 20;
}

/**
 * Score momentum from confirmation candle body strength.
 * @param {Candle[]} candles
 * @param {number} index
 * @param {'long'|'short'} direction
 * @param {string} symbol
 * @returns {number}
 */
export function scoreMomentum(candles, index, direction, symbol) {
  const candle = candles[index];
  const ratio = bodyRatio(candle);
  const confirmed = direction === 'long'
    ? isBullishConfirmation(candle, symbol)
    : isBearishConfirmation(candle, symbol);

  let score = Math.min(100, ratio * 100);
  if (confirmed) score = Math.min(100, score + 15);
  return Math.round(score);
}

/**
 * Score entry location quality relative to SL distance.
 * @param {Signal} signal
 * @returns {number}
 */
export function scoreLocation(signal) {
  const riskPips = priceToPips(Math.abs(signal.entry - signal.sl), signal.pair);
  if (riskPips <= 5) return 100;
  if (riskPips <= 10) return 85;
  if (riskPips <= 20) return 65;
  if (riskPips <= 40) return 45;
  return 25;
}

/**
 * Score volatility — moderate ATR preferred over extreme chop or flat.
 * @param {Candle[]} candles
 * @param {number} index
 * @param {string} symbol
 * @returns {number}
 */
export function scoreVolatility(candles, index, symbol) {
  const lookback = 14;
  const start = Math.max(0, index - lookback + 1);
  const slice = candles.slice(start, index + 1);
  if (slice.length < 3) return 50;

  const ranges = slice.map((c) => priceToPips(getCandleRange(c), symbol));
  const avg = ranges.reduce((s, r) => s + r, 0) / ranges.length;

  if (avg >= 8 && avg <= 25) return 100;
  if (avg >= 5 && avg <= 35) return 75;
  if (avg >= 3 && avg <= 50) return 50;
  return 30;
}

/**
 * Score price action quality via wick rejection on signal candle.
 * @param {Candle[]} candles
 * @param {number} index
 * @param {'long'|'short'} direction
 * @returns {number}
 */
export function scorePriceActionQuality(candles, index, direction) {
  const candle = candles[index];
  const { upper, lower } = getWicks(candle);
  const range = getCandleRange(candle);
  if (range <= 0) return 40;

  const upperRatio = upper / range;
  const lowerRatio = lower / range;

  if (direction === 'long') {
    if (lowerRatio >= 0.4 && upperRatio <= 0.25) return 100;
    if (lowerRatio >= 0.25) return 75;
    return 45;
  }

  if (upperRatio >= 0.4 && lowerRatio <= 0.25) return 100;
  if (upperRatio >= 0.25) return 75;
  return 45;
}

/**
 * Score risk-reward ratio.
 * @param {number} rr
 * @returns {number}
 */
export function scoreRR(rr) {
  if (rr >= 3) return 100;
  if (rr >= 2.5) return 90;
  if (rr >= 2) return 80;
  if (rr >= 1.5) return 60;
  if (rr >= 1) return 40;
  return 20;
}

/**
 * Score trading session liquidity.
 * @param {number} timestamp
 * @returns {number}
 */
export function scoreSession(timestamp) {
  const session = getSession(timestamp);
  if (session === 'London' || session === 'New York') return 100;
  if (session === 'Tokyo') return 70;
  if (session === 'Sydney') return 50;
  return 30;
}

/**
 * Score spread conditions (lower spread = higher score).
 * @param {number} spreadPips
 * @returns {number}
 */
export function scoreSpread(spreadPips) {
  if (spreadPips <= 1) return 100;
  if (spreadPips <= 1.5) return 85;
  if (spreadPips <= 2.5) return 65;
  if (spreadPips <= 4) return 45;
  return 25;
}
