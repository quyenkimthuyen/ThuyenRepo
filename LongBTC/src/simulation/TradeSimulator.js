/**
 * Bar-by-bar trade simulator — SL, TP, trailing, BE, partial close.
 * @module simulation/TradeSimulator
 */

import { createPosition, applyBreakEven, updateTrailingStop, recordPartialClose } from './Position.js';
import {
  marketEntryFill,
  marketExitFill,
  roundTripCommission,
  calcPips,
  pipsToMoney,
  normalizePrice,
} from './FillModel.js';

/**
 * @typedef {import('./TradeConfig.js').TradeConfig} TradeConfig
 * @typedef {import('../strategy/Signal.js').Signal} Signal
 * @typedef {import('../data/Candle.js').Candle} Candle
 */

/**
 * @typedef {Object} TradeResult
 * @property {string} id
 * @property {string} signalId
 * @property {string} strategyId
 * @property {string} symbol
 * @property {string} timeframe
 * @property {'long'|'short'} direction
 * @property {'win'|'loss'|'breakeven'|'open'|'expired'} outcome
 * @property {string} exitReason
 * @property {number} entryPrice
 * @property {number} exitPrice
 * @property {number} sl
 * @property {number} tp
 * @property {number} entryTime
 * @property {number} exitTime
 * @property {number} entryBar
 * @property {number} exitBar
 * @property {number} pips
 * @property {number} profit
 * @property {number} commission
 * @property {number} durationBars
 * @property {import('./Position.js').PartialClose[]} partialCloses
 * @property {string} reason
 */

let tradeIdCounter = 0;

/**
 * Find candle index matching signal timestamp.
 * @param {Candle[]} candles
 * @param {number} timestamp
 * @returns {number}
 */
export function findSignalBarIndex(candles, timestamp) {
  for (let i = 0; i < candles.length; i++) {
    if (candles[i].timestamp === timestamp) return i;
    if (candles[i].timestamp > timestamp) return Math.max(0, i - 1);
  }
  return candles.length - 1;
}

/**
 * Simulate a single signal through subsequent candles.
 * @param {Signal} signal
 * @param {Candle[]} candles
 * @param {TradeConfig} config
 * @returns {TradeResult|null}
 */
export function simulateTrade(signal, candles, config) {
  const barIndex = findSignalBarIndex(candles, signal.time);
  if (barIndex < 0 || barIndex >= candles.length - 1) return null;

  const entry = resolveEntry(signal, candles, barIndex, config);
  if (!entry) return null;

  const pos = createPosition({
    signalId: signal.id,
    strategyId: signal.strategyId,
    symbol: signal.pair,
    direction: signal.direction,
    entryPrice: entry.price,
    sl: signal.sl,
    tp: signal.tp,
    entryBar: entry.barIndex,
    entryTime: entry.timestamp,
  });

  const commission = roundTripCommission(config.lotSize, config.commissionPerLot);

  for (let i = entry.barIndex + 1; i < candles.length; i++) {
    const candle = candles[i];
    const barsHeld = i - entry.barIndex;

    if (barsHeld > config.maxBarsInTrade) {
      return closeTrade(pos, signal, candle, i, 'expired', config, commission);
    }

    updateTrailingStop(pos, candle, config.trailingStopPips, signal.pair);
    maybeBreakEven(pos, candle, config);
    maybePartialClose(pos, signal, candle, i, config);

    const exit = checkExit(pos, candle);
    if (exit) {
      return closeTrade(pos, signal, candle, i, exit, config, commission);
    }
  }

  const last = candles[candles.length - 1];
  return closeTrade(pos, signal, last, candles.length - 1, 'expired', config, commission);
}

/**
 * @param {Signal} signal
 * @param {Candle[]} candles
 * @param {number} barIndex
 * @param {TradeConfig} config
 * @returns {{ price: number, barIndex: number, timestamp: number }|null}
 */
function resolveEntry(signal, candles, barIndex, config) {
  if (config.orderType === 'market') {
    const candle = candles[barIndex];
    const price = marketEntryFill(
      signal.entry,
      signal.direction,
      signal.pair,
      config.spreadPips,
      config.slippagePips
    );
    return { price: normalizePrice(price, signal.pair), barIndex, timestamp: candle.timestamp };
  }

  for (let i = barIndex; i < Math.min(candles.length, barIndex + config.pendingMaxBars); i++) {
    const candle = candles[i];
    const touched = signal.direction === 'long'
      ? candle.low <= signal.entry
      : candle.high >= signal.entry;

    if (touched) {
      const price = marketEntryFill(
        signal.entry,
        signal.direction,
        signal.pair,
        config.spreadPips,
        config.slippagePips
      );
      return { price: normalizePrice(price, signal.pair), barIndex: i, timestamp: candle.timestamp };
    }
  }

  return null;
}

/**
 * @param {import('./Position.js').OpenPosition} pos
 * @param {Candle} candle
 * @param {TradeConfig} config
 */
function maybeBreakEven(pos, candle, config) {
  if (config.breakEvenAtR <= 0 || pos.breakEvenApplied) return;
  const target = pos.direction === 'long'
    ? pos.entryPrice + config.breakEvenAtR * pos.riskDistance
    : pos.entryPrice - config.breakEvenAtR * pos.riskDistance;

  const hit = pos.direction === 'long' ? candle.high >= target : candle.low <= target;
  if (hit) applyBreakEven(pos);
}

/**
 * @param {import('./Position.js').OpenPosition} pos
 * @param {Signal} signal
 * @param {Candle} candle
 * @param {number} barIndex
 * @param {TradeConfig} config
 */
