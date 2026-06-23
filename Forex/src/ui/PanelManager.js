/**
 * Resizable panel manager for the main content area.
 * Supports horizontal and vertical split panels with drag handles.
 * @module ui/PanelManager
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el, clamp, loadFromStorage, saveToStorage } from '../utils/dom.js';
import { createLogger } from '../utils/logger.js';
import DataManager from '../data/DataManager.js';

const log = createLogger('PanelManager');

/** Views where the data watchlist sidebar is shown. */
const WATCHLIST_VIEWS = new Set(['chart', 'data']);

/**
 * Manages resizable split panels in the main workspace.
 */
class PanelManagerImpl {
  /** @type {number} */
  leftPanelWidth = 280;

  /** @type {number} */
  bottomPanelHeight = 200;

  /**
   * Render the panel layout.
   * @returns {HTMLElement}
   */
  render() {
    const saved = loadFromStorage(Config.STORAGE_KEYS.PANEL_SIZES, {
      left: Config.LAYOUT.PANEL_MIN_WIDTH + 80,
      bottom: 200,
    });

    this.leftPanelWidth = saved.left ?? 280;
    this.bottomPanelHeight = saved.bottom ?? 200;

    return el('div', { class: 'panel-workspace watchlist-visible', id: 'panel-workspace' }, [
      el('div', { class: 'panel-row panel-row-top' }, [
        el('div', {
          class: 'panel panel-left',
          id: 'panel-left',
          style: `width: ${this.leftPanelWidth}px`,
        }, [
          el('div', { class: 'panel-header' }, [
            el('span', { class: 'panel-title' }, ['Watchlist']),
          ]),
          el('div', { class: 'panel-body' }, [
            el('div', { class: 'watchlist', id: 'watchlist' }, []),
          ]),
        ]),
        el('div', { class: 'resize-handle resize-v', 'data-resize': 'left' }),
        el('div', { class: 'panel panel-center', id: 'panel-center' }, [
          el('div', { class: 'panel-header' }, [
            el('span', { class: 'panel-title' }, ['Workspace']),
          ]),
          el('div', { class: 'panel-body panel-body-fill', id: 'view-placeholder' }),
        ]),
      ]),
      el('div', { class: 'resize-handle resize-h', 'data-resize': 'bottom' }),
      el('div', {
        class: 'panel panel-bottom',
        id: 'panel-bottom',
        style: `height: ${this.bottomPanelHeight}px`,
      }, [
        el('div', { class: 'panel-header' }, [
          el('span', { class: 'panel-title' }, ['Output / Log']),
        ]),
        el('div', { class: 'panel-body panel-log', id: 'panel-log' }, [
          el('div', { class: 'log-entry log-info' }, [
            `[${new Date().toLocaleTimeString()}] Price Action Research Lab initialized.`,
          ]),
          el('div', { class: 'log-entry' }, [
            'Phase 10 — AI Signal Scoring & Web Workers ready.',
          ]),
        ]),
      ]),
    ]);
  }

