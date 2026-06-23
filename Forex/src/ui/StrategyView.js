/**
 * Strategy management UI — plugin list, parameters, and scan controls.
 * @module ui/StrategyView
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el, loadFromStorage } from '../utils/dom.js';
import DataManager from '../data/DataManager.js';
import StrategyEngine from '../strategy/StrategyEngine.js';
import { registry } from '../plugin/PluginRegistry.js';
import { downloadFile } from '../data/DataExporter.js';
import { createHelpButton } from '../utils/contextHelp.js';
import { createLogger } from '../utils/logger.js';
import {
  buildSymbolOptions,
  buildTimeframeOptions,
  resolveDatasetSelection,
  uniqueSymbols,
  timeframesForSymbol,
} from '../utils/runnableDatasets.js';

const log = createLogger('StrategyView');

/**
 * Strategy workspace view.
 */
class StrategyViewImpl {
  /** @type {HTMLElement|null} */
  #container = null;

  /** @type {string|null} */
  #selectedId = null;

  /** @type {string|null} */
  #selectedSymbol = null;

  /** @type {string|null} */
  #selectedTimeframe = null;

  /** @type {import('../data/Candle.js').DatasetMetadata[]} */
  #runnableDatasets = [];

  /** @type {(() => void)|null} */
  #unsub = null;

  /**
   * @param {HTMLElement} container
   */
  async mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.remove('panel-body-fill');

    const settings = loadFromStorage(Config.STORAGE_KEYS.SETTINGS, {});
    const plugins = StrategyEngine.listPlugins();
    this.#selectedId = plugins[0]?.id ?? null;

    await this.#refreshDataState(settings);

    container.appendChild(el('div', { class: 'strategy-view' }, [
      this.#renderToolbar(),
      el('div', { class: 'strategy-body' }, [
        this.#renderPluginList(plugins),
        this.#renderDetailPanel(),
      ]),
    ]));

