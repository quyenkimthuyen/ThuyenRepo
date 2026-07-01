/**
 * DCA backtest comparison panel (blind vs phase-aware).
 * @module ui/DcaBacktestPanel
 */

import { el } from '../utils/dom.js';
import { runDcaBacktest } from '../analysis/DcaBacktestEngine.js';
import { loadDcaPlan } from '../analysis/DcaPlanEngine.js';
import { formatAnalysisDate } from './AnalysisViewHelpers.js';

/**
 * @param {import('../data/Candle.js').Candle[]} candles
 * @param {number} [monthlyBudgetUsd]
 * @returns {HTMLElement}
 */
export function renderDcaBacktestPanel(candles, monthlyBudgetUsd = loadDcaPlan().monthlyBudgetUsd) {
  const root = el('div', { class: 'dca-backtest-panel' });
  const report = runDcaBacktest(candles, { monthlyBudgetUsd });

  root.appendChild(el('h3', { class: 'dca-backtest-title' }, [
    'So s\u00e1nh DCA: m\u00f9 vs theo giai \u0111o\u1ea1n t\u00e2m l\u00fd',
  ]));
  root.appendChild(el('p', { class: 'dca-backtest-sub' }, [
    `M\u1ed7i th\u00e1ng $${monthlyBudgetUsd.toLocaleString()} (c\u01a1 s\u1edf) \u00b7 t\u1eeb 2016 \u00b7 khung W \u00b7 nghi\u00ean c\u1ee9u, kh\u00f4ng ph\u1ea3i l\u1eddi khuy\u00ean.`,
  ]));

  if (!report.ok) {
    root.appendChild(el('p', { class: 'dca-backtest-empty' }, [report.reason ?? 'Kh\u00f4ng \u0111\u1ee7 d\u1eef li\u1ec7u.']));
    return root;
  }

  const { blind, phase } = report;
  const winnerLabel = report.winner === 'phase'
    ? 'DCA theo phase t\u1ed1t h\u01a1n tr\u00ean l\u1ecbch s\u1eed'
    : report.winner === 'blind'
      ? 'DCA m\u00f9 t\u1ed1t h\u01a1n tr\u00ean l\u1ecbch s\u1eed'
      : 'Hai chi\u1ebfn l\u01b0\u1ee3c t\u01b0\u01a1ng \u0111\u01b0\u01a1ng';

  root.appendChild(el('div', { class: `dca-backtest-verdict dca-backtest-verdict--${report.winner}` }, [
    el('span', { class: 'dca-backtest-verdict-label' }, [winnerLabel]),
    el('span', { class: 'dca-backtest-verdict-edge' }, [
      `Ch\u00eanh l\u1ec7ch: ${report.edgeUsd >= 0 ? '+' : ''}$${Math.round(report.edgeUsd).toLocaleString()} (${report.edgeReturnPct >= 0 ? '+' : ''}${report.edgeReturnPct.toFixed(1)}% l\u1ee3i nhu\u1eadn)`,
    ]),
  ]));

  root.appendChild(renderCompareTable(blind, phase));
  root.appendChild(renderEquityChart(blind.curve, phase.curve));
  root.appendChild(el('p', { class: 'dca-backtest-meta' }, [
    `${report.monthCount} th\u00e1ng \u00b7 ${formatAnalysisDate(report.startMs)} \u2192 ${formatAnalysisDate(report.endMs)}`,
  ]));

  return root;
}

/**
 * @param {import('../analysis/DcaBacktestEngine.js').DcaBacktestResult} blind
 * @param {import('../analysis/DcaBacktestEngine.js').DcaBacktestResult} phase
 */
