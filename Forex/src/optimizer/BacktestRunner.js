/**
 * Single backtest run — strategy scan + trade simulation on candle slice.
 * @module optimizer/BacktestRunner
 */

import { registry } from '../plugin/PluginRegistry.js';
import { createContext } from '../strategy/StrategyContext.js';
import { simulateTrades } from '../simulation/TradeSimulator.js';
import { computeStatistics } from '../statistics/StatisticsCalculator.js';

/** @typedef {import('../data/Candle.js').Candle} Candle */
/** @typedef {import('../simulation/TradeConfig.js').TradeConfig} TradeConfig */
/** @typedef {import('../statistics/StatisticsCalculator.js').PerformanceStats} PerformanceStats */
/** @typedef {import('../strategy/Signal.js').Signal} Signal */
/** @typedef {import('../simulation/TradeSimulator.js').TradeResult} TradeResult */

/**
 * @typedef {Object} BacktestResult
 * @property {Signal[]} signals
 * @property {TradeResult[]} trades
 * @property {PerformanceStats} stats
 * @property {number} barsScanned
 * @property {number} durationMs
 */

/**
 * Run a full backtest on a candle array with given strategy parameters.
 * @param {string} strategyId
 * @param {string} symbol
 * @param {string} timeframe
 * @param {Candle[]} candles
 * @param {Record<string, unknown>} params
 * @param {TradeConfig} tradeConfig
 * @returns {BacktestResult}
 */
export function runBacktest(strategyId, symbol, timeframe, candles, params, tradeConfig) {
  const start = performance.now();
  const strategy = registry.createInstance(strategyId);

  strategy.initialize(params);
  strategy.setRunContext({ symbol, timeframe });

  const warmup = strategy.getWarmupBars();
  /** @type {Signal[]} */
  const signals = [];

  for (let i = warmup; i < candles.length; i++) {
    strategy.calculate(candles, i);
    const ctx = createContext(symbol, timeframe, candles, i, params);
    const signal = strategy.generateSignal(ctx);
    if (signal && strategy.validate(signal)) {
      signals.push(signal);
    }
  }

  const trades = simulateTrades(signals, candles, tradeConfig);
  const stats = computeStatistics(trades, tradeConfig.initialBalance);

  return {
    signals,
    trades,
    stats,
    barsScanned: Math.max(0, candles.length - warmup),
    durationMs: Math.round(performance.now() - start),
  };
}
