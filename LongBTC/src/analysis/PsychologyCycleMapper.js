/**
 * Map cycle position, trend, drawdown, and Elliott waves to psychology phases.
 * @module analysis/PsychologyCycleMapper
 */

import { PSYCHOLOGY_PHASES } from './BtcCycleConfig.js';
import { wavePsychologyHint } from './ElliottWaveAnalyzer.js';

/**
 * @typedef {import('./HalvingCycleAnalyzer.js').CurrentCycleState} CurrentCycleState
 * @typedef {import('./TrendAnalyzer.js').TrendDirection} TrendDirection
 * @typedef {import('./ElliottWaveAnalyzer.js').ElliottWave} ElliottWave
 * @typedef {{
 *   cycleLow: number|null,
 *   cycleHigh: number|null,
 *   drawdownFromHighPct: number|null,
 * }} CycleExtremes
 * @typedef {{
 *   phaseId: string,
 *   label: string,
 *   labelVi: string,
 *   color: string,
 *   confidence: number,
 *   description: string,
 *   cycleContribution: string,
 *   trendContribution: string,
 *   waveContribution: string,
 *   priceContribution: string,
 * }} PsychologyAssessment
 */

/** Halving-calendar windows (0-1 progress) for each psychology label. */
const CYCLE_PHASE_MAP = {
  optimism: [0.20, 0.30],
  excitement: [0.30, 0.38],
  thrill: [0.38, 0.48],
  euphoria: [0.48, 0.58],
  anxiety: [0.55, 0.62],
  denial: [0.60, 0.68],
  fear: [0.68, 0.76],
  capitulation: [0.76, 0.84],
  depression: [0.84, 0.92],
  hope: [0.92, 0.97],
  relief: [0.97, 1.0],
};

const BULLISH_PHASES = ['optimism', 'excitement', 'thrill', 'euphoria', 'hope', 'relief'];
const BEARISH_PHASES = ['anxiety', 'denial', 'fear', 'capitulation', 'depression'];

/**
 * Score each psychology phase and return best match.
 * Price drawdown + trend weigh heavily so euphoria is not shown during deep corrections.
 * @param {CurrentCycleState} cycle
 * @param {{ direction: TrendDirection, confidence: number }} trend
 * @param {ElliottWave[]} waves
 * @param {CycleExtremes} [extremes]
 * @returns {PsychologyAssessment}
 */
export function assessPsychology(cycle, trend, waves, extremes = {}) {
  const progress = cycle.progressPct / 100;
  const lastWave = waves.length > 0 ? waves[waves.length - 1] : null;
  const drawdown = extremes.drawdownFromHighPct ?? 0;
  const drawdownAbs = Math.abs(drawdown);

  const calendarWeight = drawdownAbs >= 25 ? 0.12 : drawdownAbs >= 15 ? 0.22 : 0.35;
  const drawdownWeight = drawdownAbs >= 15 ? 0.38 : 0.18;
  const trendWeight = trend.confidence >= 70 ? 0.32 : 0.24;
  const waveWeight = 0.12;
  const phaseBonusWeight = drawdownAbs >= 25 ? 0.06 : 0.11;

  let best = PSYCHOLOGY_PHASES[0];
  let bestScore = -1;

  for (const phase of PSYCHOLOGY_PHASES) {
    const range = CYCLE_PHASE_MAP[phase.id];
    let score = 0;

    if (range) {
      const [lo, hi] = range;
      if (progress >= lo && progress <= hi) score += 100 * calendarWeight;
      else {
        const mid = (lo + hi) / 2;
        score += Math.max(0, 65 - Math.abs(progress - mid) * 120) * calendarWeight;
      }
    }

    score += drawdownPsychologyScore(phase.id, drawdown) * drawdownWeight;
    score += trendPsychologyScore(phase.id, trend.direction) * trendWeight;
    if (lastWave) score += wavePsychologyScore(phase.id, lastWave.waveNumber) * waveWeight;
    score += cyclePhaseBonus(phase.id, cycle.phase, drawdownAbs) * phaseBonusWeight;

    if (score > bestScore) {
      bestScore = score;
      best = phase;
    }
  }

  const cycleNote = `Chu k\u1ef3 halving #${cycle.halvingIndex + 1}: ${cycle.phaseLabel} (${cycle.progressPct.toFixed(1)}% l\u1ecbch)`;
  const trendNote = `Xu h\u01b0\u1edbng: ${trend.direction} (\u0111\u1ed9 tin c\u1eady ${trend.confidence}%)`;
  const waveNote = lastWave
    ? wavePsychologyHint(lastWave.waveNumber, trend.direction)
    : 'Ch\u01b0a x\u00e1c \u0111\u1ecbnh s\u00f3ng Elliott';
  const priceNote = buildPriceNote(extremes, drawdown);

  return {
    phaseId: best.id,
    label: best.label,
    labelVi: best.labelVi,
    color: best.color,
    confidence: Math.min(95, Math.round(bestScore)),
    description: buildDescription(best, cycle, trend, lastWave, priceNote),
    cycleContribution: cycleNote,
    trendContribution: trendNote,
    waveContribution: waveNote,
    priceContribution: priceNote,
  };
}

