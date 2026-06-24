/**
 * Research engine — grid search, walk-forward, and Monte Carlo orchestration.
 * @module optimizer/ResearchEngine
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { loadPersistedResult, savePersistedResult } from '../utils/resultsPersistence.js';
import DataManager from '../data/DataManager.js';
import StrategyEngine from '../strategy/StrategyEngine.js';
import SimulationEngine from '../simulation/SimulationEngine.js';
import { mergeTradeConfig } from '../simulation/TradeConfig.js';
import { runGridSearch } from './GridSearchEngine.js';
import { runWalkForward } from './WalkForwardEngine.js';
import PerformanceEngine from '../performance/PerformanceEngine.js';
import {
  stripGridSearchForStorage,
  stripWalkForwardForStorage,
} from './researchPersistence.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('ResearchEngine');

/**
 * Main research / optimization service module.
 */
class ResearchEngine {
  /** @type {import('./GridSearchEngine.js').GridSearchResult|null} */
  #lastGrid = null;

  /** @type {import('./WalkForwardEngine.js').WalkForwardResult|null} */
  #lastWalkForward = null;

  /** @type {import('./MonteCarloEngine.js').MonteCarloResult|null} */
  #lastMonteCarlo = null;

  /**
   * @param {{ bus: import('../core/EventBus.js').EventBus }} _ctx
   */
  async initialize(_ctx) {
    const saved = /** @type {{ grid?: unknown, walkForward?: unknown, monteCarlo?: unknown }} */ (
      await loadPersistedResult(Config.STORAGE_KEYS.RESEARCH_RESULTS, {})
    );
    this.#lastGrid = saved.grid ?? null;
    this.#lastWalkForward = saved.walkForward ?? null;
    this.#lastMonteCarlo = saved.monteCarlo ?? null;
    log.info('Research engine ready');
  }

