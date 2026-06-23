/**
 * Chart view — candlestick chart with replay controls and data loading.
 * @module ui/ChartView
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el, loadFromStorage } from '../utils/dom.js';
import DataManager from '../data/DataManager.js';
import { ChartEngine } from '../chart/ChartEngine.js';
import { ReplayEngine } from '../replay/ReplayEngine.js';
import { ReplayControls } from './ReplayControls.js';
import { createHelpButton } from '../utils/contextHelp.js';
import { createLogger } from '../utils/logger.js';
import {
  buildSymbolOptions,
  buildTimeframeOptions,
  fillDatasetSelectors,
  resolveDatasetSelection,
} from '../utils/runnableDatasets.js';
import { takePendingChartFocus } from '../utils/chartNavigation.js';
import { formatTimestamp } from '../data/TimeframeUtils.js';

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

  /** @type {import('../data/Candle.js').DatasetMetadata[]} */
  #runnableDatasets = [];

  /** @type {Function|null} */
  #unsubs = null;

  /** @type {number|null} */
  #pendingJump = null;

  /** @type {import('../utils/chartNavigation.js').ChartSignalHighlight|null} */
  #pendingSignal = null;

  /** @type {import('../utils/chartNavigation.js').ChartSignalHighlight|null} */
  #activeSignal = null;

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

    const pending = takePendingChartFocus();
    if (pending) {
      this.#symbol = pending.symbol;
      this.#timeframe = pending.timeframe;
      if (pending.jumpTo != null) this.#pendingJump = pending.jumpTo;
      if (pending.signal) this.#pendingSignal = pending.signal;
    }

    this.#runnableDatasets = await DataManager.listRunnableDatasets();
    const resolved = resolveDatasetSelection(
      this.#runnableDatasets,
      this.#symbol,
      this.#timeframe
    );
    if (resolved.symbol) this.#symbol = resolved.symbol;
    if (resolved.timeframe) this.#timeframe = resolved.timeframe;

    const chartContainer = el('div', { class: 'chart-container', id: 'chart-container' });

    this.#replay = new ReplayEngine();
    this.#chart = new ChartEngine();

    container.appendChild(el('div', { class: 'chart-view' }, [
      this.#renderToolbar(),
      el('div', { class: 'chart-signal-banner', id: 'chart-signal-banner', hidden: true }),
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
    const symbolOptions = buildSymbolOptions(this.#runnableDatasets, this.#symbol);
    const tfOptions = buildTimeframeOptions(
      this.#runnableDatasets,
      this.#symbol,
      this.#timeframe
    );

    return el('div', { class: 'chart-toolbar' }, [
      el('div', { class: 'chart-toolbar-group' }, [
        el('select', {
          class: 'data-select',
          id: 'chart-symbol',
          disabled: this.#runnableDatasets.length === 0,
        }, symbolOptions),
        el('select', {
          class: 'data-select',
          id: 'chart-timeframe',
          disabled: this.#runnableDatasets.length === 0,
        }, tfOptions),
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
      createHelpButton('chart'),
    ]);
  }

  #wireReplay() {
    if (!this.#replay) return;

    this.#replay.onTick(({ visible, candle, index, total, fullRefresh }) => {
      if (!this.#chart) return;

      if (fullRefresh || index < 2) {
        this.#chart.setCandles(visible, { fit: !this.#activeSignal });
        if (this.#activeSignal) {
          this.#chart.setSignalOverlay(this.#activeSignal, visible);
        }
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

    unsubs.push(bus.on(Events.CHART_LOAD, ({ symbol, timeframe, jumpTo, signal }) => {
      this.#symbol = symbol;
      this.#timeframe = timeframe;
      if (jumpTo != null) this.#pendingJump = jumpTo;
      if (signal) this.#pendingSignal = signal;
      this.#syncSelectors();
      this.#loadChart();
    }));

    unsubs.push(bus.on(Events.REPLAY_COMMAND, ({ action, ...payload }) => {
      this.#handleReplayAction(action, payload);
    }));

    unsubs.push(bus.on(Events.PANEL_RESIZE, () => {
      /* ResizeObserver in ChartEngine handles this */
    }));

    unsubs.push(bus.on(Events.DATA_UPDATED, async () => {
      if (this.#container) {
        await this.#refreshDatasetSelectors();
        this.#loadChart();
      }
    }));

    this.#container?.querySelector('#chart-symbol')?.addEventListener('change', (e) => {
      this.#symbol = /** @type {HTMLSelectElement} */ (e.target).value;
      this.#clearSignalContext();
      this.#syncTimeframeOptions();
      this.#loadChart();
    });

    this.#container?.querySelector('#chart-timeframe')?.addEventListener('change', (e) => {
      this.#timeframe = /** @type {HTMLSelectElement} */ (e.target).value;
      this.#clearSignalContext();
      this.#loadChart();
    });

    this.#container?.querySelector('#chart-reload')?.addEventListener('click', () => {
      this.#clearSignalContext();
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
          status.textContent = 'No data — import or reload defaults in Data Manager';
        }
        this.#replay?.load([]);
        this.#chart?.setCandles([]);
        return;
      }

      this.#replay?.load(candles);

      if (this.#pendingJump != null) {
        this.#replay.jumpToDate(this.#pendingJump);
        this.#pendingJump = null;
      } else {
        const visible = this.#replay.getVisibleCandles();
        this.#chart?.setCandles(visible);
      }

      ReplayControls.update(this.#replay.getState(), this.#replay.getCurrentCandle());

      if (this.#pendingSignal) {
        this.#activeSignal = this.#pendingSignal;
        this.#pendingSignal = null;
        const visible = this.#replay.getVisibleCandles();
        this.#chart?.setSignalOverlay(this.#activeSignal, visible);
        this.#showSignalBanner(this.#activeSignal);
      }

      if (status) {
        if (this.#activeSignal) {
          status.textContent = `${this.#activeSignal.symbol} ${this.#activeSignal.timeframe} · ${this.#activeSignal.strategyName} · ${this.#activeSignal.direction.toUpperCase()} @ ${formatTimestamp(this.#activeSignal.time)}`;
        } else {
          const visibleCount = this.#replay?.getVisibleCandles().length ?? candles.length;
          status.textContent = `${visibleCount.toLocaleString()} / ${candles.length.toLocaleString()} candles`;
        }
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

  async #refreshDatasetSelectors() {
    this.#runnableDatasets = await DataManager.listRunnableDatasets();
    const symSel = this.#container?.querySelector('#chart-symbol');
    const tfSel = this.#container?.querySelector('#chart-timeframe');
    if (!symSel || !tfSel) return;

    const resolved = fillDatasetSelectors(
      /** @type {HTMLSelectElement} */ (symSel),
      /** @type {HTMLSelectElement} */ (tfSel),
      this.#runnableDatasets,
      this.#symbol,
      this.#timeframe
    );
    if (resolved.symbol) this.#symbol = resolved.symbol;
    if (resolved.timeframe) this.#timeframe = resolved.timeframe;
  }

  #syncTimeframeOptions() {
    const tfSel = this.#container?.querySelector('#chart-timeframe');
    if (!tfSel) return;

    const resolved = resolveDatasetSelection(
      this.#runnableDatasets,
      this.#symbol,
      this.#timeframe
    );
    this.#timeframe = resolved.timeframe ?? this.#timeframe;

    tfSel.innerHTML = '';
    for (const opt of buildTimeframeOptions(
      this.#runnableDatasets,
      this.#symbol,
      this.#timeframe
    )) {
      tfSel.appendChild(opt);
    }
    if (this.#timeframe) /** @type {HTMLSelectElement} */ (tfSel).value = this.#timeframe;
  }

  #clearSignalContext() {
    this.#activeSignal = null;
    this.#pendingSignal = null;
    this.#chart?.clearSignalOverlay();
    const banner = this.#container?.querySelector('#chart-signal-banner');
    if (banner) {
      banner.hidden = true;
      banner.innerHTML = '';
    }
  }

  /**
   * @param {import('../utils/chartNavigation.js').ChartSignalHighlight} signal
   */
  #showSignalBanner(signal) {
    const banner = this.#container?.querySelector('#chart-signal-banner');
    if (!banner) return;

    banner.hidden = false;
    banner.innerHTML = '';

    const chips = [
      el('span', { class: 'chart-signal-chip chart-signal-chip-strategy' }, [signal.strategyName]),
      el('span', { class: 'chart-signal-chip' }, [signal.symbol]),
      el('span', { class: 'chart-signal-chip' }, [signal.timeframe]),
      el('span', { class: `chart-signal-chip chart-signal-dir-${signal.direction}` }, [
        signal.direction.toUpperCase(),
      ]),
    ];
    if (signal.score != null) {
      chips.push(el('span', { class: 'chart-signal-chip' }, [`AI ${Math.round(signal.score)}/100`]));
    }
    if (signal.candleIndex != null) {
      chips.push(el('span', { class: 'chart-signal-chip' }, [`Bar ${signal.candleIndex}`]));
    }
    chips.push(el('span', { class: 'chart-signal-chip chart-signal-time' }, [formatTimestamp(signal.time)]));

    banner.appendChild(el('div', { class: 'chart-signal-banner-main' }, chips));
    banner.appendChild(el('p', { class: 'chart-signal-banner-reason' }, [signal.reason || '']));
    banner.appendChild(el('p', { class: 'chart-signal-banner-levels' }, [
      `Entry ${signal.entry.toFixed(5)} · SL ${signal.sl.toFixed(5)} · TP ${signal.tp.toFixed(5)} · ${signal.rr.toFixed(1)}R`,
    ]));
    banner.appendChild(el('p', { class: 'chart-signal-banner-hint' }, [
      'Replay dừng tại nến signal — mũi tên → xem setup hình thành từng bước (không lộ tương lai).',
    ]));
  }
}

export const ChartView = new ChartViewImpl();
