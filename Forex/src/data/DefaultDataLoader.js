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

/** Datasets loaded first so strategy scan works quickly on boot. */
const BOOT_PRIORITY = Object.freeze([
  { symbol: 'EURUSD', timeframe: 'H1' },
]);

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
 * Candidate base URLs for data/defaults (page path first, then module path).
 * @returns {string[]}
 */
function getCandidateBases() {
  const bases = [];

  if (typeof document !== 'undefined') {
    try {
      bases.push(new URL('data/defaults/', document.baseURI).href);
    } catch { /* ignore */ }
  }
  if (typeof window !== 'undefined') {
    try {
      bases.push(new URL('data/defaults/', window.location.href).href);
    } catch { /* ignore */ }
  }
  try {
    bases.push(new URL('../../data/defaults/', import.meta.url).href);
  } catch { /* ignore */ }

  return [...new Set(bases)];
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
 * @returns {Promise<string|null>}
 */
async function findWorkingBase() {
  for (const base of getCandidateBases()) {
    try {
      const res = await fetch(new URL('manifest.json', base));
      if (res.ok) return base;
    } catch { /* try next */ }
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
 * @param {DefaultManifest['datasets']} datasets
 * @param {boolean} priorityOnly
 * @param {Array<{ symbol: string, timeframe: string }>} [only]
 */
function selectDatasets(datasets, priorityOnly, only) {
  if (only?.length) {
    return datasets.filter((ds) =>
      only.some((o) => o.symbol === ds.symbol && o.timeframe === ds.timeframe)
    );
  }
  if (!priorityOnly) return datasets;
  return datasets.filter((ds) =>
    BOOT_PRIORITY.some((p) => p.symbol === ds.symbol && p.timeframe === ds.timeframe)
  );
}

/**
 * Import bundled datasets that are missing or empty in IndexedDB.
 * @param {(symbol: string, timeframe: string, candles: import('./Candle.js').Candle[]) => Promise<import('./Candle.js').DatasetMetadata>} saveCandles
 * @param {() => Promise<import('./Candle.js').DatasetMetadata[]>} listDatasets
 * @param {(symbol: string, timeframe: string) => Promise<number>} getCandleCount
 * @param {{ force?: boolean, priorityOnly?: boolean, fallbackOnly?: boolean, only?: Array<{ symbol: string, timeframe: string }> }} [options]
 * @returns {Promise<DefaultLoadResult>}
 */
export async function loadDefaultDatasets(saveCandles, listDatasets, getCandleCount, options = {}) {
  /** @type {DefaultLoadResult} */
  const result = { loaded: [], errors: [], skipped: [] };

  if (typeof window !== 'undefined' && window.location.protocol === 'file:') {
    result.errors.push(
      'Opened via file:// — data cannot load. Run: cd Forex && python3 -m http.server 8080 then open http://localhost:8080'
    );
    await seedFallback(saveCandles, listDatasets, getCandleCount, options, result);
    return result;
  }

  if (options.fallbackOnly) {
    await seedFallback(saveCandles, listDatasets, getCandleCount, options, result);
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
  const targets = manifest?.datasets?.length
    ? selectDatasets(manifest.datasets, Boolean(options.priorityOnly), options.only)
    : [];

  for (const ds of targets) {
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

      const metadata = await saveCandles(imported.symbol, imported.timeframe, imported.candles, {
        replace: Boolean(options.force),
      });
      result.loaded.push(metadata);
      log.info(`Seeded ${metadata.symbol} ${metadata.timeframe}: ${metadata.count} candles`);
    } catch (err) {
      const msg = `Failed to seed ${ds.symbol} ${ds.timeframe}: ${err instanceof Error ? err.message : String(err)}`;
      log.warn(msg, err);
      result.errors.push(msg);
    }
  }

  if (result.loaded.length === 0) {
    await seedFallback(saveCandles, listDatasets, getCandleCount, options, result);
  }

  return result;
}

/**
 * @param {typeof loadDefaultDatasets extends (...args: infer A) => any ? A[0] : never} saveCandles
 * @param {() => Promise<import('./Candle.js').DatasetMetadata[]>} listDatasets
 * @param {(symbol: string, timeframe: string) => Promise<number>} getCandleCount
 * @param {{ force?: boolean, priorityOnly?: boolean }} options
 * @param {DefaultLoadResult} result
 */
async function seedFallback(saveCandles, listDatasets, getCandleCount, options, result) {
  const existing = await listDatasets();
  const seeds = options.priorityOnly
    ? FALLBACK_SEEDS.filter((s) =>
        BOOT_PRIORITY.some((p) => p.symbol === s.symbol && p.timeframe === s.timeframe)
      )
    : FALLBACK_SEEDS;

  for (const seed of seeds.length ? seeds : FALLBACK_SEEDS) {
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

/**
 * Quick connectivity check for diagnostics UI.
 * @returns {Promise<{ ok: boolean, bases: string[], workingBase: string|null, manifest: boolean, compression: boolean }>}
 */
export async function probeDefaultData() {
  const bases = getCandidateBases();
  const workingBase = await findWorkingBase();
  const manifest = await fetchManifest();
  return {
    ok: Boolean(manifest?.datasets?.length),
    bases,
    workingBase,
    manifest: Boolean(manifest),
    compression: isCompressionSupported(),
  };
}
