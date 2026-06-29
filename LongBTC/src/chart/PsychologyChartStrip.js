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
    el('div', { class: 'chart-psychology-now', id: 'chart-psychology-now', title: 'V\u1ecb tr\u00ed \u0111ang xem' }),
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
 * @param {PsychologyBand[]} bands
 * @param {number} ts
 * @returns {PsychologyBand|undefined}
 */
function bandAtTime(bands, ts) {
  return bands.find((b) => ts >= b.startTime && ts < b.endTime);
}

/**
 * Paint psychology bands on chart background + bottom strip.
 * @param {{
 *   bg: HTMLElement,
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
export function updatePsychologyLayers(opts) {
  const {
    bg, strip, timeScale, chartWidth, analysis,
    rangeFromTs, rangeToTs, cursorTs, visible,
  } = opts;

  if (!visible || !analysis) {
    bg.hidden = true;
    strip.hidden = true;
    return;
  }

  bg.hidden = false;
  strip.hidden = false;

  const bands = buildPsychologyBandsForRange(
    rangeFromTs,
    rangeToTs,
    analysis.currentCycle.nextHalvingEstimate
  );
  const assessedId = analysis.psychology.phaseId;
  const calendarBand = bandAtTime(bands, cursorTs);

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

    bg.appendChild(el('div', {
      class: `chart-psychology-bg-seg${isAtCursor ? ' is-at-cursor' : ''}${isAssessed ? ' is-assessed' : ''}`,
      style: `left:${px.left}px;width:${px.width}px;--phase-color:${color}`,
      title,
    }));
  }

  const nowX = timeToPx(timeScale, cursorTs, chartWidth);
  if (nowX !== null) {
    nowEl.style.left = `${nowX}px`;
    nowEl.hidden = false;

    pinEl.hidden = false;
    pinEl.style.left = `${Math.min(chartWidth - 8, Math.max(8, nowX))}px`;
    pinEl.style.borderColor = analysis.psychology.color;
    pinEl.style.color = analysis.psychology.color;
    pinEl.textContent = analysis.psychology.labelVi;

    const calLabel = calendarBand?.phase.labelVi ?? '?';
    const calHint = calendarBand
      ? `L\u1ecbch halving: ${calendarBand.halvingLabel} \u2192 ${calLabel}`
      : '';
    pinEl.title = [
      `Theo gi\u00e1: ${analysis.psychology.labelVi}`,
      calHint,
      analysis.psychology.priceContribution ?? '',
    ].filter(Boolean).join(' \u00b7 ');
  } else {
    nowEl.hidden = true;
    pinEl.hidden = true;
  }
}
