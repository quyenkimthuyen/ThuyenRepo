/**
 * Suggest optimizer parameter grids from candle history (volatility heuristics).
 * @module optimizer/GridSuggestEngine
 */

import { getCandleRange } from '../strategy/helpers/CandlePatterns.js';
import { priceToPips } from '../utils/pip.js';
import { defaultGridForParam } from './ParameterGrid.js';

/** @typedef {import('../data/Candle.js').Candle} Candle */
/** @typedef {import('../strategy/ParameterSchema.js').ParamDefinition} ParamDefinition */

/** @typedef {'scalp'|'intraday'|'swing'|'position'} TimeframeScale */

/**
 * @typedef {Object} MarketStats
 * @property {number} avgRangePips - Mean candle range over 14-bar windows (pips)
 * @property {number} medianRangePips
 * @property {number} candleCount
 * @property {TimeframeScale} scale
 */

/**
 * @typedef {Object} GridSuggestion
 * @property {Record<string, string>} values - Grid strings per param key
 * @property {Record<string, boolean>} checks - Which params to include in grid
 * @property {MarketStats} stats
 * @property {string} message
 */

const RANGE_LOOKBACK = 14;

/** @type {Record<string, number>} */
const TF_MINUTES = {
  M1: 1,
  M5: 5,
  M15: 15,
  M30: 30,
  H1: 60,
  H2: 120,
  H4: 240,
  D1: 1440,
  W1: 10080,
};

/** Params to auto-check per strategy (max ~3 + keeps combos manageable). */
const STRATEGY_CHECK_KEYS = Object.freeze({
  'break-retest': ['breakoutPips', 'swingLookback', 'rr'],
  'ema-pullback': ['pullbackTolerancePips', 'rr'],
  'pin-bar-rejection': ['swingLookback', 'retestTolerancePips', 'rr'],
  'inside-bar-breakout': ['motherMinRangePips', 'breakoutBufferPips', 'rr'],
  'liquidity-grab': ['swingLookback', 'grabPips', 'rr'],
  'wyckoff-range-test': ['minRangePips', 'rangeLookback', 'rr'],
  'wyckoff-spring-utad': ['minRangePips', 'sweepPips', 'rr'],
});

/**
 * @param {string} timeframe
 * @returns {TimeframeScale}
 */
export function timeframeScale(timeframe) {
  const minutes = TF_MINUTES[timeframe] ?? 60;
  if (minutes <= 15) return 'scalp';
  if (minutes <= 60) return 'intraday';
  if (minutes <= 240) return 'swing';
  return 'position';
}

/**
 * @param {Candle[]} candles
 * @param {string} symbol
 * @returns {MarketStats}
 */
export function computeMarketStats(candles, symbol) {
  if (!candles.length) {
    return { avgRangePips: 10, medianRangePips: 10, candleCount: 0, scale: 'intraday' };
  }

  /** @type {number[]} */
  const windowAvgs = [];

  for (let i = RANGE_LOOKBACK - 1; i < candles.length; i++) {
    let sum = 0;
    for (let j = i - RANGE_LOOKBACK + 1; j <= i; j++) {
      sum += priceToPips(getCandleRange(candles[j]), symbol);
    }
    windowAvgs.push(sum / RANGE_LOOKBACK);
  }

  const sorted = [...windowAvgs].sort((a, b) => a - b);
  const avg = windowAvgs.reduce((s, v) => s + v, 0) / windowAvgs.length;
  const mid = sorted[Math.floor(sorted.length / 2)] ?? avg;

  return {
    avgRangePips: Math.max(1, avg),
    medianRangePips: Math.max(1, mid),
    candleCount: candles.length,
    scale: 'intraday',
  };
}

/**
 * @param {number} value
 * @param {ParamDefinition} def
 * @returns {number}
 */
function snapToStep(value, def) {
  const step = def.step ?? (def.type === 'integer' ? 1 : 0.5);
  if (def.type === 'integer') {
    return Math.round(value);
  }
  const snapped = Math.round(value / step) * step;
  return Number(snapped.toFixed(6));
}

/**
 * @param {number} value
 * @param {ParamDefinition} def
 * @returns {number}
 */
function clampToDef(value, def) {
  let v = value;
  if (def.min !== undefined) v = Math.max(def.min, v);
  if (def.max !== undefined) v = Math.min(def.max, v);
  return snapToStep(v, def);
}

/**
 * @param {number} low
 * @param {number} high
 * @param {number} step
 * @param {ParamDefinition} def
 * @returns {string}
 */
function formatRange(low, high, step, def) {
  const lo = clampToDef(low, def);
  const hi = clampToDef(high, def);
  const st = snapToStep(step, def);
  if (lo >= hi) {
    return defaultGridForParam(def).join(',');
  }
  return `${lo}:${hi}:${st}`;
}

/**
 * @param {TimeframeScale} scale
 * @param {ParamDefinition} def
 * @returns {[number, number, number]}
 */