    this.#bindEvents();
    this.#renderDetail();
    log.info('Strategy view mounted');
  }

  unmount() {
    this.#unsub?.();
    this.#unsub = null;
    if (this.#container) {
      this.#container.innerHTML = '';
      this.#container.classList.add('panel-body-fill');
    }
  }

  /**
   * @param {Record<string, unknown>} [settings]
   */
  async #refreshDataState(settings = loadFromStorage(Config.STORAGE_KEYS.SETTINGS, {})) {
    this.#runnableDatasets = await DataManager.listRunnableDatasets();

    const resolved = resolveDatasetSelection(
      this.#runnableDatasets,
      typeof settings.symbol === 'string' ? settings.symbol : Config.DEFAULT_SYMBOL,
      typeof settings.timeframe === 'string' ? settings.timeframe : Config.DEFAULT_TIMEFRAME
    );
    this.#selectedSymbol = resolved.symbol;
    this.#selectedTimeframe = resolved.timeframe;
  }

  /**
   * @returns {string[]}
   */
  #availableSymbols() {
    return uniqueSymbols(this.#runnableDatasets);
  }

  /**
   * @param {string} symbol
   * @returns {string[]}
   */
  #availableTimeframes(symbol) {
    return timeframesForSymbol(this.#runnableDatasets, symbol);
  }

  /**
   * @returns {HTMLElement}
   */
  #renderToolbar() {
    const hasData = this.#runnableDatasets.length > 0;
    const children = [];

    if (hasData) {
      children.push(el('div', { class: 'strategy-toolbar-group', id: 'strat-data-selectors' }, [
        el('label', { class: 'data-label' }, ['Symbol']),
        el('select', { class: 'data-select', id: 'strat-symbol' }, buildSymbolOptions(
          this.#runnableDatasets,
          this.#selectedSymbol
        )),
        el('label', { class: 'data-label' }, ['TF']),
        el('select', { class: 'data-select', id: 'strat-timeframe' }, buildTimeframeOptions(
          this.#runnableDatasets,
          this.#selectedSymbol,
          this.#selectedTimeframe
        )),
      ]));
    } else {
      children.push(el('div', { class: 'strategy-toolbar-group', id: 'strat-no-data' }, [
        el('span', { class: 'strategy-no-data-hint' }, [
          'Chưa có dữ liệu nến. Mở Data Manager → Reload Default Data hoặc Import file. Cần chạy app qua http:// (không mở file://).',
        ]),
      ]));
    }

    children.push(el('div', { class: 'strategy-toolbar-group' }, [
      el('button', {
        class: 'btn btn-primary',
        id: 'strat-run-selected',
        disabled: !hasData,
      }, ['Run Selected']),
      el('button', {
        class: 'btn btn-secondary',
        id: 'strat-run-all',
        disabled: !hasData,
      }, ['Run All Enabled']),
      createHelpButton('strategy'),
    ]));

    return el('div', { class: 'strategy-toolbar', id: 'strategy-toolbar' }, children);
  }

  async #refreshToolbar() {
    const settings = loadFromStorage(Config.STORAGE_KEYS.SETTINGS, {});
    await this.#refreshDataState(settings);

    const toolbar = this.#container?.querySelector('#strategy-toolbar');
    if (!toolbar) return;

    const newToolbar = this.#renderToolbar();
    toolbar.replaceWith(newToolbar);
    this.#bindToolbarEvents();
  }

  /**
   * @param {import('../plugin/PluginRegistry.js').PluginDescriptor[]} plugins
   * @returns {HTMLElement}
   */
  #renderPluginList(plugins) {
    const items = plugins.map((p) => {
      const config = StrategyEngine.getConfig(p.id);
      const last = StrategyEngine.getLastResult(p.id);

      return el('button', {
        class: `strategy-plugin-item${p.id === this.#selectedId ? ' active' : ''}`,
        dataset: { id: p.id },
      }, [
        el('div', { class: 'strategy-plugin-header' }, [
          el('span', { class: 'strategy-plugin-name' }, [p.name]),
          el('span', { class: `strategy-badge${config.enabled ? '' : ' disabled'}` }, [
            config.enabled ? 'ON' : 'OFF',
          ]),
        ]),
        el('div', { class: 'strategy-plugin-meta' }, [
          el('span', {}, [`v${p.version}`]),
          el('span', {}, [last ? `${last.signals.length} signals` : 'Not scanned']),
        ]),
      ]);
    });

    return el('aside', { class: 'strategy-list', id: 'strategy-list' }, items);
  }

  /**
   * @returns {HTMLElement}
   */
  #renderDetailPanel() {
    return el('div', { class: 'strategy-detail', id: 'strategy-detail' }, [
      el('p', { class: 'strategy-loading' }, ['Select a strategy…']),
    ]);
  }

  #bindEvents() {
    this.#container?.querySelector('#strategy-list')?.addEventListener('click', (e) => {
      const item = /** @type {HTMLElement} */ (e.target).closest('.strategy-plugin-item');
      if (!item?.dataset.id) return;
      this.#selectedId = item.dataset.id;
      this.#container?.querySelectorAll('.strategy-plugin-item').forEach((node) => {
        node.classList.toggle('active', node.dataset.id === this.#selectedId);
      });
      this.#renderDetail();
    });

    this.#bindToolbarEvents();

    const unsubs = [
      bus.on(Events.SIGNALS_GENERATED, () => {
        this.#refreshPluginList();
        this.#renderDetail();
      }),
      bus.on(Events.DATA_UPDATED, () => {
        this.#refreshToolbar();
      }),
      bus.on(Events.APP_READY, () => {
        this.#refreshToolbar();
      }),
    ];

    this.#unsub = () => unsubs.forEach((fn) => fn());
  }

  #bindToolbarEvents() {
    this.#container?.querySelector('#strat-symbol')?.addEventListener('change', (e) => {
      this.#selectedSymbol = /** @type {HTMLSelectElement} */ (e.target).value;
      const tfs = this.#availableTimeframes(this.#selectedSymbol);
      this.#selectedTimeframe = tfs.includes(this.#selectedTimeframe ?? '')
        ? this.#selectedTimeframe
        : tfs[0] ?? null;

      const tfSelect = this.#container?.querySelector('#strat-timeframe');
      if (!tfSelect) return;

      tfSelect.innerHTML = '';
      for (const tf of tfs) {
        const opt = document.createElement('option');
        opt.value = tf;
        opt.textContent = tf;
        opt.selected = tf === this.#selectedTimeframe;
        tfSelect.appendChild(opt);
      }
    });

    this.#container?.querySelector('#strat-timeframe')?.addEventListener('change', (e) => {
      this.#selectedTimeframe = /** @type {HTMLSelectElement} */ (e.target).value;
    });

    this.#container?.querySelector('#strat-run-selected')?.addEventListener('click', () => {
      this.#runSelected();
    });

    this.#container?.querySelector('#strat-run-all')?.addEventListener('click', () => {
      this.#runAll();
    });
  }

  #refreshPluginList() {
    const list = this.#container?.querySelector('#strategy-list');
    if (!list) return;

    const plugins = StrategyEngine.listPlugins();
    const newList = this.#renderPluginList(plugins);
    list.replaceWith(newList);
    newList.addEventListener('click', (e) => {
      const item = /** @type {HTMLElement} */ (e.target).closest('.strategy-plugin-item');
      if (!item?.dataset.id) return;
      this.#selectedId = item.dataset.id;
      newList.querySelectorAll('.strategy-plugin-item').forEach((node) => {
        node.classList.toggle('active', node.dataset.id === this.#selectedId);
      });
      this.#renderDetail();
    });
  }

  #renderDetail() {
    const panel = this.#container?.querySelector('#strategy-detail');
    if (!panel || !this.#selectedId) return;

    const plugin = registry.get(this.#selectedId);
    if (!plugin) return;

    const instance = registry.createInstance(this.#selectedId);
    const schema = instance.getParameterSchema();
    const config = StrategyEngine.getConfig(this.#selectedId);
    const last = StrategyEngine.getLastResult(this.#selectedId);

    panel.innerHTML = '';

    panel.appendChild(el('div', { class: 'strategy-detail-header' }, [
      el('h3', { class: 'strategy-detail-title' }, [plugin.name]),
      el('p', { class: 'strategy-detail-desc' }, [plugin.description]),
      el('span', { class: 'phase-badge' }, ['Phase 5 — Signal logic active']),
    ]));

    panel.appendChild(el('div', { class: 'strategy-detail-meta' }, [
      el('span', {}, [`ID: ${plugin.id}`]),
      el('span', {}, [`Category: ${plugin.category}`]),
      el('span', {}, [`Warmup: ${instance.getWarmupBars()} bars`]),
    ]));

    panel.appendChild(el('label', { class: 'strategy-enable' }, [
      el('input', {
        type: 'checkbox',
        id: 'strat-enabled',
        checked: config.enabled,
      }),
      ' Enabled',
    ]));

    const paramsForm = el('div', { class: 'strategy-params', id: 'strategy-params' });
    for (const def of schema) {
      paramsForm.appendChild(this.#renderParamField(def, config.params[def.key]));
    }
    panel.appendChild(el('h4', { class: 'strategy-section-title' }, ['Parameters']));
    panel.appendChild(paramsForm);

    panel.appendChild(el('div', { class: 'strategy-actions' }, [
      el('button', { class: 'btn btn-sm', id: 'strat-save-params' }, ['Save Parameters']),
      el('button', { class: 'btn btn-sm', id: 'strat-export' }, ['Export Signals JSON']),
    ]));

    if (last) {
      panel.appendChild(el('div', { class: 'strategy-results' }, [
        el('h4', { class: 'strategy-section-title' }, ['Last Scan']),
        el('div', { class: 'strategy-result-grid' }, [
          el('span', {}, [`Signals: ${last.signals.length}`]),
          el('span', {}, [`Bars: ${last.barsScanned.toLocaleString()}`]),
          el('span', {}, [`Duration: ${last.durationMs}ms`]),
          el('span', {}, [`Pair: ${last.symbol} ${last.timeframe}`]),
        ]),
      ]));
    }

    panel.querySelector('#strat-enabled')?.addEventListener('change', (e) => {
      StrategyEngine.setConfig(this.#selectedId, {
        enabled: /** @type {HTMLInputElement} */ (e.target).checked,
      });
      this.#refreshPluginList();
    });

    panel.querySelector('#strat-save-params')?.addEventListener('click', () => {
      this.#saveParams(schema);
    });

    panel.querySelector('#strat-export')?.addEventListener('click', () => {
      try {
        const json = StrategyEngine.exportSignalsJSON(this.#selectedId);
        downloadFile(json, `${this.#selectedId}_signals.json`, 'application/json');
      } catch (err) {
        bus.emit(Events.LOG_MESSAGE, {
          message: err.message,
          level: 'error',
          time: new Date(),
        });
      }
    });
  }

  /**
   * @param {import('../strategy/ParameterSchema.js').ParamDefinition} def
   * @param {unknown} value
   * @returns {HTMLElement}
   */
  #renderParamField(def, value) {
    const label = el('label', { class: 'strategy-param-label' }, [def.label]);

    let input;
    if (def.type === 'select') {
      input = el('select', {
        class: 'data-select strategy-param-input',
        'data-key': def.key,
      }, (def.options ?? []).map((opt) =>
        el('option', { value: String(opt), selected: opt === value }, [String(opt)])
      ));
    } else if (def.type === 'boolean') {
      input = el('input', {
        type: 'checkbox',
        class: 'strategy-param-input',
        'data-key': def.key,
        checked: Boolean(value),
      });
    } else {
      input = el('input', {
        type: 'number',
        class: 'data-select strategy-param-input',
        'data-key': def.key,
        value: String(value ?? def.default),
        min: def.min !== undefined ? String(def.min) : undefined,
        max: def.max !== undefined ? String(def.max) : undefined,
        step: def.step !== undefined ? String(def.step) : undefined,
      });
    }

    const field = el('div', { class: 'strategy-param-field' }, [label, input]);
    if (def.description) {
      field.appendChild(el('span', { class: 'strategy-param-hint' }, [def.description]));
    }
    return field;
  }

  /**
   * @param {import('../strategy/ParameterSchema.js').ParamDefinition[]} schema
   */
  #saveParams(schema) {
    const params = {};
    const panel = this.#container?.querySelector('#strategy-detail');

    for (const def of schema) {
      const input = panel?.querySelector(`[data-key="${def.key}"]`);
      if (!input) continue;

      if (def.type === 'boolean') {
        params[def.key] = /** @type {HTMLInputElement} */ (input).checked;
      } else if (def.type === 'select') {
        const raw = /** @type {HTMLSelectElement} */ (input).value;
        params[def.key] = def.options?.find((o) => String(o) === raw) ?? raw;
      } else {
        params[def.key] = def.type === 'integer'
          ? parseInt(/** @type {HTMLInputElement} */ (input).value, 10)
          : parseFloat(/** @type {HTMLInputElement} */ (input).value);
      }
    }

    StrategyEngine.setConfig(this.#selectedId, { params });
    bus.emit(Events.LOG_MESSAGE, {
      message: `Parameters saved for ${this.#selectedId}`,
      level: 'info',
      time: new Date(),
    });
  }

  /**
   * @returns {{ symbol: string, timeframe: string }|null}
   */
  #getRunSelection() {
    if (!this.#selectedSymbol || !this.#selectedTimeframe) return null;

    const symbolEl = this.#container?.querySelector('#strat-symbol');
    const tfEl = this.#container?.querySelector('#strat-timeframe');

    return {
      symbol: symbolEl
        ? /** @type {HTMLSelectElement} */ (symbolEl).value
        : this.#selectedSymbol,
      timeframe: tfEl
        ? /** @type {HTMLSelectElement} */ (tfEl).value
        : this.#selectedTimeframe,
    };
  }

  async #runSelected() {
    if (!this.#selectedId) return;
    const selection = this.#getRunSelection();
    if (!selection) return;

    try {
      await StrategyEngine.runStrategy(
        this.#selectedId,
        selection.symbol,
        selection.timeframe
      );
      this.#refreshPluginList();
      this.#renderDetail();
    } catch (err) {
      bus.emit(Events.LOG_MESSAGE, {
        message: err.message,
        level: 'error',
        time: new Date(),
      });
    }
  }

  async #runAll() {
    const selection = this.#getRunSelection();
    if (!selection) return;

    await StrategyEngine.runAll(selection.symbol, selection.timeframe);
    this.#refreshPluginList();
    this.#renderDetail();
  }
}

export const StrategyView = new StrategyViewImpl();
