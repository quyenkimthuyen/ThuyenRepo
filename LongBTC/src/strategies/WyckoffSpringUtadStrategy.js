/**
 * Wyckoff Spring / UTAD — false break of a trading range with rejection.
 * @module strategies/WyckoffSpringUtadStrategy
 */

import { BaseStrategy } from '../strategy/BaseStrategy.js';
import { createSignal } from '../strategy/Signal.js';
import { pipsToPrice, formatPrice, priceToPips } from '../utils/pip.js';
import { getWicks } from '../strategy/helpers/CandlePatterns.js';
import {
  buildLongLevels,
  buildShortLevels,
  slBufferBelow,
  slBufferAbove,
} from '../strategy/helpers/TradeLevels.js';
import { computeConfidence } from '../strategy/helpers/ConfidenceScore.js';
import {
  getTradingRange,
  rangeWidthPips,
  isConsolidationRange,
  isWyckoffSpring,
  isWyckoffUtad,
} from '../strategy/helpers/WyckoffRange.js';

/**
 * @typedef {Object} RangeSignalRecord
 * @property {number} level
 * @property {'long'|'short'} direction
 * @property {number} barIndex
 */

/**
 * Enters on spring (accumulation) or UTAD (distribution) at range boundaries.
 */
export class WyckoffSpringUtadStrategy extends BaseStrategy {
  static id = 'wyckoff-spring-utad';
  static name = 'Wyckoff Spring / UTAD';
  static description = 'Trade Wyckoff spring and UTAD false breaks from a consolidation range.';
  static version = '1.0.0';
  static category = 'Wyckoff';

  getParameterSchema() {
    return [
      {
        key: 'rangeLookback',
        label: 'Range Lookback',
        type: 'integer',
        default: 20,
        min: 10,
        max: 60,
        description: 'Bars used to define the trading range',
      },
      {
        key: 'minRangePips',
        label: 'Min Range (pips)',
        type: 'number',
        default: 15,
        min: 5,
        max: 80,
        step: 1,
        description: 'Minimum range height to qualify as consolidation',
      },
      {
        key: 'minInsideRatio',
        label: 'Min Inside Ratio',
        type: 'number',
        default: 0.65,
        min: 0.4,
        max: 0.95,
        step: 0.05,
        description: 'Share of closes inside range before the event',
      },
      {
        key: 'sweepPips',
        label: 'Sweep (pips)',
        type: 'number',
        default: 2,
        min: 1,
        max: 20,
        step: 0.5,
        description: 'Minimum breach beyond range boundary',
      },
      {
        key: 'wickRatio',
        label: 'Min Wick Ratio',
        type: 'number',
        default: 0.55,
        min: 0.35,
        max: 0.85,
        step: 0.05,
      },
      {
        key: 'rr',
        label: 'Risk Reward',
        type: 'number',
        default: 2,
        min: 1,
        max: 10,
        step: 0.5,
      },
    ];
  }

  getWarmupBars() {
    return Number(this._getParam('rangeLookback') ?? 20) + 5;
  }

  onInitialize() {
    this._setState('recentLevels', []);
    this._setState('rangeHigh', null);
    this._setState('rangeLow', null);
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   */
  calculate(candles, index) {
    const lookback = Number(this._getParam('rangeLookback'));
    const range = getTradingRange(candles, index, lookback);
    if (range) {
      this._setState('rangeHigh', range.rangeHigh);
      this._setState('rangeLow', range.rangeLow);
    }

    /** @type {RangeSignalRecord[]} */
    let recent = this._getState('recentLevels') ?? [];
    recent = recent.filter((r) => index - r.barIndex <= lookback * 2);
    this._setState('recentLevels', recent);
  }

  /**
   * @param {import('../strategy/StrategyContext.js').StrategyContext} ctx
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  generateSignal(ctx) {
    const { index, candles, symbol, timeframe } = ctx;
    const lookback = Number(this._getParam('rangeLookback'));
    const minRangePips = Number(this._getParam('minRangePips'));
    const minInsideRatio = Number(this._getParam('minInsideRatio'));
    const sweepPips = Number(this._getParam('sweepPips'));
    const minWickRatio = Number(this._getParam('wickRatio'));
    const rr = Number(this._getParam('rr'));
    const pip = pipsToPrice(1, symbol);

    const rangeHigh = /** @type {number|null} */ (this._getState('rangeHigh'));
    const rangeLow = /** @type {number|null} */ (this._getState('rangeLow'));
    const candle = candles[index];

    if (index < lookback || rangeHigh === null || rangeLow === null) return null;
    if (rangeWidthPips(rangeHigh, rangeLow, symbol) < minRangePips) return null;
    if (!isConsolidationRange(candles, index, lookback, rangeHigh, rangeLow, minInsideRatio)) {
      return null;
    }

    const shortSignal = this.#checkUtad(
      candle, rangeHigh, sweepPips, pip, minWickRatio, symbol, rr, index, timeframe
    );
    if (shortSignal) {
      this.#recordLevel(rangeHigh, 'short', index);
      return shortSignal;
    }

