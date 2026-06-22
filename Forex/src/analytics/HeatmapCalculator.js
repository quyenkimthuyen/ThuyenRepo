/**
 * Performance heatmap aggregation from trade results.
 * @module analytics/HeatmapCalculator
 */

import { getSession } from '../chart/SessionUtils.js';

/** @typedef {import('../simulation/TradeSimulator.js').TradeResult} TradeResult */

/**
 * @typedef {Object} HeatmapCell
 * @property {string} key
 * @property {string} label
 * @property {number} trades
 * @property {number} wins
 * @property {number} losses
 * @property {number} winRate
 * @property {number} netProfit
 * @property {number} avgProfit
 */

/**
 * @typedef {Object} HeatmapData
 * @property {string} dimension
 * @property {HeatmapCell[]} cells
 */

/** Weekday labels in calendar order (Mon–Sun). */
const WEEKDAYS = Object.freeze([
  { key: 'Mon', index: 1 },
  { key: 'Tue', index: 2 },
  { key: 'Wed', index: 3 },
  { key: 'Thu', index: 4 },
  { key: 'Fri', index: 5 },
  { key: 'Sat', index: 6 },
  { key: 'Sun', index: 0 },
]);

/** Available heatmap dimensions per idea.txt analytics spec. */
export const HEATMAP_DIMENSIONS = Object.freeze([
  { id: 'month', label: 'By Month' },
  { id: 'day', label: 'By Day' },
  { id: 'hour', label: 'By Hour' },
  { id: 'session', label: 'By Session' },
  { id: 'strategy', label: 'By Strategy' },
  { id: 'pair', label: 'By Pair' },
  { id: 'timeframe', label: 'By Timeframe' },
]);

/**
 * Resolve bucket key for a trade in a given dimension.
 * @param {TradeResult} trade
 * @param {string} dimension
 * @returns {string}
 */
function bucketKey(trade, dimension) {
  const date = new Date(trade.entryTime);

  switch (dimension) {
    case 'month':
      return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`;
    case 'day':
      return WEEKDAYS.find((d) => d.index === date.getUTCDay())?.key ?? 'Sun';
    case 'hour':
      return `${String(date.getUTCHours()).padStart(2, '0')}:00`;
    case 'session':
      return getSession(trade.entryTime);
    case 'strategy':
      return trade.strategyId;
    case 'pair':
      return trade.symbol;
    case 'timeframe':
      return trade.timeframe;
    default:
      return 'unknown';
  }
}

/**
 * Sort cells in a natural order for the dimension.
 * @param {HeatmapCell[]} cells
 * @param {string} dimension
 * @returns {HeatmapCell[]}
 */
function sortCells(cells, dimension) {
  if (dimension === 'day') {
    const order = WEEKDAYS.map((d) => d.key);
    return [...cells].sort((a, b) => order.indexOf(a.key) - order.indexOf(b.key));
  }
  if (dimension === 'hour') {
    return [...cells].sort((a, b) => a.key.localeCompare(b.key));
  }
  return [...cells].sort((a, b) => a.key.localeCompare(b.key));
}

/**
 * Aggregate trades into heatmap cells for one dimension.
 * @param {TradeResult[]} trades
 * @param {string} dimension
 * @returns {HeatmapData}
 */
export function computeHeatmap(trades, dimension) {
  /** @type {Map<string, HeatmapCell>} */
  const map = new Map();

  for (const trade of trades) {
    const key = bucketKey(trade, dimension);
    if (!map.has(key)) {
      map.set(key, {
        key,
        label: key,
        trades: 0,
        wins: 0,
        losses: 0,
        winRate: 0,
        netProfit: 0,
        avgProfit: 0,
      });
    }

    const cell = map.get(key);
    cell.trades += 1;
    if (trade.outcome === 'win') cell.wins += 1;
    else if (trade.outcome === 'loss') cell.losses += 1;
    cell.netProfit += trade.profit;
  }

  const cells = sortCells([...map.values()], dimension).map((cell) => ({
    ...cell,
    winRate: cell.trades ? (cell.wins / cell.trades) * 100 : 0,
    avgProfit: cell.trades ? cell.netProfit / cell.trades : 0,
  }));

  return { dimension, cells };
}

/**
 * Compute all heatmap dimensions at once.
 * @param {TradeResult[]} trades
 * @returns {Record<string, HeatmapData>}
 */
export function computeAllHeatmaps(trades) {
  /** @type {Record<string, HeatmapData>} */
  const result = {};
  for (const dim of HEATMAP_DIMENSIONS) {
    result[dim.id] = computeHeatmap(trades, dim.id);
  }
  return result;
}
