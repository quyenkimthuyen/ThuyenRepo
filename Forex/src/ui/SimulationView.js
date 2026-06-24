/**
 * Simulation workspace — Mode 1 backtest with trade engine.
 * @module ui/SimulationView
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el, loadFromStorage } from '../utils/dom.js';
import DataManager from '../data/DataManager.js';
import SimulationEngine from '../simulation/SimulationEngine.js';
import StrategyEngine from '../strategy/StrategyEngine.js';
import { downloadFile } from '../data/DataExporter.js';
import { createHelpButton } from '../utils/contextHelp.js';
import { createLogger } from '../utils/logger.js';
import { formatTimestamp } from '../data/TimeframeUtils.js';
import { requestChartFocus, tradeToChartHighlight } from '../utils/chartNavigation.js';
import {
  buildSymbolOptions,
  buildTimeframeOptions,
  resolveDatasetSelection,
} from '../utils/runnableDatasets.js';

const log = createLogger('SimulationView');

/**
 * Simulation view controller.
 */
class SimulationViewImpl {
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

  /**
   * @param {HTMLElement} container
   */
  async mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.remove('panel-body-fill');

    const settings = loadFromStorage(Config.STORAGE_KEYS.SETTINGS, {});
    const plugins = StrategyEngine.listPlugins();
    const config = SimulationEngine.getConfig();

    await this.#refreshDataState(settings);

    container.appendChild(el('div', { class: 'simulation-view' }, [
      this.#renderToolbar(plugins),
      this.#renderConfig(config),
      el('div', { class: 'sim-summary', id: 'sim-summary' }, [
        el('p', { class: 'sim-empty' }, ['Run a simulation to see results.']),
      ]),
      el('div', { class: 'sim-table-wrap', id: 'sim-table-wrap' }),
    ]));

    this.#bindEvents();

    const last = SimulationEngine.getLastResult();
    if (last?.runContext) {
      this.#applyRunContext(last.runContext);
    }
    this.#syncResultsWithSettings();

    log.info('Simulation view mounted');
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
   * @param {import('../plugin/PluginRegistry.js').PluginDescriptor[]} plugins
   * @returns {HTMLElement}
   */
  #renderToolbar(plugins) {
    const hasData = this.#runnableDatasets.length > 0;
    const stratOpts = plugins.map((p) =>
      el('option', { value: p.id }, [p.name])
    );

    const children = [
      el('div', { class: 'sim-toolbar-group' }, [
        el('label', { class: 'data-label' }, ['Strategy']),
        el('select', { class: 'data-select', id: 'sim-strategy' }, stratOpts),
      ]),
    ];

    if (hasData) {
      children[0].append(
        el('label', { class: 'data-label' }, ['Symbol']),
        el('select', { class: 'data-select', id: 'sim-symbol' }, buildSymbolOptions(
          this.#runnableDatasets,
          this.#selectedSymbol
        )),
        el('label', { class: 'data-label' }, ['TF']),
        el('select', { class: 'data-select', id: 'sim-tf' }, buildTimeframeOptions(
          this.#runnableDatasets,
          this.#selectedSymbol,
          this.#selectedTimeframe
        ))
      );
    } else {
      children.push(el('span', { class: 'sim-no-data-hint' }, [
        'Chưa có dữ liệu — mở Data Manager để import hoặc tải mặc định.',
      ]));
    }

    children.push(el('div', { class: 'sim-toolbar-group' }, [
      el('button', {
        class: 'btn btn-primary',
        id: 'sim-run',
        disabled: !hasData,
      }, ['Run Simulation']),
      el('button', { class: 'btn btn-sm', id: 'sim-export' }, ['Export JSON']),
      createHelpButton('simulation'),
    ]));

