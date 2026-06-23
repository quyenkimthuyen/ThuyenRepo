/**
 * Statistics dashboard — performance metrics and equity curve.
 * @module ui/StatisticsView
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import StatisticsEngine from '../statistics/StatisticsEngine.js';
import SimulationEngine from '../simulation/SimulationEngine.js';
import { downloadFile } from '../data/DataExporter.js';
import { createHelpButton } from '../utils/contextHelp.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('StatisticsView');

/** @type {Array<{ key: string, label: string, format: (v: number) => string }>} */
const METRIC_GROUPS = [
  { key: 'totalTrades', label: 'Total Trades', format: (v) => String(v) },
  { key: 'wins', label: 'Wins', format: (v) => String(v) },
  { key: 'losses', label: 'Losses', format: (v) => String(v) },
  { key: 'winRate', label: 'Win Rate', format: (v) => `${v.toFixed(1)}%` },
  { key: 'averageWin', label: 'Avg Win', format: (v) => `$${v.toFixed(2)}` },
  { key: 'averageLoss', label: 'Avg Loss', format: (v) => `$${v.toFixed(2)}` },
  { key: 'expectancy', label: 'Expectancy', format: (v) => `$${v.toFixed(2)}` },
  { key: 'expectancyR', label: 'Expectancy (R)', format: (v) => `${v.toFixed(2)}R` },
  { key: 'profitFactor', label: 'Profit Factor', format: (v) => v === Infinity ? '∞' : v.toFixed(2) },
  { key: 'netProfit', label: 'Net Profit', format: (v) => `$${v.toFixed(2)}` },
  { key: 'grossProfit', label: 'Gross Profit', format: (v) => `$${v.toFixed(2)}` },
  { key: 'grossLoss', label: 'Gross Loss', format: (v) => `$${v.toFixed(2)}` },
  { key: 'maxDrawdown', label: 'Max Drawdown', format: (v) => `$${v.toFixed(2)}` },
  { key: 'maxDrawdownPercent', label: 'Max DD %', format: (v) => `${v.toFixed(1)}%` },
  { key: 'recoveryFactor', label: 'Recovery Factor', format: (v) => v === Infinity ? '∞' : v.toFixed(2) },
  { key: 'sharpeRatio', label: 'Sharpe Ratio', format: (v) => v.toFixed(2) },
  { key: 'longestWinStreak', label: 'Best Win Streak', format: (v) => String(v) },
  { key: 'longestLoseStreak', label: 'Worst Lose Streak', format: (v) => String(v) },
  { key: 'averageTradeDuration', label: 'Avg Duration', format: (v) => `${v.toFixed(1)} bars` },
  { key: 'averageRR', label: 'Avg RR', format: (v) => v.toFixed(2) },
  { key: 'averageSLPips', label: 'Avg SL', format: (v) => `${v.toFixed(1)} pips` },
  { key: 'averageTPPips', label: 'Avg TP', format: (v) => `${v.toFixed(1)} pips` },
];

/**
 * Statistics view controller.
 */
class StatisticsViewImpl {
  /** @type {HTMLElement|null} */
  #container = null;

  /**
   * @param {HTMLElement} container
   */
  async mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.remove('panel-body-fill');

    container.appendChild(el('div', { class: 'statistics-view' }, [
      el('div', { class: 'stats-toolbar' }, [
        el('span', { class: 'stats-title' }, ['Performance Statistics']),
        el('div', { class: 'stats-toolbar-actions' }, [
          el('button', { class: 'btn btn-sm', id: 'stats-refresh' }, ['Refresh']),
          el('button', { class: 'btn btn-sm', id: 'stats-export' }, ['Export JSON']),
          createHelpButton('statistics'),
        ]),
      ]),
      el('div', { class: 'stats-meta', id: 'stats-meta' }, ['No data — run a simulation first.']),
      el('div', { class: 'stats-charts' }, [
        el('div', { class: 'stats-chart-panel' }, [
          el('h4', { class: 'stats-section-title' }, ['Equity Curve']),
          el('canvas', { class: 'stats-canvas', id: 'equity-canvas', width: '800', height: '200' }),
        ]),
        el('div', { class: 'stats-chart-panel' }, [
          el('h4', { class: 'stats-section-title' }, ['Drawdown']),
          el('canvas', { class: 'stats-canvas', id: 'drawdown-canvas', width: '800', height: '120' }),
        ]),
      ]),
      el('div', { class: 'stats-grid', id: 'stats-grid' }),
    ]));

