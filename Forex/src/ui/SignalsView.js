/**
 * AI signal scores view — factor breakdown and filtering.
 * @module ui/SignalsView
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import ScoringEngine from '../scoring/ScoringEngine.js';
import { registry } from '../plugin/PluginRegistry.js';
import { formatTimestamp } from '../data/TimeframeUtils.js';
import { requestChartFocus } from '../utils/chartNavigation.js';
import { createHelpButton } from '../utils/contextHelp.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('SignalsView');

/**
 * @param {string} strategyId
 * @returns {string}
 */
function strategyLabel(strategyId) {
  return registry.get(strategyId)?.name ?? strategyId;
}

/** @type {number} */
let minScoreFilter = 0;

/**
 * Signals scoring view controller.
 */
class SignalsViewImpl {
  /** @type {HTMLElement|null} */
  #container = null;

  /**
   * @param {HTMLElement} container
   */
  async mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.remove('panel-body-fill');

    container.appendChild(el('div', { class: 'signals-view' }, [
      el('div', { class: 'signals-toolbar' }, [
        el('span', { class: 'signals-title' }, ['AI Signal Scores']),
        el('div', { class: 'signals-toolbar-actions' }, [
          el('label', { class: 'signals-filter' }, [
            'Min score',
            el('input', { type: 'range', id: 'sig-min-score', min: '0', max: '100', value: '0' }),
            el('span', { id: 'sig-min-label' }, ['0']),
          ]),
          createHelpButton('signals'),
        ]),
      ]),
      el('div', { class: 'signals-meta', id: 'signals-meta' }, ['Run a strategy scan first (Ctrl+3).']),
      el('div', { class: 'signals-list', id: 'signals-list' }),
    ]));

    this.#bindEvents();
    this.#render(ScoringEngine.getLastScored());
    log.info('Signals view mounted');
  }

  unmount() {
    if (this.#container) {
      this.#container.innerHTML = '';
      this.#container.classList.add('panel-body-fill');
    }
  }

  #bindEvents() {
    const slider = this.#container?.querySelector('#sig-min-score');
    slider?.addEventListener('input', (e) => {
      minScoreFilter = parseInt(/** @type {HTMLInputElement} */ (e.target).value, 10);
      const label = this.#container?.querySelector('#sig-min-label');
      if (label) label.textContent = String(minScoreFilter);
      this.#render(ScoringEngine.getLastScored());
    });

    bus.on(Events.SIGNALS_SCORED, (set) => this.#render(set));
  }

  /**
   * @param {import('../scoring/ScoringEngine.js').ScoredSignalSet|null} set
   */
  #render(set) {
    const meta = this.#container?.querySelector('#signals-meta');
    const list = this.#container?.querySelector('#signals-list');

    if (!set || set.signals.length === 0) {
      if (meta) meta.textContent = 'No signals — run Strategy scan (Ctrl+3) first.';
      if (list) list.innerHTML = '';
      return;
    }

    const filtered = set.signals.filter(
      (s) => (s.scoreBreakdown?.score ?? s.confidence) >= minScoreFilter
    );

    if (meta) {
      meta.textContent = `${strategyLabel(set.strategyId)} (${set.strategyId}) · ${set.symbol} ${set.timeframe} · ${filtered.length}/${set.signals.length} signals · avg ${set.avgScore.toFixed(0)}/100 · bấm signal để mở Chart`;
    }

    if (!list) return;
    list.innerHTML = '';

    for (const signal of filtered.slice(0, 100)) {
      const breakdown = signal.scoreBreakdown;
      const score = breakdown?.score ?? signal.confidence;
      const grade = breakdown?.grade ?? '?';

      const factors = breakdown?.factors;
      const factorBars = factors
        ? Object.entries(factors).map(([name, value]) =>
          el('div', { class: 'signal-factor' }, [
            el('span', { class: 'signal-factor-name' }, [name]),
            el('div', { class: 'signal-factor-bar' }, [
              el('div', { class: 'signal-factor-fill', style: `width:${value}%` }),
            ]),
            el('span', { class: 'signal-factor-val' }, [String(value)]),
          ])
        )
        : [];

      const jumpAt = signal.time || signal.screenshotPosition?.timestamp;
      const card = el('button', {
        type: 'button',
        class: 'signal-card signal-card-action',
        title: 'Mở Chart tại thời điểm signal',
      }, [
        el('div', { class: 'signal-card-header' }, [
          el('span', { class: `signal-grade grade-${grade}` }, [grade]),
          el('span', { class: 'signal-score' }, [`${score}/100`]),
          el('span', { class: 'signal-strategy' }, [strategyLabel(signal.strategyId)]),
          el('span', { class: `signal-dir signal-${signal.direction}` }, [signal.direction.toUpperCase()]),
          el('span', { class: 'signal-rr' }, [`${signal.rr.toFixed(1)}R`]),
        ]),
        el('div', { class: 'signal-card-meta' }, [
          el('span', { class: 'signal-time' }, [formatTimestamp(jumpAt)]),
          el('span', { class: 'signal-prices' }, [
            `E ${signal.entry.toFixed(5)} · SL ${signal.sl.toFixed(5)} · TP ${signal.tp.toFixed(5)}`,
          ]),
        ]),
        el('p', { class: 'signal-reason' }, [signal.reason || 'No reason']),
        el('div', { class: 'signal-factors' }, factorBars),
        el('span', { class: 'signal-open-hint' }, ['→ Xem trên Chart']),
      ]);

      card.addEventListener('click', () => {
        requestChartFocus({
          symbol: signal.pair,
          timeframe: signal.timeframe,
          jumpTo: jumpAt,
        });
        bus.emit(Events.LOG_MESSAGE, {
          message: `Chart: ${signal.pair} ${signal.timeframe} @ ${formatTimestamp(jumpAt)} (${strategyLabel(signal.strategyId)})`,
          level: 'info',
          time: new Date(),
        });
      });

      list.appendChild(card);
    }

    if (filtered.length > 100) {
      list.appendChild(el('p', { class: 'signals-more' }, [`Showing 100 of ${filtered.length} signals`]));
    }
  }
}

export const SignalsView = new SignalsViewImpl();
