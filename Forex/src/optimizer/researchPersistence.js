/**
 * Trim research results before localStorage — grid search stores stats only.
 * @module optimizer/researchPersistence
 */

import { Config } from '../core/Config.js';

/** @typedef {import('./BacktestRunner.js').BacktestResult} BacktestResult */
/** @typedef {import('./GridSearchEngine.js').GridSearchResult} GridSearchResult */
/** @typedef {import('./WalkForwardEngine.js').WalkForwardResult} WalkForwardResult */

/**
 * @typedef {Object} PersistedBacktestResult
 * @property {import('../statistics/StatisticsCalculator.js').PerformanceStats} stats
 * @property {number} barsScanned
 * @property {number} durationMs
 * @property {number} signalCount
 * @property {number} tradeCount
 */

/**
 * @param {BacktestResult} result
 * @returns {PersistedBacktestResult}
 */
export function stripBacktestResult(result) {
  return {
    stats: result.stats,
    barsScanned: result.barsScanned,
    durationMs: result.durationMs,
    signalCount: result.signals?.length ?? 0,
    tradeCount: result.trades?.length ?? 0,
  };
}

/**
 * @param {GridSearchResult|null} result
 * @param {number} [maxEntries]
 * @returns {GridSearchResult|null}
 */
export function stripGridSearchForStorage(result, maxEntries = Config.OPTIMIZER.PERSIST_GRID_TOP) {
  if (!result) return null;

  const entries = result.entries.slice(0, maxEntries).map((entry) => ({
    params: entry.params,
    rank: entry.rank,
    result: stripBacktestResult(entry.result),
  }));

  return {
    strategyId: result.strategyId,
    symbol: result.symbol,
    timeframe: result.timeframe,
    rankMetric: result.rankMetric,
    totalCombinations: result.totalCombinations,
    entries,
    best: entries[0] ?? null,
    durationMs: result.durationMs,
    optimizedParamKeys: result.optimizedParamKeys,
    paramGrid: result.paramGrid,
  };
}

/**
 * @param {WalkForwardResult|null} result
 * @returns {WalkForwardResult|null}
 */
export function stripWalkForwardForStorage(result) {
  if (!result) return null;

  return {
    strategyId: result.strategyId,
    symbol: result.symbol,
    timeframe: result.timeframe,
    params: result.params,
    folds: result.folds.map((fold) => ({
      fold: fold.fold,
      isStart: fold.isStart,
      isEnd: fold.isEnd,
      oosStart: fold.oosStart,
      oosEnd: fold.oosEnd,
      inSample: stripBacktestResult(fold.inSample),
      outOfSample: stripBacktestResult(fold.outOfSample),
    })),
    avgIsNetProfit: result.avgIsNetProfit,
    avgOosNetProfit: result.avgOosNetProfit,
    oosWinRate: result.oosWinRate,
    durationMs: result.durationMs,
  };
}
