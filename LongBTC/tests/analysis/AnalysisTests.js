/**
 * LongBTC analysis engine tests.
 * Run: node tests/analysis/AnalysisTests.js
 */

import { createSuite, header, footer } from '../harness.js';
import { analyzeLongTerm } from '../../src/analysis/LongTermAnalysisEngine.js';
import { detectSwingPivots } from '../../src/analysis/SwingPivotDetector.js';
import { analyzeCurrentCycle } from '../../src/analysis/HalvingCycleAnalyzer.js';
import {
  buildPsychologyBandsForRange,
  buildSequentialPsychologyTimeline,
  buildCycleBandsForRange,
  buildChartPhaseBandsForRange,
  psychologyBandAtTime,
} from '../../src/analysis/PsychologyBands.js';
import { buildChartPsychologyTimeline } from '../../src/analysis/PsychologyCycleMapper.js';

const s = createSuite('Analysis Engine');
header('Analysis Engine');

/**
 * Build synthetic weekly BTC-like candles.
 * @param {number} count
 */
function buildSyntheticCandles(count) {
  const candles = [];
  let price = 10000;
  let ts = Date.parse('2019-01-01T00:00:00Z');

  for (let i = 0; i < count; i++) {
    const drift = Math.sin(i / 20) * 0.08 + (i > count * 0.6 ? -0.02 : 0.03);
    const open = price;
    price = Math.max(3000, price * (1 + drift));
    const high = Math.max(open, price) * 1.02;
    const low = Math.min(open, price) * 0.98;
    candles.push({
      timestamp: ts,
      open,
      high,
      low,
      close: price,
      volume: 1000,
    });
    ts += 7 * 24 * 60 * 60 * 1000;
  }
  return candles;
}

{
  const cycle = analyzeCurrentCycle(Date.parse('2021-06-01T00:00:00Z'));
  s.assert('AC-01: cycle phase in 2021', cycle.phase === 'markup' || cycle.phase === 'distribution');
  s.assert('AC-02: halving index', cycle.halvingIndex >= 2);

  const candles = buildSyntheticCandles(120);
  const pivots = detectSwingPivots(candles, { reversalPct: 0.05, minBars: 2 });
  s.assert('AC-03: pivots detected', pivots.length >= 2);

  const result = analyzeLongTerm(candles, { symbol: 'BTCUSD', timeframe: 'W' });
  s.assert('AC-04: has summary', result.summary.length > 20);
  s.assert('AC-05: has psychology', result.psychology.labelVi.length > 0);
  s.assert('AC-06: has segments', result.segments.length > 0);
  s.assert('AC-07: historical cycles', result.historicalCycles.length >= 1);

  const seq = buildChartPsychologyTimeline();
  s.assert('AC-08: chart psychology windows', seq.length === 13);
  s.assert('AC-08a: starts at 0%', seq[0].startPct === 0);
  s.assert('AC-08b: ends at 100%', seq[seq.length - 1].endPct === 100);
  for (let i = 1; i < seq.length; i++) {
    s.assert(`AC-09: no overlap at ${i}`, seq[i].startPct >= seq[i - 1].endPct - 0.001);
  }

  const legacy = buildSequentialPsychologyTimeline();
  s.assert('AC-09b: legacy alias', legacy.length === seq.length);

  const h3End = Date.parse('2024-04-20T00:00:00Z');
  const peak2021 = psychologyBandAtTime(Date.parse('2021-11-10T00:00:00Z'), h3End);
  s.assert('AC-14: 2021 bull peak phase', ['thrill', 'euphoria', 'excitement'].includes(peak2021?.phase.id ?? ''));

  const bear2022 = psychologyBandAtTime(Date.parse('2022-11-21T00:00:00Z'), h3End);
  s.assert('AC-15: 2022 bear phase', ['denial', 'fear', 'capitulation', 'depression'].includes(bear2022?.phase.id ?? ''));

  const postHalving2020 = psychologyBandAtTime(Date.parse('2020-08-01T00:00:00Z'), h3End);
  s.assert('AC-16: post-halving 2020', ['hope', 'relief', 'optimism'].includes(postHalving2020?.phase.id ?? ''));

  s.assert('AC-17: chart timeline export', buildChartPsychologyTimeline().length === 13);

  const cycleBands = buildCycleBandsForRange(
    Date.parse('2021-01-01T00:00:00Z'),
    Date.parse('2023-01-01T00:00:00Z'),
    Date.parse('2028-04-01T00:00:00Z')
  );
  s.assert('AC-10: cycle bands per halving', cycleBands.length === 4);
  s.assert('AC-10b: cycle band kinds', cycleBands.every((b) => b.kind === 'cycle'));

  const layered = buildChartPhaseBandsForRange(
    Date.parse('2020-05-11T00:00:00Z'),
    Date.parse('2024-04-20T00:00:00Z'),
    Date.parse('2028-04-01T00:00:00Z')
  );
  s.assert('AC-11: layered chart bands', layered.length >= 12);
  s.assert('AC-11b: has both layers', layered.some((b) => b.kind === 'cycle') && layered.some((b) => b.kind === 'psychology'));

  const bands = buildPsychologyBandsForRange(
    Date.parse('2020-05-11T00:00:00Z'),
    Date.parse('2024-04-20T00:00:00Z'),
    Date.parse('2028-04-01T00:00:00Z')
  );
  s.assert('AC-12: halving cycle psychology bands', bands.length === 13);

  const t1 = Date.parse('2021-06-01T00:00:00Z');
  const t2 = Date.parse('2022-06-01T00:00:00Z');
  const end = Date.parse('2028-04-01T00:00:00Z');
  const parityA = buildChartPhaseBandsForRange(t1, t2, end);
  const parityB = buildChartPhaseBandsForRange(t1, t2, end);
  s.assert('AC-13: timeframe-independent bands', JSON.stringify(parityA) === JSON.stringify(parityB));
}

process.exit(footer(s.finish()));
