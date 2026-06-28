/**
 * Chart overlays for long-term BTC analysis (swings, cycles, waves).
 * @module chart/AnalysisOverlay
 */

import { BTC_HALVING_EVENTS, CYCLE_PHASE_RANGES } from '../analysis/BtcCycleConfig.js';

/**
 * @typedef {import('../data/Candle.js').Candle} Candle
 * @typedef {import('../analysis/LongTermAnalysisEngine.js').LongTermAnalysisResult} AnalysisResult
 */

const TREND_COLORS = {
  uptrend: '#22c55e',
  downtrend: '#ef4444',
  sideways: '#94a3b8',
};

const WAVE_COLORS = ['#3b82f6', '#8b5cf6', '#06b6d4', '#f59e0b', '#ec4899', '#14b8a6', '#f97316'];

/**
 * Snap epoch ms to nearest candle chart time (seconds).
 * @param {number} timestampMs
 * @param {Candle[]} candles
 * @returns {number}
 */
export function snapTimeToCandle(timestampMs, candles) {
  if (candles.length === 0) return Math.floor(timestampMs / 1000);
  let best = candles[0];
  let bestDiff = Math.abs(candles[0].timestamp - timestampMs);
  for (const c of candles) {
    const diff = Math.abs(c.timestamp - timestampMs);
    if (diff < bestDiff) {
      bestDiff = diff;
      best = c;
    }
  }
  return Math.floor(best.timestamp / 1000);
}

/**
 * Filter analysis pivots/segments to visible candle window.
 * @param {AnalysisResult} analysis
 * @param {Candle[]} candles
 * @returns {AnalysisResult}
 */
export function clipAnalysisToCandles(analysis, candles) {
  if (!candles.length) return analysis;
  const lastTs = candles[candles.length - 1].timestamp;
  const firstTs = candles[0].timestamp;

  const pivots = analysis.pivots.filter(
    (p) => p.timestamp >= firstTs && p.timestamp <= lastTs
  );
  const segments = analysis.segments.filter(
    (s) => s.endTime >= firstTs && s.startTime <= lastTs
  );
  const waves = analysis.elliott.waves.filter(
    (w) => w.endTime >= firstTs && w.startTime <= lastTs
  );

  return {
    ...analysis,
    pivots,
    segments,
    elliott: { ...analysis.elliott, waves },
  };
}

/**
 * Build swing + Elliott markers snapped to candle times.
 * @param {AnalysisResult} analysis
 * @param {Candle[]} candles
 * @param {{ maxSwingMarkers?: number }} [options]
 * @returns {Array<Record<string, unknown>>}
 */
export function buildAnalysisMarkers(analysis, candles, options = {}) {
  const maxSwing = options.maxSwingMarkers ?? 24;
  /** @type {Array<Record<string, unknown>>} */
  const markers = [];

  if (maxSwing > 0) {
    const swingSlice = analysis.pivots.length > maxSwing
      ? analysis.pivots.slice(-maxSwing)
      : analysis.pivots;

    for (const pivot of swingSlice) {
      markers.push({
        time: snapTimeToCandle(pivot.timestamp, candles),
        position: pivot.type === 'high' ? 'aboveBar' : 'belowBar',
        color: pivot.type === 'high' ? '#f59e0b' : '#3b82f6',
        shape: pivot.type === 'high' ? 'arrowDown' : 'arrowUp',
        text: pivot.type === 'high' ? '\u0110\u1ec9nh' : '\u0110\u00e1y',
      });
    }
  }

  for (let i = 0; i < analysis.elliott.waves.length; i++) {
    const wave = analysis.elliott.waves[i];
    markers.push({
      time: snapTimeToCandle(wave.endTime, candles),
      position: wave.endPrice >= wave.startPrice ? 'aboveBar' : 'belowBar',
      color: WAVE_COLORS[i % WAVE_COLORS.length],
      shape: 'circle',
      text: wave.waveNumber,
    });
  }

  markers.sort((a, b) => a.time - b.time);
  return dedupeMarkers(markers);
}

/**
 * Halving event markers on nearest candles.
 * @param {Candle[]} candles
 * @returns {Array<Record<string, unknown>>}
 */
export function buildHalvingMarkers(candles) {
  if (!candles.length) return [];
  const firstTs = candles[0].timestamp;
  const lastTs = candles[candles.length - 1].timestamp;

  /** @type {Array<Record<string, unknown>>} */
  const markers = [];

  for (const h of BTC_HALVING_EVENTS) {
    if (h.timestamp < firstTs || h.timestamp > lastTs) continue;
    markers.push({
      time: snapTimeToCandle(h.timestamp, candles),
      position: 'belowBar',
      color: '#a855f7',
      shape: 'square',
      text: h.label.replace('Halving ', 'H'),
    });
  }

  return markers;
}

/**
 * Cycle high/low horizontal price lines.
 * @param {AnalysisResult} analysis
 * @returns {Array<{ price: number, color: string, title: string, lineStyle?: number }>}
 */
export function buildCyclePriceLines(analysis) {
  const { cycleHigh, cycleLow } = analysis.cycleExtremes;
  /** @type {Array<{ price: number, color: string, title: string, lineStyle?: number }>} */
  const lines = [];

  if (cycleHigh != null) {
    lines.push({ price: cycleHigh, color: '#22c55e', title: '\u0110\u1ec9nh CK', lineStyle: 2 });
  }
  if (cycleLow != null) {
    lines.push({ price: cycleLow, color: '#ef4444', title: '\u0110\u00e1y CK', lineStyle: 2 });
  }

  return lines;
}

/**
 * Trend segment line series (snapped to candles).
 * @param {AnalysisResult} analysis
 * @param {Candle[]} candles
 * @returns {Array<{ color: string, lineWidth: number, data: Array<{ time: number, value: number }> }>}
 */
export function buildTrendLineSeries(analysis, candles) {
  return analysis.segments.map((seg) => ({
    color: TREND_COLORS[seg.direction] ?? '#94a3b8',
    lineWidth: seg.direction === 'sideways' ? 1 : 2,
    data: [
      { time: snapTimeToCandle(seg.startTime, candles), value: seg.startPrice },
      { time: snapTimeToCandle(seg.endTime, candles), value: seg.endPrice },
    ],
  }));
}

/**
 * Elliott wave path line series.
 * @param {AnalysisResult} analysis
 * @param {Candle[]} candles
 * @returns {Array<{ color: string, lineWidth: number, data: Array<{ time: number, value: number }> }>}
 */
export function buildElliottLineSeries(analysis, candles) {
  return analysis.elliott.waves.map((wave, i) => ({
    color: WAVE_COLORS[i % WAVE_COLORS.length],
    lineWidth: wave.waveNumber === '3' ? 3 : 2,
    data: [
      { time: snapTimeToCandle(wave.startTime, candles), value: wave.startPrice },
      { time: snapTimeToCandle(wave.endTime, candles), value: wave.endPrice },
    ],
  }));
}

/**
 * @param {Array<Record<string, unknown>>} markers
 * @returns {Array<Record<string, unknown>>}
 */
function dedupeMarkers(markers) {
  const seen = new Set();
  return markers.filter((m) => {
    const key = `${m.time}:${m.text}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/**
 * @param {string} phase
 * @returns {string}
 */
export function cyclePhaseColor(phase) {
  return CYCLE_PHASE_RANGES[phase]?.color ?? '#64748b';
}

/**
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
 * @param {number} value
 * @param {number} [digits=1]
 * @returns {string}
 */
export function formatPct(value, digits = 1) {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(digits)}%`;
}
