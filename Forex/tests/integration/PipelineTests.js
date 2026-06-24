/**
 * End-to-end pipeline integration tests.
 * Strategy → Simulation → Statistics → Scoring → Report → Optimizer
 * Run: node tests/integration/PipelineTests.js
 */

import { createSuite, header, footer } from '../harness.js';
import { registerBuiltinStrategies } from '../../src/strategies/index.js';
import { registry } from '../../src/plugin/PluginRegistry.js';
import { generateSample } from '../../src/data/SampleDataGenerator.js';
import { runBacktest } from '../../src/optimizer/BacktestRunner.js';
import { getDefaultTradeConfig } from '../../src/simulation/TradeConfig.js';
import { simulateTrades } from '../../src/simulation/TradeSimulator.js';
import { computeStatistics } from '../../src/statistics/StatisticsCalculator.js';
import { scoreSignalsBatch } from '../../src/scoring/SignalScoreEngine.js';
import { buildDashboardCards } from '../../src/analytics/DashboardSummary.js';
import { computeHeatmap } from '../../src/analytics/HeatmapCalculator.js';
import { runGridSearch } from '../../src/optimizer/GridSearchEngine.js';
import { runMonteCarlo } from '../../src/optimizer/MonteCarloEngine.js';
import { createContext } from '../../src/strategy/StrategyContext.js';
import { BreakRetestStrategy } from '../../src/strategies/BreakRetestStrategy.js';

const s = createSuite('Integration Pipeline');
header('Integration Pipeline');

registerBuiltinStrategies();

const candles = generateSample('EURUSD', 'H1', 500);
const tradeConfig = getDefaultTradeConfig();
const defaultParams = new BreakRetestStrategy().getParameterSchema().reduce((p, d) => {
  p[d.key] = d.default;
  return p;
}, {});

{
  s.assert('INT-01: Registry has 5 strategies', registry.size === 5);
  s.assert('INT-02: break-retest registered', registry.has('break-retest'));
  s.assert('INT-02b: inside-bar-breakout registered', registry.has('inside-bar-breakout'));
  s.assert('INT-02c: pin-bar-rejection registered', registry.has('pin-bar-rejection'));
}

{
  const bt = runBacktest('break-retest', 'EURUSD', 'H1', candles, defaultParams, tradeConfig);
  s.assert('INT-03: Backtest runs', bt.barsScanned > 0);
  s.assert('INT-04: Backtest has stats', typeof bt.stats.finalBalance === 'number');
  s.assert('INT-05: Backtest duration', bt.durationMs >= 0);
}

{
  const strategy = new BreakRetestStrategy();
  strategy.initialize(defaultParams);
  strategy.setRunContext({ symbol: 'EURUSD', timeframe: 'H1' });
  const signals = [];
  for (let i = strategy.getWarmupBars(); i < candles.length; i++) {
    strategy.calculate(candles, i);
    const ctx = createContext('EURUSD', 'H1', candles, i, defaultParams);
    const sig = strategy.generateSignal(ctx);
    if (sig && strategy.validate(sig)) signals.push(sig);
  }
  const trades = simulateTrades(signals, candles, tradeConfig);
  const stats = computeStatistics(trades, tradeConfig.initialBalance);
  s.assert('INT-06: Manual pipeline trades array', Array.isArray(trades));
  s.assert('INT-07: Statistics from trades', stats.totalTrades === trades.length);
}

{
  const bt = runBacktest('liquidity-grab', 'EURUSD', 'H1', candles, {}, tradeConfig);
  s.assert('INT-08: Liquidity grab backtest', bt.barsScanned > 0);
}

{
  const bt = runBacktest('ema-pullback', 'EURUSD', 'H1', candles, {}, tradeConfig);
  s.assert('INT-09: EMA pullback backtest', bt.barsScanned > 0);
}

{
  const bt = runBacktest('inside-bar-breakout', 'EURUSD', 'H1', candles, {}, tradeConfig);
  s.assert('INT-09b: Inside bar backtest', bt.barsScanned > 0);
}

{
  const bt = runBacktest('pin-bar-rejection', 'EURUSD', 'H1', candles, {}, tradeConfig);
  s.assert('INT-09c: Pin bar backtest', bt.barsScanned > 0);
}

{
  const bt = runBacktest('break-retest', 'EURUSD', 'H1', candles, defaultParams, tradeConfig);
  const scored = scoreSignalsBatch(bt.signals, candles, tradeConfig.spreadPips);
  s.assert('INT-10: Signal scoring', scored.length === bt.signals.length);
  if (scored.length > 0) {
    s.assert('INT-11: Score breakdown', typeof scored[0].scoreBreakdown?.score === 'number');
  } else {
    s.assert('INT-11: Score breakdown (no signals ok)', true);
  }
}

{
  const bt = runBacktest('break-retest', 'EURUSD', 'H1', candles, defaultParams, tradeConfig);
  const dashboard = buildDashboardCards({
    strategyId: 'break-retest',
    symbol: 'EURUSD',
    timeframe: 'H1',
    stats: bt.stats,
    signalCount: bt.signals.length,
  });
  s.assert('INT-12: Dashboard cards', dashboard.length >= 4);
}

{
  const bt = runBacktest('break-retest', 'EURUSD', 'H1', candles, defaultParams, tradeConfig);
  if (bt.trades.length > 0) {
    const heatmap = computeHeatmap(bt.trades, 'hour');
    s.assert('INT-13: Heatmap by hour', heatmap.cells.length > 0);
  } else {
    s.assert('INT-13: Heatmap (no trades ok)', true);
  }
}

{
  const grid = await runGridSearch({
    strategyId: 'break-retest',
    symbol: 'EURUSD',
    timeframe: 'H1',
    candles,
    tradeConfig,
    paramGrid: { breakoutPips: [5, 8], rr: [2] },
    maxCombinations: 10,
  });
  s.assert('INT-14: Grid search', grid.entries.length > 0);
  s.assert('INT-15: Grid best result', grid.best !== null);
}

{
  const bt = runBacktest('break-retest', 'EURUSD', 'H1', candles, defaultParams, tradeConfig);
  if (bt.trades.length > 0) {
    const mc = runMonteCarlo(bt.trades, tradeConfig.initialBalance, 100);
    s.assert('INT-16: Monte Carlo', mc.iterations === 100);
  } else {
    s.assert('INT-16: Monte Carlo (no trades ok)', true);
  }
}

{
  for (const tf of ['H1', 'H4', 'D1', 'W']) {
    const tfCandles = generateSample('EURUSD', tf, 200);
    const bt = runBacktest('break-retest', 'EURUSD', tf, tfCandles, defaultParams, tradeConfig);
    s.assert(`INT-TF-${tf}: backtest on ${tf}`, bt.barsScanned > 0);
  }
}

process.exit(footer(s.finish()));
