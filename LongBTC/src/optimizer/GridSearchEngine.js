/**
 * Grid search parameter optimizer — tests every parameter combination.
 * @module optimizer/GridSearchEngine
 */

import { Config } from '../core/Config.js';
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
 * @property {boolean} [parallel]
 * @property {string[]} [optimizedParamKeys] - Params included in the grid search run
 * @property {Record<string, (number|string|boolean)[]>} [paramGrid] - Value lists used in the run
 * @property {import('./WalkForwardEngine.js').WalkForwardResult} [walkForward]
 */

/**
 * @typedef {Object} GridChunkPayload
 * @property {string} strategyId
 * @property {string} symbol
 * @property {string} timeframe
 * @property {Candle[]} candles
 * @property {Record<string, unknown>[]} combos
 * @property {Record<string, unknown>} baseParams
 * @property {TradeConfig} tradeConfig
 */

/**
 * @typedef {Object} GridChunkItem
 * @property {Record<string, unknown>} params
 * @property {BacktestResult} result
 */

/**
 * @typedef {(payload: GridChunkPayload) => Promise<GridChunkItem[]>} GridChunkFn
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
 * Split an array into fixed-size chunks.
 * @template T
 * @param {T[]} items
 * @param {number} chunkSize
 * @returns {T[][]}
 */
export function splitIntoChunks(items, chunkSize) {
  if (chunkSize < 1) return [items];
  /** @type {T[][]} */
  const chunks = [];
  for (let i = 0; i < items.length; i += chunkSize) {
    chunks.push(items.slice(i, i + chunkSize));
  }
  return chunks;
}

/**
 * @param {number} comboCount
 * @param {number} [poolSize]
 * @returns {number}
 */
export function gridChunkSize(comboCount, poolSize = Config.PERFORMANCE.WORKER_POOL_SIZE) {
  const targetChunks = Math.max(poolSize * 2, poolSize);
  return Math.max(1, Math.ceil(comboCount / targetChunks));
}

/**
 * Run grid search over parameter combinations.
 * @param {Object} options
 * @param {string} options.strategyId
 * @param {string} options.symbol
 * @param {string} options.timeframe
 * @param {Candle[]} options.candles
 * @param {Record<string, number[]|string[]|boolean[]>} options.paramGrid
 * @param {Record<string, unknown>} [options.baseParams]
 * @param {TradeConfig} options.tradeConfig
 * @param {RankMetric} [options.rankMetric='expectancy']
 * @param {number} [options.maxCombinations=500]
 * @param {(progress: number) => void} [options.onProgress]
 * @param {typeof runBacktest} [options.backtestFn]
 * @param {GridChunkFn} [options.gridChunkFn]
 * @returns {Promise<GridSearchResult>}
 */
export async function runGridSearch({
  strategyId,
  symbol,
  timeframe,
  candles,
  paramGrid,
  baseParams = {},
  tradeConfig,
  rankMetric = 'expectancy',
  maxCombinations = 500,
  onProgress,
  backtestFn = runBacktest,
  gridChunkFn,
}) {
  const start = performance.now();
  const combos = buildCombinations(paramGrid);

  if (combos.length > maxCombinations) {
    throw new Error(`Too many combinations (${combos.length}). Max is ${maxCombinations}.`);
  }

  const minParallel = Config.PERFORMANCE.GRID_PARALLEL_MIN_COMBOS;
  const useParallel = Boolean(gridChunkFn) && combos.length >= minParallel;

  /** @type {GridSearchEntry[]} */
  const entries = [];

  if (useParallel && gridChunkFn) {
    const chunkSize = gridChunkSize(combos.length);
    const chunks = splitIntoChunks(combos, chunkSize);
    let completed = 0;

    await Promise.all(chunks.map(async (chunk, chunkIndex) => {
      const chunkItems = await gridChunkFn({
        strategyId,
        symbol,
        timeframe,
        candles,
        combos: chunk,
        baseParams,
        tradeConfig,
      });

      for (const item of chunkItems) {
        entries.push({
          params: item.params,
          result: item.result,
          rank: getRankValue(item.result.stats, rankMetric),
        });
      }

      completed += chunk.length;
      if (onProgress) onProgress(completed / combos.length);
      if (chunkIndex % 2 === 0) await new Promise((r) => setTimeout(r, 0));
    }));
  } else {
    for (let i = 0; i < combos.length; i++) {
      const params = { ...baseParams, ...combos[i] };
      const result = await backtestFn(strategyId, symbol, timeframe, candles, params, tradeConfig);
      const rank = getRankValue(result.stats, rankMetric);

      entries.push({ params, result, rank });

      if (onProgress) onProgress((i + 1) / combos.length);
      if (i % 5 === 0) await new Promise((r) => setTimeout(r, 0));
    }
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
    parallel: useParallel,
    optimizedParamKeys: Object.keys(paramGrid),
    paramGrid,
  };
}
