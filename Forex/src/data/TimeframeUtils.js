/**
 * Timeframe interval utilities.
 * @module data/TimeframeUtils
 */

import { Config } from '../core/Config.js';

const MS_DAY = 24 * 60 * 60 * 1000;
const MS_WEEK = 7 * MS_DAY;

/**
 * Get interval in milliseconds for a timeframe string.
 * @param {string} timeframe
 * @returns {number}
 */
export function getTimeframeMs(timeframe) {
  const ms = Config.TIMEFRAME_MS[timeframe];
  if (!ms) {
    throw new Error(`Unsupported timeframe: ${timeframe}`);
  }
  return ms;
}

/**
 * UTC midnight for a timestamp.
 * @param {number} timestamp
 * @returns {number}
 */
function startOfUtcDay(timestamp) {
  const d = new Date(timestamp);
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
}

/**
 * Monday 00:00 UTC for the week containing timestamp (Dukascopy convention).
 * @param {number} timestamp
 * @returns {number}
 */
function startOfUtcWeek(timestamp) {
  const d = new Date(timestamp);
  const daysFromMonday = (d.getUTCDay() + 6) % 7;
  return startOfUtcDay(timestamp) - daysFromMonday * MS_DAY;
}

/**
 * Align a timestamp down to the nearest candle open for a timeframe.
 * @param {number} timestamp
 * @param {string} timeframe
 * @returns {number}
 */
export function alignToTimeframe(timestamp, timeframe) {
  switch (timeframe) {
    case 'D1':
      return startOfUtcDay(timestamp);
    case 'W':
      return startOfUtcWeek(timestamp);
    default: {
      const interval = getTimeframeMs(timeframe);
      return Math.floor(timestamp / interval) * interval;
    }
  }
}

/**
 * Compute the next expected candle open time.
 * @param {number} timestamp - Current candle open time
 * @param {string} timeframe
 * @returns {number}
 */
export function nextCandleTime(timestamp, timeframe) {
  switch (timeframe) {
    case 'D1':
      return timestamp + MS_DAY;
    case 'W':
      return timestamp + MS_WEEK;
    default:
      return timestamp + getTimeframeMs(timeframe);
  }
}

/**
 * Format a timestamp for display in the UI.
 * @param {number} timestamp
 * @returns {string}
 */
export function formatTimestamp(timestamp) {
  return new Date(timestamp).toISOString().replace('T', ' ').slice(0, 16);
}

/**
 * Value for `<input type="datetime-local">` — UTC fields (matches candle timestamps).
 * @param {number} timestamp
 * @returns {string}
 */
export function timestampToDatetimeLocalValue(timestamp) {
  return new Date(timestamp).toISOString().slice(0, 16);
}

/**
 * Parse datetime-local input as UTC (app candles use UTC epoch ms).
 * @param {string} value - `YYYY-MM-DDTHH:mm`
 * @returns {number} Epoch ms, or NaN if invalid
 */
export function parseDatetimeLocalAsUtc(value) {
  const match = value?.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  if (!match) return NaN;
  const year = Number(match[1]);
  const month = Number(match[2]) - 1;
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  return Date.UTC(year, month, day, hour, minute, 0, 0);
}

/**
 * @param {{ timestamp: number }[]} candles
 * @param {number} timestamp
 * @returns {number}
 */
export function findCandleIndexAtOrBefore(candles, timestamp) {
  if (candles.length === 0) return 0;
  if (timestamp <= candles[0].timestamp) return 0;

  const last = candles.length - 1;
  if (timestamp >= candles[last].timestamp) return last;

  let lo = 0;
  let hi = last;
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    if (candles[mid].timestamp <= timestamp) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

/**
 * Nearest candle open to a timestamp (ties prefer the earlier bar).
 * @param {{ timestamp: number }[]} candles
 * @param {number} timestamp
 * @returns {number}
 */
export function findNearestCandleIndex(candles, timestamp) {
  if (candles.length === 0) return 0;
  if (timestamp <= candles[0].timestamp) return 0;

  const last = candles.length - 1;
  if (timestamp >= candles[last].timestamp) return last;

  const floorIdx = findCandleIndexAtOrBefore(candles, timestamp);
  const ceilIdx = Math.min(floorIdx + 1, last);
  const floorDist = timestamp - candles[floorIdx].timestamp;
  const ceilDist = candles[ceilIdx].timestamp - timestamp;
  return ceilDist < floorDist ? ceilIdx : floorIdx;
}
