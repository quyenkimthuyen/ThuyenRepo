/**
 * Wyckoff Range Test — entry on secondary test after spring or UTAD.
 * @module strategies/WyckoffRangeTestStrategy
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
  isWyckoffSpringTest,
  isWyckoffUtadTest,
} from '../strategy/helpers/WyckoffRange.js';

/**
 * @typedef {Object} PendingSpring
 * @property {number} rangeLow
 * @property {number} rangeHigh
 * @property {number} springLow
 * @property {number} eventBar
 * @property {number} expiresAt
 * @property {number} rallyHigh
 */

/**
 * @typedef {Object} PendingUtad
 * @property {number} rangeHigh
 * @property {number} rangeLow
 * @property {number} utadHigh
 * @property {number} eventBar
 * @property {number} expiresAt
 * @property {number} rallyLow
 */

/**
 * Waits for a higher-low / lower-high test after a spring or UTAD event.
 */
export class WyckoffRangeTestStrategy extends BaseStrategy {
  static id = 'wyckoff-range-test';
  static name = 'Wyckoff Range Test';
  static description = 'Enter on the secondary test of range support/resistance after spring or UTAD.';
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
      },
      {
        key: 'minRangePips',
        label: 'Min Range (pips)',
        type: 'number',
        default: 15,
        min: 5,
        max: 80,
        step: 1,
      },
      {
        key: 'minInsideRatio',
        label: 'Min Inside Ratio',
        type: 'number',
        default: 0.65,
        min: 0.4,
        max: 0.95,
        step: 0.05,
      },
      {
        key: 'sweepPips',
        label: 'Event Sweep (pips)',
        type: 'number',
        default: 2,
        min: 1,
        max: 20,
        step: 0.5,
        description: 'Sweep distance to register spring/UTAD event',
      },
      {
        key: 'testMaxBars',
        label: 'Test Max Bars',
        type: 'integer',
        default: 8,
        min: 2,
        max: 25,
        description: 'Bars after spring/UTAD to wait for test entry',
      },
      {
        key: 'testTolerancePips',
        label: 'Test Zone (pips)',
        type: 'number',
        default: 3,
        min: 1,
        max: 10,
        step: 0.5,
      },
      {
        key: 'rallyMinPips',
        label: 'Rally Min (pips)',
        type: 'number',
        default: 5,
        min: 2,
        max: 40,
        step: 1,
        description: 'Price must leave the boundary before the test counts',
      },
      {
        key: 'eventWickRatio',
        label: 'Event Wick Ratio',
        type: 'number',
        default: 0.5,
        min: 0.35,
        max: 0.85,
        step: 0.05,
        description: 'Wick on spring/UTAD bar that arms the setup',
      },
      {
        key: 'testWickRatio',
        label: 'Test Wick Ratio',
        type: 'number',
        default: 0.45,
        min: 0.3,
        max: 0.8,
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
    return Number(this._getParam('rangeLookback') ?? 20) + 10;
  }

  onInitialize() {
    this._setState('pendingSpring', null);
    this._setState('pendingUtad', null);
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   */
  calculate(candles, index) {
    const lookback = Number(this._getParam('rangeLookback'));
    const minRangePips = Number(this._getParam('minRangePips'));
    const minInsideRatio = Number(this._getParam('minInsideRatio'));
    const sweepPips = Number(this._getParam('sweepPips'));
    const eventWickRatio = Number(this._getParam('eventWickRatio'));
    const testMaxBars = Number(this._getParam('testMaxBars'));
    const symbol = /** @type {string} */ (this._getState('symbol') ?? 'EURUSD');
    const pip = pipsToPrice(1, symbol);
    const candle = candles[index];

    /** @type {PendingSpring|null} */
    let pendingSpring = this._getState('pendingSpring') ?? null;
    /** @type {PendingUtad|null} */
    let pendingUtad = this._getState('pendingUtad') ?? null;

    if (pendingSpring && index > pendingSpring.expiresAt) pendingSpring = null;
    if (pendingUtad && index > pendingUtad.expiresAt) pendingUtad = null;

    if (pendingSpring && index > pendingSpring.eventBar) {
      pendingSpring.rallyHigh = Math.max(pendingSpring.rallyHigh, candle.high);
      if (candle.low < pendingSpring.springLow - sweepPips * pip) {
        pendingSpring = null;
      }
    }

    if (pendingUtad && index > pendingUtad.eventBar) {
      pendingUtad.rallyLow = Math.min(pendingUtad.rallyLow, candle.low);
      if (candle.high > pendingUtad.utadHigh + sweepPips * pip) {
        pendingUtad = null;
      }
    }

    const range = getTradingRange(candles, index, lookback);
    if (range && index >= lookback) {
      const { rangeHigh, rangeLow } = range;
      const widthOk = rangeWidthPips(rangeHigh, rangeLow, symbol) >= minRangePips;
      const consolidationOk = isConsolidationRange(
        candles, index, lookback, rangeHigh, rangeLow, minInsideRatio
      );

      if (widthOk && consolidationOk) {
        if (isWyckoffSpring(candle, rangeLow, sweepPips, pip, eventWickRatio, symbol)) {
          pendingSpring = {
            rangeLow,
            rangeHigh,
            springLow: candle.low,
            eventBar: index,
            expiresAt: index + testMaxBars,
            rallyHigh: candle.high,
          };
          pendingUtad = null;
        } else if (isWyckoffUtad(candle, rangeHigh, sweepPips, pip, eventWickRatio, symbol)) {
          pendingUtad = {
            rangeHigh,
            rangeLow,
            utadHigh: candle.high,
            eventBar: index,
            expiresAt: index + testMaxBars,
            rallyLow: candle.low,
          };
          pendingSpring = null;
        }
      }
    }

    this._setState('pendingSpring', pendingSpring);
    this._setState('pendingUtad', pendingUtad);
  }

  /**
   * @param {import('../strategy/StrategyContext.js').StrategyContext} ctx
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  generateSignal(ctx) {
    const { index, candles, symbol, timeframe } = ctx;
    const testTolerancePips = Number(this._getParam('testTolerancePips'));
    const rallyMinPips = Number(this._getParam('rallyMinPips'));
    const testWickRatio = Number(this._getParam('testWickRatio'));
    const rr = Number(this._getParam('rr'));
    const pip = pipsToPrice(1, symbol);
    const candle = candles[index];

    /** @type {PendingSpring|null} */
    const pendingSpring = this._getState('pendingSpring');
    /** @type {PendingUtad|null} */
    const pendingUtad = this._getState('pendingUtad');

    if (pendingSpring && index > pendingSpring.eventBar && index <= pendingSpring.expiresAt) {
      const rallyPips = priceToPips(pendingSpring.rallyHigh - pendingSpring.rangeLow, symbol);
      if (rallyPips >= rallyMinPips) {
        const signal = this.#checkSpringTest(
          candles, candle, pendingSpring, testTolerancePips, pip, testWickRatio, symbol, rr, index, timeframe
        );
        if (signal) {
          this._setState('pendingSpring', null);
          return signal;
        }
      }
    }

    if (pendingUtad && index > pendingUtad.eventBar && index <= pendingUtad.expiresAt) {
      const rallyPips = priceToPips(pendingUtad.rangeHigh - pendingUtad.rallyLow, symbol);
      if (rallyPips >= rallyMinPips) {
        const signal = this.#checkUtadTest(
          candles, candle, pendingUtad, testTolerancePips, pip, testWickRatio, symbol, rr, index, timeframe
        );
        if (signal) {
          this._setState('pendingUtad', null);
          return signal;
        }
      }
    }

    return null;
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {import('../data/Candle.js').Candle} candle
   * @param {PendingSpring} pending
   * @param {number} tolerancePips
   * @param {number} pip
   * @param {number} minWickRatio
   * @param {string} symbol
   * @param {number} rr
   * @param {number} index
   * @param {string} timeframe
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  #checkSpringTest(candles, candle, pending, tolerancePips, pip, minWickRatio, symbol, rr, index, timeframe) {
    if (!isWyckoffSpringTest(
      candle, pending.rangeLow, pending.springLow, tolerancePips, pip, minWickRatio, symbol
    )) {
      return null;
    }

    const wicks = getWicks(candle);
    const levels = buildLongLevels(
      candle.close,
      slBufferBelow(candle.low, symbol),
      rr
    );

    const confidence = computeConfidence(candle.timestamp, rr, {
      qualityWick: wicks.lower / wicks.range >= 0.6,
      preciseLocation: priceToPips(candle.close - pending.rangeLow, symbol) <= tolerancePips,
      extraPoints: priceToPips(pending.rallyHigh - pending.rangeLow, symbol) >= Number(this._getParam('rallyMinPips')) ? 10 : 0,
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
      reason: `Wyckoff test long: retest ${formatPrice(pending.rangeLow, symbol)} after spring bar ${pending.eventBar}`,
      screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
      strategyId: WyckoffRangeTestStrategy.id,
      setup: {
        levels: [
          { kind: 'break-level', label: 'Range low', price: pending.rangeLow },
        ],
        markers: [
          { label: 'Spring', time: candles[pending.eventBar]?.timestamp ?? candle.timestamp, role: 'sweep' },
          { label: 'Test', time: candle.timestamp, role: 'confirm' },
        ],
        steps: [
          '1. Spring quet duoi range (khong vao lenh)',
          '2. Gia rally roi test lai support',
          '3. Higher low + nen xac nhan ? LONG',
        ],
      },
    });
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {import('../data/Candle.js').Candle} candle
   * @param {PendingUtad} pending
   * @param {number} tolerancePips
   * @param {number} pip
   * @param {number} minWickRatio
   * @param {string} symbol
   * @param {number} rr
   * @param {number} index
   * @param {string} timeframe
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  #checkUtadTest(candles, candle, pending, tolerancePips, pip, minWickRatio, symbol, rr, index, timeframe) {
    if (!isWyckoffUtadTest(
      candle, pending.rangeHigh, pending.utadHigh, tolerancePips, pip, minWickRatio, symbol
    )) {
      return null;
    }

    const wicks = getWicks(candle);
    const levels = buildShortLevels(
      candle.close,
      slBufferAbove(candle.high, symbol),
      rr
    );

    const confidence = computeConfidence(candle.timestamp, rr, {
      qualityWick: wicks.upper / wicks.range >= 0.6,
      preciseLocation: priceToPips(pending.rangeHigh - candle.close, symbol) <= tolerancePips,
      extraPoints: priceToPips(pending.rangeHigh - pending.rallyLow, symbol) >= Number(this._getParam('rallyMinPips')) ? 10 : 0,
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
      reason: `Wyckoff test short: retest ${formatPrice(pending.rangeHigh, symbol)} after UTAD bar ${pending.eventBar}`,
      screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
      strategyId: WyckoffRangeTestStrategy.id,
      setup: {
        levels: [
          { kind: 'break-level', label: 'Range high', price: pending.rangeHigh },
        ],
        markers: [
          { label: 'UTAD', time: candles[pending.eventBar]?.timestamp ?? candle.timestamp, role: 'sweep' },
          { label: 'Test', time: candle.timestamp, role: 'confirm' },
        ],
        steps: [
          '1. UTAD quet tren range (khong vao lenh)',
          '2. Gia giam roi test lai resistance',
          '3. Lower high + nen xac nhan ? SHORT',
        ],
      },
    });
  }
}
