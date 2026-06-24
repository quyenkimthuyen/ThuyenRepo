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
 * @param {'long'|'short'} direction
 * @param {number} entry
 * @param {number} sl
 * @param {number} tp
 * @returns {number}
 */
function computeRiskReward(direction, entry, sl, tp) {
  const risk = Math.abs(entry - sl);
  if (risk <= 0) return 0;
  const reward = direction === 'long' ? tp - entry : entry - tp;
  return Math.max(0, reward / risk);
}

/**
 * Build chart overlay from a simulated trade; prefers original signal for setup metadata.
 * @param {import('../simulation/TradeSimulator.js').TradeResult} trade
 * @param {import('../strategy/Signal.js').Signal} [sourceSignal]
 * @returns {ChartSignalHighlight}
 */
export function tradeToChartHighlight(trade, sourceSignal) {
  const base = sourceSignal
    ? signalToChartHighlight(sourceSignal)
    : signalToChartHighlight({
        id: trade.signalId,
        strategyId: trade.strategyId,
        pair: trade.symbol,
        timeframe: trade.timeframe,
        direction: trade.direction,
        entry: trade.entryPrice,
        sl: trade.sl,
        tp: trade.tp,
        rr: computeRiskReward(trade.direction, trade.entryPrice, trade.sl, trade.tp),
        reason: trade.reason ?? `${trade.outcome} · ${trade.exitReason}`,
        time: trade.entryTime,
        screenshotPosition: { timestamp: trade.entryTime, candleIndex: trade.entryBar },
      });

  return {
    ...base,
    entry: trade.entryPrice,
    sl: trade.sl,
    tp: trade.tp,
    time: trade.entryTime,
    candleIndex: trade.entryBar,
    rr: computeRiskReward(trade.direction, trade.entryPrice, trade.sl, trade.tp),
    reason: trade.reason ?? base.reason,
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
  if (signal.strategyId === 'inside-bar-breakout' && price != null) {
    return {
      levels: [{ kind: 'break-level', label: 'Mother level', price }],
      markers: [{ label: 'Breakout', time, role: 'entry' }],
      steps: ['Inside bar nén ? break mother bar theo trend'],
    };
  }
  if (signal.strategyId === 'pin-bar-rejection' && price != null) {
    return {
      levels: [{ kind: 'liquidity', label: 'Swing level', price }],
      markers: [{ label: 'Pin reject', time, role: 'sweep' }],
      steps: ['Ch?m swing ? pin bar rejection ? entry'],
    };
  }
  if (signal.strategyId === 'wyckoff-spring-utad' && price != null) {
    return {
      levels: [{ kind: 'break-level', label: 'Range boundary', price }],
      markers: [{ label: 'Spring/UTAD', time, role: 'sweep' }],
      steps: ['Range tich luy ? quet bien ? dong lai trong range ? entry'],
    };
  }
  if (signal.strategyId === 'wyckoff-range-test' && price != null) {
    return {
      levels: [{ kind: 'break-level', label: 'Range boundary', price }],
      markers: [{ label: 'Test', time, role: 'confirm' }],
      steps: ['Spring/UTAD ? rally ? test lai bien ? entry'],
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
