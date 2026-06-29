/**
 * Long-term BTC chart context bar, overlay presets, and legend.
 * @module ui/ChartResearchUi
 */

import { el } from '../utils/dom.js';
import { formatTimestamp } from '../data/TimeframeUtils.js';
import { psychologyBandAtTime } from '../analysis/PsychologyBands.js';
import { PSYCHOLOGY_PHASES } from '../analysis/BtcCycleConfig.js';

/**
 * @typedef {import('../analysis/LongTermAnalysisEngine.js').LongTermAnalysisResult} AnalysisResult
 * @typedef {import('../data/Candle.js').Candle} Candle
 * @typedef {{ swings: boolean, trends: boolean, cycle: boolean, elliott: boolean, halving: boolean, psychology: boolean }} OverlayToggles
 */

/** @type {Record<string, OverlayToggles>} */
export const CHART_OVERLAY_PRESETS = {
  minimal: {
    swings: false, trends: true, cycle: true, elliott: false, halving: true, psychology: true,
  },
  cycle: {
    swings: false, trends: false, cycle: true, elliott: false, halving: true, psychology: true,
  },
  full: {
    swings: true, trends: true, cycle: true, elliott: true, halving: true, psychology: true,
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
  parent.insertBefore(bar, parent.firstChild);
  return bar;
}

/**
 * @param {HTMLElement} parent
 * @returns {HTMLElement}
 */
export function mountChartLegendBar(parent) {
  const bar = el('div', {
    class: 'chart-legend-bar',
    id: 'chart-legend-bar',
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
 * }} opts
 */
export function updateChartContextBar(bar, opts) {
  const { candle, analysis, toggles, timeframe, replayIndex, replayTotal, visible } = opts;
  if (!bar) return;

  if (!visible || !analysis || !candle) {
    bar.hidden = true;
    return;
  }

  bar.hidden = false;
  bar.innerHTML = '';

  const cycle = analysis.currentCycle;
  const trend = analysis.overallTrend;
  const psych = analysis.psychology;
  const calendar = psychologyBandAtTime(
    candle.timestamp,
    cycle.nextHalvingEstimate
  );
  const ext = analysis.cycleExtremes;
  const dd = ext?.drawdownFromHighPct;

  bar.appendChild(el('div', { class: 'chart-context-head' }, [
    el('div', { class: 'chart-context-datetime' }, [
      el('span', { class: 'chart-context-date' }, [formatTimestamp(candle.timestamp)]),
      el('span', { class: 'chart-context-progress' }, [
        `N\u1ebfn ${replayIndex.toLocaleString()} / ${replayTotal.toLocaleString()}`,
      ]),
    ]),
    el('div', { class: 'chart-context-price' }, [formatBtcPrice(candle.close)]),
  ]));

  const metrics = el('div', { class: 'chart-context-metrics' }, [
    el('div', {
      class: 'chart-context-metric',
      style: `border-color:${cycle.phaseColor}`,
    }, [
      el('span', { class: 'chart-context-metric-label' }, ['Chu k\u1ef3 halving']),
      el('span', { class: 'chart-context-metric-value' }, [
        `${cycle.halvingLabel.replace('Halving ', 'H')} \u00b7 ${cycle.progressPct.toFixed(1)}%`,
      ]),
      el('span', { class: 'chart-context-metric-hint' }, [cycle.phaseLabel]),
    ]),
    el('div', {
      class: 'chart-context-metric',
      style: `border-color:${trend.direction === 'uptrend' ? '#22c55e' : trend.direction === 'downtrend' ? '#ef4444' : '#94a3b8'}`,
    }, [
      el('span', { class: 'chart-context-metric-label' }, ['Xu h\u01b0\u1edbng']),
      el('span', { class: 'chart-context-metric-value' }, [
        TREND_VI[trend.direction] ?? trend.direction,
      ]),
      el('span', { class: 'chart-context-metric-hint' }, [
        `${trend.confidence}% tin c\u1eady`,
      ]),
    ]),
  ]);

  if (toggles.psychology) {
    metrics.appendChild(el('div', {
      class: 'chart-context-metric',
      style: `border-color:${psych.color}`,
    }, [
      el('span', { class: 'chart-context-metric-label' }, ['T\u00e2m l\u00fd theo gi\u00e1']),
      el('span', { class: 'chart-context-metric-value', style: `color:${psych.color}` }, [
        psych.labelVi,
      ]),
      el('span', { class: 'chart-context-metric-hint' }, [
        calendar
          ? `L\u1ecbch: ${calendar.phase.labelVi}`
          : `${psych.confidence}% tin c\u1eady`,
      ]),
    ]));
  }

  if (dd != null && Math.abs(dd) >= 5) {
    metrics.appendChild(el('div', { class: 'chart-context-metric chart-context-metric-muted' }, [
      el('span', { class: 'chart-context-metric-label' }, ['T\u1eeb \u0111\u1ec9nh chu k\u1ef3']),
      el('span', { class: 'chart-context-metric-value' }, [
        `${dd > 0 ? '+' : ''}${dd.toFixed(1)}%`,
      ]),
      el('span', { class: 'chart-context-metric-hint' }, [
        ext.cycleHigh != null ? `\u0110\u1ec9nh ~${formatBtcPrice(ext.cycleHigh)}` : '',
      ]),
    ]));
  }

  bar.appendChild(metrics);

  if (timeframe === 'H4') {
    bar.appendChild(el('p', { class: 'chart-context-note' }, [
      'Khuy\u1ebfn ngh\u1ecb W ho\u1eb7c D1 \u0111\u1ec3 \u0111\u1ecdc chu k\u1ef3 v\u00e0 t\u00e2m l\u00fd d\u00e0i h\u1ea1n.',
    ]));
  }
}

/**
 * @param {HTMLElement} bar
 * @param {OverlayToggles} toggles
 * @param {AnalysisResult|null} analysis
 */
export function updateChartLegendBar(bar, toggles, analysis) {
  if (!bar) return;

  const anyOn = Object.values(toggles).some(Boolean);
  if (!anyOn || !analysis) {
    bar.hidden = true;
    return;
  }

  bar.hidden = false;
  bar.innerHTML = '';

  const items = [];

  if (toggles.cycle) {
    items.push(legendItem('#3b82f6', 'line', 'V\u00f9ng chu k\u1ef3 4 n\u0103m'));
  }
  if (toggles.trends) {
    items.push(legendItem('#22c55e', 'line', 'Xu h\u01b0\u1edbng t\u0103ng'));
    items.push(legendItem('#ef4444', 'line', 'Xu h\u01b0\u1edbng gi\u1ea3m'));
  }
  if (toggles.swings) {
    items.push(legendItem('#f59e0b', 'dot', '\u0110\u1ec9nh swing'));
    items.push(legendItem('#3b82f6', 'dot', '\u0110\u00e1y swing'));
  }
  if (toggles.elliott) {
    items.push(legendItem('#8b5cf6', 'dot', 'S\u00f3ng Elliott'));
  }
  if (toggles.halving) {
    items.push(legendItem('#a855f7', 'dot', 'M\u1ed1c Halving'));
  }
  if (toggles.psychology) {
    const active = PSYCHOLOGY_PHASES.find((p) => p.id === analysis.psychology.phaseId);
    items.push(legendItem(active?.color ?? '#86efac', 'block', 'V\u00f9ng t\u00e2m l\u00fd (l\u1ecbch halving)'));
    items.push(el('span', { class: 'chart-legend-tip' }, [
      'Di chu\u1ed9t v\u00f9ng m\u00e0u tr\u00ean chart \u0111\u1ec3 xem giai \u0111o\u1ea1n',
    ]));
  }

  bar.appendChild(el('span', { class: 'chart-legend-bar-title' }, ['\u00dd ngh\u0129a l\u1edbp ph\u1ee7']));
  bar.appendChild(el('div', { class: 'chart-legend-bar-items' }, items));
}

/**
 * @param {string} color
 * @param {'line'|'dot'|'block'} kind
 * @param {string} label
 * @returns {HTMLElement}
 */
function legendItem(color, kind, label) {
  const swatch = kind === 'line'
    ? el('span', { class: 'chart-legend-swatch', style: `background:${color}` })
    : kind === 'block'
      ? el('span', {
        class: 'chart-legend-block',
        style: `background:color-mix(in srgb, ${color} 40%, transparent);border-color:${color}`,
      })
      : el('span', { class: 'chart-legend-dot', style: `background:${color}` });

  return el('span', { class: 'chart-legend-item' }, [swatch, label]);
}

/**
 * @param {HTMLElement} toolbar
 * @param {(preset: keyof typeof CHART_OVERLAY_PRESETS) => void} onPreset
 */
export function mountOverlayPresets(toolbar, onPreset) {
  const group = el('div', { class: 'chart-toolbar-group chart-overlay-presets' }, [
    el('span', { class: 'chart-overlay-presets-label' }, ['L\u1edbp ph\u1ee7']),
    el('button', {
      type: 'button',
      class: 'btn btn-sm chart-preset-btn active',
      id: 'chart-preset-minimal',
      title: 'Chu k\u1ef3 + xu h\u01b0\u1edbng + halving + t\u00e2m l\u00fd',
    }, ['G\u1ecdn']),
    el('button', {
      type: 'button',
      class: 'btn btn-sm chart-preset-btn',
      id: 'chart-preset-cycle',
      title: 'Ch\u1ec9 chu k\u1ef3, halving v\u00e0 t\u00e2m l\u00fd',
    }, ['Chu k\u1ef3']),
    el('button', {
      type: 'button',
      class: 'btn btn-sm chart-preset-btn',
      id: 'chart-preset-full',
      title: 'B\u1eadt m\u1ecdi l\u1edbp ph\u00e2n t\u00edch',
    }, ['\u0110\u1ea7y \u0111\u1ee7']),
  ]);

  const toggles = toolbar.querySelector('.chart-analysis-toggles');
  if (toggles) {
    toolbar.insertBefore(group, toggles);
  } else {
    toolbar.appendChild(group);
  }

  for (const [id, key] of [
    ['chart-preset-minimal', 'minimal'],
    ['chart-preset-cycle', 'cycle'],
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
