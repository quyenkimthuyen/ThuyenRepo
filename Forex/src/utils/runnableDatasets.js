/**
 * Helpers for Symbol/TF selectors — only pairs with candles in IndexedDB.
 * @module utils/runnableDatasets
 */

import { Config } from '../core/Config.js';
import { el } from './dom.js';

/**
 * @typedef {import('../data/Candle.js').DatasetMetadata} DatasetMetadata
 */

/**
 * @param {DatasetMetadata[]} datasets
 * @returns {string[]}
 */
export function uniqueSymbols(datasets) {
  return [...new Set(datasets.map((d) => d.symbol))];
}

/**
 * @param {DatasetMetadata[]} datasets
 * @param {string} symbol
 * @returns {string[]}
 */
export function timeframesForSymbol(datasets, symbol) {
  const tfs = datasets
    .filter((d) => d.symbol === symbol)
    .map((d) => d.timeframe);
  return Config.TIMEFRAMES.filter((tf) => tfs.includes(tf));
}

/**
 * @param {DatasetMetadata[]} datasets
 * @param {string} [preferredSymbol]
 * @param {string} [preferredTimeframe]
 * @returns {{ symbol: string|null, timeframe: string|null, hasData: boolean }}
 */
export function resolveDatasetSelection(datasets, preferredSymbol, preferredTimeframe) {
  if (datasets.length === 0) {
    return { symbol: null, timeframe: null, hasData: false };
  }

  const symbols = uniqueSymbols(datasets);
  const preferredSym = preferredSymbol ?? Config.DEFAULT_SYMBOL;
  const symbol = symbols.includes(preferredSym) ? preferredSym : symbols[0];

  const tfs = timeframesForSymbol(datasets, symbol);
  const preferredTf = preferredTimeframe ?? Config.DEFAULT_TIMEFRAME;
  const timeframe = tfs.includes(preferredTf) ? preferredTf : (tfs[0] ?? null);

  return { symbol, timeframe, hasData: Boolean(symbol && timeframe) };
}

/**
 * @param {DatasetMetadata[]} datasets
 * @param {string|null} selectedSymbol
 * @returns {HTMLElement[]}
 */
export function buildSymbolOptions(datasets, selectedSymbol) {
  const symbols = uniqueSymbols(datasets);
  if (symbols.length === 0) {
    return [el('option', { value: '' }, ['Ch?a có d? li?u'])];
  }
  return symbols.map((s) =>
    el('option', { value: s, selected: s === selectedSymbol }, [s])
  );
}

/**
 * @param {DatasetMetadata[]} datasets
 * @param {string|null} symbol
 * @param {string|null} selectedTimeframe
 * @returns {HTMLElement[]}
 */
export function buildTimeframeOptions(datasets, symbol, selectedTimeframe) {
  if (!symbol) {
    return [el('option', { value: '' }, ['—'])];
  }
  const tfs = timeframesForSymbol(datasets, symbol);
  if (tfs.length === 0) {
    return [el('option', { value: '' }, ['—'])];
  }
  return tfs.map((t) =>
    el('option', { value: t, selected: t === selectedTimeframe }, [t])
  );
}

/**
 * Repopulate symbol + timeframe &lt;select&gt; elements from runnable datasets.
 * @param {HTMLElement} symbolSelect
 * @param {HTMLElement} timeframeSelect
 * @param {DatasetMetadata[]} datasets
 * @param {string|null} symbol
 * @param {string|null} timeframe
 * @returns {{ symbol: string|null, timeframe: string|null, hasData: boolean }}
 */
export function fillDatasetSelectors(symbolSelect, timeframeSelect, datasets, symbol, timeframe) {
  const resolved = resolveDatasetSelection(datasets, symbol ?? undefined, timeframe ?? undefined);

  symbolSelect.innerHTML = '';
  timeframeSelect.innerHTML = '';

  for (const opt of buildSymbolOptions(datasets, resolved.symbol)) {
    symbolSelect.appendChild(opt);
  }
  for (const opt of buildTimeframeOptions(datasets, resolved.symbol, resolved.timeframe)) {
    timeframeSelect.appendChild(opt);
  }

  symbolSelect.disabled = !resolved.hasData;
  timeframeSelect.disabled = !resolved.hasData;

  if (resolved.symbol) symbolSelect.value = resolved.symbol;
  if (resolved.timeframe) timeframeSelect.value = resolved.timeframe;

  return resolved;
}
