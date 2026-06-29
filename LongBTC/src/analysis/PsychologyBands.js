/**
 * Halving-calendar psychology bands for a time range.
 * @module analysis/PsychologyBands
 */

import { BTC_HALVING_EVENTS, CYCLE_LENGTH_DAYS, CYCLE_PHASE_RANGES } from './BtcCycleConfig.js';
import { buildPsychologyTimeline } from './PsychologyCycleMapper.js';

/**
 * @typedef {{
 *   phase: { id: string, labelVi: string, label: string, color: string },
 *   startTime: number,
 *   endTime: number,
 *   halvingLabel: string,
 *   cycleIndex: number,
 * }} PsychologyBand
 */

const MS_PER_DAY = 24 * 60 * 60 * 1000;

const ACCUMULATION_PHASE = {
  id: 'accumulation',
  label: 'Accumulation',
  labelVi: 'T\u00edch l\u0169y',
  color: CYCLE_PHASE_RANGES.accumulation.color,
};

/**
 * Non-overlapping psychology windows across one halving cycle (sequential display).
 * @returns {Array<{ phase: { id: string, labelVi: string, label: string, color: string }, startPct: number, endPct: number }>}
 */
export function buildSequentialPsychologyTimeline() {
  const sorted = [...buildPsychologyTimeline()]
    .filter((item) => item.endPct > item.startPct)
    .sort((a, b) => a.startPct - b.startPct || a.endPct - b.endPct);

  /** @type {ReturnType<typeof buildSequentialPsychologyTimeline>} */
  const windows = [];

  const firstStart = sorted[0]?.startPct ?? 20;
  if (firstStart > 0) {
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
 * @param {number} halvingStartMs
 * @param {number} halvingEndMs
 * @param {string} halvingLabel
 * @param {number} cycleIndex
 * @param {boolean} [sequential=false]
 * @returns {PsychologyBand[]}
 */
function bandsForHalvingWindow(halvingStartMs, halvingEndMs, halvingLabel, cycleIndex, sequential = false) {
  const span = halvingEndMs - halvingStartMs;
  if (span <= 0) return [];

  const timeline = sequential
    ? buildSequentialPsychologyTimeline()
    : buildPsychologyTimeline().filter((item) => item.endPct > item.startPct);

  return timeline.map((item) => ({
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
