/**
 * Compare halving-cycle progress across historical and current cycles.
 * @module analysis/CycleCompareTimeline
 */

import { BTC_HALVING_EVENTS, CYCLE_LENGTH_DAYS } from './BtcCycleConfig.js';
import { analyzeCurrentCycle } from './HalvingCycleAnalyzer.js';

const MS_PER_DAY = 24 * 60 * 60 * 1000;

/**
 * @typedef {{
 *   cycleIndex: number,
 *   halvingLabel: string,
 *   startYear: number,
 *   endYear: number|null,
 *   startTime: number,
 *   endTime: number,
 *   progressPct: number,
 *   isCurrent: boolean,
 *   isComplete: boolean,
 *   compareMarkerPct: number,
 *   phaseLabel: string,
 *   phaseColor: string,
 * }} CycleCompareRow
 */

/**
 * Progress through halving N ? N+1 (0–100). Uses actual next halving date when known.
 * @param {number} halvingIndex
 * @param {number} atMs
 * @returns {{ progressPct: number, endTime: number }}
 */
function cycleProgressAt(halvingIndex, atMs) {
  const halving = BTC_HALVING_EVENTS[halvingIndex];
  const next = BTC_HALVING_EVENTS[halvingIndex + 1];
  const endTime = next
    ? next.timestamp
    : halving.timestamp + CYCLE_LENGTH_DAYS * MS_PER_DAY;
  const span = endTime - halving.timestamp;
  if (span <= 0) return { progressPct: 0, endTime };

  const elapsed = Math.max(0, Math.min(span, atMs - halving.timestamp));
  return {
    progressPct: (elapsed / span) * 100,
    endTime,
  };
}

/**
 * Four comparison rows: 2012 baseline + halving cycles 2016, 2020, 2024 (current).
 * @param {number} [now=Date.now()]
 * @returns {{ currentProgressPct: number, currentPhaseLabel: string, currentHalvingLabel: string, rows: CycleCompareRow[] }}
 */
export function buildHalvingCycleCompare(now = Date.now()) {
  const current = analyzeCurrentCycle(now);
  const markerPct = current.progressPct;

  /** Halving starts: 2016(1), 2020(2), 2024(3) — 3 chu k? + chu k? hi?n t?i */
  const compareIndices = [1, 2, 3];

  /** @type {CycleCompareRow[]} */
  const rows = [];

  for (const i of compareIndices) {
    const halving = BTC_HALVING_EVENTS[i];
    const next = BTC_HALVING_EVENTS[i + 1];
    const isCurrent = i === current.halvingIndex;
    const endMs = next?.timestamp ?? halving.timestamp + CYCLE_LENGTH_DAYS * MS_PER_DAY;
    const { progressPct, endTime } = cycleProgressAt(i, isCurrent ? now : endMs);
    const progress = isCurrent ? progressPct : 100;

    rows.push({
      cycleIndex: i + 1,
      halvingLabel: halving.label,
      startYear: new Date(halving.timestamp).getUTCFullYear(),
      endYear: next ? new Date(next.timestamp).getUTCFullYear() : new Date(endTime).getUTCFullYear(),
      startTime: halving.timestamp,
      endTime,
      progressPct: progress,
      isCurrent,
      isComplete: !isCurrent,
      compareMarkerPct: markerPct,
      phaseLabel: isCurrent ? current.phaseLabel : 'Ho\u00e0n th\u00e0nh',
      phaseColor: isCurrent ? current.phaseColor : '#64748b',
    });
  }

  return {
    currentProgressPct: markerPct,
    currentPhaseLabel: current.phaseLabel,
    currentHalvingLabel: current.halvingLabel,
    rows,
    /** 4th visual: phase segments 0–100% with current marker */
    phaseRuler: {
      markerPct,
      phaseLabel: current.phaseLabel,
      phaseColor: current.phaseColor,
    },
  };
}
