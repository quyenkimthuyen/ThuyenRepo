/**
 * Halving-calendar psychology bands for a time range.
 * @module analysis/PsychologyBands
 */

import { BTC_HALVING_EVENTS, CYCLE_LENGTH_DAYS, CYCLE_PHASE_RANGES } from './BtcCycleConfig.js';
import { buildPsychologyTimeline } from './PsychologyCycleMapper.js';

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
const NOMINAL_CYCLE_MS = CYCLE_LENGTH_DAYS * MS_PER_DAY;

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

const ACCUMULATION_PHASE = CYCLE_PHASE_META.accumulation;

/**
 * Non-overlapping psychology windows across one halving cycle (sequential display).
 * @param {{ includePreCycle?: boolean }} [options]
 * @returns {Array<{ phase: { id: string, labelVi: string, label: string, color: string }, startPct: number, endPct: number }>}
 */
export function buildSequentialPsychologyTimeline(options = {}) {
  const includePreCycle = options.includePreCycle !== false;
  const sorted = [...buildPsychologyTimeline()]
    .filter((item) => item.endPct > item.startPct)
    .sort((a, b) => a.startPct - b.startPct || a.endPct - b.endPct);

  /** @type {ReturnType<typeof buildSequentialPsychologyTimeline>} */
  const windows = [];

  const firstStart = sorted[0]?.startPct ?? 20;
  if (includePreCycle && firstStart > 0) {
    windows.push({
      phase: ACCUMULATION_PHASE,
      startPct: 0,
      endPct: firstStart,
    });
  }

  for (let i = 0; i < sorted.length; i++) {
    const item = sorted[i];
    const startPct = item.startPct;
    const endPct = i < sorted.length - 1 ? sorted[i + 1].startPct : 100;
    if (endPct <= startPct) continue;
    windows.push({
      phase: item.phase,
      startPct,
      endPct,
    });
  }

  return windows;
}

/**
 * Nominal halving-to-halving span (fixed 1460d) — same on W, D1, H4.
 * @param {number} halvingStartMs
 * @param {number} halvingEndMs
 * @returns {number}
 */
function nominalCycleSpanMs(halvingStartMs, halvingEndMs) {
  return Math.min(NOMINAL_CYCLE_MS, Math.max(0, halvingEndMs - halvingStartMs));
}

/**
 * @param {number} halvingStartMs
 * @param {number} halvingEndMs
 * @param {string} halvingLabel
 * @param {number} cycleIndex
 * @returns {PsychologyBand[]}
 */
function cycleBandsForHalvingWindow(halvingStartMs, halvingEndMs, halvingLabel, cycleIndex) {
  const span = nominalCycleSpanMs(halvingStartMs, halvingEndMs);
  if (span <= 0) return [];

  const cycleEnd = halvingStartMs + span;

  /** @type {PsychologyBand[]} */
  const bands = [];

  for (const [phaseId, range] of Object.entries(CYCLE_PHASE_RANGES)) {
    const meta = CYCLE_PHASE_META[phaseId];
    if (!meta || range.end <= range.start) continue;

    const startTime = halvingStartMs + range.start * NOMINAL_CYCLE_MS;
    const endTime = halvingStartMs + range.end * NOMINAL_CYCLE_MS;
    const clippedStart = Math.max(halvingStartMs, startTime);
    const clippedEnd = Math.min(cycleEnd, endTime);
    if (clippedEnd <= clippedStart) continue;

    bands.push({
      kind: 'cycle',
      phase: meta,
      startTime: clippedStart,
      endTime: clippedEnd,
      halvingLabel,
      cycleIndex,
    });
  }

  return bands;
}

/**
 * @param {number} halvingStartMs
 * @param {number} halvingEndMs
 * @param {string} halvingLabel
 * @param {number} cycleIndex
 * @param {boolean} [sequential=false]
 * @returns {PsychologyBand[]}
 */
