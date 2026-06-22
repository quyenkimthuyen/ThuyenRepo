/**
 * Research optimizer view — grid search, walk-forward, Monte Carlo.
 * @module ui/OptimizerView
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el, loadFromStorage } from '../utils/dom.js';
import { registry } from '../plugin/PluginRegistry.js';
import StrategyEngine from '../strategy/StrategyEngine.js';
import ResearchEngine from '../optimizer/ResearchEngine.js';
import { parseValueList, countCombinations, defaultGridForParam } from '../optimizer/ParameterGrid.js';
import { downloadFile } from '../data/DataExporter.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('OptimizerView');

/** @type {'grid'|'walkforward'|'montecarlo'} */
let activeTab = 'grid';

/**
 * Optimizer workspace view.
 */
class OptimizerViewImpl {
  /** @type {HTMLElement|null} */
  #container = null;

  /**
   * @param {HTMLElement} container
   */
  async mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.remove('panel-body-fill');

    const settings = loadFromStorage(Config.STORAGE_KEYS.SETTINGS, {});
    const plugins = StrategyEngine.listPlugins();

    container.appendChild(el('div', { class: 'optimizer-view' }, [
      el('div', { class: 'opt-toolbar' }, [
        el('span', { class: 'opt-title' }, ['Research Optimizer']),
        this.#renderSelectors(settings, plugins),
      ]),
      el('div', { class: 'opt-tabs', id: 'opt-tabs' }, [
        el('button', { class: 'opt-tab active', dataset: { tab: 'grid' } }, ['Grid Search']),
        el('button', { class: 'opt-tab', dataset: { tab: 'walkforward' } }, ['Walk Forward']),
        el('button', { class: 'opt-tab', dataset: { tab: 'montecarlo' } }, ['Monte Carlo']),
      ]),
      el('div', { class: 'opt-content', id: 'opt-content' }),
      el('div', { class: 'opt-results', id: 'opt-results' }),
    ]));

