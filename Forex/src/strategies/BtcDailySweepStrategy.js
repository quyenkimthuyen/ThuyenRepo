/**
 * BTC Daily Sweep — fade sweeps of previous UTC day high/low (minimal PA, D1-focused).
 * @module strategies/BtcDailySweepStrategy
 */

import { BaseStrategy } from '../strategy/BaseStrategy.js';
import { createSignal } from '../strategy/Signal.js';
import { pipsToPrice, formatPrice, priceToPips } from '../utils/pip.js';
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
 * @param {number} timestamp
 * @returns {string}
 */
function utcDayKey(timestamp) {
  return new Date(timestamp).toISOString().slice(0, 10);
}

/**
 * Fade liquidity grabs beyond yesterday's high/low — built for BTCUSD D1.
 */
export class BtcDailySweepStrategy extends BaseStrategy {
  static id = 'btc-daily-sweep';
  static name = 'BTC Daily Sweep';
  static description =
    'Fade false breakouts that sweep the previous UTC day high or low (BTC D1, minimal params).';
  static version = '1.0.0';
  static category = 'Price Action';

  getParameterSchema() {
    return [
      {
        key: 'grabPips',
        label: 'Grab Distance (pips)',
        type: 'number',
        default: 100,
        min: 10,
        max: 500,
        step: 10,
        description: 'Min distance beyond prev-day level (BTC: 1 pip = $1)',
      },
      {
        key: 'wickRatio',
        label: 'Min Wick Ratio',
        type: 'number',
        default: 0.6,
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
        max: 5,
        step: 0.5,
      },
      {
        key: 'minDayRangePips',
        label: 'Min Prev-Day Range (pips)',
        type: 'number',
        default: 700,
        min: 0,
        max: 3000,
        step: 50,
        description: 'Skip if yesterday high-low narrower than this (0 = off)',
      },
    ];
  }

  getWarmupBars() {
    return 2;
  }

  onInitialize() {
    this._setState('dayKey', null);
    this._setState('dayHigh', null);
    this._setState('dayLow', null);
    this._setState('prevDayHigh', null);
    this._setState('prevDayLow', null);
    this._setState('prevDayReady', false);
    this._setState('recentLevels', /** @type {LevelSignalRecord[]} */ ([]));
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   */
  calculate(candles, index) {
    const candle = candles[index];
    const day = utcDayKey(candle.timestamp);
    const prevDay = this._getState('dayKey');

    if (prevDay !== day) {
      if (prevDay != null) {
        const high = this._getState('dayHigh');
        const low = this._getState('dayLow');
        if (typeof high === 'number' && typeof low === 'number') {
          this._setState('prevDayHigh', high);
          this._setState('prevDayLow', low);
          this._setState('prevDayReady', true);
        }
      }
      this._setState('dayKey', day);
      this._setState('dayHigh', candle.high);
      this._setState('dayLow', candle.low);
    } else {
      const high = /** @type {number} */ (this._getState('dayHigh'));
      const low = /** @type {number} */ (this._getState('dayLow'));
      this._setState('dayHigh', Math.max(high, candle.high));
      this._setState('dayLow', Math.min(low, candle.low));
    }

    /** @type {LevelSignalRecord[]} */
    let recent = this._getState('recentLevels') ?? [];
    recent = recent.filter((r) => index - r.barIndex <= 10);
    this._setState('recentLevels', recent);
  }

  /**
   * @param {import('../strategy/StrategyContext.js').StrategyContext} ctx
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  generateSignal(ctx) {
    const { index, candles, symbol, timeframe } = ctx;
    if (!this._getState('prevDayReady')) return null;

    const prevHigh = /** @type {number|null} */ (this._getState('prevDayHigh'));
    const prevLow = /** @type {number|null} */ (this._getState('prevDayLow'));
    if (prevHigh == null || prevLow == null) return null;

    const minRange = Number(this._getParam('minDayRangePips'));
    if (minRange > 0 && priceToPips(prevHigh - prevLow, symbol) < minRange) {
      return null;
    }

    const grabPips = Number(this._getParam('grabPips'));
    const minWickRatio = Number(this._getParam('wickRatio'));
    const rr = Number(this._getParam('rr'));
    const pip = pipsToPrice(1, symbol);
    const candle = candles[index];

    const shortSignal = this.#tryShort(
      candle, prevHigh, grabPips, pip, minWickRatio, rr, symbol, index, timeframe
    );
    if (shortSignal) return shortSignal;

