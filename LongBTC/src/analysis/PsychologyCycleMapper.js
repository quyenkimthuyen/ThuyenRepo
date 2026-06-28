
/**
 * Map cycle position, trend, and Elliott waves to market psychology phases.
 * @module analysis/PsychologyCycleMapper
 */

import { PSYCHOLOGY_PHASES } from './BtcCycleConfig.js';
import { wavePsychologyHint } from './ElliottWaveAnalyzer.js';

/**
 * @typedef {import('./HalvingCycleAnalyzer.js').CurrentCycleState} CurrentCycleState
 * @typedef {import('./TrendAnalyzer.js').TrendDirection} TrendDirection
 * @typedef {import('./ElliottWaveAnalyzer.js').ElliottWave} ElliottWave
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
 * }} PsychologyAssessment
 */

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

export function assessPsychology(cycle, trend, waves) {
  const progress = cycle.progressPct / 100;
  const lastWave = waves.length > 0 ? waves[waves.length - 1] : null;

  let best = PSYCHOLOGY_PHASES[0];
  let bestScore = -1;
  let cycleNote = '';
  let trendNote = '';
  let waveNote = '';

  for (const phase of PSYCHOLOGY_PHASES) {
    const range = CYCLE_PHASE_MAP[phase.id];
    let score = 0;

    if (range) {
      const [lo, hi] = range;
      if (progress >= lo && progress <= hi) score += 40;
      else {
        const mid = (lo + hi) / 2;
        score += Math.max(0, 25 - Math.abs(progress - mid) * 80);
      }
    }

    score += trendPsychologyScore(phase.id, trend.direction) * 0.25;
    if (lastWave) score += wavePsychologyScore(phase.id, lastWave.waveNumber) * 0.20;
    score += cyclePhaseBonus(phase.id, cycle.phase) * 0.15;

    if (score > bestScore) {
      bestScore = score;
      best = phase;
    }
  }

  cycleNote = `Chu kỳ halving #${cycle.halvingIndex + 1}: ${cycle.phaseLabel} (${cycle.progressPct.toFixed(1)}%)`;
  trendNote = `Xu hướng: ${trend.direction} (độ tin cậy ${trend.confidence}%)`;
  waveNote = lastWave
    ? wavePsychologyHint(lastWave.waveNumber, trend.direction)
    : 'Chưa xác định sóng Elliott';

  return {
    phaseId: best.id,
    label: best.label,
    labelVi: best.labelVi,
    color: best.color,
    confidence: Math.min(95, Math.round(bestScore)),
    description: buildDescription(best, cycle, trend, lastWave),
    cycleContribution: cycleNote,
    trendContribution: trendNote,
    waveContribution: waveNote,
  };
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

function buildDescription(phase, cycle, trend, lastWave) {
  const parts = [
    `Thị trường đang ở giai đoạn "${phase.labelVi}" (${phase.label}).`,
    `Chu kỳ 4 năm: ${cycle.phaseLabel}, còn ~${cycle.daysToNextHalving} ngày đến halving tiếp theo.`,
  ];
  if (lastWave) parts.push(`Sóng hiện tại: ${lastWave.label} — ${wavePsychologyHint(lastWave.waveNumber, trend.direction)}`);
  return parts.join(' ');
}

function trendPsychologyScore(phaseId, direction) {
  const bullish = ['optimism', 'excitement', 'thrill', 'euphoria', 'hope', 'relief'];
  const bearish = ['anxiety', 'denial', 'fear', 'capitulation', 'depression'];
  if (direction === 'uptrend' && bullish.includes(phaseId)) return 80;
  if (direction === 'downtrend' && bearish.includes(phaseId)) return 80;
  if (direction === 'sideways') return 50;
  return 20;
}

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

function cyclePhaseBonus(phaseId, cyclePhase) {
  const bonuses = {
    accumulation: ['hope', 'relief', 'optimism', 'depression', 'capitulation'],
    markup: ['optimism', 'excitement', 'thrill', 'euphoria'],
    distribution: ['euphoria', 'anxiety', 'denial'],
    markdown: ['fear', 'capitulation', 'depression', 'hope'],
  };
  return (bonuses[cyclePhase] ?? []).includes(phaseId) ? 85 : 20;
}
