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