  /**
   * Attach resize drag handlers.
   * @param {HTMLElement} shell
   */
  init(shell) {
    const workspace = shell.querySelector('.panel-workspace');
    if (!workspace) return;

    workspace.querySelectorAll('.resize-handle').forEach((handle) => {
      handle.addEventListener('mousedown', (e) => this.#startResize(e, handle, workspace));
    });

    this.#refreshWatchlist();
    bus.on(Events.DATA_UPDATED, () => this.#refreshWatchlist());
    bus.on(Events.VIEW_ACTIVE, ({ view }) => this.#setWatchlistVisible(view));
    bus.on(Events.LOG_MESSAGE, ({ message, level, time }) => {
      this.#appendLog(message, level, time);
    });

    const watchlist = document.getElementById('watchlist');
    watchlist?.addEventListener('click', (e) => {
      const item = /** @type {HTMLElement} */ (e.target).closest('.watchlist-item');
      if (!item?.dataset.symbol) return;
      bus.emit(Events.NAVIGATE, { view: 'chart' });
      bus.emit(Events.CHART_LOAD, {
        symbol: item.dataset.symbol,
        timeframe: item.dataset.timeframe,
      });
    });

    log.info('Panel manager initialized');
  }

  /**
   * Show watchlist only on views that use it (chart navigation, data overview).
   * @param {string} viewId
   */
  #setWatchlistVisible(viewId) {
    const workspace = document.getElementById('panel-workspace');
    if (!workspace) return;
    workspace.classList.toggle('watchlist-visible', WATCHLIST_VIEWS.has(viewId));
  }

  /**
   * Refresh watchlist from stored dataset metadata.
   */
  async #refreshWatchlist() {
    const container = document.getElementById('watchlist');
    if (!container) return;

    const datasets = await DataManager.listDatasets();
    const metaMap = new Map(datasets.map((d) => [`${d.symbol}|${d.timeframe}`, d]));

    container.innerHTML = '';

    for (const symbol of Config.SYMBOLS) {
      for (const tf of Config.TIMEFRAMES) {
        const meta = metaMap.get(`${symbol}|${tf}`);
        const status = meta
          ? `${meta.count.toLocaleString()} candles`
          : 'No data';

        container.appendChild(el('div', {
          class: 'watchlist-item',
          dataset: { symbol, timeframe: tf },
        }, [
          el('span', { class: 'watchlist-symbol' }, [symbol]),
          el('span', { class: 'watchlist-tf' }, [tf]),
          el('span', {
            class: `watchlist-status${meta ? ' watchlist-status-ok' : ''}`,
          }, [status]),
        ]));
      }
    }
  }

  /**
   * @param {string} message
   * @param {string} [level='info']
   * @param {Date} [time=new Date()]
   */
  #appendLog(message, level = 'info', time = new Date()) {
    const logPanel = document.getElementById('panel-log');
    if (!logPanel) return;

    const entry = el('div', { class: `log-entry log-${level}` }, [
      `[${time.toLocaleTimeString()}] ${message}`,
    ]);
    logPanel.appendChild(entry);
    logPanel.scrollTop = logPanel.scrollHeight;
  }

  /**
   * @param {MouseEvent} e
   * @param {HTMLElement} handle
   * @param {HTMLElement} workspace
   */
  #startResize(e, handle, workspace) {
    e.preventDefault();
    const direction = handle.dataset.resize;
    const startX = e.clientX;
    const startY = e.clientY;
    const startLeft = this.leftPanelWidth;
    const startBottom = this.bottomPanelHeight;

    document.body.classList.add('resizing');

    /**
     * @param {MouseEvent} moveEvent
     */
    const onMove = (moveEvent) => {
      if (direction === 'left') {
        const delta = moveEvent.clientX - startX;
        this.leftPanelWidth = clamp(
          startLeft + delta,
          Config.LAYOUT.PANEL_MIN_WIDTH,
          workspace.clientWidth * 0.5
        );
        const panel = workspace.querySelector('#panel-left');
        if (panel) panel.style.width = `${this.leftPanelWidth}px`;
      }

      if (direction === 'bottom') {
        const delta = startY - moveEvent.clientY;
        this.bottomPanelHeight = clamp(
          startBottom + delta,
          Config.LAYOUT.PANEL_MIN_HEIGHT,
          workspace.clientHeight * 0.6
        );
        const panel = workspace.querySelector('#panel-bottom');
        if (panel) panel.style.height = `${this.bottomPanelHeight}px`;
      }

      bus.emit(Events.PANEL_RESIZE, {
        left: this.leftPanelWidth,
        bottom: this.bottomPanelHeight,
      });
    };

    const onUp = () => {
      document.body.classList.remove('resizing');
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      saveToStorage(Config.STORAGE_KEYS.PANEL_SIZES, {
        left: this.leftPanelWidth,
        bottom: this.bottomPanelHeight,
      });
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }
}

export const PanelManager = new PanelManagerImpl();
