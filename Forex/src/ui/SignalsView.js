/**
 * AI signal scores view — factor breakdown, filtering, and score calibration.
 * @module ui/SignalsView
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import ScoringEngine from '../scoring/ScoringEngine.js';
import SimulationEngine from '../simulation/SimulationEngine.js';
import { registry } from '../plugin/PluginRegistry.js';
import { formatTimestamp } from '../data/TimeframeUtils.js';
import { requestChartFocus, signalToChartHighlight } from '../utils/chartNavigation.js';
import { createHelpButton } from '../utils/contextHelp.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('SignalsView');

/** @type {Record<string, string>} */
const FACTOR_LABELS = {
  trend: 'Xu hướng',
  momentum: 'Momentum',
  location: 'Vị trí SL',
  volatility: 'Biến động',
  priceActionQuality: 'PA quality',
  rr: 'RR',
  session: 'Phiên',
  spread: 'Spread',
};

/**
 * @param {string} strategyId
 * @returns {string}
 */
function strategyLabel(strategyId) {
  return registry.get(strategyId)?.name ?? strategyId;
}

/** @type {number} */
let minScoreFilter = 0;

/** @type {import('../scoring/ScoreCalibration.js').WeightSuggestion|null} */
let lastWeightSuggestion = null;

/**
 * @param {string} label
 * @param {string} value
 * @returns {HTMLElement}
 */
function metaChip(label, value) {
  return el('span', { class: 'signals-chip', title: label }, [
    el('span', { class: 'signals-chip-label' }, [`${label}: `]),
    value,
  ]);
}

/**
 * @param {number} pct
 * @returns {string}
 */
