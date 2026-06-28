/**
 * Chart overlays for long-term BTC analysis (swings, cycles, waves).
 * @module chart/AnalysisOverlay
 */

import { CYCLE_PHASE_RANGES } from '../analysis/BtcCycleConfig.js';

/**
 * @typedef {import('../analysis/LongTermAnalysisEngine.js').LongTermAnalysisResult} AnalysisResult
 */

const TREND_COLORS = {
  uptrend: '#22c55e',
  downtrend: '#ef4444',
  sideways: '#94a3b8',
};

const WAVE_COLORS = ['#3b82f6', '#8b5cf6', '#06b6d4', '#f59e0b', '#ec4899', '#14b8a6', '#f97316'];

/**
 * Build Lightweight Charts markers for swing pivots and wave labels.
 * @param {AnalysisResult} analysis
 * @returns {Array<Record<string, unknown>>}
 */
export function buildAnalysisMarkers(analysis) {
  /** @type {Array<Record<string, unknown>>} */
  const markers = [];

  for (const pivot of analysis.pivots) {
    markers.push({
      time: Math.floor(pivot.timestamp / 1000),
      position: pivot.type === 'high' ? 'aboveBar' : 'belowBar',
      color: pivot.type === 'high' ? '#f59e0b' : '#3b82f6',
      shape: pivot.type === 'high' ? 'arrowDown' : 'arrowUp',
      text: pivot.type === 'high' ? 'Đỉnh' : 'Đáy',
    });
  }

  for (let i = 0; i < analysis.elliott.waves.length; i++) {
    const wave = analysis.elliott.waves[i];
    markers.push({
      time: Math.floor(wave.endTime / 1000),
      position: wave.endPrice >= wave.startPrice ? 'aboveBar' : 'belowBar',
      color: WAVE_COLORS[i % WAVE_COLORS.length],
      shape: 'circle',
      text: wave.waveNumber,
    });
  }

  markers.sort((a, b) => a.time - b.time);
  return markers;
}

/**
 * Build price lines for cycle phase boundaries (vertical markers as price annotations).
 * @param {AnalysisResult} analysis
 * @returns {Array<{ price: number, color: string, title: string }>}
 */
export function buildCyclePriceLines(analysis) {
  const { cycleHigh, cycleLow } = analysis.cycleExtremes;
  if (cycleHigh == null || cycleLow == null) return [];

  return [
    { price: cycleHigh, color: '#22c55e', title: 'Đỉnh chu kỳ' },
    { price: cycleLow, color: '#ef4444', title: 'Đáy chu kỳ' },
  ];
}

/**
 * Build line series data for trend segments overlay.
 * @param {AnalysisResult} analysis
 * @returns {Array<{ color: string, data: Array<{ time: number, value: number }> }>}
 */
export function buildTrendLineSeries(analysis) {
  return analysis.segments.map((seg) => ({
    color: TREND_COLORS[seg.direction] ?? '#94a3b8',
    data: [
      { time: Math.floor(seg.startTime / 1000), value: seg.startPrice },
      { time: Math.floor(seg.endTime / 1000), value: seg.endPrice },
    ],
  }));
}

/**
 * @param {string} phase
 * @returns {string}
 */
export function cyclePhaseColor(phase) {
  return CYCLE_PHASE_RANGES[phase]?.color ?? '#64748b';
}

/**
 * Format timestamp for display.
 * @param {number} ts
 * @returns {string}
 */
export function formatAnalysisDate(ts) {
  return new Date(ts).toLocaleDateString('vi-VN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format percentage.
 * @param {number} value
 * @param {number} [digits=1]
 * @returns {string}
 */
export function formatPct(value, digits = 1) {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(digits)}%`;
}
