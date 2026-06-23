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
 * @param {{ forexMarket?: boolean }} [options] - Skip expected forex weekend/holiday gaps
 * @returns {GapInfo[]}
 */
export function detectGaps(candles, timeframe, options = {}) {
  if (candles.length < 2) return [];

  const interval = getTimeframeMs(timeframe);
  const gaps = [];

  for (let i = 0; i < candles.length - 1; i++) {
    const current = candles[i].timestamp;
    const next = candles[i + 1].timestamp;
    const expected = nextCandleTime(current, timeframe);

    if (next > expected) {
      const missingCount = Math.round((next - expected) / interval);
      const gap = { from: current, to: next, missingCount };
      if (options.forexMarket && isExpectedForexGap(current, next, timeframe)) {
        continue;
      }
      gaps.push(gap);
    }
  }

  return gaps;
}

const MS_HOUR = 60 * 60 * 1000;

/**
 * Weekend / holiday closures are normal for spot forex — not data errors.
 * @param {number} fromTs
 * @param {number} toTs
 * @param {string} timeframe
 * @returns {boolean}
 */
export function isExpectedForexGap(fromTs, toTs, timeframe) {
  if (!['H1', 'H4'].includes(timeframe)) return false;

  const gapMs = toTs - fromTs;
  const gapHours = gapMs / MS_HOUR;

  // Fri close → Sun/Mon open (~47–56h for H1)
  if (gapHours >= 47 && gapHours <= 56) return true;

  // Christmas / Boxing Day shortened sessions (~14–16h)
  if (gapHours >= 14 && gapHours <= 16) {
    const from = new Date(fromTs);
    const month = from.getUTCMonth();
    const day = from.getUTCDate();
    if (month === 11 && (day === 24 || day === 25 || day === 26)) return true;
  }

  // New Year (~24–26h)
  if (gapHours >= 24 && gapHours <= 26) {
    const from = new Date(fromTs);
    const month = from.getUTCMonth();
    const day = from.getUTCDate();
    if ((month === 11 && day === 31) || (month === 0 && day === 1)) return true;
  }

  return false;
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
