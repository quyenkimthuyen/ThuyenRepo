/**
 * Phase 8 report exporter tests.
 * Run: node tests/report/ReportTests.js
 */

import { exportTradesCSV, exportReportJSON, buildPrintableHTML } from '../../src/report/ReportExporter.js';
import { buildDashboardCards } from '../../src/analytics/DashboardSummary.js';
import { computeStatistics } from '../../src/statistics/StatisticsCalculator.js';
import { Config } from '../../src/core/Config.js';

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
    id: `t${i}`, signalId: `s${i}`, strategyId: 'break-retest', symbol: 'EURUSD', timeframe: 'H1',
    direction: 'long', outcome: profit >= 0 ? 'win' : 'loss', exitReason: 'tp',
    entryPrice: 1.0850, exitPrice: 1.0860, sl: 1.0840, tp: 1.0870,
    entryTime: i * 3600000, exitTime: i * 3600000 + 1000, entryBar: i, exitBar: i + 5,
    pips: profit, profit, commission: 1, durationBars: 5, partialCloses: [], reason: 'test',
  };
}

console.log('\n=== Report Exporter Tests ===\n');

{
  const csv = exportTradesCSV([trade(1, 20)]);
  assert('RP-01: CSV header', csv.startsWith('id,strategyId'));
  assert('RP-02: CSV row', csv.includes('break-retest'));
}

{
  const trades = [trade(1, 20), trade(2, -10)];
  const stats = computeStatistics(trades, 10000);
  const report = {
    strategyId: 'break-retest',
    symbol: 'EURUSD',
    timeframe: 'H1',
    stats,
    dashboard: buildDashboardCards({ strategyId: 'break-retest', symbol: 'EURUSD', timeframe: 'H1', stats }),
    heatmaps: {},
    trades,
    signalCount: 2,
    durationMs: 100,
    generatedAt: Date.now(),
  };

  const json = exportReportJSON(report);
  assert('RP-03: JSON parseable', JSON.parse(json).strategyId === 'break-retest');

  const html = buildPrintableHTML(report);
  assert('RP-04: HTML title', html.includes('Research Report') || html.includes(Config.APP_NAME));
  assert('RP-05: HTML trades', html.includes('t1'));
}

{
  const stats = computeStatistics([trade(1, 20)], 10000);
  const cards = buildDashboardCards({
    strategyId: 'ema-pullback',
    symbol: 'GBPUSD',
    timeframe: 'H1',
    stats,
  });
  assert('RP-06: Dashboard cards', cards.length === 8);
  assert('RP-07: Net profit card', cards[0].value.includes('20'));
}

console.log(`\n=== Results: ${passed} passed, ${failed} failed ===\n`);
process.exit(failed > 0 ? 1 : 0);
