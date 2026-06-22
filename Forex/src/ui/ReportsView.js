/**
 * Reports view — dashboard, heatmaps, and export tools.
 * @module ui/ReportsView
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import ReportEngine from '../report/ReportEngine.js';
import { HEATMAP_DIMENSIONS } from '../analytics/HeatmapCalculator.js';
import {
  downloadTradesCSV,
  downloadReportJSON,
  downloadCanvasPNG,
  openPrintReport,
} from '../report/ReportExporter.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('ReportsView');

/** @type {'dashboard'|'heatmaps'|'export'} */
let activeTab = 'dashboard';

/** @type {string} */
let activeDimension = 'month';

/**
 * Reports view controller.
 */
class ReportsViewImpl {
  /** @type {HTMLElement|null} */
  #container = null;

  /**
   * @param {HTMLElement} container
   */
  async mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.remove('panel-body-fill');

    container.appendChild(el('div', { class: 'reports-view' }, [
      el('div', { class: 'reports-toolbar' }, [
        el('span', { class: 'reports-title' }, ['Research Dashboard & Reports']),
        el('div', { class: 'reports-toolbar-actions' }, [
          el('button', { class: 'btn btn-sm', id: 'reports-refresh' }, ['Refresh']),
        ]),
      ]),
      el('div', { class: 'reports-tabs', id: 'reports-tabs' }, [
        el('button', { class: 'reports-tab active', dataset: { tab: 'dashboard' } }, ['Dashboard']),
        el('button', { class: 'reports-tab', dataset: { tab: 'heatmaps' } }, ['Heatmaps']),
        el('button', { class: 'reports-tab', dataset: { tab: 'export' } }, ['Export']),
      ]),
      el('div', { class: 'reports-meta', id: 'reports-meta' }, ['No data — run a simulation first.']),
      el('div', { class: 'reports-content', id: 'reports-content' }),
    ]));

