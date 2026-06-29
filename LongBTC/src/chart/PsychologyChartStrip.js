/**
 * Psychology timeline lane below the price chart (no overlay on candles).
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
 * @param {number} fromTs
 * @param {number} toTs
 * @param {number} [currentCycleEnd]
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

  return bands.sort((a, b) => a.startTime - b.startTime);
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
 * @param {HTMLElement} parent - chart-main column (lane sits below canvas)
 * @returns {HTMLElement}
 */
export function mountPsychologyLane(parent) {
  const lane = el('div', {
    class: 'psychology-lane',
    id: 'chart-psychology-lane',
    hidden: true,
  }, [
    el('aside', { class: 'psychology-lane-aside' }, [
      el('span', { class: 'psychology-lane-title' }, ['T\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng']),
      el('div', { class: 'psychology-lane-current', id: 'psy-current-badge' }, [
        el('span', { class: 'psychology-lane-current-kicker' }, ['Theo gi\u00e1']),
        el('span', { class: 'psychology-lane-current-value', id: 'psy-price-value' }, ['\u2014']),
      ]),
      el('p', { class: 'psychology-lane-calendar', id: 'psy-calendar-hint' }, ['']),
    ]),
    el('div', { class: 'psychology-lane-track-wrap' }, [
      el('div', { class: 'psychology-lane-track', id: 'psy-track' }, [
        el('div', { class: 'psychology-lane-phases', id: 'psy-phases' }),
        el('div', { class: 'psychology-lane-halvings', id: 'psy-halvings' }),
        el('div', { class: 'psychology-lane-playhead', id: 'psy-playhead', hidden: true }),
      ]),
      el('p', { class: 'psychology-lane-hint' }, [
        'Di chu\u1ed9t v\u00f9ng m\u00e0u \u0111\u1ec3 xem giai \u0111o\u1ea1n \u00b7 V\u1ea1ch \u0111\u1ee9ng = Halving',
      ]),
    ]),
  ]);

  parent.insertBefore(lane, parent.querySelector('.replay-bar'));
  return lane;
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
  if (width < 1) return null;
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
 * @param {HTMLElement} lane
 * @param {{
 *   timeScale: import('../../vendor/lightweight-charts.mjs').ITimeScaleApi|null,
 *   chartWidth: number,
 *   analysis: AnalysisResult,
 *   rangeFromTs: number,
 *   rangeToTs: number,
 *   cursorTs: number,
 *   visible: boolean,
 * }} opts
 */
export function updatePsychologyLane(lane, opts) {
  const {
    timeScale, chartWidth, analysis, rangeFromTs, rangeToTs, cursorTs, visible,
  } = opts;

  if (!lane) return;

  if (!visible || !analysis) {
    lane.hidden = true;
    return;
  }

  lane.hidden = false;

  const bands = buildPsychologyBandsForRange(
    rangeFromTs,
    rangeToTs,
    analysis.currentCycle.nextHalvingEstimate
  );
  const calendarBand = bandAtTime(bands, cursorTs);
  const p = analysis.psychology;

  const priceValue = lane.querySelector('#psy-price-value');
  const calendarHint = lane.querySelector('#psy-calendar-hint');
  const phasesEl = lane.querySelector('#psy-phases');
  const halvingsEl = lane.querySelector('#psy-halvings');
  const playheadEl = lane.querySelector('#psy-playhead');
  const badgeEl = lane.querySelector('#psy-current-badge');

  if (!priceValue || !calendarHint || !phasesEl || !halvingsEl || !playheadEl) return;

  priceValue.textContent = p.labelVi;
  priceValue.style.color = p.color;
  if (badgeEl) badgeEl.style.borderColor = p.color;

  const calText = calendarBand
    ? `L\u1ecbch ${calendarBand.halvingLabel.replace('Halving ', 'H')}: ${calendarBand.phase.labelVi}`
    : 'Ngo\u00e0i v\u00f9ng chu k\u1ef3 halving';
  calendarHint.textContent = calText;

  phasesEl.innerHTML = '';
  halvingsEl.innerHTML = '';

  for (const band of bands) {
    const px = segmentPx(
      timeToPx(timeScale, band.startTime, chartWidth),
      timeToPx(timeScale, band.endTime, chartWidth),
      chartWidth
    );
    if (!px) continue;

    const isAtCursor = cursorTs >= band.startTime && cursorTs < band.endTime;

    phasesEl.appendChild(el('div', {
      class: `psychology-lane-phase${isAtCursor ? ' is-active' : ''}`,
      style: `left:${px.left}px;width:${px.width}px;--phase-color:${band.phase.color}`,
      title: `${band.halvingLabel.replace('Halving ', 'Halving #')}\n${band.phase.labelVi} (${band.phase.label})`,
    }));
  }

  for (const h of BTC_HALVING_EVENTS) {
    if (h.timestamp < rangeFromTs || h.timestamp > rangeToTs) continue;
    const x = timeToPx(timeScale, h.timestamp, chartWidth);
    if (x === null) continue;

    halvingsEl.appendChild(el('div', {
      class: 'psychology-lane-halving',
      style: `left:${x}px`,
      title: h.label,
    }, [
      el('span', { class: 'psychology-lane-halving-tag' }, [
        h.label.replace('Halving ', 'H'),
      ]),
    ]));
  }

  const playheadX = timeToPx(timeScale, cursorTs, chartWidth);
  if (playheadX !== null) {
    playheadEl.style.left = `${playheadX}px`;
    playheadEl.hidden = false;
  } else {
    playheadEl.hidden = true;
  }
}

/** @deprecated use mountPsychologyLane */
export function mountPsychologyLayers(parent) {
  return { lane: mountPsychologyLane(parent) };
}

/** @deprecated use updatePsychologyLane */
export function updatePsychologyLayers(opts) {
  const lane = opts.strip?.closest?.('.psychology-lane') ?? opts.lane;
  if (!lane) return;
  updatePsychologyLane(lane, {
    timeScale: opts.timeScale,
    chartWidth: opts.chartWidth,
    analysis: opts.analysis,
    rangeFromTs: opts.rangeFromTs,
    rangeToTs: opts.rangeToTs,
    cursorTs: opts.cursorTs,
    visible: opts.visible,
  });
}
