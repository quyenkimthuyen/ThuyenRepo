/**
 * Load bundled default forex datasets on first launch.
 * Files live in data/defaults/ (gzipped or plain JSON from Dukascopy).
 * @module data/DefaultDataLoader
 */

import { datasetKey } from './Candle.js';
import { decompress, isCompressionSupported } from './Compression.js';
import { importFromText } from './DataImporter.js';
import { createLogger } from '../utils/logger.js';
import { FALLBACK_SEEDS } from './fallbackSeed.js';

const log = createLogger('DefaultDataLoader');

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
 * Candidate base URLs for data/defaults (module path + page path fallbacks).
 * @returns {string[]}
 */
function getCandidateBases() {
  const bases = new Set();
  try {
    bases.add(new URL('../../../data/defaults/', import.meta.url).href);
  } catch { /* ignore */ }
  if (typeof document !== 'undefined') {
    try {
      bases.add(new URL('data/defaults/', document.baseURI).href);
    } catch { /* ignore */ }
  }
  if (typeof window !== 'undefined') {
    try {
      bases.add(new URL('data/defaults/', window.location.href).href);
    } catch { /* ignore */ }
  }
  return [...bases];
}

/**
 * @param {string} path
 * @returns {Promise<Response|null>}
 */
async function fetchFirst(path) {
  for (const base of getCandidateBases()) {
    try {
      const res = await fetch(new URL(path, base));
      if (res.ok) return res;
      log.warn(`HTTP ${res.status} for ${new URL(path, base).href}`);
    } catch (err) {
      log.warn(`Fetch failed for ${path} at ${base}`, err);
    }
  }
  return null;
}

/**
 * Fetch and parse the defaults manifest.
 * @returns {Promise<DefaultManifest|null>}
 */
async function fetchManifest() {
  const res = await fetchFirst('manifest.json');
  if (!res) return null;
  try {
    return /** @type {DefaultManifest} */ (await res.json());
  } catch (err) {
    log.warn('Invalid manifest JSON', err);
    return null;
  }
}

/**
 * Load dataset bytes + logical filename for importFromText.
 * @param {string} gzipFile
 * @returns {Promise<{ text: string, filename: string }|null>}
 */
async function loadDatasetText(gzipFile) {
  const plainFile = gzipFile.replace(/\.gz$/, '');

  if (isCompressionSupported()) {
    const gzRes = await fetchFirst(gzipFile);
    if (gzRes) {
      try {
        const buffer = new Uint8Array(await gzRes.arrayBuffer());
        const text = await decompress(buffer);
        return { text, filename: plainFile };
      } catch (err) {
        log.warn(`Gzip decompress failed for ${gzipFile}`, err);
      }
    }
  }

  const jsonRes = await fetchFirst(plainFile);
  if (jsonRes) {
    try {
      return { text: await jsonRes.text(), filename: plainFile };
    } catch (err) {
      log.warn(`Plain JSON read failed for ${plainFile}`, err);
    }
  }

  return null;
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
      'Opened via file:// — data cannot load. Run: cd Forex && python3 -m http.server 8080 then open http://localhost:8080'
    );
    return result;
  }

  const manifest = await fetchManifest();
  if (!manifest?.datasets?.length) {
    const bases = getCandidateBases().join(' | ');
    result.errors.push(
      `Cannot reach data/defaults/manifest.json. Tried: ${bases}. Copy the full Forex folder including data/defaults/.`
    );
  }

  const existing = await listDatasets();

  if (manifest?.datasets?.length) {
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
        const payload = await loadDatasetText(ds.file);
        if (!payload) {
          const msg = `Cannot load ${ds.file} or ${ds.file.replace(/\.gz$/, '')} from data/defaults/`;
          result.errors.push(msg);
          continue;
        }

        const imported = importFromText(payload.text, payload.filename, ds.symbol, ds.timeframe);

        if (imported.candles.length === 0) {
          result.errors.push(`No valid candles in ${ds.file}`);
          continue;
        }

        const metadata = await saveCandles(imported.symbol, imported.timeframe, imported.candles);
        result.loaded.push(metadata);
        log.info(`Seeded ${metadata.symbol} ${metadata.timeframe}: ${metadata.count} candles`);
      } catch (err) {
        const msg = `Failed to seed ${ds.symbol} ${ds.timeframe}: ${err instanceof Error ? err.message : String(err)}`;
        log.warn(msg, err);
        result.errors.push(msg);
      }
    }
  }

  if (result.loaded.length === 0) {
    for (const seed of FALLBACK_SEEDS) {
      const key = datasetKey(seed.symbol, seed.timeframe);
      if (!options.force) {
        const needs = await datasetNeedsSeed(existing, seed.symbol, seed.timeframe, getCandleCount);
        if (!needs) continue;
      }
      try {
        const metadata = await saveCandles(seed.symbol, seed.timeframe, seed.candles);
        result.loaded.push(metadata);
        result.errors.push(
          `Used built-in fallback for ${seed.symbol} ${seed.timeframe} (${seed.candles.length} candles). Deploy data/defaults/ for full history.`
        );
      } catch (err) {
        result.errors.push(`Fallback seed failed: ${err instanceof Error ? err.message : String(err)}`);
      }
    }
  }

  return result;
}

/**
 * Quick connectivity check for diagnostics UI.
 * @returns {Promise<{ ok: boolean, bases: string[], manifest: boolean, compression: boolean }>}
 */
export async function probeDefaultData() {
  const bases = getCandidateBases();
  const manifest = await fetchManifest();
  return {
    ok: Boolean(manifest?.datasets?.length),
    bases,
    manifest: Boolean(manifest),
    compression: isCompressionSupported(),
  };
}
