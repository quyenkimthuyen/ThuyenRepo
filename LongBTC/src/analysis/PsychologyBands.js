/**
 * Halving-calendar psychology bands for a time range.
 * @module analysis/PsychologyBands
 */

import { BTC_HALVING_EVENTS, CYCLE_LENGTH_DAYS, CYCLE_PHASE_RANGES } from './BtcCycleConfig.js';
import { buildChartPsychologyTimeline, resolveChartPsychologyTimeline } from './PsychologyCycleMapper.js';

/**
 * @typedef {{
 *   kind: 'cycle'|'psychology',
 *   phase: { id: string, labelVi: string, label: string, color: string },
 *   startTime: number,
 *   endTime: number,
 *   halvingLabel: string,
 *   cycleIndex: number,
 * }} PsychologyBand
 */

const MS_PER_DAY = 24 * 60 * 60 * 1000;

/** @type {Record<string, { id: string, label: string, labelVi: string, color: string }>} */
const CYCLE_PHASE_META = {
  accumulation: {
    id: 'accumulation',
    label: 'Accumulation',
    labelVi: 'T\u00edch l\u0169y',
    color: CYCLE_PHASE_RANGES.accumulation.color,
  },
  markup: {
    id: 'markup',
    label: 'Markup',
    labelVi: 'T\u0103ng tr\u01b0\u1edfng',
    color: CYCLE_PHASE_RANGES.markup.color,
  },
  distribution: {
    id: 'distribution',
    label: 'Distribution',
    labelVi: 'Ph\u00e2n ph\u1ed1i',
    color: CYCLE_PHASE_RANGES.distribution.color,
  },
  markdown: {
    id: 'markdown',
    label: 'Markdown',
    labelVi: 'Gi\u1ea3m gi\u00e1',
    color: CYCLE_PHASE_RANGES.markdown.color,
  },
};

/**
 * @deprecated Use buildChartPsychologyTimeline — kept for tests/compat.
 * @param {{ includePreCycle?: boolean }} [_options]
 */
export function buildSequentialPsychologyTimeline(_options = {}) {
  return buildChartPsychologyTimeline();
}

/**
 * @param {number} halvingIndex
 * @param {number} [currentCycleEnd]
 * @returns {number}
 */
function halvingWindowEndMs(halvingIndex, currentCycleEnd) {
  const halving = BTC_HALVING_EVENTS[halvingIndex];
  const next = BTC_HALVING_EVENTS[halvingIndex + 1];
  return next
    ? next.timestamp
    : (currentCycleEnd ?? halving.timestamp + CYCLE_LENGTH_DAYS * MS_PER_DAY);
}

/**
 * Actual halving-to-halving span (used for % phase mapping on chart).
 * @param {number} halvingStartMs
 * @param {number} halvingEndMs
 * @returns {number}
 */
function cycleSpanMs(halvingStartMs, halvingEndMs) {
  return Math.max(0, halvingEndMs - halvingStartMs);
}

/**
 * @param {number} halvingStartMs
 * @param {number} halvingEndMs
 * @param {string} halvingLabel
 * @param {number} cycleIndex
 * @returns {PsychologyBand[]}
 */
function cycleBandsForHalvingWindow(halvingStartMs, halvingEndMs, halvingLabel, cycleIndex) {
  const span = cycleSpanMs(halvingStartMs, halvingEndMs);
  if (span <= 0) return [];

  /** @type {PsychologyBand[]} */
  const bands = [];

  for (const [phaseId, range] of Object.entries(CYCLE_PHASE_RANGES)) {
    const meta = CYCLE_PHASE_META[phaseId];
    if (!meta || range.end <= range.start) continue;

    bands.push({
      kind: 'cycle',
      phase: meta,
      startTime: halvingStartMs + range.start * span,
      endTime: halvingStartMs + range.end * span,
      halvingLabel,
      cycleIndex,
    });
  }

  return bands;
}

/**
 * Psychology bands mapped to % of actual halving-to-halving window.
 * @param {number} halvingStartMs
 * @param {number} halvingEndMs
 * @param {string} halvingLabel
 * @param {number} cycleIndex
 * @param {import('../data/Candle.js').Candle[]} [candles]
 * @returns {PsychologyBand[]}
 */
