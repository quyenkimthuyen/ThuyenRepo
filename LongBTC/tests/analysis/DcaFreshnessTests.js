/**
 * DCA plan + data freshness tests.
 * Run: node tests/analysis/DcaFreshnessTests.js
 */

import { createSuite, header, footer } from '../harness.js';
import {
  describeDataFreshness,
  freshnessLevel,
  dataAgeMs,
} from '../../src/analysis/DataFreshness.js';
import {
  buildDcaRecommendation,
  TIER_DCA_MULTIPLIER,
  defaultDcaPlan,
} from '../../src/analysis/DcaPlanEngine.js';

const s = createSuite('DCA & Freshness');
header('DCA & Freshness');

const week = 7 * 24 * 60 * 60 * 1000;
const now = Date.UTC(2026, 5, 28);

{
  s.assert('DF-01: fresh week data', freshnessLevel(3 * 24 * 60 * 60 * 1000, 'W') === 'fresh');
  s.assert('DF-02: stale week data', freshnessLevel(2 * week, 'W') === 'stale');
  s.assert('DF-03: old week data', freshnessLevel(5 * week, 'W') === 'old');
  const d = describeDataFreshness(now - 2 * week, 'W', now);
  s.assert('DF-04: warn when stale', d.warn === true);
}

{
  const plan = { ...defaultDcaPlan(), monthlyBudgetUsd: 1000, currentBtcPct: 15, targetBtcPct: 20 };
  const cap = buildDcaRecommendation('capitulation', plan, { drawdownFromHighPct: -35 });
  s.assert('DF-05: capitulation boost', cap.suggestedMonthlyUsd === 1500);
  s.assert('DF-06: excellent multiplier', TIER_DCA_MULTIPLIER.excellent === 1.5);

  const euph = buildDcaRecommendation('euphoria', plan);
  s.assert('DF-07: euphoria pause', euph.suggestedMonthlyUsd === 0);
  s.assert('DF-08: allocation gap', cap.allocationGapPct === 5);
}

process.exit(footer(s.finish()));
