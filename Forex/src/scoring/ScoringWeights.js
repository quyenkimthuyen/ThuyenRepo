/**
 * Persisted AI scoring factor weights (override Config defaults).
 * @module scoring/ScoringWeights
 */

import { Config } from '../core/Config.js';
import { loadFromStorage, saveToStorage } from '../utils/dom.js';

/** @typedef {import('./SignalScoreEngine.js').ScoreFactors} ScoreFactors */

/**
 * @returns {Record<keyof ScoreFactors, number>}
 */
export function getDefaultScoringWeights() {
  return { ...Config.SCORING.WEIGHTS };
}

/**
 * @param {Record<string, number>} weights
 * @returns {Record<keyof ScoreFactors, number>}
 */
export function normalizeScoringWeights(weights) {
  const sum = Object.values(weights).reduce((s, v) => s + v, 0);
  /** @type {Record<string, number>} */
  const out = {};
  for (const [key, value] of Object.entries(weights)) {
    out[key] = value / (sum || 1);
  }
  return /** @type {Record<keyof ScoreFactors, number>} */ (out);
}

/**
 * @returns {Record<keyof ScoreFactors, number>}
 */
export function getScoringWeights() {
  const saved = loadFromStorage(Config.STORAGE_KEYS.SCORING_WEIGHTS, null);
  if (!saved || typeof saved !== 'object') return getDefaultScoringWeights();
  return normalizeScoringWeights({ ...getDefaultScoringWeights(), ...saved });
}

/**
 * @param {Record<string, number>} weights
 */
export function saveScoringWeights(weights) {
  saveToStorage(Config.STORAGE_KEYS.SCORING_WEIGHTS, normalizeScoringWeights(weights));
}

export function resetScoringWeights() {
  localStorage.removeItem(Config.STORAGE_KEYS.SCORING_WEIGHTS);
}