function psychologyBandsForHalvingWindow(halvingStartMs, halvingEndMs, halvingLabel, cycleIndex, candles = []) {
  const span = cycleSpanMs(halvingStartMs, halvingEndMs);
  if (span <= 0) return [];

  return resolveChartPsychologyTimeline(halvingStartMs, halvingEndMs, candles).map((item) => ({
    kind: 'psychology',
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
export function buildCycleBandsForRange(fromTs, toTs, currentCycleEnd) {
  if (!Number.isFinite(fromTs) || !Number.isFinite(toTs) || toTs <= fromTs) return [];

  /** @type {PsychologyBand[]} */
  const bands = [];

  for (let i = 0; i < BTC_HALVING_EVENTS.length; i++) {
    const halving = BTC_HALVING_EVENTS[i];
    const end = halvingWindowEndMs(i, currentCycleEnd);
    if (end <= fromTs || halving.timestamp >= toTs) continue;
    bands.push(...cycleBandsForHalvingWindow(halving.timestamp, end, halving.label, i + 1));
  }

  return bands;
}

/**
 * @param {number} fromTs
 * @param {number} toTs
 * @param {number} [currentCycleEnd]
 * @returns {PsychologyBand[]}
 */
export function buildChartPhaseBandsForRange(fromTs, toTs, currentCycleEnd) {
  return [
    ...buildCycleBandsForRange(fromTs, toTs, currentCycleEnd),
    ...buildPsychologyBandsForRange(fromTs, toTs, currentCycleEnd),
  ];
}

/**
 * @param {number} fromTs
 * @param {number} toTs
 * @param {number} [currentCycleEnd]
 * @param {{ candles?: import('../data/Candle.js').Candle[] }} [options]
 * @returns {PsychologyBand[]}
 */
export function buildPsychologyBandsForRange(fromTs, toTs, currentCycleEnd, options = {}) {
  if (!Number.isFinite(fromTs) || !Number.isFinite(toTs) || toTs <= fromTs) return [];

  const candles = options.candles ?? [];

  /** @type {PsychologyBand[]} */
  const bands = [];

  for (let i = 0; i < BTC_HALVING_EVENTS.length; i++) {
    const halving = BTC_HALVING_EVENTS[i];
    const end = halvingWindowEndMs(i, currentCycleEnd);
    if (end <= fromTs || halving.timestamp >= toTs) continue;
    bands.push(
      ...psychologyBandsForHalvingWindow(halving.timestamp, end, halving.label, i + 1, candles)
    );
  }

  return bands;
}

/**
 * Psychology phase band at a timestamp (price-aware when candles provided).
 * @param {number} timestampMs
 * @param {number} currentCycleEnd
 * @param {import('../data/Candle.js').Candle[]} [candles]
 * @returns {PsychologyBand|undefined}
 */
export function psychologyBandAtTime(timestampMs, currentCycleEnd, candles = []) {
  const bands = buildPsychologyBandsForRange(
    timestampMs - 1,
    timestampMs + 1,
    currentCycleEnd,
    { candles }
  );
  return bands.find((b) => timestampMs >= b.startTime && timestampMs < b.endTime);
}

/**
 * Psychology calendar bands grouped by halving cycle (for history UI).
 * @param {number} [currentCycleEnd]
 * @param {number} [asOf=Date.now()]
 * @param {import('../data/Candle.js').Candle[]} [candles]
 * @returns {Array<{
 *   halvingLabel: string,
 *   cycleIndex: number,
 *   startTime: number,
 *   endTime: number,
 *   bands: PsychologyBand[],
 *   isCurrent: boolean,
 *   progressPct: number,
 * }>}
 */
export function buildPsychologyCycleHistory(currentCycleEnd, asOf = Date.now(), candles = []) {
  /** @type {ReturnType<typeof buildPsychologyCycleHistory>} */
  const cycles = [];

  for (let i = 0; i < BTC_HALVING_EVENTS.length; i++) {
    const halving = BTC_HALVING_EVENTS[i];
    const end = halvingWindowEndMs(i, currentCycleEnd);
    if (end <= halving.timestamp) continue;

    const span = end - halving.timestamp;
    const elapsed = Math.max(0, Math.min(span, asOf - halving.timestamp));
    const progressPct = span > 0 ? (elapsed / span) * 100 : 0;
    const isCurrent = asOf >= halving.timestamp && asOf < end;

    cycles.push({
      halvingLabel: halving.label,
      cycleIndex: i + 1,
      startTime: halving.timestamp,
      endTime: end,
      bands: psychologyBandsForHalvingWindow(halving.timestamp, end, halving.label, i + 1, candles),
      isCurrent,
      progressPct: isCurrent ? progressPct : (asOf >= end ? 100 : 0),
    });
  }

  return cycles;
}

/**
 * @param {number} year
 * @returns {string}
 */
export function formatHistoryYear(year) {
  return String(year);
}

/**
 * @param {number} ts
 * @returns {number}
 */
export function historyYear(ts) {
  return new Date(ts).getUTCFullYear();
}
