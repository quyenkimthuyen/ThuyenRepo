/**
 * Simplified Elliott Wave labeling on swing pivots.
 * Research heuristic — not a substitute for manual wave count.
 * @module analysis/ElliottWaveAnalyzer
 */

/**
 * @typedef {import('./SwingPivotDetector.js').SwingPivot} SwingPivot
 * @typedef {import('./TrendAnalyzer.js').TrendSegment} TrendSegment
 * @typedef {'impulse'|'correction'|'unknown'} WaveStructure
 * @typedef {{
 *   label: string,
 *   waveNumber: string,
 *   startIndex: number,
 *   endIndex: number,
 *   startTime: number,
 *   endTime: number,
 *   startPrice: number,
 *   endPrice: number,
 *   structure: WaveStructure,
 *   degree: 'primary'|'intermediate',
 * }} ElliottWave
 */

const IMPULSE_LABELS = ['1', '2', '3', '4', '5'];
const CORRECTION_LABELS = ['A', 'B', 'C'];

/**
 * Label Elliott waves from pivot sequence and trend segments.
 * @param {SwingPivot[]} pivots
 * @param {TrendSegment[]} segments
 * @returns {{ waves: ElliottWave[], structure: WaveStructure, summary: string }}
 */
export function labelElliottWaves(pivots, segments) {
  if (segments.length < 3) {
    return {
      waves: [],
      structure: 'unknown',
      summary: 'C?n thêm swing ?? ??m sóng Elliott',
    };
  }

  const recent = segments.slice(-8);
  const structure = detectStructure(recent);
  const labels = structure === 'correction' ? CORRECTION_LABELS : IMPULSE_LABELS;

  /** @type {ElliottWave[]} */
  const waves = [];

  for (let i = 0; i < Math.min(recent.length, labels.length); i++) {
    const seg = recent[i];
    waves.push({
      label: `Sóng ${labels[i]}`,
      waveNumber: labels[i],
      startIndex: seg.startIndex,
      endIndex: seg.endIndex,
      startTime: seg.startTime,
      endTime: seg.endTime,
      startPrice: seg.startPrice,
      endPrice: seg.endPrice,
      structure,
      degree: structure === 'impulse' ? 'primary' : 'intermediate',
    });
  }

  const summary = structure === 'impulse'
    ? `C?u trúc xung ${waves.length} sóng — ${describeImpulse(waves)}`
    : structure === 'correction'
      ? `C?u trúc ?i?u ch?nh ABC — ${describeCorrection(waves)}`
      : 'C?u trúc ch?a rõ — c?n thêm d? li?u';

  return { waves, structure, summary };
}

/**
 * @param {TrendSegment[]} segments
 * @returns {WaveStructure}
 */
function detectStructure(segments) {
  const ups = segments.filter((s) => s.direction === 'uptrend').length;
  const downs = segments.filter((s) => s.direction === 'downtrend').length;

  if (segments.length >= 5) {
    const last5 = segments.slice(-5);
    const alt = last5.every((s, i) =>
      i === 0 ? true : s.direction !== last5[i - 1].direction
    );
    if (alt) return 'impulse';
  }

  if (segments.length >= 3 && downs >= 1 && ups >= 1) {
    const last3 = segments.slice(-3);
    if (last3.length === 3) return 'correction';
  }

  return ups > downs ? 'impulse' : downs > ups ? 'correction' : 'unknown';
}

/**
 * @param {ElliottWave[]} waves
 * @returns {string}
 */
function describeImpulse(waves) {
  if (waves.length < 3) return '?ang hình thành';
  const w3 = waves.find((w) => w.waveNumber === '3');
  const w1 = waves.find((w) => w.waveNumber === '1');
  if (w3 && w1 && Math.abs(w3.endPrice - w3.startPrice) > Math.abs(w1.endPrice - w1.startPrice)) {
    return 'Sóng 3 m?nh nh?t (?úng quy t?c Elliott)';
  }
  return '?ang trong xung — theo dõi sóng 3/5';
}

/**
 * @param {ElliottWave[]} waves
 * @returns {string}
 */
function describeCorrection(waves) {
  if (waves.length < 2) return '?i?u ch?nh s?m';
  const waveA = waves.find((w) => w.waveNumber === 'A');
  const waveC = waves.find((w) => w.waveNumber === 'C');
  if (waveA && waveC) {
    const aLen = Math.abs(waveA.endPrice - waveA.startPrice);
    const cLen = Math.abs(waveC.endPrice - waveC.startPrice);
    if (Math.abs(aLen - cLen) / Math.max(aLen, cLen) < 0.3) {
      return 'A ? C — mô hình ?i?u ch?nh zigzag';
    }
  }
  return '?i?u ch?nh ?ang di?n ra';
}

/**
 * Map wave number to typical market psychology sub-phase.
 * @param {string} waveNumber
 * @param {import('./TrendAnalyzer.js').TrendDirection} trend
 * @returns {string}
 */
export function wavePsychologyHint(waveNumber, trend) {
  const hints = {
    '1': 'Hy v?ng / Relief — kh?i ??u xu h??ng m?i',
    '2': 'Denial — ?i?u ch?nh nh? sau sóng 1',
    '3': 'Optimism ? Thrill — sóng m?nh nh?t',
    '4': 'Anxiety — tích l?y tr??c sóng cu?i',
    '5': 'Euphoria — ??nh xung, c?nh giác phân ph?i',
    A: 'Anxiety / Fear — b?t ??u ?i?u ch?nh',
    B: 'Denial / Hope — h?i ph?c gi?',
    C: 'Capitulation / Depression — k?t thúc ?i?u ch?nh',
  };
  const base = hints[waveNumber] ?? 'Theo dõi c?u trúc';
  return trend === 'downtrend' ? `${base} (trong xu h??ng gi?m)` : base;
}
