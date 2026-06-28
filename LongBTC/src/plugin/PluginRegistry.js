/**
 * Plugin registry for strategy modules.
 * Supports built-in and future external plugin registration.
 * @module plugin/PluginRegistry
 */

import { bus, Events } from '../core/EventBus.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('PluginRegistry');

/**
 * @typedef {Object} PluginDescriptor
 * @property {string} id
 * @property {string} name
 * @property {string} description
 * @property {string} version
 * @property {string} category
 * @property {typeof import('../strategy/BaseStrategy.js').BaseStrategy} StrategyClass
 */

/**
 * Central registry for strategy plugins.
 */
export class PluginRegistry {
  /** @type {Map<string, PluginDescriptor>} */
  #plugins = new Map();

  /**
   * Register a strategy plugin class.
   * @param {typeof import('../strategy/BaseStrategy.js').BaseStrategy} StrategyClass
   */
  register(StrategyClass) {
    const id = StrategyClass.id;
    if (!id || id === 'base') {
      throw new Error('Strategy must define a unique static id');
    }

    if (this.#plugins.has(id)) {
      log.warn(`Plugin "${id}" already registered — overwriting`);
    }

    const descriptor = {
      id,
      name: StrategyClass.name,
      description: StrategyClass.description,
      version: StrategyClass.version,
      category: StrategyClass.category,
      StrategyClass,
    };

    this.#plugins.set(id, descriptor);
    bus.emit(Events.STRATEGY_REGISTERED, { id, name: descriptor.name });
    log.info(`Registered plugin: ${id} (${descriptor.name})`);
  }

  /**
   * Register multiple strategy classes.
   * @param {Array<typeof import('../strategy/BaseStrategy.js').BaseStrategy>} classes
   */
  registerAll(classes) {
    for (const C of classes) {
      this.register(C);
    }
  }

  /**
   * @param {string} id
   * @returns {PluginDescriptor|undefined}
   */
  get(id) {
    return this.#plugins.get(id);
  }

  /**
   * @returns {PluginDescriptor[]}
   */
  getAll() {
    return [...this.#plugins.values()];
  }

  /**
   * @param {string} id
   * @returns {boolean}
   */
  has(id) {
    return this.#plugins.has(id);
  }

  /**
   * Create a new strategy instance by plugin ID.
   * @param {string} id
   * @returns {import('../strategy/BaseStrategy.js').BaseStrategy}
   */
  createInstance(id) {
    const plugin = this.#plugins.get(id);
    if (!plugin) {
      throw new Error(`Unknown strategy plugin: ${id}`);
    }
    const Instance = plugin.StrategyClass;
    return new Instance();
  }

  /**
   * @returns {number}
   */
  get size() {
    return this.#plugins.size;
  }
}

/** Singleton plugin registry. */
export const registry = new PluginRegistry();
