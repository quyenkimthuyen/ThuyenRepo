/**
 * Long-term BTC chart context bar and overlay presets.
 * @module ui/ChartResearchUi
 */

import { el } from '../utils/dom.js';
import { formatTimestamp } from '../data/TimeframeUtils.js';
import { psychologyBandAtTime } from '../analysis/PsychologyBands.js';

/**
 * @typedef {import('../analysis/LongTermAnalysisEngine.js').LongTermAnalysisResult} AnalysisResult
 * @typedef {import('../data/Candle.js').Candle} Candle
 * @typedef {{ swings: boolean, trends: boolean, cycle: boolean, elliott: boolean, halving: boolean, psychology: boolean, psychologyBg: boolean }} OverlayToggles
 */

/** @type {Record<string, OverlayToggles>} */
export const CHART_OVERLAY_PRESETS = {
  clean: {
    swings: false, trends: false, cycle: true, elliott: false, halving: true,
    psychology: true, psychologyBg: true,
  },
  trend: {
    swings: false, trends: true, cycle: true, elliott: false, halving: true,
    psychology: true, psychologyBg: true,
  },
  full: {
    swings: true, trends: true, cycle: true, elliott: true, halving: true,
    psychology: true, psychologyBg: true,
  },
};

const TREND_VI = {
  uptrend: 'T\u0103ng',
  downtrend: 'Gi\u1ea3m',
  sideways: 'Ngang',
};

/**
 * @param {HTMLElement} parent
 * @returns {HTMLElement}
 */
export function mountChartContextBar(parent) {
  const bar = el('div', {
    class: 'chart-context-bar',
    id: 'chart-context-bar',
    hidden: true,
  });
  const container = parent.querySelector('.chart-container');
  if (container) {
    parent.insertBefore(bar, container);
  } else {
    parent.appendChild(bar);
  }
  return bar;
}

/**
 * @param {number} price
 * @returns {string}
 */
