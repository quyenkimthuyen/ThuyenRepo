/**
 * Strategy compare view — rank setups on the same pair/timeframe.
 * @module ui/CompareView
 */

import { Config } from '../core/Config.js';
import { bus, Events } from '../core/EventBus.js';
import { el, loadFromStorage } from '../utils/dom.js';
import DataManager from '../data/DataManager.js';
import StrategyEngine from '../strategy/StrategyEngine.js';
import CompareEngine from '../research/CompareEngine.js';
import { createHelpButton } from '../utils/contextHelp.js';
import { createLogger } from '../utils/logger.js';
import {
  buildSymbolOptions,
  buildTimeframeOptions,
  resolveDatasetSelection,
} from '../utils/runnableDatasets.js';

const log = createLogger('CompareView');

class CompareViewImpl {
  /** @type {HTMLElement|null} */
  #container = null;

  /** @type {string|null} */
  #selectedSymbol = null;

  /** @type {string|null} */
  #selectedTimeframe = null;

  /** @type {import('../data/Candle.js').DatasetMetadata[]} */
  #runnableDatasets = [];

  /**
   * @param {HTMLElement} container
   */
  async mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.remove('panel-body-fill');

    const settings = loadFromStorage(Config.STORAGE_KEYS.SETTINGS, {});
    await CompareEngine.initialize();
    await this.#refreshDataState(settings);

    const plugins = StrategyEngine.listPlugins();

    container.classList.add('compare-view-root');
    container.appendChild(el('div', { class: 'compare-view' }, [
      this.#renderToolbar(plugins),
      el('div', { class: 'compare-results', id: 'compare-results' }, [
        el('p', { class: 'compare-empty' }, [
          'Chọn symbol/TF và các strategy, bấm Compare để xếp hạng expectancy trên cùng dữ liệu.',
        ]),
      ]),
    ]));

    this.#bindEvents();

    const last = CompareEngine.getLastResult();
    if (last) this.#renderResults(last);

