/**
 * Break & Retest strategy — full implementation per STRATEGY_SPECIFICATION.md §3.
 * @module strategies/BreakRetestStrategy
 */

import { BaseStrategy } from '../strategy/BaseStrategy.js';
import { createSignal } from '../strategy/Signal.js';
import { pipsToPrice, formatPrice } from '../utils/pip.js';
import { swingHigh, swingLow } from '../strategy/helpers/SwingLevels.js';
import {
  RETEST_TOLERANCE_PIPS,
  isBullishConfirmation,
  isBearishConfirmation,
  touchesZone,
  bodyRatio,
  getWicks,
  getLevelZone,
} from '../strategy/helpers/CandlePatterns.js';
import {
  buildLongLevels,
  buildShortLevels,
  slBufferBelow,
  slBufferAbove,
} from '../strategy/helpers/TradeLevels.js';
import { computeConfidence } from '../strategy/helpers/ConfidenceScore.js';

/**
 * @typedef {Object} PendingSetup
 * @property {'long'|'short'} direction
 * @property {number} level
 * @property {number} breakoutBar
 * @property {number} invalidation
 * @property {number} expiresAtBar
 * @property {import('../data/Candle.js').Candle} breakoutCandle
 */

/**
 * Identifies breakout levels followed by retest confirmation.
 */
export class BreakRetestStrategy extends BaseStrategy {
  static id = 'break-retest';
  static name = 'Break & Retest';
  static description = 'Trade breakouts that retest the broken level before continuing.';
  static version = '1.0.0';
  static category = 'Price Action';

  getParameterSchema() {
    return [
      {
        key: 'breakoutPips',
        label: 'Breakout (pips)',
        type: 'number',
        default: 5,
        min: 1,
        max: 50,
        step: 1,
        description: 'Minimum pips beyond level to confirm breakout',
      },
      {
        key: 'retestMaxBars',
        label: 'Retest Max Bars',
        type: 'integer',
        default: 10,
        min: 1,
        max: 50,
        description: 'Maximum candles to wait for retest',
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
        key: 'swingLookback',
        label: 'Swing Lookback',
        type: 'integer',
        default: 5,
        min: 3,
        max: 20,
      },
    ];
  }

  getWarmupBars() {
    return Number(this._getParam('swingLookback') ?? 5) + 20;
  }

