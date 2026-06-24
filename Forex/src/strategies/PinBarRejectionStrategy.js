/**
 * Pin Bar Rejection strategy — rejection candles at swing support/resistance.
 * @module strategies/PinBarRejectionStrategy
 */

import { BaseStrategy } from '../strategy/BaseStrategy.js';
import { createSignal } from '../strategy/Signal.js';
import { pipsToPrice, formatPrice, priceToPips } from '../utils/pip.js';
import { swingHigh, swingLow } from '../strategy/helpers/SwingLevels.js';
import {
  isBullishConfirmation,
  isBearishConfirmation,
  touchesZone,
  isPinBar,
  getWicks,
} from '../strategy/helpers/CandlePatterns.js';
import {
  buildLongLevels,
  buildShortLevels,
  slBufferBelow,
  slBufferAbove,
} from '../strategy/helpers/TradeLevels.js';
import { computeConfidence } from '../strategy/helpers/ConfidenceScore.js';

/**
 * @typedef {Object} LevelSignalRecord
 * @property {number} level
 * @property {'long'|'short'} direction
 * @property {number} barIndex
 */

/**
 * Fades or bounces from swing levels when a pin-bar rejection forms at the zone.
 */
export class PinBarRejectionStrategy extends BaseStrategy {
  static id = 'pin-bar-rejection';
  static name = 'Pin Bar Rejection';
  static description = 'Trade pin-bar rejections at swing support and resistance.';
  static version = '1.0.0';
  static category = 'Price Action';

  getParameterSchema() {
    return [
      {
        key: 'swingLookback',
        label: 'Swing Lookback',
        type: 'integer',
        default: 7,
        min: 3,
        max: 30,
      },
      {
        key: 'retestTolerancePips',
        label: 'Level Zone (pips)',
        type: 'number',
        default: 2,
        min: 1,
        max: 10,
        step: 0.5,
        description: 'Swing level touch tolerance',
      },
      {
        key: 'minWickRatio',
        label: 'Min Wick Ratio',
        type: 'number',
        default: 0.55,
        min: 0.4,
        max: 0.85,
        step: 0.05,
        description: 'Rejection wick as fraction of candle range',
      },
      {
        key: 'maxBodyRatio',
        label: 'Max Body Ratio',
        type: 'number',
        default: 0.35,
        min: 0.15,
        max: 0.5,
        step: 0.05,
        description: 'Body must be smaller than this fraction of range',
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
    return Number(this._getParam('swingLookback') ?? 7) + 15;
  }

  onInitialize() {
    this._setState('recentLevels', []);
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   */
  calculate(candles, index) {
    const lookback = Number(this._getParam('swingLookback'));
    /** @type {LevelSignalRecord[]} */
    let recent = this._getState('recentLevels') ?? [];
    const window = lookback * 2;

    recent = recent.filter((r) => index - r.barIndex <= window);
    this._setState('recentLevels', recent);
    this._setState('levelHigh', swingHigh(candles, index, lookback));
    this._setState('levelLow', swingLow(candles, index, lookback));
  }

  /**
   * @param {import('../strategy/StrategyContext.js').StrategyContext} ctx
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  generateSignal(ctx) {
    const { index, candles, symbol, timeframe } = ctx;
    const lookback = Number(this._getParam('swingLookback'));
    const tolerancePips = Number(this._getParam('retestTolerancePips'));
    const minWickRatio = Number(this._getParam('minWickRatio'));
    const maxBodyRatio = Number(this._getParam('maxBodyRatio'));
    const rr = Number(this._getParam('rr'));

    const levelHigh = /** @type {number|null} */ (this._getState('levelHigh'));
    const levelLow = /** @type {number|null} */ (this._getState('levelLow'));
    const candle = candles[index];

    if (index < lookback) return null;

    const shortSignal = this.#checkShort(
      candle, levelHigh, tolerancePips, minWickRatio, maxBodyRatio, symbol, rr, index, timeframe
    );
    if (shortSignal) {
      this.#recordLevel(levelHigh, 'short', index);
      return shortSignal;
    }

    const longSignal = this.#checkLong(
      candle, levelLow, tolerancePips, minWickRatio, maxBodyRatio, symbol, rr, index, timeframe
    );
    if (longSignal) {
      this.#recordLevel(levelLow, 'long', index);
      return longSignal;
    }

    return null;
  }

