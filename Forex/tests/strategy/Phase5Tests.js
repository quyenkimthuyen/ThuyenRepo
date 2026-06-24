/**
 * Phase 5 strategy test cases per STRATEGY_SPECIFICATION.md §7.
 * Run: node tests/strategy/run.mjs
 */

import { BreakRetestStrategy } from '../../src/strategies/BreakRetestStrategy.js';
import { EMAPullbackStrategy } from '../../src/strategies/EMAPullbackStrategy.js';
import { LiquidityGrabStrategy } from '../../src/strategies/LiquidityGrabStrategy.js';
import { InsideBarBreakoutStrategy } from '../../src/strategies/InsideBarBreakoutStrategy.js';
import { PinBarRejectionStrategy } from '../../src/strategies/PinBarRejectionStrategy.js';
import { WyckoffSpringUtadStrategy } from '../../src/strategies/WyckoffSpringUtadStrategy.js';
import { WyckoffRangeTestStrategy } from '../../src/strategies/WyckoffRangeTestStrategy.js';
import { createContext } from '../../src/strategy/StrategyContext.js';

const H = 3600000;
let passed = 0;
let failed = 0;

/**
 * @param {number} i
 * @param {number} o
 * @param {number} h
 * @param {number} l
 * @param {number} c
 * @param {number} [vol]
 * @returns {import('../../src/data/Candle.js').Candle}
 */
function c(i, o, h, l, close, vol = 500) {
  return { timestamp: i * H, open: o, high: h, low: l, close, volume: vol };
}

/**
 * @param {import('../../src/strategy/BaseStrategy.js').BaseStrategy} strategy
 * @param {import('../../src/data/Candle.js').Candle[]} candles
 * @param {string} symbol
 * @param {Record<string, unknown>} [paramOverrides]
 * @returns {import('../../src/strategy/Signal.js').Signal[]}
 */
function runScan(strategy, candles, symbol = 'EURUSD', paramOverrides = {}) {
  strategy.initialize(strategy.getParameterSchema().reduce((p, d) => {
    p[d.key] = paramOverrides[d.key] ?? d.default;
    return p;
  }, {}));
  strategy.setRunContext({ symbol, timeframe: 'H1' });

  const signals = [];
  const warmup = strategy.getWarmupBars();

  for (let i = 0; i < candles.length; i++) {
    strategy.calculate(candles, i);
    if (i < warmup) continue;
    const ctx = createContext(symbol, 'H1', candles, i, strategy.getParams());
    const sig = strategy.generateSignal(ctx);
    if (sig && strategy.validate(sig)) signals.push(sig);
  }

  return signals;
}

/**
 * @param {string} name
 * @param {boolean} condition
 */
function assert(name, condition) {
  if (condition) {
    passed++;
    console.log(`  ✓ ${name}`);
  } else {
    failed++;
    console.error(`  ✗ ${name}`);
  }
}

console.log('\n=== Break & Retest Tests ===\n');

{
  const candles = [];
  for (let i = 0; i < 30; i++) {
    candles.push(c(i, 1.0840, 1.0845, 1.0838, 1.0842));
  }
  candles.push(c(30, 1.0848, 1.08502, 1.0847, 1.08495));
  const signals = runScan(new BreakRetestStrategy(), candles);
  assert('BR-01: Breakout không đủ pips → no signal', signals.length === 0);
}

{
  const candles = [];
  for (let i = 0; i < 95; i++) {
    candles.push(c(i, 1.0840, 1.0845, 1.0838, 1.0842));
  }
  for (let i = 95; i < 100; i++) {
    candles.push(c(i, 1.0840, 1.0845, 1.0838, 1.0840));
  }
  candles.push(c(100, 1.0848, 1.08520, 1.0847, 1.08512));
  for (let i = 101; i < 103; i++) {
    candles.push(c(i, 1.0850, 1.0852, 1.0848, 1.0851));
  }
  candles.push(c(103, 1.0849, 1.08510, 1.08440, 1.08500));
  const signals = runScan(new BreakRetestStrategy(), candles);
  assert('BR-02: Breakout + retest → 1 LONG', signals.length === 1 && signals[0].direction === 'long');
}

{
  const candles = [];
  for (let i = 0; i < 95; i++) candles.push(c(i, 1.0840, 1.0845, 1.0838, 1.0842));
  for (let i = 95; i < 100; i++) candles.push(c(i, 1.0840, 1.0845, 1.0838, 1.0840));
  candles.push(c(100, 1.0848, 1.08520, 1.0847, 1.08512));
  for (let i = 101; i <= 112; i++) {
    candles.push(c(i, 1.0850, 1.0853, 1.0849, 1.0852));
  }
  const signals = runScan(new BreakRetestStrategy(), candles);
  assert('BR-03: Quá retestMaxBars → no signal', signals.length === 0);
}

