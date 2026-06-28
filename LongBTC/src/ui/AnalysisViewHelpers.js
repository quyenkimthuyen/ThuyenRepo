/**
 * Shared helpers for BTC analysis views.
 * @module ui/AnalysisViewHelpers
 */

import { el } from '../utils/dom.js';
import { formatAnalysisDate, formatPct } from '../chart/AnalysisOverlay.js';
import { trendLabelVi } from '../analysis/TrendAnalyzer.js';
import { createHelpButton } from '../utils/contextHelp.js';

/**
 * @typedef {import('../analysis/LongTermAnalysisEngine.js').LongTermAnalysisResult} AnalysisResult
 */

/**
 * Render metric card grid.
 * @param {Array<{ label: string, value: string, hint?: string, color?: string }>} metrics
 * @returns {HTMLElement}
 */
export function renderMetricGrid(metrics) {
  return el('div', { class: 'analysis-metrics' }, metrics.map((m) =>
    el('div', { class: 'analysis-metric-card' }, [
      el('span', { class: 'analysis-metric-label' }, [m.label]),
      el('span', {
        class: 'analysis-metric-value',
        style: m.color ? `color:${m.color}` : undefined,
      }, [m.value]),
      m.hint ? el('span', { class: 'analysis-metric-hint' }, [m.hint]) : null,
    ].filter(Boolean))
  ));
}

/**
 * Render analysis summary header.
 * @param {string} title
 * @param {string} subtitle
 * @param {string} [helpSection]
 * @returns {HTMLElement}
 */
export function renderAnalysisHeader(title, subtitle, helpSection) {
  return el('div', { class: 'analysis-header' }, [
    el('div', { class: 'analysis-header-text' }, [
      el('h2', { class: 'view-title' }, [title]),
      el('p', { class: 'view-desc' }, [subtitle]),
    ]),
    helpSection ? createHelpButton(helpSection) : null,
  ].filter(Boolean));
}

/**
 * Render empty state when no analysis available.
 * @returns {HTMLElement}
 */
export function renderNoAnalysis() {
  return el('div', { class: 'analysis-empty' }, [
    el('p', {}, ['Ch?a có d? li?u phân tích.']),
    el('p', { class: 'analysis-empty-hint' }, [
      'M? bi?u ?? BTC (W ho?c D1) ?? t? ??ng ch?y phân tích, ho?c vào Data Manager t?i d? li?u BTCUSD.',
    ]),
  ]);
}

/**
 * Build dashboard metrics from analysis result.
 * @param {AnalysisResult} analysis
 * @returns {Array<{ label: string, value: string, hint?: string, color?: string }>}
 */
export function buildDashboardMetrics(analysis) {
  const { overallTrend, currentCycle, psychology, cycleExtremes: ext } = analysis;
  return [
    {
      label: 'Xu h??ng chính',
      value: trendLabelVi(overallTrend.direction),
      hint: overallTrend.reason,
      color: overallTrend.direction === 'uptrend' ? '#22c55e'
        : overallTrend.direction === 'downtrend' ? '#ef4444' : '#94a3b8',
    },
    {
      label: 'Chu k? 4 n?m',
      value: currentCycle.phaseLabel,
      hint: `${currentCycle.progressPct.toFixed(1)}% · ${currentCycle.halvingLabel}`,
      color: currentCycle.phaseColor,
    },
    {
      label: 'Sóng Elliott',
      value: analysis.elliott.waves.length > 0
        ? `Sóng ${analysis.elliott.waves[analysis.elliott.waves.length - 1].waveNumber}`
        : '—',
      hint: analysis.elliott.summary,
    },
    {
      label: 'Tâm lý th? tr??ng',
      value: psychology.labelVi,
      hint: `${psychology.confidence}% tin c?y`,
      color: psychology.color,
    },
    {
      label: '??nh chu k? hi?n t?i',
      value: ext.cycleHigh != null ? `$${ext.cycleHigh.toLocaleString('en-US', { maximumFractionDigits: 0 })}` : '—',
      hint: ext.drawdownFromHighPct != null ? `Drawdown: ${formatPct(ext.drawdownFromHighPct)}` : undefined,
    },
    {
      label: '?áy chu k? hi?n t?i',
      value: ext.cycleLow != null ? `$${ext.cycleLow.toLocaleString('en-US', { maximumFractionDigits: 0 })}` : '—',
      hint: `Còn ~${currentCycle.daysToNextHalving} ngày ??n halving`,
    },
  ];
}

/**
 * Render data table.
 * @param {string[]} headers
 * @param {string[][]} rows
 * @returns {HTMLElement}
 */
export function renderTable(headers, rows) {
  const thead = el('thead', {}, [
    el('tr', {}, headers.map((h) => el('th', {}, [h]))),
  ]);
  const tbody = el('tbody', {}, rows.map((row) =>
    el('tr', {}, row.map((cell) => el('td', {}, [cell])))
  ));
  return el('div', { class: 'analysis-table-wrap' }, [
    el('table', { class: 'analysis-table' }, [thead, tbody]),
  ]);
}

export { formatAnalysisDate, formatPct };
