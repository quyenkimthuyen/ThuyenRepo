/**
 * Phase 6 trade engine tests.
 * Run: node tests/simulation/TradeTests.js
 */

import { simulateTrade, summarizeTrades } from '../../src/simulation/TradeSimulator.js';
import { getDefaultTradeConfig } from '../../src/simulation/TradeConfig.js';
import { marketEntryFill, calcPips } from '../../src/simulation/FillModel.js';

const H = 3600000;
let passed = 0;
let failed = 0;

/**
 * @param {number} i
 * @param {number} o
 * @param {number} h
 * @param {number} l
 * @param {number} c
 */
function candle(i, o, h, l, c) {
  return { timestamp: i * H, open: o, high: h, low: l, close: c, volume: 500 };
}

/**
 * @param {string} name
 * @param {boolean} ok
 */
function assert(name, ok) {
  if (ok) { passed++; console.log(`  ✓ ${name}`); }
  else { failed++; console.error(`  ✗ ${name}`); }
}

console.log('\n=== Trade Engine Tests ===\n');

{
  const fill = marketEntryFill(1.0850, 'long', 'EURUSD', 1.5, 0.5);
  assert('TE-01: Long entry includes spread+slippage', fill > 1.0850);
}

{
  const candles = [
    candle(0, 1.0850, 1.0852, 1.0848, 1.0851),
    candle(1, 1.0851, 1.0875, 1.0850, 1.0872),
  ];
  const signal = {
    id: 's1', time: 0, pair: 'EURUSD', timeframe: 'H1', direction: 'long',
    entry: 1.0851, sl: 1.0840, tp: 1.0870, rr: 2, confidence: 50,
    reason: 'test', screenshotPosition: { candleIndex: 0, timestamp: 0 },
    strategyId: 'test',
  };
  const result = simulateTrade(signal, candles, getDefaultTradeConfig());
  assert('TE-02: Long hits TP', result?.exitReason === 'tp' && result.outcome === 'win');
}

{
  const candles = [
    candle(0, 1.0850, 1.0852, 1.0848, 1.0851),
    candle(1, 1.0851, 1.0853, 1.0835, 1.0838),
  ];
  const signal = {
    id: 's2', time: 0, pair: 'EURUSD', timeframe: 'H1', direction: 'long',
    entry: 1.0851, sl: 1.0840, tp: 1.0870, rr: 2, confidence: 50,
    reason: 'test', screenshotPosition: { candleIndex: 0, timestamp: 0 },
    strategyId: 'test',
  };
  const result = simulateTrade(signal, candles, getDefaultTradeConfig());
  assert('TE-03: Long hits SL', result?.exitReason === 'sl' && result.outcome === 'loss');
}

{
  const pips = calcPips(1.0850, 1.0860, 'long', 'EURUSD');
  assert('TE-04: Pip calc 10 pips', Math.abs(pips - 10) < 0.1);
}

{
  const trades = [
    { profit: 20, outcome: 'win', durationBars: 5 },
    { profit: -10, outcome: 'loss', durationBars: 3 },
  ];
  const s = summarizeTrades(trades, 10000);
  assert('TE-05: Summary win rate 50%', s.winRate === 50 && s.netProfit === 10);
}

console.log(`\n=== Results: ${passed} passed, ${failed} failed ===\n`);
process.exit(failed > 0 ? 1 : 0);
