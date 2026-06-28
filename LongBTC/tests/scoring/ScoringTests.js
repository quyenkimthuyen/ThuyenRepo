/**
 * Phase 10 AI scoring tests.
 * Run: node tests/scoring/ScoringTests.js
 */

import { scoreSignal, scoreToGrade, filterByMinScore } from '../../src/scoring/SignalScoreEngine.js';
import { scoreTrend, scoreRR, scoreSession } from '../../src/scoring/ScoreFactors.js';
import { limitChartCandles, uniformSample } from '../../src/performance/CandleSampler.js';

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

/** @returns {import('../../src/data/Candle.js').Candle} */
function candle(i, close) {
  return {
    timestamp: i * 3600000,
    open: close - 0.0005,
    high: close + 0.001,
    low: close - 0.001,
    close,
    volume: 100,
  };
}

/** @returns {import('../../src/strategy/Signal.js').Signal} */
function signal() {
  return {
    id: 's1', time: 50 * 3600000, pair: 'EURUSD', timeframe: 'H1',
    direction: 'long', entry: 1.0860, sl: 1.0840, tp: 1.0900, rr: 2,
    confidence: 50, reason: 'test', screenshotPosition: { candleIndex: 50, timestamp: 50 * 3600000 },
    strategyId: 'break-retest',
  };
}

console.log('\n=== AI Scoring Tests ===\n');

{
  const candles = Array.from({ length: 60 }, (_, i) => candle(i, 1.08 + i * 0.0001));
  const trend = scoreTrend(candles, 55, 'long');
  assert('SC-01: Trend score range', trend >= 0 && trend <= 100);
}

{
  assert('SC-02: RR score high', scoreRR(3) === 100);
  assert('SC-03: Grade A', scoreToGrade(85) === 'A');
}

{
  const london = Date.UTC(2024, 0, 10, 10);
  assert('SC-04: London session', scoreSession(london) === 100);
}

{
  const candles = Array.from({ length: 60 }, (_, i) => candle(i, 1.08 + i * 0.0001));
  const result = scoreSignal(signal(), candles, 1.5);
  assert('SC-05: Score 0-100', result.score >= 0 && result.score <= 100);
  assert('SC-06: Has 8 factors', Object.keys(result.factors).length === 8);
  assert('SC-07: Has grade', ['A', 'B', 'C', 'D', 'F'].includes(result.grade));
}

{
  const big = Array.from({ length: 100000 }, (_, i) => candle(i, 1.08));
  const limited = limitChartCandles(big, 50000);
  assert('SC-08: Chart limit', limited.length === 50000);

  const sampled = uniformSample(big, 1000);
  assert('SC-09: Uniform sample', sampled.length === 1000);
}

{
  const scored = [
    { ...signal(), confidence: 80, scoreBreakdown: { score: 80, grade: 'A', factors: {} } },
    { ...signal(), confidence: 40, scoreBreakdown: { score: 40, grade: 'D', factors: {} } },
  ];
  assert('SC-10: Filter min score', filterByMinScore(scored, 50).length === 1);
}

console.log(`\n=== Results: ${passed} passed, ${failed} failed ===\n`);
process.exit(failed > 0 ? 1 : 0);
