/**
 * Grid search parameter optimizer — tests every parameter combination.
 * @module optimizer/GridSearchEngine
 */

import { buildCombinations } from './ParameterGrid.js';
import { runBacktest } from './BacktestRunner.js';

/** @typedef {import('./BacktestRunner.js').BacktestResult} BacktestResult */
/** @typedef {import('../simulation/TradeConfig.js').TradeConfig} TradeConfig */
/** @typedef {import('../data/Candle.js').Candle} Candle */

/** @typedef {'expectancy'|'netProfit'|'profitFactor'|'sharpeRatio'|'winRate'} RankMetric */

/**
 * @typedef {Object} GridSearchEntry
 * @property {Record<string, unknown>} params
 * @property {BacktestResult} result
 * @property {number} rank
 */

/**
 * @typedef {Object} GridSearchResult
 * @property {string} strategyId
 * @property {string} symbol
 * @property {string} timeframe
 * @property {RankMetric} rankMetric
 * @property {number} totalCombinations
 * @property {GridSearchEntry[]} entries
 * @property {GridSearchEntry|null} best
 * @property {number} durationMs
 */

/**
 * Rank value for sorting (higher is better).
 * @param {import('../statistics/StatisticsCalculator.js').PerformanceStats} stats
 * @param {RankMetric} metric
 * @returns {number}
 */
export function getRankValue(stats, metric) {
  if (metric === 'profitFactor') {
    return stats.profitFactor === Infinity ? 999 : stats.profitFactor;
  }
  return /** @type {number} */ (stats[metric] ?? 0);
}

/**
 * Run grid search over parameter combinations.
 * @param {Object} options
 * @param {string} options.strategyId
 * @param {string} options.symbol
 * @param {string} options.timeframe
 * @param {Candle[]} options.candles
 * @param {Record<string, number[]|string[]|boolean[]>} options.paramGrid
 * @param {TradeConfig} options.tradeConfig
 * @param {RankMetric} [options.rankMetric='expectancy']
 * @param {number} [options.maxCombinations=500]
 * @param {(progress: number) => void} [options.onProgress]
 * @param {typeof runBacktest} [options.backtestFn]
 * @returns {Promise<GridSearchResult>}
 */
export async function runGridSearch({
  strategyId,
  symbol,
  timeframe,
  candles,
  paramGrid,
  tradeConfig,
  rankMetric = 'expectancy',
  maxCombinations = 500,
  onProgress,
}) {
  const start = performance.now();
  const combos = buildCombinations(paramGrid);

  if (combos.length > maxCombinations) {
    throw new Error(`Too many combinations (${combos.length}). Max is ${maxCombinations}.`);
  }

  /** @type {(typeof runBacktest)} */
  const backtest = options.backtestFn ?? runBacktest;

  /** @type {GridSearchEntry[]} */
  const entries = [];

  for (let i = 0; i < combos.length; i++) {
    const params = combos[i];
    const result = await backtest(strategyId, symbol, timeframe, candles, params, tradeConfig);
    const rank = getRankValue(result.stats, rankMetric);

    entries.push({ params, result, rank });

    if (onProgress) onProgress((i + 1) / combos.length);
    if (i % 5 === 0) await new Promise((r) => setTimeout(r, 0));
  }

  entries.sort((a, b) => b.rank - a.rank);

  return {
    strategyId,
    symbol,
    timeframe,
    rankMetric,
    totalCombinations: combos.length,
    entries,
    best: entries[0] ?? null,
    durationMs: Math.round(performance.now() - start),
  };
}
