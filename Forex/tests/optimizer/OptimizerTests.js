/**
 * Phase 9 optimizer tests.
 * Run: node tests/optimizer/OptimizerTests.js
 */

import { parseValueList, buildCombinations, countCombinations, defaultGridForParam, augmentParamGrid } from '../../src/optimizer/ParameterGrid.js';
import { runMonteCarlo } from '../../src/optimizer/MonteCarloEngine.js';
import { getRankValue } from '../../src/optimizer/GridSearchEngine.js';
import { stripBacktestResult, stripGridSearchForStorage } from '../../src/optimizer/researchPersistence.js';
import {
  computeMarketStats,
  suggestGridString,
  suggestParamGridFromData,
  timeframeScale,
} from '../../src/optimizer/GridSuggestEngine.js';
import {
  buildSensitivitySeries,
  getVaryingParamKeys,
} from '../../src/optimizer/GridSensitivity.js';
import { computeStatistics } from '../../src/statistics/StatisticsCalculator.js';

let passed = 0;
let failed = 0;

/**
 * @param {string} name
 * @param {boolean} ok
 */
function assert(name, ok) {
  if (ok) { passed++; console.log(`  ✓ ${name}`); }
  else { failed++; console.error(`  ✗ ${name}`); }
}

/** @returns {import('../../src/simulation/TradeSimulator.js').TradeResult} */
function trade(i, profit) {
  return {
    id: `t${i}`, signalId: `s${i}`, strategyId: 'test', symbol: 'EURUSD', timeframe: 'H1',
    direction: 'long', outcome: profit >= 0 ? 'win' : 'loss', exitReason: 'tp',
    entryPrice: 1.0850, exitPrice: 1.0860, sl: 1.0840, tp: 1.0870,
    entryTime: i * 3600000, exitTime: i * 3600000 + 1000, entryBar: i, exitBar: i + 5,
    pips: profit, profit, commission: 1, durationBars: 5, partialCloses: [], reason: '',
  };
}

console.log('\n=== Optimizer Tests ===\n');

{
  assert('OP-01: Parse comma list', parseValueList('1,2,3').join(',') === '1,2,3');
  assert('OP-02: Parse range', parseValueList('10:30:10').length === 3);
}

{
  const combos = buildCombinations({ rr: [1, 2], swing: [5, 7] });
  assert('OP-03: 4 combinations', combos.length === 4);
  assert('OP-04: Count matches', countCombinations({ rr: [1, 2], swing: [5, 7] }) === 4);
}

{
  const def = { key: 'rr', label: 'RR', type: 'number', default: 2, min: 1, max: 5, step: 0.5 };
  const grid = defaultGridForParam(def);
  assert('OP-05: Default grid has 3', grid.length === 3);
}

{
  const grid = augmentParamGrid('break-retest', { emaFast: [10, 20, 30] });
  assert('OP-05b: Trend EMA grid forces filter', grid.useTrendFilter?.length === 1 && grid.useTrendFilter[0] === true);
  const plain = augmentParamGrid('break-retest', { rr: [1, 2] });
  assert('OP-05c: Non-trend grid unchanged', !('useTrendFilter' in plain));
}

{
  const trades = [trade(1, 20), trade(2, -10), trade(3, 15), trade(4, -5), trade(5, 10)];
  const mc = runMonteCarlo(trades, 10000, 200);
  assert('OP-06: MC iterations', mc.iterations === 200);
  assert('OP-07: MC percentiles', mc.percentiles.p50.finalBalance > 0);
  assert('OP-08: P5 <= P95', mc.percentiles.p5.finalBalance <= mc.percentiles.p95.finalBalance);
}

{
  const stats = computeStatistics([trade(1, 20), trade(2, -10)], 10000);
  assert('OP-09: Rank expectancy', getRankValue(stats, 'expectancy') === 5);
  assert('OP-10: Rank PF', getRankValue(stats, 'profitFactor') === 2);
}

