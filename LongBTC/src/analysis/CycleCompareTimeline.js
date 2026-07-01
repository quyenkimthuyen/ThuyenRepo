/**
 * Compare halving-cycle progress across historical and current cycles.
 * @module analysis/CycleCompareTimeline
 */

import { BTC_HALVING_EVENTS, CYCLE_LENGTH_DAYS } from './BtcCycleConfig.js';
import { analyzeCurrentCycle } from './HalvingCycleAnalyzer.js';

const MS_PER_DAY = 24 * 60 * 60 * 1000;

/**
 * @typedef {import('../data/Candle.js').Candle} Candle
 * @typedef {{
 *   markerTime: number,
 *   price: number,
 *   pctFromCycleStart: number,
 *   pctFromCycleLow: number,
 *   pctFromCycleHigh: number,
 * }} CycleMarkerPrice
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
 *   markerPrice: CycleMarkerPrice|null,
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
 * Price context at a given % through halving N ? N+1.
 * @param {Candle[]} candles
 * @param {number} halvingIndex
 * @param {number} progressPct — 0–100
 * @param {number} [atMs] — for current cycle, use actual now
 * @returns {CycleMarkerPrice|null}
 */
export function snapshotAtCycleProgress(candles, halvingIndex, progressPct, atMs) {
  if (!candles.length) return null;

  const halving = BTC_HALVING_EVENTS[halvingIndex];
  const next = BTC_HALVING_EVENTS[halvingIndex + 1];
  const endTime = next
    ? next.timestamp
    : halving.timestamp + CYCLE_LENGTH_DAYS * MS_PER_DAY;
  const markerTime = atMs != null
    ? atMs
    : halving.timestamp + (progressPct / 100) * (endTime - halving.timestamp);

  const slice = candles.filter(
    (c) => c.timestamp >= halving.timestamp && c.timestamp <= markerTime
  );
  if (slice.length === 0) return null;

  const candle = slice[slice.length - 1];
  const cycleStart = candles.find((c) => c.timestamp >= halving.timestamp);
  const startPrice = cycleStart?.open ?? slice[0].open;

  let low = Infinity;
  let high = -Infinity;
  for (const c of slice) {
    low = Math.min(low, c.low);
    high = Math.max(high, c.high);
  }

  return {
    markerTime: candle.timestamp,
    price: candle.close,
    pctFromCycleStart: startPrice > 0 ? ((candle.close - startPrice) / startPrice) * 100 : 0,
    pctFromCycleLow: low > 0 && low !== Infinity ? ((candle.close - low) / low) * 100 : 0,
    pctFromCycleHigh: high > 0 ? ((candle.close - high) / high) * 100 : 0,
  };
}

/**
 * Halving cycles 2016, 2020, 2024 + price at shared progress marker.
 * @param {Candle[]} [candles]
 * @param {number} [now=Date.now()]
 */
export function buildHalvingCycleCompare(candles = [], now = Date.now()) {
  const current = analyzeCurrentCycle(now);
  const markerPct = current.progressPct;
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

    const markerPrice = candles.length > 0
      ? snapshotAtCycleProgress(
        candles,
        i,
        markerPct,
        isCurrent ? now : undefined
      )
      : null;

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
      markerPrice,
    });
  }

  return {
    currentProgressPct: markerPct,
    currentPhaseLabel: current.phaseLabel,
    currentHalvingLabel: current.halvingLabel,
    rows,
    phaseRuler: {
      markerPct,
      phaseLabel: current.phaseLabel,
      phaseColor: current.phaseColor,
    },
  };
}
