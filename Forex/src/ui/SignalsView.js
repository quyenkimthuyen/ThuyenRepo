/**
 * AI signal scores — list + simulation calibration (tabbed layout).
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
  priceActionQuality: 'PA',
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

/** @type {'list' | 'calibration'} */
let activeTab = 'list';

/** @type {import('../scoring/ScoreCalibration.js').WeightSuggestion|null} */
let lastWeightSuggestion = null;

/**
 * @param {number} pct
 * @returns {string}
 */
function fmtPct(pct) {
  return `${pct.toFixed(1)}%`;
}

/**
 * @param {string} label
 * @param {string} value
 * @param {string} [tone]
 * @returns {HTMLElement}
 */
function statCard(label, value, tone = '') {
  return el('div', { class: `signals-stat${tone ? ` signals-stat-${tone}` : ''}` }, [
    el('span', { class: 'signals-stat-label' }, [label]),
    el('span', { class: 'signals-stat-value' }, [value]),
  ]);
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
      el('div', { class: 'signals-header' }, [
        el('div', { class: 'signals-header-top' }, [
          el('span', { class: 'signals-title' }, ['AI Signals']),
          el('span', { class: 'signals-subtitle' }, ['Chấm & lọc setup — không dự đoán thắng/thua']),
          createHelpButton('signals'),
        ]),
        el('div', { class: 'signals-context', id: 'signals-context' }, [
          el('p', { class: 'signals-empty-hint' }, ['Chạy Strategies (Ctrl+3) để quét tín hiệu.']),
        ]),
      ]),
      el('div', { class: 'signals-tabbar', id: 'signals-tabbar' }, [
        el('button', {
          type: 'button',
          class: 'signals-tab active',
          dataset: { tab: 'list' },
        }, ['Danh sách']),
        el('button', {
          type: 'button',
          class: 'signals-tab',
          dataset: { tab: 'calibration' },
        }, ['Đối chiếu Simulation']),
      ]),
      el('div', { class: 'signals-panel signals-panel-list', id: 'signals-panel-list' }, [
        el('div', { class: 'signals-list-controls' }, [
          el('label', { class: 'signals-filter' }, [
            'Min score',
            el('input', { type: 'range', id: 'sig-min-score', min: '0', max: '100', value: '0' }),
            el('span', { id: 'sig-min-label' }, ['0']),
          ]),
          el('span', { class: 'signals-list-hint' }, ['Bấm signal → mở Chart kiểm tra setup']),
        ]),
        el('div', { class: 'signals-list', id: 'signals-list' }),
      ]),
      el('div', {
        class: 'signals-panel signals-panel-calibration hidden',
        id: 'signals-panel-calibration',
      }),
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

    this.#container?.querySelector('#signals-tabbar')?.addEventListener('click', (e) => {
      const btn = /** @type {HTMLElement} */ (e.target).closest('.signals-tab');
      if (!btn?.dataset.tab) return;
      activeTab = /** @type {'list'|'calibration'} */ (btn.dataset.tab);
      this.#container?.querySelectorAll('.signals-tab').forEach((tab) => {
        tab.classList.toggle('active', tab.dataset.tab === activeTab);
      });
      this.#syncPanels();
    });

    bus.on(Events.SIGNALS_SCORED, (set) => this.#render(set));
    bus.on(Events.SIMULATION_COMPLETE, () => this.#render(ScoringEngine.getLastScored()));
  }

  #syncPanels() {
    const listPanel = this.#container?.querySelector('#signals-panel-list');
    const calPanel = this.#container?.querySelector('#signals-panel-calibration');
    listPanel?.classList.toggle('hidden', activeTab !== 'list');
    calPanel?.classList.toggle('hidden', activeTab !== 'calibration');
  }

  /**
   * @param {import('../scoring/ScoringEngine.js').ScoredSignalSet|null} set
   */
  #render(set) {
    this.#renderContext(set);
    this.#renderList(set);
    this.#renderCalibrationPanel(set);
    this.#syncPanels();

    const calTab = this.#container?.querySelector('.signals-tab[data-tab="calibration"]');
    const sim = SimulationEngine.getLastResult();
    const report = set ? ScoringEngine.getCalibrationReport(sim, Math.max(minScoreFilter, 65)) : null;
    if (calTab) {
      calTab.classList.toggle('signals-tab-ready', Boolean(report?.matched));
    }
  }

  /**
   * @param {import('../scoring/ScoringEngine.js').ScoredSignalSet|null} set
   */
  #renderContext(set) {
    const ctx = this.#container?.querySelector('#signals-context');
    if (!ctx) return;

    if (!set || set.signals.length === 0) {
      ctx.innerHTML = '';
      ctx.appendChild(el('p', { class: 'signals-empty-hint' }, [
        'Chạy Strategies (Ctrl+3) để quét tín hiệu.',
      ]));
      return;
    }

    const filtered = set.signals.filter(
      (s) => (s.scoreBreakdown?.score ?? s.confidence) >= minScoreFilter
    );

    ctx.innerHTML = '';
    ctx.appendChild(el('div', { class: 'signals-context-chips' }, [
      el('span', { class: 'signals-chip signals-chip-strategy' }, [
        strategyLabel(set.strategyId),
      ]),
      el('span', { class: 'signals-chip' }, [set.symbol]),
      el('span', { class: 'signals-chip' }, [set.timeframe]),
      el('span', { class: 'signals-chip' }, [`${filtered.length}/${set.signals.length} hiển thị`]),
      el('span', { class: 'signals-chip' }, [`TB ${set.avgScore.toFixed(0)}/100`]),
    ]));
  }

  /**
   * @param {import('../scoring/ScoringEngine.js').ScoredSignalSet|null} set
   */
  #renderList(set) {
    const list = this.#container?.querySelector('#signals-list');
    if (!list) return;
    list.innerHTML = '';

    if (!set || set.signals.length === 0) return;

    const filtered = set.signals.filter(
      (s) => (s.scoreBreakdown?.score ?? s.confidence) >= minScoreFilter
    );

    if (filtered.length === 0) {
      list.appendChild(el('p', { class: 'signals-empty-hint' }, [
        'Không có signal nào ≥ Min score. Giảm thanh trượt hoặc scan lại.',
      ]));
      return;
    }

    for (const signal of filtered.slice(0, 100)) {
      list.appendChild(this.#renderSignalCard(signal));
    }

    if (filtered.length > 100) {
      list.appendChild(el('p', { class: 'signals-more' }, [
        `Hiển thị 100 / ${filtered.length} signal`,
      ]));
    }
  }

  /**
   * @param {import('../scoring/ScoringEngine.js').ScoredSignalSet|null} set
   */
  #renderCalibrationPanel(set) {
    const root = this.#container?.querySelector('#signals-panel-calibration');
    if (!root) return;
    root.innerHTML = '';

    if (!set) {
      root.appendChild(this.#renderCalibrationEmpty(
        'Chưa có signal đã chấm.',
        ['Strategies (Ctrl+3) → Run scan', 'Simulation (Ctrl+4) cùng Symbol/TF', 'Quay lại tab này']
      ));
      return;
    }

    const sim = SimulationEngine.getLastResult();
    const report = ScoringEngine.getCalibrationReport(sim, Math.max(minScoreFilter, 65));
    const weights = ScoringEngine.getWeights();

    if (!report.matched) {
      root.appendChild(this.#renderCalibrationEmpty(
        report.reason ?? 'Chưa đối chiếu được.',
        [
          `Scan: ${strategyLabel(set.strategyId)} · ${set.symbol} ${set.timeframe}`,
          'Simulation (Ctrl+4) — chọn đúng Strategy / Symbol / TF',
          'Run Simulation rồi mở lại tab này',
        ]
      ));
      return;
    }

    const corr = report.scoreProfitCorrelation ?? 0;
    const corrTone = corr > 0.15 ? 'good' : corr < -0.05 ? 'bad' : '';

    root.appendChild(el('div', { class: 'signals-cal-layout' }, [
      el('p', { class: 'signals-cal-intro' }, [
        `${report.matchedTrades} lệnh khớp điểm AI`,
        report.skippedTrades ? ` (${report.skippedTrades} lệnh không ghép được)` : '',
        ` · Strategy ${strategyLabel(set.strategyId)} · ${set.symbol} ${set.timeframe}`,
      ]),
      el('div', { class: 'signals-stats-row' }, [
        statCard('Tương quan điểm–lãi', corr.toFixed(2), corrTone),
        statCard(`WR ≥ ${report.minScoreCutoffUsed}`, fmtPct(report.highScoreWinRate ?? 0), 'good'),
        statCard(`WR < ${report.minScoreCutoffUsed}`, fmtPct(report.lowScoreWinRate ?? 0)),
        statCard('Lệnh khớp', String(report.matchedTrades)),
      ]),
      this.#renderDetailsSection('Theo nhóm điểm', this.#renderBucketTable(report.buckets ?? [])),
      report.factors?.length
        ? this.#renderDetailsSection(
          'Yếu tố khác biệt (thắng vs thua)',
          this.#renderFactorTable(report.factors.slice(0, 6))
        )
        : null,
      this.#renderDetailsSection(
        'Trọng số chấm điểm',
        this.#renderWeightsBlock(weights)
      ),
    ].filter(Boolean)));
  }

  /**
   * @param {string} message
   * @param {string[]} steps
   * @returns {HTMLElement}
   */
  #renderCalibrationEmpty(message, steps) {
    return el('div', { class: 'signals-cal-empty-state' }, [
      el('p', { class: 'signals-cal-empty-title' }, [message]),
      el('ol', { class: 'signals-cal-steps' }, steps.map((s) => el('li', {}, [s]))),
    ]);
  }

  /**
   * @param {string} title
   * @param {HTMLElement} body
   * @returns {HTMLElement}
   */
  #renderDetailsSection(title, body) {
    const details = el('details', { class: 'signals-cal-details' }, [
      el('summary', { class: 'signals-cal-summary' }, [title]),
      el('div', { class: 'signals-cal-details-body' }, [body]),
    ]);
    details.open = title.startsWith('Theo nhóm');
    return details;
  }

  /**
   * @param {import('../scoring/ScoreCalibration.js').ScoreBucketSummary[]} buckets
   * @returns {HTMLElement}
   */
  #renderBucketTable(buckets) {
    return el('table', { class: 'signals-cal-table' }, [
      el('thead', {}, [
        el('tr', {}, [
          el('th', {}, ['Nhóm']),
          el('th', {}, ['Lệnh']),
          el('th', {}, ['WR']),
          el('th', {}, ['Lãi TB']),
          el('th', {}, ['Tổng']),
        ]),
      ]),
      el('tbody', {}, buckets.map((b) =>
        el('tr', {}, [
          el('td', {}, [b.label]),
          el('td', {}, [String(b.trades)]),
          el('td', {}, [b.trades ? fmtPct(b.winRate) : '—']),
          el('td', { class: 'signals-cal-mono' }, [b.trades ? `$${b.avgProfit.toFixed(2)}` : '—']),
          el('td', { class: 'signals-cal-mono' }, [b.trades ? `$${b.netProfit.toFixed(2)}` : '—']),
        ])
      )),
    ]);
  }

  /**
   * @param {import('../scoring/ScoreCalibration.js').FactorDiscrimination[]} factors
   * @returns {HTMLElement}
   */
  #renderFactorTable(factors) {
    return el('table', { class: 'signals-cal-table' }, [
      el('thead', {}, [
        el('tr', {}, [
          el('th', {}, ['Yếu tố']),
          el('th', {}, ['Thắng']),
          el('th', {}, ['Thua']),
          el('th', {}, ['Chênh']),
        ]),
      ]),
      el('tbody', {}, factors.map((f) =>
        el('tr', {}, [
          el('td', {}, [FACTOR_LABELS[f.factor] ?? f.factor]),
          el('td', { class: 'signals-cal-mono' }, [f.avgWin.toFixed(0)]),
          el('td', { class: 'signals-cal-mono' }, [f.avgLoss.toFixed(0)]),
          el('td', { class: `signals-cal-mono${f.delta >= 0 ? ' signals-cal-pos' : ' signals-cal-neg'}` }, [
            `${f.delta >= 0 ? '+' : ''}${f.delta.toFixed(1)}`,
          ]),
        ])
      )),
    ]);
  }

  /**
   * @param {Record<string, number>} weights
   * @returns {HTMLElement}
   */
  #renderWeightsBlock(weights) {
    const wrap = el('div', { class: 'signals-weights-block' }, [
      el('p', { class: 'signals-cal-note', id: 'sig-weight-note' }, [
        'Gợi ý trọng số dựa trên lệnh đã mô phỏng — cần ≥10 lệnh; kiểm tra lại trên period khác.',
      ]),
      el('table', { class: 'signals-cal-table' }, [
        el('thead', {}, [
          el('tr', {}, [
            el('th', {}, ['Yếu tố']),
            el('th', {}, ['Hiện tại']),
            el('th', {}, ['Gợi ý']),
          ]),
        ]),
        el('tbody', {}, Object.entries(weights).map(([key, value]) =>
          el('tr', {}, [
            el('td', {}, [FACTOR_LABELS[key] ?? key]),
            el('td', { class: 'signals-cal-mono' }, [`${(value * 100).toFixed(1)}%`]),
            el('td', { class: 'signals-cal-mono', id: `sig-weight-suggest-${key}` }, ['—']),
          ])
        )),
      ]),
      el('div', { class: 'signals-cal-actions' }, [
        el('button', { class: 'btn btn-sm btn-secondary', id: 'sig-suggest-weights', type: 'button' }, [
          'Gợi ý trọng số',
        ]),
        el('button', { class: 'btn btn-sm btn-primary', id: 'sig-apply-weights', type: 'button', disabled: true }, [
          'Áp dụng',
        ]),
        el('button', { class: 'btn btn-sm', id: 'sig-reset-weights', type: 'button' }, [
          'Mặc định',
        ]),
      ]),
    ]);

    wrap.querySelector('#sig-suggest-weights')?.addEventListener('click', () => {
      const sim = SimulationEngine.getLastResult();
      if (!sim) return;
      lastWeightSuggestion = ScoringEngine.suggestWeights(sim);
      this.#fillWeightSuggestion(lastWeightSuggestion);
      const applyBtn = /** @type {HTMLButtonElement} */ (wrap.querySelector('#sig-apply-weights'));
      if (applyBtn) applyBtn.disabled = false;
    });

    wrap.querySelector('#sig-apply-weights')?.addEventListener('click', async () => {
      if (!lastWeightSuggestion) return;
      await ScoringEngine.applyWeights(lastWeightSuggestion.weights);
      lastWeightSuggestion = null;
      this.#render(ScoringEngine.getLastScored());
    });

    wrap.querySelector('#sig-reset-weights')?.addEventListener('click', async () => {
      lastWeightSuggestion = null;
      await ScoringEngine.resetWeights();
      this.#render(ScoringEngine.getLastScored());
    });

    if (lastWeightSuggestion) {
      this.#fillWeightSuggestion(lastWeightSuggestion);
    }

    return wrap;
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

    const card = el('button', {
      type: 'button',
      class: 'signal-card signal-card-compact',
      title: 'Mở Chart tại nến signal',
    }, [
      el('div', { class: 'signal-card-row' }, [
        el('span', { class: `signal-grade grade-${grade}` }, [grade]),
        el('span', { class: 'signal-score' }, [`${score}`]),
        el('span', { class: `signal-dir signal-${signal.direction}` }, [signal.direction.toUpperCase()]),
        el('span', { class: 'signal-rr' }, [`${signal.rr.toFixed(1)}R`]),
        el('span', { class: 'signal-time' }, [formatTimestamp(jumpAt)]),
        el('span', { class: 'signal-open-hint' }, ['Chart →']),
      ]),
      el('p', { class: 'signal-reason signal-reason-compact' }, [
        signal.reason || '—',
        ` · E ${signal.entry.toFixed(5)} · SL ${signal.sl.toFixed(5)} · TP ${signal.tp.toFixed(5)}`,
      ]),
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
