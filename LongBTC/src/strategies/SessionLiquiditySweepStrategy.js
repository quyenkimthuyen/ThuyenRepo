/**
 * Session Liquidity Sweep v1.2 — session-focused sweeps with quality filters.
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
 * @typedef {Object} PendingSweep
 * @property {'long'|'short'} direction
 * @property {number} level
 * @property {string} levelSource
 * @property {number} sweepBar
 * @property {number} sweepHigh
 * @property {number} sweepLow
 * @property {number} expiresAtBar
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
 * Session liquidity sweeps with pending confirmation and multiple level sources.
 */
export class SessionLiquiditySweepStrategy extends BaseStrategy {
  static id = 'session-liquidity-sweep';
  static name = 'Session Liquidity Sweep';
  static description =
    'Fade liquidity sweeps at Asian/London session levels during London hours (2-phase confirmation).';
  static version = '1.2.0';
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
      },
      {
        key: 'londonEndHour',
        label: 'London End Hour (UTC)',
        type: 'integer',
        default: 12,
        min: 8,
        max: 16,
        description: 'London morning range ends before this hour — used for overlap/NY sweeps',
      },
      {
        key: 'sessionStartHour',
        label: 'Session Start (UTC)',
        type: 'integer',
        default: 6,
        min: 0,
        max: 23,
        description: 'Earliest hour to detect sweeps and enter',
      },
      {
        key: 'sessionEndHour',
        label: 'Session End (UTC)',
        type: 'integer',
        default: 20,
        min: 1,
        max: 24,
        description: 'No new sweeps/entries from this hour onward',
      },
      {
        key: 'grabPips',
        label: 'Grab Distance (pips)',
        type: 'number',
        default: 5,
        min: 2,
        max: 20,
        step: 0.5,
      },
      {
        key: 'wickRatio',
        label: 'Min Sweep Wick Ratio',
        type: 'number',
        default: 0.6,
        min: 0.35,
        max: 0.9,
        step: 0.05,
        description: 'Wick on the sweep candle',
      },
      {
        key: 'confirmMaxBars',
        label: 'Confirm Max Bars',
        type: 'integer',
        default: 1,
        min: 1,
        max: 8,
        description: 'Bars after sweep to wait for confirmation entry',
      },
      {
        key: 'rr',
        label: 'Risk Reward',
        type: 'number',
        default: 1.5,
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
      },
      {
        key: 'minVolatilityRatio',
        label: 'Min Volatility Ratio',
        type: 'number',
        default: 1.1,
        min: 0.5,
        max: 2,
        step: 0.1,
      },
      {
        key: 'volatilityLookback',
        label: 'Volatility Lookback',
        type: 'integer',
        default: 14,
        min: 5,
        max: 30,
      },
      {
        key: 'usePrevAsian',
        label: 'Use Previous Asian Range',
        type: 'boolean',
        default: true,
        description: 'Also sweep prior day Asian high/low during early London',
      },
      {
        key: 'useSwingLevels',
        label: 'Use Swing Levels',
        type: 'boolean',
        default: false,
        description: 'Fallback to swing high/low when session levels unavailable',
      },
      {
        key: 'minSessionRangePips',
        label: 'Min Session Range (pips)',
        type: 'number',
        default: 0,
        min: 0,
        max: 40,
        step: 1,
        description: 'Skip Asian/London range if high-low is narrower than this (0 = off)',
      },
      {
        key: 'maxVolatilityRatio',
        label: 'Max Volatility Ratio',
        type: 'number',
        default: 0,
        min: 0,
        max: 3,
        step: 0.05,
        description: '0 = off; skip when avg range exceeds ratio × median (extreme vol)',
      },
      {
        key: 'confirmClosePips',
        label: 'Confirm Close Beyond Level (pips)',
        type: 'number',
        default: 0,
        min: 0,
        max: 10,
        step: 0.5,
        description: 'Confirmation close must be this many pips past the swept level (0 = off)',
      },
      {
        key: 'tradeCooldownBars',
        label: 'Trade Cooldown (bars)',
        type: 'integer',
        default: 0,
        min: 0,
        max: 48,
        description: 'Minimum bars between entries (reduces clustered trades)',
      },
    ];
  }

  getWarmupBars() {
    const swing = Number(this._getParam('swingLookback') ?? 8);
    const volLb = Number(this._getParam('volatilityLookback') ?? 14);
    return swing + volLb + 60;
  }

  onInitialize() {
    this._setState('recentLevels', []);
    this._setState('asianDay', null);
    this._setState('asianHigh', null);
    this._setState('asianLow', null);
    this._setState('asianComplete', false);
    this._setState('prevAsianHigh', null);
    this._setState('prevAsianLow', null);
    this._setState('londonDay', null);
    this._setState('londonHigh', null);
    this._setState('londonLow', null);
    this._setState('londonComplete', false);
    this._setState('pendingSweeps', /** @type {PendingSweep[]} */ ([]));
    this._setState('volOk', false);
    this._setState('lastEntryBar', -9999);
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   */
  calculate(candles, index) {
    const candle = candles[index];
    const symbol = /** @type {string} */ (this._getState('symbol') ?? 'EURUSD');
    const asianEndHour = Number(this._getParam('asianEndHour'));
    const londonEndHour = Number(this._getParam('londonEndHour'));
    const swingLookback = Number(this._getParam('swingLookback'));
    const hour = utcHour(candle.timestamp);
    const day = utcDayKey(candle.timestamp);

    this.#updateAsianRange(candle, hour, day, asianEndHour);
    this.#updateLondonRange(candle, hour, day, asianEndHour, londonEndHour);
    this.#updateVolatility(candles, index, symbol);
    this.#pruneRecentLevels(index, swingLookback);
    this.#prunePending(index);

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

    const cooldown = Number(this._getParam('tradeCooldownBars'));
    const lastEntry = Number(this._getState('lastEntryBar') ?? -9999);
    if (index - lastEntry < cooldown) return null;

    const candle = candles[index];
    const grabPips = Number(this._getParam('grabPips'));
    const minWickRatio = Number(this._getParam('wickRatio'));
    const rr = Number(this._getParam('rr'));
    const pip = pipsToPrice(1, symbol);
    const confirmMaxBars = Number(this._getParam('confirmMaxBars'));

    const confirmSignal = this.#tryConfirmPending(candle, symbol, rr, index, timeframe);
    if (confirmSignal) return confirmSignal;

    const levelSets = this.#collectLiquidityLevels(candles[index].timestamp, hour, symbol);
    let armedShort = false;
    let armedLong = false;

    for (const levels of levelSets) {
      if (!armedShort) {
        const sweptShort = this.#detectSweepShort(
          candle, levels.high, levels.highSource, grabPips, pip, minWickRatio, symbol, index
        );
        if (sweptShort) {
          this.#addPending({
            direction: 'short',
            level: levels.high,
            levelSource: levels.highSource,
            sweepBar: index,
            sweepHigh: candle.high,
            sweepLow: candle.low,
            expiresAtBar: index + confirmMaxBars,
          });
          armedShort = true;
        }
      }

      if (!armedLong) {
        const sweptLong = this.#detectSweepLong(
          candle, levels.low, levels.lowSource, grabPips, pip, minWickRatio, symbol, index
        );
        if (sweptLong) {
          this.#addPending({
            direction: 'long',
            level: levels.low,
            levelSource: levels.lowSource,
            sweepBar: index,
            sweepHigh: candle.high,
            sweepLow: candle.low,
            expiresAtBar: index + confirmMaxBars,
          });
          armedLong = true;
        }
      }

      if (armedShort && armedLong) break;
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
        if (prevDay != null && this._getState('asianComplete')) {
          this._setState('prevAsianHigh', this._getState('asianHigh'));
          this._setState('prevAsianLow', this._getState('asianLow'));
        }
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
   * @param {import('../data/Candle.js').Candle} candle
   * @param {number} hour
   * @param {string} day
   * @param {number} asianEndHour
   * @param {number} londonEndHour
   */
  #updateLondonRange(candle, hour, day, asianEndHour, londonEndHour) {
    const inLondon = hour >= asianEndHour && hour < londonEndHour;
    const prevDay = this._getState('londonDay');

    if (inLondon) {
      if (prevDay !== day) {
        this._setState('londonDay', day);
        this._setState('londonHigh', candle.high);
        this._setState('londonLow', candle.low);
        this._setState('londonComplete', false);
      } else {
        const high = /** @type {number} */ (this._getState('londonHigh'));
        const low = /** @type {number} */ (this._getState('londonLow'));
        this._setState('londonHigh', Math.max(high, candle.high));
        this._setState('londonLow', Math.min(low, candle.low));
      }
      return;
    }

    if (hour >= londonEndHour && prevDay === day && !this._getState('londonComplete')) {
      const high = this._getState('londonHigh');
      const low = this._getState('londonLow');
      if (typeof high === 'number' && typeof low === 'number') {
        this._setState('londonComplete', true);
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
    const maxRatio = Number(this._getParam('maxVolatilityRatio'));
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
    const aboveMin = currentAvg >= minRatio * median;
    const belowMax = maxRatio <= 0 || currentAvg <= maxRatio * median;
    this._setState('volOk', aboveMin && belowMax);
  }

  /**
   * @param {number} high
   * @param {number} low
   * @param {string} symbol
   * @returns {boolean}
   */
  #isSessionRangeWideEnough(high, low, symbol) {
    const minPips = Number(this._getParam('minSessionRangePips'));
    if (minPips <= 0) return true;
    return priceToPips(high - low, symbol) >= minPips;
  }

  /**
   * @param {number} timestamp
   * @param {number} hour
   * @param {string} symbol
   * @returns {{ high: number, low: number, highSource: string, lowSource: string }[]}
   */
  #collectLiquidityLevels(timestamp, hour, symbol) {
    const asianEndHour = Number(this._getParam('asianEndHour'));
    const londonEndHour = Number(this._getParam('londonEndHour'));
    const usePrevAsian = Boolean(this._getParam('usePrevAsian'));
    const useSwingLevels = Boolean(this._getParam('useSwingLevels'));
    const day = utcDayKey(timestamp);
    const swingHighLevel = /** @type {number|null} */ (this._getState('levelHigh'));
    const swingLowLevel = /** @type {number|null} */ (this._getState('levelLow'));

    /** @type {{ high: number, low: number, highSource: string, lowSource: string }[]} */
    const sets = [];

    const asianReady =
      hour >= asianEndHour &&
      this._getState('asianDay') === day &&
      this._getState('asianComplete') === true;
    const asianHigh = /** @type {number|null} */ (this._getState('asianHigh'));
    const asianLow = /** @type {number|null} */ (this._getState('asianLow'));

    if (asianReady && asianHigh != null && asianLow != null && this.#isSessionRangeWideEnough(asianHigh, asianLow, symbol)) {
      sets.push({ high: asianHigh, low: asianLow, highSource: 'asian', lowSource: 'asian' });
    }

    if (usePrevAsian && hour >= asianEndHour && hour < londonEndHour + 2) {
      const prevHigh = /** @type {number|null} */ (this._getState('prevAsianHigh'));
      const prevLow = /** @type {number|null} */ (this._getState('prevAsianLow'));
      if (
        prevHigh != null &&
        prevLow != null &&
        this.#isSessionRangeWideEnough(prevHigh, prevLow, symbol)
      ) {
        sets.push({ high: prevHigh, low: prevLow, highSource: 'prev-asian', lowSource: 'prev-asian' });
      }
    }

    const londonReady =
      hour >= londonEndHour &&
      this._getState('londonDay') === day &&
      this._getState('londonComplete') === true;
    const londonHigh = /** @type {number|null} */ (this._getState('londonHigh'));
    const londonLow = /** @type {number|null} */ (this._getState('londonLow'));

    if (
      londonReady &&
      londonHigh != null &&
      londonLow != null &&
      this.#isSessionRangeWideEnough(londonHigh, londonLow, symbol)
    ) {
      sets.push({ high: londonHigh, low: londonLow, highSource: 'london', lowSource: 'london' });
    }

    if (useSwingLevels && swingHighLevel != null && swingLowLevel != null) {
      sets.push({
        high: swingHighLevel,
        low: swingLowLevel,
        highSource: 'swing',
        lowSource: 'swing',
      });
    }

    return sets;
  }

  /**
   * @param {import('../data/Candle.js').Candle} candle
   * @param {number} levelHigh
   * @param {string} levelSource
   * @param {number} grabPips
   * @param {number} pip
   * @param {number} minWickRatio
   * @param {string} symbol
   * @param {number} index
   * @returns {boolean}
   */
  #detectSweepShort(candle, levelHigh, levelSource, grabPips, pip, minWickRatio, symbol, index) {
    if (this.#isDuplicateLevel(levelHigh, 'short', symbol, index)) return false;
    if (candle.high < levelHigh + grabPips * pip) return false;
    if (candle.close >= levelHigh) return false;

    const wicks = getWicks(candle);
    if (wicks.range <= 0 || wicks.upper / wicks.range < minWickRatio) return false;

    return true;
  }

  /**
   * @param {import('../data/Candle.js').Candle} candle
   * @param {number} levelLow
   * @param {string} levelSource
   * @param {number} grabPips
   * @param {number} pip
   * @param {number} minWickRatio
   * @param {string} symbol
   * @param {number} index
   * @returns {boolean}
   */
  #detectSweepLong(candle, levelLow, levelSource, grabPips, pip, minWickRatio, symbol, index) {
    if (this.#isDuplicateLevel(levelLow, 'long', symbol, index)) return false;
    if (candle.low > levelLow - grabPips * pip) return false;
    if (candle.close <= levelLow) return false;

    const wicks = getWicks(candle);
    if (wicks.range <= 0 || wicks.lower / wicks.range < minWickRatio) return false;

    return true;
  }

  /**
   * @param {import('../data/Candle.js').Candle} candle
   * @param {string} symbol
   * @param {number} rr
   * @param {number} index
   * @param {string} timeframe
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  #tryConfirmPending(candle, symbol, rr, index, timeframe) {
    /** @type {PendingSweep[]} */
    const pending = this._getState('pendingSweeps') ?? [];
    const pip = pipsToPrice(1, symbol);
    const confirmClosePips = Number(this._getParam('confirmClosePips'));

    for (const setup of pending) {
      if (index <= setup.sweepBar || index > setup.expiresAtBar) continue;
      if (this.#isDuplicateLevel(setup.level, setup.direction, symbol, index)) continue;

      if (setup.direction === 'short') {
        if (candle.high > setup.sweepHigh) continue;
        if (candle.close >= setup.level) continue;
        if (confirmClosePips > 0 && candle.close > setup.level - confirmClosePips * pip) continue;
        if (!isBearishConfirmation(candle, symbol)) continue;

        const levels = buildShortLevels(candle.close, slBufferAbove(setup.sweepHigh, symbol), rr);
        this.#recordLevel(setup.level, 'short', index);
        this._setState('pendingSweeps', pending.filter((p) => p !== setup));
        this._setState('lastEntryBar', index);

        return createSignal({
          time: candle.timestamp,
          pair: symbol,
          timeframe,
          direction: 'short',
          entry: levels.entry,
          sl: levels.sl,
          tp: levels.tp,
          rr,
          confidence: this.#buildConfidence(candle.timestamp, rr, setup, symbol),
          reason: `Session sweep short: ${setup.levelSource} ${formatPrice(setup.level, symbol)}, confirm bar ${index}`,
          screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
          strategyId: SessionLiquiditySweepStrategy.id,
          setup: {
            levels: [{ kind: 'liquidity', label: `${setup.levelSource} high`, price: setup.level }],
            markers: [
              { label: 'Sweep', time: candle.timestamp, role: 'sweep' },
              { label: 'Confirm', time: candle.timestamp, role: 'confirm' },
            ],
            steps: [
              '1. Liquidity sweep beyond session/swing level',
              '2. Wait for bearish confirmation (1–3 bars)',
              '3. Short with SL above sweep high',
            ],
          },
        });
      }

      if (setup.direction === 'long') {
        if (candle.low < setup.sweepLow) continue;
        if (candle.close <= setup.level) continue;
        if (confirmClosePips > 0 && candle.close < setup.level + confirmClosePips * pip) continue;
        if (!isBullishConfirmation(candle, symbol)) continue;

        const levels = buildLongLevels(candle.close, slBufferBelow(setup.sweepLow, symbol), rr);
        this.#recordLevel(setup.level, 'long', index);
        this._setState('pendingSweeps', pending.filter((p) => p !== setup));
        this._setState('lastEntryBar', index);

        return createSignal({
          time: candle.timestamp,
          pair: symbol,
          timeframe,
          direction: 'long',
          entry: levels.entry,
          sl: levels.sl,
          tp: levels.tp,
          rr,
          confidence: this.#buildConfidence(candle.timestamp, rr, setup, symbol),
          reason: `Session sweep long: ${setup.levelSource} ${formatPrice(setup.level, symbol)}, confirm bar ${index}`,
          screenshotPosition: { candleIndex: index, timestamp: candle.timestamp },
          strategyId: SessionLiquiditySweepStrategy.id,
          setup: {
            levels: [{ kind: 'liquidity', label: `${setup.levelSource} low`, price: setup.level }],
            markers: [
              { label: 'Sweep', time: candle.timestamp, role: 'sweep' },
              { label: 'Confirm', time: candle.timestamp, role: 'confirm' },
            ],
            steps: [
              '1. Liquidity sweep beyond session/swing level',
              '2. Wait for bullish confirmation (1–3 bars)',
              '3. Long with SL below sweep low',
            ],
          },
        });
      }
    }

    return null;
  }

  /**
   * @param {number} timestamp
   * @param {number} rr
   * @param {PendingSweep} setup
   * @param {string} symbol
   * @returns {number}
   */
  #buildConfidence(timestamp, rr, setup, symbol) {
    const closeDistPips =
      setup.direction === 'short'
        ? priceToPips(setup.level - setup.sweepLow, symbol)
        : priceToPips(setup.sweepHigh - setup.level, symbol);

    return computeConfidence(timestamp, rr, {
      qualityWick: true,
      preciseLocation: closeDistPips <= 3,
      extraPoints:
        (setup.levelSource === 'asian' || setup.levelSource === 'prev-asian' ? 15 : 10) +
        (setup.levelSource === 'london' ? 8 : 0) +
        (closeDistPips <= 3 ? 10 : 0),
    });
  }

  /**
   * @param {PendingSweep} setup
   */
  #addPending(setup) {
    /** @type {PendingSweep[]} */
    const pending = this._getState('pendingSweeps') ?? [];
    const tol = pipsToPrice(1, 'EURUSD');
    const exists = pending.some(
      (p) =>
        p.direction === setup.direction &&
        Math.abs(p.level - setup.level) < tol &&
        setup.sweepBar - p.sweepBar <= 3
    );
    if (exists) return;

    pending.push(setup);
    this._setState('pendingSweeps', pending);
  }

  /**
   * @param {number} index
   */
  #prunePending(index) {
    /** @type {PendingSweep[]} */
    const pending = this._getState('pendingSweeps') ?? [];
    this._setState(
      'pendingSweeps',
      pending.filter((p) => index <= p.expiresAtBar)
    );
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
   * @returns {boolean}
   */
  #isDuplicateLevel(level, direction, symbol, index) {
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
