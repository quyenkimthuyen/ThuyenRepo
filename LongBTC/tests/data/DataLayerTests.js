/**
 * Data layer tests — import, merge, gaps, export, sample generation.
 * Run: node tests/data/DataLayerTests.js
 */

import { createSuite, header, footer, candle } from '../harness.js';
import { importFromText, importCSV, importJSON } from '../../src/data/DataImporter.js';
import { exportCSV, exportJSON } from '../../src/data/DataExporter.js';
import { mergeCandles, detectGaps, computeStats } from '../../src/data/CandleMerge.js';
import { normalizeCandle, isValidCandle } from '../../src/data/Candle.js';
import { generateSample } from '../../src/data/SampleDataGenerator.js';
import { Config } from '../../src/core/Config.js';
import {
  parseBinanceKline,
  parseBinanceKlines,
  binanceIntervalFor,
  fetchStartAfter,
} from '../../src/data/BtcLivePriceFetcher.js';
import { alignToTimeframe } from '../../src/data/TimeframeUtils.js';

const s = createSuite('Data Layer');
header('Data Layer');

{
  const raw = { timestamp: 1000, open: 1.1, high: 1.2, low: 1.0, close: 1.15, volume: 100 };
  s.assert('DL-01: Valid candle', isValidCandle(raw));
  s.assert('DL-02: Invalid high', !isValidCandle({ ...raw, high: 1.0 }));
  s.assert('DL-03: normalizeCandle', normalizeCandle({ o: 1.1, h: 1.2, l: 1.0, c: 1.15, t: 1000 })?.close === 1.15);
}

{
  const csv = `timestamp,datetime,open,high,low,close,volume
1000,2024-01-01 00:00,1.0845,1.0850,1.0840,1.0848,400`;
  const r = importCSV(csv, 'BTCUSD', 'D1');
  s.assert('DL-04: CSV import', r.candles.length === 1 && r.symbol === 'BTCUSD');
}

{
  const json = JSON.stringify({
    symbol: 'BTCUSD',
    timeframe: 'D1',
    candles: [{ timestamp: 2000, open: 42000, high: 43000, low: 41000, close: 42500, volume: 50 }],
  });
  const r = importJSON(json);
  s.assert('DL-05: JSON import', r.candles.length === 1 && r.timeframe === 'D1');
}

{
  const a = [candle(0, 1, 1.1, 0.9, 1.05), candle(1, 1.05, 1.1, 1.0, 1.08)];
  const b = [candle(1, 1.05, 1.2, 1.0, 1.1), candle(2, 1.1, 1.15, 1.05, 1.12)];
  const merged = mergeCandles(a, b);
  s.assert('DL-06: Merge dedup', merged.length === 3);
  s.assert('DL-07: Merge overwrite', merged[1].close === 1.1);
}

{
  const gaps = detectGaps([candle(0, 1, 1, 1, 1), candle(3, 1, 1, 1, 1)], 'H1');
  s.assert('DL-08: Gap detection H1', gaps.length === 1 && gaps[0].missingCount === 2);
}

{
  const d1candles = [
    { timestamp: Date.UTC(2024, 0, 1), open: 1, high: 1, low: 1, close: 1, volume: 1 },
    { timestamp: Date.UTC(2024, 0, 4), open: 1, high: 1, low: 1, close: 1, volume: 1 },
  ];
  const d1gaps = detectGaps(d1candles, 'D1');
  s.assert('DL-09: Gap detection D1', d1gaps.length === 1 && d1gaps[0].missingCount === 2);
}

{
  const sample = generateSample('BTCUSD', 'W', 100);
  const stats = computeStats(sample);
  s.assert('DL-10: Sample generation', sample.length === 100 && stats.count === 100);
  s.assert('DL-11: Sample sorted', sample[0].timestamp < sample[99].timestamp);
}

{
  const candles = [candle(0, 1.0845, 1.085, 1.084, 1.0848)];
  const csvOut = exportCSV(candles);
  const jsonOut = exportJSON('BTCUSD', 'W', candles);
  s.assert('DL-12: Export CSV header', csvOut.startsWith('timestamp,datetime'));
  s.assert('DL-13: Export JSON parse', JSON.parse(jsonOut).candles.length === 1);
}

{
  s.assert('DL-14: Config timeframes', Config.TIMEFRAMES.includes('H4') && Config.TIMEFRAMES.includes('W'));
  s.assert('DL-15: Config symbols', Config.SYMBOLS.includes('BTCUSD'));
}

{
  const row = [1781481600000, '65000', '67000', '64000', '65500', '123.45'];
  const c = parseBinanceKline(row, 'W');
  s.assert('DL-16: Binance kline parse', c != null && c.close === 65500);
  s.assert('DL-17: Binance kline align W', c?.timestamp === alignToTimeframe(1781481600000, 'W'));
  s.assert('DL-18: Binance interval W', binanceIntervalFor('W') === '1w');
  const day = 24 * 60 * 60 * 1000;
  s.assert('DL-19: fetch overlap', fetchStartAfter(Date.UTC(2024, 5, 1), 'D1') === Date.UTC(2024, 5, 1) - day);

  const multi = parseBinanceKlines([row, [1781568000000, '65500', '66000', '65000', '65800', '50']], 'D1');
  s.assert('DL-20: Binance klines batch', multi.length === 2);
}

process.exit(footer(s.finish()));
