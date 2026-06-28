/**
 * Trend segment analysis from swing pivots.
 * @module analysis/TrendAnalyzer
 */

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
 * Build trend segments between consecutive pivots.
 * @param {SwingPivot[]} pivots
 * @param {number} [sidewaysThresholdPct=3]
 * @returns {TrendSegment[]}
 */
export function buildTrendSegments(pivots, sidewaysThresholdPct = 3) {
  if (pivots.length < 2) return [];

  /** @type {TrendSegment[]} */
  const segments = [];

  for (let i = 1; i < pivots.length; i++) {
    const from = pivots[i - 1];
    const to = pivots[i];
    const changePct = ((to.price - from.price) / from.price) * 100;
    let direction = /** @type {TrendDirection} */ ('sideways');

    if (changePct > sidewaysThresholdPct) direction = 'uptrend';
    else if (changePct < -sidewaysThresholdPct) direction = 'downtrend';

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
    return { direction: 'sideways', confidence: 30, reason: 'Ch?a ?? swing ?? xác ??nh xu h??ng' };
  }

  const lastTwoHighs = highs.slice(-2);
  const lastTwoLows = lows.slice(-2);
  const hh = lastTwoHighs[1].price > lastTwoHighs[0].price;
  const hl = lastTwoLows[1].price > lastTwoLows[0].price;
  const lh = lastTwoHighs[1].price < lastTwoHighs[0].price;
  const ll = lastTwoLows[1].price < lastTwoLows[0].price;

  if (hh && hl) {
    return { direction: 'uptrend', confidence: 85, reason: 'Higher High + Higher Low — xu h??ng t?ng' };
  }
  if (lh && ll) {
    return { direction: 'downtrend', confidence: 85, reason: 'Lower High + Lower Low — xu h??ng gi?m' };
  }
  if (hh && ll) {
    return { direction: 'sideways', confidence: 60, reason: 'Phân k? HH/LL — ?i ngang / chuy?n pha' };
  }
  if (lh && hl) {
    return { direction: 'sideways', confidence: 60, reason: 'Phân k? LH/HL — ?i ngang / tích l?y' };
  }

  return { direction: 'sideways', confidence: 45, reason: 'C?u trúc swing h?n h?p' };
}

/**
 * @param {TrendDirection} direction
 * @returns {string}
 */
export function trendLabelVi(direction) {
  const labels = { uptrend: 'T?ng', downtrend: 'Gi?m', sideways: '?i ngang' };
  return labels[direction] ?? direction;
}
