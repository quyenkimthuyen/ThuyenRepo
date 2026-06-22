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

  /**
   * @param {{ bus: import('../core/EventBus.js').EventBus }} _ctx
   */
  async initialize(_ctx) {
    this.#lastScored = loadFromStorage(Config.STORAGE_KEYS.SCORED_SIGNALS, null);

    bus.on(Events.SIGNALS_GENERATED, async (result) => {
      await this.scoreFromScan(result.strategyId, result.symbol, result.timeframe, result.signals);
    });

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
}

export default new ScoringEngine();
