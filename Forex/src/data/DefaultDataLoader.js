/**
 * Load bundled default forex datasets on first launch.
 * Files live in data/defaults/ (gzipped JSON from Dukascopy).
 * @module data/DefaultDataLoader
 */

import { datasetKey } from './Candle.js';
import { decompress } from './Compression.js';
import { importFromText } from './DataImporter.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('DefaultDataLoader');

const DEFAULT_DATA_BASE = 'data/defaults';

/**
 * @typedef {Object} DefaultManifest
 * @property {Array<{ symbol: string, timeframe: string, file: string, count?: number }>} datasets
 */

/**
 * Fetch and parse the defaults manifest.
 * @returns {Promise<DefaultManifest|null>}
 */
async function fetchManifest() {
  try {
    const res = await fetch(`${DEFAULT_DATA_BASE}/manifest.json`);
    if (!res.ok) return null;
    return /** @type {DefaultManifest} */ (await res.json());
  } catch (err) {
    log.warn('Could not load default data manifest', err);
    return null;
  }
}

/**
 * Import bundled datasets that are not already in IndexedDB.
 * @param {(symbol: string, timeframe: string, candles: import('./Candle.js').Candle[]) => Promise<import('./Candle.js').DatasetMetadata>} saveCandles
 * @param {() => Promise<import('./Candle.js').DatasetMetadata[]>} listDatasets
 * @returns {Promise<import('./Candle.js').DatasetMetadata[]>}
 */
export async function loadDefaultDatasets(saveCandles, listDatasets) {
  const manifest = await fetchManifest();
  if (!manifest?.datasets?.length) return [];

  const existing = await listDatasets();
  const existingKeys = new Set(existing.map((d) => d.key));
  const loaded = [];

  for (const ds of manifest.datasets) {
    const key = datasetKey(ds.symbol, ds.timeframe);
    if (existingKeys.has(key)) continue;

    try {
      const fileRes = await fetch(`${DEFAULT_DATA_BASE}/${ds.file}`);
      if (!fileRes.ok) {
        log.warn(`Missing default file: ${ds.file}`);
        continue;
      }

      const buffer = new Uint8Array(await fileRes.arrayBuffer());
      const text = await decompress(buffer);
      const jsonName = ds.file.replace(/\.gz$/, '');
      const result = importFromText(text, jsonName, ds.symbol, ds.timeframe);

      if (result.candles.length === 0) {
        log.warn(`No valid candles in ${ds.file}`);
        continue;
      }

      const metadata = await saveCandles(result.symbol, result.timeframe, result.candles);
      loaded.push(metadata);
      log.info(`Seeded ${metadata.symbol} ${metadata.timeframe}: ${metadata.count} candles`);
    } catch (err) {
      log.warn(`Failed to seed ${ds.file}`, err);
    }
  }

  return loaded;
}