    const longSignal = this.#checkSpring(
      candle, rangeLow, sweepPips, pip, minWickRatio, symbol, rr, index, timeframe
    );
    if (longSignal) {
      this.#recordLevel(rangeLow, 'long', index);
      return longSignal;
    }

    return null;
  }

  /**
   * @param {import('../data/Candle.js').Candle} candle
   * @param {number} rangeHigh
   * @param {number} sweepPips
   * @param {number} pip
   * @param {number} minWickRatio
   * @param {string} symbol
   * @param {number} rr
   * @param {number} index
   * @param {string} timeframe
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  #checkUtad(candle, rangeHigh, sweepPips, pip, minWickRatio, symbol, rr, index, timeframe) {
    if (this.#isDuplicateLevel(rangeHigh, 'short', index, symbol)) return null;
    if (!isWyckoffUtad(candle, rangeHigh, sweepPips, pip, minWickRatio, symbol)) return null;

    const wicks = getWicks(candle);
    const levels = buildShortLevels(
      candle.close,
      slBufferAbove(candle.high, symbol),
      rr
    );

    const confidence = computeConfidence(candle.timestamp, rr, {
      qualityWick: wicks.upper / wicks.range >= 0.7,
      preciseLocation: priceToPips(rangeHigh - candle.close, symbol) <= 3,
      extraPoints:
        (wicks.upper / wicks.range >= 0.7 ? 15 : 0) +
        (priceToPips(candle.high - rangeHigh, symbol) >= sweepPips ? 10 : 0),
    });

    return createSignal({
      time: candle.timestamp,
      pair: symbol,
      timeframe,
      direction: 'short',
      entry: levels.entry,
      sl: levels.sl,
      tp: levels.tp,
      rr,
      confidence,
      reason: `Wyckoff UTAD: swept ${formatPrice(rangeHigh, symbol)}, rejected bar ${index}`,
      screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
      strategyId: WyckoffSpringUtadStrategy.id,
      setup: {
        levels: [
          { kind: 'break-level', label: 'Range high', price: rangeHigh },
        ],
        markers: [{ label: 'UTAD', time: candle.timestamp, role: 'sweep' }],
        steps: [
          '1. Gia trong range tich luy',
          '2. Quet tren range high (UTAD)',
          '3. Dong lai trong range ? SHORT',
        ],
      },
    });
  }

  /**
   * @param {import('../data/Candle.js').Candle} candle
   * @param {number} rangeLow
   * @param {number} sweepPips
   * @param {number} pip
   * @param {number} minWickRatio
   * @param {string} symbol
   * @param {number} rr
   * @param {number} index
   * @param {string} timeframe
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  #checkSpring(candle, rangeLow, sweepPips, pip, minWickRatio, symbol, rr, index, timeframe) {
    if (this.#isDuplicateLevel(rangeLow, 'long', index, symbol)) return null;
    if (!isWyckoffSpring(candle, rangeLow, sweepPips, pip, minWickRatio, symbol)) return null;

    const wicks = getWicks(candle);
    const levels = buildLongLevels(
      candle.close,
      slBufferBelow(candle.low, symbol),
      rr
    );

    const confidence = computeConfidence(candle.timestamp, rr, {
      qualityWick: wicks.lower / wicks.range >= 0.7,
      preciseLocation: priceToPips(candle.close - rangeLow, symbol) <= 3,
      extraPoints:
        (wicks.lower / wicks.range >= 0.7 ? 15 : 0) +
        (priceToPips(rangeLow - candle.low, symbol) >= sweepPips ? 10 : 0),
    });

    return createSignal({
      time: candle.timestamp,
      pair: symbol,
      timeframe,
      direction: 'long',
      entry: levels.entry,
      sl: levels.sl,
      tp: levels.tp,
      rr,
      confidence,
      reason: `Wyckoff spring: swept ${formatPrice(rangeLow, symbol)}, rejected bar ${index}`,
      screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
      strategyId: WyckoffSpringUtadStrategy.id,
      setup: {
        levels: [
          { kind: 'break-level', label: 'Range low', price: rangeLow },
        ],
        markers: [{ label: 'Spring', time: candle.timestamp, role: 'sweep' }],
        steps: [
          '1. Gia trong range tich luy',
          '2. Quet duoi range low (spring)',
          '3. Dong lai trong range ? LONG',
        ],
      },
    });
  }

  /**
   * @param {number} level
   * @param {'long'|'short'} direction
   * @param {number} barIndex
   */
  #recordLevel(level, direction, barIndex) {
    const recent = this._getState('recentLevels') ?? [];
    recent.push({ level, direction, barIndex });
    this._setState('recentLevels', recent);
  }

  /**
   * @param {number} level
   * @param {'long'|'short'} direction
   * @param {number} index
   * @param {string} symbol
   * @returns {boolean}
   */
  #isDuplicateLevel(level, direction, index, symbol) {
    const lookback = Number(this._getParam('rangeLookback'));
    /** @type {RangeSignalRecord[]} */
    const recent = this._getState('recentLevels') ?? [];

    return recent.some(
      (r) =>
        r.direction === direction &&
        Math.abs(r.level - level) < pipsToPrice(1, symbol) &&
        index - r.barIndex <= lookback * 2
    );
  }
}