    return this.#tryLong(
      candle, prevLow, grabPips, pip, minWickRatio, rr, symbol, index, timeframe
    );
  }

  /**
   * @param {import('../data/Candle.js').Candle} candle
   * @param {number} levelHigh
   * @param {number} grabPips
   * @param {number} pip
   * @param {number} minWickRatio
   * @param {number} rr
   * @param {string} symbol
   * @param {number} index
   * @param {string} timeframe
   */
  #tryShort(candle, levelHigh, grabPips, pip, minWickRatio, rr, symbol, index, timeframe) {
    if (this.#isDuplicateLevel(levelHigh, 'short', symbol, index)) return null;
    if (candle.high < levelHigh + grabPips * pip) return null;
    if (candle.close >= levelHigh) return null;

    const wicks = getWicks(candle);
    if (wicks.range <= 0 || wicks.upper / wicks.range < minWickRatio) return null;
    if (!isBearishConfirmation(candle, symbol)) return null;

    const levels = buildShortLevels(candle.close, slBufferAbove(candle.high, symbol), rr);
    this.#recordLevel(levelHigh, 'short', index);

    return createSignal({
      time: candle.timestamp,
      pair: symbol,
      timeframe,
      direction: 'short',
      entry: levels.entry,
      sl: levels.sl,
      tp: levels.tp,
      rr,
      confidence: computeConfidence(candle.timestamp, rr, {
        qualityWick: true,
        preciseLocation: priceToPips(candle.high - levelHigh, symbol) <= grabPips * 1.5,
        extraPoints: 12,
      }),
      reason: `Daily sweep short: prev high ${formatPrice(levelHigh, symbol)}`,
      screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
      strategyId: BtcDailySweepStrategy.id,
      setup: {
        levels: [{ kind: 'liquidity', label: 'Prev day high', price: levelHigh }],
        markers: [{ label: 'Sweep', time: candle.timestamp, role: 'sweep' }],
        steps: [
          '1. Price sweeps above previous UTC day high',
          '2. Closes back below with bearish rejection wick',
          '3. Short — SL above sweep high',
        ],
      },
    });
  }

  /**
   * @param {import('../data/Candle.js').Candle} candle
   * @param {number} levelLow
   * @param {number} grabPips
   * @param {number} pip
   * @param {number} minWickRatio
   * @param {number} rr
   * @param {string} symbol
   * @param {number} index
   * @param {string} timeframe
   */
  #tryLong(candle, levelLow, grabPips, pip, minWickRatio, rr, symbol, index, timeframe) {
    if (this.#isDuplicateLevel(levelLow, 'long', symbol, index)) return null;
    if (candle.low > levelLow - grabPips * pip) return null;
    if (candle.close <= levelLow) return null;

    const wicks = getWicks(candle);
    if (wicks.range <= 0 || wicks.lower / wicks.range < minWickRatio) return null;
    if (!isBullishConfirmation(candle, symbol)) return null;

    const levels = buildLongLevels(candle.close, slBufferBelow(candle.low, symbol), rr);
    this.#recordLevel(levelLow, 'long', index);

    return createSignal({
      time: candle.timestamp,
      pair: symbol,
      timeframe,
      direction: 'long',
      entry: levels.entry,
      sl: levels.sl,
      tp: levels.tp,
      rr,
      confidence: computeConfidence(candle.timestamp, rr, {
        qualityWick: true,
        preciseLocation: priceToPips(levelLow - candle.low, symbol) <= grabPips * 1.5,
        extraPoints: 12,
      }),
      reason: `Daily sweep long: prev low ${formatPrice(levelLow, symbol)}`,
      screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
      strategyId: BtcDailySweepStrategy.id,
      setup: {
        levels: [{ kind: 'liquidity', label: 'Prev day low', price: levelLow }],
        markers: [{ label: 'Sweep', time: candle.timestamp, role: 'sweep' }],
        steps: [
          '1. Price sweeps below previous UTC day low',
          '2. Closes back above with bullish rejection wick',
          '3. Long — SL below sweep low',
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
   * @param {string} symbol
   * @param {number} index
   */
  #isDuplicateLevel(level, direction, symbol, index) {
    /** @type {LevelSignalRecord[]} */
    const recent = this._getState('recentLevels') ?? [];
    return recent.some(
      (r) =>
        r.direction === direction &&
        Math.abs(r.level - level) < pipsToPrice(5, symbol) &&
        index - r.barIndex <= 10
    );
  }
}
