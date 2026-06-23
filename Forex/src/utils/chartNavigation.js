/**
 * Navigate to Chart with optional replay jump — survives async Chart mount.
 * @module utils/chartNavigation
 */

import { bus, Events } from '../core/EventBus.js';

/**
 * @typedef {Object} ChartFocusRequest
 * @property {string} symbol
 * @property {string} timeframe
 * @property {number} [jumpTo] - Epoch ms to jump replay to
 */

/** @type {ChartFocusRequest|null} */
let pendingRequest = null;

/**
 * Open Chart for a symbol/timeframe and optionally jump replay to a candle time.
 * @param {ChartFocusRequest} request
 */
export function requestChartFocus(request) {
  pendingRequest = request;
  bus.emit(Events.NAVIGATE, { view: 'chart' });
  bus.emit(Events.CHART_LOAD, request);
}

/**
 * @returns {ChartFocusRequest|null}
 */
export function takePendingChartFocus() {
  const request = pendingRequest;
  pendingRequest = null;
  return request;
}