{
  const candles = [];
  for (let i = 0; i < 95; i++) candles.push(c(i, 1.0840, 1.0845, 1.0838, 1.0842));
  for (let i = 95; i < 100; i++) candles.push(c(i, 1.0840, 1.0845, 1.0838, 1.0840));
  candles.push(c(100, 1.0848, 1.08520, 1.0840, 1.08512));
  candles.push(c(101, 1.0850, 1.0851, 1.0835, 1.0838));
  const signals = runScan(new BreakRetestStrategy(), candles);
  assert('BR-04: Invalidation → no signal', signals.length === 0);
}

console.log('\n=== Liquidity Grab Tests ===\n');

const LG_PAD = 25;

{
  const candles = [];
  for (let i = 0; i < LG_PAD + 20; i++) candles.push(c(i, 1.0855, 1.0860, 1.0853, 1.0858));
  candles.push(c(LG_PAD + 20, 1.0860, 1.08635, 1.0859, 1.08610));
  const signals = runScan(new LiquidityGrabStrategy(), candles);
  assert('LG-01: Sweep but close above level → no short', signals.filter((s) => s.direction === 'short').length === 0);
}

{
  const candles = [];
  for (let i = 0; i < LG_PAD + 20; i++) candles.push(c(i, 1.0855, 1.0860, 1.0853, 1.0858));
  candles.push(c(LG_PAD + 20, 1.08575, 1.08635, 1.08550, 1.08560, 600));
  const signals = runScan(new LiquidityGrabStrategy(), candles);
  const shorts = signals.filter((s) => s.direction === 'short');
  assert('LG-02: Sweep + close below + wick → 1 SHORT', shorts.length === 1);
}

{
  const candles = [];
  for (let i = 0; i < LG_PAD + 20; i++) candles.push(c(i, 1.0855, 1.0860, 1.0853, 1.0858));
  candles.push(c(LG_PAD + 20, 1.08600, 1.08632, 1.08568, 1.08570, 600));
  const signals = runScan(new LiquidityGrabStrategy(), candles);
  assert('LG-03: Wick ratio too small → no signal', signals.length === 0);
}

{
  const candles = [];
  for (let i = 0; i < LG_PAD + 20; i++) candles.push(c(i, 1.0845, 1.0848, 1.0840, 1.0845));
  candles.push(c(LG_PAD + 20, 1.08400, 1.08420, 1.08365, 1.08415, 600));
  const signals = runScan(new LiquidityGrabStrategy(), candles);
  const longs = signals.filter((s) => s.direction === 'long');
  assert('LG-04: Bullish grab → 1 LONG', longs.length === 1);
}

{
  const candles = [];
  for (let i = 0; i < LG_PAD + 20; i++) candles.push(c(i, 1.0855, 1.0860, 1.0853, 1.0858));
  candles.push(c(LG_PAD + 20, 1.08575, 1.08635, 1.08550, 1.08560, 600));
  candles.push(c(LG_PAD + 21, 1.08570, 1.08632, 1.08545, 1.08555, 600));
  const signals = runScan(new LiquidityGrabStrategy(), candles);
  assert('LG-05: Duplicate level → 1 signal only', signals.length === 1);
}

console.log('\n=== EMA Pullback Tests ===\n');

{
  const candles = [];
  let price = 1.0800;
  for (let i = 0; i < 80; i++) {
    price -= 0.0001;
    candles.push(c(i, price, price + 0.0003, price - 0.0003, price - 0.00005));
  }
  const signals = runScan(new EMAPullbackStrategy(), candles);
  assert('EP-01: Downtrend data → no long signals', signals.filter((s) => s.direction === 'long').length === 0);
}

console.log('\n=== Inside Bar Breakout Tests ===\n');

const IB_PARAMS = { trendEma: 20, motherMinRangePips: 10, breakoutBufferPips: 1, maxWaitBars: 3, rr: 2 };

/**
 * @param {number} count
 * @returns {import('../../src/data/Candle.js').Candle[]}
 */
function uptrendCandles(count) {
  const candles = [];
  for (let i = 0; i < count; i++) {
    const price = 1.0800 + i * 0.0002;
    candles.push(c(i, price, price + 0.0003, price - 0.0002, price + 0.0001));
  }
  return candles;
}

{
  const candles = uptrendCandles(32);
  candles[30] = c(30, 1.0860, 1.0864, 1.0858, 1.0862);
  candles[31] = c(31, 1.0861, 1.0863, 1.0859, 1.0862);
  candles.push(c(32, 1.0862, 1.0866, 1.0860, 1.0865));
  const signals = runScan(new InsideBarBreakoutStrategy(), candles, 'EURUSD', IB_PARAMS);
  assert('IB-01: Mother range too small → no signal', signals.length === 0);
}

