/**
 * Time-synced psychology background zones on the price chart.
 * @module chart/PsychologyChartOverlay
 */

import { el } from '../utils/dom.js';
import { buildPsychologyBandsForRange } from '../analysis/PsychologyBands.js';

/**
 * @param {HTMLElement} chartContainer
 * @returns {HTMLElement}
 */
export function mountPsychologyChartBg(chartContainer) {
  const bg = el('div', {
    class: 'chart-phase-bg chart-phase-bg--psych-only',
    id: 'chart-psychology-bg',
    hidden: true,
  });
  chartContainer.appendChild(bg);
  return bg;
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

  bg.hidden = false;
  const gutter = chartWidth != null && chartWidth > plotWidth ? chartWidth - plotWidth : 0;
  bg.style.marginRight = gutter > 0 ? `${gutter}px` : '';

  const bands = buildPsychologyBandsForRange(
    rangeFromTs,
    rangeToTs,
    currentCycleEnd,
    { sequential: true }
  );

  bg.innerHTML = '';
  let rendered = 0;

  for (const band of bands) {
    const px = segmentPx(
      timeToPx(timeScale, band.startTime, plotWidth),
      timeToPx(timeScale, band.endTime, plotWidth),
      plotWidth
    );
    if (!px) continue;

    rendered++;
    const isAtCursor = cursorTs >= band.startTime && cursorTs < band.endTime;
    const title = [
      band.halvingLabel,
      'T\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng',
      band.phase.labelVi,
      `(${band.phase.label})`,
    ].join(' \u00b7 ');

    const showLabel = px.width >= 40;

    bg.appendChild(el('div', {
      class: `chart-phase-bg-seg chart-phase-bg-seg--psych${isAtCursor ? ' is-at-cursor' : ''}`,
      style: `left:${px.left}px;width:${px.width}px;--phase-color:${band.phase.color}`,
      title,
    }, showLabel ? [
      el('span', { class: 'chart-phase-bg-label chart-phase-bg-label--psych' }, [band.phase.labelVi]),
    ] : []));
  }

  return rendered;
}
