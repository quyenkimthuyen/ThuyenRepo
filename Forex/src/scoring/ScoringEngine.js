/**
 * Scoring service — auto-scores signals after strategy scans.
 * @module scoring/ScoringEngine
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { loadFromStorage, saveToStorage } from '../utils/dom.js';
import DataManager from '../data/DataManager.js';
import SimulationEngine from '../simulation/SimulationEngine.js';
import PerformanceEngine from '../performance/PerformanceEngine.js';
import { scoreSignalsBatch, filterByMinScore } from './SignalScoreEngine.js';
import {
  buildCalibrationReport,
  suggestWeightsFromSimulation,
} from './ScoreCalibration.js';
import {
  getScoringWeights,
  saveScoringWeights,
  resetScoringWeights,
  getDefaultScoringWeights,
} from './ScoringWeights.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('ScoringEngine');

/**
 * @typedef {import('./SignalScoreEngine.js').ScoredSignal} ScoredSignal
 */

/**
 * @typedef {Object} ScoredSignalSet
 * @property {string} strategyId
 * @property {string} symbol
 * @property {string} timeframe
 * @property {ScoredSignal[]} signals
 * @property {number} avgScore
 * @property {number} scoredAt
 */

/**
 * Main AI scoring service module.
 */
class ScoringEngine {
  /** @type {ScoredSignalSet|null} */
  #lastScored = null;

  /** @type {boolean} */
  #listenerReady = false;

  /**
   * @param {{ bus: import('../core/EventBus.js').EventBus }} _ctx
   */
  async initialize(_ctx) {
    this.#lastScored = loadFromStorage(Config.STORAGE_KEYS.SCORED_SIGNALS, null);

    if (!this.#listenerReady) {
      this.#listenerReady = true;
      bus.on(Events.SIGNALS_GENERATED, async (result) => {
        await this.scoreFromScan(result.strategyId, result.symbol, result.timeframe, result.signals);
      });
    }

    log.info('Scoring engine ready');
  }

  /**
   * @returns {ScoredSignalSet|null}
   */
  getLastScored() {
    return this.#lastScored;
  }

  /**
   * Score signals from a strategy scan result.
   * @param {string} strategyId
   * @param {string} symbol
   * @param {string} timeframe
   * @param {import('../strategy/Signal.js').Signal[]} signals
   * @returns {Promise<ScoredSignalSet>}
   */
  async scoreFromScan(strategyId, symbol, timeframe, signals) {
    const candles = await DataManager.getCandles(symbol, timeframe);
    const spread = SimulationEngine.getConfig().spreadPips;

    const scored = candles.length >= Config.PERFORMANCE.WORKER_THRESHOLD
      ? await PerformanceEngine.scoreBatch(signals, candles, spread)
      : scoreSignalsBatch(signals, candles, spread);

    const avgScore = scored.length
      ? scored.reduce((s, sig) => s + (sig.scoreBreakdown?.score ?? 0), 0) / scored.length
      : 0;

    const set = {
      strategyId,
      symbol,
      timeframe,
      signals: scored,
      avgScore,
      scoredAt: Date.now(),
    };

    this.#lastScored = set;
    saveToStorage(Config.STORAGE_KEYS.SCORED_SIGNALS, set);

    bus.emit(Events.SIGNALS_SCORED, set);
    bus.emit(Events.LOG_MESSAGE, {
      message: `AI scored ${scored.length} signals — avg ${avgScore.toFixed(0)}/100`,
      level: 'info',
      time: new Date(),
    });

    log.info(`Scored ${scored.length} signals for ${strategyId}`);
    return set;
  }

  /**
   * Get signals meeting minimum AI score threshold.
   * @param {number} minScore
   * @returns {ScoredSignal[]}
   */
  getFilteredSignals(minScore) {
    if (!this.#lastScored) return [];
    return filterByMinScore(this.#lastScored.signals, minScore);
  }

  /**
   * @returns {Record<string, number>}
   */
  getWeights() {
    return getScoringWeights();
  }

  /**
   * @param {import('../simulation/SimulationEngine.js').SimulationResult|null} simResult
   * @param {number} [minScoreCutoff]
   */
  getCalibrationReport(simResult, minScoreCutoff = 65) {
    return buildCalibrationReport(this.#lastScored, simResult, minScoreCutoff);
  }

  /**
   * @param {import('../simulation/SimulationEngine.js').SimulationResult} simResult
   */
  suggestWeights(simResult) {
    if (!this.#lastScored) {
      return {
        weights: getDefaultScoringWeights(),
        fitness: 0,
        baselineFitness: 0,
        note: 'Chưa có signal đã chấm — scan Strategies trước.',
      };
    }
    return suggestWeightsFromSimulation(this.#lastScored, simResult, getScoringWeights());
  }

  /**
   * @param {Record<string, number>} weights
   */
  async applyWeights(weights) {
    saveScoringWeights(weights);
    if (!this.#lastScored) return null;
    const candles = await DataManager.getCandles(
      this.#lastScored.symbol,
      this.#lastScored.timeframe
    );
    const spread = SimulationEngine.getConfig().spreadPips;
    const rescored = scoreSignalsBatch(
      this.#lastScored.signals.map(({ scoreBreakdown, confidence, ...base }) => base),
      candles,
      spread
    );
    const set = {
      ...this.#lastScored,
      signals: rescored,
      avgScore: rescored.length
        ? rescored.reduce((s, sig) => s + (sig.scoreBreakdown?.score ?? 0), 0) / rescored.length
        : 0,
      scoredAt: Date.now(),
    };
    this.#lastScored = set;
    saveToStorage(Config.STORAGE_KEYS.SCORED_SIGNALS, set);
    bus.emit(Events.SIGNALS_SCORED, set);
    bus.emit(Events.LOG_MESSAGE, {
      message: `Đã áp trọng số AI mới — avg ${set.avgScore.toFixed(0)}/100`,
      level: 'info',
      time: new Date(),
    });
    return set;
  }

  async resetWeights() {
    resetScoringWeights();
    if (!this.#lastScored) return null;
    return this.applyWeights(getDefaultScoringWeights());
  }
}

export default new ScoringEngine();