    this.#bindEvents();
    this.#render(ReportEngine.getLastReport());
    log.info('Reports view mounted');
  }

  unmount() {
    if (this.#container) {
      this.#container.innerHTML = '';
      this.#container.classList.add('panel-body-fill');
    }
  }

  #bindEvents() {
    this.#container?.querySelector('#reports-refresh')?.addEventListener('click', () => {
      const report = ReportEngine.refreshFromSimulation();
      if (!report?.stats?.totalTrades) {
        bus.emit(Events.LOG_MESSAGE, {
          message: 'No simulation results — run Simulation first',
          level: 'warn',
          time: new Date(),
        });
      }
      this.#render(report ?? ReportEngine.getLastReport());
    });

    this.#container?.querySelector('#reports-tabs')?.addEventListener('click', (e) => {
      const btn = /** @type {HTMLElement} */ (e.target).closest('.reports-tab');
      if (!btn?.dataset.tab) return;
      activeTab = /** @type {'dashboard'|'heatmaps'|'export'} */ (btn.dataset.tab);
      this.#container?.querySelectorAll('.reports-tab').forEach((tab) => {
        tab.classList.toggle('active', tab.dataset.tab === activeTab);
      });
      this.#render(ReportEngine.getLastReport());
    });

    bus.on(Events.REPORT_GENERATED, (report) => this.#render(report));
    bus.on(Events.STATISTICS_COMPUTED, () => {
      setTimeout(() => this.#render(ReportEngine.getLastReport()), 50);
    });
  }

  /**
   * @param {import('../report/ReportEngine.js').ResearchReport|null} report
   */
  #render(report) {
    const meta = this.#container?.querySelector('#reports-meta');
    const content = this.#container?.querySelector('#reports-content');

    if (!report || report.stats.totalTrades === 0) {
      if (meta) meta.textContent = 'No trades — run Simulation (Ctrl+4) first.';
      if (content) content.innerHTML = '<p class="reports-empty">Run a backtest to generate dashboard and heatmaps.</p>';
      return;
    }

    if (meta) {
      meta.textContent = `${report.strategyId} · ${report.symbol} ${report.timeframe} · ${report.stats.totalTrades} trades · Report ${new Date(report.generatedAt).toLocaleString()}`;
    }

    if (!content) return;
    content.innerHTML = '';

    if (activeTab === 'dashboard') this.#renderDashboard(content, report);
    else if (activeTab === 'heatmaps') this.#renderHeatmaps(content, report);
    else this.#renderExport(content, report);
  }

  /**
   * @param {HTMLElement} content
   * @param {import('../report/ReportEngine.js').ResearchReport} report
   */
  #renderDashboard(content, report) {
    const cards = el('div', { class: 'dashboard-cards' });
    for (const card of report.dashboard) {
      cards.appendChild(el('div', { class: `dashboard-card tone-${card.tone}` }, [
        el('span', { class: 'dashboard-card-label' }, [card.label]),
        el('span', { class: 'dashboard-card-value' }, [card.value]),
        card.hint ? el('span', { class: 'dashboard-card-hint' }, [card.hint]) : null,
      ].filter(Boolean)));
    }

    const chartPanel = el('div', { class: 'reports-chart-panel' }, [
      el('h4', { class: 'reports-section-title' }, ['Equity Curve']),
      el('canvas', { class: 'reports-canvas', id: 'report-equity-canvas', width: '800', height: '180' }),
    ]);

    content.append(cards, chartPanel);
    requestAnimationFrame(() => this.#drawEquityCurve(report.stats.equityCurve));
  }

  /**
   * @param {HTMLElement} content
   * @param {import('../report/ReportEngine.js').ResearchReport} report
   */
  #renderHeatmaps(content, report) {
    const dimBar = el('div', { class: 'heatmap-dimensions' });
    for (const dim of HEATMAP_DIMENSIONS) {
      const btn = el('button', {
        class: `btn btn-sm heatmap-dim-btn${dim.id === activeDimension ? ' active' : ''}`,
        dataset: { dim: dim.id },
      }, [dim.label]);
      btn.addEventListener('click', () => {
        activeDimension = dim.id;
        this.#renderHeatmaps(content, report);
      });
      dimBar.appendChild(btn);
    }

    const heatmap = report.heatmaps[activeDimension];
    const grid = el('div', { class: 'heatmap-grid' });
    const profits = heatmap.cells.map((c) => c.netProfit);
    const maxP = Math.max(...profits, 0);
    const minP = Math.min(...profits, 0);

    for (const cell of heatmap.cells) {
      const bg = this.#profitColor(cell.netProfit, minP, maxP);
      grid.appendChild(el('div', {
        class: 'heatmap-cell',
        style: `background:${bg}`,
        title: `${cell.label}: $${cell.netProfit.toFixed(2)}`,
      }, [
        el('span', { class: 'heatmap-cell-label' }, [cell.label]),
        el('span', { class: 'heatmap-cell-profit' }, [`$${cell.netProfit.toFixed(0)}`]),
        el('span', { class: 'heatmap-cell-meta' }, [`${cell.trades} trades · ${cell.winRate.toFixed(0)}% WR`]),
      ]));
    }

    if (heatmap.cells.length === 0) {
      grid.appendChild(el('p', { class: 'reports-empty' }, ['No data for this dimension.']));
    }

    content.append(dimBar, grid);
  }

  /**
   * @param {HTMLElement} content
   * @param {import('../report/ReportEngine.js').ResearchReport} report
   */
  #renderExport(content, report) {
    const panel = el('div', { class: 'export-panel' }, [
      el('h4', { class: 'reports-section-title' }, ['Export Results']),
      el('p', { class: 'export-desc' }, ['Download or print your research report. All exports are generated locally in the browser.']),
      el('div', { class: 'export-actions' }, [
        el('button', { class: 'btn', id: 'export-csv' }, ['Export Trades CSV']),
        el('button', { class: 'btn', id: 'export-json' }, ['Export Report JSON']),
        el('button', { class: 'btn', id: 'export-png' }, ['Export Dashboard PNG']),
        el('button', { class: 'btn btn-primary', id: 'export-pdf' }, ['Print / Save PDF']),
      ]),
    ]);

    content.appendChild(panel);

    content.querySelector('#export-csv')?.addEventListener('click', () => {
      downloadTradesCSV(report.trades, `${report.strategyId}_trades.csv`);
    });
    content.querySelector('#export-json')?.addEventListener('click', () => {
      downloadReportJSON(report, `${report.strategyId}_report.json`);
    });
    content.querySelector('#export-png')?.addEventListener('click', () => {
      const canvas = this.#buildExportCanvas(report);
      downloadCanvasPNG(canvas, `${report.strategyId}_dashboard.png`);
    });
    content.querySelector('#export-pdf')?.addEventListener('click', () => {
      openPrintReport(report);
    });
  }

  /**
   * @param {import('../report/ReportEngine.js').ResearchReport} report
   * @returns {HTMLCanvasElement}
   */
  #buildExportCanvas(report) {
    const canvas = document.createElement('canvas');
    canvas.width = 800;
    canvas.height = 400;
    const ctx = canvas.getContext('2d');
    if (!ctx) return canvas;

    ctx.fillStyle = '#1a2332';
    ctx.fillRect(0, 0, 800, 400);
    ctx.fillStyle = '#e8edf4';
    ctx.font = 'bold 16px Inter, sans-serif';
    ctx.fillText(`PARL — ${report.strategyId} · ${report.symbol}`, 20, 30);
    ctx.font = '13px Inter, sans-serif';
    ctx.fillStyle = '#8b9cb3';
    ctx.fillText(`Net: $${report.stats.netProfit.toFixed(2)} · WR: ${report.stats.winRate.toFixed(1)}% · PF: ${report.stats.profitFactor.toFixed(2)}`, 20, 55);

    const curve = report.stats.equityCurve;
    if (curve.length >= 2) {
      const balances = curve.map((p) => p.balance);
      const min = Math.min(...balances);
      const max = Math.max(...balances);
      const range = max - min || 1;
      ctx.strokeStyle = '#22c55e';
      ctx.lineWidth = 2;
      ctx.beginPath();
      curve.forEach((point, i) => {
        const x = 20 + (i / (curve.length - 1)) * 760;
        const y = 380 - ((point.balance - min) / range) * 300;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    }

    return canvas;
  }

  /**
   * @param {import('../statistics/EquityCurve.js').EquityPoint[]} curve
   */
  #drawEquityCurve(curve) {
    const canvas = /** @type {HTMLCanvasElement} */ (this.#container?.querySelector('#report-equity-canvas'));
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
   * @param {number} value
   * @param {number} min
   * @param {number} max
   * @returns {string}
   */
  #profitColor(value, min, max) {
    if (value > 0) {
      const intensity = max > 0 ? value / max : 0;
      return `rgba(34, 197, 94, ${0.25 + intensity * 0.65})`;
    }
    if (value < 0) {
      const intensity = min < 0 ? value / min : 0;
      return `rgba(239, 68, 68, ${0.25 + intensity * 0.65})`;
    }
    return 'rgba(90, 106, 130, 0.3)';
  }
}

export const ReportsView = new ReportsViewImpl();
