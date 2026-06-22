/**
 * Default bundled data tests — verify files on disk import correctly.
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

const s = createSuite('Default Data');
header('Default Data');

{
  const manifestPath = join(DEFAULTS, 'manifest.json');
  s.assert('DD-01: manifest.json exists', existsSync(manifestPath));
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  s.assert('DD-02: manifest has datasets', manifest.datasets?.length >= 8);
  s.assert('DD-03: EURUSD H1 in manifest', manifest.datasets.some((d) => d.symbol === 'EURUSD' && d.timeframe === 'H1'));
}

for (const tf of ['H1', 'H4', 'D1', 'W']) {
  const gzPath = join(DEFAULTS, `EURUSD_${tf}.json.gz`);
  const jsonPath = join(DEFAULTS, `EURUSD_${tf}.json`);
  s.assert(`DD-gz-${tf}: gzip file exists`, existsSync(gzPath));
  s.assert(`DD-json-${tf}: plain json exists`, existsSync(jsonPath));

  const gzText = gunzipSync(readFileSync(gzPath)).toString();
  const gzResult = importFromText(gzText, `EURUSD_${tf}.json`, 'EURUSD', tf);
  s.assert(`DD-import-gz-${tf}`, gzResult.candles.length > 0);

  const jsonText = readFileSync(jsonPath, 'utf8');
  const jsonResult = importFromText(jsonText, `EURUSD_${tf}.json`, 'EURUSD', tf);
  s.assert(`DD-import-json-${tf}`, jsonResult.candles.length === gzResult.candles.length);
}

{
  s.assert('DD-04: H1 has substantial history', (() => {
    const text = gunzipSync(readFileSync(join(DEFAULTS, 'EURUSD_H1.json.gz'))).toString();
    return importFromText(text, 'EURUSD_H1.json', 'EURUSD', 'H1').candles.length > 10000;
  })());
}

{
  s.assert('DD-05: Fallback seed present', FALLBACK_SEEDS.length > 0);
  s.assert('DD-06: Fallback EURUSD H1', FALLBACK_SEEDS[0].candles.length >= 100);
}

process.exit(footer(s.finish()));
