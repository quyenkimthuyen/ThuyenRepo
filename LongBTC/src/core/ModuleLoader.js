/**
 * Dynamic ES module loader with lifecycle management.
 * Supports future plugin registration via the same interface.
 * @module core/ModuleLoader
 */

import { bus, Events } from './EventBus.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('ModuleLoader');

/**
 * @typedef {Object} ModuleDescriptor
 * @property {string} id - Unique module identifier
 * @property {string} path - Relative import path
 * @property {boolean} [required=true] - If true, failure stops boot
 * @property {string[]} [dependsOn] - Module IDs that must load first
 */

/**
 * @typedef {Object} LoadedModule
 * @property {string} id
 * @property {Object} instance
 * @property {'loaded'|'initialized'|'error'} status
 */

/**
 * Loads and initializes application modules in dependency order.
 */
export class ModuleLoader {
  /** @type {Map<string, LoadedModule>} */
  #modules = new Map();

  /** @type {ModuleDescriptor[]} */
  #registry = [];

  /**
   * Register a module descriptor.
   * @param {ModuleDescriptor} descriptor
   */
  register(descriptor) {
    this.#registry.push(descriptor);
  }

  /**
   * Register multiple module descriptors.
   * @param {ModuleDescriptor[]} descriptors
   */
  registerAll(descriptors) {
    for (const d of descriptors) {
      this.register(d);
    }
  }

  /**
   * Load all registered modules respecting dependencies.
   * @param {import('./EventBus.js').EventBus} eventBus
   * @returns {Promise<Map<string, LoadedModule>>}
   */
  async loadAll(eventBus) {
    const sorted = this.#topologicalSort(this.#registry);

    for (const descriptor of sorted) {
      await this.#loadOne(descriptor, eventBus);
    }

    return this.#modules;
  }

  /**
   * Get a loaded module instance by ID.
   * @param {string} id
   * @returns {Object|undefined}
   */
  get(id) {
    return this.#modules.get(id)?.instance;
  }

  /**
   * @param {ModuleDescriptor} descriptor
   * @param {import('./EventBus.js').EventBus} eventBus
   */
  async #loadOne(descriptor, eventBus) {
    const { id, path, required = true } = descriptor;

    try {
      log.info(`Loading module: ${id}`);
      const mod = await import(path);

      const instance = mod.default ?? mod;
      this.#modules.set(id, { id, instance, status: 'loaded' });

      if (typeof instance.initialize === 'function') {
        await instance.initialize({ bus: eventBus, loader: this });
        this.#modules.get(id).status = 'initialized';
      }

      bus.emit(Events.MODULE_LOADED, { id });
      log.info(`Module ready: ${id}`);
    } catch (err) {
      log.error(`Failed to load module "${id}":`, err);
      this.#modules.set(id, { id, instance: null, status: 'error' });
      bus.emit(Events.MODULE_ERROR, { id, error: err });

      if (required) {
        throw new Error(`Required module "${id}" failed to load: ${err.message}`);
      }
    }
  }

  /**
   * Topological sort of module descriptors by dependsOn.
   * @param {ModuleDescriptor[]} descriptors
   * @returns {ModuleDescriptor[]}
   */
  #topologicalSort(descriptors) {
    const map = new Map(descriptors.map((d) => [d.id, d]));
    const visited = new Set();
    const result = [];

    /**
     * @param {string} id
     */
    const visit = (id) => {
      if (visited.has(id)) return;
      visited.add(id);
      const desc = map.get(id);
      if (!desc) return;
      for (const dep of desc.dependsOn ?? []) {
        visit(dep);
      }
      result.push(desc);
    };

    for (const d of descriptors) {
      visit(d.id);
    }

    return result;
  }
}
