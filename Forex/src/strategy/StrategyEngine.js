/**
 * Strategy execution engine — runs plugins bar-by-bar without lookahead.
 * @module strategy/StrategyEngine
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { registry } from '../plugin/PluginRegistry.js';
import { createContext } from './StrategyContext.js';
import { loadFromStorage, saveToStorage } from '../utils/dom.js';
import DataManager from '../data/DataManager.js';
import { createLogger } from '../utils/logger.js';
import { registerBuiltinStrategies } from '../strategies/index.js';

const log = createLogger('StrategyEngine');

/**
 * @typedef {Object} StrategyConfig
 * @property {boolean} enabled
 * @property {Record<string, unknown>} params
 */

/**
 * @typedef {Object} ScanResult
 * @property {string} strategyId
 * @property {string} symbol
 * @property {string} timeframe
 * @property {import('./Signal.js').Signal[]} signals
 * @property {number} barsScanned
 * @property {number} durationMs
 */

/**
 * Main strategy engine module.
 */
const StrategyEngine = {
  /** @type {Record<string, StrategyConfig>} */
  #configs: {},

  /** @type {Record<string, ScanResult>} */
  #lastResults: {},

  /**
   * @param {{ bus: import('../core/EventBus.js').EventBus }} _ctx
   */
  async initialize(_ctx) {
    registerBuiltinStrategies();
    this.#configs = loadFromStorage(Config.STORAGE_KEYS.STRATEGIES, {});
    this.#lastResults = loadFromStorage(Config.STORAGE_KEYS.STRATEGY_RESULTS, {});
    this.#ensureDefaults();
    log.info(`Strategy engine ready — ${registry.size} plugins loaded`);
  },

  /**
   * @returns {import('../plugin/PluginRegistry.js').PluginDescriptor[]}
   */
  listPlugins() {
    return registry.getAll();
  },

  /**
   * @param {string} strategyId
   * @returns {StrategyConfig}
   */
  getConfig(strategyId) {
    return this.#configs[strategyId] ?? { enabled: true, params: {} };
  },

  /**
   * @param {string} strategyId
   * @param {Partial<StrategyConfig>} config
   */
  setConfig(strategyId, config) {
    this.#configs[strategyId] = {
      ...this.getConfig(strategyId),
      ...config,
      params: {
        ...this.getConfig(strategyId).params,
        ...(config.params ?? {}),
      },
    };
    this.#persistConfigs();
    bus.emit(Events.STRATEGY_PARAMS_CHANGED, { strategyId, config: this.#configs[strategyId] });
  },

  /**
   * @param {string} strategyId
   * @returns {ScanResult|undefined}
   */
  getLastResult(strategyId) {
    return this.#lastResults[strategyId];
  },

  /**
   * Run a single strategy scan on candle data.
   * @param {string} strategyId
   * @param {string} symbol
   * @param {string} timeframe
   * @param {Record<string, unknown>} [paramOverrides]
   * @returns {Promise<ScanResult>}
   */
  async runStrategy(strategyId, symbol, timeframe, paramOverrides) {
    const start = performance.now();
    const plugin = registry.get(strategyId);

    if (!plugin) {
      throw new Error(`Strategy not found: ${strategyId}`);
    }

    const candles = await DataManager.getCandles(symbol, timeframe);
    if (candles.length === 0) {
      throw new Error(`No candle data for ${symbol} ${timeframe}`);
    }

    const config = this.getConfig(strategyId);
    const params = { ...config.params, ...paramOverrides };
    const strategy = registry.createInstance(strategyId);

    strategy.initialize(params);
    strategy.setRunContext({ symbol, timeframe });

    const warmup = strategy.getWarmupBars();
    const signals = [];

    for (let i = warmup; i < candles.length; i++) {
      strategy.calculate(candles, i);
      const ctx = createContext(symbol, timeframe, candles, i, params);
      const signal = strategy.generateSignal(ctx);

      if (signal && strategy.validate(signal)) {
        signals.push(signal);
      }
    }

    const result = {
      strategyId,
      symbol,
      timeframe,
      signals,
      barsScanned: candles.length - warmup,
      durationMs: Math.round(performance.now() - start),
    };

    this.#lastResults[strategyId] = result;
    saveToStorage(Config.STORAGE_KEYS.STRATEGY_RESULTS, this.#lastResults);

    bus.emit(Events.STRATEGY_RUN, result);
    bus.emit(Events.SIGNALS_GENERATED, result);
    bus.emit(Events.LOG_MESSAGE, {
      message: `${plugin.name}: ${signals.length} signals on ${symbol} ${timeframe} (${result.durationMs}ms)`,
      level: 'info',
      time: new Date(),
    });

    log.info(`Scan complete: ${strategyId} → ${signals.length} signals`);
    return result;
  },

  /**
   * Run all enabled strategies.
   * @param {string} symbol
   * @param {string} timeframe
   * @returns {Promise<ScanResult[]>}
   */
  async runAll(symbol, timeframe) {
    const results = [];

    for (const plugin of registry.getAll()) {
      const config = this.getConfig(plugin.id);
      if (!config.enabled) continue;

      try {
        const result = await this.runStrategy(plugin.id, symbol, timeframe);
        results.push(result);
      } catch (err) {
        log.error(`Failed to run ${plugin.id}:`, err);
        bus.emit(Events.LOG_MESSAGE, {
          message: `Strategy ${plugin.name} failed: ${err.message}`,
          level: 'error',
          time: new Date(),
        });
      }
    }

    return results;
  },

  /**
   * Export signals from last scan as JSON string.
   * @param {string} strategyId
   * @returns {string}
   */
  exportSignalsJSON(strategyId) {
    const result = this.#lastResults[strategyId];
    if (!result) throw new Error('No scan results to export');
    return JSON.stringify(result, null, 2);
  },

  #ensureDefaults() {
    for (const plugin of registry.getAll()) {
      if (!this.#configs[plugin.id]) {
        const instance = registry.createInstance(plugin.id);
        const schema = instance.getParameterSchema();
        const params = {};
        for (const def of schema) {
          params[def.key] = def.default;
        }
        this.#configs[plugin.id] = { enabled: true, params };
      }
    }
    this.#persistConfigs();
  },

  #persistConfigs() {
    saveToStorage(Config.STORAGE_KEYS.STRATEGIES, this.#configs);
  },
};

export default StrategyEngine;
