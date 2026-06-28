/**
 * Import candles from CSV and JSON files.
 * @module data/DataImporter
 */

import { normalizeCandle, sortCandles } from './Candle.js';
import { alignToTimeframe } from './TimeframeUtils.js';

/**
 * @typedef {Object} ImportResult
 * @property {string} symbol
 * @property {string} timeframe
 * @property {import('./Candle.js').Candle[]} candles
 * @property {number} skipped
 */

/**
 * Parse a datetime string or number into epoch milliseconds.
 * @param {string|number} value
 * @returns {number|null}
 */
function parseDateTime(value) {
  if (typeof value === 'number') return value;
  const trimmed = String(value).trim();

  if (/^\d+$/.test(trimmed)) {
    const num = Number(trimmed);
    return trimmed.length <= 10 ? num * 1000 : num;
  }

  const parsed = Date.parse(trimmed);
  return Number.isNaN(parsed) ? null : parsed;
}

/**
 * Detect CSV delimiter from the header line.
 * @param {string} header
 * @returns {string}
 */
function detectDelimiter(header) {
  const counts = { ',': 0, ';': 0, '\t': 0 };
  for (const ch of header) {
    if (ch in counts) counts[ch]++;
  }
  return Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0];
}

/**
 * Map CSV header columns to canonical field names.
 * @param {string[]} headers
 * @returns {Record<string, number>}
 */
function mapHeaders(headers) {
  const map = {};
  const aliases = {
    timestamp: ['timestamp', 'time', 't', 'date', 'datetime', 'date time'],
    open: ['open', 'o'],
    high: ['high', 'h'],
    low: ['low', 'l'],
    close: ['close', 'c'],
    volume: ['volume', 'vol', 'v', 'tickvolume', 'tick volume'],
  };

  headers.forEach((h, i) => {
    const lower = h.trim().toLowerCase();
    for (const [field, names] of Object.entries(aliases)) {
      if (names.includes(lower)) {
        map[field] = i;
      }
    }
  });

  return map;
}

/**
 * Parse CSV text into candles.
 * @param {string} text
 * @param {string} symbol
 * @param {string} timeframe
 * @returns {ImportResult}
 */
export function importCSV(text, symbol, timeframe) {
  const lines = text.trim().split(/\r?\n/).filter((l) => l.trim());
  if (lines.length < 2) {
    throw new Error('CSV file must have a header and at least one data row');
  }

  const delimiter = detectDelimiter(lines[0]);
  const headers = lines[0].split(delimiter);
  const colMap = mapHeaders(headers);

  if (colMap.timestamp === undefined || colMap.open === undefined) {
    throw new Error('CSV must contain timestamp/date and open columns');
  }

  const candles = [];
  let skipped = 0;

  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(delimiter);
    const ts = parseDateTime(cols[colMap.timestamp]);
    if (ts === null) { skipped++; continue; }

    const raw = {
      timestamp: alignToTimeframe(ts, timeframe),
      open: cols[colMap.open],
      high: cols[colMap.high ?? colMap.open],
      low: cols[colMap.low ?? colMap.open],
      close: cols[colMap.close ?? colMap.open],
      volume: colMap.volume !== undefined ? cols[colMap.volume] : 0,
    };

    const candle = normalizeCandle(raw);
    if (candle) {
      candles.push(candle);
    } else {
      skipped++;
    }
  }

  return { symbol, timeframe, candles: sortCandles(candles), skipped };
}

/**
 * Parse JSON text into candles.
 * Accepts `{ symbol, timeframe, candles }` or a bare array.
 * @param {string} text
 * @param {string} [defaultSymbol]
 * @param {string} [defaultTimeframe]
 * @returns {ImportResult}
 */
export function importJSON(text, defaultSymbol, defaultTimeframe) {
  const data = JSON.parse(text);

  let symbol = defaultSymbol;
  let timeframe = defaultTimeframe;
  let rawList;

  if (Array.isArray(data)) {
    rawList = data;
  } else if (data && Array.isArray(data.candles)) {
    symbol = data.symbol ?? defaultSymbol;
    timeframe = data.timeframe ?? defaultTimeframe;
    rawList = data.candles;
  } else {
    throw new Error('JSON must be an array of candles or { symbol, timeframe, candles }');
  }

  if (!symbol || !timeframe) {
    throw new Error('Symbol and timeframe are required for JSON import');
  }

  const candles = [];
  let skipped = 0;

  for (const raw of rawList) {
    const ts = parseDateTime(raw.timestamp ?? raw.time ?? raw.date);
    if (ts !== null) {
      raw.timestamp = alignToTimeframe(ts, timeframe);
    }
    const candle = normalizeCandle(raw);
    if (candle) {
      candles.push(candle);
    } else {
      skipped++;
    }
  }

  return { symbol, timeframe, candles: sortCandles(candles), skipped };
}

/**
 * Detect file format from name and dispatch to the correct parser.
 * @param {string} text
 * @param {string} filename
 * @param {string} symbol
 * @param {string} timeframe
 * @returns {ImportResult}
 */
export function importFromText(text, filename, symbol, timeframe) {
  const lower = filename.toLowerCase();

  if (lower.endsWith('.csv')) {
    return importCSV(text, symbol, timeframe);
  }
  if (lower.endsWith('.json')) {
    return importJSON(text, symbol, timeframe);
  }

  try {
    return importJSON(text, symbol, timeframe);
  } catch {
    return importCSV(text, symbol, timeframe);
  }
}
