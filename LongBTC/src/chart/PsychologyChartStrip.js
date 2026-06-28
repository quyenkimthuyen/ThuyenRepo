/**
 * Psychology phase strip synced to chart time scale (halving cycle bands + price assessment).
 * @module chart/PsychologyChartStrip
 */

import { el } from '../utils/dom.js';
import { buildPsychologyTimeline } from '../analysis/PsychologyCycleMapper.js';

/**
 * @typedef {import('../analysis/LongTermAnalysisEngine.js').LongTermAnalysisResult} AnalysisResult
 */

/**
 * @param {AnalysisResult['currentCycle']} cycle
 * @returns {Array<{ phase: { id: string, labelVi: string, label: string, color: string }, startTime: number, endTime: number }>}
 */
export function buildPsychologyBandsForCycle(cycle) {
  const start = cycle.halvingTime;
  const span = cycle.nextHalvingEstimate - start;
  if (span <= 0) return [];

  return buildPsychologyTimeline()
    .filter((item) => item.endPct > item.startPct)
    .map((item) => ({
      phase: item.phase,
      startTime: start + (item.startPct / 100) * span,
      endTime: start + (item.endPct / 100) * span,
    }));
}

/**
 * @param {HTMLElement} chartContainer
 * @returns {{ bg: HTMLElement, strip: HTMLElement }}
 */
export function mountPsychologyLayers(chartContainer) {
  const bg = el('div', {
    class: 'chart-psychology-bg',
    id: 'chart-psychology-bg',
    hidden: true,
  });
  const strip = el('div', {
    class: 'chart-psychology-strip',
    id: 'chart-psychology-strip',
    hidden: true,
  }, [
    el('span', { class: 'chart-psychology-strip-title' }, ['T\u00e2m l\u00fd TT']),
    el('div', { class: 'chart-psychology-segments', id: 'chart-psychology-segments' }),
    el('div', { class: 'chart-psychology-now', id: 'chart-psychology-now', title: 'V\u1ecb tr\u00ed n\u1ebfn hi\u1ec7n t\u1ea1i' }),
    el('div', { class: 'chart-psychology-pin', id: 'chart-psychology-pin', hidden: true }),
  ]);

  chartContainer.prepend(bg);
  chartContainer.appendChild(strip);
  return { bg, strip };
}

/**
 * @param {import('../../vendor/lightweight-charts.mjs').ITimeScaleApi|null} timeScale
 * @param {number} tsMs
 * @param {number} chartWidth
 * @returns {number|null}
 */
function timeToPx(timeScale, tsMs, chartWidth) {
  if (!timeScale) return null;
  const x = timeScale.timeToCoordinate(Math.floor(tsMs / 1000));
  if (x === null || !Number.isFinite(x)) return null;
  return Math.max(0, Math.min(chartWidth, x));
}

/**
 * @param {number|null} x1
 * @param {number|null} x2
 * @param {number} chartWidth
 * @returns {{ left: number, width: number }|null}
 */
function segmentPx(x1, x2, chartWidth) {
  if (x1 === null && x2 === null) return null;
  const a = x1 ?? 0;
  const b = x2 ?? chartWidth;
  const left = Math.max(0, Math.min(a, b));
  const right = Math.min(chartWidth, Math.max(a, b));
  const width = right - left;
  if (width < 2) return null;
  return { left, width };
}

/**
 * Paint psychology bands on chart background + bottom strip.
 * @param {{
 *   bg: HTMLElement,
 *   strip: HTMLElement,
 *   timeScale: import('../../vendor/lightweight-charts.mjs').ITimeScaleApi|null,
 *   chartWidth: number,
 *   analysis: AnalysisResult,
 *   lastCandleTs: number,
 *   visible: boolean,
 * }} opts
 */
export function updatePsychologyLayers(opts) {
  const { bg, strip, timeScale, chartWidth, analysis, lastCandleTs, visible } = opts;
  if (!visible || !analysis) {
    bg.hidden = true;
    strip.hidden = true;
    return;
  }

  bg.hidden = false;
  strip.hidden = false;

  const bands = buildPsychologyBandsForCycle(analysis.currentCycle);
  const assessedId = analysis.psychology.phaseId;
  const segmentsEl = strip.querySelector('#chart-psychology-segments');
  const nowEl = strip.querySelector('#chart-psychology-now');
  const pinEl = strip.querySelector('#chart-psychology-pin');

  if (!segmentsEl || !nowEl || !pinEl) return;

  segmentsEl.innerHTML = '';
  bg.innerHTML = '';

  for (const band of bands) {
    const px = segmentPx(
      timeToPx(timeScale, band.startTime, chartWidth),
      timeToPx(timeScale, band.endTime, chartWidth),
      chartWidth
    );
    if (!px) continue;

    const isAssessed = band.phase.id === assessedId;
    const color = band.phase.color;

    segmentsEl.appendChild(el('div', {
      class: `chart-psychology-seg${isAssessed ? ' is-assessed' : ''}`,
      style: `left:${px.left}px;width:${px.width}px;--phase-color:${color}`,
      title: `${band.phase.labelVi} (${band.phase.label})`,
    }, [
      el('span', { class: 'chart-psychology-seg-label' }, [band.phase.labelVi]),
    ]));

    bg.appendChild(el('div', {
      class: `chart-psychology-bg-seg${isAssessed ? ' is-assessed' : ''}`,
      style: `left:${px.left}px;width:${px.width}px;--phase-color:${color}`,
      title: band.phase.labelVi,
    }));
  }

  const nowX = timeToPx(timeScale, lastCandleTs, chartWidth);
  if (nowX !== null) {
    nowEl.style.left = `${nowX}px`;
    nowEl.hidden = false;

    pinEl.hidden = false;
    pinEl.style.left = `${Math.min(chartWidth - 8, Math.max(8, nowX))}px`;
    pinEl.style.borderColor = analysis.psychology.color;
    pinEl.style.color = analysis.psychology.color;
    pinEl.textContent = analysis.psychology.labelVi;
    pinEl.title = analysis.psychology.priceContribution ?? analysis.psychology.description;
  } else {
    nowEl.hidden = true;
    pinEl.hidden = true;
  }
}
