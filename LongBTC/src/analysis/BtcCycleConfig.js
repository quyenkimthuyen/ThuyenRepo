/**
 * BTC halving cycle constants and phase definitions.
 * @module analysis/BtcCycleConfig
 */

/** @typedef {'accumulation'|'markup'|'distribution'|'markdown'} CyclePhase */

/**
 * Known Bitcoin halving events (UTC midnight).
 * @type {ReadonlyArray<{ label: string, timestamp: number, blockReward: string }>}
 */
export const BTC_HALVING_EVENTS = Object.freeze([
  { label: 'Halving #1', timestamp: Date.parse('2012-11-28T00:00:00Z'), blockReward: '25 BTC' },
  { label: 'Halving #2', timestamp: Date.parse('2016-07-09T00:00:00Z'), blockReward: '12.5 BTC' },
  { label: 'Halving #3', timestamp: Date.parse('2020-05-11T00:00:00Z'), blockReward: '6.25 BTC' },
  { label: 'Halving #4', timestamp: Date.parse('2024-04-20T00:00:00Z'), blockReward: '3.125 BTC' },
]);

/** Approximate cycle length in days (~4 years). */
export const CYCLE_LENGTH_DAYS = 1460;

/** Phase boundaries as fraction of cycle length from halving. */
export const CYCLE_PHASE_RANGES = Object.freeze({
  accumulation: Object.freeze({ start: 0, end: 0.25, label: 'Tích l?y', color: '#3b82f6' }),
  markup: Object.freeze({ start: 0.25, end: 0.55, label: 'T?ng tr??ng', color: '#22c55e' }),
  distribution: Object.freeze({ start: 0.55, end: 0.75, label: 'Phân ph?i', color: '#f59e0b' }),
  markdown: Object.freeze({ start: 0.75, end: 1.0, label: 'Gi?m giá', color: '#ef4444' }),
});

/**
 * Market psychology phases mapped to cycle position.
 * @type {ReadonlyArray<{ id: string, label: string, labelVi: string, color: string }>}
 */
export const PSYCHOLOGY_PHASES = Object.freeze([
  { id: 'optimism', label: 'Optimism', labelVi: 'L?c quan', color: '#86efac' },
  { id: 'excitement', label: 'Excitement', labelVi: 'H?ng ph?n', color: '#4ade80' },
  { id: 'thrill', label: 'Thrill', labelVi: 'Ph?n khích', color: '#22c55e' },
  { id: 'euphoria', label: 'Euphoria', labelVi: 'H?ng ph?n c?c ??', color: '#16a34a' },
  { id: 'anxiety', label: 'Anxiety', labelVi: 'Lo l?ng', color: '#fbbf24' },
  { id: 'denial', label: 'Denial', labelVi: 'Ph? nh?n', color: '#f59e0b' },
  { id: 'fear', label: 'Fear', labelVi: 'S? hãi', color: '#f97316' },
  { id: 'capitulation', label: 'Capitulation', labelVi: '??u hàng', color: '#ef4444' },
  { id: 'depression', label: 'Depression', labelVi: 'Chán n?n', color: '#dc2626' },
  { id: 'hope', label: 'Hope', labelVi: 'Hy v?ng', color: '#60a5fa' },
  { id: 'relief', label: 'Relief', labelVi: 'Nh? nhõm', color: '#38bdf8' },
]);

/**
 * Resolve cycle phase from progress ratio (0–1) since last halving.
 * @param {number} progress
 * @returns {CyclePhase}
 */
export function phaseFromProgress(progress) {
  const p = Math.max(0, Math.min(1, progress));
  for (const [phase, range] of Object.entries(CYCLE_PHASE_RANGES)) {
    if (p >= range.start && p < range.end) return /** @type {CyclePhase} */ (phase);
  }
  return 'markdown';
}

/**
 * Find halving index for a given timestamp.
 * @param {number} timestamp
 * @returns {number}
 */
export function halvingIndexAt(timestamp) {
  let idx = 0;
  for (let i = 0; i < BTC_HALVING_EVENTS.length; i++) {
    if (timestamp >= BTC_HALVING_EVENTS[i].timestamp) idx = i;
    else break;
  }
  return idx;
}
