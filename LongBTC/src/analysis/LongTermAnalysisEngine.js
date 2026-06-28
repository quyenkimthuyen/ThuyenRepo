/**
 * Orchestrates long-term BTC analysis: cycle → trend → Elliott → psychology.
 * @module analysis/LongTermAnalysisEngine
 */

import { bus, Events } from '../core/EventBus.js';
import { createLogger } from '../utils/logger.js';
import { detectSwingPivots, defaultReversalPct } from './SwingPivotDetector.js';
import { buildTrendSegments, classifyOverallTrend } from './TrendAnalyzer.js';
import {
  analyzeCurrentCycle,
  buildHistoricalCycles,
  cycleExtremes,
} from './HalvingCycleAnalyzer.js';
import { labelElliottWaves } from './ElliottWaveAnalyzer.js';
import { assessPsychology, buildPsychologyTimeline } from './PsychologyCycleMapper.js';

const log = createLogger('LongTermAnalysis');

/**
 * @typedef {import('../data/Candle.js').Candle} Candle
 * @typedef {{
 *   symbol: string,
 *   timeframe: string,
 *   candleCount: number,
 *   analyzedAt: number,
 *   pivots: import('./SwingPivotDetector.js').SwingPivot[],
 *   segments: import('./TrendAnalyzer.js').TrendSegment[],
 *   overallTrend: ReturnType<typeof classifyOverallTrend>,
 *   currentCycle: import('./HalvingCycleAnalyzer.js').CurrentCycleState,
 *   historicalCycles: import('./HalvingCycleAnalyzer.js').HistoricalCycle[],
 *   cycleExtremes: ReturnType<typeof cycleExtremes>,
 *   elliott: ReturnType<typeof labelElliottWaves>,
 *   psychology: import('./PsychologyCycleMapper.js').PsychologyAssessment,
 *   psychologyTimeline: ReturnType<typeof buildPsychologyTimeline>,
 *   summary: string,
 * }} LongTermAnalysisResult
 */

/** @type {LongTermAnalysisResult|null} */
let lastResult = null;

/**
 * Run full long-term analysis pipeline on candle data.
 * @param {Candle[]} candles
 * @param {{ symbol?: string, timeframe?: string, reversalPct?: number }} [options]
 * @returns {LongTermAnalysisResult}
 */
export function analyzeLongTerm(candles, options = {}) {
  const symbol = options.symbol ?? 'BTCUSD';
  const timeframe = options.timeframe ?? 'W';
  const reversalPct = options.reversalPct ?? defaultReversalPct(timeframe);

  const pivots = detectSwingPivots(candles, { reversalPct });
  const segments = buildTrendSegments(pivots);
  const overallTrend = classifyOverallTrend(pivots);
  const currentCycle = analyzeCurrentCycle();
  const historicalCycles = buildHistoricalCycles(candles);
  const extremes = cycleExtremes(candles, currentCycle);
  const elliott = labelElliottWaves(pivots, segments);
  const psychology = assessPsychology(currentCycle, overallTrend, elliott.waves);
  const psychologyTimeline = buildPsychologyTimeline();

  const summary = [
    `BTC ${timeframe}: ${overallTrend.reason}`,
    `Chu kỳ: ${currentCycle.phaseLabel} (${currentCycle.progressPct.toFixed(1)}% chu kỳ halving)`,
    elliott.summary,
    `Tâm lý: ${psychology.labelVi} (${psychology.confidence}% tin cậy)`,
  ].join(' · ');

  const result = {
    symbol,
    timeframe,
    candleCount: candles.length,
    analyzedAt: Date.now(),
    pivots,
    segments,
    overallTrend,
    currentCycle,
    historicalCycles,
    cycleExtremes: extremes,
    elliott,
    psychology,
    psychologyTimeline,
    summary,
  };

  lastResult = result;
  log.info('Analysis complete:', summary);
  return result;
}

/**
 * @returns {LongTermAnalysisResult|null}
 */
export function getLastAnalysis() {
  return lastResult;
}

/**
 * Analysis engine module with initialize lifecycle.
 */
const LongTermAnalysisEngine = {
  /**
   * @param {{ bus: import('../core/EventBus.js').EventBus }} ctx
   */
  async initialize(ctx) {
    ctx.bus.on(Events.CHART_LOADED, ({ candles, symbol, timeframe }) => {
      if (symbol === 'BTCUSD' && candles?.length > 0) {
        const result = analyzeLongTerm(candles, { symbol, timeframe });
        ctx.bus.emit(Events.ANALYSIS_COMPLETE, result);
      }
    });
    log.info('Long-term analysis engine ready');
  },

  analyzeLongTerm,
  getLastAnalysis,
};

export default LongTermAnalysisEngine;
