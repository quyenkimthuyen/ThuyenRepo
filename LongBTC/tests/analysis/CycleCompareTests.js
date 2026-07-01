/**
 * Halving cycle compare timeline tests.
 * Run: node tests/analysis/CycleCompareTests.js
 */

import { createSuite, header, footer } from '../harness.js';
import { buildHalvingCycleCompare, snapshotAtCycleProgress } from '../../src/analysis/CycleCompareTimeline.js';
import { BTC_HALVING_EVENTS } from '../../src/analysis/BtcCycleConfig.js';

const s = createSuite('Cycle Compare');
header('Cycle Compare');

const h4 = BTC_HALVING_EVENTS[3].timestamp;
const mid2025 = h4 + 400 * 24 * 60 * 60 * 1000;

{
  const data = buildHalvingCycleCompare(mid2025);
  s.assert('CC-01: three halving rows', data.rows.length === 3);
  s.assert('CC-02: years 2016 2020 2024', data.rows.map((r) => r.startYear).join(',') === '2016,2020,2024');
  s.assert('CC-03: two completed', data.rows.filter((r) => r.isComplete).length === 2);
  s.assert('CC-04: one current', data.rows.filter((r) => r.isCurrent).length === 1);
  s.assert('CC-05: current is 2024', data.rows.find((r) => r.isCurrent)?.startYear === 2024);
  s.assert('CC-06: past cycles 100%', data.rows.filter((r) => !r.isCurrent).every((r) => r.progressPct === 100));
  s.assert('CC-07: current partial', data.rows.find((r) => r.isCurrent).progressPct > 0);
  s.assert('CC-08: current partial < 100', data.rows.find((r) => r.isCurrent).progressPct < 100);
  s.assert('CC-09: shared marker', data.rows.every((r) => r.compareMarkerPct === data.currentProgressPct));
  s.assert('CC-10: phase ruler', data.phaseRuler.markerPct === data.currentProgressPct);
}

{
  const candles = [];
  let price = 5000;
  const h2 = BTC_HALVING_EVENTS[1].timestamp;
  for (let i = 0; i < 200; i++) {
    price *= 1.005;
    candles.push({
      timestamp: h2 + i * 7 * 24 * 60 * 60 * 1000,
      open: price,
      high: price * 1.02,
      low: price * 0.98,
      close: price,
      volume: 1,
    });
  }
  const withPrices = buildHalvingCycleCompare(candles, h2 + 100 * 7 * 24 * 60 * 60 * 1000);
  s.assert('CC-11: marker prices when candles', withPrices.rows[0].markerPrice != null);
  s.assert('CC-12: snapshot fn', snapshotAtCycleProgress(candles, 1, 25)?.price > 0);
}

footer(s.finish());
