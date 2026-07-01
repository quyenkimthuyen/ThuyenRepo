#!/usr/bin/env node
/**
 * PARL test runner — executes all unit & integration test suites.
 * Run: node tests/run-all.mjs
 */

import { spawnSync } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

/** @type {Array<{ file: string, label: string }>} */
const SUITES = [
  { file: 'analysis/AnalysisTests.js', label: 'BTC Analysis Engine' },
  { file: 'analysis/CycleCompareTests.js', label: 'Cycle Compare' },
  { file: 'analysis/DcaBacktestTests.js', label: 'DCA Backtest' },
  { file: 'analysis/DcaFreshnessTests.js', label: 'DCA & Freshness' },
  { file: 'data/TimeframeTests.js', label: 'Timeframe Utils' },
  { file: 'data/DataLayerTests.js', label: 'Data Layer' },
  { file: 'data/DefaultDataTests.js', label: 'Default Bundled Data' },
  { file: 'replay/ReplayTests.js', label: 'Replay Engine' },
  { file: 'strategy/Phase5Tests.js', label: 'Strategies (Phase 5)' },
  { file: 'simulation/TradeTests.js', label: 'Trade Simulation' },
  { file: 'research/CompareTests.js', label: 'Compare & Persistence' },
  { file: 'utils/ChartNavigationTests.js', label: 'Chart Navigation' },
  { file: 'utils/StorageUtilsTests.js', label: 'Storage Utils' },
  { file: 'statistics/StatisticsTests.js', label: 'Statistics' },
  { file: 'analytics/HeatmapTests.js', label: 'Heatmap Analytics' },
  { file: 'report/ReportTests.js', label: 'Reports' },
  { file: 'optimizer/OptimizerTests.js', label: 'Optimizer' },
  { file: 'scoring/ScoringTests.js', label: 'AI Scoring' },
  { file: 'scoring/ScoreCalibrationTests.js', label: 'Score Calibration' },
  { file: 'integration/DataStrategyTests.js', label: 'Integration: Data → Strategy' },
  { file: 'integration/PipelineTests.js', label: 'Integration: Full Pipeline' },
];

console.log('\n╔══════════════════════════════════════════════╗');
console.log('║   LongBTC Test Suite — Unit + Integration    ║');
console.log('╚══════════════════════════════════════════════╝');

let totalPassed = 0;
let totalFailed = 0;
/** @type {Array<{ label: string, ok: boolean, output?: string }>} */
const results = [];

for (const suite of SUITES) {
  const path = join(__dirname, suite.file);
  const proc = spawnSync(process.execPath, [path], {
    encoding: 'utf8',
    cwd: join(__dirname, '..'),
    maxBuffer: 10 * 1024 * 1024,
  });

  const output = `${proc.stdout ?? ''}${proc.stderr ?? ''}`;
  const match = output.match(/(\d+) passed, (\d+) failed/);
  const passed = match ? Number(match[1]) : 0;
  const failed = match ? Number(match[2]) : (proc.status !== 0 ? 1 : 0);

  totalPassed += passed;
  totalFailed += failed;

  const ok = proc.status === 0 && failed === 0;
  results.push({ label: suite.label, ok, output: ok ? undefined : output });

  const icon = ok ? '✓' : '✗';
  console.log(`${icon} ${suite.label.padEnd(36)} ${passed} passed, ${failed} failed`);
}

console.log('\n────────────────────────────────────────────────');
console.log(`TOTAL: ${totalPassed} passed, ${totalFailed} failed across ${SUITES.length} suites`);

if (totalFailed > 0) {
  console.log('\nFailed suite details:\n');
  for (const r of results) {
    if (!r.ok && r.output) {
      console.log(`--- ${r.label} ---`);
      console.log(r.output.trim());
      console.log('');
    }
  }
  process.exit(1);
}

console.log('\nAll tests passed.\n');
process.exit(0);
