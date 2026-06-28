/**
 * Phase 8 heatmap calculator tests.
 * Run: node tests/analytics/HeatmapTests.js
 */

import { computeHeatmap, computeAllHeatmaps } from '../../src/analytics/HeatmapCalculator.js';

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

/**
 * @param {number} i
 * @param {number} profit
 * @param {number} entryTime
 * @returns {import('../../src/simulation/TradeSimulator.js').TradeResult}
 */
function trade(i, profit, entryTime) {
  return {
    id: `t${i}`, signalId: `s${i}`, strategyId: 'break-retest', symbol: 'EURUSD', timeframe: 'H1',
    direction: 'long', outcome: profit >= 0 ? 'win' : 'loss', exitReason: 'tp',
    entryPrice: 1.0850, exitPrice: 1.0860, sl: 1.0840, tp: 1.0870,
    entryTime, exitTime: entryTime + 3600000, entryBar: i, exitBar: i + 5,
    pips: profit, profit, commission: 1, durationBars: 5, partialCloses: [], reason: '',
  };
}

console.log('\n=== Heatmap Calculator Tests ===\n');

{
  const heatmap = computeHeatmap([], 'month');
  assert('HM-01: Empty trades', heatmap.cells.length === 0);
}

{
  const jan = Date.UTC(2024, 0, 15, 10);
  const feb = Date.UTC(2024, 1, 10, 14);
  const trades = [trade(1, 20, jan), trade(2, -10, jan), trade(3, 15, feb)];
  const heatmap = computeHeatmap(trades, 'month');
  assert('HM-02: Two months', heatmap.cells.length === 2);
  assert('HM-03: Jan profit 10', heatmap.cells.find((c) => c.key === '2024-01')?.netProfit === 10);
}

{
  const mon = Date.UTC(2024, 0, 1, 8);
  const wed = Date.UTC(2024, 0, 3, 12);
  const trades = [trade(1, 10, mon), trade(2, 5, wed)];
  const heatmap = computeHeatmap(trades, 'day');
  assert('HM-04: Day buckets', heatmap.cells.length === 2);
  assert('HM-05: Mon first', heatmap.cells[0].key === 'Mon');
}

{
  const london = Date.UTC(2024, 0, 10, 10);
  const ny = Date.UTC(2024, 0, 10, 14);
  const trades = [trade(1, 10, london), trade(2, -5, ny)];
  const all = computeAllHeatmaps(trades);
  assert('HM-06: All dimensions', Object.keys(all).length === 7);
  assert('HM-07: Session bucket', all.session.cells.length >= 1);
}

console.log(`\n=== Results: ${passed} passed, ${failed} failed ===\n`);
process.exit(failed > 0 ? 1 : 0);
