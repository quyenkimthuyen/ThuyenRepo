/**
 * Break & Retest strategy plugin (skeleton — logic in Phase 5).
 * @module strategies/BreakRetestStrategy
 */

import { BaseStrategy } from '../strategy/BaseStrategy.js';

/**
 * Identifies breakout levels followed by retest confirmation.
 * Full specification and algorithm — Phase 5.
 */
export class BreakRetestStrategy extends BaseStrategy {
  static id = 'break-retest';
  static name = 'Break & Retest';
  static description = 'Trade breakouts that retest the broken level before continuing.';
  static version = '0.1.0';
  static category = 'Price Action';

  /**
   * @returns {import('../strategy/ParameterSchema.js').ParamDefinition[]}
   */
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
    this._setState('pendingBreakout', null);
    this._setState('activeLevel', null);
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   */
  calculate(candles, index) {
    const lookback = Number(this._getParam('swingLookback'));
    if (index < lookback) return;

    const slice = candles.slice(index - lookback, index + 1);
    const highs = slice.map((c) => c.high);
    const lows = slice.map((c) => c.low);

    this._setState('recentHigh', Math.max(...highs));
    this._setState('recentLow', Math.min(...lows));
    this._setState('lastIndex', index);
  }

  /**
   * @param {import('../strategy/StrategyContext.js').StrategyContext} ctx
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  generateSignal(ctx) {
    // Phase 5: implement full Break & Retest specification
    return null;
  }
}
