/**
 * Phase 7 statistics engine tests.
 * Run: node tests/statistics/StatisticsTests.js
 */

import { computeStatistics } from '../../src/statistics/StatisticsCalculator.js';
import { calcStreaks } from '../../src/statistics/StreakCalculator.js';
import { buildEquityCurve, calcMaxDrawdown } from '../../src/statistics/EquityCurve.js';

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
function trade(i, profit, outcome) {
  return {
    id: `t${i}`, signalId: `s${i}`, strategyId: 'test', symbol: 'EURUSD', timeframe: 'H1',
    direction: 'long', outcome, exitReason: outcome === 'win' ? 'tp' : 'sl',
    entryPrice: 1.0850, exitPrice: 1.0860, sl: 1.0840, tp: 1.0870,
    entryTime: i * 1000, exitTime: i * 1000 + 500, entryBar: i, exitBar: i + 5,
    pips: profit, profit, commission: 1, durationBars: 5, partialCloses: [], reason: '',
  };
}

console.log('\n=== Statistics Engine Tests ===\n');

{
  const stats = computeStatistics([], 10000);
  assert('ST-01: Empty trades', stats.totalTrades === 0 && stats.finalBalance === 10000);
}

{
  const trades = [trade(1, 20, 'win'), trade(2, -10, 'loss'), trade(3, 20, 'win')];
  const stats = computeStatistics(trades, 10000);
  assert('ST-02: Win rate 66.7%', Math.abs(stats.winRate - 66.67) < 1);
  assert('ST-03: Net profit 30', stats.netProfit === 30);
  assert('ST-04: Profit factor 4', stats.profitFactor === 4);
}

{
  const trades = [trade(1, 10, 'win'), trade(2, 10, 'win'), trade(3, -5, 'loss')];
  const streaks = calcStreaks(trades);
  assert('ST-05: Longest win streak 2', streaks.longestWinStreak === 2);
}

{
  const trades = [trade(1, 20, 'win'), trade(2, -30, 'loss'), trade(3, 10, 'win')];
  const curve = buildEquityCurve(trades, 10000);
  const dd = calcMaxDrawdown(curve);
  assert('ST-06: Max drawdown 30', dd.maxDrawdown === 30);
}

{
  const trades = [trade(1, 20, 'win'), trade(2, -10, 'loss')];
  const stats = computeStatistics(trades, 10000);
  assert('ST-07: Expectancy positive', stats.expectancy === 5);
  assert('ST-08: Has equity curve', stats.equityCurve.length === 3);
}

console.log(`\n=== Results: ${passed} passed, ${failed} failed ===\n`);
process.exit(failed > 0 ? 1 : 0);
