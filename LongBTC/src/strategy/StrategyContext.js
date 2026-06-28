/**
 * Execution context passed to strategy plugins during a scan.
 * @module strategy/StrategyContext
 */

/**
 * @typedef {Object} StrategyContext
 * @property {string} symbol
 * @property {string} timeframe
 * @property {import('../data/Candle.js').Candle[]} candles - Full candle array (read-only)
 * @property {number} index - Current bar index (inclusive, no lookahead)
 * @property {Record<string, unknown>} params - Strategy parameters
 */

/**
 * Create a frozen strategy context for a specific bar.
 * @param {string} symbol
 * @param {string} timeframe
 * @param {import('../data/Candle.js').Candle[]} candles
 * @param {number} index
 * @param {Record<string, unknown>} params
 * @returns {StrategyContext}
 */
export function createContext(symbol, timeframe, candles, index, params) {
  return Object.freeze({
    symbol,
    timeframe,
    candles,
    index,
    params,
  });
}

/**
 * Get visible candles up to and including the current index.
 * @param {StrategyContext} ctx
 * @returns {import('../data/Candle.js').Candle[]}
 */
export function getVisibleCandles(ctx) {
  return ctx.candles.slice(0, ctx.index + 1);
}

/**
 * Get the current candle at the context index.
 * @param {StrategyContext} ctx
 * @returns {import('../data/Candle.js').Candle|undefined}
 */
export function getCurrentCandle(ctx) {
  return ctx.candles[ctx.index];
}
