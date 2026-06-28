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
 * Detect swing pivots using percentage reversal threshold.
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

  const startPrice = candles[0].close;
  /** @type {'high'|'low'} */
  let seeking = candles[candles.length - 1].close >= startPrice ? 'high' : 'low';

  let extremeIdx = 0;
  let extremePrice = seeking === 'high' ? candles[0].high : candles[0].low;

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
 * Adaptive reversal threshold based on timeframe bar count.
 * @param {string} timeframe
 * @returns {number}
 */
export function defaultReversalPct(timeframe) {
  const map = { W: 0.12, D1: 0.08, H4: 0.05, H1: 0.03 };
  return map[timeframe] ?? 0.10;
}
