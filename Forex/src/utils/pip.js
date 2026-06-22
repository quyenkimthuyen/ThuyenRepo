/**
 * Pip size utilities for forex symbols.
 * @module utils/pip
 */

/** @type {Record<string, number>} */
const PIP_SIZES = {
  EURUSD: 0.0001,
  GBPUSD: 0.0001,
  USDJPY: 0.01,
  XAUUSD: 0.01,
  BTCUSD: 1,
};

/**
 * Get pip size for a symbol.
 * @param {string} symbol
 * @returns {number}
 */
export function getPipSize(symbol) {
  return PIP_SIZES[symbol] ?? 0.0001;
}

/**
 * Convert pips to price distance.
 * @param {number} pips
 * @param {string} symbol
 * @returns {number}
 */
export function pipsToPrice(pips, symbol) {
  return pips * getPipSize(symbol);
}

/**
 * Convert price distance to pips.
 * @param {number} priceDiff
 * @param {string} symbol
 * @returns {number}
 */
export function priceToPips(priceDiff, symbol) {
  return priceDiff / getPipSize(symbol);
}

/**
 * Format price for display in reason strings.
 * @param {number} price
 * @param {string} symbol
 * @returns {string}
 */
export function formatPrice(price, symbol) {
  const decimals = symbol === 'XAUUSD' ? 2 : symbol === 'USDJPY' ? 3 : 5;
  return price.toFixed(decimals);
}
