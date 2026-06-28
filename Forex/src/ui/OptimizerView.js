/**
 * Research optimizer view — grid search, walk-forward, Monte Carlo.
 * @module ui/OptimizerView
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el, loadFromStorage } from '../utils/dom.js';
import StrategyEngine from '../strategy/StrategyEngine.js';
import ResearchEngine from '../optimizer/ResearchEngine.js';
import { parseValueList, countCombinations, defaultGridForParam, augmentParamGrid } from '../optimizer/ParameterGrid.js';
import { suggestParamGridFromData } from '../optimizer/GridSuggestEngine.js';
import {
  buildSensitivitySeries,
  getVaryingParamKeys,
  MIN_TRADES_PER_SENSITIVITY_POINT,
} from '../optimizer/GridSensitivity.js';
import { drawGridSensitivityChart } from '../optimizer/GridSensitivityChart.js';
import { downloadFile } from '../data/DataExporter.js';
import { createHelpButton } from '../utils/contextHelp.js';
import { createLogger } from '../utils/logger.js';
import DataManager from '../data/DataManager.js';
import {
  buildSymbolOptions,
  buildTimeframeOptions,
  resolveDatasetSelection,
} from '../utils/runnableDatasets.js';

const log = createLogger('OptimizerView');

/** @type {'grid'|'sensitivity'|'walkforward'|'montecarlo'} */
let activeTab = 'grid';

/**
 * Optimizer workspace view.
 */
class OptimizerViewImpl {
  /** @type {HTMLElement|null} */
  #container = null;

  /** @type {string|null} */
  #selectedSymbol = null;

  /** @type {string|null} */
  #selectedTimeframe = null;

  /** @type {import('../data/Candle.js').DatasetMetadata[]} */
  #runnableDatasets = [];

  /** @type {(() => void)|null} */
  #unsub = null;

  /** @type {import('../optimizer/GridSearchEngine.js').GridSearchResult|null} */
  #gridResult = null;

  /** @type {(() => void)|null} */
  #sensitivityResizeHandler = null;

  /** @type {Record<string, GridFormState>} */
  #gridFormByStrategy = {};

  /**
   * @param {HTMLElement} container
   */
  async mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.remove('panel-body-fill');

    const settings = loadFromStorage(Config.STORAGE_KEYS.SETTINGS, {});
    const plugins = StrategyEngine.listPlugins();

    await this.#refreshDataState(settings);

    container.classList.add('panel-body-optimizer');

    container.appendChild(el('div', { class: 'optimizer-view opt-mode-grid', id: 'optimizer-root' }, [
      el('div', { class: 'opt-toolbar' }, [
        el('span', { class: 'opt-title' }, ['Research Optimizer']),
        this.#renderSelectors(settings, plugins),
        createHelpButton('optimizer'),
      ]),
      el('div', { class: 'opt-tabs', id: 'opt-tabs' }, [
        el('button', { class: 'opt-tab active', dataset: { tab: 'grid' } }, ['Grid Search']),
        el('button', { class: 'opt-tab', dataset: { tab: 'sensitivity' } }, ['Sensitivity']),
        el('button', { class: 'opt-tab', dataset: { tab: 'walkforward' } }, ['Walk Forward']),
        el('button', { class: 'opt-tab', dataset: { tab: 'montecarlo' } }, ['Monte Carlo']),
      ]),
      el('div', { class: 'opt-body', id: 'opt-body' }, [
        el('div', { class: 'opt-content', id: 'opt-content' }),
        el('div', { class: 'opt-results', id: 'opt-results' }),
      ]),
    ]));

