/**
 * Chart view — candlestick chart with replay controls and data loading.
 * @module ui/ChartView
 */

import { Config } from '../core/Config.js';
import { limitChartCandles } from '../performance/CandleSampler.js';
import { bus, Events } from '../core/EventBus.js';
import { el, loadFromStorage } from '../utils/dom.js';
import DataManager from '../data/DataManager.js';
import { ChartEngine } from '../chart/ChartEngine.js';
import { ReplayEngine } from '../replay/ReplayEngine.js';
import { ReplayControls } from './ReplayControls.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('ChartView');

/**
 * Main chart workspace view.
 */
class ChartViewImpl {
  /** @type {HTMLElement|null} */
  #container = null;

  /** @type {ChartEngine|null} */
  #chart = null;

  /** @type {ReplayEngine|null} */
  #replay = null;

  /** @type {string} */
  #symbol = Config.DEFAULT_SYMBOL;

  /** @type {string} */
  #timeframe = Config.DEFAULT_TIMEFRAME;

  /** @type {Function|null} */
  #unsubs = null;

  /**
   * Mount the chart view.
   * @param {HTMLElement} container
   */
  async mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.remove('panel-body-fill');
    container.classList.add('chart-view-root');

    const settings = loadFromStorage(Config.STORAGE_KEYS.SETTINGS, {});
    this.#symbol = settings.symbol ?? Config.DEFAULT_SYMBOL;
    this.#timeframe = settings.timeframe ?? Config.DEFAULT_TIMEFRAME;

    const chartContainer = el('div', { class: 'chart-container', id: 'chart-container' });

    this.#replay = new ReplayEngine();
    this.#chart = new ChartEngine();

    container.appendChild(el('div', { class: 'chart-view' }, [
      this.#renderToolbar(),
      chartContainer,
      ReplayControls.render((action, payload) => this.#handleReplayAction(action, payload)),
    ]));

    this.#chart.mount(chartContainer);
    this.#wireReplay();
    this.#bindEvents();
    await this.#loadChart();

    log.info('Chart view mounted');
  }

  /**
   * Tear down the view.
   */
  unmount() {
    this.#unsubs?.();
    this.#unsubs = null;
    this.#replay?.destroy();
    this.#chart?.destroy();
    this.#replay = null;
    this.#chart = null;

    if (this.#container) {
      this.#container.innerHTML = '';
      this.#container.classList.remove('chart-view-root');
      this.#container.classList.add('panel-body-fill');
    }
  }

