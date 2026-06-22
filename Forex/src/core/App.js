/**
 * Root application controller.
 * Bootstraps the module loader and wires the UI shell.
 * @module core/App
 */

import { Config, getDefaultSettings } from './Config.js';
import { bus, Events } from './EventBus.js';
import { ModuleLoader } from './ModuleLoader.js';
import { loadFromStorage, saveToStorage } from '../utils/dom.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('App');

/**
 * Main application class — single entry point for the research lab.
 */
class App {
  /** @type {ModuleLoader|null} */
  #loader = null;

  /** @type {Record<string, unknown>} */
  #settings = {};

  /**
   * Boot the application.
   * @returns {Promise<void>}
   */
  async boot() {
    log.info(`Starting ${Config.APP_NAME} v${Config.APP_VERSION}`);
    this.#settings = this.#loadSettings();
    this.#applyTheme();

    this.#loader = new ModuleLoader();
    this.#registerModules();

    try {
      await this.#loader.loadAll(bus);
      bus.emit(Events.APP_READY, { settings: this.#settings });
      log.info('Application ready');
    } catch (err) {
      log.error('Boot failed:', err);
      bus.emit(Events.APP_ERROR, { error: err });
      this.#showBootError(err);
    }
  }

  /**
   * @returns {Record<string, unknown>}
   */
  getSettings() {
    return { ...this.#settings };
  }

  /**
   * Persist a settings change.
   * @param {Record<string, unknown>} partial
   */
  updateSettings(partial) {
    this.#settings = { ...this.#settings, ...partial };
    saveToStorage(Config.STORAGE_KEYS.SETTINGS, this.#settings);
    bus.emit(Events.SETTINGS_CHANGE, this.#settings);
  }

  #loadSettings() {
    return loadFromStorage(Config.STORAGE_KEYS.SETTINGS, getDefaultSettings());
  }

  #applyTheme() {
    document.documentElement.dataset.theme = this.#settings.theme ?? 'dark';
  }

  #registerModules() {
    this.#loader.registerAll([
      { id: 'layout', path: '../ui/Layout.js' },
      { id: 'keyboard', path: '../ui/KeyboardShortcuts.js', dependsOn: ['layout'] },
    ]);
  }

  /**
   * @param {Error} err
   */
  #showBootError(err) {
    const root = document.getElementById('app');
    if (!root) return;
    root.innerHTML = `
      <div class="boot-error">
        <h2>Failed to start application</h2>
        <p>${err.message}</p>
        <button onclick="location.reload()">Reload</button>
      </div>
    `;
  }
}

/** Singleton application instance. */
const app = new App();

export default app;
