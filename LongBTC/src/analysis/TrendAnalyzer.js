/**
 * Trend segment analysis from swing pivots.
 * @module analysis/TrendAnalyzer
 */

import { sidewaysThresholdPct as thresholdForTimeframe } from './SwingPivotDetector.js';

/**
 * @typedef {import('./SwingPivotDetector.js').SwingPivot} SwingPivot
 * @typedef {'uptrend'|'downtrend'|'sideways'} TrendDirection
 * @typedef {{
 *   startIndex: number,
 *   endIndex: number,
 *   startTime: number,
 *   endTime: number,
 *   startPrice: number,
 *   endPrice: number,
 *   direction: TrendDirection,
 *   changePct: number,
 *   durationBars: number,
 * }} TrendSegment
 */

/**
 * @param {string} timeframe
 * @returns {number}
 */
export function sidewaysThresholdPct(timeframe) {
  return thresholdForTimeframe(timeframe);
}

/**
 * Build trend segments between consecutive pivots.
 * @param {SwingPivot[]} pivots
 * @param {number} [thresholdPct=3]
 * @returns {TrendSegment[]}
 */
export function buildTrendSegments(pivots, thresholdPct = 3) {
  if (pivots.length < 2) return [];

  /** @type {TrendSegment[]} */
  const segments = [];

  for (let i = 1; i < pivots.length; i++) {
    const from = pivots[i - 1];
    const to = pivots[i];
    const changePct = ((to.price - from.price) / from.price) * 100;
    let direction = /** @type {TrendDirection} */ ('sideways');

    if (changePct > thresholdPct) direction = 'uptrend';
    else if (changePct < -thresholdPct) direction = 'downtrend';

    segments.push({
      startIndex: from.index,
      endIndex: to.index,
      startTime: from.timestamp,
      endTime: to.timestamp,
      startPrice: from.price,
      endPrice: to.price,
      direction,
      changePct,
      durationBars: to.index - from.index,
    });
  }

  return segments;
}

/**
 * Classify overall trend from recent pivot structure (HH/HL or LH/LL).
 * @param {SwingPivot[]} pivots
 * @returns {{ direction: TrendDirection, confidence: number, reason: string }}
 */
export function classifyOverallTrend(pivots) {
  const highs = pivots.filter((p) => p.type === 'high');
  const lows = pivots.filter((p) => p.type === 'low');

  if (highs.length < 2 || lows.length < 2) {
    return { direction: 'sideways', confidence: 30, reason: 'Ch\u01b0a \u0111\u1ee7 swing \u0111\u1ec3 x\u00e1c \u0111\u1ecbnh xu h\u01b0\u1edbng' };
  }

  const lastTwoHighs = highs.slice(-2);
  const lastTwoLows = lows.slice(-2);
  const hh = lastTwoHighs[1].price > lastTwoHighs[0].price;
  const hl = lastTwoLows[1].price > lastTwoLows[0].price;
  const lh = lastTwoHighs[1].price < lastTwoHighs[0].price;
  const ll = lastTwoLows[1].price < lastTwoLows[0].price;

  if (hh && hl) {
    return { direction: 'uptrend', confidence: 85, reason: 'Higher High + Higher Low \u2014 xu h\u01b0\u1edbng t\u0103ng' };
  }
  if (lh && ll) {
    return { direction: 'downtrend', confidence: 85, reason: 'Lower High + Lower Low \u2014 xu h\u01b0\u1edbng gi\u1ea3m' };
  }
  if (hh && ll) {
    return { direction: 'sideways', confidence: 60, reason: 'Ph\u00e2n k\u1ef3 HH/LL \u2014 \u0111i ngang / chuy\u1ec3n pha' };
  }
  if (lh && hl) {
    return { direction: 'sideways', confidence: 60, reason: 'Ph\u00e2n k\u1ef3 LH/HL \u2014 \u0111i ngang / t\u00edch l\u0169y' };
  }

  return { direction: 'sideways', confidence: 45, reason: 'C\u1ea5u tr\u00fac swing h\u1ed7n h\u1ee3p' };
}

/**
 * @param {TrendDirection} direction
 * @returns {string}
 */
export function trendLabelVi(direction) {
  const labels = { uptrend: 'T\u0103ng', downtrend: 'Gi\u1ea3m', sideways: '\u0110i ngang' };
  return labels[direction] ?? direction;
}
