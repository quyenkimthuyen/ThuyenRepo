/**
 * Trade simulation configuration defaults and validation.
 * @module simulation/TradeConfig
 */

import { Config } from '../core/Config.js';

/**
 * @typedef {'market'|'pending'} OrderType
 */

/**
 * @typedef {Object} TradeConfig
 * @property {OrderType} orderType
 * @property {number} spreadPips
 * @property {number} slippagePips
 * @property {number} commissionPerLot
 * @property {number} lotSize
 * @property {number} maxBarsInTrade
 * @property {number} pendingMaxBars
 * @property {number} trailingStopPips
 * @property {number} breakEvenAtR
 * @property {number} partialCloseAtR
 * @property {number} partialClosePercent
 * @property {number} initialBalance
 */

/**
 * @returns {TradeConfig}
 */
export function getDefaultTradeConfig() {
  const s = Config.SIMULATION;
  return {
    orderType: 'market',
    spreadPips: s.SPREAD_PIPS,
    slippagePips: s.SLIPPAGE_PIPS,
    commissionPerLot: s.COMMISSION_PER_LOT,
    lotSize: s.DEFAULT_LOT_SIZE,
    maxBarsInTrade: s.MAX_BARS_IN_TRADE,
    pendingMaxBars: s.PENDING_MAX_BARS,
    trailingStopPips: s.TRAILING_STOP_PIPS,
    breakEvenAtR: s.BREAK_EVEN_AT_R,
    partialCloseAtR: s.PARTIAL_CLOSE_AT_R,
    partialClosePercent: s.PARTIAL_CLOSE_PERCENT,
    initialBalance: s.INITIAL_BALANCE,
  };
}

/**
 * @param {Partial<TradeConfig>} partial
 * @returns {TradeConfig}
 */
export function mergeTradeConfig(partial = {}) {
  return { ...getDefaultTradeConfig(), ...partial };
}
