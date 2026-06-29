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
    class: 'chart-psychology-bg',
    id: 'chart-psychology-bg',
    hidden: true,
  });
  chartContainer.prepend(bg);
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
 *   analysis: import('../analysis/LongTermAnalysisEngine.js').LongTermAnalysisResult,
 *   rangeFromTs: number,
 *   rangeToTs: number,
 *   cursorTs: number,
 *   visible: boolean,
 * }} opts
 */
export function updatePsychologyChartBg(bg, opts) {
  const {
    timeScale, plotWidth, analysis, rangeFromTs, rangeToTs, cursorTs, visible,
  } = opts;

  if (!bg) return;

  if (!visible || !analysis || plotWidth < 10) {
    bg.hidden = true;
    return;
  }

  bg.hidden = false;

  const bands = buildPsychologyBandsForRange(
    rangeFromTs,
    rangeToTs,
    analysis.currentCycle.nextHalvingEstimate
  );

  bg.innerHTML = '';

  for (const band of bands) {
    const px = segmentPx(
      timeToPx(timeScale, band.startTime, plotWidth),
      timeToPx(timeScale, band.endTime, plotWidth),
      plotWidth
    );
    if (!px) continue;

    const isAtCursor = cursorTs >= band.startTime && cursorTs < band.endTime;
    const title = [
      band.halvingLabel,
      band.phase.labelVi,
      `(${band.phase.label})`,
    ].join(' \u00b7 ');

    bg.appendChild(el('div', {
      class: `chart-psychology-bg-seg${isAtCursor ? ' is-at-cursor' : ''}`,
      style: `left:${px.left}px;width:${px.width}px;--phase-color:${band.phase.color}`,
      title,
    }));
  }
}
