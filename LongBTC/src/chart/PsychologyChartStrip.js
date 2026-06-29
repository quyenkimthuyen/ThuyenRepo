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
const STRIP_HEIGHT_PX = 58;

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
    style: `--psychology-strip-height:${STRIP_HEIGHT_PX}px`,
  }, [
    el('aside', { class: 'chart-psychology-aside' }, [
      el('span', { class: 'chart-psychology-strip-title' }, ['T\u00e2m l\u00fd TT']),
      el('div', { class: 'chart-psychology-detail', id: 'psy-detail' }, [
        el('span', { class: 'chart-psychology-detail-kicker' }, ['Theo gi\u00e1']),
        el('span', { class: 'chart-psychology-detail-price', id: 'psy-price' }, ['\u2014']),
        el('span', { class: 'chart-psychology-detail-calendar', id: 'psy-calendar' }, ['']),
      ]),
    ]),
    el('div', { class: 'chart-psychology-track' }, [
      el('div', { class: 'chart-psychology-segments', id: 'chart-psychology-segments' }),
      el('div', { class: 'chart-psychology-halvings', id: 'psy-halvings' }),
      el('div', { class: 'chart-psychology-now', id: 'chart-psychology-now', hidden: true }),
    ]),
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
 * @param {PsychologyBand[]} bands
 * @param {number} ts
 * @returns {PsychologyBand|undefined}
 */
function bandAtTime(bands, ts) {
  return bands.find((b) => ts >= b.startTime && ts < b.endTime);
}

/**
 * @param {string} labelVi
 * @param {number} widthPx
 * @returns {string|null}
 */
function segmentLabel(labelVi, widthPx) {
  if (widthPx >= 64) return labelVi;
  if (widthPx >= 40) {
    const short = {
      'H\u01b0ng ph\u1ea5n c\u1ef1c \u0111\u1ed9': 'H\u01b0ng ph\u1ea5n',
      'Ch\u00e1n n\u1ea3n': 'Ch\u00e1n',
      'Ph\u1ee7 nh\u1eadn': 'Ph\u1ee7 nh\u1eadn',
      'Nh\u1eb9 nh\u00f5m': 'Nh\u1eb9',
      '\u0110\u1ea7u h\u00e0ng': '\u0110\u1ea7u h\u00e0ng',
    };
    return short[labelVi] ?? labelVi.split(' ')[0];
  }
  return null;
}

/**
 * @param {HTMLElement} priceEl
 * @param {HTMLElement} calendarEl
 * @param {AnalysisResult} analysis
 * @param {PsychologyBand|undefined} calendarBand
 */
function updateDetailPanel(priceEl, calendarEl, analysis, calendarBand) {
  const p = analysis.psychology;
  priceEl.textContent = `${p.labelVi} \u00b7 ${p.confidence}%`;
  priceEl.style.color = p.color;

  if (calendarBand) {
    const halvingShort = calendarBand.halvingLabel.replace('Halving ', 'H');
    calendarEl.textContent = `L\u1ecbch ${halvingShort}: ${calendarBand.phase.labelVi}`;
    calendarEl.title = [
      calendarBand.halvingLabel,
      calendarBand.phase.labelVi,
      calendarBand.phase.label,
      p.priceContribution ?? '',
    ].filter(Boolean).join(' \u00b7 ');
  } else {
    calendarEl.textContent = 'Ngo\u00e0i v\u00f9ng chu k\u1ef3 halving';
    calendarEl.title = p.priceContribution ?? '';
  }
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
  const calendarBand = bandAtTime(bands, cursorTs);

  const segmentsEl = strip.querySelector('#chart-psychology-segments');
  const halvingsEl = strip.querySelector('#psy-halvings');
  const nowEl = strip.querySelector('#chart-psychology-now');
  const priceEl = strip.querySelector('#psy-price');
  const calendarEl = strip.querySelector('#psy-calendar');

  if (!segmentsEl || !halvingsEl || !nowEl || !priceEl || !calendarEl) return;

  updateDetailPanel(priceEl, calendarEl, analysis, calendarBand);

  segmentsEl.innerHTML = '';
  halvingsEl.innerHTML = '';

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
    const halvingShort = band.halvingLabel.replace('Halving ', 'H');
    const title = [
      band.halvingLabel,
      band.phase.labelVi,
      `(${band.phase.label})`,
      isAssessed ? `\u00b7 Kh\u1edbp \u0111\u00e1nh gi\u00e1 theo gi\u00e1` : '',
    ].filter(Boolean).join(' \u00b7 ');

    const label = segmentLabel(band.phase.labelVi, px.width);

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
      label ? el('span', { class: 'chart-psychology-seg-label' }, [label]) : null,
      px.width >= 28
        ? el('span', { class: 'chart-psychology-seg-halving' }, [halvingShort])
        : null,
    ].filter(Boolean)));
  }

  for (const h of BTC_HALVING_EVENTS) {
    if (h.timestamp < rangeFromTs || h.timestamp > rangeToTs) continue;
    const x = timeToPx(timeScale, h.timestamp, chartWidth);
    if (x === null) continue;

    halvingsEl.appendChild(el('div', {
      class: 'chart-psychology-halving',
      style: `left:${x}px`,
      title: h.label,
    }, [
      el('span', { class: 'chart-psychology-halving-tag' }, [
        h.label.replace('Halving ', 'H'),
      ]),
    ]));
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
