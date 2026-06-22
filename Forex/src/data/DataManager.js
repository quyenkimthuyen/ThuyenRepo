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
 * Main data service — singleton module with initialize() lifecycle.
 */
const DataManager = {
  /**
   * @param {{ bus: import('../core/EventBus.js').EventBus, loader: import('../core/ModuleLoader.js').ModuleLoader }} _ctx
   */
  async initialize(_ctx) {
    await store.open();
    log.info('DataManager ready');
    emitDataLog('IndexedDB initialized — data layer active');
  },

  /**
   * List all stored datasets.
   * @returns {Promise<import('./Candle.js').DatasetMetadata[]>}
   */
  async listDatasets() {
    return store.getAllMetadata();
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
