/**
 * Statistics engine — computes and stores performance analytics.
 * @module statistics/StatisticsEngine
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { loadFromStorage, saveToStorage } from '../utils/dom.js';
import SimulationEngine from '../simulation/SimulationEngine.js';
import { computeStatistics } from './StatisticsCalculator.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('StatisticsEngine');

/**
 * @typedef {import('./StatisticsCalculator.js').PerformanceStats} PerformanceStats
 */

/**
 * @typedef {Object} StatisticsReport
 * @property {string} strategyId
 * @property {string} symbol
 * @property {string} timeframe
 * @property {PerformanceStats} stats
 * @property {number} computedAt
 */

/**
 * Main statistics service module.
 */
const StatisticsEngine = {
  /** @type {StatisticsReport|null} */
  #lastReport: null,

  /**
   * @param {{ bus: import('../core/EventBus.js').EventBus }} _ctx
   */
  async initialize(_ctx) {
    this.#lastReport = loadFromStorage(Config.STORAGE_KEYS.STATISTICS_RESULTS, null);
    bus.on(Events.SIMULATION_COMPLETE, (result) => {
      this.computeFromTrades(
        result.trades,
        result.strategyId,
        result.symbol,
        result.timeframe,
        SimulationEngine.getConfig().initialBalance
      );
    });
    log.info('Statistics engine ready');
  },

  /**
   * @returns {StatisticsReport|null}
   */
  getLastReport() {
    return this.#lastReport;
  },

  /**
   * Compute statistics from trade array.
   * @param {import('../simulation/TradeSimulator.js').TradeResult[]} trades
   * @param {string} strategyId
   * @param {string} symbol
   * @param {string} timeframe
   * @param {number} [initialBalance]
   * @returns {StatisticsReport}
   */
  computeFromTrades(trades, strategyId, symbol, timeframe, initialBalance) {
    const balance = initialBalance ?? SimulationEngine.getConfig().initialBalance;
    const stats = computeStatistics(trades, balance);

    const report = {
      strategyId,
      symbol,
      timeframe,
      stats,
      computedAt: Date.now(),
    };

    this.#lastReport = report;
    saveToStorage(Config.STORAGE_KEYS.STATISTICS_RESULTS, report);

    bus.emit(Events.STATISTICS_COMPUTED, report);
    bus.emit(Events.LOG_MESSAGE, {
      message: `Statistics: Expectancy $${stats.expectancy.toFixed(2)}, Max DD $${stats.maxDrawdown.toFixed(2)} (${stats.maxDrawdownPercent.toFixed(1)}%)`,
      level: 'info',
      time: new Date(),
    });

    log.info(`Computed stats for ${trades.length} trades`);
    return report;
  },

  /**
   * Recompute from last simulation result.
   * @returns {StatisticsReport|null}
   */
  refreshFromSimulation() {
    const sim = SimulationEngine.getLastResult();
    if (!sim) return null;

    return this.computeFromTrades(
      sim.trades,
      sim.strategyId,
      sim.symbol,
      sim.timeframe
    );
  },
};

export default StatisticsEngine;
