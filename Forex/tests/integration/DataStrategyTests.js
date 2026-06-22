/**
 * Real default data → strategy integration test.
 * Ensures bundled EURUSD H1 can be scanned (the user-reported failure path).
 * Run: node tests/integration/DataStrategyTests.js
 */

import { readFileSync } from 'fs';
import { gunzipSync } from 'zlib';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createSuite, header, footer } from '../harness.js';
import { importFromText } from '../../src/data/DataImporter.js';
import { registerBuiltinStrategies } from '../../src/strategies/index.js';
import { runBacktest } from '../../src/optimizer/BacktestRunner.js';
import { getDefaultTradeConfig } from '../../src/simulation/TradeConfig.js';
import { mergeCandles } from '../../src/data/CandleMerge.js';
import { FALLBACK_SEEDS } from '../../src/data/fallbackSeed.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '../..');

const s = createSuite('Data → Strategy Integration');
header('Data → Strategy Integration');

registerBuiltinStrategies();
const tradeConfig = getDefaultTradeConfig();
const params = { breakoutPips: 5, retestMaxBars: 10, rr: 2, swingLookback: 5 };

function loadBundled(symbol, tf) {
  const path = join(ROOT, 'data/defaults', `${symbol}_${tf}.json.gz`);
  const text = gunzipSync(readFileSync(path)).toString();
  return importFromText(text, `${symbol}_${tf}.json`, symbol, tf).candles;
}

{
  const candles = loadBundled('EURUSD', 'H1').slice(0, 3000);
  s.assert('DS-01: Load EURUSD H1 from disk', candles.length === 3000);
  const bt = runBacktest('break-retest', 'EURUSD', 'H1', candles, params, tradeConfig);
  s.assert('DS-02: Strategy scan on real H1 data', bt.barsScanned > 0);
  s.assert('DS-03: No throw on empty signals', Array.isArray(bt.signals));
}

{
  const h1 = loadBundled('EURUSD', 'H1').slice(0, 500);
  const h4 = loadBundled('EURUSD', 'H4').slice(0, 200);
  s.assert('DS-04: Load EURUSD H4', h4.length === 200);
  const bt4 = runBacktest('break-retest', 'EURUSD', 'H4', h4, params, tradeConfig);
  s.assert('DS-05: Strategy on H4', bt4.barsScanned > 0);
  const merged = mergeCandles(h1, []);
  s.assert('DS-06: Merge preserves count', merged.length === 500);
}

{
  const fallback = FALLBACK_SEEDS[0].candles;
  const bt = runBacktest('break-retest', 'EURUSD', 'H1', fallback, params, tradeConfig);
  s.assert('DS-07: Fallback seed scannable', bt.barsScanned > 0);
}

{
  const candles = loadBundled('GBPUSD', 'H1').slice(0, 2000);
  const bt = runBacktest('break-retest', 'GBPUSD', 'H1', candles, params, tradeConfig);
  s.assert('DS-08: GBPUSD H1 scan', bt.barsScanned > 0);
}

process.exit(footer(s.finish()));
