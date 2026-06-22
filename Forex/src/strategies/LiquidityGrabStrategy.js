/**
 * Liquidity Grab strategy plugin (skeleton — logic in Phase 5).
 * @module strategies/LiquidityGrabStrategy
 */

import { BaseStrategy } from '../strategy/BaseStrategy.js';

/**
 * Identifies stop hunts beyond swing highs/lows with rejection.
 * Full specification and algorithm — Phase 5.
 */
export class LiquidityGrabStrategy extends BaseStrategy {
  static id = 'liquidity-grab';
  static name = 'Liquidity Grab';
  static description = 'Trade false breakouts that grab liquidity beyond swing points.';
  static version = '0.1.0';
  static category = 'Price Action';

  /**
   * @returns {import('../strategy/ParameterSchema.js').ParamDefinition[]}
   */
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
    this._setState('swingHigh', null);
    this._setState('swingLow', null);
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   */
  calculate(candles, index) {
    const lookback = Number(this._getParam('swingLookback'));
    if (index < lookback) return;

    const slice = candles.slice(index - lookback, index);
    this._setState('swingHigh', Math.max(...slice.map((c) => c.high)));
    this._setState('swingLow', Math.min(...slice.map((c) => c.low)));
  }

  /**
   * @param {import('../strategy/StrategyContext.js').StrategyContext} ctx
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  generateSignal(ctx) {
    // Phase 5: implement full Liquidity Grab specification
    return null;
  }
}
