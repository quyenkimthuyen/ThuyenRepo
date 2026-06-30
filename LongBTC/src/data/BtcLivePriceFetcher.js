/**
 * Fetch latest BTC OHLCV from Binance public API (BTCUSDT proxy for BTCUSD).
 * @module data/BtcLivePriceFetcher
 */

import { Config } from '../core/Config.js';
import { normalizeCandle } from './Candle.js';
import { alignToTimeframe, getTimeframeMs } from './TimeframeUtils.js';

/** @typedef {import('./Candle.js').Candle} Candle */

const BINANCE_BASE = 'https://api.binance.com/api/v3';

/** @type {Record<string, string>} */
export const BINANCE_INTERVAL = Object.freeze({
  W: '1w',
  D1: '1d',
  H4: '4h',
});

/**
 * @param {string} timeframe
 * @returns {string}
 */
export function binanceIntervalFor(timeframe) {
  const interval = BINANCE_INTERVAL[timeframe];
  if (!interval) {
    throw new Error(`Không h? tr? c?p nh?t live cho timeframe ${timeframe}`);
  }
  return interval;
}

/**
 * @param {unknown[]} row - Binance kline array
 * @param {string} timeframe
 * @returns {Candle|null}
 */
export function parseBinanceKline(row, timeframe) {
  if (!Array.isArray(row) || row.length < 6) return null;

  const openTime = Number(row[0]);
  if (!Number.isFinite(openTime)) return null;

  return normalizeCandle({
    timestamp: alignToTimeframe(openTime, timeframe),
    open: row[1],
    high: row[2],
    low: row[3],
    close: row[4],
    volume: row[5],
  });
}

/**
 * @param {unknown} data
 * @param {string} timeframe
 * @returns {Candle[]}
 */
export function parseBinanceKlines(data, timeframe) {
  if (!Array.isArray(data)) return [];
  /** @type {Candle[]} */
  const out = [];
  for (const row of data) {
    const candle = parseBinanceKline(row, timeframe);
    if (candle) out.push(candle);
  }
  return out;
}

/**
 * Start time for incremental fetch (overlap one bar to refresh forming candle).
 * @param {number} lastTimestamp
 * @param {string} timeframe
 * @returns {number|undefined}
 */
export function fetchStartAfter(lastTimestamp, timeframe) {
  if (!lastTimestamp || lastTimestamp <= 0) return undefined;
  return Math.max(0, lastTimestamp - getTimeframeMs(timeframe));
}

/**
 * @param {string} timeframe
 * @param {{ startTime?: number, limit?: number, signal?: AbortSignal }} [options]
 * @returns {Promise<Candle[]>}
 */
export async function fetchBtcKlines(timeframe, options = {}) {
  const interval = binanceIntervalFor(timeframe);
  const limit = Math.min(1000, Math.max(1, options.limit ?? 500));
  const params = new URLSearchParams({
    symbol: Config.BTC_LIVE?.SYMBOL ?? 'BTCUSDT',
    interval,
    limit: String(limit),
  });

  if (options.startTime != null && options.startTime > 0) {
    params.set('startTime', String(Math.floor(options.startTime)));
  }

  const url = `${Config.BTC_LIVE?.BINANCE_API ?? BINANCE_BASE}/klines?${params}`;
  const res = await fetch(url, { signal: options.signal });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`Binance API ${res.status}${body ? `: ${body.slice(0, 120)}` : ''}`);
  }

  const data = await res.json();
  return parseBinanceKlines(data, timeframe);
}

/**
 * Fetch candles newer than (or overlapping) the last stored bar.
 * @param {string} timeframe
 * @param {Candle[]} existing
 * @param {{ signal?: AbortSignal }} [options]
 * @returns {Promise<{ candles: Candle[], fromMs: number|undefined }>}
 */
export async function fetchIncrementalBtcCandles(timeframe, existing, options = {}) {
  const last = existing.length > 0 ? existing[existing.length - 1].timestamp : 0;
  const fromMs = fetchStartAfter(last, timeframe);
  const candles = await fetchBtcKlines(timeframe, {
    startTime: fromMs,
    limit: 500,
    signal: options.signal,
  });

  if (fromMs != null) {
    return {
      candles: candles.filter((c) => c.timestamp >= fromMs),
      fromMs,
    };
  }

  return { candles, fromMs };
}
