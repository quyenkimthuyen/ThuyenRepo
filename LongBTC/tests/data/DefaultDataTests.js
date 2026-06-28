/**
 * Default bundled BTC data tests — verify files on disk import correctly.
 * Run: node tests/data/DefaultDataTests.js
 */

import { readFileSync, existsSync } from 'fs';
import { gunzipSync } from 'zlib';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { createSuite, header, footer } from '../harness.js';
import { importFromText } from '../../src/data/DataImporter.js';
import { FALLBACK_SEEDS } from '../../src/data/fallbackSeed.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '../..');
const DEFAULTS = join(ROOT, 'data/defaults');

const BTC_TIMEFRAMES = ['H4', 'D1', 'W'];

/**
 * Read dataset file (plain JSON or gzip).
 * @param {string} symbol
 * @param {string} tf
 * @returns {string|null}
 */
function readDatasetText(symbol, tf) {
  const jsonPath = join(DEFAULTS, `${symbol}_${tf}.json`);
  const gzPath = join(DEFAULTS, `${symbol}_${tf}.json.gz`);
  if (existsSync(jsonPath)) return readFileSync(jsonPath, 'utf8');
  if (existsSync(gzPath)) return gunzipSync(readFileSync(gzPath)).toString();
  return null;
}

const s = createSuite('Default Data');
header('Default Data');

{
  const manifestPath = join(DEFAULTS, 'manifest.json');
  s.assert('DD-01: manifest.json exists', existsSync(manifestPath));
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  s.assert('DD-02: manifest has BTC datasets', manifest.datasets?.length === 3);
  s.assert('DD-03: only BTCUSD in manifest', manifest.datasets.every((d) => d.symbol === 'BTCUSD'));
  s.assert('DD-03b: BTCUSD H4 in manifest', manifest.datasets.some((d) => d.symbol === 'BTCUSD' && d.timeframe === 'H4'));
  s.assert('DD-03c: BTCUSD D1 in manifest', manifest.datasets.some((d) => d.symbol === 'BTCUSD' && d.timeframe === 'D1'));
  s.assert('DD-03d: BTCUSD W in manifest', manifest.datasets.some((d) => d.symbol === 'BTCUSD' && d.timeframe === 'W'));
}

for (const tf of BTC_TIMEFRAMES) {
  const text = readDatasetText('BTCUSD', tf);
  s.assert(`DD-file-${tf}: BTCUSD ${tf} exists`, text != null);
  if (text) {
    const result = importFromText(text, `BTCUSD_${tf}.json`, 'BTCUSD', tf);
    s.assert(`DD-import-${tf}`, result.candles.length > 100);
  }
}

{
  const h4Text = readDatasetText('BTCUSD', 'H4');
  s.assert('DD-04: H4 has substantial history', h4Text != null && importFromText(h4Text, 'BTCUSD_H4.json', 'BTCUSD', 'H4').candles.length > 1000);
}

{
  s.assert('DD-05: Fallback seed present', FALLBACK_SEEDS.length > 0);
  s.assert('DD-06: Fallback BTCUSD W', FALLBACK_SEEDS[0].symbol === 'BTCUSD' && FALLBACK_SEEDS[0].candles.length >= 50);
}

process.exit(footer(s.finish()));