    return el('div', { class: 'sim-toolbar', id: 'sim-toolbar' }, children);
  }

  async #refreshToolbar() {
    const plugins = StrategyEngine.listPlugins();
    await this.#refreshDataState();
    const toolbar = this.#container?.querySelector('#sim-toolbar');
    if (!toolbar) return;
    toolbar.replaceWith(this.#renderToolbar(plugins));
    this.#bindToolbarEvents();
    this.#syncResultsWithSettings();
  }

  /**
   * @param {import('../simulation/TradeConfig.js').TradeConfig} config
   * @returns {HTMLElement}
   */
  #renderConfig(config) {
    return el('div', { class: 'sim-config' }, [
      el('div', { class: 'sim-config-row' }, [
        el('label', { class: 'sim-field' }, [
          'Order',
          el('select', { class: 'data-select', id: 'sim-order-type' }, [
            el('option', { value: 'market', selected: config.orderType === 'market' }, ['Market']),
            el('option', { value: 'pending', selected: config.orderType === 'pending' }, ['Pending']),
          ]),
        ]),
        el('label', { class: 'sim-field' }, [
          'Spread (pips)',
          el('input', { type: 'number', class: 'data-select', id: 'sim-spread', value: String(config.spreadPips), step: '0.1' }),
        ]),
        el('label', { class: 'sim-field' }, [
          'Slippage (pips)',
          el('input', { type: 'number', class: 'data-select', id: 'sim-slippage', value: String(config.slippagePips), step: '0.1' }),
        ]),
        el('label', { class: 'sim-field' }, [
          'Lot size',
          el('input', { type: 'number', class: 'data-select', id: 'sim-lot', value: String(config.lotSize), step: '0.01' }),
        ]),
      ]),
      el('div', { class: 'sim-config-row' }, [
        el('label', { class: 'sim-field' }, [
          'Trailing (pips)',
          el('input', { type: 'number', class: 'data-select', id: 'sim-trailing', value: String(config.trailingStopPips), step: '1' }),
        ]),
        el('label', { class: 'sim-field' }, [
          'Break-even at R',
          el('input', { type: 'number', class: 'data-select', id: 'sim-be', value: String(config.breakEvenAtR), step: '0.5' }),
        ]),
        el('label', { class: 'sim-field' }, [
          'Partial at R',
          el('input', { type: 'number', class: 'data-select', id: 'sim-partial-r', value: String(config.partialCloseAtR), step: '0.5' }),
        ]),
        el('label', { class: 'sim-field' }, [
          'Partial %',
          el('input', { type: 'number', class: 'data-select', id: 'sim-partial-pct', value: String(config.partialClosePercent), step: '5' }),
        ]),
      ]),
      el('div', { class: 'sim-config-row sim-ai-row' }, [
        el('label', { class: 'sim-field sim-field-check' }, [
          el('input', {
            type: 'checkbox',
            id: 'sim-ai-filter',
            checked: (config.minAiScore ?? 0) > 0,
          }),
          ' AI score filter',
        ]),
        el('label', { class: 'sim-field' }, [
          'Min score',
          el('input', {
            type: 'number',
            class: 'data-select',
            id: 'sim-min-ai',
            value: String(config.minAiScore > 0 ? config.minAiScore : Config.SIMULATION.DEFAULT_MIN_AI_SCORE),
            min: '0',
            max: '100',
            step: '1',
          }),
        ]),
        el('label', { class: 'sim-field sim-field-check' }, [
          el('input', {
            type: 'checkbox',
            id: 'sim-ai-compare',
            checked: Boolean(config.compareAiFilter),
          }),
          ' Compare vs all signals',
        ]),
      ]),
    ]);
  }

  #bindEvents() {
    this.#bindToolbarEvents();
    this.#bindConfigEvents();
    const unsubData = bus.on(Events.DATA_UPDATED, () => this.#refreshToolbar());
    const unsubSim = bus.on(Events.SIMULATION_COMPLETE, (result) => {
      if (result.runContext) {
        this.#applyRunContext(result.runContext);
      }
      this.#renderResults(result);
    });
    this.#unsub = () => {
      unsubData();
      unsubSim();
    };
  }

  #bindConfigEvents() {
    const root = this.#container;
    if (!root) return;

    const selectors = [
      '#sim-order-type',
      '#sim-spread',
      '#sim-slippage',
      '#sim-lot',
      '#sim-trailing',
      '#sim-be',
      '#sim-partial-r',
      '#sim-partial-pct',
      '#sim-ai-filter',
      '#sim-min-ai',
      '#sim-ai-compare',
    ];

    for (const sel of selectors) {
      root.querySelector(sel)?.addEventListener('change', () => this.#syncResultsWithSettings());
      root.querySelector(sel)?.addEventListener('input', () => this.#syncResultsWithSettings());
    }
  }

  #bindToolbarEvents() {
    this.#container?.querySelector('#sim-run')?.addEventListener('click', () => this.#run());
    this.#container?.querySelector('#sim-export')?.addEventListener('click', () => this.#export());

    this.#container?.querySelector('#sim-strategy')?.addEventListener('change', () => {
      this.#syncResultsWithSettings();
    });

    this.#container?.querySelector('#sim-symbol')?.addEventListener('change', (e) => {
      this.#selectedSymbol = /** @type {HTMLSelectElement} */ (e.target).value;
      const resolved = resolveDatasetSelection(
        this.#runnableDatasets,
        this.#selectedSymbol,
        this.#selectedTimeframe ?? undefined
      );
      this.#selectedTimeframe = resolved.timeframe;

      const tfSelect = this.#container?.querySelector('#sim-tf');
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
      this.#syncResultsWithSettings();
    });

    this.#container?.querySelector('#sim-tf')?.addEventListener('change', (e) => {
      this.#selectedTimeframe = /** @type {HTMLSelectElement} */ (e.target).value;
      this.#syncResultsWithSettings();
    });
  }

  #readConfig() {
    const root = this.#container;
    const useAiFilter = /** @type {HTMLInputElement} */ (root.querySelector('#sim-ai-filter'))?.checked ?? false;
    const minAiRaw = parseInt(/** @type {HTMLInputElement} */ (root.querySelector('#sim-min-ai')).value, 10);
    const compareAiFilter = /** @type {HTMLInputElement} */ (root.querySelector('#sim-ai-compare'))?.checked ?? false;

    return {
      orderType: /** @type {HTMLSelectElement} */ (root.querySelector('#sim-order-type')).value,
      spreadPips: parseFloat(/** @type {HTMLInputElement} */ (root.querySelector('#sim-spread')).value),
      slippagePips: parseFloat(/** @type {HTMLInputElement} */ (root.querySelector('#sim-slippage')).value),
      lotSize: parseFloat(/** @type {HTMLInputElement} */ (root.querySelector('#sim-lot')).value),
      trailingStopPips: parseFloat(/** @type {HTMLInputElement} */ (root.querySelector('#sim-trailing')).value),
      breakEvenAtR: parseFloat(/** @type {HTMLInputElement} */ (root.querySelector('#sim-be')).value),
      partialCloseAtR: parseFloat(/** @type {HTMLInputElement} */ (root.querySelector('#sim-partial-r')).value),
      partialClosePercent: parseFloat(/** @type {HTMLInputElement} */ (root.querySelector('#sim-partial-pct')).value),
      minAiScore: useAiFilter ? Math.max(0, Math.min(100, minAiRaw || 0)) : 0,
      compareAiFilter: useAiFilter && compareAiFilter,
    };
  }

  async #run() {
    const strategyId = /** @type {HTMLSelectElement} */ (this.#container.querySelector('#sim-strategy')).value;
    const symbol = /** @type {HTMLSelectElement} */ (this.#container.querySelector('#sim-symbol')).value;
    const timeframe = /** @type {HTMLSelectElement} */ (this.#container.querySelector('#sim-tf')).value;
    const config = this.#readConfig();

    SimulationEngine.setConfig(config);

    try {
      const summary = this.#container.querySelector('#sim-summary');
      if (summary) summary.innerHTML = '<p class="sim-empty">Running…</p>';
      await SimulationEngine.runMode1(strategyId, symbol, timeframe, config);
    } catch (err) {
      bus.emit(Events.LOG_MESSAGE, {
        message: `Simulation failed: ${err.message}`,
        level: 'error',
        time: new Date(),
      });
    }
  }

  #export() {
    const result = SimulationEngine.getLastResult();
    const current = this.#readRunContext();
    if (!result || !this.#contextMatches(result.runContext, current)) {
      bus.emit(Events.LOG_MESSAGE, {
        message: 'Không có kết quả khớp cài đặt hiện tại để export',
        level: 'warn',
        time: new Date(),
      });
      return;
    }
    downloadFile(JSON.stringify(result, null, 2), `simulation_${result.strategyId}.json`, 'application/json');
  }

  /**
   * @returns {import('../simulation/SimulationEngine.js').SimulationRunContext|null}
   */
  #readRunContext() {
    const root = this.#container;
    if (!root?.querySelector('#sim-strategy')) return null;

    return {
      strategyId: /** @type {HTMLSelectElement} */ (root.querySelector('#sim-strategy')).value,
      symbol: /** @type {HTMLSelectElement} */ (root.querySelector('#sim-symbol')).value,
      timeframe: /** @type {HTMLSelectElement} */ (root.querySelector('#sim-tf')).value,
      config: this.#readConfig(),
    };
  }

  /**
   * @param {import('../simulation/SimulationEngine.js').SimulationRunContext|undefined} saved
   * @param {import('../simulation/SimulationEngine.js').SimulationRunContext|null} current
   * @returns {boolean}
   */
  #contextMatches(saved, current) {
    if (!saved || !current) return false;
    if (saved.strategyId !== current.strategyId) return false;
    if (saved.symbol !== current.symbol) return false;
    if (saved.timeframe !== current.timeframe) return false;

    const keys = [
      'orderType',
      'spreadPips',
      'slippagePips',
      'lotSize',
      'trailingStopPips',
      'breakEvenAtR',
      'partialCloseAtR',
      'partialClosePercent',
      'minAiScore',
      'compareAiFilter',
    ];
    for (const key of keys) {
      if (saved.config[key] !== current.config[key]) return false;
    }
    return true;
  }

  /**
   * Show results only when they match the current toolbar + config.
   */
  #syncResultsWithSettings() {
    const last = SimulationEngine.getLastResult();
    const current = this.#readRunContext();
    if (last && this.#contextMatches(last.runContext, current)) {
      this.#renderResults(last);
      return;
    }
    this.#clearResultsDisplay(Boolean(last?.runContext));
  }

  /**
   * @param {boolean} [settingsChanged=false]
   */
  #clearResultsDisplay(settingsChanged = false) {
    const summary = this.#container?.querySelector('#sim-summary');
    const tableWrap = this.#container?.querySelector('#sim-table-wrap');
    if (!summary || !tableWrap) return;

    summary.innerHTML = '';
    tableWrap.innerHTML = '';

    if (settingsChanged) {
      summary.appendChild(el('p', { class: 'sim-empty sim-stale' }, [
        'Đã thay đổi cài đặt — bấm Run Simulation để xem kết quả mới.',
      ]));
    } else {
      summary.appendChild(el('p', { class: 'sim-empty' }, [
        'Run a simulation to see results.',
      ]));
    }
  }

  /**
   * Apply saved run context to toolbar + config inputs.
   * @param {import('../simulation/SimulationEngine.js').SimulationRunContext} ctx
   */
  #applyRunContext(ctx) {
    const root = this.#container;
    if (!root) return;

    const strat = root.querySelector('#sim-strategy');
    const sym = root.querySelector('#sim-symbol');
    const tf = root.querySelector('#sim-tf');

    if (strat) strat.value = ctx.strategyId;

    if (sym && ctx.symbol) {
      sym.value = ctx.symbol;
      this.#selectedSymbol = ctx.symbol;
    }

    if (tf && ctx.timeframe) {
      this.#selectedTimeframe = ctx.timeframe;
      tf.innerHTML = '';
      for (const opt of buildTimeframeOptions(
        this.#runnableDatasets,
        this.#selectedSymbol,
        this.#selectedTimeframe
      )) {
        tf.appendChild(opt);
      }
      tf.value = ctx.timeframe;
    }

    const cfg = ctx.config;
    const setVal = (id, value) => {
      const el = root.querySelector(id);
      if (el) /** @type {HTMLInputElement|HTMLSelectElement} */ (el).value = String(value);
    };
    setVal('#sim-order-type', cfg.orderType);
    setVal('#sim-spread', cfg.spreadPips);
    setVal('#sim-slippage', cfg.slippagePips);
    setVal('#sim-lot', cfg.lotSize);
    setVal('#sim-trailing', cfg.trailingStopPips);
    setVal('#sim-be', cfg.breakEvenAtR);
    setVal('#sim-partial-r', cfg.partialCloseAtR);
    setVal('#sim-partial-pct', cfg.partialClosePercent);
    const aiFilter = root.querySelector('#sim-ai-filter');
    const minAi = root.querySelector('#sim-min-ai');
    const aiCompare = root.querySelector('#sim-ai-compare');
    if (aiFilter) /** @type {HTMLInputElement} */ (aiFilter).checked = (cfg.minAiScore ?? 0) > 0;
    if (minAi) {
      /** @type {HTMLInputElement} */ (minAi).value = String(
        cfg.minAiScore > 0 ? cfg.minAiScore : Config.SIMULATION.DEFAULT_MIN_AI_SCORE
      );
    }
    if (aiCompare) /** @type {HTMLInputElement} */ (aiCompare).checked = Boolean(cfg.compareAiFilter);
  }

  /**
   * @param {import('../simulation/TradeSimulator.js').TradeResult} trade
   * @returns {import('../strategy/Signal.js').Signal|undefined}
   */
  #findSignalForTrade(trade) {
    const scan = StrategyEngine.getLastResult(trade.strategyId);
    if (!scan) return undefined;
    if (scan.symbol !== trade.symbol || scan.timeframe !== trade.timeframe) return undefined;
    return scan.signals.find((s) => s.id === trade.signalId);
  }

  /**
   * @param {import('../simulation/TradeSimulator.js').TradeResult} trade
   */
  #openTradeOnChart(trade) {
    const sourceSignal = this.#findSignalForTrade(trade);
    const highlight = tradeToChartHighlight(trade, sourceSignal);
    requestChartFocus({
      symbol: trade.symbol,
      timeframe: trade.timeframe,
      jumpTo: highlight.time,
      signal: highlight,
    });
    bus.emit(Events.LOG_MESSAGE, {
      message: `Chart: ${highlight.strategyName} · ${trade.symbol} ${trade.timeframe} @ ${formatTimestamp(highlight.time)} (${trade.outcome})`,
      level: 'info',
      time: new Date(),
    });
  }

  /**
   * @param {import('../simulation/SimulationEngine.js').SimulationResult} result
   */
  #renderResults(result) {
    const summary = this.#container?.querySelector('#sim-summary');
    const tableWrap = this.#container?.querySelector('#sim-table-wrap');
    if (!summary || !tableWrap) return;

    const s = result.summary;
    summary.innerHTML = '';
    summary.appendChild(el('div', { class: 'sim-run-meta' }, [
      el('span', { class: 'sim-run-meta-ok' }, ['Kết quả khớp cài đặt hiện tại']),
      el('span', {}, [
        `${result.strategyId} · ${result.symbol} ${result.timeframe} · ${result.durationMs}ms`,
      ]),
    ]));
    summary.appendChild(el('div', { class: 'sim-cards' }, [
      this.#card('Trades', String(s.totalTrades)),
      this.#card('Win Rate', `${s.winRate.toFixed(1)}%`),
      this.#card('Net Profit', `$${s.netProfit.toFixed(2)}`),
      this.#card('Profit Factor', s.profitFactor === Infinity ? '∞' : s.profitFactor.toFixed(2)),
      this.#card('Signals', String(result.signalCount)),
      this.#card('Balance', `$${s.finalBalance.toFixed(2)}`),
    ]));

    if (result.aiComparison) {
      const cmp = result.aiComparison;
      const b = cmp.baselineSummary;
      const f = cmp.filteredSummary;
      summary.appendChild(el('div', { class: 'sim-ai-compare' }, [
        el('div', { class: 'sim-ai-compare-title' }, [
          `AI filter ≥ ${cmp.minScore} — ${cmp.filteredSignalCount} / ${cmp.baselineSignalCount} signals`,
        ]),
        el('div', { class: 'sim-ai-compare-grid' }, [
          el('div', { class: 'sim-ai-col' }, [
            el('h5', {}, ['All signals']),
            el('p', { class: 'sim-ai-stat' }, [`Trades: ${b.totalTrades} · WR ${b.winRate.toFixed(1)}%`]),
            el('p', { class: 'sim-ai-stat' }, [`Net $${b.netProfit.toFixed(2)} · Exp $${b.expectancy.toFixed(2)}`]),
          ]),
          el('div', { class: 'sim-ai-col' }, [
            el('h5', {}, [`Filtered ≥ ${cmp.minScore}`]),
            el('p', { class: 'sim-ai-stat' }, [`Trades: ${f.totalTrades} · WR ${f.winRate.toFixed(1)}%`]),
            el('p', { class: 'sim-ai-stat' }, [`Net $${f.netProfit.toFixed(2)} · Exp $${f.expectancy.toFixed(2)}`]),
          ]),
        ]),
      ]));
    }

    tableWrap.innerHTML = '';
    tableWrap.appendChild(el('p', { class: 'sim-table-hint' }, [
      'Bấm một dòng lệnh → Chart mở đúng Symbol/TF, nhảy tới nến vào lệnh, vẽ Entry / SL / TP.',
    ]));

    if (result.trades.length === 0) {
      tableWrap.appendChild(el('p', { class: 'sim-empty' }, ['No trades executed.']));
      return;
    }

    const rows = result.trades.map((t) => {
      const row = el('tr', {
        class: 'sim-row-action',
        title: 'Mở Chart tại thời điểm vào lệnh',
      }, [
        el('td', {}, [t.direction.toUpperCase()]),
        el('td', { class: `sim-outcome sim-${t.outcome}` }, [t.outcome]),
        el('td', {}, [t.exitReason]),
        el('td', { class: 'sim-mono sim-time' }, [formatTimestamp(t.entryTime)]),
        el('td', { class: 'sim-mono' }, [t.entryPrice.toFixed(5)]),
        el('td', { class: 'sim-mono' }, [t.exitPrice.toFixed(5)]),
        el('td', { class: 'sim-mono' }, [t.pips.toFixed(1)]),
        el('td', { class: `sim-mono${t.profit >= 0 ? ' sim-profit' : ' sim-loss'}` }, [
          `$${t.profit.toFixed(2)}`,
        ]),
        el('td', {}, [String(t.durationBars)]),
      ]);
      row.addEventListener('click', () => this.#openTradeOnChart(t));
      return row;
    });

    tableWrap.appendChild(el('table', { class: 'data-table sim-table' }, [
      el('thead', {}, [
        el('tr', {}, [
          el('th', {}, ['Dir']),
          el('th', {}, ['Outcome']),
          el('th', {}, ['Exit']),
          el('th', {}, ['Entry time']),
          el('th', {}, ['Entry']),
          el('th', {}, ['Exit Px']),
          el('th', {}, ['Pips']),
          el('th', {}, ['Profit']),
          el('th', {}, ['Bars']),
        ]),
      ]),
      el('tbody', {}, rows),
    ]));
  }

  /**
   * @param {string} label
   * @param {string} value
   * @returns {HTMLElement}
   */
  #card(label, value) {
    return el('div', { class: 'sim-card' }, [
      el('span', { class: 'sim-card-label' }, [label]),
      el('span', { class: 'sim-card-value' }, [value]),
    ]);
  }
}

export const SimulationView = new SimulationViewImpl();
