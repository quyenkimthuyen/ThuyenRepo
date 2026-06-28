/**
 * Lightweight namespaced logger for development and debugging.
 * @module utils/logger
 */

/** @type {'debug'|'info'|'warn'|'error'} */
const LOG_LEVEL = 'info';

const LEVELS = { debug: 0, info: 1, warn: 2, error: 3 };

/**
 * Create a namespaced logger.
 * @param {string} namespace - Module name prefix
 * @returns {{ debug: Function, info: Function, warn: Function, error: Function }}
 */
export function createLogger(namespace) {
  const prefix = `[${namespace}]`;

  /**
   * @param {'debug'|'info'|'warn'|'error'} level
   * @param {unknown[]} args
   */
  const log = (level, ...args) => {
    if (LEVELS[level] >= LEVELS[LOG_LEVEL]) {
      console[level](prefix, ...args);
    }
  };

  return {
    debug: (...args) => log('debug', ...args),
    info: (...args) => log('info', ...args),
    warn: (...args) => log('warn', ...args),
    error: (...args) => log('error', ...args),
  };
}
