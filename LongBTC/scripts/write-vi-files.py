from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def w(rel, s):
    text = s.encode("utf-8").decode("unicode_escape")
    (ROOT / rel).write_text(text, encoding="utf-8")
    print(rel, "OK" if "\ufffd" not in text and "??" not in text else "CHECK")


w(
    "src/ui/AnalysisViewHelpers.js",
    r"""
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
    el('p', {}, ['Ch\u01b0a c\u00f3 d\u1eef li\u1ec7u ph\u00e2n t\u00edch.']),
    el('p', { class: 'analysis-empty-hint' }, [
      'M\u1edf bi\u1ec3u \u0111\u1ed3 BTC (W ho\u1eb7c D1) \u0111\u1ec3 t\u1ef1 \u0111\u1ed9ng ch\u1ea1y ph\u00e2n t\u00edch, ho\u1eb7c v\u00e0o Data Manager t\u1ea3i d\u1eef li\u1ec7u BTCUSD.',
    ]),
  ]);
}

export function buildDashboardMetrics(analysis) {
  const { overallTrend, currentCycle, psychology, cycleExtremes: ext } = analysis;
  return [
    {
      label: 'Xu h\u01b0\u1edbng ch\u00ednh',
      value: trendLabelVi(overallTrend.direction),
      hint: overallTrend.reason,
      color: overallTrend.direction === 'uptrend' ? '#22c55e'
        : overallTrend.direction === 'downtrend' ? '#ef4444' : '#94a3b8',
    },
    {
      label: 'Chu k\u1ef3 4 n\u0103m',
      value: currentCycle.phaseLabel,
      hint: `${currentCycle.progressPct.toFixed(1)}% \u00b7 ${currentCycle.halvingLabel}`,
      color: currentCycle.phaseColor,
    },
    {
      label: 'S\u00f3ng Elliott',
      value: analysis.elliott.waves.length > 0
        ? `S\u00f3ng ${analysis.elliott.waves[analysis.elliott.waves.length - 1].waveNumber}`
        : '\u2014',
      hint: analysis.elliott.summary,
    },
    {
      label: 'T\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng',
      value: psychology.labelVi,
      hint: `${psychology.confidence}% tin c\u1eady`,
      color: psychology.color,
    },
    {
      label: '\u0110\u1ec9nh chu k\u1ef3 hi\u1ec7n t\u1ea1i',
      value: ext.cycleHigh != null ? `$${ext.cycleHigh.toLocaleString('en-US', { maximumFractionDigits: 0 })}` : '\u2014',
      hint: ext.drawdownFromHighPct != null ? `Drawdown: ${formatPct(ext.drawdownFromHighPct)}` : undefined,
    },
    {
      label: '\u0110\u00e1y chu k\u1ef3 hi\u1ec7n t\u1ea1i',
      value: ext.cycleLow != null ? `$${ext.cycleLow.toLocaleString('en-US', { maximumFractionDigits: 0 })}` : '\u2014',
      hint: `C\u00f2n ~${currentCycle.daysToNextHalving} ng\u00e0y \u0111\u1ebfn halving`,
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
""",
)