{
  const candles = uptrendCandles(32);
  candles[30] = c(30, 1.0860, 1.0880, 1.0850, 1.0870);
  candles[31] = c(31, 1.0870, 1.0875, 1.0860, 1.0872);
  candles.push(c(32, 1.0875, 1.0885, 1.0870, 1.0882));
  const signals = runScan(new InsideBarBreakoutStrategy(), candles, 'EURUSD', IB_PARAMS);
  assert('IB-02: Inside bar + bullish breakout → 1 LONG', signals.length === 1 && signals[0].direction === 'long');
}

{
  const candles = [];
  for (let i = 0; i < 32; i++) {
    const price = 1.1000 - i * 0.0002;
    candles.push(c(i, price, price + 0.0002, price - 0.0003, price - 0.0001));
  }
  candles[30] = c(30, 1.0940, 1.0950, 1.0920, 1.0930);
  candles[31] = c(31, 1.0930, 1.0945, 1.0925, 1.0935);
  candles.push(c(32, 1.0930, 1.0935, 1.0910, 1.0915));
  const signals = runScan(new InsideBarBreakoutStrategy(), candles, 'EURUSD', IB_PARAMS);
  assert('IB-03: Inside bar + bearish breakout → 1 SHORT', signals.length === 1 && signals[0].direction === 'short');
}

{
  const candles = uptrendCandles(32);
  candles[30] = c(30, 1.0860, 1.0880, 1.0850, 1.0870);
  candles[31] = c(31, 1.0870, 1.0875, 1.0860, 1.0872);
  for (let i = 32; i <= 35; i++) {
    candles.push(c(i, 1.0870, 1.0878, 1.0868, 1.0875));
  }
  const signals = runScan(new InsideBarBreakoutStrategy(), candles, 'EURUSD', IB_PARAMS);
  assert('IB-04: No breakout within maxWaitBars → no signal', signals.length === 0);
}

console.log('\n=== Pin Bar Rejection Tests ===\n');

const PB_PAD = 25;

{
  const candles = [];
  for (let i = 0; i < PB_PAD + 20; i++) candles.push(c(i, 1.0855, 1.0860, 1.0853, 1.0858));
  candles.push(c(PB_PAD + 20, 1.0856, 1.0862, 1.0850, 1.0858, 600));
  const signals = runScan(new PinBarRejectionStrategy(), candles);
  assert('PB-01: Touch swing but body too large → no short', signals.filter((s) => s.direction === 'short').length === 0);
}

{
  const candles = [];
  for (let i = 0; i < PB_PAD + 20; i++) candles.push(c(i, 1.0855, 1.0860, 1.0853, 1.0858));
  candles.push(c(PB_PAD + 20, 1.0855, 1.0863, 1.0850, 1.0851, 600));
  const signals = runScan(new PinBarRejectionStrategy(), candles);
  assert('PB-02: Bearish pin at swing high → 1 SHORT', signals.filter((s) => s.direction === 'short').length === 1);
}

{
  const candles = [];
  for (let i = 0; i < PB_PAD + 20; i++) candles.push(c(i, 1.0845, 1.0848, 1.0840, 1.0845));
  candles.push(c(PB_PAD + 20, 1.0841, 1.0845, 1.0836, 1.0844, 600));
  const signals = runScan(new PinBarRejectionStrategy(), candles);
  assert('PB-03: Bullish pin at swing low → 1 LONG', signals.filter((s) => s.direction === 'long').length === 1);
}

{
  const candles = [];
  for (let i = 0; i < PB_PAD + 20; i++) candles.push(c(i, 1.0855, 1.0860, 1.0853, 1.0858));
  candles.push(c(PB_PAD + 20, 1.0858, 1.0862, 1.0854, 1.0856, 600));
  const signals = runScan(new PinBarRejectionStrategy(), candles);
  assert('PB-04: Wick too small → no signal', signals.length === 0);
}

{
  const candles = [];
  for (let i = 0; i < PB_PAD + 20; i++) candles.push(c(i, 1.0855, 1.0860, 1.0853, 1.0858));
  candles.push(c(PB_PAD + 20, 1.0854, 1.0860, 1.0850, 1.0851, 600));
  candles.push(c(PB_PAD + 21, 1.0853, 1.0860, 1.0849, 1.0850, 600));
  const signals = runScan(new PinBarRejectionStrategy(), candles);
  assert('PB-05: Duplicate swing level → 1 signal only', signals.length === 1);
}

console.log('\n=== Wyckoff Spring / UTAD Tests ===\n');