    this.#bindEvents();
    this.#render(StatisticsEngine.getLastReport());
    log.info('Statistics view mounted');
  }

  unmount() {
    if (this.#container) {
      this.#container.innerHTML = '';
      this.#container.classList.add('panel-body-fill');
    }
  }

  #bindEvents() {
    this.#container?.querySelector('#stats-refresh')?.addEventListener('click', () => {
      const report = StatisticsEngine.refreshFromSimulation();
      if (!report) {
        bus.emit(Events.LOG_MESSAGE, {
          message: 'No simulation results — run Simulation first',
          level: 'warn',
          time: new Date(),
        });
      }
      this.#render(report ?? StatisticsEngine.getLastReport());
    });

    this.#container?.querySelector('#stats-export')?.addEventListener('click', () => {
      const report = StatisticsEngine.getLastReport();
      if (!report) return;
      downloadFile(JSON.stringify(report, null, 2), 'statistics_report.json', 'application/json');
    });

    bus.on(Events.STATISTICS_COMPUTED, (report) => this.#render(report));
    bus.on(Events.SIMULATION_COMPLETE, () => {
      setTimeout(() => this.#render(StatisticsEngine.getLastReport()), 50);
    });
  }

  /**
   * @param {import('../statistics/StatisticsEngine.js').StatisticsReport|null} report
   */
  #render(report) {
    const meta = this.#container?.querySelector('#stats-meta');
    const grid = this.#container?.querySelector('#stats-grid');

    if (!report || report.stats.totalTrades === 0) {
      if (meta) meta.textContent = 'No trades — run Simulation (Ctrl+4) first.';
      if (grid) grid.innerHTML = '';
      this.#clearCharts();
      return;
    }

    const { stats, strategyId, symbol, timeframe } = report;
    if (meta) {
      meta.textContent = `${strategyId} · ${symbol} ${timeframe} · ${stats.totalTrades} trades · Balance $${stats.finalBalance.toFixed(2)}`;
    }

    if (grid) {
      grid.innerHTML = '';
      for (const m of METRIC_GROUPS) {
        const value = stats[m.key];
        const formatted = m.format(/** @type {number} */ (value));
        const isPositive = ['netProfit', 'expectancy', 'grossProfit'].includes(m.key);
        const isNegative = ['grossLoss', 'maxDrawdown', 'averageLoss'].includes(m.key);
        let cls = '';
        if (isPositive && value > 0) cls = ' stats-positive';
        if (isNegative && value > 0) cls = ' stats-negative';

        grid.appendChild(el('div', { class: `stats-metric${cls}` }, [
          el('span', { class: 'stats-metric-label' }, [m.label]),
          el('span', { class: 'stats-metric-value' }, [formatted]),
        ]));
      }
    }

    this.#drawEquityCurve(stats.equityCurve);
    this.#drawDrawdown(stats.equityCurve);
  }

  /**
   * @param {import('../statistics/EquityCurve.js').EquityPoint[]} curve
   */
  #drawEquityCurve(curve) {
    const canvas = /** @type {HTMLCanvasElement} */ (this.#container?.querySelector('#equity-canvas'));
    if (!canvas || curve.length < 2) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const balances = curve.map((p) => p.balance);
    const min = Math.min(...balances);
    const max = Math.max(...balances);
    const range = max - min || 1;

    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = '#2a3548';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, h - 1);
    ctx.lineTo(w, h - 1);
    ctx.stroke();

    ctx.strokeStyle = '#22c55e';
    ctx.lineWidth = 2;
    ctx.beginPath();

    curve.forEach((point, i) => {
      const x = (i / (curve.length - 1)) * w;
      const y = h - ((point.balance - min) / range) * (h - 10) - 5;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  /**
   * @param {import('../statistics/EquityCurve.js').EquityPoint[]} curve
   */
  #drawDrawdown(curve) {
    const canvas = /** @type {HTMLCanvasElement} */ (this.#container?.querySelector('#drawdown-canvas'));
    if (!canvas || curve.length < 2) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const maxDd = Math.max(...curve.map((p) => p.drawdown), 0.01);

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = 'rgba(239, 68, 68, 0.4)';
    ctx.beginPath();
    ctx.moveTo(0, 0);

    curve.forEach((point, i) => {
      const x = (i / (curve.length - 1)) * w;
      const barH = (point.drawdown / maxDd) * (h - 4);
      ctx.lineTo(x, barH);
    });

    ctx.lineTo(w, 0);
    ctx.closePath();
    ctx.fill();
  }

  #clearCharts() {
    for (const id of ['equity-canvas', 'drawdown-canvas']) {
      const canvas = /** @type {HTMLCanvasElement} */ (this.#container?.querySelector(`#${id}`));
      const ctx = canvas?.getContext('2d');
      if (ctx && canvas) ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  }
}

export const StatisticsView = new StatisticsViewImpl();
