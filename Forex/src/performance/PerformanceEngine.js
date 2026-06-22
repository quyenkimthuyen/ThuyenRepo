/**
 * Performance engine — routes heavy work to Web Workers when beneficial.
 * @module performance/PerformanceEngine
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { runBacktest } from '../optimizer/BacktestRunner.js';
import { runMonteCarlo } from '../optimizer/MonteCarloEngine.js';
import { scoreSignalsBatch } from '../scoring/SignalScoreEngine.js';
import { shouldUseWorker } from './CandleSampler.js';
import { WorkerPool } from './WorkerPool.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('PerformanceEngine');

/**
 * Performance optimization service module.
 */
class PerformanceEngine {
  /** @type {WorkerPool|null} */
  #pool = null;

  /** @type {boolean} */
  #workersEnabled = false;

  /**
   * @param {{ bus: import('../core/EventBus.js').EventBus }} _ctx
   */
  async initialize(_ctx) {
    if (typeof Worker !== 'undefined') {
      try {
        this.#pool = new WorkerPool(
          new URL('../workers/compute.worker.js', import.meta.url),
          Config.PERFORMANCE.WORKER_POOL_SIZE
        );
        this.#workersEnabled = this.#pool.isAvailable();
      } catch (err) {
        log.warn('Worker init failed, using main thread:', err);
      }
    }

    bus.emit(Events.LOG_MESSAGE, {
      message: this.#workersEnabled
        ? `Web Workers active (${Config.PERFORMANCE.WORKER_POOL_SIZE} threads)`
        : 'Running on main thread (workers unavailable)',
      level: 'info',
      time: new Date(),
    });

    log.info(`Performance engine ready — workers: ${this.#workersEnabled}`);
  }

  /**
   * @returns {boolean}
   */
  workersEnabled() {
    return this.#workersEnabled;
  }

  /**
   * Run backtest on worker or main thread.
   * @param {Parameters<typeof runBacktest>} args
   * @returns {Promise<ReturnType<typeof runBacktest>>}
   */
  async runBacktest(...args) {
    const candles = args[3];
    if (this.#workersEnabled && this.#pool && shouldUseWorker(candles.length)) {
      return /** @type {ReturnType<typeof runBacktest>} */ (
        await this.#pool.run('backtest', {
          strategyId: args[0],
          symbol: args[1],
          timeframe: args[2],
          candles: args[3],
          params: args[4],
          tradeConfig: args[5],
        })
      );
    }
    return runBacktest(...args);
  }

  /**
   * Run Monte Carlo on worker or main thread.
   * @param {import('../simulation/TradeSimulator.js').TradeResult[]} trades
   * @param {number} initialBalance
   * @param {number} iterations
   * @returns {Promise<import('../optimizer/MonteCarloEngine.js').MonteCarloResult>}
   */
  async runMonteCarlo(trades, initialBalance, iterations) {
    if (this.#workersEnabled && this.#pool && iterations >= 200) {
      return /** @type {import('../optimizer/MonteCarloEngine.js').MonteCarloResult} */ (
        await this.#pool.run('monteCarlo', { trades, initialBalance, iterations })
      );
    }
    return runMonteCarlo(trades, initialBalance, iterations);
  }

  /**
   * Score signals batch on worker or main thread.
   * @param {import('../strategy/Signal.js').Signal[]} signals
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} spreadPips
   * @returns {Promise<import('../scoring/SignalScoreEngine.js').ScoredSignal[]>}
   */
  async scoreBatch(signals, candles, spreadPips) {
    if (this.#workersEnabled && this.#pool && signals.length >= 50) {
      return /** @type {import('../scoring/SignalScoreEngine.js').ScoredSignal[]} */ (
        await this.#pool.run('scoreBatch', { signals, candles, spreadPips })
      );
    }
    return scoreSignalsBatch(signals, candles, spreadPips);
  }
}

export default new PerformanceEngine();
