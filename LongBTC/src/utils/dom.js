/**
 * DOM utility helpers.
 * @module utils/dom
 */

/**
 * Create an HTML element with optional attributes and children.
 * @param {string} tag - HTML tag name
 * @param {Record<string, string|boolean>} [attrs] - Attributes (class → className)
 * @param {(Node|string)[]} [children] - Child nodes or text
 * @returns {HTMLElement}
 */
export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);

  for (const [key, value] of Object.entries(attrs)) {
    if (key === 'class') {
      node.className = String(value);
    } else if (key === 'dataset') {
      Object.assign(node.dataset, value);
    } else if (key.startsWith('on') && typeof value === 'function') {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (typeof value === 'boolean') {
      if (value) node.setAttribute(key, '');
    } else {
      node.setAttribute(key, String(value));
    }
  }

  for (const child of children) {
    node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
  }

  return node;
}

/**
 * Query a single element, throwing if not found.
 * @param {string} selector
 * @param {ParentNode} [root=document]
 * @returns {HTMLElement}
 */
export function $(selector, root = document) {
  const node = root.querySelector(selector);
  if (!node) throw new Error(`Element not found: ${selector}`);
  return /** @type {HTMLElement} */ (node);
}

/**
 * Clamp a number between min and max.
 * @param {number} value
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

/**
 * Read a value from localStorage with JSON parse fallback.
 * @param {string} key
 * @param {unknown} fallback
 * @returns {unknown}
 */
export function loadFromStorage(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw !== null ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

/**
 * Save a value to localStorage as JSON.
 * @param {string} key
 * @param {unknown} value
 * @returns {boolean} False when quota is exceeded or save fails
 */
export function saveToStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (err) {
    console.warn(`[Storage] Failed to save "${key}":`, err);
    return false;
  }
}

/**
 * List localStorage keys owned by LongBTC (prefix longbtc_ or legacy parl_).
 * @returns {string[]}
 */
export function listParlStorageKeys() {
  const keys = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key?.startsWith('parl_') || key?.startsWith('longbtc_')) keys.push(key);
  }
  return keys;
}

/**
 * Remove all app keys from localStorage (settings, legacy forex results…).
 */
export function clearParlLocalStorage() {
  for (const key of listParlStorageKeys()) {
    localStorage.removeItem(key);
  }
}

/**
 * Resolve a path relative to the app HTML (works with Live Server / subpaths).
 * @param {string} relativePath
 * @returns {string}
 */
export function resolveAppAsset(relativePath) {
  const clean = relativePath.replace(/^\//, '');
  try {
    return new URL(`../../${clean}`, import.meta.url).href;
  } catch {
    /* fall through */
  }
  if (typeof document !== 'undefined') {
    try {
      return new URL(clean, document.baseURI).href;
    } catch {
      /* fall through */
    }
  }
  return `/${clean}`;
}