/**
 * @param {CycleExtremes} extremes
 * @param {number} drawdown
 * @returns {string}
 */
function buildPriceNote(extremes, drawdown) {
  if (extremes.cycleHigh == null) {
    return 'Ch\u01b0a \u0111\u1ee7 d\u1eef li\u1ec7u \u0111\u1ec9nh chu k\u1ef3';
  }
  const dd = Math.abs(drawdown);
  if (dd >= 40) {
    return `Gi\u00e1 gi\u1ea3m ~${dd.toFixed(0)}% t\u1eeb \u0111\u1ec9nh chu k\u1ef3 \u2014 giai \u0111o\u1ea1n s\u1ee3 h\u00e3i / b\u00e1n th\u00e1o`;
  }
  if (dd >= 25) {
    return `Gi\u00e1 gi\u1ea3m ~${dd.toFixed(0)}% t\u1eeb \u0111\u1ec9nh chu k\u1ef3 \u2014 lo l\u1eafng / ph\u1ee7 nh\u1eadn`;
  }
  if (dd >= 15) {
    return `Gi\u00e1 h\u1ed3i l\u1ea1i ~${dd.toFixed(0)}% t\u1eeb \u0111\u1ec9nh \u2014 t\u00e2m l\u00fd b\u1eaft \u0111\u1ea7u chuy\u1ec3n`;
  }
  if (dd <= 5) {
    return 'Gi\u00e1 g\u1ea7n \u0111\u1ec9nh chu k\u1ef3 \u2014 t\u00e2m l\u00fd t\u00edch c\u1ef1c c\u00f3 th\u1ec3 cao';
  }
  return `Drawdown ~${dd.toFixed(0)}% t\u1eeb \u0111\u1ec9nh chu k\u1ef3`;
}

/**
 * @param {string} phaseId
 * @param {number} drawdownPct - negative when price below cycle high
 * @returns {number}
 */
function drawdownPsychologyScore(phaseId, drawdownPct) {
  const dd = Math.abs(drawdownPct);

  if (dd >= 45) {
    if (phaseId === 'capitulation' || phaseId === 'depression') return 95;
    if (phaseId === 'fear') return 90;
    if (BULLISH_PHASES.includes(phaseId)) return 8;
    if (['anxiety', 'denial'].includes(phaseId)) return 70;
    return 40;
  }
  if (dd >= 30) {
    if (['fear', 'capitulation', 'anxiety'].includes(phaseId)) return 90;
    if (phaseId === 'denial') return 80;
    if (phaseId === 'euphoria' || phaseId === 'thrill') return 10;
    return 45;
  }
  if (dd >= 20) {
    if (['anxiety', 'denial', 'fear'].includes(phaseId)) return 85;
    if (['euphoria', 'excitement'].includes(phaseId)) return 15;
    return 50;
  }
  if (dd >= 10) {
    if (['anxiety', 'denial'].includes(phaseId)) return 65;
    if (phaseId === 'euphoria') return 35;
    return 50;
  }
  if (dd <= 5 && ['euphoria', 'thrill', 'excitement'].includes(phaseId)) return 80;
  return 50;
}

export function buildPsychologyTimeline() {
  return PSYCHOLOGY_PHASES.map((phase) => {
    const range = CYCLE_PHASE_MAP[phase.id] ?? [0, 0];
    return {
      phase,
      startPct: range[0] * 100,
      endPct: range[1] * 100,
    };
  });
}

/**
 * Non-overlapping psychology windows (0-100%) for chart/history display.
 * Calibrated to BTC halving-to-halving span (actual dates, not fixed 1460d).
 * @returns {Array<{ phase: typeof PSYCHOLOGY_PHASES[number], startPct: number, endPct: number }>}
 */
