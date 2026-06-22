/**
 * Trading signal model and factory helpers.
 * @module strategy/Signal
 */

import { Config } from '../core/Config.js';

/** @typedef {'long'|'short'} Direction */

/**
 * @typedef {Object} ScreenshotPosition
 * @property {number} candleIndex - Index in the candle array
 * @property {number} timestamp - Epoch ms of the signal candle
 */

/**
 * @typedef {Object} Signal
 * @property {string} id - Unique signal identifier
 * @property {number} time - Signal timestamp (epoch ms)
 * @property {string} pair - Currency pair
 * @property {string} timeframe
 * @property {Direction} direction
 * @property {number} entry
 * @property {number} sl - Stop loss price
 * @property {number} tp - Take profit price
 * @property {number} rr - Risk-reward ratio
 * @property {number} confidence - Score 0–100
 * @property {string} reason - Human-readable setup description
 * @property {ScreenshotPosition} screenshotPosition
 * @property {string} strategyId - Originating strategy plugin ID
 */

let signalCounter = 0;

/**
 * Generate a unique signal ID.
 * @returns {string}
 */
export function createSignalId() {
  signalCounter += 1;
  return `sig_${Date.now()}_${signalCounter}`;
}

/**
 * Create a fully-formed signal object.
 * @param {Partial<Signal> & Pick<Signal, 'pair'|'timeframe'|'direction'|'entry'|'sl'|'tp'|'strategyId'>} fields
 * @returns {Signal}
 */
export function createSignal(fields) {
  const entry = fields.entry;
  const sl = fields.sl;
  const tp = fields.tp;
  const risk = Math.abs(entry - sl);
  const reward = Math.abs(tp - entry);
  const rr = fields.rr ?? (risk > 0 ? reward / risk : Config.STRATEGY.DEFAULT_RR);

  return {
    id: fields.id ?? createSignalId(),
    time: fields.time ?? 0,
    pair: fields.pair,
    timeframe: fields.timeframe,
    direction: fields.direction,
    entry,
    sl,
    tp,
    rr,
    confidence: fields.confidence ?? Config.STRATEGY.DEFAULT_CONFIDENCE,
    reason: fields.reason ?? '',
    screenshotPosition: fields.screenshotPosition ?? {
      candleIndex: 0,
      timestamp: fields.time ?? 0,
    },
    strategyId: fields.strategyId,
  };
}

/**
 * Validate a signal object has required fields and sane values.
 * @param {Partial<Signal>} signal
 * @returns {boolean}
 */
export function isValidSignal(signal) {
  if (!signal) return false;
  if (!signal.pair || !signal.timeframe || !signal.strategyId) return false;
  if (!['long', 'short'].includes(signal.direction)) return false;
  if ([signal.entry, signal.sl, signal.tp, signal.time].some(
    (v) => typeof v !== 'number' || Number.isNaN(v)
  )) return false;

  if (signal.direction === 'long') {
    if (signal.sl >= signal.entry || signal.tp <= signal.entry) return false;
  } else {
    if (signal.sl <= signal.entry || signal.tp >= signal.entry) return false;
  }

  return true;
}

/**
 * Calculate risk-reward ratio from prices.
 * @param {Direction} direction
 * @param {number} entry
 * @param {number} sl
 * @param {number} tp
 * @returns {number}
 */
export function calculateRR(direction, entry, sl, tp) {
  const risk = Math.abs(entry - sl);
  const reward = Math.abs(tp - entry);
  return risk > 0 ? reward / risk : 0;
}
