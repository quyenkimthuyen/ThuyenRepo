/**
 * Compare multiple strategies on the same symbol/timeframe.
 * @module research/CompareEngine
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import DataManager from '../data/DataManager.js';
import StrategyEngine from '../strategy/StrategyEngine.js';
import SimulationEngine from '../simulation/SimulationEngine.js';
import { mergeTradeConfig } from '../simulation/TradeConfig.js';
import { simulateTrades, summarizeTrades } from '../simulation/TradeSimulator.js';
import { computeStatistics } from '../statistics/StatisticsCalculator.js';
import { registry } from '../plugin/PluginRegistry.js';
import { registerBuiltinStrategies } from '../strategies/index.js';
import { loadPersistedResult, savePersistedResult } from '../utils/resultsPersistence.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('CompareEngine');

/**
 * @typedef {Object} StrategyCompareRow
 * @property {string} strategyId
 * @property {string} strategyName
 * @property {number} signalCount
 * @property {import('../statistics/StatisticsCalculator.js').PerformanceStats} stats
 * @property {ReturnType<typeof summarizeTrades>} summary
 * @property {number} durationMs
 */

/**
 * @typedef {Object} StrategyCompareResult
 * @property {string} symbol
 * @property {string} timeframe
 * @property {StrategyCompareRow[]} rows
 * @property {number} comparedAt
 */

class CompareEngineImpl {
  /** @type {StrategyCompareResult|null} */
  #lastResult = null;

  async initialize() {
    this.#lastResult = /** @type {StrategyCompareResult|null} */ (
      await loadPersistedResult(Config.STORAGE_KEYS.STRATEGY_COMPARE, null)
    );
    log.info('Compare engine ready');
  }

  /**
   * @returns {StrategyCompareResult|null}
   */
  getLastResult() {
    return this.#lastResult;
  }

  /**
   * @param {string[]} strategyIds
   * @param {string} symbol
   * @param {string} timeframe
   * @returns {Promise<StrategyCompareResult>}
   */
  async compare(strategyIds, symbol, timeframe) {
    registerBuiltinStrategies();
    const candles = await DataManager.getCandles(symbol, timeframe);
    if (candles.length === 0) {
      throw new Error(`No candle data for ${symbol} ${timeframe}`);
    }

    const tradeConfig = mergeTradeConfig(SimulationEngine.getConfig());
    /** @type {StrategyCompareRow[]} */
    const rows = [];

    for (const strategyId of strategyIds) {
      const scan = await StrategyEngine.runStrategy(strategyId, symbol, timeframe, undefined, {
        emitSignals: false,
      });
      const trades = simulateTrades(scan.signals, candles, tradeConfig);
      const stats = computeStatistics(trades, tradeConfig.initialBalance);
      const plugin = registry.get(strategyId);

      rows.push({
        strategyId,
        strategyName: plugin?.name ?? strategyId,
        signalCount: scan.signals.length,
        stats,
        summary: summarizeTrades(trades, tradeConfig.initialBalance),
        durationMs: scan.durationMs,
      });
    }

    rows.sort((a, b) => b.stats.expectancy - a.stats.expectancy);

    const result = {
      symbol,
      timeframe,
      rows,
      comparedAt: Date.now(),
    };

    this.#lastResult = result;
    await savePersistedResult(Config.STORAGE_KEYS.STRATEGY_COMPARE, result);

    bus.emit(Events.STRATEGY_COMPARE_COMPLETE, result);
    bus.emit(Events.LOG_MESSAGE, {
      message: `Strategy compare: ${rows.length} setups on ${symbol} ${timeframe} — best ${rows[0]?.strategyName ?? '—'} (Exp $${rows[0]?.stats.expectancy.toFixed(2) ?? '0'})`,
      level: 'info',
      time: new Date(),
    });

    log.info(`Compared ${rows.length} strategies`);
    return result;
  }
}

export default new CompareEngineImpl();
