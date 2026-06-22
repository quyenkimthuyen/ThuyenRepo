/**
 * Bottom status bar showing app state and performance info.
 * @module ui/StatusBar
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';

/**
 * StatusBar component factory.
 */
export const StatusBar = {
  /** @type {HTMLElement|null} */
  #statusText: null,

  /**
   * Render the status bar element.
   * @returns {HTMLElement}
   */
  render() {
    return el('footer', { class: 'statusbar' }, [
      el('span', { class: 'status-item status-ready' }, ['● Ready']),
      el('span', { class: 'status-item', id: 'status-message' }, ['No data loaded']),
      el('span', { class: 'status-item status-spacer' }),
      el('span', { class: 'status-item' }, [`${Config.SYMBOLS.length} pairs`]),
      el('span', { class: 'status-item' }, [`${Config.TARGET_FPS} FPS target`]),
      el('span', { class: 'status-item status-time', id: 'status-time' }, ['']),
    ]);
  },

  /**
   * Attach listeners and start clock.
   * @param {HTMLElement} shell
   */
  init(shell) {
    this.#statusText = shell.querySelector('#status-message');
    this.#updateClock();
    setInterval(() => this.#updateClock(), 1000);

    bus.on(Events.APP_READY, () => {
      if (this.#statusText) {
        this.#statusText.textContent = 'PARL v1.0.0 — All phases ready';
      }
    });

    bus.on(Events.VIEW_ACTIVE, ({ view }) => {
      if (this.#statusText) {
        this.#statusText.textContent = `View: ${view}`;
      }
    });
  },

  #updateClock() {
    const clock = document.getElementById('status-time');
    if (clock) {
      clock.textContent = new Date().toLocaleTimeString();
    }
  },
};
