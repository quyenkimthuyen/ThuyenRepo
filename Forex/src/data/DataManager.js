/**
 * High-level data management service.
 * Orchestrates IndexedDB, import/export, merge, and gap detection.
 * @module data/DataManager
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { datasetKey, toStoredCandle } from './Candle.js';
import { store } from './IndexedDBStore.js';
import { mergeCandles, detectGaps, computeStats } from './CandleMerge.js';
import { importFromText } from './DataImporter.js';
import { exportCSV, exportJSON, downloadFile, downloadBinary } from './DataExporter.js';
import { compress, decompress } from './Compression.js';
import { generateSample } from './SampleDataGenerator.js';
import { loadDefaultDatasets, probeDefaultData } from './DefaultDataLoader.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('DataManager');

/**
 * Emit a log message to the UI panel.
 * @param {string} message
 * @param {'info'|'warn'|'error'} [level='info']
 */
function emitDataLog(message, level = 'info') {
  bus.emit(Events.LOG_MESSAGE, { message, level, time: new Date() });
}

/**
 * @param {string} message
 */
function setBootMessage(message) {
  const boot = document.querySelector('.boot-screen');
  if (boot) boot.textContent = message;
}

/**
 * Main data service — singleton module with initialize() lifecycle.
 */
const DataManager = {
  /**
   * @param {{ bus: import('../core/EventBus.js').EventBus, loader: import('../core/ModuleLoader.js').ModuleLoader }} _ctx
   */
  async initialize(_ctx) {
    await store.open();
    setBootMessage('Loading EURUSD / GBPUSD market data…');
    await this.seedDefaults();
    setBootMessage('Starting Price Action Research Lab…');

    log.info('DataManager ready');
    emitDataLog('IndexedDB initialized — data layer active');
  },

  /**
   * Load bundled EURUSD/GBPUSD datasets from data/defaults/.
   * @param {{ force?: boolean }} [options] - Re-import even if metadata already exists
   * @returns {Promise<import('./DefaultDataLoader.js').DefaultLoadResult>}
   */
  async seedDefaults(options = {}) {
    if (options.force) {
      const probe = await probeDefaultData();
      if (probe.ok) {
        const res = await fetch(
          new URL('manifest.json', probe.bases[0] ?? 'data/defaults/')
        );
        if (res.ok) {
          const manifest = await res.json();
          for (const ds of manifest.datasets ?? []) {
            await this.deleteDataset(ds.symbol, ds.timeframe);
          }
        }
      }
    }

    const result = await loadDefaultDatasets(
      (symbol, timeframe, candles) => this.saveCandles(symbol, timeframe, candles),
      () => this.listDatasets(),
      async (symbol, timeframe) => (await this.getCandles(symbol, timeframe)).length,
      options
    );

    if (result.loaded.length > 0) {
      const summary = result.loaded
        .map((d) => `${d.symbol} ${d.timeframe} (${d.count.toLocaleString()})`)
        .join(', ');
      emitDataLog(`Loaded default data — ${summary}`);
    }

    for (const err of result.errors) {
      const level = err.startsWith('Used built-in fallback') ? 'warn' : 'error';
      emitDataLog(err, level);
    }

    if (result.loaded.length === 0 && result.errors.length === 0) {
      const datasets = await this.listDatasets();
      const hasData = datasets.some((d) => d.count > 0);
      if (!hasData) {
        emitDataLog(
          'No market data in IndexedDB. Click "Reload Default Data" or import CSV/JSON.',
          'warn'
        );
      }
    }

    bus.emit(Events.DATA_UPDATED, { seeded: result.loaded });
    return result;
  },

  /**
   * Diagnostic snapshot for troubleshooting empty data issues.
   * @returns {Promise<Record<string, unknown>>}
   */
  async getDataHealth() {
    const probe = await probeDefaultData();
    const datasets = await this.listDatasets();
    const eurusdH1 = await this.getCandles('EURUSD', 'H1');
    return {
      protocol: typeof window !== 'undefined' ? window.location.protocol : 'unknown',
      href: typeof window !== 'undefined' ? window.location.href : '',
      ...probe,
      indexedDbDatasets: datasets.length,
      eurusdH1Count: eurusdH1.length,
      datasets: datasets.map((d) => ({
        key: d.key,
        count: d.count,
      })),
    };
  },

  /**
   * List all stored datasets.
   * @returns {Promise<import('./Candle.js').DatasetMetadata[]>}
   */
  async listDatasets() {
    return store.getAllMetadata();
  },

  /**
   * Datasets that have at least one candle (usable for strategy scan / backtest).
   * @returns {Promise<import('./Candle.js').DatasetMetadata[]>}
   */
  async listRunnableDatasets() {
    const datasets = await this.listDatasets();
    const runnable = [];

    for (const meta of datasets) {
      if (meta.count > 0) {
        const actual = (await this.getCandles(meta.symbol, meta.timeframe)).length;
        if (actual > 0) runnable.push({ ...meta, count: actual });
      }
    }

    return runnable.sort((a, b) => {
      const sym = a.symbol.localeCompare(b.symbol);
      if (sym !== 0) return sym;
      const order = Config.TIMEFRAMES;
      return order.indexOf(a.timeframe) - order.indexOf(b.timeframe);
    });
  },

  /**
   * Get candles for a symbol/timeframe.
   * @param {string} symbol
   * @param {string} timeframe
   * @param {number} [from]
   * @param {number} [to]
   * @returns {Promise<import('./Candle.js').Candle[]>}
   */
  async getCandles(symbol, timeframe, from, to) {
    const stored = await store.getCandles(symbol, timeframe, from, to);
    return stored.map(({ timestamp, open, high, low, close, volume }) => ({
      timestamp, open, high, low, close, volume,
    }));
  },

  /**
   * Save candles, merging with existing data (incremental update).
   * @param {string} symbol
   * @param {string} timeframe
   * @param {import('./Candle.js').Candle[]} incoming
   * @returns {Promise<import('./Candle.js').DatasetMetadata>}
   */
  async saveCandles(symbol, timeframe, incoming) {
    const existing = await this.getCandles(symbol, timeframe);
    const merged = mergeCandles(existing, incoming);
    const stored = merged.map((c) => toStoredCandle(symbol, timeframe, c));

    await store.putCandles(stored);

    const stats = computeStats(merged);
    const metadata = {
      key: datasetKey(symbol, timeframe),
      symbol,
      timeframe,
      ...stats,
      lastUpdated: Date.now(),
    };

    await store.putMetadata(metadata);
    bus.emit(Events.DATA_UPDATED, { metadata });
    return metadata;
  },

  /**
   * Import a file (CSV, JSON, or gzip-compressed JSON).
   * @param {File} file
   * @param {string} symbol
   * @param {string} timeframe
   * @returns {Promise<import('./Candle.js').DatasetMetadata>}
   */
  async importFile(file, symbol, timeframe) {
    let text;

    if (file.name.toLowerCase().endsWith('.gz')) {
      const buffer = new Uint8Array(await file.arrayBuffer());
      text = await decompress(buffer);
    } else {
      text = await file.text();
    }

    const result = importFromText(text, file.name.replace(/\.gz$/, ''), symbol, timeframe);

    if (result.candles.length === 0) {
      throw new Error('No valid candles found in file');
    }

    const metadata = await this.saveCandles(result.symbol, result.timeframe, result.candles);

    emitDataLog(
      `Imported ${result.candles.length} candles for ${result.symbol} ${result.timeframe}` +
      (result.skipped ? ` (${result.skipped} skipped)` : '')
    );

    bus.emit(Events.DATA_IMPORTED, { metadata, skipped: result.skipped });
    return metadata;
  },

  /**
   * Export dataset to file.
   * @param {string} symbol
   * @param {string} timeframe
   * @param {'csv'|'json'} format
   * @param {boolean} [gzip=false]
   */
  async exportDataset(symbol, timeframe, format, gzip = false) {
    const candles = await this.getCandles(symbol, timeframe);
    if (candles.length === 0) throw new Error('No data to export');

    const baseName = `${symbol}_${timeframe}`;

    if (format === 'csv') {
      const content = exportCSV(candles);
      if (gzip) {
        const compressed = await compress(content);
        downloadBinary(compressed, `${baseName}.csv.gz`, 'application/gzip');
      } else {
        downloadFile(content, `${baseName}.csv`, 'text/csv');
      }
    } else {
      const content = exportJSON(symbol, timeframe, candles);
      if (gzip) {
        const compressed = await compress(content);
        downloadBinary(compressed, `${baseName}.json.gz`, 'application/gzip');
      } else {
        downloadFile(content, `${baseName}.json`, 'application/json');
      }
    }

    emitDataLog(`Exported ${candles.length} candles → ${baseName}.${format}${gzip ? '.gz' : ''}`);
    bus.emit(Events.DATA_EXPORTED, { symbol, timeframe, format, count: candles.length });
  },

  /**
   * Detect missing candles in a dataset.
   * @param {string} symbol
   * @param {string} timeframe
   * @returns {Promise<import('./CandleMerge.js').GapInfo[]>}
   */
  async findGaps(symbol, timeframe) {
    const candles = await this.getCandles(symbol, timeframe);
    return detectGaps(candles, timeframe);
  },

  /**
   * Delete a dataset entirely.
   * @param {string} symbol
   * @param {string} timeframe
   */
  async deleteDataset(symbol, timeframe) {
    await store.deleteDataset(symbol, timeframe);
    emitDataLog(`Deleted dataset ${symbol} ${timeframe}`);
    bus.emit(Events.DATA_UPDATED, { deleted: { symbol, timeframe } });
  },

  /**
   * Generate and store synthetic sample data.
   * @param {string} symbol
   * @param {string} timeframe
   * @param {number} [count]
   * @returns {Promise<import('./Candle.js').DatasetMetadata>}
   */
  async generateSample(symbol, timeframe, count) {
    const candles = generateSample(symbol, timeframe, count);
    const metadata = await this.saveCandles(symbol, timeframe, candles);
    emitDataLog(`Generated ${candles.length} sample candles for ${symbol} ${timeframe}`);
    return metadata;
  },

};

export default DataManager;