{
  const signals = Array.from({ length: 100 }, (_, i) => ({ id: `s${i}`, time: i }));
  const trades = Array.from({ length: 80 }, (_, i) => trade(i, i % 2 ? 10 : -5));
  const full = {
    signals,
    trades,
    stats: computeStatistics(trades, 10000),
    barsScanned: 5000,
    durationMs: 120,
  };
  const stripped = stripBacktestResult(full);
  assert('OP-11: Strip backtest drops arrays', !('signals' in stripped) && !('trades' in stripped));
  assert('OP-12: Strip keeps counts', stripped.signalCount === 100 && stripped.tradeCount === 80);

  const grid = {
    strategyId: 'ema-pullback',
    symbol: 'EURUSD',
    timeframe: 'H1',
    rankMetric: 'expectancy',
    totalCombinations: 200,
    durationMs: 999,
    entries: Array.from({ length: 200 }, (_, i) => ({
      params: { rr: 1 + (i % 3) },
      rank: 200 - i,
      result: full,
    })),
    best: null,
  };
  grid.best = grid.entries[0];
  const persisted = stripGridSearchForStorage(grid, 50);
  assert('OP-13: Grid persist caps rows', persisted.entries.length === 50);
  assert('OP-14: Grid persist strips trades', !('trades' in persisted.entries[0].result));
}

{
  /** @type {import('../../src/data/Candle.js').Candle[]} */
  const candles = Array.from({ length: 30 }, (_, i) => ({
    time: i * 3600000,
    open: 1.08,
    high: 1.0812,
    low: 1.0790,
    close: 1.0805,
    volume: 100,
  }));
  const stats = computeMarketStats(candles, 'EURUSD');
  assert('OP-15: Market stats avg range', stats.avgRangePips > 0 && stats.candleCount === 30);
  assert('OP-16: H1 timeframe scale', timeframeScale('H1') === 'intraday');
  assert('OP-17: M15 timeframe scale', timeframeScale('M15') === 'scalp');

  const breakoutDef = {
    key: 'breakoutPips',
    label: 'Breakout',
    type: 'number',
    default: 5,
    min: 1,
    max: 50,
    step: 1,
  };
  const gridStr = suggestGridString(breakoutDef, { ...stats, scale: 'intraday' });
  const parsed = parseValueList(gridStr ?? '');
  assert('OP-18: Breakout grid from volatility', parsed.length >= 2);

  const suggestion = suggestParamGridFromData(
    'break-retest',
    [breakoutDef, { key: 'rr', label: 'RR', type: 'number', default: 2, min: 1, max: 10, step: 0.5 }],
    candles,
    'EURUSD',
    'H1'
  );
  assert('OP-19: Suggest checks breakout + rr', suggestion.checks.breakoutPips && suggestion.checks.rr);
  assert('OP-20: Suggest message has candle count', suggestion.message.includes('30'));
}

{
  /** @type {import('../../src/optimizer/GridSearchEngine.js').GridSearchEntry[]} */
  const entries = [
    { params: { rr: 1.5, swing: 5 }, result: { stats: { winRate: 40, expectancy: 5, totalTrades: 20 } }, rank: 1 },
    { params: { rr: 2, swing: 5 }, result: { stats: { winRate: 50, expectancy: 10, totalTrades: 22 } }, rank: 2 },
    { params: { rr: 2.5, swing: 7 }, result: { stats: { winRate: 60, expectancy: 15, totalTrades: 18 } }, rank: 3 },
    { params: { rr: 3, swing: 7 }, result: { stats: { winRate: 45, expectancy: 8, totalTrades: 25 } }, rank: 4 },
  ];

  const varying = getVaryingParamKeys(entries);
  assert('OP-21: Varying params detected', varying.includes('rr') && varying.includes('swing'));

  const rrSeries = buildSensitivitySeries(entries, 'rr', 5);
  assert('OP-22: RR sensitivity buckets', rrSeries.length === 4);
  assert('OP-23: RR=2 averaged WR', rrSeries.find((p) => p.paramValue === 2)?.winRate === 50);

  const lowTrade = buildSensitivitySeries([
    { params: { rr: 1 }, result: { stats: { winRate: 100, expectancy: 99, totalTrades: 2 } }, rank: 1 },
    { params: { rr: 2 }, result: { stats: { winRate: 0, expectancy: -5, totalTrades: 2 } }, rank: 0 },
  ], 'rr', 5);
  assert('OP-24: Low-trade buckets hidden', lowTrade.length === 0);
}

console.log(`\n=== Results: ${passed} passed, ${failed} failed ===\n`);
process.exit(failed > 0 ? 1 : 0);
