
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

export function renderAnalysisHeader(title, subtitle, helpSection) {
  return el('div', { class: 'analysis-header' }, [
    el('div', { class: 'analysis-header-text' }, [
      el('h2', { class: 'view-title' }, [title]),
      el('p', { class: 'view-desc' }, [subtitle]),
    ]),
    helpSection ? createHelpButton(helpSection) : null,
  ].filter(Boolean));
}

export function renderNoAnalysis() {
  return el('div', { class: 'analysis-empty' }, [
    el('p', {}, ['Chưa có dữ liệu phân tích.']),
    el('p', { class: 'analysis-empty-hint' }, [
      'Mở biểu đồ BTC (W hoặc D1) để tự động chạy phân tích, hoặc vào Data Manager tải dữ liệu BTCUSD.',
    ]),
  ]);
}

export function buildDashboardMetrics(analysis) {
  const { overallTrend, currentCycle, psychology, cycleExtremes: ext } = analysis;
  return [
    {
      label: 'Xu hướng chính',
      value: trendLabelVi(overallTrend.direction),
      hint: overallTrend.reason,
      color: overallTrend.direction === 'uptrend' ? '#22c55e'
        : overallTrend.direction === 'downtrend' ? '#ef4444' : '#94a3b8',
    },
    {
      label: 'Chu kỳ 4 năm',
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
      label: 'Tâm lý thị trường',
      value: psychology.labelVi,
      hint: `${psychology.confidence}% tin cậy`,
      color: psychology.color,
    },
    {
      label: 'Đỉnh chu kỳ hiện tại',
      value: ext.cycleHigh != null ? `$${ext.cycleHigh.toLocaleString('en-US', { maximumFractionDigits: 0 })}` : '—',
      hint: ext.drawdownFromHighPct != null ? `Drawdown: ${formatPct(ext.drawdownFromHighPct)}` : undefined,
    },
    {
      label: 'Đáy chu kỳ hiện tại',
      value: ext.cycleLow != null ? `$${ext.cycleLow.toLocaleString('en-US', { maximumFractionDigits: 0 })}` : '—',
      hint: `Còn ~${currentCycle.daysToNextHalving} ngày đến halving`,
    },
  ];
}

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
