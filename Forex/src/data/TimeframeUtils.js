/**
 * Timeframe interval utilities.
 * @module data/TimeframeUtils
 */

import { Config } from '../core/Config.js';

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
 * Align a timestamp down to the nearest candle open for a timeframe.
 * @param {number} timestamp
 * @param {string} timeframe
 * @returns {number}
 */
export function alignToTimeframe(timestamp, timeframe) {
  const interval = getTimeframeMs(timeframe);
  return Math.floor(timestamp / interval) * interval;
}

/**
 * Compute the next expected candle open time.
 * @param {number} timestamp - Current candle open time
 * @param {string} timeframe
 * @returns {number}
 */
export function nextCandleTime(timestamp, timeframe) {
  return timestamp + getTimeframeMs(timeframe);
}

/**
 * Format a timestamp for display in the UI.
 * @param {number} timestamp
 * @returns {string}
 */
export function formatTimestamp(timestamp) {
  return new Date(timestamp).toISOString().replace('T', ' ').slice(0, 16);
}
