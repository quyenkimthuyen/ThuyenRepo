/**
 * Zigzag swing pivot detection for long-term BTC structure.
 * @module analysis/SwingPivotDetector
 */

/**
 * @typedef {import('../data/Candle.js').Candle} Candle
 * @typedef {'high'|'low'} PivotType
 * @typedef {{ index: number, timestamp: number, price: number, type: PivotType }} SwingPivot
 */

/**
 * Detect swing pivots using percentage reversal threshold (classic zigzag).
 * @param {Candle[]} candles
 * @param {{ reversalPct?: number, minBars?: number }} [options]
 * @returns {SwingPivot[]}
 */
export function detectSwingPivots(candles, options = {}) {
  const reversalPct = options.reversalPct ?? 0.15;
  const minBars = options.minBars ?? 2;

  if (candles.length < minBars + 2) return [];

  /** @type {SwingPivot[]} */
  const pivots = [];

  let extremeIdx = 0;
  let extremePrice = candles[0].high;
  /** @type {'high'|'low'} */
  let seeking = 'high';

  for (let i = 1; i < candles.length; i++) {
    const c = candles[i];

    if (seeking === 'high') {
      if (c.high >= extremePrice) {
        extremePrice = c.high;
        extremeIdx = i;
      }
      const drop = (extremePrice - c.low) / extremePrice;
      if (drop >= reversalPct && i - extremeIdx >= minBars) {
        pivots.push({
          index: extremeIdx,
          timestamp: candles[extremeIdx].timestamp,
          price: extremePrice,
          type: 'high',
        });
        seeking = 'low';
        extremeIdx = i;
        extremePrice = c.low;
      }
    } else {
      if (c.low <= extremePrice) {
        extremePrice = c.low;
        extremeIdx = i;
      }
      const rise = (c.high - extremePrice) / extremePrice;
      if (rise >= reversalPct && i - extremeIdx >= minBars) {
        pivots.push({
          index: extremeIdx,
          timestamp: candles[extremeIdx].timestamp,
          price: extremePrice,
          type: 'low',
        });
        seeking = 'high';
        extremeIdx = i;
        extremePrice = c.high;
      }
    }
  }

  const finalType = seeking;
  if (pivots.length === 0 || pivots[pivots.length - 1].type !== finalType) {
    pivots.push({
      index: extremeIdx,
      timestamp: candles[extremeIdx].timestamp,
      price: extremePrice,
      type: finalType,
    });
  }

  return pivots;
}

/**
 * Adaptive reversal threshold based on timeframe.
 * @param {string} timeframe
 * @returns {number}
 */
export function defaultReversalPct(timeframe) {
  const map = { W: 0.18, D1: 0.12, H4: 0.08, H1: 0.05 };
  return map[timeframe] ?? 0.10;
}

/**
 * Minimum bars between pivots per timeframe.
 * @param {string} timeframe
 * @returns {number}
 */
export function defaultMinBars(timeframe) {
  const map = { W: 1, D1: 2, H4: 4, H1: 6 };
  return map[timeframe] ?? 2;
}

/**
 * Combined swing detection options for a timeframe.
 * @param {string} timeframe
 * @returns {{ reversalPct: number, minBars: number }}
 */
export function defaultSwingOptions(timeframe) {
  return {
    reversalPct: defaultReversalPct(timeframe),
    minBars: defaultMinBars(timeframe),
  };
}

/**
 * Sideways segment threshold (%) by timeframe.
 * @param {string} timeframe
 * @returns {number}
 */
export function sidewaysThresholdPct(timeframe) {
  const map = { W: 10, D1: 6, H4: 3, H1: 1.5 };
  return map[timeframe] ?? 3;
}
