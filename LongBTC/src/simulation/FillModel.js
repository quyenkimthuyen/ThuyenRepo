/**
 * Spread, slippage, and commission fill model.
 * @module simulation/FillModel
 */

import { Config } from '../core/Config.js';
import { pipsToPrice, priceToPips, getPipSize } from '../utils/pip.js';

/**
 * Half spread in price units.
 * @param {string} symbol
 * @param {number} spreadPips
 * @returns {number}
 */
export function halfSpread(symbol, spreadPips) {
  return pipsToPrice(spreadPips / 2, symbol);
}

/**
 * Apply slippage against the trader (worse fill).
 * @param {number} price
 * @param {'long'|'short'} direction
 * @param {'entry'|'exit'} side
 * @param {string} symbol
 * @param {number} slippagePips
 * @returns {number}
 */
export function applySlippage(price, direction, side, symbol, slippagePips) {
  const slip = pipsToPrice(slippagePips, symbol);
  const isBuy = (direction === 'long' && side === 'entry') || (direction === 'short' && side === 'exit');
  return isBuy ? price + slip : price - slip;
}

/**
 * Market entry fill price for a direction.
 * @param {number} midPrice
 * @param {'long'|'short'} direction
 * @param {string} symbol
 * @param {number} spreadPips
 * @param {number} slippagePips
 * @returns {number}
 */
export function marketEntryFill(midPrice, direction, symbol, spreadPips, slippagePips) {
  const half = halfSpread(symbol, spreadPips);
  const ask = midPrice + half;
  const bid = midPrice - half;
  const raw = direction === 'long' ? ask : bid;
  return applySlippage(raw, direction, 'entry', symbol, slippagePips);
}

/**
 * Market exit fill price for a direction.
 * @param {number} midPrice
 * @param {'long'|'short'} direction
 * @param {string} symbol
 * @param {number} spreadPips
 * @param {number} slippagePips
 * @returns {number}
 */
export function marketExitFill(midPrice, direction, symbol, spreadPips, slippagePips) {
  const half = halfSpread(symbol, spreadPips);
  const ask = midPrice + half;
  const bid = midPrice - half;
  const raw = direction === 'long' ? bid : ask;
  return applySlippage(raw, direction, 'exit', symbol, slippagePips);
}

/**
 * Round-trip commission for a trade.
 * @param {number} lotSize
 * @param {number} commissionPerLot
 * @returns {number}
 */
export function roundTripCommission(lotSize, commissionPerLot) {
  return lotSize * commissionPerLot * 2;
}

/**
 * Convert pip profit to account currency.
 * @param {number} pips
 * @param {string} symbol
 * @param {number} lotSize
 * @returns {number}
 */
export function pipsToMoney(pips, symbol, lotSize) {
  return pips * lotSize * Config.SIMULATION.PIP_VALUE_PER_LOT;
}

/**
 * @param {number} entry
 * @param {number} exit
 * @param {'long'|'short'} direction
 * @param {string} symbol
 * @returns {number}
 */
export function calcPips(entry, exit, direction, symbol) {
  const diff = direction === 'long' ? exit - entry : entry - exit;
  return priceToPips(diff, symbol);
}

/**
 * @param {number} price
 * @param {string} symbol
 * @returns {number}
 */
export function normalizePrice(price, symbol) {
  const pip = getPipSize(symbol);
  const decimals = pip >= 0.01 ? 2 : 5;
  return Number(price.toFixed(decimals));
}
