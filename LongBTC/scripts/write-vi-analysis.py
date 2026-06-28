from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def w(rel, s):
    text = s.encode("utf-8").decode("unicode_escape")
    (ROOT / rel).write_text(text, encoding="utf-8")
    print(rel, "OK")


w(
    "src/analysis/BtcCycleConfig.js",
    r"""
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
  accumulation: Object.freeze({ start: 0, end: 0.25, label: 'T\u00edch l\u0169y', color: '#3b82f6' }),
  markup: Object.freeze({ start: 0.25, end: 0.55, label: 'T\u0103ng tr\u01b0\u1edfng', color: '#22c55e' }),
  distribution: Object.freeze({ start: 0.55, end: 0.75, label: 'Ph\u00e2n ph\u1ed1i', color: '#f59e0b' }),
  markdown: Object.freeze({ start: 0.75, end: 1.0, label: 'Gi\u1ea3m gi\u00e1', color: '#ef4444' }),
});

export const PSYCHOLOGY_PHASES = Object.freeze([
  { id: 'optimism', label: 'Optimism', labelVi: 'L\u1ea1c quan', color: '#86efac' },
  { id: 'excitement', label: 'Excitement', labelVi: 'H\u01b0ng ph\u1ea5n', color: '#4ade80' },
  { id: 'thrill', label: 'Thrill', labelVi: 'Ph\u1ea5n kh\u00edch', color: '#22c55e' },
  { id: 'euphoria', label: 'Euphoria', labelVi: 'H\u01b0ng ph\u1ea5n c\u1ef1c \u0111\u1ed9', color: '#16a34a' },
  { id: 'anxiety', label: 'Anxiety', labelVi: 'Lo l\u1eafng', color: '#fbbf24' },
  { id: 'denial', label: 'Denial', labelVi: 'Ph\u1ee7 nh\u1eadn', color: '#f59e0b' },
  { id: 'fear', label: 'Fear', labelVi: 'S\u1ee3 h\u00e3i', color: '#f97316' },
  { id: 'capitulation', label: 'Capitulation', labelVi: '\u0110\u1ea7u h\u00e0ng', color: '#ef4444' },
  { id: 'depression', label: 'Depression', labelVi: 'Ch\u00e1n n\u1ea3n', color: '#dc2626' },
  { id: 'hope', label: 'Hope', labelVi: 'Hy v\u1ecdng', color: '#60a5fa' },
  { id: 'relief', label: 'Relief', labelVi: 'Nh\u1eb9 nh\u00f5m', color: '#38bdf8' },
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
""",
)