function formatBtcPrice(price) {
  if (!Number.isFinite(price)) return '\u2014';
  if (price >= 1000) {
    return `$${price.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
  }
  return `$${price.toFixed(2)}`;
}

/**
 * @param {HTMLElement} bar
 * @param {{
 *   candle: Candle|null,
 *   analysis: AnalysisResult|null,
 *   toggles: OverlayToggles,
 *   timeframe: string,
 *   replayIndex: number,
 *   replayTotal: number,
 *   visible: boolean,
 *   inspecting?: boolean,
 * }} opts
 */
export function updateChartContextBar(bar, opts) {
  const {
    candle, analysis, toggles, timeframe, replayIndex, replayTotal, visible, inspecting,
  } = opts;
  if (!bar) return;

  if (!visible || !analysis || !candle) {
    bar.hidden = true;
    bar.classList.remove('chart-ctx-bar-inspecting');
    return;
  }

  bar.hidden = false;
  bar.classList.toggle('chart-ctx-bar-inspecting', Boolean(inspecting));
  bar.innerHTML = '';

  const cycle = analysis.currentCycle;
  const trend = analysis.overallTrend;
  const psych = analysis.psychology;
  const calendar = psychologyBandAtTime(candle.timestamp, cycle.nextHalvingEstimate);
  const dd = analysis.cycleExtremes?.drawdownFromHighPct;

  const chips = [
    el('span', {
      class: 'chart-ctx-chip chart-ctx-chip-date',
      title: inspecting ? 'Th\u1eddi \u0111i\u1ec3m \u0111ang xem' : 'Th\u1eddi \u0111i\u1ec3m replay',
    }, [
      formatTimestamp(candle.timestamp),
    ]),
    el('span', { class: 'chart-ctx-chip chart-ctx-chip-price' }, [formatBtcPrice(candle.close)]),
    el('span', {
      class: 'chart-ctx-chip',
      style: `border-color:${cycle.phaseColor};color:${cycle.phaseColor}`,
      title: cycle.phaseLabel,
    }, [
      `${cycle.halvingLabel.replace('Halving ', 'H')} \u00b7 ${cycle.progressPct.toFixed(0)}%`,
    ]),
    el('span', {
      class: 'chart-ctx-chip',
      style: `border-color:${trend.direction === 'uptrend' ? '#22c55e' : trend.direction === 'downtrend' ? '#ef4444' : '#94a3b8'}`,
    }, [
      `${TREND_VI[trend.direction] ?? trend.direction}`,
    ]),
  ];

  if (toggles.psychology) {
    chips.push(el('span', {
      class: 'chart-ctx-chip',
      style: `border-color:${psych.color};color:${psych.color}`,
      title: calendar ? `L\u1ecbch: ${calendar.phase.labelVi}` : psych.description,
    }, [
      psych.labelVi,
    ]));
  }

  if (dd != null && Math.abs(dd) >= 8) {
    chips.push(el('span', {
      class: 'chart-ctx-chip chart-ctx-chip-muted',
      title: 'Drawdown t\u1eeb \u0111\u1ec9nh chu k\u1ef3',
    }, [
      `${dd.toFixed(0)}% \u0111\u1ec9nh CK`,
    ]));
  }

  bar.appendChild(el('div', { class: 'chart-context-row' }, chips));
  const metaParts = [
    inspecting ? '\u0110ang xem' : null,
    `N\u1ebfn ${replayIndex.toLocaleString()}/${replayTotal.toLocaleString()}`,
    timeframe === 'H4' ? 'N\u00ean d\u00f9ng W/D1' : null,
  ].filter(Boolean);
  bar.appendChild(el('span', { class: 'chart-context-meta' }, [metaParts.join(' \u00b7 ')]));
}

/**
 * @param {HTMLElement} toolbar
 * @param {(preset: keyof typeof CHART_OVERLAY_PRESETS) => void} onPreset
 */
export function mountOverlayPresets(toolbar, onPreset) {
  const group = el('div', { class: 'chart-toolbar-group chart-overlay-presets' }, [
    el('button', {
      type: 'button',
      class: 'btn btn-sm chart-preset-btn active',
      id: 'chart-preset-clean',
      title: 'Chu k\u1ef3 + halving + t\u00e2m l\u00fd',
    }, ['S\u1ea1ch']),
    el('button', {
      type: 'button',
      class: 'btn btn-sm chart-preset-btn',
      id: 'chart-preset-trend',
      title: 'Th\u00eam \u0111\u01b0\u1eddng xu h\u01b0\u1edbng',
    }, ['+ Xu h\u01b0\u1edbng']),
    el('button', {
      type: 'button',
      class: 'btn btn-sm chart-preset-btn',
      id: 'chart-preset-full',
      title: 'Swing + Elliott + t\u1ea5t c\u1ea3',
    }, ['\u0110\u1ea7y \u0111\u1ee7']),
  ]);

  const emaGroup = toolbar.querySelector('.chart-toolbar-group:has(#chart-ema)');
  if (emaGroup?.nextSibling) {
    toolbar.insertBefore(group, emaGroup.nextSibling);
  } else {
    toolbar.appendChild(group);
  }

  for (const [id, key] of [
    ['chart-preset-clean', 'clean'],
    ['chart-preset-trend', 'trend'],
    ['chart-preset-full', 'full'],
  ]) {
    group.querySelector(`#${id}`)?.addEventListener('click', () => {
      group.querySelectorAll('.chart-preset-btn').forEach((btn) => {
        btn.classList.toggle('active', btn.id === id);
      });
      onPreset(/** @type {keyof typeof CHART_OVERLAY_PRESETS} */ (key));
    });
  }
}

/**
 * @param {HTMLElement} toolbar
 * @param {OverlayToggles} toggles
 */
export function syncOverlayCheckboxes(toolbar, toggles) {
  for (const [id, key] of [
    ['chart-overlay-swings', 'swings'],
    ['chart-overlay-trends', 'trends'],
    ['chart-overlay-cycle', 'cycle'],
    ['chart-overlay-elliott', 'elliott'],
    ['chart-overlay-halving', 'halving'],
    ['chart-overlay-psychology', 'psychology'],
    ['chart-overlay-psychology-bg', 'psychologyBg'],
  ]) {
    const input = toolbar.querySelector(`#${id}`);
    if (input) /** @type {HTMLInputElement} */ (input).checked = toggles[key];
  }
}

/**
 * @param {HTMLElement} toolbar
 */
export function clearPresetActiveState(toolbar) {
  toolbar.querySelectorAll('.chart-preset-btn').forEach((btn) => {
    btn.classList.remove('active');
  });
}