  onInitialize() {
    this._setState('pending', null);
    this._setState('lastSignalTime', null);
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   */
  calculate(candles, index) {
    const symbol = this._getState('symbol');
    if (!symbol) return;

    const lookback = Number(this._getParam('swingLookback'));
    const breakoutPips = Number(this._getParam('breakoutPips'));
    const retestMaxBars = Number(this._getParam('retestMaxBars'));
    const pip = pipsToPrice(1, symbol);

    /** @type {PendingSetup|null} */
    let pending = this._getState('pending');

    if (pending) {
      if (index > pending.expiresAtBar) {
        pending = null;
      } else {
        const c = candles[index];
        const invalidated = pending.direction === 'long'
          ? c.close < pending.invalidation
          : c.close > pending.invalidation;
        if (invalidated) pending = null;
      }
    }

    if (index >= lookback) {
      const levelHigh = swingHigh(candles, index, lookback);
      const levelLow = swingLow(candles, index, lookback);
      const c = candles[index];

      if (levelHigh !== null) {
        const threshold = levelHigh + breakoutPips * pip;
        if (c.close >= threshold) {
          pending = {
            direction: 'long',
            level: levelHigh,
            breakoutBar: index,
            invalidation: slBufferBelow(c.low, symbol),
            expiresAtBar: index + retestMaxBars,
            breakoutCandle: c,
          };
        }
      }

      if (levelLow !== null) {
        const threshold = levelLow - breakoutPips * pip;
        if (c.close <= threshold) {
          pending = {
            direction: 'short',
            level: levelLow,
            breakoutBar: index,
            invalidation: slBufferAbove(c.high, symbol),
            expiresAtBar: index + retestMaxBars,
            breakoutCandle: c,
          };
        }
      }
    }

    this._setState('pending', pending);
  }

  /**
   * @param {import('../strategy/StrategyContext.js').StrategyContext} ctx
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  generateSignal(ctx) {
    this._setState('symbol', ctx.symbol);

    /** @type {PendingSetup|null} */
    const pending = this._getState('pending');
    if (!pending) return null;

    const { index, candles, symbol, timeframe } = ctx;
    const r = index;

    if (r <= pending.breakoutBar || r > pending.expiresAtBar) return null;

    const candle = candles[r];
    const rr = Number(this._getParam('rr'));
    const zone = getLevelZone(pending.level, RETEST_TOLERANCE_PIPS, symbol);

    if (pending.direction === 'long') {
      if (candle.close < pending.invalidation) return null;

      const retestTouch = touchesZone(candle, pending.level, RETEST_TOLERANCE_PIPS, symbol);
      if (!retestTouch || !isBullishConfirmation(candle, symbol)) return null;

      const rawSl = Math.min(candle.low, zone.lower);
      const levels = buildLongLevels(candle.close, slBufferBelow(rawSl, symbol), rr);

      const wicks = getWicks(candle);
      const preciseLocation = Math.abs(candle.low - pending.level) <= pipsToPrice(1, symbol);
      const wickTouch = candle.low <= pending.level && candle.close > pending.level;

      const confidence = computeConfidence(candle.timestamp, rr, {
        trendAlignment: true,
        momentum: bodyRatio(candle) > 0.5,
        preciseLocation,
        qualityWick: wickTouch,
        extraPoints:
          (bodyRatio(pending.breakoutCandle) > 0.6 ? 10 : 0) +
          (r - pending.breakoutBar <= 3 ? 10 : 0) +
          (wickTouch ? 10 : 0),
      });

      this._setState('pending', null);

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
        reason: `Bullish B&R: broke ${formatPrice(pending.level, symbol)}, retest bar ${r - pending.breakoutBar}, entry on confirmation`,
        screenshotPosition: { candleIndex: r, timestamp: candle.timestamp },
        strategyId: BreakRetestStrategy.id,
        setup: {
          levels: [
            { kind: 'break-level', label: 'Mức B&R', price: pending.level },
            { kind: 'invalidation', label: 'Vô hiệu', price: pending.invalidation },
          ],
          markers: [
            {
              label: 'Breakout',
              time: pending.breakoutCandle.timestamp,
              role: 'breakout',
            },
            {
              label: 'Retest + Entry',
              time: candle.timestamp,
              role: 'entry',
            },
          ],
          steps: [
            '1. Giá phá vượt swing level (Breakout)',
            '2. Hồi retest vùng level cam',
            '3. Nến xác nhận → Entry xanh dương',
          ],
        },
      });
    }

    if (candle.close > pending.invalidation) return null;

    const retestTouch = touchesZone(candle, pending.level, RETEST_TOLERANCE_PIPS, symbol);
    if (!retestTouch || !isBearishConfirmation(candle, symbol)) return null;

    const rawSl = Math.max(candle.high, zone.upper);
    const levels = buildShortLevels(candle.close, slBufferAbove(rawSl, symbol), rr);

    const wickTouch = candle.high >= pending.level && candle.close < pending.level;
    const preciseLocation = Math.abs(candle.high - pending.level) <= pipsToPrice(1, symbol);

    const confidence = computeConfidence(candle.timestamp, rr, {
      trendAlignment: true,
      momentum: bodyRatio(candle) > 0.5,
      preciseLocation,
      qualityWick: wickTouch,
      extraPoints:
        (bodyRatio(pending.breakoutCandle) > 0.6 ? 10 : 0) +
        (r - pending.breakoutBar <= 3 ? 10 : 0) +
        (wickTouch ? 10 : 0),
    });

    this._setState('pending', null);

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
      reason: `Bearish B&R: broke ${formatPrice(pending.level, symbol)}, retest bar ${r - pending.breakoutBar}, entry on confirmation`,
      screenshotPosition: { candleIndex: r, timestamp: candle.timestamp },
      strategyId: BreakRetestStrategy.id,
      setup: {
        levels: [
          { kind: 'break-level', label: 'Mức B&R', price: pending.level },
          { kind: 'invalidation', label: 'Vô hiệu', price: pending.invalidation },
        ],
        markers: [
          { label: 'Breakout', time: pending.breakoutCandle.timestamp, role: 'breakout' },
          { label: 'Retest + Entry', time: candle.timestamp, role: 'entry' },
        ],
        steps: [
          '1. Giá phá xuống swing level (Breakout)',
          '2. Hồi retest vùng level cam',
          '3. Nến xác nhận → Entry xanh dương',
        ],
      },
    });
  }

  /**
   * @param {import('../strategy/Signal.js').Signal} signal
   * @returns {boolean}
   */
  validate(signal) {
    if (!super.validate(signal)) return false;
    const lastTime = this._getState('lastSignalTime');
    if (lastTime === signal.time) return false;
    this._setState('lastSignalTime', signal.time);
    return true;
  }
}
