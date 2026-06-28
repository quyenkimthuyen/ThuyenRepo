/**
 * Walk-forward analysis — in-sample vs out-of-sample rolling windows.
 * @module optimizer/WalkForwardEngine
 */

import { runBacktest } from './BacktestRunner.js';

/** @typedef {import('./BacktestRunner.js').BacktestResult} BacktestResult */
/** @typedef {import('../simulation/TradeConfig.js').TradeConfig} TradeConfig */
/** @typedef {import('../data/Candle.js').Candle} Candle */

/**
 * @typedef {Object} WalkForwardFold
 * @property {number} fold
 * @property {number} isStart
 * @property {number} isEnd
 * @property {number} oosStart
 * @property {number} oosEnd
 * @property {BacktestResult} inSample
 * @property {BacktestResult} outOfSample
 */

/**
 * @typedef {Object} WalkForwardResult
 * @property {string} strategyId
 * @property {string} symbol
 * @property {string} timeframe
 * @property {Record<string, unknown>} params
 * @property {WalkForwardFold[]} folds
 * @property {number} avgIsNetProfit
 * @property {number} avgOosNetProfit
 * @property {number} oosWinRate
 * @property {number} durationMs
 */

/**
 * Run rolling walk-forward test on candle data.
 * @param {Object} options
 * @param {string} options.strategyId
 * @param {string} options.symbol
 * @param {string} options.timeframe
 * @param {Candle[]} options.candles
 * @param {Record<string, unknown>} options.params
 * @param {TradeConfig} options.tradeConfig
 * @param {number} [options.inSampleRatio=0.7]
 * @param {number} [options.oosRatio=0.15]
 * @param {number} [options.stepRatio=0.1]
 * @param {number} [options.maxFolds=5]
 * @returns {WalkForwardResult}
 */
export function runWalkForward({
  strategyId,
  symbol,
  timeframe,
  candles,
  params,
  tradeConfig,
  inSampleRatio = 0.7,
  oosRatio = 0.15,
  stepRatio = 0.1,
  maxFolds = 5,
}) {
  const start = performance.now();
  const total = candles.length;
  const isLen = Math.floor(total * inSampleRatio);
  const oosLen = Math.floor(total * oosRatio);
  const step = Math.max(1, Math.floor(total * stepRatio));

  /** @type {WalkForwardFold[]} */
  const folds = [];

  for (let fold = 0; fold < maxFolds; fold++) {
    const isStart = fold * step;
    const isEnd = isStart + isLen;
    const oosEnd = isEnd + oosLen;

    if (isEnd >= total || oosEnd > total) break;

    const isCandles = candles.slice(isStart, isEnd);
    const oosCandles = candles.slice(isEnd, oosEnd);

    const inSample = runBacktest(strategyId, symbol, timeframe, isCandles, params, tradeConfig);
    const outOfSample = runBacktest(strategyId, symbol, timeframe, oosCandles, params, tradeConfig);

    folds.push({
      fold: fold + 1,
      isStart,
      isEnd,
      oosStart: isEnd,
      oosEnd,
      inSample,
      outOfSample,
    });
  }

  if (folds.length === 0) {
    throw new Error('Not enough candle data for walk-forward analysis.');
  }

  const avgIsNetProfit = folds.reduce((s, f) => s + f.inSample.stats.netProfit, 0) / folds.length;
  const avgOosNetProfit = folds.reduce((s, f) => s + f.outOfSample.stats.netProfit, 0) / folds.length;
  const profitableOos = folds.filter((f) => f.outOfSample.stats.netProfit > 0).length;
  const oosWinRate = (profitableOos / folds.length) * 100;

  return {
    strategyId,
    symbol,
    timeframe,
    params,
    folds,
    avgIsNetProfit,
    avgOosNetProfit,
    oosWinRate,
    durationMs: Math.round(performance.now() - start),
  };
}
