/**
 * Simulation orchestrator — connects strategies, signals, and trade engine.
 * @module simulation/SimulationEngine
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { loadFromStorage, saveToStorage } from '../utils/dom.js';
import DataManager from '../data/DataManager.js';
import StrategyEngine from '../strategy/StrategyEngine.js';
import { getDefaultTradeConfig, mergeTradeConfig } from './TradeConfig.js';
import { simulateTrades, summarizeTrades } from './TradeSimulator.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('SimulationEngine');

/**
 * @typedef {import('./TradeConfig.js').TradeConfig} TradeConfig
 * @typedef {import('./TradeSimulator.js').TradeResult} TradeResult
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
 */

/**
 * Main simulation service module.
 */
const SimulationEngine = {
  /** @type {TradeConfig} */
  #config: getDefaultTradeConfig(),

  /** @type {SimulationResult|null} */
  #lastResult: null,

  /**
   * @param {{ bus: import('../core/EventBus.js').EventBus }} _ctx
   */
  async initialize(_ctx) {
    this.#config = loadFromStorage(
      Config.STORAGE_KEYS.SIMULATION_CONFIG,
      getDefaultTradeConfig()
    );
    log.info('Simulation engine ready');
  },

  /**
   * @returns {TradeConfig}
   */
  getConfig() {
    return { ...this.#config };
  },

  /**
   * @param {Partial<TradeConfig>} partial
   */
  setConfig(partial) {
    this.#config = mergeTradeConfig({ ...this.#config, ...partial });
    saveToStorage(Config.STORAGE_KEYS.SIMULATION_CONFIG, this.#config);
  },

  /**
   * @returns {SimulationResult|null}
   */
  getLastResult() {
    return this.#lastResult;
  },

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

    const scan = await StrategyEngine.runStrategy(strategyId, symbol, timeframe);
    const candles = await DataManager.getCandles(symbol, timeframe);
    const trades = simulateTrades(scan.signals, candles, config);
    const summary = summarizeTrades(trades, config.initialBalance);

    const result = {
      strategyId,
      symbol,
      timeframe,
      trades,
      summary,
      signalCount: scan.signals.length,
      durationMs: Math.round(performance.now() - start),
    };

    this.#lastResult = result;
    saveToStorage(Config.STORAGE_KEYS.SIMULATION_RESULTS, result);

    bus.emit(Events.SIMULATION_RUN, result);
    bus.emit(Events.SIMULATION_COMPLETE, result);
    bus.emit(Events.LOG_MESSAGE, {
      message: `Simulation: ${trades.length} trades, WR ${summary.winRate.toFixed(1)}%, Net $${summary.netProfit.toFixed(2)}`,
      level: 'info',
      time: new Date(),
    });

    log.info(`Mode 1 complete: ${trades.length} trades`);
    return result;
  },

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
    };

    this.#lastResult = result;
    bus.emit(Events.SIMULATION_COMPLETE, result);
    return result;
  },
};

export default SimulationEngine;
