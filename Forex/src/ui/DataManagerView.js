/**
 * Data Manager UI — import, export, gap detection, and dataset overview.
 * @module ui/DataManagerView
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import { formatTimestamp } from '../data/TimeframeUtils.js';
import DataManager from '../data/DataManager.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('DataManagerView');

/**
 * Data Manager view controller.
 */
class DataManagerViewImpl {
  /** @type {HTMLElement|null} */
  #container = null;

  /** @type {Function|null} */
  #unsub = null;

  /**
   * Mount the view into the workspace container.
   * @param {HTMLElement} container
   */
  async mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.remove('panel-body-fill');

    container.appendChild(this.#renderShell());
    this.#bindEvents();
    this.#unsub = bus.on(Events.DATA_UPDATED, () => this.refresh());
    await this.refresh();
    await this.#refreshHealth();
    log.info('Data Manager view mounted');
  }

  /**
   * Tear down the view.
   */
  unmount() {
    this.#unsub?.();
    this.#unsub = null;
    if (this.#container) {
      this.#container.innerHTML = '';
      this.#container.classList.add('panel-body-fill');
    }
  }

  /**
   * Reload the dataset table.
   */
  async refresh() {
    const tbody = this.#container?.querySelector('#data-table-body');
    if (!tbody) return;

    const datasets = await DataManager.listDatasets();
    tbody.innerHTML = '';

    if (datasets.length === 0) {
      tbody.appendChild(el('tr', {}, [
        el('td', { colspan: '7', class: 'data-empty' }, [
          'No data stored. Click "Reload Default Data" or import a CSV/JSON file.',
        ]),
      ]));
      await this.#refreshHealth();
      return;
    }

    for (const ds of datasets.sort((a, b) => a.symbol.localeCompare(b.symbol))) {
      tbody.appendChild(this.#renderRow(ds));
    }
    await this.#refreshHealth();
  }

  async #refreshHealth() {
    const box = this.#container?.querySelector('#data-health');
    if (!box) return;

    try {
      const h = await DataManager.getDataHealth();
      const ok = h.eurusdH1Count > 0;
      box.className = `data-health${ok ? ' data-health-ok' : ' data-health-warn'}`;
      box.textContent = ok
        ? `Data OK — EURUSD H1: ${h.eurusdH1Count.toLocaleString()} candles · ${h.indexedDbDatasets} datasets in IndexedDB`
        : `No data loaded — protocol: ${h.protocol} · manifest: ${h.manifest ? 'found' : 'MISSING'} · gzip: ${h.compression ? 'yes' : 'no (using .json fallback)'}`;
    } catch (err) {
      box.className = 'data-health data-health-warn';
      box.textContent = `Health check failed: ${err.message}`;
    }
  }

  /**
   * @returns {HTMLElement}
   */
  #renderShell() {
    const symbolOptions = Config.SYMBOLS.map((s) =>
      el('option', { value: s }, [s])
    );
    const tfOptions = Config.TIMEFRAMES.map((t) =>
      el('option', { value: t }, [t])
    );