    log.info('Compare view mounted');
  }

  unmount() {
    if (this.#container) {
      this.#container.innerHTML = '';
      this.#container.classList.remove('compare-view-root');
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
   */
  #renderToolbar(plugins) {
    const hasData = this.#runnableDatasets.length > 0;
    const checks = plugins.map((p) =>
      el('label', { class: 'compare-strat-check' }, [
        el('input', {
          type: 'checkbox',
          class: 'compare-strat-cb',
          value: p.id,
          checked: true,
        }),
        ` ${p.name}`,
      ])
    );

    const children = [
      el('span', { class: 'compare-title' }, ['Strategy Compare']),
      createHelpButton('compare'),
    ];

    if (hasData) {
      children.push(
        el('select', { class: 'data-select', id: 'compare-symbol' }, buildSymbolOptions(
          this.#runnableDatasets,
          this.#selectedSymbol
        )),
        el('select', { class: 'data-select', id: 'compare-tf' }, buildTimeframeOptions(
          this.#runnableDatasets,
          this.#selectedSymbol,
          this.#selectedTimeframe
        ))
      );
    }

    children.push(
      el('button', { class: 'btn btn-primary', id: 'compare-run', disabled: !hasData }, ['Compare']),
    );

    return el('div', { class: 'compare-toolbar' }, [
      el('div', { class: 'compare-toolbar-row' }, children),
      el('div', { class: 'compare-strat-list', id: 'compare-strat-list' }, checks),
    ]);
  }

  #bindEvents() {
    this.#container?.querySelector('#compare-run')?.addEventListener('click', () => this.#run());

    this.#container?.querySelector('#compare-symbol')?.addEventListener('change', (e) => {
      this.#selectedSymbol = /** @type {HTMLSelectElement} */ (e.target).value;
      const resolved = resolveDatasetSelection(
        this.#runnableDatasets,
        this.#selectedSymbol,
        this.#selectedTimeframe ?? undefined
      );
      this.#selectedTimeframe = resolved.timeframe;
      const tfSel = this.#container?.querySelector('#compare-tf');
      if (!tfSel) return;
      tfSel.innerHTML = '';
      for (const opt of buildTimeframeOptions(
        this.#runnableDatasets,
        this.#selectedSymbol,
        this.#selectedTimeframe
      )) {
        tfSel.appendChild(opt);
      }
      if (this.#selectedTimeframe) {
        /** @type {HTMLSelectElement} */ (tfSel).value = this.#selectedTimeframe;
      }
    });

    bus.on(Events.STRATEGY_COMPARE_COMPLETE, (result) => this.#renderResults(result));
    bus.on(Events.DATA_UPDATED, async () => {
      await this.#refreshDataState();
    });
  }

  async #run() {
    const symbol = /** @type {HTMLSelectElement} */ (this.#container?.querySelector('#compare-symbol'))?.value;
    const timeframe = /** @type {HTMLSelectElement} */ (this.#container?.querySelector('#compare-tf'))?.value;
    const ids = [...(this.#container?.querySelectorAll('.compare-strat-cb:checked') ?? [])]
      .map((cb) => /** @type {HTMLInputElement} */ (cb).value);

    if (!symbol || !timeframe || ids.length === 0) {
      bus.emit(Events.LOG_MESSAGE, {
        message: 'Chọn ít nhất một strategy để so sánh',
        level: 'warn',
        time: new Date(),
      });
      return;
    }

    const wrap = this.#container?.querySelector('#compare-results');
    if (wrap) wrap.innerHTML = '<p class="compare-empty">Đang chạy…</p>';

    try {
      await CompareEngine.compare(ids, symbol, timeframe);
    } catch (err) {
      bus.emit(Events.LOG_MESSAGE, {
        message: err instanceof Error ? err.message : String(err),
        level: 'error',
        time: new Date(),
      });
      if (wrap) wrap.innerHTML = '<p class="compare-empty">Compare thất bại.</p>';
    }
  }

  /**
   * @param {import('../research/CompareEngine.js').StrategyCompareResult} result
   */
  #renderResults(result) {
    const wrap = this.#container?.querySelector('#compare-results');
    if (!wrap) return;

    wrap.innerHTML = '';
    wrap.appendChild(el('p', { class: 'compare-meta' }, [
      `${result.symbol} ${result.timeframe} · ${result.rows.length} strategies · `,
      new Date(result.comparedAt).toLocaleString(),
    ]));

    const rows = result.rows.map((row, i) => {
      const st = row.stats;
      return el('tr', { class: i === 0 ? 'compare-best-row' : '' }, [
        el('td', { class: 'compare-rank' }, [String(i + 1)]),
        el('td', {}, [row.strategyName]),
        el('td', { class: 'opt-mono' }, [String(row.signalCount)]),
        el('td', {}, [String(st.totalTrades)]),
        el('td', {}, [`${st.winRate.toFixed(1)}%`]),
        el('td', { class: 'opt-mono' }, [`$${st.netProfit.toFixed(2)}`]),
        el('td', { class: 'opt-mono' }, [`$${st.expectancy.toFixed(2)}`]),
        el('td', {}, [st.profitFactor === Infinity ? '?' : st.profitFactor.toFixed(2)]),
        el('td', { class: 'opt-mono' }, [`$${st.maxDrawdown.toFixed(2)}`]),
      ]);
    });

    wrap.appendChild(el('div', { class: 'compare-table-scroll' }, [
      el('table', { class: 'data-table compare-table' }, [
        el('thead', {}, [
          el('tr', {}, [
            '#', 'Strategy', 'Signals', 'Trades', 'WR', 'Net', 'Exp', 'PF', 'Max DD',
          ].map((h) => el('th', {}, [h]))),
        ]),
        el('tbody', {}, rows),
      ]),
    ]));
  }
}

export const CompareView = new CompareViewImpl();
