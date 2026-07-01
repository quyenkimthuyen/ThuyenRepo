/**
 * DCA backtest + cycle price compare tests.
 * Run: node tests/analysis/DcaBacktestTests.js
 */

import { readFileSync, existsSync } from 'fs';
import { gunzipSync } from 'zlib';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createSuite, header, footer } from '../harness.js';
import {
  runDcaBacktest,
  collectMonthlyBuyCandles,
  simulateDcaPath,
  phaseMultiplierAt,
  DEFAULT_DCA_BACKTEST_START,
} from '../../src/analysis/DcaBacktestEngine.js';
import {
  buildHalvingCycleCompare,
  snapshotAtCycleProgress,
} from '../../src/analysis/CycleCompareTimeline.js';
import { importFromText } from '../../src/data/DataImporter.js';
import { BTC_HALVING_EVENTS } from '../../src/analysis/BtcCycleConfig.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '../..');

const s = createSuite('DCA Backtest');
header('DCA Backtest');

/** @returns {import('../../src/data/Candle.js').Candle[]} */
function loadWeeklyBtc() {
  const gzPath = join(ROOT, 'data/defaults/BTCUSD_W.json.gz');
  const jsonPath = join(ROOT, 'data/defaults/BTCUSD_W.json');
  const text = existsSync(gzPath)
    ? gunzipSync(readFileSync(gzPath)).toString()
    : existsSync(jsonPath)
      ? readFileSync(jsonPath, 'utf8')
      : null;
  if (!text) return [];
  return importFromText(text, 'BTCUSD_W.json', 'BTCUSD', 'W').candles;
}

const weekMs = 7 * 24 * 60 * 60 * 1000;

/** @returns {import('../../src/data/Candle.js').Candle[]} */
function syntheticWeekly(count, startTs = Date.parse('2017-01-01T00:00:00Z')) {
  /** @type {import('../../src/data/Candle.js').Candle[]} */
  const candles = [];
  let price = 1000;
  for (let i = 0; i < count; i++) {
    const open = price;
    price *= 1.01;
    candles.push({
      timestamp: startTs + i * weekMs,
      open,
      high: price * 1.01,
      low: open * 0.99,
      close: price,
      volume: 100,
    });
  }
  return candles;
}

{
  const candles = syntheticWeekly(80);
  const buys = collectMonthlyBuyCandles(candles, DEFAULT_DCA_BACKTEST_START);
  s.assert('DB-01: monthly buys', buys.length >= 18);
}

{
  const candles = syntheticWeekly(60, Date.parse('2015-01-01T00:00:00Z'));
  const blind = simulateDcaPath(
    collectMonthlyBuyCandles(candles, Date.parse('2016-01-01T00:00:00Z')),
    candles,
    'blind',
    100
  );
  s.assert('DB-02: blind invests', blind.totalInvested > 0);
  s.assert('DB-03: blind btc', blind.btcHeld > 0);
  s.assert('DB-04: blind return positive uptrend', blind.returnPct > 0);
}

{
  const candles = loadWeeklyBtc();
  if (candles.length > 100) {
    const report = runDcaBacktest(candles, { monthlyBudgetUsd: 500 });
    s.assert('DB-05: real data ok', report.ok === true);
    s.assert('DB-06: many months', report.monthCount > 60);
    s.assert('DB-07: blind invested', report.blind.totalInvested > 0);
    s.assert('DB-08: phase invested', report.phase.totalInvested > 0);
    s.assert('DB-09: phase avg cost differs or same', typeof report.phase.avgCostUsd === 'number');
    s.assert('DB-10: curves', report.blind.curve.length === report.monthCount);

    const cmp = buildHalvingCycleCompare(candles);
    s.assert('DB-11: price rows', cmp.rows.every((r) => r.markerPrice != null));
    s.assert('DB-12: prices positive', cmp.rows.every((r) => (r.markerPrice?.price ?? 0) > 0));

    const h2snap = snapshotAtCycleProgress(candles, 1, 30);
    s.assert('DB-13: 2016 snapshot', h2snap != null && h2snap.price > 0);
  } else {
    s.assert('DB-05: skip no bundled W', true);
  }
}

{
  const ts = BTC_HALVING_EVENTS[2].timestamp + 200 * 24 * 60 * 60 * 1000;
  const candles = loadWeeklyBtc();
  if (candles.length > 50) {
    const mult = phaseMultiplierAt(ts, candles);
    s.assert('DB-14: multiplier range', mult >= 0 && mult <= 1.5);
  }
}

footer(s.finish());