function maybePartialClose(pos, signal, candle, barIndex, config) {
  if (config.partialCloseAtR <= 0 || pos.partialCloseDone) return;

  const target = pos.direction === 'long'
    ? pos.entryPrice + config.partialCloseAtR * pos.riskDistance
    : pos.entryPrice - config.partialCloseAtR * pos.riskDistance;

  const hit = pos.direction === 'long' ? candle.high >= target : candle.low <= target;
  if (!hit) return;

  const exitPrice = marketExitFill(target, pos.direction, signal.pair, config.spreadPips, config.slippagePips);
  const pips = calcPips(pos.entryPrice, exitPrice, pos.direction, signal.pair) * (config.partialClosePercent / 100);
  const profit = pipsToMoney(pips, signal.pair, config.lotSize);

  recordPartialClose(pos, {
    barIndex,
    timestamp: candle.timestamp,
    price: normalizePrice(exitPrice, signal.pair),
    percent: config.partialClosePercent,
    pips,
    profit,
  }, config.partialClosePercent);
}

/**
 * @param {import('./Position.js').OpenPosition} pos
 * @param {Candle} candle
 * @returns {string|null}
 */
function checkExit(pos, candle) {
  if (pos.direction === 'long') {
    const slHit = candle.low <= pos.sl;
    const tpHit = candle.high >= pos.tp;
    if (slHit && tpHit) return candle.open >= pos.entryPrice ? 'sl' : 'tp';
    if (slHit) return pos.breakEvenApplied && pos.sl === pos.entryPrice ? 'be' : 'sl';
    if (tpHit) return 'tp';
  } else {
    const slHit = candle.high >= pos.sl;
    const tpHit = candle.low <= pos.tp;
    if (slHit && tpHit) return candle.open <= pos.entryPrice ? 'sl' : 'tp';
    if (slHit) return pos.breakEvenApplied && pos.sl === pos.entryPrice ? 'be' : 'sl';
    if (tpHit) return 'tp';
  }
  return null;
}

/**
 * @param {import('./Position.js').OpenPosition} pos
 * @param {Signal} signal
 * @param {Candle} candle
 * @param {number} barIndex
 * @param {string} reason
 * @param {TradeConfig} config
 * @param {number} commission
 * @returns {TradeResult}
 */
function closeTrade(pos, signal, candle, barIndex, reason, config, commission) {
  const rawExit = reason === 'tp' ? signal.tp
    : reason === 'sl' || reason === 'be' ? pos.sl
      : candle.close;

  const exitPrice = normalizePrice(
    marketExitFill(rawExit, pos.direction, signal.pair, config.spreadPips, config.slippagePips),
    signal.pair
  );

  const remainingPips = calcPips(pos.entryPrice, exitPrice, pos.direction, signal.pair) * pos.sizeRemaining;
  const remainingProfit = pipsToMoney(remainingPips, signal.pair, config.lotSize);
  const grossProfit = pos.accumulatedProfit + remainingProfit;
  const netProfit = grossProfit - commission;
  const totalPips = calcPips(pos.entryPrice, exitPrice, pos.direction, signal.pair);

  let outcome = 'loss';
  if (netProfit > 0) outcome = 'win';
  else if (Math.abs(netProfit) < 0.01) outcome = 'breakeven';

  tradeIdCounter += 1;

  return {
    id: `trade_${tradeIdCounter}`,
    signalId: signal.id,
    strategyId: signal.strategyId,
    symbol: signal.pair,
    timeframe: signal.timeframe,
    direction: signal.direction,
    outcome,
    exitReason: reason,
    entryPrice: pos.entryPrice,
    exitPrice,
    sl: pos.initialSl,
    tp: signal.tp,
    entryTime: pos.entryTime,
    exitTime: candle.timestamp,
    entryBar: pos.entryBar,
    exitBar: barIndex,
    pips: totalPips,
    profit: netProfit,
    commission,
    durationBars: barIndex - pos.entryBar,
    partialCloses: [...pos.partialCloses],
    reason: signal.reason,
  };
}

/**
 * Simulate multiple signals (non-overlapping — one position at a time).
 * @param {Signal[]} signals
 * @param {Candle[]} candles
 * @param {TradeConfig} config
 * @returns {TradeResult[]}
 */
export function simulateTrades(signals, candles, config) {
  const sorted = [...signals].sort((a, b) => a.time - b.time);
  const results = [];
  let nextAvailableBar = 0;

  for (const signal of sorted) {
    const barIndex = findSignalBarIndex(candles, signal.time);
    if (barIndex < nextAvailableBar) continue;

    const result = simulateTrade(signal, candles, config);
    if (result) {
      results.push(result);
      nextAvailableBar = result.exitBar + 1;
    }
  }

  return results;
}

/**
 * Quick summary stats from trade results.
 * @param {TradeResult[]} trades
 * @param {number} initialBalance
 * @returns {Object}
 */
export function summarizeTrades(trades, initialBalance) {
  const wins = trades.filter((t) => t.outcome === 'win').length;
  const losses = trades.filter((t) => t.outcome === 'loss').length;
  const netProfit = trades.reduce((s, t) => s + t.profit, 0);
  const grossProfit = trades.filter((t) => t.profit > 0).reduce((s, t) => s + t.profit, 0);
  const grossLoss = Math.abs(trades.filter((t) => t.profit < 0).reduce((s, t) => s + t.profit, 0));

  return {
    totalTrades: trades.length,
    wins,
    losses,
    winRate: trades.length ? (wins / trades.length) * 100 : 0,
    netProfit,
    grossProfit,
    grossLoss,
    profitFactor: grossLoss > 0 ? grossProfit / grossLoss : grossProfit,
    finalBalance: initialBalance + netProfit,
    avgDuration: trades.length
      ? trades.reduce((s, t) => s + t.durationBars, 0) / trades.length
      : 0,
  };
}