function bandsForHalvingWindow(halvingStartMs, halvingEndMs, halvingLabel, cycleIndex, sequential = false) {
  const span = nominalCycleSpanMs(halvingStartMs, halvingEndMs);
  if (span <= 0) return [];

  const cycleEnd = halvingStartMs + span;

  const timeline = sequential
    ? buildSequentialPsychologyTimeline({ includePreCycle: false })
    : buildPsychologyTimeline().filter((item) => item.endPct > item.startPct);

  return timeline.map((item) => {
    const startTime = halvingStartMs + (item.startPct / 100) * NOMINAL_CYCLE_MS;
    const endTime = halvingStartMs + (item.endPct / 100) * NOMINAL_CYCLE_MS;
    return {
      kind: 'psychology',
      phase: item.phase,
      startTime: Math.max(halvingStartMs, startTime),
      endTime: Math.min(cycleEnd, endTime),
      halvingLabel,
      cycleIndex,
    };
  }).filter((b) => b.endTime > b.startTime);
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
    const next = BTC_HALVING_EVENTS[i + 1];
    const end = next
      ? next.timestamp
      : (currentCycleEnd ?? halving.timestamp + CYCLE_LENGTH_DAYS * MS_PER_DAY);

    if (end < fromTs || halving.timestamp > toTs) continue;

    bands.push(...cycleBandsForHalvingWindow(halving.timestamp, end, halving.label, i + 1));
  }

  return bands;
}

/**
 * Cycle + psychology bands for chart background (cycle first, then psychology).
 * @param {number} fromTs
 * @param {number} toTs
 * @param {number} [currentCycleEnd]
 * @returns {PsychologyBand[]}
 */
export function buildChartPhaseBandsForRange(fromTs, toTs, currentCycleEnd) {
  return [
    ...buildCycleBandsForRange(fromTs, toTs, currentCycleEnd),
    ...buildPsychologyBandsForRange(fromTs, toTs, currentCycleEnd, { sequential: true }),
  ];
}

/**
 * @param {number} fromTs
 * @param {number} toTs
 * @param {number} [currentCycleEnd]
 * @param {{ sequential?: boolean }} [options]
 * @returns {PsychologyBand[]}
 */
export function buildPsychologyBandsForRange(fromTs, toTs, currentCycleEnd, options = {}) {
  if (!Number.isFinite(fromTs) || !Number.isFinite(toTs) || toTs <= fromTs) return [];

  const sequential = options.sequential === true;

  /** @type {PsychologyBand[]} */
  const bands = [];

  for (let i = 0; i < BTC_HALVING_EVENTS.length; i++) {
    const halving = BTC_HALVING_EVENTS[i];
    const next = BTC_HALVING_EVENTS[i + 1];
    const end = next
      ? next.timestamp
      : (currentCycleEnd ?? halving.timestamp + CYCLE_LENGTH_DAYS * MS_PER_DAY);

    if (end < fromTs || halving.timestamp > toTs) continue;

    bands.push(...bandsForHalvingWindow(halving.timestamp, end, halving.label, i + 1, sequential));
  }

  return bands;
}

/**
 * Calendar psychology phase at a timestamp.
 * @param {number} timestampMs
 * @param {number} currentCycleEnd
 * @returns {PsychologyBand|undefined}
 */
export function psychologyBandAtTime(timestampMs, currentCycleEnd) {
  const bands = buildPsychologyBandsForRange(
    timestampMs - 1,
    timestampMs + 1,
    currentCycleEnd
  );
  return bands.find((b) => timestampMs >= b.startTime && timestampMs < b.endTime);
}

/**
 * Psychology calendar bands grouped by halving cycle (for history UI).
 * @param {number} [currentCycleEnd]
 * @param {number} [asOf=Date.now()]
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
export function buildPsychologyCycleHistory(currentCycleEnd, asOf = Date.now()) {
  /** @type {ReturnType<typeof buildPsychologyCycleHistory>} */
  const cycles = [];

  for (let i = 0; i < BTC_HALVING_EVENTS.length; i++) {
    const halving = BTC_HALVING_EVENTS[i];
    const next = BTC_HALVING_EVENTS[i + 1];
    const end = next
      ? next.timestamp
      : (currentCycleEnd ?? halving.timestamp + CYCLE_LENGTH_DAYS * MS_PER_DAY);

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
      bands: bandsForHalvingWindow(halving.timestamp, end, halving.label, i + 1),
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
