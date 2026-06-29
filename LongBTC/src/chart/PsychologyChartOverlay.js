/**
 * Time-synced cycle + psychology background zones on the price chart.
 * @module chart/PsychologyChartOverlay
 */

import { el } from '../utils/dom.js';
import { buildChartPhaseBandsForRange } from '../analysis/PsychologyBands.js';

/**
 * @param {HTMLElement} chartContainer
 * @returns {HTMLElement}
 */
export function mountPsychologyChartBg(chartContainer) {
  const wrap = el('div', {
    class: 'chart-phase-bg',
    id: 'chart-psychology-bg',
    hidden: true,
  });
  wrap.appendChild(el('div', { class: 'chart-phase-bg-cycle', id: 'chart-phase-bg-cycle' }));
  wrap.appendChild(el('div', { class: 'chart-phase-bg-psych', id: 'chart-phase-bg-psych' }));
  chartContainer.appendChild(wrap);
  return wrap;
}

/**
 * @param {import('../../vendor/lightweight-charts.mjs').ITimeScaleApi|null} timeScale
 * @param {number} tsMs
 * @param {number} plotWidth
 * @returns {number|null}
 */
function timeToPx(timeScale, tsMs, plotWidth) {
  if (!timeScale) return null;
  const x = timeScale.timeToCoordinate(Math.floor(tsMs / 1000));
  if (x === null || !Number.isFinite(x)) return null;
  return Math.max(0, Math.min(plotWidth, x));
}

/**
 * @param {number|null} x1
 * @param {number|null} x2
 * @param {number} plotWidth
 * @returns {{ left: number, width: number }|null}
 */
function segmentPx(x1, x2, plotWidth) {
  if (x1 === null && x2 === null) return null;
  const a = x1 ?? 0;
  const b = x2 ?? plotWidth;
  const left = Math.max(0, Math.min(a, b));
  const right = Math.min(plotWidth, Math.max(a, b));
  const width = right - left;
  if (width < 1) return null;
  return { left, width };
}

/**
 * @param {HTMLElement} layer
 * @param {import('../analysis/PsychologyBands.js').PsychologyBand[]} bands
 * @param {'cycle'|'psychology'} kind
 * @param {import('../../vendor/lightweight-charts.mjs').ITimeScaleApi|null} timeScale
 * @param {number} plotWidth
 * @param {number} cursorTs
 * @returns {number}
 */
function renderBandLayer(layer, bands, kind, timeScale, plotWidth, cursorTs) {
  layer.innerHTML = '';
  let rendered = 0;

  for (const band of bands) {
    if (band.kind !== kind) continue;

    const px = segmentPx(
      timeToPx(timeScale, band.startTime, plotWidth),
      timeToPx(timeScale, band.endTime, plotWidth),
      plotWidth
    );
    if (!px) continue;

    rendered++;
    const isAtCursor = cursorTs >= band.startTime && cursorTs < band.endTime;
    const isCycle = kind === 'cycle';
    const layerLabel = isCycle ? 'Giai \u0111o\u1ea1n chu k\u1ef3 BTC' : 'T\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng';
    const title = [
      band.halvingLabel,
      layerLabel,
      band.phase.labelVi,
      `(${band.phase.label})`,
    ].join(' \u00b7 ');

    const showLabel = isCycle ? px.width >= 56 : px.width >= 40;

    layer.appendChild(el('div', {
      class: [
        'chart-phase-bg-seg',
        isCycle ? 'chart-phase-bg-seg--cycle' : 'chart-phase-bg-seg--psych',
        isAtCursor ? 'is-at-cursor' : '',
      ].filter(Boolean).join(' '),
      style: `left:${px.left}px;width:${px.width}px;--phase-color:${band.phase.color}`,
      title,
    }, showLabel ? [
      el('span', {
        class: `chart-phase-bg-label${isCycle ? ' chart-phase-bg-label--cycle' : ' chart-phase-bg-label--psych'}`,
      }, [band.phase.labelVi]),
    ] : []));
  }

  return rendered;
}

/**
 * @param {HTMLElement} bg
 * @param {{
 *   timeScale: import('../../vendor/lightweight-charts.mjs').ITimeScaleApi|null,
 *   plotWidth: number,
 *   chartWidth?: number,
 *   currentCycleEnd: number,
 *   rangeFromTs: number,
 *   rangeToTs: number,
 *   cursorTs: number,
 *   visible: boolean,
 * }} opts
 */
export function updatePsychologyChartBg(bg, opts) {
  const {
    timeScale, plotWidth, chartWidth, currentCycleEnd,
    rangeFromTs, rangeToTs, cursorTs, visible,
  } = opts;

  if (!bg) return 0;

  if (!visible || plotWidth < 10 || !Number.isFinite(currentCycleEnd)) {
    bg.hidden = true;
    return 0;
  }

  const cycleLayer = bg.querySelector('.chart-phase-bg-cycle');
  const psychLayer = bg.querySelector('.chart-phase-bg-psych');
  if (!cycleLayer || !psychLayer) return 0;

  bg.hidden = false;
  const gutter = chartWidth != null && chartWidth > plotWidth ? chartWidth - plotWidth : 0;
  bg.style.marginRight = gutter > 0 ? `${gutter}px` : '';

  const bands = buildChartPhaseBandsForRange(
    rangeFromTs,
    rangeToTs,
    currentCycleEnd
  );

  const cycleRendered = renderBandLayer(
    /** @type {HTMLElement} */ (cycleLayer),
    bands,
    'cycle',
    timeScale,
    plotWidth,
    cursorTs
  );
  const psychRendered = renderBandLayer(
    /** @type {HTMLElement} */ (psychLayer),
    bands,
    'psychology',
    timeScale,
    plotWidth,
    cursorTs
  );

  return cycleRendered + psychRendered;
}
