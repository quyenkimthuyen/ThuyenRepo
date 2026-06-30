/**
 * Dataset age / staleness helpers for BTC OHLCV.
 * @module analysis/DataFreshness
 */

import { getTimeframeMs } from '../data/TimeframeUtils.js';

/** @typedef {'fresh'|'stale'|'old'|'empty'} FreshnessLevel */

/**
 * @param {number} lastTimestampMs - Last candle open time
 * @param {string} [timeframe='W']
 * @param {number} [now=Date.now()]
 * @returns {number} Age in milliseconds
 */
export function dataAgeMs(lastTimestampMs, timeframe = 'W', now = Date.now()) {
  if (!lastTimestampMs || lastTimestampMs <= 0) return Infinity;
  return Math.max(0, now - lastTimestampMs);
}

/**
 * @param {number} ageMs
 * @param {string} timeframe
 * @returns {FreshnessLevel}
 */
export function freshnessLevel(ageMs, timeframe) {
  if (!Number.isFinite(ageMs) || ageMs === Infinity) return 'empty';
  const bar = getTimeframeMs(timeframe);
  if (ageMs <= bar * 1.5) return 'fresh';
  if (ageMs <= bar * 4) return 'stale';
  return 'old';
}

/**
 * Human-readable age (Vietnamese).
 * @param {number} ageMs
 * @returns {string}
 */
export function formatDataAgeVi(ageMs) {
  if (!Number.isFinite(ageMs) || ageMs === Infinity) return 'Kh\u00f4ng c\u00f3 d\u1eef li\u1ec7u';

  const min = Math.floor(ageMs / 60000);
  if (min < 90) return `${min} ph\u00fat tr\u01b0\u1edbc`;

  const hours = Math.floor(ageMs / 3600000);
  if (hours < 36) return `${hours} gi\u1edd tr\u01b0\u1edbc`;

  const days = Math.floor(ageMs / 86400000);
  if (days < 14) return `${days} ng\u00e0y tr\u01b0\u1edbc`;

  const weeks = Math.floor(days / 7);
  if (weeks < 8) return `${weeks} tu\u1ea7n tr\u01b0\u1edbc`;

  const months = Math.floor(days / 30);
  return `${months} th\u00e1ng tr\u01b0\u1edbc`;
}

/**
 * @param {number} lastTimestampMs
 * @param {string} timeframe
 * @param {number} [now]
 * @returns {{ ageMs: number, level: FreshnessLevel, labelVi: string, warn: boolean }}
 */
export function describeDataFreshness(lastTimestampMs, timeframe, now = Date.now()) {
  const ageMs = dataAgeMs(lastTimestampMs, timeframe, now);
  const level = freshnessLevel(ageMs, timeframe);
  const labelVi = formatDataAgeVi(ageMs);
  return {
    ageMs,
    level,
    labelVi,
    warn: level === 'stale' || level === 'old' || level === 'empty',
  };
}

/**
 * @param {import('../data/Candle.js').DatasetMetadata|undefined|null} meta
 * @param {number} [now]
 * @returns {ReturnType<typeof describeDataFreshness>|null}
 */
export function freshnessFromMetadata(meta, now = Date.now()) {
  if (!meta?.lastTimestamp) return null;
  return describeDataFreshness(meta.lastTimestamp, meta.timeframe, now);
}
