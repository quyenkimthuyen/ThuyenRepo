/**
 * Compute Web Worker — runs backtests and Monte Carlo off the main thread.
 */

import { registerBuiltinStrategies } from '../strategies/index.js';
import { runBacktest } from '../optimizer/BacktestRunner.js';
import { runMonteCarlo } from '../optimizer/MonteCarloEngine.js';
import { scoreSignalsBatch } from '../scoring/SignalScoreEngine.js';

registerBuiltinStrategies();

/**
 * @param {MessageEvent} event
 */
self.onmessage = (event) => {
  const { id, task, payload } = event.data;

  try {
    /** @type {unknown} */
    let result;

    switch (task) {
      case 'backtest':
        result = runBacktest(
          payload.strategyId,
          payload.symbol,
          payload.timeframe,
          payload.candles,
          payload.params,
          payload.tradeConfig
        );
        break;

      case 'monteCarlo':
        result = runMonteCarlo(
          payload.trades,
          payload.initialBalance,
          payload.iterations
        );
        break;

      case 'scoreBatch':
        result = scoreSignalsBatch(
          payload.signals,
          payload.candles,
          payload.spreadPips
        );
        break;

      case 'gridChunk': {
        /** @type {unknown[]} */
        const chunkResults = [];
        for (const combo of payload.combos) {
          chunkResults.push({
            params: combo,
            result: runBacktest(
              payload.strategyId,
              payload.symbol,
              payload.timeframe,
              payload.candles,
              combo,
              payload.tradeConfig
            ),
          });
        }
        result = chunkResults;
        break;
      }

      default:
        throw new Error(`Unknown worker task: ${task}`);
    }

    self.postMessage({ id, ok: true, result });
  } catch (err) {
    self.postMessage({
      id,
      ok: false,
      error: err instanceof Error ? err.message : String(err),
    });
  }
};
