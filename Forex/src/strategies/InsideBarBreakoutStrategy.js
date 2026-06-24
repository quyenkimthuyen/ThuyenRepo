/**
 * Inside Bar Breakout strategy — consolidation breakout with trend filter.
 * @module strategies/InsideBarBreakoutStrategy
 */

import { BaseStrategy } from '../strategy/BaseStrategy.js';
import { createSignal } from '../strategy/Signal.js';
import { pipsToPrice, formatPrice, priceToPips } from '../utils/pip.js';
import { isInsideBar } from '../strategy/helpers/CandlePatterns.js';
import {
  buildLongLevels,
  buildShortLevels,
  slBufferBelow,
  slBufferAbove,
} from '../strategy/helpers/TradeLevels.js';
import { computeConfidence } from '../strategy/helpers/ConfidenceScore.js';
import { emaAtIndex } from '../strategy/helpers/EmaHelper.js';

/**
 * @typedef {Object} PendingInsideBar
 * @property {number} motherBar
 * @property {number} motherHigh
 * @property {number} motherLow
 * @property {number} expiresAtBar
 */

/**
 * Trades breakouts from inside-bar consolidation aligned with EMA trend.
 */
export class InsideBarBreakoutStrategy extends BaseStrategy {
  static id = 'inside-bar-breakout';
  static name = 'Inside Bar Breakout';
  static description = 'Enter when price breaks the mother bar after an inside-bar pause in trend.';
  static version = '1.0.0';
  static category = 'Price Action';

  getParameterSchema() {
    return [
      {
        key: 'trendEma',
        label: 'Trend EMA',
        type: 'select',
        default: 50,
        options: [20, 50, 200],
        description: 'Long above EMA, short below EMA',
      },
      {
        key: 'motherMinRangePips',
        label: 'Mother Min Range (pips)',
        type: 'number',
        default: 10,
        min: 3,
        max: 80,
        step: 1,
        description: 'Mother bar range must be at least this wide',
      },
      {
        key: 'breakoutBufferPips',
        label: 'Breakout Buffer (pips)',
        type: 'number',
        default: 1,
        min: 0,
        max: 10,
        step: 0.5,
        description: 'Close must exceed mother extreme by this buffer',
      },
      {
        key: 'maxWaitBars',
        label: 'Max Wait Bars',
        type: 'integer',
        default: 3,
        min: 1,
        max: 10,
        description: 'Bars after inside bar to allow breakout',
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
    return Number(this._getParam('trendEma') ?? 50) + 10;
  }

  onInitialize() {
    this._setState('pending', null);
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   */
  calculate(candles, index) {
    if (index < 2) return;

    const symbol = /** @type {string} */ (this._getState('symbol') ?? 'EURUSD');
    const mother = candles[index - 2];
    const inside = candles[index - 1];
    const motherMinRange = Number(this._getParam('motherMinRangePips'));
    const maxWaitBars = Number(this._getParam('maxWaitBars'));

    if (!isInsideBar(inside, mother)) return;

    const motherRangePips = priceToPips(mother.high - mother.low, symbol);
    if (motherRangePips < motherMinRange) return;

    /** @type {PendingInsideBar} */
    const pending = {
      motherBar: index - 2,
      motherHigh: mother.high,
      motherLow: mother.low,
      expiresAtBar: index - 1 + maxWaitBars,
    };
    this._setState('pending', pending);
  }

  /**
   * @param {import('../strategy/StrategyContext.js').StrategyContext} ctx
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  generateSignal(ctx) {
    const { index, candles, symbol, timeframe } = ctx;
    /** @type {PendingInsideBar|null} */
    const pending = this._getState('pending') ?? null;
    if (!pending) return null;
    if (index <= pending.motherBar + 1) return null;
    if (index > pending.expiresAtBar) {
      this._setState('pending', null);
      return null;
    }

    const trendEma = Number(this._getParam('trendEma'));
    const bufferPips = Number(this._getParam('breakoutBufferPips'));
    const rr = Number(this._getParam('rr'));
    const buffer = pipsToPrice(bufferPips, symbol);
    const candle = candles[index];
    const ema = emaAtIndex(candles, index, trendEma);
    if (ema === null) return null;

    const longBreak = candle.close > pending.motherHigh + buffer && candle.close > ema;
    const shortBreak = candle.close < pending.motherLow - buffer && candle.close < ema;

    if (!longBreak && !shortBreak) return null;

    this._setState('pending', null);

    if (longBreak) {
      const levels = buildLongLevels(
        candle.close,
        slBufferBelow(pending.motherLow, symbol),
        rr
      );
      const confidence = computeConfidence(candle.timestamp, rr, {
        trendAlignment: true,
        momentum: candle.close > candle.open,
        rrGte2: rr >= 2,
        extraPoints: bufferPips === 0 ? 5 : 0,
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
        reason: `Inside bar long: broke ${formatPrice(pending.motherHigh, symbol)} mother high bar ${index}`,
        screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
        strategyId: InsideBarBreakoutStrategy.id,
        setup: {
          levels: [
            { kind: 'break-level', label: 'Mother high', price: pending.motherHigh },
            { kind: 'break-level', label: 'Mother low', price: pending.motherLow },
          ],
          markers: [
            { label: 'Inside bar', time: candles[index - 1]?.timestamp ?? candle.timestamp, role: 'confirm' },
            { label: 'Breakout', time: candle.timestamp, role: 'entry' },
          ],
          steps: [
            '1. Mother bar + inside bar (nén)',
            '2. Giá trên EMA trend',
            '3. Close phá mother high ? LONG',
          ],
        },
      });
    }

    const levels = buildShortLevels(
      candle.close,
      slBufferAbove(pending.motherHigh, symbol),
      rr
    );
    const confidence = computeConfidence(candle.timestamp, rr, {
      trendAlignment: true,
      momentum: candle.close < candle.open,
      rrGte2: rr >= 2,
      extraPoints: bufferPips === 0 ? 5 : 0,
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
      reason: `Inside bar short: broke ${formatPrice(pending.motherLow, symbol)} mother low bar ${index}`,
      screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
      strategyId: InsideBarBreakoutStrategy.id,
      setup: {
        levels: [
          { kind: 'break-level', label: 'Mother high', price: pending.motherHigh },
          { kind: 'break-level', label: 'Mother low', price: pending.motherLow },
        ],
        markers: [
          { label: 'Inside bar', time: candles[index - 1]?.timestamp ?? candle.timestamp, role: 'confirm' },
          { label: 'Breakout', time: candle.timestamp, role: 'entry' },
        ],
        steps: [
          '1. Mother bar + inside bar (nén)',
          '2. Giá d??i EMA trend',
          '3. Close phá mother low ? SHORT',
        ],
      },
    });
  }
}