  /**
   * @returns {HTMLElement}
   */
  #renderToolbar() {
    const symbolOptions = Config.SYMBOLS.map((s) =>
      el('option', { value: s, selected: s === this.#symbol }, [s])
    );
    const tfOptions = Config.TIMEFRAMES.map((t) =>
      el('option', { value: t, selected: t === this.#timeframe }, [t])
    );

    return el('div', { class: 'chart-toolbar' }, [
      el('div', { class: 'chart-toolbar-group' }, [
        el('select', { class: 'data-select', id: 'chart-symbol' }, symbolOptions),
        el('select', { class: 'data-select', id: 'chart-timeframe' }, tfOptions),
        el('button', { class: 'btn btn-sm', id: 'chart-reload' }, ['Reload']),
      ]),
      el('div', { class: 'chart-toolbar-group' }, [
        el('label', { class: 'chart-toggle' }, [
          el('input', { type: 'checkbox', id: 'chart-ema', checked: true }),
          ' EMA 20/50',
        ]),
      ]),
      el('div', { class: 'chart-toolbar-group chart-status', id: 'chart-status' }, [
        'Loading…',
      ]),
    ]);
  }

  #wireReplay() {
    if (!this.#replay) return;

    this.#replay.onTick(({ visible, candle, index, total, fullRefresh }) => {
      if (!this.#chart) return;

      if (fullRefresh || index < 2) {
        this.#chart.setCandles(visible);
      } else {
        this.#chart.updateCandle(candle, visible);
      }

      ReplayControls.update(this.#replay.getState(), candle);
      bus.emit(Events.REPLAY_TICK, { index, total, candle });
    });

    this.#replay.onStateChange((state) => {
      ReplayControls.update(state, this.#replay?.getCurrentCandle());
      bus.emit(Events.REPLAY_STATE, state);
    });
  }

  #bindEvents() {
    const unsubs = [];

    unsubs.push(bus.on(Events.CHART_LOAD, ({ symbol, timeframe }) => {
      this.#symbol = symbol;
      this.#timeframe = timeframe;
      this.#syncSelectors();
      this.#loadChart();
    }));

    unsubs.push(bus.on(Events.REPLAY_COMMAND, ({ action, ...payload }) => {
      this.#handleReplayAction(action, payload);
    }));

    unsubs.push(bus.on(Events.PANEL_RESIZE, () => {
      /* ResizeObserver in ChartEngine handles this */
    }));

    unsubs.push(bus.on(Events.DATA_UPDATED, () => {
      if (this.#container) this.#loadChart();
    }));

    this.#container?.querySelector('#chart-symbol')?.addEventListener('change', (e) => {
      this.#symbol = /** @type {HTMLSelectElement} */ (e.target).value;
      this.#loadChart();
    });

    this.#container?.querySelector('#chart-timeframe')?.addEventListener('change', (e) => {
      this.#timeframe = /** @type {HTMLSelectElement} */ (e.target).value;
      this.#loadChart();
    });

    this.#container?.querySelector('#chart-reload')?.addEventListener('click', () => {
      this.#loadChart();
    });

    this.#container?.querySelector('#chart-ema')?.addEventListener('change', (e) => {
      this.#chart?.setEmaVisible(/** @type {HTMLInputElement} */ (e.target).checked);
      const visible = this.#replay?.getVisibleCandles() ?? [];
      if (visible.length) this.#chart?.setCandles(visible);
    });

    this.#unsubs = () => unsubs.forEach((fn) => fn());
  }

  async #loadChart() {
    const status = document.getElementById('chart-status');
    if (status) status.textContent = `Loading ${this.#symbol} ${this.#timeframe}…`;

    try {
      const candles = await DataManager.getCandles(this.#symbol, this.#timeframe);

      if (candles.length === 0) {
        if (status) {
          status.textContent = 'No data — generate sample or import in Data Manager';
        }
        this.#replay?.load([]);
        this.#chart?.setCandles([]);
        return;
      }

      this.#replay?.load(candles);
      const chartCandles = limitChartCandles(candles);
      this.#chart?.setCandles(chartCandles);
      ReplayControls.update(this.#replay.getState(), candles[candles.length - 1]);

      if (status) {
        const chartNote = chartCandles.length < candles.length
          ? ` (chart: ${chartCandles.length.toLocaleString()})`
          : '';
        status.textContent = `${candles.length.toLocaleString()} candles loaded${chartNote}`;
      }

      bus.emit(Events.CHART_LOADED, {
        symbol: this.#symbol,
        timeframe: this.#timeframe,
        count: candles.length,
      });

      bus.emit(Events.LOG_MESSAGE, {
        message: `Chart loaded: ${this.#symbol} ${this.#timeframe} (${candles.length} candles)`,
        level: 'info',
        time: new Date(),
      });
    } catch (err) {
      if (status) status.textContent = `Error: ${err.message}`;
      bus.emit(Events.LOG_MESSAGE, {
        message: `Chart load failed: ${err.message}`,
        level: 'error',
        time: new Date(),
      });
    }
  }

  /**
   * @param {string} action
   * @param {Record<string, unknown>} [payload]
   */
  #handleReplayAction(action, payload = {}) {
    if (!this.#replay) return;

    switch (action) {
      case 'toggle-play':
        if (this.#replay.getState().status === 'playing') {
          this.#replay.pause();
        } else {
          this.#replay.play();
        }
        break;
      case 'play':
        this.#replay.play();
        break;
      case 'pause':
        this.#replay.pause();
        break;
      case 'next':
        this.#replay.next();
        break;
      case 'prev':
        this.#replay.prev();
        break;
      case 'reset':
        this.#replay.resetReplay();
        break;
      case 'live':
        this.#replay.goLive();
        break;
      case 'speed':
        this.#replay.setSpeed(/** @type {number} */ (payload.speed));
        break;
      case 'jump':
        if (payload.date) this.#replay.jumpToDate(/** @type {number} */ (payload.date));
        break;
      default:
        break;
    }
  }

  #syncSelectors() {
    const sym = this.#container?.querySelector('#chart-symbol');
    const tf = this.#container?.querySelector('#chart-timeframe');
    if (sym) /** @type {HTMLSelectElement} */ (sym).value = this.#symbol;
    if (tf) /** @type {HTMLSelectElement} */ (tf).value = this.#timeframe;
  }
}

export const ChartView = new ChartViewImpl();