function barRangeForScale(scale, def) {
  /** @type {Record<TimeframeScale, [number, number, number]>} */
  const presets = {
    scalp: {
      swingLookback: [8, 15, 2],
      rangeLookback: [12, 24, 4],
      retestMaxBars: [5, 15, 2],
      testMaxBars: [5, 15, 2],
      maxWaitBars: [2, 6, 1],
      trendBars: [8, 12, 2],
    },
    intraday: {
      swingLookback: [5, 10, 1],
      rangeLookback: [8, 16, 2],
      retestMaxBars: [8, 20, 2],
      testMaxBars: [8, 20, 2],
      maxWaitBars: [2, 5, 1],
      trendBars: [5, 10, 1],
    },
    swing: {
      swingLookback: [4, 8, 1],
      rangeLookback: [6, 12, 2],
      retestMaxBars: [10, 25, 3],
      testMaxBars: [10, 25, 3],
      maxWaitBars: [3, 8, 1],
      trendBars: [5, 8, 1],
    },
    position: {
      swingLookback: [3, 7, 1],
      rangeLookback: [5, 10, 1],
      retestMaxBars: [10, 30, 5],
      testMaxBars: [10, 30, 5],
      maxWaitBars: [3, 10, 1],
      trendBars: [3, 8, 1],
    },
  };

  const table = presets[scale];
  const row = table[/** @type {keyof typeof table.scalp} */ (def.key)];
  if (!row) return [def.default, def.default, def.step ?? 1];
  return row;
}

/**
 * @param {ParamDefinition} def
 * @param {MarketStats} stats
 * @param {string} key
 * @returns {string|null} null = use default grid fallback
 */
export function suggestGridString(def, stats, key = def.key) {
  const R = stats.avgRangePips;
  const scale = stats.scale;

  /** @type {Record<string, () => string>} */
  const handlers = {
    breakoutPips: () => formatRange(0.3 * R, 1.0 * R, 1, def),
    breakoutBufferPips: () => formatRange(0.1 * R, 0.4 * R, 0.5, def),
    pullbackTolerancePips: () => formatRange(0.15 * R, 0.4 * R, 0.5, def),
    retestTolerancePips: () => formatRange(0.15 * R, 0.4 * R, 0.5, def),
    testTolerancePips: () => formatRange(0.15 * R, 0.4 * R, 0.5, def),
    motherMinRangePips: () => formatRange(0.5 * R, 1.5 * R, 1, def),
    minRangePips: () => formatRange(0.8 * R, 2.0 * R, 1, def),
    grabPips: () => formatRange(0.2 * R, 0.6 * R, 0.5, def),
    sweepPips: () => formatRange(0.2 * R, 0.8 * R, 0.5, def),
    rallyMinPips: () => formatRange(0.5 * R, 1.5 * R, 1, def),
    rr: () => formatRange(1.5, 3, 0.5, def),
    swingLookback: () => {
      const [lo, hi, step] = barRangeForScale(scale, def);
      return formatRange(lo, hi, step, def);
    },
    rangeLookback: () => {
      const [lo, hi, step] = barRangeForScale(scale, def);
      return formatRange(lo, hi, step, def);
    },
    retestMaxBars: () => {
      const [lo, hi, step] = barRangeForScale(scale, def);
      return formatRange(lo, hi, step, def);
    },
    testMaxBars: () => {
      const [lo, hi, step] = barRangeForScale(scale, def);
      return formatRange(lo, hi, step, def);
    },
    maxWaitBars: () => {
      const [lo, hi, step] = barRangeForScale(scale, def);
      return formatRange(lo, hi, step, def);
    },
    trendBars: () => {
      const [lo, hi, step] = barRangeForScale(scale, def);
      return formatRange(lo, hi, step, def);
    },
  };

  const handler = handlers[key];
  if (!handler) return null;
  return handler();
}

/**
 * Build grid value strings and checkbox state for a strategy schema.
 * @param {string} strategyId
 * @param {ParamDefinition[]} schema
 * @param {Candle[]} candles
 * @param {string} symbol
 * @param {string} timeframe
 * @returns {GridSuggestion}
 */
export function suggestParamGridFromData(strategyId, schema, candles, symbol, timeframe) {
  const stats = computeMarketStats(candles, symbol);
  stats.scale = timeframeScale(timeframe);

  /** @type {Record<string, string>} */
  const values = {};
  /** @type {Record<string, boolean>} */
  const checks = {};

  const numericSchema = schema.filter((d) => d.type === 'number' || d.type === 'integer');
  const checkKeys = STRATEGY_CHECK_KEYS[strategyId] ?? ['rr'];

  for (const def of numericSchema) {
    const suggested = suggestGridString(def, stats, def.key);
    values[def.key] = suggested ?? defaultGridForParam(def).join(',');
    checks[def.key] = checkKeys.includes(def.key);
  }

  const message = stats.candleCount === 0
    ? 'Không có n?n — dùng grid m?c ??nh.'
    : `G?i ý t? ${stats.candleCount.toLocaleString()} n?n · avg range ${stats.avgRangePips.toFixed(1)} pips (${stats.scale})`;

  return { values, checks, stats, message };
}
