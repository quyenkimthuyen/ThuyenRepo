/**
 * Session Liquidity Sweep — Asian range sweeps during London/overlap with volatility filter.
 * Designed for EURUSD H1-style session structure; works on any symbol/timeframe.
 * @module strategies/SessionLiquiditySweepStrategy
 */

import { BaseStrategy } from '../strategy/BaseStrategy.js';
import { createSignal } from '../strategy/Signal.js';
import { pipsToPrice, formatPrice, priceToPips } from '../utils/pip.js';
import { swingHigh, swingLow } from '../strategy/helpers/SwingLevels.js';
import {
  getCandleRange,
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
 * @returns {number}
 */
function utcHour(timestamp) {
  return new Date(timestamp).getUTCHours();
}

/**
 * @param {number} timestamp
 * @returns {string}
 */
function utcDayKey(timestamp) {
  return new Date(timestamp).toISOString().slice(0, 10);
}

/**
 * Trades liquidity sweeps of the Asian session range during active UTC hours.
 */
export class SessionLiquiditySweepStrategy extends BaseStrategy {
  static id = 'session-liquidity-sweep';
  static name = 'Session Liquidity Sweep';
  static description =
    'Fade sweeps of the Asian session range during London/overlap when volatility is active.';
  static version = '1.0.0';
  static category = 'Price Action';

  getParameterSchema() {
    return [
      {
        key: 'asianEndHour',
        label: 'Asian End Hour (UTC)',
        type: 'integer',
        default: 7,
        min: 5,
        max: 9,
        description: 'Asian range ends before this UTC hour (H1: bars 00–06 when set to 7)',
      },
      {
        key: 'sessionStartHour',
        label: 'Session Start (UTC)',
        type: 'integer',
        default: 7,
        min: 0,
        max: 23,
      },
      {
        key: 'sessionEndHour',
        label: 'Session End (UTC)',
        type: 'integer',
        default: 17,
        min: 1,
        max: 24,
      },
      {
        key: 'grabPips',
        label: 'Grab Distance (pips)',
        type: 'number',
        default: 6,
        min: 2,
        max: 20,
        step: 0.5,
      },
      {
        key: 'wickRatio',
        label: 'Min Wick Ratio',
        type: 'number',
        default: 0.65,
        min: 0.4,
        max: 0.9,
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
        key: 'swingLookback',
        label: 'Swing Lookback',
        type: 'integer',
        default: 10,
        min: 5,
        max: 25,
        description: 'Fallback liquidity level when Asian range is not ready',
      },
      {
        key: 'minVolatilityRatio',
        label: 'Min Volatility Ratio',
        type: 'number',
        default: 0.85,
        min: 0.5,
        max: 2,
        step: 0.1,
        description: '14-bar avg range must be >= ratio × median of recent windows',
      },
      {
        key: 'volatilityLookback',
        label: 'Volatility Lookback',
        type: 'integer',
        default: 14,
        min: 5,
        max: 30,
      },
    ];
  }

  getWarmupBars() {
    const swing = Number(this._getParam('swingLookback') ?? 10);
    const volLb = Number(this._getParam('volatilityLookback') ?? 14);
    return swing + volLb + 60;
  }

  onInitialize() {
    this._setState('recentLevels', []);
    this._setState('asianDay', null);
    this._setState('asianHigh', null);
    this._setState('asianLow', null);
    this._setState('asianComplete', false);
    this._setState('volOk', false);
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   */
  calculate(candles, index) {
    const candle = candles[index];
    const symbol = /** @type {string} */ (this._getState('symbol') ?? 'EURUSD');
    const asianEndHour = Number(this._getParam('asianEndHour'));
    const swingLookback = Number(this._getParam('swingLookback'));
    const hour = utcHour(candle.timestamp);
    const day = utcDayKey(candle.timestamp);

    this.#updateAsianRange(candle, hour, day, asianEndHour);
    this.#updateVolatility(candles, index, symbol);
    this.#pruneRecentLevels(index, swingLookback);

    this._setState('levelHigh', swingHigh(candles, index, swingLookback));
    this._setState('levelLow', swingLow(candles, index, swingLookback));
  }

  /**
   * @param {import('../strategy/StrategyContext.js').StrategyContext} ctx
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  generateSignal(ctx) {
    const { index, candles, symbol, timeframe } = ctx;
    const hour = utcHour(candles[index].timestamp);
    const sessionStart = Number(this._getParam('sessionStartHour'));
    const sessionEnd = Number(this._getParam('sessionEndHour'));

    if (hour < sessionStart || hour >= sessionEnd) return null;
    if (!this._getState('volOk')) return null;

    const levels = this.#resolveLiquidityLevels(candles[index].timestamp, hour);
    if (!levels) return null;

    const grabPips = Number(this._getParam('grabPips'));
    const minWickRatio = Number(this._getParam('wickRatio'));
    const rr = Number(this._getParam('rr'));
    const pip = pipsToPrice(1, symbol);
    const candle = candles[index];
    const avgVolume = this.#avgVolume(candles, index, Number(this._getParam('swingLookback')));
    const volumeOk = candle.volume === 0 || candle.volume >= 0.8 * avgVolume;

    const shortSignal = this.#checkShort(
      candle,
      levels.high,
      levels.highSource,
      grabPips,
      pip,
      minWickRatio,
      volumeOk,
      avgVolume,
      symbol,
      rr,
      index,
      timeframe
    );
    if (shortSignal) {
      this.#recordLevel(levels.high, 'short', index);
      return shortSignal;
    }

    const longSignal = this.#checkLong(
      candle,
      levels.low,
      levels.lowSource,
      grabPips,
      pip,
      minWickRatio,
      volumeOk,
      avgVolume,
      symbol,
      rr,
      index,
      timeframe
    );
    if (longSignal) {
      this.#recordLevel(levels.low, 'long', index);
      return longSignal;
    }

    return null;
  }

  /**
   * @param {import('../data/Candle.js').Candle} candle
   * @param {number} hour
   * @param {string} day
   * @param {number} asianEndHour
   */
  #updateAsianRange(candle, hour, day, asianEndHour) {
    const prevDay = this._getState('asianDay');

    if (hour < asianEndHour) {
      if (prevDay !== day) {
        this._setState('asianDay', day);
        this._setState('asianHigh', candle.high);
        this._setState('asianLow', candle.low);
        this._setState('asianComplete', false);
      } else {
        const high = /** @type {number} */ (this._getState('asianHigh'));
        const low = /** @type {number} */ (this._getState('asianLow'));
        this._setState('asianHigh', Math.max(high, candle.high));
        this._setState('asianLow', Math.min(low, candle.low));
      }
      return;
    }

    if (prevDay === day && !this._getState('asianComplete')) {
      const high = this._getState('asianHigh');
      const low = this._getState('asianLow');
      if (typeof high === 'number' && typeof low === 'number') {
        this._setState('asianComplete', true);
      }
    }
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   * @param {string} symbol
   */
  #updateVolatility(candles, index, symbol) {
    const lb = Number(this._getParam('volatilityLookback'));
    const minRatio = Number(this._getParam('minVolatilityRatio'));
    const medianBars = 50;

    if (index < lb + medianBars - 1) {
      this._setState('volOk', false);
      return;
    }

    let currentSum = 0;
    for (let j = index - lb + 1; j <= index; j++) {
      currentSum += priceToPips(getCandleRange(candles[j]), symbol);
    }
    const currentAvg = currentSum / lb;

    /** @type {number[]} */
    const windowAvgs = [];
    for (let w = 0; w < medianBars; w++) {
      const end = index - w;
      if (end < lb - 1) break;
      let sum = 0;
      for (let j = end - lb + 1; j <= end; j++) {
        sum += priceToPips(getCandleRange(candles[j]), symbol);
      }
      windowAvgs.push(sum / lb);
    }

    if (!windowAvgs.length) {
      this._setState('volOk', false);
      return;
    }

    windowAvgs.sort((a, b) => a - b);
    const median = windowAvgs[Math.floor(windowAvgs.length / 2)];
    this._setState('volOk', currentAvg >= minRatio * median);
  }

  /**
   * @param {number} timestamp
   * @param {number} hour
   * @returns {{ high: number, low: number, highSource: string, lowSource: string }|null}
   */
  #resolveLiquidityLevels(timestamp, hour) {
    const asianEndHour = Number(this._getParam('asianEndHour'));
    const day = utcDayKey(timestamp);
    const swingHighLevel = /** @type {number|null} */ (this._getState('levelHigh'));
    const swingLowLevel = /** @type {number|null} */ (this._getState('levelLow'));

    const asianReady =
      hour >= asianEndHour &&
      this._getState('asianDay') === day &&
      this._getState('asianComplete') === true;

    const asianHigh = /** @type {number|null} */ (this._getState('asianHigh'));
    const asianLow = /** @type {number|null} */ (this._getState('asianLow'));

    const high = asianReady && asianHigh != null ? asianHigh : swingHighLevel;
    const low = asianReady && asianLow != null ? asianLow : swingLowLevel;

    if (high == null || low == null) return null;

    return {
      high,
      low,
      highSource: asianReady && asianHigh != null ? 'asian' : 'swing',
      lowSource: asianReady && asianLow != null ? 'asian' : 'swing',
    };
  }

  /**
   * @param {number} index
   * @param {number} swingLookback
   */
  #pruneRecentLevels(index, swingLookback) {
    /** @type {LevelSignalRecord[]} */
    const recent = this._getState('recentLevels') ?? [];
    const window = swingLookback * 2;
    this._setState(
      'recentLevels',
      recent.filter((r) => index - r.barIndex <= window)
    );
  }

  /**
   * @param {import('../data/Candle.js').Candle} candle
   * @param {number} levelHigh
   * @param {string} levelSource
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
  #checkShort(
    candle,
    levelHigh,
    levelSource,
    grabPips,
    pip,
    minWickRatio,
    volumeOk,
    avgVolume,
    symbol,
    rr,
    index,
    timeframe
  ) {
    if (this.#isDuplicateLevel(levelHigh, 'short', index, symbol)) return null;
    if (!volumeOk) return null;
    if (candle.high < levelHigh + grabPips * pip) return null;
    if (candle.close >= levelHigh) return null;

    const wicks = getWicks(candle);
    if (wicks.range <= 0 || wicks.upper / wicks.range < minWickRatio) return null;
    if (!isBearishConfirmation(candle, symbol)) return null;

    const levels = buildShortLevels(candle.close, slBufferAbove(candle.high, symbol), rr);
    const closeDistPips = priceToPips(levelHigh - candle.close, symbol);
    const confidence = computeConfidence(candle.timestamp, rr, {
      qualityWick: wicks.upper / wicks.range >= 0.7,
      preciseLocation: closeDistPips <= 2,
      extraPoints:
        (levelSource === 'asian' ? 15 : 0) +
        (wicks.upper / wicks.range >= 0.7 ? 10 : 0) +
        (grabPips >= 5 ? 10 : 0) +
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
      reason: `Session sweep short: ${levelSource} high ${formatPrice(levelHigh, symbol)}, bar ${index}`,
      screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
      strategyId: SessionLiquiditySweepStrategy.id,
      setup: {
        levels: [{ kind: 'liquidity', label: `${levelSource} high`, price: levelHigh }],
        markers: [{ label: 'Sweep + reject', time: candle.timestamp, role: 'sweep' }],
        steps: [
          '1. Asian range high (or swing) defines liquidity',
          '2. London/overlap sweeps above with rejection wick',
          '3. Short on bearish confirmation',
        ],
      },
    });
  }

  /**
   * @param {import('../data/Candle.js').Candle} candle
   * @param {number} levelLow
   * @param {string} levelSource
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
  #checkLong(
    candle,
    levelLow,
    levelSource,
    grabPips,
    pip,
    minWickRatio,
    volumeOk,
    avgVolume,
    symbol,
    rr,
    index,
    timeframe
  ) {
    if (this.#isDuplicateLevel(levelLow, 'long', index, symbol)) return null;
    if (!volumeOk) return null;
    if (candle.low > levelLow - grabPips * pip) return null;
    if (candle.close <= levelLow) return null;

    const wicks = getWicks(candle);
    if (wicks.range <= 0 || wicks.lower / wicks.range < minWickRatio) return null;
    if (!isBullishConfirmation(candle, symbol)) return null;

    const levels = buildLongLevels(candle.close, slBufferBelow(candle.low, symbol), rr);
    const closeDistPips = priceToPips(candle.close - levelLow, symbol);
    const confidence = computeConfidence(candle.timestamp, rr, {
      qualityWick: wicks.lower / wicks.range >= 0.7,
      preciseLocation: closeDistPips <= 2,
      extraPoints:
        (levelSource === 'asian' ? 15 : 0) +
        (wicks.lower / wicks.range >= 0.7 ? 10 : 0) +
        (grabPips >= 5 ? 10 : 0) +
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
      reason: `Session sweep long: ${levelSource} low ${formatPrice(levelLow, symbol)}, bar ${index}`,
      screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
      strategyId: SessionLiquiditySweepStrategy.id,
      setup: {
        levels: [{ kind: 'liquidity', label: `${levelSource} low`, price: levelLow }],
        markers: [{ label: 'Sweep + reject', time: candle.timestamp, role: 'sweep' }],
        steps: [
          '1. Asian range low (or swing) defines liquidity',
          '2. London/overlap sweeps below with rejection wick',
          '3. Long on bullish confirmation',
        ],
      },
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
   * @param {string} symbol
   * @returns {boolean}
   */
  #isDuplicateLevel(level, direction, index, symbol) {
    const lookback = Number(this._getParam('swingLookback'));
    const window = lookback * 2;
    /** @type {LevelSignalRecord[]} */
    const recent = this._getState('recentLevels') ?? [];

    return recent.some(
      (r) =>
        r.direction === direction &&
        Math.abs(r.level - level) < pipsToPrice(0.5, symbol) &&
        index - r.barIndex <= window
    );
  }
}
