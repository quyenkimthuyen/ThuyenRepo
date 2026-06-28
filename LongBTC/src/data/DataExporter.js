/**
 * Export candles to CSV and JSON formats.
 * @module data/DataExporter
 */

import { formatTimestamp } from './TimeframeUtils.js';

/**
 * Convert candles to CSV string.
 * @param {import('./Candle.js').Candle[]} candles
 * @returns {string}
 */
export function exportCSV(candles) {
  const header = 'timestamp,datetime,open,high,low,close,volume';
  const rows = candles.map((c) =>
    [
      c.timestamp,
      formatTimestamp(c.timestamp),
      c.open,
      c.high,
      c.low,
      c.close,
      c.volume,
    ].join(',')
  );
  return [header, ...rows].join('\n');
}

/**
 * Convert candles to a JSON export object.
 * @param {string} symbol
 * @param {string} timeframe
 * @param {import('./Candle.js').Candle[]} candles
 * @returns {string}
 */
export function exportJSON(symbol, timeframe, candles) {
  return JSON.stringify({ symbol, timeframe, candles }, null, 2);
}

/**
 * Trigger a browser file download.
 * @param {string} content
 * @param {string} filename
 * @param {string} [mimeType='text/plain']
 */
export function downloadFile(content, filename, mimeType = 'text/plain') {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

/**
 * Trigger a binary file download.
 * @param {Uint8Array} data
 * @param {string} filename
 * @param {string} mimeType
 */
export function downloadBinary(data, filename, mimeType) {
  const blob = new Blob([data], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
