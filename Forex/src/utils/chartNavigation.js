/**
 * Chart navigation with signal highlight — survives async Chart mount.
 * @module utils/chartNavigation
 */

import { bus, Events } from '../core/EventBus.js';
import { registry } from '../plugin/PluginRegistry.js';

/**
 * @typedef {import('../chart/SetupAnnotationStyles.js').SignalSetupAnnotations} SignalSetupAnnotations
 */

/**
 * @typedef {Object} ChartSignalHighlight
 * @property {string} strategyId
 * @property {string} strategyName
 * @property {string} symbol
 * @property {string} timeframe
 * @property {'long'|'short'} direction
 * @property {number} entry
 * @property {number} sl
 * @property {number} tp
 * @property {number} rr
 * @property {string} reason
 * @property {number} time
 * @property {number} [candleIndex]
 * @property {number} [score]
 * @property {SignalSetupAnnotations} [setup]
 */

/**
 * @typedef {Object} ChartFocusRequest
 * @property {string} symbol
 * @property {string} timeframe
 * @property {number} [jumpTo]
 * @property {ChartSignalHighlight} [signal]
 */

/** @type {ChartFocusRequest|null} */
let pendingRequest = null;

/**
 * @param {import('../strategy/Signal.js').Signal & { scoreBreakdown?: { score?: number } }} signal
 * @returns {ChartSignalHighlight}
 */
export function signalToChartHighlight(signal) {
  const time = signal.time || signal.screenshotPosition?.timestamp || 0;
  return {
    strategyId: signal.strategyId,
    strategyName: registry.get(signal.strategyId)?.name ?? signal.strategyId,
    symbol: signal.pair,
    timeframe: signal.timeframe,
    direction: signal.direction,
    entry: signal.entry,
    sl: signal.sl,
    tp: signal.tp,
    rr: signal.rr,
    reason: signal.reason ?? '',
    time,
    candleIndex: signal.screenshotPosition?.candleIndex,
    score: signal.scoreBreakdown?.score ?? signal.confidence,
    setup: signal.setup ?? inferSetupFromSignal(signal),
  };
}

/**
 * Fallback for signals scanned before setup metadata existed.
 * @param {import('../strategy/Signal.js').Signal} signal
 * @returns {SignalSetupAnnotations|undefined}
 */
function inferSetupFromSignal(signal) {
  const reason = signal.reason ?? '';
  const priceMatch = reason.match(/(\d+\.\d{4,5})/);
  const price = priceMatch ? parseFloat(priceMatch[1]) : null;
  const time = signal.time || signal.screenshotPosition?.timestamp || 0;

  if (signal.strategyId === 'break-retest' && price != null) {
    return {
      levels: [{ kind: 'break-level', label: 'M?c B&R', price }],
      markers: [{ label: 'Entry', time, role: 'entry' }],
      steps: ['Phá level ? retest ? entry (scan l?i ?? xem ?? b??c)'],
    };
  }
  if (signal.strategyId === 'liquidity-grab' && price != null) {
    return {
      levels: [{ kind: 'liquidity', label: 'Liquidity', price }],
      markers: [{ label: 'Sweep', time, role: 'sweep' }],
      steps: ['Quét liquidity ? rejection ? entry'],
    };
  }
  if (signal.strategyId === 'ema-pullback' && price != null) {
    return {
      levels: [{ kind: 'ema-zone', label: 'EMA zone', price }],
      markers: [{ label: 'Confirm', time, role: 'confirm' }],
      steps: ['Pullback EMA zone ? n?n confirm'],
    };
  }
  return undefined;
}

/**
 * Open Chart for a symbol/timeframe, jump replay, and optionally draw setup levels.
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
