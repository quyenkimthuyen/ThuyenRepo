/**
 * Candle data model, validation, and normalization.
 * @module data/Candle
 */

/**
 * @typedef {Object} Candle
 * @property {number} timestamp - Unix epoch milliseconds (candle open time)
 * @property {number} open
 * @property {number} high
 * @property {number} low
 * @property {number} close
 * @property {number} volume
 */

/**
 * @typedef {Object} StoredCandle
 * @property {string} symbol
 * @property {string} timeframe
 * @property {number} timestamp
 * @property {number} open
 * @property {number} high
 * @property {number} low
 * @property {number} close
 * @property {number} volume
 */

/**
 * @typedef {Object} DatasetMetadata
 * @property {string} key - `${symbol}|${timeframe}`
 * @property {string} symbol
 * @property {string} timeframe
 * @property {number} count
 * @property {number} firstTimestamp
 * @property {number} lastTimestamp
 * @property {number} lastUpdated
 */

/**
 * Build a metadata cache key from symbol and timeframe.
 * @param {string} symbol
 * @param {string} timeframe
 * @returns {string}
 */
export function datasetKey(symbol, timeframe) {
  return `${symbol}|${timeframe}`;
}

/**
 * Validate a raw candle object.
 * @param {Partial<Candle>} raw
 * @returns {boolean}
 */
export function isValidCandle(raw) {
  if (!raw || typeof raw.timestamp !== 'number') return false;
  const { open, high, low, close, volume } = raw;
  if ([open, high, low, close].some((v) => typeof v !== 'number' || Number.isNaN(v))) {
    return false;
  }
  if (high < Math.max(open, close) || low > Math.min(open, close)) return false;
  if (low > high) return false;
  if (typeof volume !== 'number' || volume < 0) return false;
  return true;
}

/**
 * Normalize a raw candle into a validated Candle or null.
 * @param {Record<string, unknown>} raw
 * @returns {Candle|null}
 */
export function normalizeCandle(raw) {
  const candle = {
    timestamp: Number(raw.timestamp ?? raw.time ?? raw.t ?? raw.date),
    open: Number(raw.open ?? raw.o),
    high: Number(raw.high ?? raw.h),
    low: Number(raw.low ?? raw.l),
    close: Number(raw.close ?? raw.c),
    volume: Number(raw.volume ?? raw.v ?? 0),
  };

  if (!Number.isFinite(candle.timestamp)) return null;
  return isValidCandle(candle) ? candle : null;
}

/**
 * Attach symbol and timeframe to a candle for IndexedDB storage.
 * @param {string} symbol
 * @param {string} timeframe
 * @param {Candle} candle
 * @returns {StoredCandle}
 */
export function toStoredCandle(symbol, timeframe, candle) {
  return { symbol, timeframe, ...candle };
}

/**
 * Sort candles ascending by timestamp (in-place).
 * @param {Candle[]} candles
 * @returns {Candle[]}
 */
export function sortCandles(candles) {
  return candles.sort((a, b) => a.timestamp - b.timestamp);
}