export function buildChartPsychologyTimeline() {
  const byId = Object.fromEntries(PSYCHOLOGY_PHASES.map((p) => [p.id, p]));
  /** @type {Array<[string, number, number]>} */
  const windows = [
    ['hope', 0, 10],
    ['relief', 10, 18],
    ['optimism', 18, 26],
    ['excitement', 26, 34],
    ['thrill', 34, 42],
    ['euphoria', 42, 52],
    ['anxiety', 52, 58],
    ['denial', 58, 65],
    ['fear', 65, 72],
    ['capitulation', 72, 80],
    ['depression', 80, 88],
    ['hope', 88, 94],
    ['relief', 94, 100],
  ];

  return windows.map(([id, startPct, endPct]) => ({
    phase: byId[id],
    startPct,
    endPct,
  }));
}

/**
 * Calendar psychology phase at progress through a halving cycle (0-1).
 * @param {number} progress
 * @returns {typeof PSYCHOLOGY_PHASES[number]|undefined}
 */
export function psychologyPhaseAtCycleProgress(progress) {
  const pct = Math.max(0, Math.min(100, progress * 100));
  const timeline = buildChartPsychologyTimeline();
  const hit = timeline.find((w) => pct >= w.startPct && pct < w.endPct);
  return hit?.phase ?? timeline[timeline.length - 1]?.phase;
}

/**
 * @param {typeof PSYCHOLOGY_PHASES[number]} phase
 * @param {CurrentCycleState} cycle
 * @param {{ direction: TrendDirection }} trend
 * @param {ElliottWave|null} lastWave
 * @param {string} priceNote
 * @returns {string}
 */
function buildDescription(phase, cycle, trend, lastWave, priceNote) {
  const parts = [
    `Th\u1ecb tr\u01b0\u1eddng \u0111ang \u1edf giai \u0111o\u1ea1n "${phase.labelVi}" (${phase.label}).`,
    priceNote + '.',
    `Chu k\u1ef3 halving (l\u1ecbch): ${cycle.phaseLabel}, c\u00f2n ~${cycle.daysToNextHalving} ng\u00e0y \u0111\u1ebfn halving ti\u1ebfp theo.`,
  ];
  if (lastWave) {
    parts.push(`S\u00f3ng hi\u1ec7n t\u1ea1i: ${lastWave.label} \u2014 ${wavePsychologyHint(lastWave.waveNumber, trend.direction)}`);
  }
  return parts.join(' ');
}

/**
 * @param {string} phaseId
 * @param {TrendDirection} direction
 * @returns {number}
 */
function trendPsychologyScore(phaseId, direction) {
  if (direction === 'uptrend' && BULLISH_PHASES.includes(phaseId)) return 85;
  if (direction === 'downtrend' && BEARISH_PHASES.includes(phaseId)) return 85;
  if (direction === 'sideways') return 50;
  if (direction === 'downtrend' && BULLISH_PHASES.includes(phaseId)) return 12;
  if (direction === 'uptrend' && BEARISH_PHASES.includes(phaseId)) return 12;
  return 25;
}

/**
 * @param {string} phaseId
 * @param {string} waveNumber
 * @returns {number}
 */
function wavePsychologyScore(phaseId, waveNumber) {
  const map = {
    '1': ['hope', 'relief', 'optimism'],
    '2': ['denial', 'anxiety'],
    '3': ['optimism', 'excitement', 'thrill'],
    '4': ['anxiety', 'denial'],
    '5': ['euphoria', 'thrill'],
    A: ['anxiety', 'fear'],
    B: ['denial', 'hope'],
    C: ['capitulation', 'depression', 'fear'],
  };
  return (map[waveNumber] ?? []).includes(phaseId) ? 90 : 15;
}

/**
 * @param {string} phaseId
 * @param {string} cyclePhase
 * @param {number} drawdownAbs
 * @returns {number}
 */
function cyclePhaseBonus(phaseId, cyclePhase, drawdownAbs) {
  if (drawdownAbs >= 30) {
    if (BEARISH_PHASES.includes(phaseId)) return 75;
    if (phaseId === 'euphoria') return 5;
    return 25;
  }

  const bonuses = {
    accumulation: ['hope', 'relief', 'optimism', 'depression', 'capitulation'],
    markup: ['optimism', 'excitement', 'thrill', 'euphoria'],
    distribution: ['euphoria', 'anxiety', 'denial'],
    markdown: ['fear', 'capitulation', 'depression', 'hope'],
  };
  return (bonuses[cyclePhase] ?? []).includes(phaseId) ? 85 : 20;
}