    this.#bindEvents();
    this.#renderTab();
    log.info('Optimizer view mounted');
  }

  unmount() {
    if (this.#container) {
      this.#container.innerHTML = '';
      this.#container.classList.add('panel-body-fill');
    }
  }

  /**
   * @param {Record<string, unknown>} settings
   * @param {import('../plugin/PluginRegistry.js').PluginDescriptor[]} plugins
   * @returns {HTMLElement}
   */
  #renderSelectors(settings, plugins) {
    const stratOpts = plugins.map((p) => el('option', { value: p.id }, [p.name]));
    const symOpts = Config.SYMBOLS.map((s) =>
      el('option', { value: s, selected: s === settings.symbol }, [s])
    );
    const tfOpts = Config.TIMEFRAMES.map((t) =>
      el('option', { value: t, selected: t === settings.timeframe }, [t])
    );

    return el('div', { class: 'opt-selectors' }, [
      el('select', { class: 'data-select', id: 'opt-strategy' }, stratOpts),
      el('select', { class: 'data-select', id: 'opt-symbol' }, symOpts),
      el('select', { class: 'data-select', id: 'opt-tf' }, tfOpts),
    ]);
  }

  #bindEvents() {
    this.#container?.querySelector('#opt-tabs')?.addEventListener('click', (e) => {
      const btn = /** @type {HTMLElement} */ (e.target).closest('.opt-tab');
      if (!btn?.dataset.tab) return;
      activeTab = /** @type {'grid'|'walkforward'|'montecarlo'} */ (btn.dataset.tab);
      this.#container?.querySelectorAll('.opt-tab').forEach((t) => {
        t.classList.toggle('active', t.dataset.tab === activeTab);
      });
      this.#renderTab();
    });

    this.#container?.querySelector('#opt-strategy')?.addEventListener('change', () => {
      if (activeTab === 'grid') this.#renderTab();
    });

    bus.on(Events.OPTIMIZATION_COMPLETE, (r) => this.#renderGridResults(r));
    bus.on(Events.WALK_FORWARD_COMPLETE, (r) => this.#renderWalkForwardResults(r));
    bus.on(Events.MONTE_CARLO_COMPLETE, (r) => this.#renderMonteCarloResults(r));
  }

  #renderTab() {
    const content = this.#container?.querySelector('#opt-content');
    const results = this.#container?.querySelector('#opt-results');
    if (!content || !results) return;

    content.innerHTML = '';
    results.innerHTML = '';

    if (activeTab === 'grid') {
      this.#renderGridPanel(content);
      const last = ResearchEngine.getLastGridResult();
      if (last) this.#renderGridResults(last);
    } else if (activeTab === 'walkforward') {
      this.#renderWalkForwardPanel(content);
      const last = ResearchEngine.getLastWalkForwardResult();
      if (last) this.#renderWalkForwardResults(last);
    } else {
      this.#renderMonteCarloPanel(content);
      const last = ResearchEngine.getLastMonteCarloResult();
      if (last) this.#renderMonteCarloResults(last);
    }
  }

  /**
   * @param {HTMLElement} content
   */
  #renderGridPanel(content) {
    const strategyId = /** @type {HTMLSelectElement} */ (this.#container.querySelector('#opt-strategy')).value;
    const instance = registry.createInstance(strategyId);
    const schema = instance.getParameterSchema();

    const paramRows = schema
      .filter((d) => d.type === 'number' || d.type === 'integer')
      .map((def) => {
        const defaults = defaultGridForParam(def).join(',');
        return el('label', { class: 'opt-param-row' }, [
          el('input', { type: 'checkbox', class: 'opt-param-check', dataset: { key: def.key }, checked: def.key === 'rr' }),
          el('span', { class: 'opt-param-label' }, [def.label]),
          el('input', {
            type: 'text',
            class: 'data-select opt-param-values',
            dataset: { key: def.key },
            value: defaults,
            placeholder: 'e.g. 1,2,3 or 10:50:10',
          }),
        ]);
      });

    content.appendChild(el('div', { class: 'opt-panel' }, [
      el('p', { class: 'opt-desc' }, ['Test every parameter combination. Max ', String(Config.OPTIMIZER.MAX_COMBINATIONS), ' combos.']),
      el('div', { class: 'opt-param-grid' }, paramRows),
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
      el('div', { class: 'opt-actions' }, [
        el('button', { class: 'btn btn-primary', id: 'opt-run-grid' }, ['Run Grid Search']),
        el('span', { class: 'opt-progress', id: 'opt-progress' }, ['']),
      ]),
    ]));

    content.querySelector('#opt-run-grid')?.addEventListener('click', () => this.#runGrid());
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
      el('button', { class: 'btn btn-primary', id: 'opt-run-wf' }, ['Run Walk Forward']),
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
      el('button', { class: 'btn btn-primary', id: 'opt-run-mc' }, ['Run Monte Carlo']),
    ]));
    content.querySelector('#opt-run-mc')?.addEventListener('click', () => this.#runMonteCarlo());
  }

  #readSelectors() {
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
    const paramGrid = this.#readParamGrid();
    const rankMetric = /** @type {HTMLSelectElement} */ (this.#container.querySelector('#opt-rank')).value;
    const progress = this.#container?.querySelector('#opt-progress');

    const total = countCombinations(paramGrid);
    if (total === 0) {
      bus.emit(Events.LOG_MESSAGE, { message: 'Select at least one parameter with values', level: 'warn', time: new Date() });
      return;
    }

    if (progress) progress.textContent = `0 / ${total}`;
    try {
      await ResearchEngine.runGridSearch({
        strategyId,
        symbol,
        timeframe,
        paramGrid,
        rankMetric: /** @type {import('../optimizer/GridSearchEngine.js').RankMetric} */ (rankMetric),
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
   * @param {import('../optimizer/GridSearchEngine.js').GridSearchResult} result
   */
  #renderGridResults(result) {
    const wrap = this.#container?.querySelector('#opt-results');
    if (!wrap || activeTab !== 'grid') return;

    wrap.innerHTML = '';
    wrap.appendChild(el('div', { class: 'opt-results-header' }, [
      el('h4', {}, [`Top Results (${result.totalCombinations} combos, ${result.durationMs}ms)`]),
      el('button', { class: 'btn btn-sm', id: 'opt-export-grid' }, ['Export JSON']),
    ]));

    const top = result.entries.slice(0, 20);
    const rows = top.map((entry, i) =>
      el('tr', {}, [
        el('td', {}, [String(i + 1)]),
        el('td', { class: 'opt-mono' }, [JSON.stringify(entry.params)]),
        el('td', {}, [String(entry.result.stats.totalTrades)]),
        el('td', {}, [`${entry.result.stats.winRate.toFixed(1)}%`]),
        el('td', { class: 'opt-mono' }, [`$${entry.result.stats.netProfit.toFixed(2)}`]),
        el('td', { class: 'opt-mono' }, [`$${entry.result.stats.expectancy.toFixed(2)}`]),
        el('td', {}, [entry.result.stats.profitFactor === Infinity ? '∞' : entry.result.stats.profitFactor.toFixed(2)]),
      ])
    );

    wrap.appendChild(el('table', { class: 'data-table opt-table' }, [
      el('thead', {}, [
        el('tr', {}, ['#', 'Params', 'Trades', 'WR', 'Net', 'Exp', 'PF'].map((h) => el('th', {}, [h]))),
      ]),
      el('tbody', {}, rows),
    ]));

    wrap.querySelector('#opt-export-grid')?.addEventListener('click', () => {
      downloadFile(JSON.stringify(result, null, 2), 'grid_search.json', 'application/json');
    });
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

    wrap.appendChild(el('table', { class: 'data-table opt-table' }, [
      el('thead', {}, [
        el('tr', {}, ['Fold', 'IS Start', 'IS Trades', 'IS Net', 'OOS Trades', 'OOS Net'].map((h) => el('th', {}, [h]))),
      ]),
      el('tbody', {}, rows),
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
