/**
 * Replay engine tests — no-lookahead candle replay.
 * Run: node tests/replay/ReplayTests.js
 */

import { createSuite, header, footer, candle } from '../harness.js';
import { ReplayEngine } from '../../src/replay/ReplayEngine.js';
import { Config } from '../../src/core/Config.js';

const s = createSuite('Replay Engine');
header('Replay Engine');

const candles = Array.from({ length: 100 }, (_, i) => candle(i, 1.08, 1.09, 1.07, 1.085));

{
  const replay = new ReplayEngine();
  replay.load(candles);
  const state = replay.getState();
  s.assert('RP-01: Live mode on load', state.mode === 'live' && state.total === 100);
  s.assert('RP-02: Live shows all', replay.getVisibleCandles().length === 100);
  replay.destroy();
}

{
  const replay = new ReplayEngine();
  replay.load(candles);
  replay.resetReplay();
  const state = replay.getState();
  s.assert('RP-03: Replay mode after reset', state.mode === 'replay');
  s.assert('RP-04: Lookback bars', state.index === Config.REPLAY.LOOKBACK_BARS);
  s.assert('RP-05: Visible subset', replay.getVisibleCandles().length === state.index + 1);
  replay.destroy();
}

{
  const replay = new ReplayEngine();
  replay.load(candles);
  replay.resetReplay();
  const before = replay.getState().index;
  replay.next();
  s.assert('RP-06: Next advances', replay.getState().index === before + 1);
  replay.prev();
  s.assert('RP-07: Prev rewinds', replay.getState().index === before);
  replay.destroy();
}

{
  const replay = new ReplayEngine();
  replay.load(candles);
  replay.jumpToDate(candles[50].timestamp);
  s.assert('RP-08: Jump to date', replay.getState().index === 50);
  s.assert('RP-09: Replay after jump', replay.getState().mode === 'replay');
  replay.destroy();
}

{
  const replay = new ReplayEngine();
  replay.load(candles);
  const between = candles[50].timestamp + 2000000;
  replay.jumpToDate(between);
  s.assert('RP-08b: Jump nearest between bars', replay.getState().index === 51);
  replay.destroy();
}

{
  const replay = new ReplayEngine();
  replay.load(candles);
  replay.jumpToDate(candles[99].timestamp + 999999);
  s.assert('RP-08c: Jump after last candle', replay.getState().index === 99);
  replay.destroy();
}

{
  const replay = new ReplayEngine();
  replay.load(candles);
  replay.resetReplay();
  while (replay.next()) { /* advance */ }
  s.assert('RP-10: End of replay', replay.getState().index === candles.length - 1);
  replay.goLive();
  s.assert('RP-11: Go live', replay.getState().mode === 'live');
  replay.destroy();
}

{
  const replay = new ReplayEngine();
  replay.load([]);
  s.assert('RP-12: Empty load', replay.getVisibleCandles().length === 0);
  replay.destroy();
}

process.exit(footer(s.finish()));
