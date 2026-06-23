/**
 * PA chart annotation colors — legend matches drawn levels/markers.
 * @module chart/SetupAnnotationStyles
 */

/** @typedef {'break-level'|'liquidity'|'ema-zone'|'invalidation'} SetupLevelKind */

/**
 * @typedef {Object} SetupLevelAnnotation
 * @property {SetupLevelKind|string} kind
 * @property {string} label
 * @property {number} price
 * @property {number} [priceTo]
 */

/**
 * @typedef {Object} SetupMarkerAnnotation
 * @property {string} label
 * @property {number} time
 * @property {'breakout'|'sweep'|'retest'|'entry'|'confirm'} [role]
 */

/**
 * @typedef {Object} SignalSetupAnnotations
 * @property {SetupLevelAnnotation[]} levels
 * @property {SetupMarkerAnnotation[]} markers
 * @property {string[]} steps
 */

/** @type {Record<string, { color: string, lineStyle: number }>} */
export const SETUP_LEVEL_STYLES = {
  'break-level': { color: '#f59e0b', lineStyle: 2 },
  liquidity: { color: '#c084fc', lineStyle: 2 },
  'ema-zone': { color: '#38bdf8', lineStyle: 2 },
  invalidation: { color: '#64748b', lineStyle: 1 },
};

/** @type {Record<string, { color: string, lineStyle: number }>} */
export const TRADE_LEVEL_STYLES = {
  entry: { color: '#3b82f6', lineStyle: 0, title: 'Entry' },
  sl: { color: '#ef4444', lineStyle: 2, title: 'SL' },
  tp: { color: '#22c55e', lineStyle: 2, title: 'TP' },
};

/** @type {Record<string, string>} */
export const MARKER_ROLE_COLORS = {
  breakout: '#f59e0b',
  sweep: '#c084fc',
  retest: '#fbbf24',
  confirm: '#38bdf8',
  entry: '#3b82f6',
};

/**
 * @param {SetupLevelKind|string} kind
 * @returns {{ color: string, lineStyle: number }}
 */
export function styleForSetupLevel(kind) {
  return SETUP_LEVEL_STYLES[kind] ?? { color: '#94a3b8', lineStyle: 2 };
}
