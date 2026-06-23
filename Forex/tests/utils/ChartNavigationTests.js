/**
 * Chart navigation helpers — trade ? chart highlight.
 * Run: node tests/utils/ChartNavigationTests.js
 */

import { tradeToChartHighlight } from '../../src/utils/chartNavigation.js';

let passed = 0;
let failed = 0;

/**
 * @param {string} name
 * @param {boolean} ok
 */
function assert(name, ok) {
  if (ok) { passed++; console.log(`  ? ${name}`); }
  else { failed++; console.error(`  ? ${name}`); }
}

/** @type {import('../../src/simulation/TradeSimulator.js').TradeResult} */
const sampleTrade = {
  id: 'trade_1',
  signalId: 'sig_1',
  strategyId: 'break-retest',
  symbol: 'EURUSD',
  timeframe: 'H1',
  direction: 'long',
  outcome: 'win',
  exitReason: 'tp',
  entryPrice: 1.0851,
  exitPrice: 1.0871,
  sl: 1.0841,
  tp: 1.0871,
  entryTime: 1_700_000_000_000,
  exitTime: 1_700_003_600_000,
  entryBar: 42,
  exitBar: 46,
  pips: 20,
  profit: 18.5,
  commission: 0,
  durationBars: 4,
  partialCloses: [],
  reason: 'Break & retest long @ 1.0850',
};

/** @type {import('../../src/strategy/Signal.js').Signal} */
const sampleSignal = {
  id: 'sig_1',
  strategyId: 'break-retest',
  pair: 'EURUSD',
  timeframe: 'H1',
  direction: 'long',
  entry: 1.085,
  sl: 1.084,
  tp: 1.087,
  rr: 2,
  reason: 'Break & retest long @ 1.0850',
  time: 1_700_000_000_000,
  screenshotPosition: { timestamp: 1_700_000_000_000, candleIndex: 40 },
  setup: {
    levels: [{ kind: 'break-level', label: 'M?c B&R', price: 1.085 }],
    markers: [{ label: 'Entry', time: 1_700_000_000_000, role: 'entry' }],
    steps: ['Phá level ? retest ? entry'],
  },
};

console.log('\n=== Chart Navigation ===\n');

const fromTrade = tradeToChartHighlight(sampleTrade);
assert('uses trade fill prices', fromTrade.entry === sampleTrade.entryPrice);
assert('uses trade entry time', fromTrade.time === sampleTrade.entryTime);
assert('uses trade entry bar', fromTrade.candleIndex === sampleTrade.entryBar);

const fromSignal = tradeToChartHighlight(sampleTrade, sampleSignal);
assert('keeps setup from source signal', fromSignal.setup === sampleSignal.setup);
assert('overrides entry with simulated fill', fromSignal.entry === sampleTrade.entryPrice);

console.log(`\n=== Chart Navigation: ${passed} passed, ${failed} failed ===\n`);
process.exit(failed > 0 ? 1 : 0);
