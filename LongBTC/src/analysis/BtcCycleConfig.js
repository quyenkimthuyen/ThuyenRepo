/**
 * BTC halving cycle constants and phase definitions.
 * @module analysis/BtcCycleConfig
 */

/** @typedef {'accumulation'|'markup'|'distribution'|'markdown'} CyclePhase */

export const BTC_HALVING_EVENTS = Object.freeze([
  { label: 'Halving #1', timestamp: Date.parse('2012-11-28T00:00:00Z'), blockReward: '25 BTC' },
  { label: 'Halving #2', timestamp: Date.parse('2016-07-09T00:00:00Z'), blockReward: '12.5 BTC' },
  { label: 'Halving #3', timestamp: Date.parse('2020-05-11T00:00:00Z'), blockReward: '6.25 BTC' },
  { label: 'Halving #4', timestamp: Date.parse('2024-04-20T00:00:00Z'), blockReward: '3.125 BTC' },
]);

export const CYCLE_LENGTH_DAYS = 1460;

export const CYCLE_PHASE_RANGES = Object.freeze({
  accumulation: Object.freeze({ start: 0, end: 0.25, label: 'Tích lũy', color: '#3b82f6' }),
  markup: Object.freeze({ start: 0.25, end: 0.55, label: 'Tăng trưởng', color: '#22c55e' }),
  distribution: Object.freeze({ start: 0.55, end: 0.75, label: 'Phân phối', color: '#f59e0b' }),
  markdown: Object.freeze({ start: 0.75, end: 1.0, label: 'Giảm giá', color: '#ef4444' }),
});

export const PSYCHOLOGY_PHASES = Object.freeze([
  { id: 'optimism', label: 'Optimism', labelVi: 'Lạc quan', color: '#86efac' },
  { id: 'excitement', label: 'Excitement', labelVi: 'Hưng phấn', color: '#4ade80' },
  { id: 'thrill', label: 'Thrill', labelVi: 'Phấn khích', color: '#22c55e' },
  { id: 'euphoria', label: 'Euphoria', labelVi: 'Hưng phấn cực độ', color: '#16a34a' },
  { id: 'anxiety', label: 'Anxiety', labelVi: 'Lo lắng', color: '#fbbf24' },
  { id: 'denial', label: 'Denial', labelVi: 'Phủ nhận', color: '#f59e0b' },
  { id: 'fear', label: 'Fear', labelVi: 'Sợ hãi', color: '#f97316' },
  { id: 'capitulation', label: 'Capitulation', labelVi: 'Đầu hàng', color: '#ef4444' },
  { id: 'depression', label: 'Depression', labelVi: 'Chán nản', color: '#dc2626' },
  { id: 'hope', label: 'Hope', labelVi: 'Hy vọng', color: '#60a5fa' },
  { id: 'relief', label: 'Relief', labelVi: 'Nhẹ nhõm', color: '#38bdf8' },
]);

export function phaseFromProgress(progress) {
  const p = Math.max(0, Math.min(1, progress));
  for (const [phase, range] of Object.entries(CYCLE_PHASE_RANGES)) {
    if (p >= range.start && p < range.end) return /** @type {CyclePhase} */ (phase);
  }
  return 'markdown';
}

export function halvingIndexAt(timestamp) {
  let idx = 0;
  for (let i = 0; i < BTC_HALVING_EVENTS.length; i++) {
    if (timestamp >= BTC_HALVING_EVENTS[i].timestamp) idx = i;
    else break;
  }
  return idx;
}
