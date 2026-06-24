/**
 * Simulation orchestrator — connects strategies, signals, and trade engine.
 * @module simulation/SimulationEngine
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { loadFromStorage, saveToStorage } from '../utils/dom.js';
import { loadPersistedResult, savePersistedResult } from '../utils/resultsPersistence.js';
import DataManager from '../data/DataManager.js';
import StrategyEngine from '../strategy/StrategyEngine.js';
import { scoreSignalsBatch, filterByMinScore } from '../scoring/SignalScoreEngine.js';
import { getDefaultTradeConfig, mergeTradeConfig } from './TradeConfig.js';
import { simulateTrades, summarizeTrades } from './TradeSimulator.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('SimulationEngine');

/**
 * @typedef {import('./TradeConfig.js').TradeConfig} TradeConfig
 * @typedef {import('./TradeSimulator.js').TradeResult} TradeResult
 */

/**
 * @typedef {Object} SimulationRunContext
 * @property {string} strategyId
 * @property {string} symbol
 * @property {string} timeframe
 * @property {import('./TradeConfig.js').TradeConfig} config
 */

/**
 * @typedef {Object} AiFilterComparison
 * @property {number} minScore
 * @property {number} baselineSignalCount
 * @property {number} filteredSignalCount
 * @property {ReturnType<typeof summarizeTrades>} baselineSummary
 * @property {ReturnType<typeof summarizeTrades>} filteredSummary
 */

/**
 * @typedef {Object} SimulationResult
 * @property {string} strategyId
 * @property {string} symbol
 * @property {string} timeframe
 * @property {TradeResult[]} trades
 * @property {Object} summary
 * @property {number} signalCount
 * @property {number} durationMs
 * @property {SimulationRunContext} [runContext]
 * @property {AiFilterComparison|null} [aiComparison]
 */

/**
 * Main simulation service module.
 */
class SimulationEngine {
  /** @type {TradeConfig} */
  #config = getDefaultTradeConfig();

  /** @type {SimulationResult|null} */
  #lastResult = null;

  /**
   * @param {{ bus: import('../core/EventBus.js').EventBus }} _ctx
   */
  async initialize(_ctx) {
    this.#config = loadFromStorage(
      Config.STORAGE_KEYS.SIMULATION_CONFIG,
      getDefaultTradeConfig()
    );
    const saved = await loadPersistedResult(Config.STORAGE_KEYS.SIMULATION_RESULTS, null);
    if (saved && Array.isArray(saved.trades)) {
      this.#lastResult = saved;
    }
    log.info('Simulation engine ready');
  }

  /**
   * @returns {TradeConfig}
   */
  getConfig() {
    return { ...this.#config };
  }

  /**
   * @param {Partial<TradeConfig>} partial
   */
  setConfig(partial) {
    this.#config = mergeTradeConfig({ ...this.#config, ...partial });
    saveToStorage(Config.STORAGE_KEYS.SIMULATION_CONFIG, this.#config);
  }

  /**
   * @returns {SimulationResult|null}
   */
  getLastResult() {
    return this.#lastResult;
  }

  /**
   * Mode 1: One setup, one pair — run strategy scan then simulate trades.
   * @param {string} strategyId
   * @param {string} symbol
   * @param {string} timeframe
   * @param {Partial<TradeConfig>} [configOverride]
   * @returns {Promise<SimulationResult>}
   */
  async runMode1(strategyId, symbol, timeframe, configOverride) {
    const start = performance.now();
    const config = mergeTradeConfig({ ...this.#config, ...configOverride });

    const scan = await StrategyEngine.runStrategy(strategyId, symbol, timeframe, undefined, {
      emitSignals: false,
    });
    const candles = await DataManager.getCandles(symbol, timeframe);

    const minScore = config.minAiScore ?? 0;
    /** @type {import('../strategy/Signal.js').Signal[]} */
    let signalsToTrade = scan.signals;
    /** @type {AiFilterComparison|null} */
    let aiComparison = null;

    if (minScore > 0) {
      const scored = scoreSignalsBatch(scan.signals, candles, config.spreadPips);
      const filtered = filterByMinScore(scored, minScore);
      const filteredIds = new Set(filtered.map((s) => s.id));
      const filteredSignals = scan.signals.filter((s) => filteredIds.has(s.id));

      if (config.compareAiFilter) {
        const baselineTrades = simulateTrades(scan.signals, candles, config);
        const filteredTrades = simulateTrades(filteredSignals, candles, config);
        aiComparison = {
          minScore,
          baselineSignalCount: scan.signals.length,
          filteredSignalCount: filteredSignals.length,
          baselineSummary: summarizeTrades(baselineTrades, config.initialBalance),
          filteredSummary: summarizeTrades(filteredTrades, config.initialBalance),
        };
      }

      signalsToTrade = filteredSignals;
    }

    const trades = simulateTrades(signalsToTrade, candles, config);
    const summary = summarizeTrades(trades, config.initialBalance);

    const result = {
      strategyId,
      symbol,
      timeframe,
      trades,
      summary,
      signalCount: signalsToTrade.length,
      durationMs: Math.round(performance.now() - start),
      runContext: { strategyId, symbol, timeframe, config: { ...config } },
      aiComparison,
    };

    this.#lastResult = result;
    await savePersistedResult(Config.STORAGE_KEYS.SIMULATION_RESULTS, result);

    bus.emit(Events.SIMULATION_RUN, result);
    bus.emit(Events.SIMULATION_COMPLETE, result);
    bus.emit(Events.SIGNALS_GENERATED, {
      strategyId: scan.strategyId,
      symbol: scan.symbol,
      timeframe: scan.timeframe,
      signals: scan.signals,
      barsScanned: scan.barsScanned,
      durationMs: scan.durationMs,
    });

    let logMsg = `Simulation: ${trades.length} trades, WR ${summary.winRate.toFixed(1)}%, Net $${summary.netProfit.toFixed(2)}`;
    if (aiComparison) {
      logMsg += ` (AI ≥${minScore}: ${aiComparison.filteredSignalCount}/${aiComparison.baselineSignalCount} signals)`;
    } else if (minScore > 0) {
      logMsg += ` (AI filter ≥${minScore})`;
    }

    bus.emit(Events.LOG_MESSAGE, {
      message: logMsg,
      level: 'info',
      time: new Date(),
    });

    log.info(`Mode 1 complete: ${trades.length} trades`);
    return result;
  }

  /**
   * Simulate from existing signals without re-scanning.
   * @param {import('../strategy/Signal.js').Signal[]} signals
   * @param {string} symbol
   * @param {string} timeframe
   * @param {string} strategyId
   * @returns {Promise<SimulationResult>}
   */
  async simulateSignals(signals, symbol, timeframe, strategyId) {
    const start = performance.now();
    const candles = await DataManager.getCandles(symbol, timeframe);
    const trades = simulateTrades(signals, candles, this.#config);
    const summary = summarizeTrades(trades, this.#config.initialBalance);

    const result = {
      strategyId,
      symbol,
      timeframe,
      trades,
      summary,
      signalCount: signals.length,
      durationMs: Math.round(performance.now() - start),
      runContext: {
        strategyId,
        symbol,
        timeframe,
        config: { ...this.#config },
      },
      aiComparison: null,
    };

    this.#lastResult = result;
    await savePersistedResult(Config.STORAGE_KEYS.SIMULATION_RESULTS, result);
    bus.emit(Events.SIMULATION_COMPLETE, result);
    return result;
  }
}

export default new SimulationEngine();