function fmtPct(pct) {
  return `${pct.toFixed(1)}%`;
}

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
      el('div', { class: 'signals-calibration', id: 'signals-calibration' }),
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
    bus.on(Events.SIMULATION_COMPLETE, () => this.#render(ScoringEngine.getLastScored()));
  }

  /**
   * @param {import('../scoring/ScoringEngine.js').ScoredSignalSet|null} set
   */
  #render(set) {
    const meta = this.#container?.querySelector('#signals-meta');
    const calibration = this.#container?.querySelector('#signals-calibration');
    const list = this.#container?.querySelector('#signals-list');

    if (!set || set.signals.length === 0) {
      if (meta) meta.textContent = 'No signals — run Strategy scan (Ctrl+3) first.';
      if (calibration) calibration.innerHTML = '';
      if (list) list.innerHTML = '';
      return;
    }

    const filtered = set.signals.filter(
      (s) => (s.scoreBreakdown?.score ?? s.confidence) >= minScoreFilter
    );

    if (meta) {
      meta.innerHTML = '';
      meta.appendChild(el('div', { class: 'signals-scan-summary' }, [
        metaChip('Strategy', `${strategyLabel(set.strategyId)} (${set.strategyId})`),
        metaChip('Symbol', set.symbol),
        metaChip('TF', set.timeframe),
        metaChip('Signals', `${filtered.length}/${set.signals.length}`),
        metaChip('Avg score', `${set.avgScore.toFixed(0)}/100`),
      ]));
      meta.appendChild(el('p', { class: 'signals-scan-hint' }, [
        'Bấm signal → Chart mở đúng Symbol/TF, nhảy tới nến setup, vẽ Entry / SL / TP.',
      ]));
    }

    this.#renderCalibration(calibration, set);

    if (!list) return;
    list.innerHTML = '';

    for (const signal of filtered.slice(0, 100)) {
      list.appendChild(this.#renderSignalCard(signal));
    }

    if (filtered.length > 100) {
      list.appendChild(el('p', { class: 'signals-more' }, [`Showing 100 of ${filtered.length} signals`]));
    }
  }

  /**
   * @param {HTMLElement|null} root
   * @param {import('../scoring/ScoringEngine.js').ScoredSignalSet} set
   */
  #renderCalibration(root, set) {
    if (!root) return;
    root.innerHTML = '';

    const sim = SimulationEngine.getLastResult();
    const report = ScoringEngine.getCalibrationReport(sim, Math.max(minScoreFilter, 65));
    const weights = ScoringEngine.getWeights();

    const panel = el('div', { class: 'signals-cal-panel' }, [
      el('div', { class: 'signals-cal-header' }, [
        el('strong', {}, ['Điểm AI vs kết quả thực tế']),
        el('span', { class: 'signals-cal-sub' }, [
          'So sánh điểm signal với lệnh Simulation (cùng Strategy / Symbol / TF).',
        ]),
      ]),
    ]);

    if (!report.matched) {
      panel.appendChild(el('p', { class: 'signals-cal-empty' }, [report.reason ?? 'Chưa có dữ liệu.']));
      root.appendChild(panel);
      return;
    }

    panel.appendChild(el('p', { class: 'signals-cal-meta' }, [
      `${report.matchedTrades} lệnh khớp`,
      report.skippedTrades ? ` · ${report.skippedTrades} lệnh không ghép được điểm` : '',
      ` · tương quan điểm/lãi: ${(report.scoreProfitCorrelation ?? 0).toFixed(2)}`,
      ` · WR điểm ≥${report.minScoreCutoffUsed}: ${fmtPct(report.highScoreWinRate ?? 0)}`,
      ` vs <${report.minScoreCutoffUsed}: ${fmtPct(report.lowScoreWinRate ?? 0)}`,
    ]));

    panel.appendChild(el('table', { class: 'signals-cal-table' }, [
      el('thead', {}, [
        el('tr', {}, [
          el('th', {}, ['Nhóm điểm']),
          el('th', {}, ['Lệnh']),
          el('th', {}, ['Win rate']),
          el('th', {}, ['Lãi TB/lệnh']),
          el('th', {}, ['Lãi tổng']),
        ]),
      ]),
      el('tbody', {}, (report.buckets ?? []).map((b) =>
        el('tr', {}, [
          el('td', {}, [b.label]),
          el('td', {}, [String(b.trades)]),
          el('td', {}, [b.trades ? fmtPct(b.winRate) : '—']),
          el('td', { class: 'signals-cal-mono' }, [b.trades ? `$${b.avgProfit.toFixed(2)}` : '—']),
          el('td', { class: 'signals-cal-mono' }, [b.trades ? `$${b.netProfit.toFixed(2)}` : '—']),
        ])
      )),
    ]));

    if (report.factors?.length) {
      panel.appendChild(el('p', { class: 'signals-cal-section-title' }, [
        'Yếu tố phân biệt thắng / thua (trung bình điểm yếu tố)',
      ]));
      panel.appendChild(el('table', { class: 'signals-cal-table signals-cal-table-factors' }, [
        el('thead', {}, [
          el('tr', {}, [
            el('th', {}, ['Yếu tố']),
            el('th', {}, ['Thắng']),
            el('th', {}, ['Thua']),
            el('th', {}, ['Chênh']),
          ]),
        ]),
        el('tbody', {}, report.factors.map((f) =>
          el('tr', {}, [
            el('td', {}, [FACTOR_LABELS[f.factor] ?? f.factor]),
            el('td', { class: 'signals-cal-mono' }, [f.avgWin.toFixed(0)]),
            el('td', { class: 'signals-cal-mono' }, [f.avgLoss.toFixed(0)]),
            el('td', { class: `signals-cal-mono${f.delta >= 0 ? ' signals-cal-pos' : ' signals-cal-neg'}` }, [
              `${f.delta >= 0 ? '+' : ''}${f.delta.toFixed(1)}`,
            ]),
          ])
        )),
      ]));
    }

    const weightRows = Object.entries(weights).map(([key, value]) =>
      el('tr', {}, [
        el('td', {}, [FACTOR_LABELS[key] ?? key]),
        el('td', { class: 'signals-cal-mono' }, [`${(value * 100).toFixed(1)}%`]),
        el('td', { class: 'signals-cal-mono', id: `sig-weight-suggest-${key}` }, ['—']),
      ])
    );

    panel.appendChild(el('p', { class: 'signals-cal-section-title' }, ['Trọng số chấm điểm (đang dùng)']));
    panel.appendChild(el('table', { class: 'signals-cal-table signals-cal-table-weights', id: 'sig-weights-table' }, [
      el('thead', {}, [
        el('tr', {}, [
          el('th', {}, ['Yếu tố']),
          el('th', {}, ['Hiện tại']),
          el('th', {}, ['Gợi ý']),
        ]),
      ]),
      el('tbody', {}, weightRows),
    ]));

    const suggestNote = el('p', { class: 'signals-cal-note', id: 'sig-weight-note' }, [
      'Bấm 「Gợi ý trọng số」 để tối ưu trên lệnh đã mô phỏng (sample nhỏ dễ học vẹt).',
    ]);
    panel.appendChild(suggestNote);

    panel.appendChild(el('div', { class: 'signals-cal-actions' }, [
      el('button', { class: 'btn btn-sm btn-secondary', id: 'sig-suggest-weights', type: 'button' }, [
        'Gợi ý trọng số',
      ]),
      el('button', { class: 'btn btn-sm btn-primary', id: 'sig-apply-weights', type: 'button', disabled: true }, [
        'Áp dụng gợi ý',
      ]),
      el('button', { class: 'btn btn-sm', id: 'sig-reset-weights', type: 'button' }, [
        'Về mặc định',
      ]),
    ]));

    root.appendChild(panel);

    if (lastWeightSuggestion) {
      this.#fillWeightSuggestion(lastWeightSuggestion);
    }

    root.querySelector('#sig-suggest-weights')?.addEventListener('click', () => {
      if (!sim) return;
      lastWeightSuggestion = ScoringEngine.suggestWeights(sim);
      this.#fillWeightSuggestion(lastWeightSuggestion);
      const applyBtn = /** @type {HTMLButtonElement} */ (root.querySelector('#sig-apply-weights'));
      if (applyBtn) applyBtn.disabled = false;
    });

    root.querySelector('#sig-apply-weights')?.addEventListener('click', async () => {
      if (!lastWeightSuggestion) return;
      await ScoringEngine.applyWeights(lastWeightSuggestion.weights);
      lastWeightSuggestion = null;
      this.#render(ScoringEngine.getLastScored());
    });

    root.querySelector('#sig-reset-weights')?.addEventListener('click', async () => {
      lastWeightSuggestion = null;
      await ScoringEngine.resetWeights();
      this.#render(ScoringEngine.getLastScored());
    });
  }

  /**
   * @param {import('../scoring/ScoreCalibration.js').WeightSuggestion} suggestion
   */
  #fillWeightSuggestion(suggestion) {
    const note = this.#container?.querySelector('#sig-weight-note');
    if (note) {
      note.textContent = [
        suggestion.note,
        ` Fitness: ${suggestion.baselineFitness.toFixed(3)} → ${suggestion.fitness.toFixed(3)}.`,
      ].join('');
    }
    for (const [key, value] of Object.entries(suggestion.weights)) {
      const cell = this.#container?.querySelector(`#sig-weight-suggest-${key}`);
      if (cell) cell.textContent = `${(value * 100).toFixed(1)}%`;
    }
  }

  /**
   * @param {import('../scoring/SignalScoreEngine.js').ScoredSignal} signal
   * @returns {HTMLElement}
   */
  #renderSignalCard(signal) {
    const breakdown = signal.scoreBreakdown;
    const score = breakdown?.score ?? signal.confidence;
    const grade = breakdown?.grade ?? '?';
    const jumpAt = signal.time || signal.screenshotPosition?.timestamp;
    const barIndex = signal.screenshotPosition?.candleIndex;

    const factors = breakdown?.factors;
    const factorBars = factors
      ? Object.entries(factors).map(([name, value]) =>
        el('div', { class: 'signal-factor' }, [
          el('span', { class: 'signal-factor-name' }, [FACTOR_LABELS[name] ?? name]),
          el('div', { class: 'signal-factor-bar' }, [
            el('div', { class: 'signal-factor-fill', style: `width:${value}%` }),
          ]),
          el('span', { class: 'signal-factor-val' }, [String(value)]),
        ])
      )
      : [];

    const card = el('button', {
      type: 'button',
      class: 'signal-card signal-card-action',
      title: 'Mở Chart tại thời điểm signal và xem Entry / SL / TP',
    }, [
      el('div', { class: 'signal-card-tags' }, [
        el('span', { class: 'signals-chip signals-chip-strategy' }, [strategyLabel(signal.strategyId)]),
        el('span', { class: 'signals-chip' }, [signal.pair]),
        el('span', { class: 'signals-chip' }, [signal.timeframe]),
        barIndex != null ? el('span', { class: 'signals-chip' }, [`Bar ${barIndex}`]) : null,
      ].filter(Boolean)),
      el('div', { class: 'signal-card-header' }, [
        el('span', { class: `signal-grade grade-${grade}` }, [grade]),
        el('span', { class: 'signal-score' }, [`${score}/100`]),
        el('span', { class: `signal-dir signal-${signal.direction}` }, [signal.direction.toUpperCase()]),
        el('span', { class: 'signal-rr' }, [`${signal.rr.toFixed(1)}R`]),
      ]),
      el('div', { class: 'signal-card-meta' }, [
        el('span', { class: 'signal-time' }, [formatTimestamp(jumpAt)]),
        el('span', { class: 'signal-prices' }, [
          `Entry ${signal.entry.toFixed(5)} · SL ${signal.sl.toFixed(5)} · TP ${signal.tp.toFixed(5)}`,
        ]),
      ]),
      el('p', { class: 'signal-reason' }, [signal.reason || 'No reason']),
      el('div', { class: 'signal-factors' }, factorBars),
      el('span', { class: 'signal-open-hint' }, ['→ Kiểm chứng setup trên Chart']),
    ]);

    card.addEventListener('click', () => {
      const highlight = signalToChartHighlight(signal);
      requestChartFocus({
        symbol: signal.pair,
        timeframe: signal.timeframe,
        jumpTo: highlight.time,
        signal: highlight,
      });
      bus.emit(Events.LOG_MESSAGE, {
        message: `Chart: ${highlight.strategyName} · ${highlight.symbol} ${highlight.timeframe} @ ${formatTimestamp(highlight.time)}`,
        level: 'info',
        time: new Date(),
      });
    });

    return card;
  }
}

export const SignalsView = new SignalsViewImpl();
