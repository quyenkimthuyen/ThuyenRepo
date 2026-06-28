/**
 * High-level data management service.
 * Orchestrates IndexedDB, import/export, merge, and gap detection.
 * @module data/DataManager
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { clearParlLocalStorage } from '../utils/dom.js';
import { datasetKey, toStoredCandle } from './Candle.js';
import { store } from './IndexedDBStore.js';
import { mergeCandles, detectGaps, computeStats } from './CandleMerge.js';
import { importFromText } from './DataImporter.js';
import { exportCSV, exportJSON, downloadFile, downloadBinary } from './DataExporter.js';
import { compress, decompress } from './Compression.js';
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
 * Load remaining default datasets after boot (non-blocking).
 */
function seedRemainingInBackground() {
  DataManager.seedDefaults()
    .then((result) => {
      if (result.loaded.length > 0) {
        const summary = result.loaded
          .map((d) => `${d.symbol} ${d.timeframe}`)
          .join(', ');
        emitDataLog(`Background load complete — ${summary}`);
      }
    })
    .catch((err) => {
      emitDataLog(`Background data load failed: ${err.message}`, 'warn');
    });
}

/**
 * Remove legacy PARL IndexedDB (forex era).
 */
function deleteLegacyDatabase() {
  try {
    indexedDB.deleteDatabase('parl_data');
  } catch {
    /* ignore */
  }
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
    deleteLegacyDatabase();
    await this.purgeNonBtcDatasets();
    setBootMessage('Đang tải dữ liệu BTCUSD…');

    let btcW = await this.getCandleCount('BTCUSD', 'W');
    if (btcW === 0) {
      await this.seedDefaults({ fallbackOnly: true });
      btcW = await this.getCandleCount('BTCUSD', 'W');
    }
    if (btcW === 0) {
      emitDataLog('Quick seed failed — loading BTCUSD W from data/defaults/…', 'warn');
      await this.seedDefaults({ priorityOnly: true });
      btcW = await this.getCandleCount('BTCUSD', 'W');
    }
    if (btcW === 0) {
      emitDataLog(
        'Chưa có dữ liệu BTC — mở Data Manager → Reload Default Data hoặc Import (cần chạy qua http://).',
        'warn'
      );
    }

    setBootMessage(`Khởi động ${Config.APP_NAME}…`);
    seedRemainingInBackground();

    log.info('DataManager ready');
    emitDataLog('IndexedDB initialized — data layer active');
  },

  /**
   * Fast candle count without loading all OHLCV rows.
   * @param {string} symbol
   * @param {string} timeframe
   * @returns {Promise<number>}
   */
  async getCandleCount(symbol, timeframe) {
    return store.countCandles(symbol, timeframe);
  },

  /**
   * Load bundled BTCUSD datasets from data/defaults/.
   * @param {{ force?: boolean, priorityOnly?: boolean, fallbackOnly?: boolean, only?: Array<{ symbol: string, timeframe: string }> }} [options]
   * @returns {Promise<import('./DefaultDataLoader.js').DefaultLoadResult>}
   */
  async seedDefaults(options = {}) {
    if (options.force) {
      const probe = await probeDefaultData();
      const base = probe.workingBase ?? probe.bases[0];
      if (probe.ok && base) {
        const res = await fetch(new URL('manifest.json', base));
        if (res.ok) {
          const manifest = await res.json();
          const targets = options.only?.length
            ? manifest.datasets?.filter((ds) =>
                options.only.some((o) => o.symbol === ds.symbol && o.timeframe === ds.timeframe)
              ) ?? []
            : manifest.datasets ?? [];
          for (const ds of targets) {
            await this.deleteDataset(ds.symbol, ds.timeframe);
          }
        }
      }
    }

    const result = await loadDefaultDatasets(
      (symbol, timeframe, candles) => this.saveCandles(symbol, timeframe, candles),
      () => this.listDatasets(),
      (symbol, timeframe) => this.getCandleCount(symbol, timeframe),
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
   * Re-import one bundled dataset from data/defaults/ (replace, not merge).
   * @param {string} symbol
   * @param {string} timeframe
   */
  async reloadBundledDataset(symbol, timeframe) {
    return this.seedDefaults({
      force: true,
      only: [{ symbol, timeframe }],
    });
  },

  /**
   * Diagnostic snapshot for troubleshooting empty data issues.
   * @returns {Promise<Record<string, unknown>>}
   */
  async getDataHealth() {
    const probe = await probeDefaultData();
    const datasets = await this.listDatasets();
    const btcW = datasets.find((d) => d.symbol === 'BTCUSD' && d.timeframe === 'W');
    const btcWCount = await this.getCandleCount('BTCUSD', 'W');
    return {
      protocol: typeof window !== 'undefined' ? window.location.protocol : 'unknown',
      href: typeof window !== 'undefined' ? window.location.href : '',
      ...probe,
      indexedDbDatasets: datasets.length,
      btcWCount,
      btcWMetaCount: btcW?.count ?? 0,
      datasets: datasets.map((d) => ({
        key: d.key,
        symbol: d.symbol,
        timeframe: d.timeframe,
        count: d.count,
      })),
    };
  },

  /**
   * Delete all non-BTC datasets from IndexedDB (legacy EUR/GBP cleanup).
   * @returns {Promise<number>} Number of datasets removed
   */
  async purgeNonBtcDatasets() {
    const all = await store.getAllMetadata();
    let removed = 0;
    for (const ds of all) {
      if (ds.symbol !== 'BTCUSD') {
        await store.deleteDataset(ds.symbol, ds.timeframe);
        removed++;
      }
    }
    if (removed > 0) {
      emitDataLog(
        `Đã xóa ${removed} dataset không phải BTC (dữ liệu EUR/GBP cũ trong trình duyệt).`,
        'warn'
      );
      bus.emit(Events.DATA_UPDATED, { purgedForex: removed });
    }
    return removed;
  },

  /**
   * List all stored datasets (BTC only).
   * @returns {Promise<import('./Candle.js').DatasetMetadata[]>}
   */
  async listDatasets() {
    const all = await store.getAllMetadata();
    return all.filter((d) => d.symbol === 'BTCUSD');
  },

  /**
   * Datasets that have at least one candle (usable for strategy scan / backtest).
   * @returns {Promise<import('./Candle.js').DatasetMetadata[]>}
   */
  async listRunnableDatasets() {
    const datasets = await this.listDatasets();
    return datasets
      .filter((d) => d.count > 0)
      .sort((a, b) => {
        const sym = a.symbol.localeCompare(b.symbol);
        if (sym !== 0) return sym;
        return Config.TIMEFRAMES.indexOf(a.timeframe) - Config.TIMEFRAMES.indexOf(b.timeframe);
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
   * @param {{ replace?: boolean }} [options]
   * @returns {Promise<import('./Candle.js').DatasetMetadata>}
   */
  async saveCandles(symbol, timeframe, incoming, options = {}) {
    const existing = options.replace ? [] : await this.getCandles(symbol, timeframe);
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
    return detectGaps(candles, timeframe, { forexMarket: false });
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
   * Delete all stored datasets for a timeframe (e.g. all H1).
   * @param {string} timeframe
   * @returns {Promise<number>} Number of datasets removed
   */
  async deleteTimeframe(timeframe) {
    const datasets = await this.listDatasets();
    const targets = datasets.filter((d) => d.timeframe === timeframe);
    for (const ds of targets) {
      await store.deleteDataset(ds.symbol, ds.timeframe);
    }
    if (targets.length > 0) {
      emitDataLog(`Deleted ${targets.length} dataset(s) for timeframe ${timeframe}`);
      bus.emit(Events.DATA_UPDATED, { deletedTimeframe: timeframe, count: targets.length });
    }
    return targets.length;
  },

  /**
   * Wipe all app data (IndexedDB + localStorage) and reload — like a fresh install.
   * @returns {Promise<void>}
   */
  async resetAppData() {
    await store.clearAll();
    clearParlLocalStorage();
    emitDataLog('Đã xóa toàn bộ dữ liệu app — đang tải lại…', 'warn');
    bus.emit(Events.APP_DATA_RESET);
    window.location.reload();
  },

};

export default DataManager;
