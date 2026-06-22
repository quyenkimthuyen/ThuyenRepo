/**
 * EMA Pullback strategy plugin (skeleton — logic in Phase 5).
 * @module strategies/EMAPullbackStrategy
 */

import { BaseStrategy } from '../strategy/BaseStrategy.js';

/**
 * Trades pullbacks to EMA in a confirmed trend.
 * Full specification and algorithm — Phase 5.
 */
export class EMAPullbackStrategy extends BaseStrategy {
  static id = 'ema-pullback';
  static name = 'EMA Pullback';
  static description = 'Enter on pullback to EMA within a trending market.';
  static version = '0.1.0';
  static category = 'Price Action';

  /**
   * @returns {import('../strategy/ParameterSchema.js').ParamDefinition[]}
   */
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
    this._setState('emaFastValues', []);
    this._setState('emaSlowValues', []);
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   */
  calculate(candles, index) {
    const fastPeriod = Number(this._getParam('emaFast'));
    const slowPeriod = Number(this._getParam('emaSlow'));
    const visible = candles.slice(0, index + 1);

    if (visible.length < slowPeriod) return;

    this._setState('emaFast', this.#ema(visible, fastPeriod));
    this._setState('emaSlow', this.#ema(visible, slowPeriod));
    this._setState('trend', this.#detectTrend(visible));
  }

  /**
   * @param {import('../strategy/StrategyContext.js').StrategyContext} ctx
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  generateSignal(ctx) {
    // Phase 5: implement full EMA Pullback specification
    return null;
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} period
   * @returns {number}
   */
  #ema(candles, period) {
    const k = 2 / (period + 1);
    let ema = candles[0].close;
    for (let i = 1; i < candles.length; i++) {
      ema = candles[i].close * k + ema * (1 - k);
    }
    return ema;
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @returns {'up'|'down'|'none'}
   */
  #detectTrend(candles) {
    const bars = Number(this._getParam('trendBars'));
    if (candles.length < bars + 1) return 'none';

    const recent = candles.slice(-bars);
    const ups = recent.filter((c, i) => i > 0 && c.close > recent[i - 1].close).length;
    const downs = recent.filter((c, i) => i > 0 && c.close < recent[i - 1].close).length;

    if (ups > downs * 1.5) return 'up';
    if (downs > ups * 1.5) return 'down';
    return 'none';
  }
}
