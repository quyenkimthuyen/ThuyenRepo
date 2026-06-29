/**
 * Halving-calendar psychology bands for a time range.
 * @module analysis/PsychologyBands
 */

import { BTC_HALVING_EVENTS, CYCLE_LENGTH_DAYS } from './BtcCycleConfig.js';
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

/**
 * @param {number} halvingStartMs
 * @param {number} halvingEndMs
 * @param {string} halvingLabel
 * @param {number} cycleIndex
 * @returns {PsychologyBand[]}
 */
function bandsForHalvingWindow(halvingStartMs, halvingEndMs, halvingLabel, cycleIndex) {
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

    bands.push(...bandsForHalvingWindow(halving.timestamp, end, halving.label, i + 1));
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