function renderCompareTable(blind, phase) {
  const rows = [
    ['T\u1ed5ng \u0111\u1ea7u t\u01b0', fmtUsd(blind.totalInvested), fmtUsd(phase.totalInvested)],
    ['BTC t\u00edch l\u0169y', blind.btcHeld.toFixed(4), phase.btcHeld.toFixed(4)],
    ['Gi\u00e1 v\u1ed1n TB', fmtUsd(blind.avgCostUsd), fmtUsd(phase.avgCostUsd)],
    ['Gi\u00e1 tr\u1ecb cu\u1ed1i', fmtUsd(blind.finalValueUsd), fmtUsd(phase.finalValueUsd)],
    ['L\u1ee3i nhu\u1eadn', fmtPct(blind.returnPct), fmtPct(phase.returnPct)],
    ['Max drawdown', fmtPct(blind.maxDrawdownPct), fmtPct(phase.maxDrawdownPct)],
    ['S\u1ed1 l\u1ea7n mua', String(blind.buyCount), String(phase.buyCount)],
  ];

  const table = el('table', { class: 'dca-backtest-table' });
  table.appendChild(el('thead', {}, [
    el('tr', {}, [
      el('th', {}, ['Ch\u1ec9 s\u1ed1']),
      el('th', {}, ['DCA m\u00f9']),
      el('th', {}, ['DCA theo phase']),
    ]),
  ]));
  const tbody = el('tbody');
  for (const [label, a, b] of rows) {
    tbody.appendChild(el('tr', {}, [
      el('td', {}, [label]),
      el('td', { class: 'dca-backtest-num' }, [a]),
      el('td', { class: 'dca-backtest-num' }, [b]),
    ]));
  }
  table.appendChild(tbody);
  return table;
}

/**
 * @param {import('../analysis/DcaBacktestEngine.js').DcaBacktestPoint[]} blindCurve
 * @param {import('../analysis/DcaBacktestEngine.js').DcaBacktestPoint[]} phaseCurve
 */
function renderEquityChart(blindCurve, phaseCurve) {
  const w = 560;
  const h = 160;
  const pad = { l: 8, r: 8, t: 12, b: 24 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;

  const allVals = [
    ...blindCurve.map((p) => p.portfolioValue),
    ...phaseCurve.map((p) => p.portfolioValue),
  ];
  const minV = Math.min(...allVals);
  const maxV = Math.max(...allVals);
  const span = maxV - minV || 1;

  const toPath = (curve) => {
    if (curve.length < 2) return '';
    return curve.map((p, i) => {
      const x = pad.l + (i / (curve.length - 1)) * innerW;
      const y = pad.t + innerH - ((p.portfolioValue - minV) / span) * innerH;
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
  };

  const wrap = el('div', { class: 'dca-backtest-chart-wrap' });
  wrap.appendChild(el('div', { class: 'dca-backtest-chart-legend' }, [
    el('span', {}, [el('span', { class: 'dca-backtest-line dca-backtest-line--blind' }), 'DCA m\u00f9']),
    el('span', {}, [el('span', { class: 'dca-backtest-line dca-backtest-line--phase' }), 'DCA theo phase']),
  ]));

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  svg.setAttribute('class', 'dca-backtest-chart');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'Equity curve DCA m\u00f9 vs theo phase');

  const blindPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  blindPath.setAttribute('d', toPath(blindCurve));
  blindPath.setAttribute('fill', 'none');
  blindPath.setAttribute('stroke', '#94a3b8');
  blindPath.setAttribute('stroke-width', '2');

  const phasePath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  phasePath.setAttribute('d', toPath(phaseCurve));
  phasePath.setAttribute('fill', 'none');
  phasePath.setAttribute('stroke', '#3b82f6');
  phasePath.setAttribute('stroke-width', '2');

  svg.appendChild(blindPath);
  svg.appendChild(phasePath);
  wrap.appendChild(svg);
  return wrap;
}

/**
 * @param {number} n
 */
function fmtUsd(n) {
  return `$${Math.round(n).toLocaleString('en-US')}`;
}

/**
 * @param {number} n
 */
function fmtPct(n) {
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`;
}
