/**
 * Data Manager UI — import, export, gap detection, and dataset overview.
 * @module ui/DataManagerView
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import { formatTimestamp } from '../data/TimeframeUtils.js';
import DataManager from '../data/DataManager.js';
import { createHelpButton } from '../utils/contextHelp.js';
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
      const candleCount = Math.max(h.eurusdH1Count, h.eurusdH1MetaCount ?? 0);
      const ok = candleCount > 0;
      box.className = `data-health${ok ? ' data-health-ok' : ' data-health-warn'}`;
      if (ok) {
        box.textContent = `Data OK — EURUSD H1: ${candleCount.toLocaleString()} candles · ${h.indexedDbDatasets} datasets in IndexedDB`;
      } else if (h.protocol === 'file:') {
        box.textContent = 'Không load được qua file:// — chạy: cd Forex && python3 -m http.server 8080 rồi mở http://localhost:8080';
      } else {
        box.textContent = `Chưa có dữ liệu — manifest: ${h.manifest ? 'OK' : 'MISSING'} · gzip: ${h.compression ? 'yes' : 'no'} · base: ${h.workingBase ?? 'none'}`;
      }
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
          el('button', { class: 'btn btn-secondary', id: 'btn-reload-eurusd-h1' }, [
            'Cập nhật EURUSD H1',
          ]),
          el('button', { class: 'btn btn-danger btn-sm', id: 'btn-delete-h1' }, [
            'Xóa tất cả H1',
          ]),
          el('button', { class: 'btn btn-secondary', id: 'btn-gen-all' }, [
            'Generate Sample (All Pairs)',
          ]),
        ]),
        createHelpButton('data'),
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
        'Dữ liệu Dukascopy: chart H1 có khoảng trống cuối tuần (thị trường đóng cửa) — bình thường. ',
        'Cột Gaps chỉ báo thiếu nến bất thường (không tính T7/CN). ',
        'CSV/JSON/.gz → IndexedDB.',
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
      if (gaps.length === 0) {
        cell.textContent = 'OK';
      } else {
        cell.textContent = `${gaps.length} lỗ (${total} nến)`;
        cell.title = 'Thiếu nến giữa phiên — không tính cuối tuần/lễ';
      }
      cell.classList.toggle('data-gaps-warn', gaps.length > 0);
    } catch {
      cell.textContent = 'Error';
    }
  }

  /**
   * @param {string} btnId
   * @param {string} loadingLabel
   * @param {string} doneLabel
   * @param {() => Promise<unknown>} action
   */
  async #runReload(btnId, loadingLabel, doneLabel, action) {
    const btn = /** @type {HTMLButtonElement} */ (
      this.#container?.querySelector(`#${btnId}`)
    );
    const health = this.#container?.querySelector('#data-health');
    btn.disabled = true;
    btn.textContent = loadingLabel;
    if (health) {
      health.className = 'data-health';
      health.textContent = 'Đang tải dữ liệu…';
    }

    try {
      const result = await action();
      await this.refresh();

      if (result && typeof result === 'object' && 'loaded' in result && result.loaded.length === 0) {
        const msg = result.errors?.join(' · ') || 'Không tải được dataset nào';
        bus.emit(Events.LOG_MESSAGE, { message: msg, level: 'error', time: new Date() });
      }
    } catch (err) {
      bus.emit(Events.LOG_MESSAGE, {
        message: `Reload failed: ${err.message}`,
        level: 'error',
        time: new Date(),
      });
      await this.#refreshHealth();
    } finally {
      btn.disabled = false;
      btn.textContent = doneLabel;
    }
  }

  #bindEvents() {
    const fileInput = this.#container?.querySelector('#import-file');

    fileInput?.addEventListener('change', async (e) => {
      const file = /** @type {HTMLInputElement} */ (e.target).files?.[0];
      if (!file) return;

      const symbol = /** @type {HTMLSelectElement} */ (
        this.#container?.querySelector('#import-symbol')
      ).value;
      const timeframe = /** @type {HTMLSelectElement} */ (
        this.#container?.querySelector('#import-tf')
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

    this.#container?.querySelector('#btn-load-defaults')?.addEventListener('click', async () => {
      await this.#runReload('btn-load-defaults', 'Loading…', 'Reload Default Data', () =>
        DataManager.seedDefaults({ force: true })
      );
    });

    this.#container?.querySelector('#btn-reload-eurusd-h1')?.addEventListener('click', async () => {
      await this.#runReload('btn-reload-eurusd-h1', 'Đang tải…', 'Cập nhật EURUSD H1', () =>
        DataManager.reloadBundledDataset('EURUSD', 'H1')
      );
    });

    this.#container?.querySelector('#btn-delete-h1')?.addEventListener('click', async () => {
      if (!confirm('Xóa toàn bộ dữ liệu H1 (mọi cặp) trong IndexedDB?')) return;
      const btn = /** @type {HTMLButtonElement} */ (
        this.#container?.querySelector('#btn-delete-h1')
      );
      btn.disabled = true;
      try {
        const count = await DataManager.deleteTimeframe('H1');
        await this.refresh();
        bus.emit(Events.LOG_MESSAGE, {
          message: count > 0 ? `Đã xóa ${count} dataset H1.` : 'Không có dữ liệu H1.',
          level: 'info',
          time: new Date(),
        });
      } catch (err) {
        bus.emit(Events.LOG_MESSAGE, {
          message: `Xóa H1 thất bại: ${err.message}`,
          level: 'error',
          time: new Date(),
        });
      } finally {
        btn.disabled = false;
      }
    });

    this.#container?.querySelector('#btn-gen-all')?.addEventListener('click', async () => {
      const btn = /** @type {HTMLButtonElement} */ (
        this.#container?.querySelector('#btn-gen-all')
      );
      btn.disabled = true;
      try {
        const timeframe = Config.DEFAULT_TIMEFRAME;
        for (const symbol of Config.SYMBOLS) {
          await DataManager.generateSample(symbol, timeframe);
        }
        await this.refresh();
      } catch (err) {
        bus.emit(Events.LOG_MESSAGE, {
          message: `Sample generation failed: ${err.message}`,
          level: 'error',
          time: new Date(),
        });
      } finally {
        btn.disabled = false;
      }
    });

    this.#container?.addEventListener('click', async (e) => {
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