const WY_SPRING_PARAMS = {
  rangeLookback: 15,
  minRangePips: 8,
  minInsideRatio: 0.6,
  sweepPips: 2,
  wickRatio: 0.5,
  rr: 2,
};

/**
 * @param {number} n
 * @param {number} [low]
 * @param {number} [high]
 * @returns {import('../../src/data/Candle.js').Candle[]}
 */
function buildConsolidationRange(n, low = 1.0850, high = 1.0865) {
  const candles = [];
  for (let i = 0; i < n; i++) {
    if (i % 2 === 0) {
      candles.push(c(i, 1.0863, high, high - 0.0005, 1.0862));
    } else {
      candles.push(c(i, 1.0852, low + 0.0005, low, 1.0853));
    }
  }
  return candles;
}

{
  const candles = buildConsolidationRange(30);
  candles.push(c(30, 1.0852, 1.0854, 1.08475, 1.0848));
  const signals = runScan(new WyckoffSpringUtadStrategy(), candles, 'EURUSD', WY_SPRING_PARAMS);
  assert('WS-01: Spring sweep but close below range → no long', signals.filter((s) => s.direction === 'long').length === 0);
}

{
  const candles = buildConsolidationRange(30);
  candles.push(c(30, 1.08525, 1.0855, 1.08475, 1.0854, 600));
  const signals = runScan(new WyckoffSpringUtadStrategy(), candles, 'EURUSD', WY_SPRING_PARAMS);
  assert('WS-02: Valid spring in range → 1 LONG', signals.filter((s) => s.direction === 'long').length === 1);
}

{
  const candles = buildConsolidationRange(30);
  candles.push(c(30, 1.0864, 1.08675, 1.0862, 1.08625, 600));
  const signals = runScan(new WyckoffSpringUtadStrategy(), candles, 'EURUSD', WY_SPRING_PARAMS);
  assert('WS-03: Valid UTAD in range → 1 SHORT', signals.filter((s) => s.direction === 'short').length === 1);
}

{
  const candles = [];
  for (let i = 0; i < 35; i++) {
    const price = 1.0800 + i * 0.0003;
    candles.push(c(i, price, price + 0.0002, price - 0.0001, price + 0.00015));
  }
  const signals = runScan(new WyckoffSpringUtadStrategy(), candles, 'EURUSD', WY_SPRING_PARAMS);
  assert('WS-04: Trending market (no consolidation) → no signal', signals.length === 0);
}

console.log('\n=== Wyckoff Range Test Tests ===\n');

const WY_TEST_PARAMS = {
  rangeLookback: 15,
  minRangePips: 8,
  minInsideRatio: 0.6,
  sweepPips: 2,
  testMaxBars: 6,
  testTolerancePips: 3,
  rallyMinPips: 5,
  eventWickRatio: 0.5,
  testWickRatio: 0.4,
  rr: 2,
};

{
  const candles = buildConsolidationRange(30);
  candles.push(c(30, 1.08525, 1.0855, 1.08475, 1.0854, 600));
  candles.push(c(31, 1.0855, 1.0868, 1.0854, 1.0866));
  candles.push(c(32, 1.0853, 1.0855, 1.0847, 1.0849));
  const signals = runScan(new WyckoffRangeTestStrategy(), candles, 'EURUSD', WY_TEST_PARAMS);
  assert('WT-01: Test breaks spring low → no long', signals.filter((s) => s.direction === 'long').length === 0);
}

{
  const candles = buildConsolidationRange(30);
  candles.push(c(30, 1.08525, 1.0855, 1.08475, 1.0854, 600));
  candles.push(c(31, 1.0855, 1.0870, 1.0854, 1.0868));
  candles.push(c(32, 1.0865, 1.0868, 1.0858, 1.0866));
  candles.push(c(33, 1.0854, 1.0856, 1.08515, 1.0855, 600));
  const signals = runScan(new WyckoffRangeTestStrategy(), candles, 'EURUSD', WY_TEST_PARAMS);
  assert('WT-02: Spring + rally + higher-low test → 1 LONG', signals.filter((s) => s.direction === 'long').length === 1);
}

{
  const candles = buildConsolidationRange(30);
  candles.push(c(30, 1.08525, 1.0855, 1.08475, 1.0854, 600));
  candles.push(c(31, 1.08535, 1.08542, 1.08525, 1.0853, 600));
  const signals = runScan(new WyckoffRangeTestStrategy(), candles, 'EURUSD', WY_TEST_PARAMS);
  assert('WT-03: No rally before test → no signal', signals.length === 0);
}

console.log(`\n=== Results: ${passed} passed, ${failed} failed ===\n`);
process.exit(failed > 0 ? 1 : 0);