    this.#bindEvents();
    this.#renderTab();
    log.info('Optimizer view mounted');
  }

  unmount() {
    this.#unsub?.();
    this.#unsub = null;
    if (this.#sensitivityResizeHandler) {
      window.removeEventListener('resize', this.#sensitivityResizeHandler);
      this.#sensitivityResizeHandler = null;
    }
    if (this.#container) {
      this.#container.classList.remove('panel-body-optimizer');
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
   * @param {Record<string, unknown>} settings
   * @param {import('../plugin/PluginRegistry.js').PluginDescriptor[]} plugins
   * @returns {HTMLElement}
   */
  #renderSelectors(settings, plugins) {
    const hasData = this.#runnableDatasets.length > 0;
    const stratOpts = plugins.map((p) => el('option', { value: p.id }, [p.name]));

    const children = [
      el('select', { class: 'data-select', id: 'opt-strategy' }, stratOpts),
    ];

    if (hasData) {
      children.push(
        el('select', { class: 'data-select', id: 'opt-symbol' }, buildSymbolOptions(
          this.#runnableDatasets,
          this.#selectedSymbol
        )),
        el('select', { class: 'data-select', id: 'opt-tf' }, buildTimeframeOptions(
          this.#runnableDatasets,
          this.#selectedSymbol,
          this.#selectedTimeframe
        ))
      );
    } else {
      children.push(el('span', { class: 'opt-no-data-hint' }, ['Chưa có dữ liệu']));
    }

    return el('div', { class: 'opt-selectors', id: 'opt-selectors' }, children);
  }

  async #refreshSelectors() {
    const plugins = StrategyEngine.listPlugins();
    await this.#refreshDataState();
    const old = this.#container?.querySelector('#opt-selectors');
    if (!old) return;
    old.replaceWith(this.#renderSelectors({}, plugins));
    this.#bindSelectorEvents();
    if (activeTab === 'grid') this.#renderTab();
  }

  #bindEvents() {
    this.#bindSelectorEvents();

    this.#container?.querySelector('#opt-tabs')?.addEventListener('click', (e) => {
      const btn = /** @type {HTMLElement} */ (e.target).closest('.opt-tab');
      if (!btn?.dataset.tab) return;
      activeTab = /** @type {'grid'|'sensitivity'|'walkforward'|'montecarlo'} */ (btn.dataset.tab);
      this.#container?.querySelectorAll('.opt-tab').forEach((t) => {
        t.classList.toggle('active', t.dataset.tab === activeTab);
      });
      this.#renderTab();
    });

    const unsubs = [
      bus.on(Events.OPTIMIZATION_COMPLETE, (r) => {
        this.#gridResult = r;
        if (activeTab === 'grid') this.#renderGridResults(r);
        else if (activeTab === 'sensitivity') this.#renderSensitivityResults(r);
      }),
      bus.on(Events.WALK_FORWARD_COMPLETE, (r) => this.#renderWalkForwardResults(r)),
      bus.on(Events.MONTE_CARLO_COMPLETE, (r) => this.#renderMonteCarloResults(r)),
      bus.on(Events.DATA_UPDATED, () => this.#refreshSelectors()),
    ];
    this.#unsub = () => unsubs.forEach((fn) => fn());
  }

  #bindSelectorEvents() {
    this.#container?.querySelector('#opt-strategy')?.addEventListener('change', () => {
      if (activeTab === 'grid') this.#renderTab();
    });

    this.#container?.querySelector('#opt-symbol')?.addEventListener('change', (e) => {
      this.#selectedSymbol = /** @type {HTMLSelectElement} */ (e.target).value;
      const resolved = resolveDatasetSelection(
        this.#runnableDatasets,
        this.#selectedSymbol,
        this.#selectedTimeframe ?? undefined
      );
      this.#selectedTimeframe = resolved.timeframe;

      const tfSelect = this.#container?.querySelector('#opt-tf');
      if (!tfSelect) return;
      tfSelect.innerHTML = '';
      for (const opt of buildTimeframeOptions(
        this.#runnableDatasets,
        this.#selectedSymbol,
        this.#selectedTimeframe
      )) {
        tfSelect.appendChild(opt);
      }
      if (this.#selectedTimeframe) {
        /** @type {HTMLSelectElement} */ (tfSelect).value = this.#selectedTimeframe;
      }
    });

    this.#container?.querySelector('#opt-tf')?.addEventListener('change', (e) => {
      this.#selectedTimeframe = /** @type {HTMLSelectElement} */ (e.target).value;
    });
  }

  #renderTab() {
    const content = this.#container?.querySelector('#opt-content');
    const results = this.#container?.querySelector('#opt-results');
    const root = this.#container?.querySelector('#optimizer-root');
    if (!content || !results) return;

    const strategySelect = /** @type {HTMLSelectElement|null} */ (
      this.#container?.querySelector('#opt-strategy')
    );
    if (strategySelect && this.#container?.querySelector('#opt-run-grid')) {
      this.#captureGridFormState(strategySelect.value);
    }

    if (this.#sensitivityResizeHandler) {
      window.removeEventListener('resize', this.#sensitivityResizeHandler);
      this.#sensitivityResizeHandler = null;
    }

    root?.classList.toggle('opt-mode-grid', activeTab === 'grid');
    root?.classList.toggle('opt-mode-stack', activeTab !== 'grid');

    content.innerHTML = '';
    results.innerHTML = '';

    if (activeTab === 'grid') {
      this.#renderGridPanel(content);
      const last = this.#gridResult ?? ResearchEngine.getLastGridResult();
      if (last) this.#renderGridResults(last);
      else this.#renderGridResultsPlaceholder(results);
    } else if (activeTab === 'sensitivity') {
      this.#renderSensitivityConfigPanel(content);
      const last = this.#gridResult ?? ResearchEngine.getLastGridResult();
      if (last) this.#renderSensitivityResults(last);
      else this.#renderResultsPlaceholder(
        results,
        'Param Sensitivity',
        'Chạy Grid Search trước — biểu đồ WR và expectancy theo từng tham số sẽ hiển thị ở đây.'
      );
    } else if (activeTab === 'walkforward') {
      this.#renderWalkForwardPanel(content);
      const last = ResearchEngine.getLastWalkForwardResult();
      if (last) this.#renderWalkForwardResults(last);
      else this.#renderResultsPlaceholder(results, 'Walk Forward', 'Chạy Walk Forward để xem kết quả in-sample / out-of-sample.');
    } else {
      this.#renderMonteCarloPanel(content);
      const last = ResearchEngine.getLastMonteCarloResult();
      if (last) this.#renderMonteCarloResults(last);
      else this.#renderResultsPlaceholder(results, 'Monte Carlo', 'Chạy Monte Carlo sau khi có lệnh từ Simulation.');
    }
  }

  /**
   * @param {HTMLElement} content
   */
  #renderGridPanel(content) {
    const strategyId = /** @type {HTMLSelectElement} */ (this.#container.querySelector('#opt-strategy')).value;

    let instance;
    try {
      instance = StrategyEngine.createInstance(strategyId);
    } catch (err) {
      content.appendChild(el('div', { class: 'opt-panel opt-error' }, [
        el('p', { class: 'opt-desc opt-error-text' }, [err instanceof Error ? err.message : String(err)]),
      ]));
      return;
    }

    const schema = instance.getParameterSchema();
    const formState = this.#getGridFormState(strategyId, schema);

    const paramRows = schema
      .filter((d) => d.type === 'number' || d.type === 'integer')
      .map((def) => {
        const saved = formState.params[def.key];
        const defaults = saved?.values ?? defaultGridForParam(def).join(',');
        const checked = saved?.checked ?? def.key === 'rr';
        const isTrendEma = strategyId === 'break-retest' && ['emaFast', 'emaSlow', 'trendBars'].includes(def.key);
        const children = [
          el('input', { type: 'checkbox', class: 'opt-param-check', dataset: { key: def.key }, checked }),
          el('span', { class: 'opt-param-label' }, [def.label]),
          el('input', {
            type: 'text',
            class: 'data-select opt-param-values',
            dataset: { key: def.key },
            value: defaults,
            placeholder: 'e.g. 1,2,3 or 10:50:10',
          }),
        ];
        if (isTrendEma) {
          children.push(el('span', { class: 'opt-param-hint' }, ['Bật EMA trend filter khi chạy grid']));
        }
        return el('label', { class: 'opt-param-row' }, children);
      });

    content.appendChild(el('div', { class: 'opt-panel' }, [
      el('p', { class: 'opt-desc' }, ['Test every parameter combination. Max ', String(Config.OPTIMIZER.MAX_COMBINATIONS), ' combos.']),
      el('div', { class: 'opt-param-section' }, [
        el('div', { class: 'opt-param-section-head' }, [
          el('span', { class: 'opt-param-section-title' }, ['Parameters']),
          el('span', { class: 'opt-param-section-hint' }, ['Tick để đưa vào grid']),
          el('div', { class: 'opt-param-section-actions' }, [
            el('button', {
              type: 'button',
              class: 'btn btn-secondary opt-suggest-btn',
              id: 'opt-suggest-grid',
              title: 'Điền lưới tham số từ biến động nến hiện tại',
            }, ['Suggest from data']),
            el('button', {
              type: 'button',
              class: 'btn btn-secondary opt-suggest-btn',
              id: 'opt-restore-grid',
              title: 'Khôi phục lưới mặc định cho strategy này',
            }, ['Restore defaults']),
          ]),
        ]),
        el('div', { class: 'opt-param-grid' }, paramRows),
        el('div', { class: 'opt-suggest-status', id: 'opt-suggest-hint', 'aria-live': 'polite' }, []),
      ]),
      el('label', { class: 'opt-field' }, [
        'Rank by',
        el('select', { class: 'data-select', id: 'opt-rank' }, [
          el('option', { value: 'expectancy' }, ['Expectancy']),
          el('option', { value: 'netProfit' }, ['Net Profit']),
          el('option', { value: 'profitFactor' }, ['Profit Factor']),
          el('option', { value: 'sharpeRatio' }, ['Sharpe Ratio']),
          el('option', { value: 'winRate' }, ['Win Rate']),
        ]),
      ]),
      el('label', { class: 'opt-field opt-field-check' }, [
        el('input', {
          type: 'checkbox',
          id: 'opt-auto-wf',
          checked: formState.autoWalkForward,
        }),
        ' Auto walk-forward on best combo',
      ]),
      el('div', { class: 'opt-actions' }, [
        el('button', { class: 'btn btn-primary', id: 'opt-run-grid' }, ['Run Grid Search']),
        el('span', { class: 'opt-progress', id: 'opt-progress' }, ['']),
      ]),
    ]));

    content.querySelector('#opt-run-grid')?.addEventListener('click', () => this.#runGrid());
    content.querySelector('#opt-suggest-grid')?.addEventListener('click', () => this.#suggestGridFromData(strategyId, schema));
    content.querySelector('#opt-restore-grid')?.addEventListener('click', () => {
      this.#gridFormByStrategy[strategyId] = this.#buildDefaultGridFormState(schema);
      this.#renderGridPanel(content);
      const last = this.#gridResult ?? ResearchEngine.getLastGridResult();
      const results = this.#container?.querySelector('#opt-results');
      if (results) {
        results.innerHTML = '';
        if (last) this.#renderGridResults(last);
        else this.#renderGridResultsPlaceholder(results);
      }
      bus.emit(Events.LOG_MESSAGE, {
        message: 'Grid Search: restored default parameter grid',
        level: 'info',
        time: new Date(),
      });
    });

    const rankSelect = /** @type {HTMLSelectElement|null} */ (content.querySelector('#opt-rank'));
    if (rankSelect) rankSelect.value = formState.rankMetric;

    if (formState.suggestMessage) {
      this.#setSuggestStatus(formState.suggestMessage, formState.suggestError ?? false);
    }
  }

  /**
   * @typedef {Object} GridFormParamState
   * @property {string} values
   * @property {boolean} checked
   */

  /**
   * @typedef {Object} GridFormState
   * @property {Record<string, GridFormParamState>} params
   * @property {string} rankMetric
   * @property {boolean} autoWalkForward
   * @property {string} [suggestMessage]
   * @property {boolean} [suggestError]
   */

  /**
   * @param {import('../strategy/ParameterSchema.js').ParamDefinition[]} schema
   * @returns {GridFormState}
   */
  #buildDefaultGridFormState(schema) {
    /** @type {Record<string, GridFormParamState>} */
    const params = {};
    for (const def of schema.filter((d) => d.type === 'number' || d.type === 'integer')) {
      params[def.key] = {
        values: defaultGridForParam(def).join(','),
        checked: def.key === 'rr',
      };
    }
    return {
      params,
      rankMetric: Config.OPTIMIZER.DEFAULT_RANK_METRIC,
      autoWalkForward: Config.OPTIMIZER.AUTO_WALK_FORWARD_AFTER_GRID,
    };
  }

  /**
   * @param {string} strategyId
   * @param {import('../strategy/ParameterSchema.js').ParamDefinition[]} schema
   * @returns {GridFormState}
   */
  #getGridFormState(strategyId, schema) {
    return this.#gridFormByStrategy[strategyId] ?? this.#buildDefaultGridFormState(schema);
  }

  /**
   * @param {string} strategyId
   */
  #captureGridFormState(strategyId) {
    if (!this.#container?.querySelector('#opt-run-grid')) return;

    /** @type {Record<string, GridFormParamState>} */
    const params = {};
    this.#container.querySelectorAll('.opt-param-check').forEach((cb) => {
      const key = /** @type {HTMLElement} */ (cb).dataset.key;
      if (!key) return;
      const input = this.#container.querySelector(`.opt-param-values[data-key="${key}"]`);
      params[key] = {
        checked: /** @type {HTMLInputElement} */ (cb).checked,
        values: input ? /** @type {HTMLInputElement} */ (input).value : '',
      };
    });

    const rank = /** @type {HTMLSelectElement|null} */ (this.#container.querySelector('#opt-rank'));
    const autoWf = /** @type {HTMLInputElement|null} */ (this.#container.querySelector('#opt-auto-wf'));
    const hint = this.#container.querySelector('#opt-suggest-hint');

    this.#gridFormByStrategy[strategyId] = {
      params,
      rankMetric: rank?.value ?? Config.OPTIMIZER.DEFAULT_RANK_METRIC,
      autoWalkForward: autoWf?.checked ?? Config.OPTIMIZER.AUTO_WALK_FORWARD_AFTER_GRID,
      suggestMessage: hint?.textContent?.trim() ?? '',
      suggestError: hint?.classList.contains('opt-suggest-status-error') ?? false,
    };
  }

  /**
   * @param {string} strategyId
   * @param {import('../strategy/ParameterSchema.js').ParamDefinition[]} schema
   */
  #persistGridFormState(strategyId, schema) {
    this.#captureGridFormState(strategyId);
    if (!this.#gridFormByStrategy[strategyId]) {
      this.#gridFormByStrategy[strategyId] = this.#buildDefaultGridFormState(schema);
    }
  }

  /**
   * @param {string} strategyId
   * @param {import('../strategy/ParameterSchema.js').ParamDefinition[]} schema
   */
  async #suggestGridFromData(strategyId, schema) {
    const { symbol, timeframe } = this.#readSelectors();
    const btn = this.#container?.querySelector('#opt-suggest-grid');

    if (btn) /** @type {HTMLButtonElement} */ (btn).disabled = true;
    this.#setSuggestStatus('Đang đọc dữ liệu nến…');

    try {
      const candles = await DataManager.getCandles(symbol, timeframe);
      const suggestion = suggestParamGridFromData(strategyId, schema, candles, symbol, timeframe);

      for (const def of schema.filter((d) => d.type === 'number' || d.type === 'integer')) {
        const input = this.#container?.querySelector(`.opt-param-values[data-key="${def.key}"]`);
        if (input && suggestion.values[def.key]) {
          /** @type {HTMLInputElement} */ (input).value = suggestion.values[def.key];
        }
        const check = this.#container?.querySelector(`.opt-param-check[data-key="${def.key}"]`);
        if (check) {
          /** @type {HTMLInputElement} */ (check).checked = suggestion.checks[def.key] ?? false;
        }
      }

      const total = countCombinations(augmentParamGrid(strategyId, this.#readParamGrid()));
      const statusMsg = `${suggestion.message} — ${total} combo nếu chạy ngay`;
      this.#setSuggestStatus(statusMsg);
      this.#persistGridFormState(strategyId, schema);
      if (this.#gridFormByStrategy[strategyId]) {
        this.#gridFormByStrategy[strategyId].suggestMessage = statusMsg;
        this.#gridFormByStrategy[strategyId].suggestError = false;
      }
      bus.emit(Events.LOG_MESSAGE, {
        message: `Grid suggest: ${suggestion.message}`,
        level: 'info',
        time: new Date(),
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      this.#setSuggestStatus(msg, true);
      bus.emit(Events.LOG_MESSAGE, { message: msg, level: 'error', time: new Date() });
    } finally {
      if (btn) /** @type {HTMLButtonElement} */ (btn).disabled = false;
    }
  }

  /**
   * @param {string} message
   * @param {boolean} [isError]
   */
  #setSuggestStatus(message, isError = false) {
    const hint = this.#container?.querySelector('#opt-suggest-hint');
    if (!hint) return;
    hint.textContent = message;
    hint.classList.toggle('opt-suggest-status-error', isError);
    hint.classList.toggle('opt-suggest-status-visible', Boolean(message));
  }

  /**
   * @param {HTMLElement} content
   */
  #renderWalkForwardPanel(content) {
    const opt = Config.OPTIMIZER;
    content.appendChild(el('div', { class: 'opt-panel' }, [
      el('p', { class: 'opt-desc' }, ['Rolling in-sample / out-of-sample validation using current strategy parameters.']),
      el('div', { class: 'opt-config-row' }, [
        el('label', { class: 'opt-field' }, [
          'In-sample %',
          el('input', { type: 'number', class: 'data-select', id: 'wf-is', value: String(opt.IN_SAMPLE_RATIO * 100), min: '50', max: '90' }),
        ]),
        el('label', { class: 'opt-field' }, [
          'OOS %',
          el('input', { type: 'number', class: 'data-select', id: 'wf-oos', value: String(opt.OOS_RATIO * 100), min: '5', max: '30' }),
        ]),
        el('label', { class: 'opt-field' }, [
          'Folds',
          el('input', { type: 'number', class: 'data-select', id: 'wf-folds', value: String(opt.WALK_FORWARD_FOLDS), min: '2', max: '10' }),
        ]),
      ]),
      el('div', { class: 'opt-actions' }, [
        el('button', { class: 'btn btn-primary', id: 'opt-run-wf' }, ['Run Walk Forward']),
      ]),
    ]));
    content.querySelector('#opt-run-wf')?.addEventListener('click', () => this.#runWalkForward());
  }

  /**
   * @param {HTMLElement} content
   */
  #renderMonteCarloPanel(content) {
    content.appendChild(el('div', { class: 'opt-panel' }, [
      el('p', { class: 'opt-desc' }, ['Shuffle trade order to estimate balance distribution. Uses last simulation trades.']),
      el('label', { class: 'opt-field' }, [
        'Iterations',
        el('input', {
          type: 'number',
          class: 'data-select',
          id: 'mc-iterations',
          value: String(Config.OPTIMIZER.MONTE_CARLO_ITERATIONS),
          min: '100',
          max: '10000',
          step: '100',
        }),
      ]),
      el('div', { class: 'opt-actions' }, [
        el('button', { class: 'btn btn-primary', id: 'opt-run-mc' }, ['Run Monte Carlo']),
      ]),
    ]));
    content.querySelector('#opt-run-mc')?.addEventListener('click', () => this.#runMonteCarlo());
  }

  #readSelectors() {
    if (this.#runnableDatasets.length === 0) {
      throw new Error('Chưa có dữ liệu nến — mở Data Manager để import hoặc tải mặc định.');
    }
    return {
      strategyId: /** @type {HTMLSelectElement} */ (this.#container.querySelector('#opt-strategy')).value,
      symbol: /** @type {HTMLSelectElement} */ (this.#container.querySelector('#opt-symbol')).value,
      timeframe: /** @type {HTMLSelectElement} */ (this.#container.querySelector('#opt-tf')).value,
    };
  }

  #readParamGrid() {
    /** @type {Record<string, number[]>} */
    const grid = {};
    this.#container?.querySelectorAll('.opt-param-check:checked').forEach((cb) => {
      const key = /** @type {HTMLElement} */ (cb).dataset.key;
      const input = this.#container?.querySelector(`.opt-param-values[data-key="${key}"]`);
      if (!key || !input) return;
      const values = parseValueList(/** @type {HTMLInputElement} */ (input).value);
      if (values.length) grid[key] = values;
    });
    return grid;
  }

  async #runGrid() {
    const { strategyId, symbol, timeframe } = this.#readSelectors();
    const paramGrid = augmentParamGrid(strategyId, this.#readParamGrid());
    const rankMetric = /** @type {HTMLSelectElement} */ (this.#container.querySelector('#opt-rank')).value;
    const progress = this.#container?.querySelector('#opt-progress');

    const total = countCombinations(paramGrid);
    if (total === 0) {
      bus.emit(Events.LOG_MESSAGE, { message: 'Select at least one parameter with values', level: 'warn', time: new Date() });
      return;
    }

    if (progress) progress.textContent = `0 / ${total}`;
    try {
      const autoWalkForward = /** @type {HTMLInputElement} */ (
        this.#container.querySelector('#opt-auto-wf')
      )?.checked ?? Config.OPTIMIZER.AUTO_WALK_FORWARD_AFTER_GRID;

      await ResearchEngine.runGridSearch({
        strategyId,
        symbol,
        timeframe,
        paramGrid,
        rankMetric: /** @type {import('../optimizer/GridSearchEngine.js').RankMetric} */ (rankMetric),
        autoWalkForward,
        onProgress: (p) => {
          if (progress) progress.textContent = `${Math.round(p * total)} / ${total}`;
        },
      });
    } catch (err) {
      bus.emit(Events.LOG_MESSAGE, { message: err.message, level: 'error', time: new Date() });
    }
    if (progress) progress.textContent = '';
  }

  async #runWalkForward() {
    const { strategyId, symbol, timeframe } = this.#readSelectors();
    const isRatio = parseFloat(/** @type {HTMLInputElement} */ (this.#container.querySelector('#wf-is')).value) / 100;
    const oosRatio = parseFloat(/** @type {HTMLInputElement} */ (this.#container.querySelector('#wf-oos')).value) / 100;
    const maxFolds = parseInt(/** @type {HTMLInputElement} */ (this.#container.querySelector('#wf-folds')).value, 10);

    try {
      await ResearchEngine.runWalkForward({ strategyId, symbol, timeframe, inSampleRatio: isRatio, oosRatio, maxFolds });
    } catch (err) {
      bus.emit(Events.LOG_MESSAGE, { message: err.message, level: 'error', time: new Date() });
    }
  }

  async #runMonteCarlo() {
    const iterations = parseInt(/** @type {HTMLInputElement} */ (this.#container.querySelector('#mc-iterations')).value, 10);
    try {
      await ResearchEngine.runMonteCarlo({ iterations });
    } catch (err) {
      bus.emit(Events.LOG_MESSAGE, { message: err.message, level: 'error', time: new Date() });
    }
  }

  /**
   * @param {HTMLElement} wrap
   */
  #renderGridResultsPlaceholder(wrap) {
    this.#renderResultsPlaceholder(wrap, 'Top Results', 'Chạy Grid Search — kết quả xếp hạng combo sẽ hiển thị ở đây.');
  }

  /**
   * @param {HTMLElement} wrap
   * @param {string} title
   * @param {string} hint
   */
  #renderResultsPlaceholder(wrap, title, hint) {
    wrap.appendChild(el('div', { class: 'opt-results-placeholder' }, [
      el('h4', {}, [title]),
      el('p', {}, [hint]),
    ]));
  }

  /**
   * @param {Record<string, unknown>} params
   * @returns {HTMLElement}
   */
  #formatParamsCell(params) {
    const entries = Object.entries(params);
    if (entries.length === 0) {
      return el('span', { class: 'opt-mono' }, ['—']);
    }
    return el('div', { class: 'opt-params-stack' },
      entries.map(([key, value]) =>
        el('span', { class: 'opt-param-chip', title: `${key}=${value}` }, [`${key}=${value}`])
      )
    );
  }

  /**
   * @param {import('../optimizer/GridSearchEngine.js').GridSearchResult} result
   */
  #renderGridResults(result) {
    const wrap = this.#container?.querySelector('#opt-results');
    if (!wrap || activeTab !== 'grid') return;

    this.#gridResult = result;

    wrap.innerHTML = '';
    const headerActions = [
      el('button', { class: 'btn btn-sm', id: 'opt-export-grid' }, ['Export JSON']),
    ];
    if (result.best?.params) {
      headerActions.unshift(
        el('button', {
          class: 'btn btn-sm btn-primary',
          id: 'opt-apply-best',
          title: 'Lưu tham số combo #1 vào Strategies',
        }, ['Apply best to Strategy'])
      );
    }

    wrap.appendChild(el('div', { class: 'opt-results-header' }, [
      el('h4', {}, [
        `Top Results (${result.totalCombinations} combos, ${result.durationMs}ms${result.parallel ? ', parallel' : ''})`,
      ]),
      el('div', { class: 'opt-results-actions' }, headerActions),
    ]));

    const top = result.entries.slice(0, 20);
    const rows = top.map((entry, i) =>
      el('tr', {}, [
        el('td', { class: 'opt-rank-cell' }, [String(i + 1)]),
        el('td', { class: 'opt-params-cell' }, [this.#formatParamsCell(entry.params)]),
        el('td', {}, [String(entry.result.stats.totalTrades)]),
        el('td', {}, [`${entry.result.stats.winRate.toFixed(1)}%`]),
        el('td', { class: 'opt-mono' }, [`$${entry.result.stats.netProfit.toFixed(2)}`]),
        el('td', { class: 'opt-mono' }, [`$${entry.result.stats.expectancy.toFixed(2)}`]),
        el('td', {}, [entry.result.stats.profitFactor === Infinity ? '∞' : entry.result.stats.profitFactor.toFixed(2)]),
      ])
    );

    wrap.appendChild(el('div', { class: 'opt-table-scroll' }, [
      el('table', { class: 'data-table opt-table' }, [
        el('thead', {}, [
          el('tr', {}, ['#', 'Params', 'Trades', 'WR', 'Net', 'Exp', 'PF'].map((h) => el('th', {}, [h]))),
        ]),
        el('tbody', {}, rows),
      ]),
    ]));

    if (result.walkForward) {
      const wf = result.walkForward;
      wrap.appendChild(el('div', { class: 'opt-wf-inline' }, [
        el('h4', { class: 'opt-wf-inline-title' }, [
          `Walk-forward on best combo (${wf.folds.length} folds)`,
        ]),
        el('div', { class: 'opt-summary-cards' }, [
          this.#card('Avg IS', `$${wf.avgIsNetProfit.toFixed(2)}`),
          this.#card('Avg OOS', `$${wf.avgOosNetProfit.toFixed(2)}`),
          this.#card('OOS profitable', `${wf.oosWinRate.toFixed(0)}%`),
        ]),
      ]));
    }

    wrap.querySelector('#opt-export-grid')?.addEventListener('click', () => {
      downloadFile(JSON.stringify(result, null, 2), 'grid_search.json', 'application/json');
    });

    wrap.querySelector('#opt-apply-best')?.addEventListener('click', () => {
      try {
        ResearchEngine.applyGridBestToStrategy(result.strategyId);
        bus.emit(Events.LOG_MESSAGE, {
          message: 'Đã lưu combo tốt nhất — mở Strategies (Ctrl+3) để xem hoặc chạy lại scan.',
          level: 'info',
          time: new Date(),
        });
      } catch (err) {
        bus.emit(Events.LOG_MESSAGE, {
          message: err instanceof Error ? err.message : String(err),
          level: 'error',
          time: new Date(),
        });
      }
    });
  }

  /**
   * @param {HTMLElement} content
   */
  #renderSensitivityConfigPanel(content) {
    content.appendChild(el('div', { class: 'opt-panel' }, [
      el('p', { class: 'opt-desc' }, [
        'Trung binh theo tung gia tri tham so (in-sample). Chon param va metric ben phai.',
      ]),
      el('p', { class: 'opt-desc opt-desc-note' }, [
        'Net Profit phu thuoc so lenh — so sanh kem Exp khi trade count chenh nhau nhieu.',
      ]),
    ]));
  }

  /**
   * @param {import('../optimizer/GridSearchEngine.js').GridSearchResult} result
   */
  #renderSensitivityResults(result) {
    const wrap = this.#container?.querySelector('#opt-results');
    if (!wrap || activeTab !== 'sensitivity') return;

    this.#gridResult = result;
    const varying = getVaryingParamKeys(result.entries);

    wrap.innerHTML = '';

    if (!varying.length) {
      this.#renderResultsPlaceholder(
        wrap,
        'Param Sensitivity',
        'Cần grid search với ít nhất 2 giá trị khác nhau cho một tham số.'
      );
      return;
    }

    wrap.appendChild(el('div', { class: 'opt-results-header opt-sensitivity-toolbar' }, [
      el('h4', {}, [
        `Sensitivity (${result.totalCombinations} combos, ${result.strategyId})`,
      ]),
      el('div', { class: 'opt-sensitivity-controls' }, [
        el('label', { class: 'opt-sensitivity-field' }, [
          'Parameter',
          el('select', { class: 'data-select', id: 'opt-sensitivity-param' },
            varying.map((key) => el('option', { value: key }, [key]))),
        ]),
        el('div', { class: 'opt-sensitivity-metrics' }, [
          el('label', { class: 'opt-sensitivity-metric' }, [
            el('input', { type: 'checkbox', id: 'opt-sens-wr', checked: true }),
            'WR',
          ]),
          el('label', { class: 'opt-sensitivity-metric' }, [
            el('input', { type: 'checkbox', id: 'opt-sens-exp', checked: true }),
            'Exp',
          ]),
          el('label', { class: 'opt-sensitivity-metric' }, [
            el('input', { type: 'checkbox', id: 'opt-sens-net', checked: true }),
            'Net',
          ]),
        ]),
      ]),
    ]));

    wrap.appendChild(el('div', { class: 'opt-sensitivity' }, [
      el('canvas', { class: 'opt-sensitivity-canvas', id: 'opt-sensitivity-canvas', width: '800', height: '280' }),
      el('p', { class: 'opt-sensitivity-hint', id: 'opt-sensitivity-hint' }, ['']),
    ]));

    for (const id of ['#opt-sensitivity-param', '#opt-sens-wr', '#opt-sens-exp', '#opt-sens-net']) {
      wrap.querySelector(id)?.addEventListener('change', () => this.#updateSensitivityChart());
    }

    this.#sensitivityResizeHandler = () => this.#updateSensitivityChart();
    window.addEventListener('resize', this.#sensitivityResizeHandler);

    this.#updateSensitivityChart();
  }

  #updateSensitivityChart() {
    if (!this.#gridResult) return;

    const select = /** @type {HTMLSelectElement|null} */ (
      this.#container?.querySelector('#opt-sensitivity-param')
    );
    const showWinRate = /** @type {HTMLInputElement} */ (
      this.#container?.querySelector('#opt-sens-wr')
    )?.checked ?? true;
    const showExpectancy = /** @type {HTMLInputElement} */ (
      this.#container?.querySelector('#opt-sens-exp')
    )?.checked ?? true;
    const showNetProfit = /** @type {HTMLInputElement} */ (
      this.#container?.querySelector('#opt-sens-net')
    )?.checked ?? true;

    const canvas = /** @type {HTMLCanvasElement|null} */ (
      this.#container?.querySelector('#opt-sensitivity-canvas')
    );
    const hint = this.#container?.querySelector('#opt-sensitivity-hint');
    if (!select || !canvas || !hint) return;

    const paramKey = select.value;
    const series = buildSensitivitySeries(this.#gridResult.entries, paramKey);
    const drawn = drawGridSensitivityChart(canvas, series, paramKey, {
      showWinRate,
      showExpectancy,
      showNetProfit,
    });

    if (!drawn) {
      hint.textContent = !showWinRate && !showExpectancy && !showNetProfit
        ? 'Bat it nhat mot metric (WR, Exp hoac Net).'
        : series.length === 0
          ? `Khong du diem — can TB >= ${MIN_TRADES_PER_SENSITIVITY_POINT} lenh/combo cho moi gia tri ${paramKey}.`
          : `Can it nhat 2 gia tri ${paramKey} de ve bieu do.`;
      const ctx = canvas.getContext('2d');
      if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }

    const buckets = series.length;
    const combos = series.reduce((sum, p) => sum + p.sampleCount, 0);
    hint.textContent = `TB theo ${paramKey} — ${buckets} gia tri — ${combos} combo — an diem < ${MIN_TRADES_PER_SENSITIVITY_POINT} lenh TB`;
  }

  /**
   * @param {import('../optimizer/WalkForwardEngine.js').WalkForwardResult} result
   */
  #renderWalkForwardResults(result) {
    const wrap = this.#container?.querySelector('#opt-results');
    if (!wrap || activeTab !== 'walkforward') return;

    wrap.innerHTML = '';
    wrap.appendChild(el('div', { class: 'opt-summary-cards' }, [
      this.#card('Folds', String(result.folds.length)),
      this.#card('Avg IS Profit', `$${result.avgIsNetProfit.toFixed(2)}`),
      this.#card('Avg OOS Profit', `$${result.avgOosNetProfit.toFixed(2)}`),
      this.#card('OOS Profitable', `${result.oosWinRate.toFixed(0)}%`),
    ]));

    const rows = result.folds.map((f) =>
      el('tr', {}, [
        el('td', {}, [String(f.fold)]),
        el('td', { class: 'opt-mono' }, [String(f.isStart)]),
        el('td', {}, [String(f.inSample.stats.totalTrades)]),
        el('td', { class: 'opt-mono' }, [`$${f.inSample.stats.netProfit.toFixed(2)}`]),
        el('td', {}, [String(f.outOfSample.stats.totalTrades)]),
        el('td', { class: 'opt-mono' }, [`$${f.outOfSample.stats.netProfit.toFixed(2)}`]),
      ])
    );

    wrap.appendChild(el('div', { class: 'opt-table-scroll' }, [
      el('table', { class: 'data-table opt-table' }, [
        el('thead', {}, [
          el('tr', {}, ['Fold', 'IS Start', 'IS Trades', 'IS Net', 'OOS Trades', 'OOS Net'].map((h) => el('th', {}, [h]))),
        ]),
        el('tbody', {}, rows),
      ]),
    ]));
  }

  /**
   * @param {import('../optimizer/MonteCarloEngine.js').MonteCarloResult} result
   */
  #renderMonteCarloResults(result) {
    const wrap = this.#container?.querySelector('#opt-results');
    if (!wrap || activeTab !== 'montecarlo') return;

    wrap.innerHTML = '';
    const { p5, p50, p95 } = result.percentiles;

    wrap.appendChild(el('div', { class: 'opt-summary-cards' }, [
      this.#card('Iterations', String(result.iterations)),
      this.#card('Trades', String(result.tradeCount)),
      this.#card('Ruin Rate', `${result.ruinRate.toFixed(1)}%`),
      this.#card('P50 Balance', `$${p50.finalBalance.toFixed(2)}`),
    ]));

    wrap.appendChild(el('div', { class: 'opt-mc-grid' }, [
      this.#mcCard('P5 (worst)', p5),
      this.#mcCard('P50 (median)', p50),
      this.#mcCard('P95 (best)', p95),
    ]));
  }

  /**
   * @param {string} label
   * @param {string} value
   * @returns {HTMLElement}
   */
  #card(label, value) {
    return el('div', { class: 'opt-card' }, [
      el('span', { class: 'opt-card-label' }, [label]),
      el('span', { class: 'opt-card-value' }, [value]),
    ]);
  }

  /**
   * @param {string} label
   * @param {import('../optimizer/MonteCarloEngine.js').MonteCarloIteration} iter
   * @returns {HTMLElement}
   */
  #mcCard(label, iter) {
    return el('div', { class: 'opt-mc-card' }, [
      el('span', { class: 'opt-card-label' }, [label]),
      el('span', { class: 'opt-card-value' }, [`$${iter.finalBalance.toFixed(2)}`]),
      el('span', { class: 'opt-mc-meta' }, [
        `Net $${iter.netProfit.toFixed(2)} · DD $${iter.maxDrawdown.toFixed(2)} (${iter.maxDrawdownPercent.toFixed(1)}%)`,
      ]),
    ]);
  }
}

export const OptimizerView = new OptimizerViewImpl();
