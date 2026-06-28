/**
 * Simplified Elliott Wave labeling on swing pivots.
 * Research heuristic � not a substitute for manual wave count.
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
      summary: 'Cần thêm swing để đếm sóng Elliott',
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
      label: `S�ng ${labels[i]}`,
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
    ? `Cấu trúc xung ${waves.length} sóng — ${describeImpulse(waves)}`
    : structure === 'correction'
      ? `Cấu trúc điều chỉnh ABC — ${describeCorrection(waves)}`
      : 'Cấu trúc chưa rõ — cần thêm dữ liệu';

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
  if (waves.length < 3) return 'đang hình thành';
  const w3 = waves.find((w) => w.waveNumber === '3');
  const w1 = waves.find((w) => w.waveNumber === '1');
  if (w3 && w1 && Math.abs(w3.endPrice - w3.startPrice) > Math.abs(w1.endPrice - w1.startPrice)) {
    return 'Sóng 3 mạnh nhất (đúng quy tắc Elliott)';
  }
  return 'đang trong xung — theo dõi sóng 3/5';
}

/**
 * @param {ElliottWave[]} waves
 * @returns {string}
 */
function describeCorrection(waves) {
  if (waves.length < 2) return 'điều chỉnh sớm';
  const waveA = waves.find((w) => w.waveNumber === 'A');
  const waveC = waves.find((w) => w.waveNumber === 'C');
  if (waveA && waveC) {
    const aLen = Math.abs(waveA.endPrice - waveA.startPrice);
    const cLen = Math.abs(waveC.endPrice - waveC.startPrice);
    if (Math.abs(aLen - cLen) / Math.max(aLen, cLen) < 0.3) {
      return 'A ≈ C — mô hình điều chỉnh zigzag';
    }
  }
  return 'điều chỉnh đang diễn ra';
}

/**
 * Map wave number to typical market psychology sub-phase.
 * @param {string} waveNumber
 * @param {import('./TrendAnalyzer.js').TrendDirection} trend
 * @returns {string}
 */
export function wavePsychologyHint(waveNumber, trend) {
  const hints = {
    '1': 'Hy vọng / Relief — khởi đầu xu hướng mới',
    '2': 'Denial — điều chỉnh nhẹ sau sóng 1',
    '3': 'Optimism → Thrill — sóng mạnh nhất',
    '4': 'Anxiety — tích lũy trước sóng cuối',
    '5': 'Euphoria — đỉnh xung, cảnh giác phân phối',
    A: 'Anxiety / Fear — bắt đầu điều chỉnh',
    B: 'Denial / Hope — hồi phục giả',
    C: 'Capitulation / Depression — kết thúc điều chỉnh',
  };
  const base = hints[waveNumber] ?? 'Theo dõi cấu trúc';
  return trend === 'downtrend' ? `${base} (trong xu hướng giảm)` : base;
}
