/**
 * Open position state during bar-by-bar simulation.
 * @module simulation/Position
 */

import { pipsToPrice } from '../utils/pip.js';

/**
 * @typedef {Object} PartialClose
 * @property {number} barIndex
 * @property {number} timestamp
 * @property {number} price
 * @property {number} percent
 * @property {number} pips
 * @property {number} profit
 */

/**
 * @typedef {Object} OpenPosition
 * @property {string} signalId
 * @property {string} strategyId
 * @property {string} symbol
 * @property {'long'|'short'} direction
 * @property {number} entryPrice
 * @property {number} sl
 * @property {number} tp
 * @property {number} initialSl
 * @property {number} sizeRemaining
 * @property {number} entryBar
 * @property {number} entryTime
 * @property {number} riskDistance
 * @property {boolean} breakEvenApplied
 * @property {boolean} partialCloseDone
 * @property {PartialClose[]} partialCloses
 * @property {number} accumulatedProfit
 */

/**
 * Create a new open position from a filled entry.
 * @param {Object} params
 * @returns {OpenPosition}
 */
export function createPosition(params) {
  return {
    signalId: params.signalId,
    strategyId: params.strategyId,
    symbol: params.symbol,
    direction: params.direction,
    entryPrice: params.entryPrice,
    sl: params.sl,
    tp: params.tp,
    initialSl: params.sl,
    sizeRemaining: 1,
    entryBar: params.entryBar,
    entryTime: params.entryTime,
    riskDistance: Math.abs(params.entryPrice - params.sl),
    breakEvenApplied: false,
    partialCloseDone: false,
    partialCloses: [],
    accumulatedProfit: 0,
  };
}

/**
 * Move stop loss to break-even (entry price).
 * @param {OpenPosition} pos
 */
export function applyBreakEven(pos) {
  pos.sl = pos.entryPrice;
  pos.breakEvenApplied = true;
}

/**
 * Update trailing stop based on candle extreme.
 * @param {OpenPosition} pos
 * @param {import('../data/Candle.js').Candle} candle
 * @param {number} trailingPips
 * @param {string} symbol
 */
export function updateTrailingStop(pos, candle, trailingPips, symbol) {
  if (trailingPips <= 0) return;

  const trail = pipsToPrice(trailingPips, symbol);

  if (pos.direction === 'long') {
    const newSl = candle.high - trail;
    if (newSl > pos.sl && newSl < candle.close) {
      pos.sl = newSl;
    }
  } else {
    const newSl = candle.low + trail;
    if (newSl < pos.sl && newSl > candle.close) {
      pos.sl = newSl;
    }
  }
}

/**
 * Record a partial close on the position.
 * @param {OpenPosition} pos
 * @param {PartialClose} partial
 * @param {number} percent
 */
export function recordPartialClose(pos, partial, percent) {
  pos.partialCloses.push(partial);
  pos.accumulatedProfit += partial.profit;
  pos.sizeRemaining -= percent / 100;
  pos.partialCloseDone = true;
}
