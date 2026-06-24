/**
 * Low-level IndexedDB persistence for OHLCV candle data.
 * Schema: Symbol → Timeframe → Candles
 * @module data/IndexedDBStore
 */

import { Config } from '../core/Config.js';
import { datasetKey } from './Candle.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('IndexedDBStore');

/**
 * IDBKeyRange on the compound primary key [symbol, timeframe, timestamp].
 * @param {string} symbol
 * @param {string} timeframe
 * @param {number} [from]
 * @param {number} [to]
 * @returns {IDBKeyRange}
 */
function candleKeyRange(symbol, timeframe, from, to) {
  const lower = from ?? 0;
  const upper = to ?? Number.MAX_SAFE_INTEGER;
  return IDBKeyRange.bound(
    [symbol, timeframe, lower],
    [symbol, timeframe, upper]
  );
}

/**
 * IndexedDB wrapper with batch write support.
 */
export class IndexedDBStore {
  /** @type {IDBDatabase|null} */
  #db = null;

  /**
   * Open (or create) the database.
   * @returns {Promise<IDBDatabase>}
   */
  async open() {
    if (this.#db) return this.#db;

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(Config.DB_NAME, Config.DB_VERSION);

      request.onupgradeneeded = (event) => {
        const db = /** @type {IDBOpenDBRequest} */ (event.target).result;

        if (!db.objectStoreNames.contains(Config.DB_STORES.CANDLES)) {
          const store = db.createObjectStore(Config.DB_STORES.CANDLES, {
            keyPath: ['symbol', 'timeframe', 'timestamp'],
          });
          store.createIndex('bySymbolTf', ['symbol', 'timeframe'], { unique: false });
        }

        if (!db.objectStoreNames.contains(Config.DB_STORES.METADATA)) {
          db.createObjectStore(Config.DB_STORES.METADATA, { keyPath: 'key' });
        }

        if (!db.objectStoreNames.contains(Config.DB_STORES.RESULTS)) {
          db.createObjectStore(Config.DB_STORES.RESULTS, { keyPath: 'key' });
        }

        log.info('Database schema created / upgraded');
      };

      request.onsuccess = () => {
        this.#db = request.result;
        log.info('Database opened');
        resolve(this.#db);
      };

      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Write candles in batches for performance.
   * @param {import('./Candle.js').StoredCandle[]} candles
   * @returns {Promise<number>}
   */
  async putCandles(candles) {
    const db = await this.open();
    const batchSize = Config.DB_BATCH_SIZE;
    let written = 0;

    for (let i = 0; i < candles.length; i += batchSize) {
      const batch = candles.slice(i, i + batchSize);
      await new Promise((resolve, reject) => {
        const tx = db.transaction(Config.DB_STORES.CANDLES, 'readwrite');
        const store = tx.objectStore(Config.DB_STORES.CANDLES);

        for (const candle of batch) {
          const req = store.put(candle);
          req.onerror = () => reject(req.error);
        }

        tx.oncomplete = () => resolve(undefined);
        tx.onerror = () => reject(tx.error);
        tx.onabort = () => reject(tx.error);
      });
      written += batch.length;
    }

    return written;
  }

  /**
   * @param {import('./Candle.js').DatasetMetadata} metadata
   */
  async putMetadata(metadata) {
    const db = await this.open();
    await this.#runTransaction(db, Config.DB_STORES.METADATA, 'readwrite', (store) => {
      store.put(metadata);
    });
  }

  /**
   * Count candles for a symbol/timeframe without loading them into memory.
   * @param {string} symbol
   * @param {string} timeframe
   * @returns {Promise<number>}
   */
  async countCandles(symbol, timeframe) {
    const db = await this.open();
    const range = candleKeyRange(symbol, timeframe);

    return new Promise((resolve, reject) => {
      const tx = db.transaction(Config.DB_STORES.CANDLES, 'readonly');
      const store = tx.objectStore(Config.DB_STORES.CANDLES);
      const request = store.count(range);
      request.onsuccess = () => resolve(request.result ?? 0);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Read all candles for a symbol/timeframe, optionally within a range.
   * @param {string} symbol
   * @param {string} timeframe
   * @param {number} [from]
   * @param {number} [to]
   * @returns {Promise<import('./Candle.js').StoredCandle[]>}
   */
  async getCandles(symbol, timeframe, from, to) {
    const db = await this.open();
    const range = candleKeyRange(symbol, timeframe, from, to);

    return new Promise((resolve, reject) => {
      const tx = db.transaction(Config.DB_STORES.CANDLES, 'readonly');
      const store = tx.objectStore(Config.DB_STORES.CANDLES);
      const request = store.getAll(range);
      request.onsuccess = () => resolve(request.result ?? []);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * @param {string} symbol
   * @param {string} timeframe
   * @returns {Promise<import('./Candle.js').DatasetMetadata|undefined>}
   */
  async getMetadata(symbol, timeframe) {
    const db = await this.open();
    const key = datasetKey(symbol, timeframe);

    return new Promise((resolve, reject) => {
      const tx = db.transaction(Config.DB_STORES.METADATA, 'readonly');
      const request = tx.objectStore(Config.DB_STORES.METADATA).get(key);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * @returns {Promise<import('./Candle.js').DatasetMetadata[]>}
   */
  async getAllMetadata() {
    const db = await this.open();

    return new Promise((resolve, reject) => {
      const tx = db.transaction(Config.DB_STORES.METADATA, 'readonly');
      const request = tx.objectStore(Config.DB_STORES.METADATA).getAll();
      request.onsuccess = () => resolve(request.result ?? []);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Delete all candles and metadata for a dataset.
   * @param {string} symbol
   * @param {string} timeframe
   */
  async deleteDataset(symbol, timeframe) {
    const db = await this.open();
    const candles = await this.getCandles(symbol, timeframe);

    await this.#runTransaction(db, Config.DB_STORES.CANDLES, 'readwrite', (store) => {
      for (const c of candles) {
        store.delete([symbol, timeframe, c.timestamp]);
      }
    });

    await this.#runTransaction(db, Config.DB_STORES.METADATA, 'readwrite', (store) => {
      store.delete(datasetKey(symbol, timeframe));
    });
  }

  /**
   * @param {string} key
   * @param {unknown} value
   */
  async putJsonResult(key, value) {
    const db = await this.open();
    await this.#runTransaction(db, Config.DB_STORES.RESULTS, 'readwrite', (store) => {
      store.put({ key, value, updatedAt: Date.now() });
    });
  }

  /**
   * @param {string} key
   * @returns {Promise<unknown|undefined>}
   */
  async getJsonResult(key) {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(Config.DB_STORES.RESULTS, 'readonly');
      const request = tx.objectStore(Config.DB_STORES.RESULTS).get(key);
      request.onsuccess = () => resolve(request.result?.value);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * @param {string} key
   */
  async deleteJsonResult(key) {
    const db = await this.open();
    await this.#runTransaction(db, Config.DB_STORES.RESULTS, 'readwrite', (store) => {
      store.delete(key);
    });
  }

  /** Delete every candle row, metadata record, and persisted result blob. */
  async clearAll() {
    const db = await this.open();
    await this.#runTransaction(db, Config.DB_STORES.CANDLES, 'readwrite', (store) => {
      store.clear();
    });
    await this.#runTransaction(db, Config.DB_STORES.METADATA, 'readwrite', (store) => {
      store.clear();
    });
    if (db.objectStoreNames.contains(Config.DB_STORES.RESULTS)) {
      await this.#runTransaction(db, Config.DB_STORES.RESULTS, 'readwrite', (store) => {
        store.clear();
      });
    }
    log.info('IndexedDB cleared');
  }

  /**
   * @param {IDBDatabase} db
   * @param {string} storeName
   * @param {IDBTransactionMode} mode
   * @param {Function} fn
   */
  #runTransaction(db, storeName, mode, fn) {
    return new Promise((resolve, reject) => {
      const tx = db.transaction(storeName, mode);
      const store = tx.objectStore(storeName);
      fn(store);
      tx.oncomplete = () => resolve(undefined);
      tx.onerror = () => reject(tx.error);
    });
  }
}

/** Singleton store instance. */
export const store = new IndexedDBStore();
