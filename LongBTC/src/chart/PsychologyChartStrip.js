/**
 * Psychology phase strip synced to chart time scale (all halving cycles + price assessment).
 * @module chart/PsychologyChartStrip
 */

import { el } from '../utils/dom.js';
import { BTC_HALVING_EVENTS, CYCLE_LENGTH_DAYS } from '../analysis/BtcCycleConfig.js';
import { buildPsychologyTimeline } from '../analysis/PsychologyCycleMapper.js';

/**
 * @typedef {import('../analysis/LongTermAnalysisEngine.js').LongTermAnalysisResult} AnalysisResult
 * @typedef {{
 *   phase: { id: string, labelVi: string, label: string, color: string },
 *   startTime: number,
 *   endTime: number,
 *   halvingLabel: string,
 *   cycleIndex: number,
 * }} PsychologyBand
 */

const MS_PER_DAY = 24 * 60 * 60 * 1000;

/**
 * Psychology bands for one halving-to-halving window.
 * @param {number} halvingStartMs
 * @param {number} halvingEndMs
 * @param {string} halvingLabel
 * @param {number} cycleIndex
 * @returns {PsychologyBand[]}
 */
export function buildPsychologyBandsForHalvingWindow(
  halvingStartMs,
  halvingEndMs,
  halvingLabel,
  cycleIndex
) {
  const span = halvingEndMs - halvingStartMs;
  if (span <= 0) return [];

  return buildPsychologyTimeline()
    .filter((item) => item.endPct > item.startPct)
    .map((item) => ({
      phase: item.phase,
      startTime: halvingStartMs + (item.startPct / 100) * span,
      endTime: halvingStartMs + (item.endPct / 100) * span,
      halvingLabel,
      cycleIndex,
    }));
}

/**
 * All psychology bands for every halving cycle overlapping a time range.
 * @param {number} fromTs
 * @param {number} toTs
 * @param {number} [currentCycleEnd] - end of active cycle (next halving estimate)
 * @returns {PsychologyBand[]}
 */
export function buildPsychologyBandsForRange(fromTs, toTs, currentCycleEnd) {
  if (!Number.isFinite(fromTs) || !Number.isFinite(toTs) || toTs <= fromTs) return [];

  /** @type {PsychologyBand[]} */
  const bands = [];

  for (let i = 0; i < BTC_HALVING_EVENTS.length; i++) {
    const halving = BTC_HALVING_EVENTS[i];
    const next = BTC_HALVING_EVENTS[i + 1];
    const end = next
      ? next.timestamp
      : (currentCycleEnd ?? halving.timestamp + CYCLE_LENGTH_DAYS * MS_PER_DAY);

    if (end < fromTs || halving.timestamp > toTs) continue;

    bands.push(...buildPsychologyBandsForHalvingWindow(
      halving.timestamp,
      end,
      halving.label,
      i + 1
    ));
  }

  return bands;
}

/**
 * @param {AnalysisResult['currentCycle']} cycle
 * @returns {PsychologyBand[]}
 */
export function buildPsychologyBandsForCycle(cycle) {
  return buildPsychologyBandsForRange(
    cycle.halvingTime,
    cycle.nextHalvingEstimate,
    cycle.nextHalvingEstimate
  );
}

/**
 * @param {HTMLElement} chartContainer
 * @returns {HTMLElement}
 */
export function mountPsychologyStrip(chartContainer) {
  const strip = el('div', {
    class: 'chart-psychology-strip',
    id: 'chart-psychology-strip',
    hidden: true,
  }, [
    el('span', { class: 'chart-psychology-strip-title' }, ['T\u00e2m l\u00fd TT']),
    el('div', { class: 'chart-psychology-segments', id: 'chart-psychology-segments' }),
    el('div', { class: 'chart-psychology-now', id: 'chart-psychology-now', title: 'V\u1ecb tr\u00ed \u0111ang xem' }),
  ]);

  chartContainer.appendChild(strip);
  return strip;
}

/** @deprecated use mountPsychologyStrip */
export function mountPsychologyLayers(chartContainer) {
  return { strip: mountPsychologyStrip(chartContainer) };
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
 * Paint psychology bands on the bottom strip only (not on the price chart).
 * @param {{
 *   strip: HTMLElement,
 *   timeScale: import('../../vendor/lightweight-charts.mjs').ITimeScaleApi|null,
 *   chartWidth: number,
 *   analysis: AnalysisResult,
 *   rangeFromTs: number,
 *   rangeToTs: number,
 *   cursorTs: number,
 *   visible: boolean,
 * }} opts
 */
export function updatePsychologyStrip(opts) {
  const {
    strip, timeScale, chartWidth, analysis,
    rangeFromTs, rangeToTs, cursorTs, visible,
  } = opts;

  if (!strip) return;

  if (!visible || !analysis) {
    strip.hidden = true;
    return;
  }

  strip.hidden = false;

  const bands = buildPsychologyBandsForRange(
    rangeFromTs,
    rangeToTs,
    analysis.currentCycle.nextHalvingEstimate
  );
  const assessedId = analysis.psychology.phaseId;

  const segmentsEl = strip.querySelector('#chart-psychology-segments');
  const nowEl = strip.querySelector('#chart-psychology-now');

  if (!segmentsEl || !nowEl) return;

  segmentsEl.innerHTML = '';

  for (const band of bands) {
    const px = segmentPx(
      timeToPx(timeScale, band.startTime, chartWidth),
      timeToPx(timeScale, band.endTime, chartWidth),
      chartWidth
    );
    if (!px) continue;

    const isAtCursor = cursorTs >= band.startTime && cursorTs < band.endTime;
    const isAssessed = isAtCursor && band.phase.id === assessedId;
    const color = band.phase.color;
    const title = `${band.halvingLabel} \u00b7 ${band.phase.labelVi} (${band.phase.label})`;

    const classes = [
      'chart-psychology-seg',
      isAtCursor ? ' is-at-cursor' : '',
      isAssessed ? ' is-assessed' : '',
    ].join('');

    segmentsEl.appendChild(el('div', {
      class: classes,
      style: `left:${px.left}px;width:${px.width}px;--phase-color:${color}`,
      title,
    }, [
      px.width > 36
        ? el('span', { class: 'chart-psychology-seg-label' }, [band.phase.labelVi])
        : null,
    ].filter(Boolean)));
  }

  const nowX = timeToPx(timeScale, cursorTs, chartWidth);
  if (nowX !== null) {
    nowEl.style.left = `${nowX}px`;
    nowEl.hidden = false;
  } else {
    nowEl.hidden = true;
  }
}

/** @deprecated use updatePsychologyStrip */
export function updatePsychologyLayers(opts) {
  updatePsychologyStrip({
    strip: opts.strip,
    timeScale: opts.timeScale,
    chartWidth: opts.chartWidth,
    analysis: opts.analysis,
    rangeFromTs: opts.rangeFromTs,
    rangeToTs: opts.rangeToTs,
    cursorTs: opts.cursorTs,
    visible: opts.visible,
  });
}