  /**
   * @param {import('../data/Candle.js').Candle} candle
   * @param {number|null} levelHigh
   * @param {number} tolerancePips
   * @param {number} minWickRatio
   * @param {number} maxBodyRatio
   * @param {string} symbol
   * @param {number} rr
   * @param {number} index
   * @param {string} timeframe
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  #checkShort(candle, levelHigh, tolerancePips, minWickRatio, maxBodyRatio, symbol, rr, index, timeframe) {
    if (levelHigh === null) return null;
    if (this.#isDuplicateLevel(levelHigh, 'short', index, symbol)) return null;
    if (!touchesZone(candle, levelHigh, tolerancePips, symbol)) return null;
    if (!isPinBar(candle, 'short', minWickRatio, maxBodyRatio)) return null;
    if (!isBearishConfirmation(candle, symbol)) return null;

    const wicks = getWicks(candle);
    const levels = buildShortLevels(
      candle.close,
      slBufferAbove(candle.high, symbol),
      rr
    );

    const confidence = computeConfidence(candle.timestamp, rr, {
      qualityWick: wicks.upper / wicks.range >= 0.65,
      preciseLocation: true,
      extraPoints: wicks.upper / wicks.range >= 0.65 ? 10 : 0,
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
      reason: `Pin bar short: rejected ${formatPrice(levelHigh, symbol)} swing high bar ${index}`,
      screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
      strategyId: PinBarRejectionStrategy.id,
      setup: {
        levels: [{ kind: 'liquidity', label: 'Swing high', price: levelHigh }],
        markers: [{ label: 'Pin reject', time: candle.timestamp, role: 'sweep' }],
        steps: [
          '1. Giá ch?m swing high',
          '2. Pin bar râu trên dài + n?n gi?m',
          '3. Entry short t?i close',
        ],
      },
    });
  }

  /**
   * @param {import('../data/Candle.js').Candle} candle
   * @param {number|null} levelLow
   * @param {number} tolerancePips
   * @param {number} minWickRatio
   * @param {number} maxBodyRatio
   * @param {string} symbol
   * @param {number} rr
   * @param {number} index
   * @param {string} timeframe
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  #checkLong(candle, levelLow, tolerancePips, minWickRatio, maxBodyRatio, symbol, rr, index, timeframe) {
    if (levelLow === null) return null;
    if (this.#isDuplicateLevel(levelLow, 'long', index, symbol)) return null;
    if (!touchesZone(candle, levelLow, tolerancePips, symbol)) return null;
    if (!isPinBar(candle, 'long', minWickRatio, maxBodyRatio)) return null;
    if (!isBullishConfirmation(candle, symbol)) return null;

    const wicks = getWicks(candle);
    const levels = buildLongLevels(
      candle.close,
      slBufferBelow(candle.low, symbol),
      rr
    );

    const confidence = computeConfidence(candle.timestamp, rr, {
      qualityWick: wicks.lower / wicks.range >= 0.65,
      preciseLocation: true,
      extraPoints: wicks.lower / wicks.range >= 0.65 ? 10 : 0,
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
      reason: `Pin bar long: rejected ${formatPrice(levelLow, symbol)} swing low bar ${index}`,
      screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
      strategyId: PinBarRejectionStrategy.id,
      setup: {
        levels: [{ kind: 'liquidity', label: 'Swing low', price: levelLow }],
        markers: [{ label: 'Pin reject', time: candle.timestamp, role: 'sweep' }],
        steps: [
          '1. Giá ch?m swing low',
          '2. Pin bar râu d??i dài + n?n t?ng',
          '3. Entry long t?i close',
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
    const lookback = Number(this._getParam('swingLookback'));
    const tolerancePips = Number(this._getParam('retestTolerancePips'));
    const window = lookback * 2;
    /** @type {LevelSignalRecord[]} */
    const recent = this._getState('recentLevels') ?? [];

    return recent.some(
      (r) =>
        r.direction === direction &&
        Math.abs(r.level - level) < pipsToPrice(tolerancePips, symbol) &&
        index - r.barIndex <= window
    );
  }
}
