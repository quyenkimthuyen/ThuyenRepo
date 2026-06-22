/**
 * Liquidity Grab strategy — full implementation per STRATEGY_SPECIFICATION.md §5.
 * @module strategies/LiquidityGrabStrategy
 */

import { BaseStrategy } from '../strategy/BaseStrategy.js';
import { createSignal } from '../strategy/Signal.js';
import { pipsToPrice, formatPrice, priceToPips } from '../utils/pip.js';
import { swingHigh, swingLow } from '../strategy/helpers/SwingLevels.js';
import {
  isBullishConfirmation,
  isBearishConfirmation,
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
 * Identifies stop hunts beyond swing highs/lows with rejection.
 */
export class LiquidityGrabStrategy extends BaseStrategy {
  static id = 'liquidity-grab';
  static name = 'Liquidity Grab';
  static description = 'Trade false breakouts that grab liquidity beyond swing points.';
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
        max: 20,
      },
      {
        key: 'grabPips',
        label: 'Grab Distance (pips)',
        type: 'number',
        default: 3,
        min: 1,
        max: 30,
        step: 0.5,
        description: 'Minimum pips beyond swing to qualify as grab',
      },
      {
        key: 'wickRatio',
        label: 'Min Wick Ratio',
        type: 'number',
        default: 0.6,
        min: 0.3,
        max: 0.9,
        step: 0.05,
        description: 'Wick must be at least this fraction of candle range',
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
    const grabPips = Number(this._getParam('grabPips'));
    const minWickRatio = Number(this._getParam('wickRatio'));
    const rr = Number(this._getParam('rr'));
    const pip = pipsToPrice(1, symbol);

    const levelHigh = /** @type {number|null} */ (this._getState('levelHigh'));
    const levelLow = /** @type {number|null} */ (this._getState('levelLow'));
    const candle = candles[index];

    if (index < lookback) return null;

    const avgVolume = this.#avgVolume(candles, index, lookback);
    const volumeOk = candle.volume === 0 || candle.volume >= 0.8 * avgVolume;

    const shortSignal = this.#checkShort(
      candle, levelHigh, grabPips, pip, minWickRatio, volumeOk, avgVolume, symbol, rr, index, timeframe
    );
    if (shortSignal) {
      this.#recordLevel(levelHigh, 'short', index);
      return shortSignal;
    }

    const longSignal = this.#checkLong(
      candle, levelLow, grabPips, pip, minWickRatio, volumeOk, avgVolume, symbol, rr, index, timeframe
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
   * @param {number} grabPips
   * @param {number} pip
   * @param {number} minWickRatio
   * @param {boolean} volumeOk
   * @param {number} avgVolume
   * @param {string} symbol
   * @param {number} rr
   * @param {number} index
   * @param {string} timeframe
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  #checkShort(candle, levelHigh, grabPips, pip, minWickRatio, volumeOk, avgVolume, symbol, rr, index, timeframe) {
    if (levelHigh === null) return null;
    if (this.#isDuplicateLevel(levelHigh, 'short', index)) return null;
    if (!volumeOk) return null;

    if (candle.high < levelHigh + grabPips * pip) return null;
    if (candle.close >= levelHigh) return null;

    const wicks = getWicks(candle);
    if (wicks.range <= 0 || wicks.upper / wicks.range < minWickRatio) return null;
    if (!isBearishConfirmation(candle, symbol)) return null;

    const levels = buildShortLevels(
      candle.close,
      slBufferAbove(candle.high, symbol),
      rr
    );

    const closeDistPips = priceToPips(levelHigh - candle.close, symbol);
    const confidence = computeConfidence(candle.timestamp, rr, {
      qualityWick: wicks.upper / wicks.range >= 0.7,
      preciseLocation: closeDistPips <= 2,
      extraPoints:
        (wicks.upper / wicks.range >= 0.7 ? 15 : 0) +
        (grabPips >= 5 ? 10 : 0) +
        (candle.volume > 0 && candle.volume >= 1.2 * avgVolume ? 10 : 0) +
        (closeDistPips <= 2 ? 10 : 0),
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
      reason: `Liquidity grab short: swept ${formatPrice(levelHigh, symbol)}, rejected bar ${index}`,
      screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
      strategyId: LiquidityGrabStrategy.id,
    });
  }

  /**
   * @param {import('../data/Candle.js').Candle} candle
   * @param {number|null} levelLow
   * @param {number} grabPips
   * @param {number} pip
   * @param {number} minWickRatio
   * @param {boolean} volumeOk
   * @param {number} avgVolume
   * @param {string} symbol
   * @param {number} rr
   * @param {number} index
   * @param {string} timeframe
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  #checkLong(candle, levelLow, grabPips, pip, minWickRatio, volumeOk, avgVolume, symbol, rr, index, timeframe) {
    if (levelLow === null) return null;
    if (this.#isDuplicateLevel(levelLow, 'long', index)) return null;
    if (!volumeOk) return null;

    if (candle.low > levelLow - grabPips * pip) return null;
    if (candle.close <= levelLow) return null;

    const wicks = getWicks(candle);
    if (wicks.range <= 0 || wicks.lower / wicks.range < minWickRatio) return null;
    if (!isBullishConfirmation(candle, symbol)) return null;

    const levels = buildLongLevels(
      candle.close,
      slBufferBelow(candle.low, symbol),
      rr
    );

    const closeDistPips = priceToPips(candle.close - levelLow, symbol);
    const confidence = computeConfidence(candle.timestamp, rr, {
      qualityWick: wicks.lower / wicks.range >= 0.7,
      preciseLocation: closeDistPips <= 2,
      extraPoints:
        (wicks.lower / wicks.range >= 0.7 ? 15 : 0) +
        (grabPips >= 5 ? 10 : 0) +
        (candle.volume > 0 && candle.volume >= 1.2 * avgVolume ? 10 : 0) +
        (closeDistPips <= 2 ? 10 : 0),
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
      reason: `Liquidity grab long: swept ${formatPrice(levelLow, symbol)}, rejected bar ${index}`,
      screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
      strategyId: LiquidityGrabStrategy.id,
    });
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   * @param {number} lookback
   * @returns {number}
   */
  #avgVolume(candles, index, lookback) {
    let sum = 0;
    let count = 0;
    for (let j = index - lookback; j < index; j++) {
      if (j >= 0) {
        sum += candles[j].volume;
        count++;
      }
    }
    return count > 0 ? sum / count : 0;
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
   * @returns {boolean}
   */
  #isDuplicateLevel(level, direction, index) {
    const lookback = Number(this._getParam('swingLookback'));
    const window = lookback * 2;
    /** @type {LevelSignalRecord[]} */
    const recent = this._getState('recentLevels') ?? [];

    return recent.some(
      (r) =>
        r.direction === direction &&
        Math.abs(r.level - level) < pipsToPrice(0.5, 'EURUSD') &&
        index - r.barIndex <= window
    );
  }
}
