/**
 * Synthetic OHLCV data generator for demo and testing.
 * @module data/SampleDataGenerator
 */

import { Config } from '../core/Config.js';
import { alignToTimeframe, getTimeframeMs } from './TimeframeUtils.js';
import { sortCandles } from './Candle.js';

/** Base prices per symbol for realistic generation. */
const BASE_PRICES = {
  EURUSD: 1.0850,
  GBPUSD: 1.2650,
};

/** Typical H1 volatility (fraction of price). */
const VOLATILITY = 0.0008;

/**
 * Generate synthetic candle data using a random walk model.
 * @param {string} symbol
 * @param {string} timeframe
 * @param {number} [count=Config.SAMPLE_CANDLE_COUNT]
 * @returns {import('./Candle.js').Candle[]}
 */
export function generateSample(symbol, timeframe, count = Config.SAMPLE_CANDLE_COUNT) {
  const interval = getTimeframeMs(timeframe);
  const now = alignToTimeframe(Date.now(), timeframe);
  const start = now - count * interval;

  let price = BASE_PRICES[symbol] ?? 1.0;
  const candles = [];

  for (let i = 0; i < count; i++) {
    const timestamp = start + i * interval;
    const change = (Math.random() - 0.5) * 2 * VOLATILITY * price;
    const open = price;
    const close = price + change;
    const wick = Math.random() * VOLATILITY * price;
    const high = Math.max(open, close) + wick;
    const low = Math.min(open, close) - wick;
    const volume = Math.floor(100 + Math.random() * 900);

    candles.push({ timestamp, open, high, low, close, volume });
    price = close;
  }

  return sortCandles(candles);
}

/**
 * Generate sample data for all configured symbols.
 * @param {string} timeframe
 * @param {number} count
 * @returns {Array<{ symbol: string, timeframe: string, candles: import('./Candle.js').Candle[] }>}
 */
export function generateAllSamples(timeframe, count) {
  return Config.SYMBOLS.map((symbol) => ({
    symbol,
    timeframe,
    candles: generateSample(symbol, timeframe, count),
  }));
}