  getLastGridResult() { return this.#lastGrid; }
  getLastWalkForwardResult() { return this.#lastWalkForward; }
  getLastMonteCarloResult() { return this.#lastMonteCarlo; }

  /**
   * @param {Object} options
   * @param {string} options.strategyId
   * @param {string} options.symbol
   * @param {string} options.timeframe
   * @param {Record<string, number[]|string[]|boolean[]>} options.paramGrid
   * @param {import('./GridSearchEngine.js').RankMetric} [options.rankMetric]
   * @param {(progress: number) => void} [options.onProgress]
   * @param {boolean} [options.autoWalkForward]
   * @returns {Promise<import('./GridSearchEngine.js').GridSearchResult>}
   */
  async runGridSearch(options) {
    const candles = await DataManager.getCandles(options.symbol, options.timeframe);
    if (candles.length === 0) throw new Error(`No candle data for ${options.symbol} ${options.timeframe}`);

    const tradeConfig = mergeTradeConfig(SimulationEngine.getConfig());
    const max = Config.OPTIMIZER.MAX_COMBINATIONS;
    const autoWf = options.autoWalkForward ?? Config.OPTIMIZER.AUTO_WALK_FORWARD_AFTER_GRID;

    const result = await runGridSearch({
      ...options,
      candles,
      tradeConfig,
      maxCombinations: max,
      backtestFn: PerformanceEngine.runBacktest.bind(PerformanceEngine),
    });

    if (autoWf && result.best?.params) {
      const opt = Config.OPTIMIZER;
      try {
        const wf = runWalkForward({
          strategyId: options.strategyId,
          symbol: options.symbol,
          timeframe: options.timeframe,
          candles,
          params: result.best.params,
          tradeConfig,
          inSampleRatio: opt.IN_SAMPLE_RATIO,
          oosRatio: opt.OOS_RATIO,
          stepRatio: opt.STEP_RATIO,
          maxFolds: opt.WALK_FORWARD_FOLDS,
        });
        result.walkForward = wf;
        this.#lastWalkForward = wf;
      } catch (err) {
        bus.emit(Events.LOG_MESSAGE, {
          message: `Walk-forward on best combo skipped: ${err instanceof Error ? err.message : String(err)}`,
          level: 'warn',
          time: new Date(),
        });
      }
    }

    this.#lastGrid = result;
    await this.#persist();

    bus.emit(Events.OPTIMIZATION_COMPLETE, result);
    const wfNote = result.walkForward
      ? ` · WF OOS avg $${result.walkForward.avgOosNetProfit.toFixed(2)}`
      : '';
    bus.emit(Events.LOG_MESSAGE, {
      message: `Grid search: ${result.totalCombinations} combos, best ${options.rankMetric ?? 'expectancy'} = ${result.best?.rank.toFixed(2) ?? 'N/A'}${wfNote}`,
      level: 'info',
      time: new Date(),
    });

    log.info(`Grid search done: ${result.totalCombinations} combinations`);
    return result;
  }

  /**
   * @param {Object} options
   * @param {string} options.strategyId
   * @param {string} options.symbol
   * @param {string} options.timeframe
   * @param {number} [options.inSampleRatio]
   * @param {number} [options.oosRatio]
   * @param {number} [options.maxFolds]
   * @returns {Promise<import('./WalkForwardEngine.js').WalkForwardResult>}
   */
  async runWalkForward(options) {
    const candles = await DataManager.getCandles(options.symbol, options.timeframe);
    if (candles.length === 0) throw new Error(`No candle data for ${options.symbol} ${options.timeframe}`);

    const config = StrategyEngine.getConfig(options.strategyId);
    const tradeConfig = mergeTradeConfig(SimulationEngine.getConfig());
    const opt = Config.OPTIMIZER;

    const result = runWalkForward({
      ...options,
      candles,
      params: config.params,
      tradeConfig,
      inSampleRatio: options.inSampleRatio ?? opt.IN_SAMPLE_RATIO,
      oosRatio: options.oosRatio ?? opt.OOS_RATIO,
      stepRatio: opt.STEP_RATIO,
      maxFolds: options.maxFolds ?? opt.WALK_FORWARD_FOLDS,
    });

    this.#lastWalkForward = result;
    await this.#persist();

    bus.emit(Events.WALK_FORWARD_COMPLETE, result);
    bus.emit(Events.LOG_MESSAGE, {
      message: `Walk-forward: ${result.folds.length} folds, avg OOS $${result.avgOosNetProfit.toFixed(2)}`,
      level: 'info',
      time: new Date(),
    });

    log.info(`Walk-forward done: ${result.folds.length} folds`);
    return result;
  }

  /**
   * @param {Object} [options]
   * @param {number} [options.iterations]
   * @param {import('../simulation/TradeSimulator.js').TradeResult[]} [options.trades]
   * @returns {Promise<import('./MonteCarloEngine.js').MonteCarloResult>}
   */
  async runMonteCarlo(options = {}) {
    const sim = SimulationEngine.getLastResult();
    const trades = options.trades ?? sim?.trades;

    if (!trades?.length) {
      throw new Error('No trades available — run a simulation first.');
    }

    const balance = SimulationEngine.getConfig().initialBalance;
    const iterations = options.iterations ?? Config.OPTIMIZER.MONTE_CARLO_ITERATIONS;

    const result = await PerformanceEngine.runMonteCarlo(trades, balance, iterations);

    this.#lastMonteCarlo = result;
    await this.#persist();

    bus.emit(Events.MONTE_CARLO_COMPLETE, result);
    bus.emit(Events.LOG_MESSAGE, {
      message: `Monte Carlo: ${iterations} runs, median balance $${result.percentiles.p50.finalBalance.toFixed(2)}`,
      level: 'info',
      time: new Date(),
    });

    log.info(`Monte Carlo done: ${iterations} iterations`);
    return result;
  }

  async #persist() {
    const payload = {
      grid: stripGridSearchForStorage(this.#lastGrid),
      walkForward: stripWalkForwardForStorage(this.#lastWalkForward),
      monteCarlo: this.#lastMonteCarlo,
    };
    const ok = await savePersistedResult(Config.STORAGE_KEYS.RESEARCH_RESULTS, payload);

    if (!ok) {
      bus.emit(Events.LOG_MESSAGE, {
        message: 'Không lưu được kết quả optimizer — vẫn giữ trong phiên hiện tại.',
        level: 'warn',
        time: new Date(),
      });
    }
  }
}

export default new ResearchEngine();
