/**
 * EMA Pullback strategy — full implementation per STRATEGY_SPECIFICATION.md §4.
 * @module strategies/EMAPullbackStrategy
 */

import { BaseStrategy } from '../strategy/BaseStrategy.js';
import { createSignal } from '../strategy/Signal.js';
import { pipsToPrice, formatPrice } from '../utils/pip.js';
import {
  isBullishConfirmation,
  isBearishConfirmation,
  bodyRatio,
} from '../strategy/helpers/CandlePatterns.js';
import {
  buildLongLevels,
  buildShortLevels,
  slBufferBelow,
  slBufferAbove,
} from '../strategy/helpers/TradeLevels.js';
import { computeConfidence } from '../strategy/helpers/ConfidenceScore.js';
import {
  emaAtIndex,
  countHigherCloses,
  countLowerCloses,
} from '../strategy/helpers/EmaHelper.js';

/**
 * Trades pullbacks to EMA in a confirmed trend.
 */
export class EMAPullbackStrategy extends BaseStrategy {
  static id = 'ema-pullback';
  static name = 'EMA Pullback';
  static description = 'Enter on pullback to EMA within a trending market.';
  static version = '1.0.0';
  static category = 'Price Action';

  getParameterSchema() {
    return [
      {
        key: 'emaFast',
        label: 'EMA Fast',
        type: 'select',
        default: 20,
        options: [10, 20, 30],
      },
      {
        key: 'emaSlow',
        label: 'EMA Slow',
        type: 'select',
        default: 50,
        options: [30, 40, 50, 60],
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
      {
        key: 'pullbackTolerancePips',
        label: 'Pullback Tolerance (pips)',
        type: 'number',
        default: 3,
        min: 1,
        max: 20,
        step: 0.5,
      },
      {
        key: 'trendBars',
        label: 'Trend Confirmation Bars',
        type: 'integer',
        default: 5,
        min: 3,
        max: 20,
      },
    ];
  }

  getWarmupBars() {
    return Number(this._getParam('emaSlow') ?? 50) + 10;
  }

  onInitialize() {
    this._setState('lastSignalIndex', -999);
    this._setState('lastSignalDirection', null);
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   */
  calculate(candles, index) {
    const fastPeriod = Number(this._getParam('emaFast'));
    const slowPeriod = Number(this._getParam('emaSlow'));
    const trendBars = Number(this._getParam('trendBars'));

    const emaFast = emaAtIndex(candles, index, fastPeriod);
    const emaSlow = emaAtIndex(candles, index, slowPeriod);
    const emaFastPrev = index >= trendBars
      ? emaAtIndex(candles, index - trendBars, fastPeriod)
      : null;

    this._setState('emaFast', emaFast);
    this._setState('emaSlow', emaSlow);
    this._setState('emaFastPrev', emaFastPrev);
    this._setState('trend', this.#detectTrend(candles, index));
  }

  /**
   * @param {import('../strategy/StrategyContext.js').StrategyContext} ctx
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  generateSignal(ctx) {
    const { index, candles, symbol, timeframe } = ctx;
    const candle = candles[index];
    const rr = Number(this._getParam('rr'));
    const tolerance = Number(this._getParam('pullbackTolerancePips'));
    const trendBars = Number(this._getParam('trendBars'));

    const emaFast = /** @type {number} */ (this._getState('emaFast'));
    const emaSlow = /** @type {number} */ (this._getState('emaSlow'));
    if (emaFast === null || emaSlow === null) return null;

    const trend = /** @type {'up'|'down'|'none'} */ (this._getState('trend'));
    if (trend === 'none') return null;

    const emaSpread = Math.abs(emaFast - emaSlow);
    const minSpread = pipsToPrice(3, symbol);
    const maxSpread = pipsToPrice(50, symbol);
    if (emaSpread < minSpread || emaSpread > maxSpread) return null;

    const lastIdx = Number(this._getState('lastSignalIndex'));
    if (index - lastIdx < trendBars) return null;

    const zoneUpper = emaFast + pipsToPrice(tolerance, symbol);
    const zoneLower = emaFast - pipsToPrice(tolerance, symbol);

    if (trend === 'up') {
      const pullbackTouch = candle.low <= zoneUpper && candle.close >= zoneLower;
      if (!pullbackTouch) return null;
      if (!isBullishConfirmation(candle, symbol)) return null;
      if (candle.close <= emaFast) return null;
      if (candle.low <= emaSlow) return null;

      const levels = buildLongLevels(
        candle.close,
        slBufferBelow(Math.min(candle.low, zoneLower), symbol),
        rr
      );

      const wickOnlyTouch = candle.low <= emaFast && Math.min(candle.open, candle.close) > emaFast;
      const spreadPips = emaSpread / pipsToPrice(1, symbol);

      const confidence = computeConfidence(candle.timestamp, rr, {
        trendAlignment: true,
        momentum: bodyRatio(candle) > 0.5,
        qualityWick: wickOnlyTouch,
        extraPoints:
          (spreadPips >= 5 && spreadPips <= 20 ? 10 : 0) +
          (wickOnlyTouch ? 15 : 0),
      });

      this._setState('lastSignalIndex', index);
      this._setState('lastSignalDirection', 'long');

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
        reason: `EMA pullback long: trend up, touch EMA${this._getParam('emaFast')} (${formatPrice(emaFast, symbol)}), bullish confirm`,
        screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
        strategyId: EMAPullbackStrategy.id,
      });
    }

    const pullbackTouch = candle.high >= zoneLower && candle.close <= zoneUpper;
    if (!pullbackTouch) return null;
    if (!isBearishConfirmation(candle, symbol)) return null;
    if (candle.close >= emaFast) return null;
    if (candle.high >= emaSlow) return null;

    const levels = buildShortLevels(
      candle.close,
      slBufferAbove(Math.max(candle.high, zoneUpper), symbol),
      rr
    );

    const wickOnlyTouch = candle.high >= emaFast && Math.max(candle.open, candle.close) < emaFast;
    const spreadPips = emaSpread / pipsToPrice(1, symbol);

    const confidence = computeConfidence(candle.timestamp, rr, {
      trendAlignment: true,
      momentum: bodyRatio(candle) > 0.5,
      qualityWick: wickOnlyTouch,
      extraPoints:
        (spreadPips >= 5 && spreadPips <= 20 ? 10 : 0) +
        (wickOnlyTouch ? 15 : 0),
    });

    this._setState('lastSignalIndex', index);
    this._setState('lastSignalDirection', 'short');

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
      reason: `EMA pullback short: trend down, touch EMA${this._getParam('emaFast')} (${formatPrice(emaFast, symbol)}), bearish confirm`,
      screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
      strategyId: EMAPullbackStrategy.id,
    });
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   * @returns {'up'|'down'|'none'}
   */
  #detectTrend(candles, index) {
    const fastPeriod = Number(this._getParam('emaFast'));
    const slowPeriod = Number(this._getParam('emaSlow'));
    const trendBars = Number(this._getParam('trendBars'));

    const emaFast = emaAtIndex(candles, index, fastPeriod);
    const emaSlow = emaAtIndex(candles, index, slowPeriod);
    const emaFastPrev = emaAtIndex(candles, index - trendBars, fastPeriod);

    if (emaFast === null || emaSlow === null || emaFastPrev === null) return 'none';

    const minCount = Math.ceil(trendBars * 0.6);
    const windowStart = index - trendBars + 1;

    const higherCloses = countHigherCloses(candles, windowStart, index);
    const lowerCloses = countLowerCloses(candles, windowStart, index);

    if (
      emaFast > emaSlow &&
      emaFast > emaFastPrev &&
      candles[index].close > emaSlow &&
      higherCloses >= minCount
    ) {
      return 'up';
    }

    if (
      emaFast < emaSlow &&
      emaFast < emaFastPrev &&
      candles[index].close < emaSlow &&
      lowerCloses >= minCount
    ) {
      return 'down';
    }

    return 'none';
  }
}
