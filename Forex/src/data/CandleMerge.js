/**
 * Candle merge, deduplication, and gap detection.
 * @module data/CandleMerge
 */

import { getTimeframeMs, nextCandleTime } from './TimeframeUtils.js';
import { normalizeCandle, sortCandles } from './Candle.js';

/**
 * @typedef {Object} GapInfo
 * @property {number} from - Last candle before the gap
 * @property {number} to - First candle after the gap
 * @property {number} missingCount - Number of missing candles
 */

/**
 * Merge new candles into existing data, deduplicating by timestamp.
 * Newer values overwrite older ones for the same timestamp.
 * @param {import('./Candle.js').Candle[]} existing
 * @param {import('./Candle.js').Candle[]} incoming
 * @returns {import('./Candle.js').Candle[]}
 */
export function mergeCandles(existing, incoming) {
  const map = new Map();

  for (const c of existing) {
    map.set(c.timestamp, c);
  }
  for (const c of incoming) {
    map.set(c.timestamp, c);
  }

  return sortCandles([...map.values()]);
}

/**
 * Detect missing candles between sorted data points.
 * @param {import('./Candle.js').Candle[]} candles - Sorted ascending
 * @param {string} timeframe
 * @returns {GapInfo[]}
 */
export function detectGaps(candles, timeframe) {
  if (candles.length < 2) return [];

  const interval = getTimeframeMs(timeframe);
  const gaps = [];

  for (let i = 0; i < candles.length - 1; i++) {
    const current = candles[i].timestamp;
    const next = candles[i + 1].timestamp;
    const expected = nextCandleTime(current, timeframe);

    if (next > expected) {
      const missingCount = Math.round((next - expected) / interval);
      gaps.push({ from: current, to: next, missingCount });
    }
  }

  return gaps;
}

/**
 * Parse and validate an array of raw candle objects.
 * @param {Record<string, unknown>[]} rawList
 * @returns {import('./Candle.js').Candle[]}
 */
export function parseCandleList(rawList) {
  const result = [];
  for (const raw of rawList) {
    const candle = normalizeCandle(raw);
    if (candle) result.push(candle);
  }
  return sortCandles(result);
}

/**
 * Compute metadata summary from a sorted candle array.
 * @param {import('./Candle.js').Candle[]} candles
 * @returns {{ count: number, firstTimestamp: number, lastTimestamp: number }}
 */
export function computeStats(candles) {
  if (candles.length === 0) {
    return { count: 0, firstTimestamp: 0, lastTimestamp: 0 };
  }
  return {
    count: candles.length,
    firstTimestamp: candles[0].timestamp,
    lastTimestamp: candles[candles.length - 1].timestamp,
  };
}
