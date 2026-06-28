/**
 * Comprehensive performance statistics per idea.txt §STATISTICS.
 * @module statistics/StatisticsCalculator
 */

import { priceToPips } from '../utils/pip.js';
import { buildEquityCurve, calcMaxDrawdown, tradeReturns, calcSharpeRatio } from './EquityCurve.js';
import { calcStreaks } from './StreakCalculator.js';

/**
 * @typedef {import('../simulation/TradeSimulator.js').TradeResult} TradeResult
 */

/**
 * @typedef {Object} PerformanceStats
 * @property {number} totalTrades
 * @property {number} wins
 * @property {number} losses
 * @property {number} breakeven
 * @property {number} winRate
 * @property {number} averageWin
 * @property {number} averageLoss
 * @property {number} expectancy
 * @property {number} expectancyR
 * @property {number} profitFactor
 * @property {number} netProfit
 * @property {number} grossProfit
 * @property {number} grossLoss
 * @property {number} maxDrawdown
 * @property {number} maxDrawdownPercent
 * @property {number} recoveryFactor
 * @property {number} sharpeRatio
 * @property {number} longestWinStreak
 * @property {number} longestLoseStreak
 * @property {number} averageTradeDuration
 * @property {number} averageRR
 * @property {number} averageSLPips
 * @property {number} averageTPPips
 * @property {number} initialBalance
 * @property {number} finalBalance
 * @property {import('./EquityCurve.js').EquityPoint[]} equityCurve
 */

/**
 * Compute full performance statistics from trade results.
 * @param {TradeResult[]} trades
 * @param {number} [initialBalance=10000]
 * @returns {PerformanceStats}
 */
export function computeStatistics(trades, initialBalance = 10000) {
  if (trades.length === 0) {
    return emptyStats(initialBalance);
  }

  const wins = trades.filter((t) => t.outcome === 'win');
  const losses = trades.filter((t) => t.outcome === 'loss');
  const breakeven = trades.filter((t) => t.outcome === 'breakeven');

  const grossProfit = wins.reduce((s, t) => s + t.profit, 0);
  const grossLoss = Math.abs(losses.reduce((s, t) => s + t.profit, 0));
  const netProfit = trades.reduce((s, t) => s + t.profit, 0);

  const averageWin = wins.length ? grossProfit / wins.length : 0;
  const averageLoss = losses.length ? grossLoss / losses.length : 0;
  const winRate = (wins.length / trades.length) * 100;
  const lossRate = (losses.length / trades.length) * 100;

  const expectancy = (winRate / 100) * averageWin - (lossRate / 100) * averageLoss;

  const equityCurve = buildEquityCurve(trades, initialBalance);
  const { maxDrawdown, maxDrawdownPercent } = calcMaxDrawdown(equityCurve);
  const recoveryFactor = maxDrawdown > 0 ? netProfit / maxDrawdown : netProfit > 0 ? Infinity : 0;
  const sharpeRatio = calcSharpeRatio(tradeReturns(trades, initialBalance));
  const streaks = calcStreaks(trades);

  const rrValues = trades.map((t) => calcTradeRR(t));
  const slPips = trades.map((t) => priceToPips(Math.abs(t.entryPrice - t.sl), t.symbol));
  const tpPips = trades.map((t) => priceToPips(Math.abs(t.tp - t.entryPrice), t.symbol));

  const expectancyR = trades.length
    ? trades.reduce((s, t) => {
      const riskPips = priceToPips(Math.abs(t.entryPrice - t.sl), t.symbol);
      return s + (riskPips > 0 ? t.pips / riskPips : 0);
    }, 0) / trades.length
    : 0;

  return {
    totalTrades: trades.length,
    wins: wins.length,
    losses: losses.length,
    breakeven: breakeven.length,
    winRate,
    averageWin,
    averageLoss,
    expectancy,
    expectancyR,
    profitFactor: grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : 0,
    netProfit,
    grossProfit,
    grossLoss,
    maxDrawdown,
    maxDrawdownPercent,
    recoveryFactor,
    sharpeRatio,
    longestWinStreak: streaks.longestWinStreak,
    longestLoseStreak: streaks.longestLoseStreak,
    averageTradeDuration: average(trades.map((t) => t.durationBars)),
    averageRR: average(rrValues),
    averageSLPips: average(slPips),
    averageTPPips: average(tpPips),
    initialBalance,
    finalBalance: initialBalance + netProfit,
    equityCurve,
  };
}

/**
 * Planned risk-reward ratio for a trade.
 * @param {TradeResult} trade
 * @returns {number}
 */
function calcTradeRR(trade) {
  const risk = Math.abs(trade.entryPrice - trade.sl);
  const reward = Math.abs(trade.tp - trade.entryPrice);
  return risk > 0 ? reward / risk : 0;
}

/**
 * @param {number[]} values
 * @returns {number}
 */
function average(values) {
  if (values.length === 0) return 0;
  return values.reduce((s, v) => s + v, 0) / values.length;
}

/**
 * @param {number} initialBalance
 * @returns {PerformanceStats}
 */
function emptyStats(initialBalance) {
  return {
    totalTrades: 0,
    wins: 0,
    losses: 0,
    breakeven: 0,
    winRate: 0,
    averageWin: 0,
    averageLoss: 0,
    expectancy: 0,
    expectancyR: 0,
    profitFactor: 0,
    netProfit: 0,
    grossProfit: 0,
    grossLoss: 0,
    maxDrawdown: 0,
    maxDrawdownPercent: 0,
    recoveryFactor: 0,
    sharpeRatio: 0,
    longestWinStreak: 0,
    longestLoseStreak: 0,
    averageTradeDuration: 0,
    averageRR: 0,
    averageSLPips: 0,
    averageTPPips: 0,
    initialBalance,
    finalBalance: initialBalance,
    equityCurve: [{ index: 0, timestamp: 0, balance: initialBalance, drawdown: 0, drawdownPercent: 0 }],
  };
}
