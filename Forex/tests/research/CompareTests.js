/**
 * Compare engine + persistence strip tests.
 * Run: node tests/research/CompareTests.js
 */

import { createSuite, header, footer, candle } from '../harness.js';
import { stripGridSearchForStorage, stripBacktestResult } from '../../src/optimizer/researchPersistence.js';
import { computeStatistics } from '../../src/statistics/StatisticsCalculator.js';
import { simulateTrades } from '../../src/simulation/TradeSimulator.js';
import { mergeTradeConfig } from '../../src/simulation/TradeConfig.js';
import { registerBuiltinStrategies } from '../../src/strategies/index.js';
import { registry } from '../../src/plugin/PluginRegistry.js';
import StrategyEngine from '../../src/strategy/StrategyEngine.js';
import DataManager from '../../src/data/DataManager.js';

const s = createSuite('Compare & Persistence');
header('Compare & Persistence');

registerBuiltinStrategies();
s.assert('CP-01: Built-in strategies registered', registry.size >= 7);

{
  const stats = computeStatistics([], 10000);
  const stripped = stripBacktestResult({
    signals: [{ id: 'a' }],
    trades: [{ id: 't' }],
    stats,
    barsScanned: 10,
    durationMs: 5,
  });
  s.assert('CP-02: Strip removes heavy arrays', !('signals' in stripped) && stripped.signalCount === 1);
  s.assert('CP-03: Strip keeps stats', stripped.stats.totalTrades === stats.totalTrades);
}

{
  const grid = stripGridSearchForStorage({
    strategyId: 'ema-pullback',
    symbol: 'EURUSD',
    timeframe: 'H1',
    rankMetric: 'expectancy',
    totalCombinations: 3,
    durationMs: 100,
    entries: Array.from({ length: 3 }, (_, i) => ({
      params: { rr: i + 1 },
      rank: 3 - i,
      result: {
        signals: [],
        trades: [],
        stats: computeStatistics([], 10000),
        barsScanned: 1,
        durationMs: 1,
      },
    })),
    best: null,
  });
  s.assert('CP-04: Grid strip compact', grid && grid.entries.length === 3);
}

{
  const candles = Array.from({ length: 80 }, (_, i) => candle(i, 1.08, 1.09, 1.07, 1.085));
  const originalGet = DataManager.getCandles.bind(DataManager);
  DataManager.getCandles = async () => candles;

  try {
    const scan = await StrategyEngine.runStrategy('ema-pullback', 'EURUSD', 'H1', undefined, {
      emitSignals: false,
    });
    const config = mergeTradeConfig({ spreadPips: 1.5 });
    const trades = simulateTrades(scan.signals, candles, config);
    s.assert('CP-05: Strategy scan produces signals or empty', Array.isArray(scan.signals));
    s.assert('CP-06: Trades array from signals', Array.isArray(trades));
  } finally {
    DataManager.getCandles = originalGet;
  }
}

process.exit(footer(s.finish()));
