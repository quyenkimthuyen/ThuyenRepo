/**
 * Confidence score calculator per STRATEGY_SPECIFICATION.md §2.8.
 * @module strategy/helpers/ConfidenceScore
 */

import { getSession } from '../../chart/SessionUtils.js';

/**
 * @typedef {Object} ConfidenceFactors
 * @property {boolean} [trendAlignment]
 * @property {boolean} [momentum]
 * @property {boolean} [rrGte2]
 * @property {boolean} [preciseLocation]
 * @property {boolean} [qualityWick]
 * @property {number} [extraPoints]
 */

/**
 * Compute confidence score capped at 100.
 * @param {number} timestamp
 * @param {number} rr
 * @param {ConfidenceFactors} factors
 * @returns {number}
 */
export function computeConfidence(timestamp, rr, factors = {}) {
  let score = 25;

  if (factors.trendAlignment) score += 15;

  const session = getSession(timestamp);
  if (session === 'London' || session === 'New York') score += 10;

  if (factors.momentum) score += 10;
  if (rr >= 2 || factors.rrGte2) score += 10;
  if (factors.preciseLocation) score += 15;
  if (factors.qualityWick) score += 15;
  if (factors.extraPoints) score += factors.extraPoints;

  return Math.min(100, score);
}
