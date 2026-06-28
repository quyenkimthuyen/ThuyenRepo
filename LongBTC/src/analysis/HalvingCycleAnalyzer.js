/**
 * Bitcoin 4-year halving cycle analysis.
 * @module analysis/HalvingCycleAnalyzer
 */

import {
  BTC_HALVING_EVENTS,
  CYCLE_LENGTH_DAYS,
  CYCLE_PHASE_RANGES,
  halvingIndexAt,
  phaseFromProgress,
} from './BtcCycleConfig.js';

/**
 * @typedef {import('../data/Candle.js').Candle} Candle
 * @typedef {import('./BtcCycleConfig.js').CyclePhase} CyclePhase
 * @typedef {{
 *   halvingIndex: number,
 *   halvingLabel: string,
 *   halvingTime: number,
 *   nextHalvingEstimate: number,
 *   progressPct: number,
 *   phase: CyclePhase,
 *   phaseLabel: string,
 *   phaseColor: string,
 *   daysSinceHalving: number,
 *   daysToNextHalving: number,
 * }} CurrentCycleState
 * @typedef {{
 *   cycleIndex: number,
 *   halving: typeof BTC_HALVING_EVENTS[number],
 *   startTime: number,
 *   endTime: number,
 *   startPrice: number,
 *   endPrice: number,
 *   lowPrice: number,
 *   highPrice: number,
 *   changePct: number,
 *   phases: Array<{ phase: CyclePhase, startTime: number, endTime: number }>,
 * }} HistoricalCycle
 */

const MS_PER_DAY = 24 * 60 * 60 * 1000;

/**
 * Analyze current position in the 4-year halving cycle.
 * @param {number} [now=Date.now()]
 * @returns {CurrentCycleState}
 */
export function analyzeCurrentCycle(now = Date.now()) {
  const idx = halvingIndexAt(now);
  const halving = BTC_HALVING_EVENTS[idx];
  const nextEstimate = halving.timestamp + CYCLE_LENGTH_DAYS * MS_PER_DAY;
  const daysSince = (now - halving.timestamp) / MS_PER_DAY;
  const daysToNext = Math.max(0, (nextEstimate - now) / MS_PER_DAY);
  const progress = Math.min(1, daysSince / CYCLE_LENGTH_DAYS);
  const phase = phaseFromProgress(progress);
  const range = CYCLE_PHASE_RANGES[phase];

  return {
    halvingIndex: idx,
    halvingLabel: halving.label,
    halvingTime: halving.timestamp,
    nextHalvingEstimate: nextEstimate,
    progressPct: progress * 100,
    phase,
    phaseLabel: range.label,
    phaseColor: range.color,
    daysSinceHalving: Math.round(daysSince),
    daysToNextHalving: Math.round(daysToNext),
  };
}

/**
 * Build historical cycle records from candle data.
 * @param {Candle[]} candles
 * @returns {HistoricalCycle[]}
 */
export function buildHistoricalCycles(candles) {
  if (candles.length === 0) return [];

  /** @type {HistoricalCycle[]} */
  const cycles = [];

  for (let i = 0; i < BTC_HALVING_EVENTS.length; i++) {
    const halving = BTC_HALVING_EVENTS[i];
    const nextHalving = BTC_HALVING_EVENTS[i + 1];
    const startTime = halving.timestamp;
    const endTime = nextHalving
      ? nextHalving.timestamp
      : halving.timestamp + CYCLE_LENGTH_DAYS * MS_PER_DAY;

    const slice = candles.filter((c) => c.timestamp >= startTime && c.timestamp < endTime);
    if (slice.length === 0) continue;

    const startPrice = slice[0].open;
    const endPrice = slice[slice.length - 1].close;
    let lowPrice = Infinity;
    let highPrice = -Infinity;
    for (const c of slice) {
      lowPrice = Math.min(lowPrice, c.low);
      highPrice = Math.max(highPrice, c.high);
    }

    /** @type {HistoricalCycle['phases']} */
    const phases = [];
    for (const [phaseKey, range] of Object.entries(CYCLE_PHASE_RANGES)) {
      phases.push({
        phase: /** @type {CyclePhase} */ (phaseKey),
        startTime: startTime + range.start * CYCLE_LENGTH_DAYS * MS_PER_DAY,
        endTime: startTime + range.end * CYCLE_LENGTH_DAYS * MS_PER_DAY,
      });
    }

    cycles.push({
      cycleIndex: i + 1,
      halving,
      startTime,
      endTime,
      startPrice,
      endPrice,
      lowPrice,
      highPrice,
      changePct: ((endPrice - startPrice) / startPrice) * 100,
      phases,
    });
  }

  return cycles;
}

/**
 * Find cycle low and high within current cycle from candles.
 * @param {Candle[]} candles
 * @param {CurrentCycleState} current
 * @returns {{ cycleLow: number|null, cycleHigh: number|null, drawdownFromHighPct: number|null }}
 */
export function cycleExtremes(candles, current) {
  const slice = candles.filter((c) => c.timestamp >= current.halvingTime);
  if (slice.length === 0) {
    return { cycleLow: null, cycleHigh: null, drawdownFromHighPct: null };
  }

  let low = Infinity;
  let high = -Infinity;
  for (const c of slice) {
    low = Math.min(low, c.low);
    high = Math.max(high, c.high);
  }

  const lastClose = slice[slice.length - 1].close;
  const drawdown = high > 0 ? ((lastClose - high) / high) * 100 : null;

  return { cycleLow: low, cycleHigh: high, drawdownFromHighPct: drawdown };
}