    return el('div', { class: 'data-manager' }, [
      el('div', { class: 'data-health', id: 'data-health' }, ['Checking data…']),
      el('div', { class: 'data-toolbar' }, [
        el('div', { class: 'data-toolbar-group' }, [
          el('label', { class: 'data-label' }, ['Symbol']),
          el('select', { class: 'data-select', id: 'import-symbol' }, symbolOptions),
          el('label', { class: 'data-label' }, ['TF']),
          el('select', { class: 'data-select', id: 'import-tf' }, tfOptions),
          el('label', { class: 'btn btn-primary data-import-btn' }, [
            'Import File',
            el('input', {
              type: 'file',
              id: 'import-file',
              accept: '.csv,.json,.gz,.csv.gz,.json.gz',
              hidden: true,
            }),
          ]),
        ]),
        el('div', { class: 'data-toolbar-group' }, [
          el('button', { class: 'btn btn-secondary', id: 'btn-load-defaults' }, [
            'Reload Default Data',
          ]),
          el('button', { class: 'btn btn-secondary', id: 'btn-gen-all' }, [
            'Generate Sample (All Pairs)',
          ]),
        ]),
      ]),
      el('div', { class: 'data-table-wrap' }, [
        el('table', { class: 'data-table' }, [
          el('thead', {}, [
            el('tr', {}, [
              el('th', {}, ['Symbol']),
              el('th', {}, ['TF']),
              el('th', {}, ['Candles']),
              el('th', {}, ['From']),
              el('th', {}, ['To']),
              el('th', {}, ['Gaps']),
              el('th', {}, ['Actions']),
            ]),
          ]),
          el('tbody', { id: 'data-table-body' }),
        ]),
      ]),
      el('div', { class: 'data-hint' }, [
        'Supported: CSV (timestamp,open,high,low,close,volume), JSON, .gz compressed. ',
        'Data is stored locally in IndexedDB.',
      ]),
    ]);
  }

  /**
   * @param {import('../data/Candle.js').DatasetMetadata} ds
   * @returns {HTMLElement}
   */
  #renderRow(ds) {
    const gapCell = el('td', { class: 'data-gaps', id: `gaps-${ds.key}` }, ['—']);

    this.#loadGaps(ds, gapCell);

    return el('tr', { dataset: { key: ds.key } }, [
      el('td', { class: 'data-symbol' }, [ds.symbol]),
      el('td', {}, [ds.timeframe]),
      el('td', {}, [ds.count.toLocaleString()]),
      el('td', { class: 'data-date' }, [formatTimestamp(ds.firstTimestamp)]),
      el('td', { class: 'data-date' }, [formatTimestamp(ds.lastTimestamp)]),
      gapCell,
      el('td', { class: 'data-actions' }, [
        el('button', {
          class: 'btn btn-sm',
          title: 'Export CSV',
          dataset: { action: 'export-csv', symbol: ds.symbol, tf: ds.timeframe },
        }, ['CSV']),
        el('button', {
          class: 'btn btn-sm',
          title: 'Export JSON',
          dataset: { action: 'export-json', symbol: ds.symbol, tf: ds.timeframe },
        }, ['JSON']),
        el('button', {
          class: 'btn btn-sm',
          title: 'Export compressed JSON',
          dataset: { action: 'export-gz', symbol: ds.symbol, tf: ds.timeframe },
        }, ['.gz']),
        el('button', {
          class: 'btn btn-sm btn-danger',
          title: 'Delete dataset',
          dataset: { action: 'delete', symbol: ds.symbol, tf: ds.timeframe },
        }, ['✕']),
      ]),
    ]);
  }

  /**
   * @param {import('../data/Candle.js').DatasetMetadata} ds
   * @param {HTMLElement} cell
   */
  async #loadGaps(ds, cell) {
    try {
      const gaps = await DataManager.findGaps(ds.symbol, ds.timeframe);
      const total = gaps.reduce((sum, g) => sum + g.missingCount, 0);
      cell.textContent = gaps.length === 0 ? 'None' : `${gaps.length} (${total} candles)`;
      cell.classList.toggle('data-gaps-warn', gaps.length > 0);
    } catch {
      cell.textContent = 'Error';
    }
  }

  #bindEvents() {
    const fileInput = this.#container.querySelector('#import-file');

    fileInput?.addEventListener('change', async (e) => {
      const file = /** @type {HTMLInputElement} */ (e.target).files?.[0];
      if (!file) return;

      const symbol = /** @type {HTMLSelectElement} */ (
        this.#container.querySelector('#import-symbol')
      ).value;
      const timeframe = /** @type {HTMLSelectElement} */ (
        this.#container.querySelector('#import-tf')
      ).value;

      try {
        await DataManager.importFile(file, symbol, timeframe);
        await this.refresh();
      } catch (err) {
        bus.emit(Events.DATA_ERROR, { error: err });
        bus.emit(Events.LOG_MESSAGE, {
          message: `Import failed: ${err.message}`,
          level: 'error',
          time: new Date(),
        });
      }

      fileInput.value = '';
    });

    this.#container.querySelector('#btn-load-defaults')?.addEventListener('click', async () => {
      const btn = /** @type {HTMLButtonElement} */ (
        this.#container.querySelector('#btn-load-defaults')
      );
      btn.disabled = true;
      btn.textContent = 'Loading…';
      try {
        await DataManager.seedDefaults({ force: true });
        await this.refresh();
      } finally {
        btn.disabled = false;
        btn.textContent = 'Reload Default Data';
      }
    });

    this.#container.querySelector('#btn-gen-all')?.addEventListener('click', async () => {
      const timeframe = Config.DEFAULT_TIMEFRAME;
      for (const symbol of Config.SYMBOLS) {
        await DataManager.generateSample(symbol, timeframe);
      }
      await this.refresh();
    });

    this.#container.addEventListener('click', async (e) => {
      const btn = /** @type {HTMLElement} */ (e.target).closest('[data-action]');
      if (!btn) return;

      const { action, symbol, tf } = btn.dataset;
      try {
        if (action === 'export-csv') await DataManager.exportDataset(symbol, tf, 'csv');
        if (action === 'export-json') await DataManager.exportDataset(symbol, tf, 'json');
        if (action === 'export-gz') await DataManager.exportDataset(symbol, tf, 'json', true);
        if (action === 'delete') {
          if (confirm(`Delete all ${symbol} ${tf} data?`)) {
            await DataManager.deleteDataset(symbol, tf);
            await this.refresh();
          }
        }
      } catch (err) {
        bus.emit(Events.LOG_MESSAGE, {
          message: err.message,
          level: 'error',
          time: new Date(),
        });
      }
    });
  }
}

export const DataManagerView = new DataManagerViewImpl();
