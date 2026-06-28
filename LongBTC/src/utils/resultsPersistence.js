/**
 * Persist large research payloads in IndexedDB (fallback: localStorage).
 * @module utils/resultsPersistence
 */

import { store } from '../data/IndexedDBStore.js';
import { loadFromStorage, saveToStorage } from './dom.js';

/**
 * @param {string} storageKey
 * @param {unknown} [fallback]
 * @returns {Promise<unknown>}
 */
export async function loadPersistedResult(storageKey, fallback = null) {
  if (typeof indexedDB !== 'undefined') {
    try {
      const value = await store.getJsonResult(storageKey);
      if (value != null) return value;
    } catch (err) {
      console.warn(`[Results] IndexedDB read failed for "${storageKey}":`, err);
    }
  }

  const fromLocal = loadFromStorage(storageKey, fallback);
  if (fromLocal != null && fromLocal !== fallback && typeof indexedDB !== 'undefined') {
    savePersistedResult(storageKey, fromLocal).catch(() => {});
  }
  return fromLocal;
}

/**
 * @param {string} storageKey
 * @param {unknown} value
 * @returns {Promise<boolean>}
 */
export async function savePersistedResult(storageKey, value) {
  if (typeof indexedDB !== 'undefined') {
    try {
      await store.putJsonResult(storageKey, value);
      try {
        localStorage.removeItem(storageKey);
      } catch {
        /* ignore */
      }
      return true;
    } catch (err) {
      console.warn(`[Results] IndexedDB write failed for "${storageKey}":`, err);
    }
  }
  if (typeof localStorage !== 'undefined') {
    return saveToStorage(storageKey, value);
  }
  return false;
}
