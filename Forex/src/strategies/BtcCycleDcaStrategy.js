/**
 * BTC Cycle DCA — long-only accumulation on dips from rolling cycle high, percent TP, no practical SL.
 * @module strategies/BtcCycleDcaStrategy
 */

import { BaseStrategy } from '../strategy/BaseStrategy.js';
import { createSignal } from '../strategy/Signal.js';
import { formatPrice } from '../utils/pip.js';
import { calculateRR } from '../strategy/Signal.js';

/**
 * Long-term BTC D1: buy drawdowns from cycle peak (DCA tiers), exit at % gain target.
 */
export class BtcCycleDcaStrategy extends BaseStrategy {
  static id = 'btc-cycle-dca';
  static name = 'BTC Cycle DCA';
  static description =
    'Long-only BTC D1 — DCA on % dips from rolling cycle high, exit at cycle gain target (wide SL for sim only).';
  static version = '1.0.0';
  static category = 'Accumulation';

  getParameterSchema() {
    return [
      {
        key: 'lookback',
        label: 'Cycle Lookback (bars)',
        type: 'integer',
        default: 60,
        min: 20,
        max: 365,
        description: 'Rolling window for cycle high reference',
      },
      {
        key: 'dipPct',
        label: 'First Dip %',
        type: 'number',
        default: 15,
        min: 5,
        max: 50,
        step: 1,
        description: 'Buy when close is this % below cycle high',
      },
      {
        key: 'addDipPct',
        label: 'Add Dip % (DCA)',
        type: 'number',
        default: 45,
        min: 0,
        max: 70,
        step: 1,
        description: 'Second buy at deeper dip; 0 = disabled',
      },
      {
        key: 'exitGainPct',
        label: 'Exit Gain %',
        type: 'number',
        default: 70,
        min: 10,
        max: 150,
        step: 5,
        description: 'Take profit when price rises this % above entry',
      },
      {
        key: 'slFloorPct',
        label: 'Sim SL Floor %',
        type: 'number',
        default: 1,
        min: 0.1,
        max: 20,
        step: 0.5,
        description: 'SL only for simulator (1% ? no stop); not a live stop',
      },
    ];
  }

  getWarmupBars() {
    return Number(this._getParam('lookback') ?? 90) + 5;
  }

  onInitialize() {
    this._setState('cyclePeak', null);
    this._setState('dip1Used', false);
    this._setState('dip2Used', false);
    this._setState('lastPeakBar', -1);
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} index
   */
  calculate(candles, index) {
    const lookback = Number(this._getParam('lookback'));
    const start = Math.max(0, index - lookback + 1);
    let peak = candles[start].high;
    for (let i = start + 1; i <= index; i++) {
      peak = Math.max(peak, candles[i].high);
    }

    const prevPeak = /** @type {number|null} */ (this._getState('cyclePeak'));
    if (prevPeak == null || peak > prevPeak * 1.02) {
      this._setState('dip1Used', false);
      this._setState('dip2Used', false);
      this._setState('lastPeakBar', index);
    }

    this._setState('cyclePeak', peak);
  }

  /**
   * @param {import('../strategy/StrategyContext.js').StrategyContext} ctx
   * @returns {import('../strategy/Signal.js').Signal|null}
   */
  generateSignal(ctx) {
    const { index, candles, symbol, timeframe } = ctx;
    const peak = /** @type {number|null} */ (this._getState('cyclePeak'));
    if (peak == null || peak <= 0) return null;

    const dipPct = Number(this._getParam('dipPct'));
    const addDipPct = Number(this._getParam('addDipPct'));
    const exitGainPct = Number(this._getParam('exitGainPct'));
    const slFloorPct = Number(this._getParam('slFloorPct'));

    const close = candles[index].close;
    const drawdownPct = ((peak - close) / peak) * 100;

    const dip1Used = Boolean(this._getState('dip1Used'));
    const dip2Used = Boolean(this._getState('dip2Used'));

    let tier = null;
    if (!dip1Used && drawdownPct >= dipPct) {
      tier = 1;
      this._setState('dip1Used', true);
    } else if (addDipPct > 0 && dip1Used && !dip2Used && drawdownPct >= addDipPct) {
      tier = 2;
      this._setState('dip2Used', true);
    }

    if (tier == null) return null;

    const entry = close;
    const sl = entry * (slFloorPct / 100);
    const tp = entry * (1 + exitGainPct / 100);
    const rr = calculateRR('long', entry, sl, tp);

    return createSignal({
      time: candles[index].timestamp,
      pair: symbol,
      timeframe,
      direction: 'long',
      entry,
      sl,
      tp,
      rr,
      confidence: 55 + tier * 10 + Math.min(20, Math.floor(drawdownPct)),
      reason: `Cycle DCA long tier ${tier}: ${drawdownPct.toFixed(1)}% below peak ${formatPrice(peak, symbol)}`,
      screenshotPosition: { candleIndex: index, timestamp: candles[index].timestamp },
      strategyId: BtcCycleDcaStrategy.id,
      setup: {
        levels: [
          { kind: 'liquidity', label: 'Cycle high', price: peak },
          { kind: 'entry', label: `DCA tier ${tier}`, price: entry },
        ],
        markers: [{ label: `DCA ${tier}`, time: candles[index].timestamp, role: 'entry' }],
        steps: [
          `1. Cycle high (lookback) = ${formatPrice(peak, symbol)}`,
          `2. Dip ${drawdownPct.toFixed(1)}% ? accumulate long (tier ${tier})`,
          `3. Target +${exitGainPct}% — hold through drawdown (no practical SL)`,
        ],
      },
    });
  }
}
