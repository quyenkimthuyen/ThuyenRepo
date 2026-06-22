/**
 * Load bundled default forex datasets on first launch.
 * Files live in data/defaults/ (gzipped JSON from Dukascopy).
 * @module data/DefaultDataLoader
 */

import { datasetKey } from './Candle.js';
import { decompress, isCompressionSupported } from './Compression.js';
import { importFromText } from './DataImporter.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('DefaultDataLoader');

/** Resolve bundled data URLs relative to this module (works with any server root). */
const DEFAULT_DATA_BASE = new URL('../../../data/defaults/', import.meta.url);

/**
 * @typedef {Object} DefaultManifest
 * @property {Array<{ symbol: string, timeframe: string, file: string, count?: number }>} datasets
 */

/**
 * @typedef {Object} DefaultLoadResult
 * @property {import('./Candle.js').DatasetMetadata[]} loaded
 * @property {string[]} errors
 * @property {string[]} skipped
 */

/**
 * Fetch and parse the defaults manifest.
 * @returns {Promise<DefaultManifest|null>}
 */
async function fetchManifest() {
  try {
    const res = await fetch(new URL('manifest.json', DEFAULT_DATA_BASE));
    if (!res.ok) {
      log.warn(`Manifest HTTP ${res.status}`);
      return null;
    }
    return /** @type {DefaultManifest} */ (await res.json());
  } catch (err) {
    log.warn('Could not load default data manifest', err);
    return null;
  }
}

/**
 * @param {import('./Candle.js').DatasetMetadata[]} existing
 * @param {string} symbol
 * @param {string} timeframe
 * @param {(symbol: string, timeframe: string) => Promise<number>} getCandleCount
 * @returns {Promise<boolean>}
 */
async function datasetNeedsSeed(existing, symbol, timeframe, getCandleCount) {
  const key = datasetKey(symbol, timeframe);
  const meta = existing.find((d) => d.key === key);
  if (!meta || meta.count === 0) return true;
  const count = await getCandleCount(symbol, timeframe);
  return count === 0;
}

/**
 * Import bundled datasets that are missing or empty in IndexedDB.
 * @param {(symbol: string, timeframe: string, candles: import('./Candle.js').Candle[]) => Promise<import('./Candle.js').DatasetMetadata>} saveCandles
 * @param {() => Promise<import('./Candle.js').DatasetMetadata[]>} listDatasets
 * @param {(symbol: string, timeframe: string) => Promise<number>} getCandleCount
 * @param {{ force?: boolean }} [options]
 * @returns {Promise<DefaultLoadResult>}
 */
export async function loadDefaultDatasets(saveCandles, listDatasets, getCandleCount, options = {}) {
  /** @type {DefaultLoadResult} */
  const result = { loaded: [], errors: [], skipped: [] };

  if (typeof window !== 'undefined' && window.location.protocol === 'file:') {
    result.errors.push(
      'Opened via file:// — bundled data cannot load. Run from HTTP server: cd Forex && python3 -m http.server 8080'
    );
    return result;
  }

  if (!isCompressionSupported()) {
    result.errors.push(
      'Browser lacks DecompressionStream — cannot read .json.gz bundles. Use Chrome 80+, Edge 80+, Firefox 113+, or Safari 16.4+.'
    );
    return result;
  }

  const manifest = await fetchManifest();
  if (!manifest?.datasets?.length) {
    result.errors.push(
      'Default data manifest not found. Ensure the data/defaults/ folder is deployed and the app is served over HTTP (not file://).'
    );
    return result;
  }

  const existing = await listDatasets();

  for (const ds of manifest.datasets) {
    const key = datasetKey(ds.symbol, ds.timeframe);

    if (!options.force) {
      const needs = await datasetNeedsSeed(existing, ds.symbol, ds.timeframe, getCandleCount);
      if (!needs) {
        result.skipped.push(key);
        continue;
      }
    }

    try {
      const fileRes = await fetch(new URL(ds.file, DEFAULT_DATA_BASE));
      if (!fileRes.ok) {
        const msg = `Missing default file: ${ds.file} (HTTP ${fileRes.status})`;
        log.warn(msg);
        result.errors.push(msg);
        continue;
      }

      const buffer = new Uint8Array(await fileRes.arrayBuffer());
      const text = await decompress(buffer);
      const jsonName = ds.file.replace(/\.gz$/, '');
      const imported = importFromText(text, jsonName, ds.symbol, ds.timeframe);

      if (imported.candles.length === 0) {
        const msg = `No valid candles in ${ds.file}`;
        log.warn(msg);
        result.errors.push(msg);
        continue;
      }

      const metadata = await saveCandles(imported.symbol, imported.timeframe, imported.candles);
      result.loaded.push(metadata);
      log.info(`Seeded ${metadata.symbol} ${metadata.timeframe}: ${metadata.count} candles`);
    } catch (err) {
      const msg = `Failed to seed ${ds.file}: ${err instanceof Error ? err.message : String(err)}`;
      log.warn(msg, err);
      result.errors.push(msg);
    }
  }

  return result;
}
