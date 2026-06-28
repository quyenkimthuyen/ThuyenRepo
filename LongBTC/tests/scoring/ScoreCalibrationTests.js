/**
 * AI score vs simulation outcome calibration.
 * Run: node tests/scoring/ScoreCalibrationTests.js
 */

import {
  joinTradesWithScores,
  summarizeByScoreBucket,
  suggestScoringWeights,
  pearsonCorrelation,
} from '../../src/scoring/ScoreCalibration.js';
import { composeScoreFromFactors } from '../../src/scoring/SignalScoreEngine.js';

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
function trade(id, signalId, outcome, profit) {
  return {
    id,
    signalId,
    strategyId: 'break-retest',
    symbol: 'EURUSD',
    timeframe: 'H1',
    direction: 'long',
    outcome,
    exitReason: outcome === 'win' ? 'tp' : 'sl',
    entryPrice: 1.085,
    exitPrice: outcome === 'win' ? 1.087 : 1.084,
    sl: 1.084,
    tp: 1.087,
    entryTime: 1,
    exitTime: 2,
    entryBar: 1,
    exitBar: 2,
    pips: outcome === 'win' ? 20 : -10,
    profit,
    commission: 0,
    durationBars: 1,
    partialCloses: [],
    reason: 'test',
  };
}

/** @param {string} id @param {number} score @param {import('../../src/scoring/SignalScoreEngine.js').ScoreFactors} factors */
function signal(id, score, factors) {
  return {
    id,
    pair: 'EURUSD',
    timeframe: 'H1',
    direction: 'long',
    entry: 1.085,
    sl: 1.084,
    tp: 1.087,
    rr: 2,
    time: 1,
    strategyId: 'break-retest',
    confidence: score,
    reason: 'test',
    scoreBreakdown: { score, grade: 'B', factors },
  };
}

console.log('\n=== Score Calibration ===\n');

const factorsHigh = {
  trend: 90, momentum: 85, location: 80, volatility: 70,
  priceActionQuality: 88, rr: 80, session: 100, spread: 85,
};
const factorsLow = {
  trend: 30, momentum: 35, location: 40, volatility: 45,
  priceActionQuality: 32, rr: 40, session: 50, spread: 45,
};

const signals = [
  ...Array.from({ length: 6 }, (_, i) => signal(`s${i}`, 85, factorsHigh)),
  ...Array.from({ length: 6 }, (_, i) => signal(`s${i + 6}`, 45, factorsLow)),
];
const trades = [
  ...Array.from({ length: 6 }, (_, i) => trade(`t${i}`, `s${i}`, 'win', 20)),
  ...Array.from({ length: 6 }, (_, i) => trade(`t${i + 6}`, `s${i + 6}`, 'loss', -10)),
];

const joined = joinTradesWithScores(trades, signals);
assert('joins trades to signals', joined.length === 12);

const buckets = summarizeByScoreBucket(joined);
const aBucket = buckets.find((b) => b.min === 80);
const dBucket = buckets.find((b) => b.max === 49);
assert('high score bucket wins more', (aBucket?.winRate ?? 0) > (dBucket?.winRate ?? 0));

assert('pearson perfect positive', pearsonCorrelation([1, 2, 3], [2, 4, 6]) > 0.99);
assert('compose score from factors', composeScoreFromFactors(factorsHigh, {
  trend: 0.5, momentum: 0.5, location: 0, volatility: 0,
  priceActionQuality: 0, rr: 0, session: 0, spread: 0,
}) === 87 || composeScoreFromFactors(factorsHigh, {
  trend: 0.5, momentum: 0.5, location: 0, volatility: 0,
  priceActionQuality: 0, rr: 0, session: 0, spread: 0,
}) === 88);

const suggestion = suggestScoringWeights(joined);
assert('suggests weights object', typeof suggestion.weights.trend === 'number');
assert('fitness improves or holds', suggestion.fitness >= suggestion.baselineFitness - 0.001);

console.log(`\n=== Score Calibration: ${passed} passed, ${failed} failed ===\n`);
process.exit(failed > 0 ? 1 : 0);
