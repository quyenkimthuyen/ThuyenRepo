/**
 * Simulation workspace — Mode 1 backtest with trade engine.
 * @module ui/SimulationView
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el, loadFromStorage } from '../utils/dom.js';
import SimulationEngine from '../simulation/SimulationEngine.js';
import StrategyEngine from '../strategy/StrategyEngine.js';
import { downloadFile } from '../data/DataExporter.js';
import { createHelpButton } from '../utils/contextHelp.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('SimulationView');

/**
 * Simulation view controller.
 */
class SimulationViewImpl {
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
    const config = SimulationEngine.getConfig();

    container.appendChild(el('div', { class: 'simulation-view' }, [
      this.#renderToolbar(settings, plugins),
      this.#renderConfig(config),
      el('div', { class: 'sim-summary', id: 'sim-summary' }, [
        el('p', { class: 'sim-empty' }, ['Run a simulation to see results.']),
      ]),
      el('div', { class: 'sim-table-wrap', id: 'sim-table-wrap' }),
    ]));

    this.#bindEvents();
    log.info('Simulation view mounted');
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
  #renderToolbar(settings, plugins) {
    const stratOpts = plugins.map((p) =>
      el('option', { value: p.id }, [p.name])
    );
    const symOpts = Config.SYMBOLS.map((s) =>
      el('option', { value: s, selected: s === settings.symbol }, [s])
    );
    const tfOpts = Config.TIMEFRAMES.map((t) =>
      el('option', { value: t, selected: t === settings.timeframe }, [t])
    );

    return el('div', { class: 'sim-toolbar' }, [
      el('div', { class: 'sim-toolbar-group' }, [
        el('label', { class: 'data-label' }, ['Strategy']),
        el('select', { class: 'data-select', id: 'sim-strategy' }, stratOpts),
        el('label', { class: 'data-label' }, ['Symbol']),
        el('select', { class: 'data-select', id: 'sim-symbol' }, symOpts),
        el('label', { class: 'data-label' }, ['TF']),
        el('select', { class: 'data-select', id: 'sim-tf' }, tfOpts),
      ]),
      el('div', { class: 'sim-toolbar-group' }, [
        el('button', { class: 'btn btn-primary', id: 'sim-run' }, ['Run Simulation']),
        el('button', { class: 'btn btn-sm', id: 'sim-export' }, ['Export JSON']),
        createHelpButton('simulation'),
      ]),
    ]);
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
    ]);
  }

  #bindEvents() {
    this.#container?.querySelector('#sim-run')?.addEventListener('click', () => this.#run());
    this.#container?.querySelector('#sim-export')?.addEventListener('click', () => this.#export());
    bus.on(Events.SIMULATION_COMPLETE, (result) => this.#renderResults(result));
  }

  #readConfig() {
    const root = this.#container;
    return {
      orderType: /** @type {HTMLSelectElement} */ (root.querySelector('#sim-order-type')).value,
      spreadPips: parseFloat(/** @type {HTMLInputElement} */ (root.querySelector('#sim-spread')).value),
      slippagePips: parseFloat(/** @type {HTMLInputElement} */ (root.querySelector('#sim-slippage')).value),
      lotSize: parseFloat(/** @type {HTMLInputElement} */ (root.querySelector('#sim-lot')).value),
      trailingStopPips: parseFloat(/** @type {HTMLInputElement} */ (root.querySelector('#sim-trailing')).value),
      breakEvenAtR: parseFloat(/** @type {HTMLInputElement} */ (root.querySelector('#sim-be')).value),
      partialCloseAtR: parseFloat(/** @type {HTMLInputElement} */ (root.querySelector('#sim-partial-r')).value),
      partialClosePercent: parseFloat(/** @type {HTMLInputElement} */ (root.querySelector('#sim-partial-pct')).value),
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
    if (!result) {
      bus.emit(Events.LOG_MESSAGE, { message: 'No results to export', level: 'warn', time: new Date() });
      return;
    }
    downloadFile(JSON.stringify(result, null, 2), `simulation_${result.strategyId}.json`, 'application/json');
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
    summary.appendChild(el('div', { class: 'sim-cards' }, [
      this.#card('Trades', String(s.totalTrades)),
      this.#card('Win Rate', `${s.winRate.toFixed(1)}%`),
      this.#card('Net Profit', `$${s.netProfit.toFixed(2)}`),
      this.#card('Profit Factor', s.profitFactor === Infinity ? '∞' : s.profitFactor.toFixed(2)),
      this.#card('Signals', String(result.signalCount)),
      this.#card('Balance', `$${s.finalBalance.toFixed(2)}`),
    ]));

    tableWrap.innerHTML = '';
    if (result.trades.length === 0) {
      tableWrap.appendChild(el('p', { class: 'sim-empty' }, ['No trades executed.']));
      return;
    }

    const rows = result.trades.map((t) =>
      el('tr', {}, [
        el('td', {}, [t.direction.toUpperCase()]),
        el('td', { class: `sim-outcome sim-${t.outcome}` }, [t.outcome]),
        el('td', {}, [t.exitReason]),
        el('td', { class: 'sim-mono' }, [t.entryPrice.toFixed(5)]),
        el('td', { class: 'sim-mono' }, [t.exitPrice.toFixed(5)]),
        el('td', { class: 'sim-mono' }, [t.pips.toFixed(1)]),
        el('td', { class: `sim-mono${t.profit >= 0 ? ' sim-profit' : ' sim-loss'}` }, [
          `$${t.profit.toFixed(2)}`,
        ]),
        el('td', {}, [String(t.durationBars)]),
      ])
    );

    tableWrap.appendChild(el('table', { class: 'data-table sim-table' }, [
      el('thead', {}, [
        el('tr', {}, [
          el('th', {}, ['Dir']),
          el('th', {}, ['Outcome']),
          el('th', {}, ['Exit']),
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
