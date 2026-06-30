/**
 * StatusBar component factory.
 */
import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import DataManager from '../data/DataManager.js';
import { dataFreshnessChipText } from './DataFreshnessUi.js';

class StatusBarImpl {
  /** @type {HTMLElement|null} */
  #statusText = null;

  /** @type {HTMLElement|null} */
  #dataFreshness = null;

  /**
   * @returns {HTMLElement}
   */
  render() {
    return el('footer', { class: 'statusbar' }, [
      el('span', { class: 'status-item status-ready' }, ['\u25cf Ready']),
      el('span', { class: 'status-item', id: 'status-message' }, ['No data loaded']),
      el('span', { class: 'status-item status-data-age', id: 'status-data-age' }, ['']),
      el('span', { class: 'status-item status-spacer' }),
      el('span', { class: 'status-item' }, ['BTCUSD']),
      el('span', { class: 'status-item' }, [`${Config.TARGET_FPS} FPS target`]),
      el('span', { class: 'status-item status-time', id: 'status-time' }, ['']),
    ]);
  }

  /**
   * @param {HTMLElement} shell
   */
  init(shell) {
    this.#statusText = shell.querySelector('#status-message');
    this.#dataFreshness = shell.querySelector('#status-data-age');
    this.#updateClock();
    setInterval(() => this.#updateClock(), 1000);

    bus.on(Events.APP_READY, () => {
      if (this.#statusText) {
        this.#statusText.textContent = `${Config.APP_SHORT_NAME} v${Config.APP_VERSION} \u2014 S\u1eb5n s\u00e0ng`;
      }
      this.#refreshDataAge();
    });

    bus.on(Events.VIEW_ACTIVE, ({ view }) => {
      if (this.#statusText) {
        this.#statusText.textContent = `View: ${view}`;
      }
    });

    bus.on(Events.DATA_UPDATED, () => this.#refreshDataAge());
    bus.on(Events.CHART_LOADED, ({ symbol, timeframe, candles }) => {
      if (symbol === 'BTCUSD' && candles?.length) {
        this.#setDataAge(candles[candles.length - 1].timestamp, timeframe);
      }
    });
  }

  async #refreshDataAge() {
    const datasets = await DataManager.listDatasets();
    const w = datasets.find((d) => d.symbol === 'BTCUSD' && d.timeframe === 'W');
    if (w?.lastTimestamp) {
      this.#setDataAge(w.lastTimestamp, w.timeframe);
    }
  }

  /**
   * @param {number} lastTs
   * @param {string} timeframe
   */
  #setDataAge(lastTs, timeframe) {
    if (!this.#dataFreshness) return;
    this.#dataFreshness.textContent = `Data ${timeframe}: ${dataFreshnessChipText(lastTs, timeframe)}`;
  }

  #updateClock() {
    const clock = document.getElementById('status-time');
    if (clock) {
      clock.textContent = new Date().toLocaleTimeString();
    }
  }
}

export const StatusBar = new StatusBarImpl();
