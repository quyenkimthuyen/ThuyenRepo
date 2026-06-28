/**
 * LongBTC analysis engine tests.
 * Run: node tests/analysis/AnalysisTests.js
 */

import { createSuite, header, footer } from '../harness.js';
import { analyzeLongTerm } from '../../src/analysis/LongTermAnalysisEngine.js';
import { detectSwingPivots } from '../../src/analysis/SwingPivotDetector.js';
import { analyzeCurrentCycle } from '../../src/analysis/HalvingCycleAnalyzer.js';

const s = createSuite('Analysis Engine');
header('Analysis Engine');

/**
 * Build synthetic weekly BTC-like candles.
 * @param {number} count
 */
function buildSyntheticCandles(count) {
  const candles = [];
  let price = 10000;
  let ts = Date.parse('2019-01-01T00:00:00Z');

  for (let i = 0; i < count; i++) {
    const drift = Math.sin(i / 20) * 0.08 + (i > count * 0.6 ? -0.02 : 0.03);
    const open = price;
    price = Math.max(3000, price * (1 + drift));
    const high = Math.max(open, price) * 1.02;
    const low = Math.min(open, price) * 0.98;
    candles.push({
      timestamp: ts,
      open,
      high,
      low,
      close: price,
      volume: 1000,
    });
    ts += 7 * 24 * 60 * 60 * 1000;
  }
  return candles;
}

{
  const cycle = analyzeCurrentCycle(Date.parse('2021-06-01T00:00:00Z'));
  s.assert('AC-01: cycle phase in 2021', cycle.phase === 'markup' || cycle.phase === 'distribution');
  s.assert('AC-02: halving index', cycle.halvingIndex >= 2);

  const candles = buildSyntheticCandles(120);
  const pivots = detectSwingPivots(candles, { reversalPct: 0.05, minBars: 2 });
  s.assert('AC-03: pivots detected', pivots.length >= 2);

  const result = analyzeLongTerm(candles, { symbol: 'BTCUSD', timeframe: 'W' });
  s.assert('AC-04: has summary', result.summary.length > 20);
  s.assert('AC-05: has psychology', result.psychology.labelVi.length > 0);
  s.assert('AC-06: has segments', result.segments.length > 0);
  s.assert('AC-07: historical cycles', result.historicalCycles.length >= 1);
}

process.exit(footer(s.finish()));
