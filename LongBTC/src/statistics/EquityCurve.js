/**
 * Equity curve and drawdown calculations.
 * @module statistics/EquityCurve
 */

/**
 * @typedef {Object} EquityPoint
 * @property {number} index
 * @property {number} timestamp
 * @property {number} balance
 * @property {number} drawdown
 * @property {number} drawdownPercent
 */

/**
 * Build equity curve from chronological trades.
 * @param {import('../simulation/TradeSimulator.js').TradeResult[]} trades
 * @param {number} initialBalance
 * @returns {EquityPoint[]}
 */
export function buildEquityCurve(trades, initialBalance) {
  const sorted = [...trades].sort((a, b) => a.exitTime - b.exitTime);
  const curve = [];
  let balance = initialBalance;
  let peak = initialBalance;

  curve.push({
    index: 0,
    timestamp: sorted[0]?.entryTime ?? 0,
    balance,
    drawdown: 0,
    drawdownPercent: 0,
  });

  sorted.forEach((trade, i) => {
    balance += trade.profit;
    peak = Math.max(peak, balance);
    const drawdown = peak - balance;
    const drawdownPercent = peak > 0 ? (drawdown / peak) * 100 : 0;

    curve.push({
      index: i + 1,
      timestamp: trade.exitTime,
      balance,
      drawdown,
      drawdownPercent,
    });
  });

  return curve;
}

/**
 * @param {EquityPoint[]} curve
 * @returns {{ maxDrawdown: number, maxDrawdownPercent: number }}
 */
export function calcMaxDrawdown(curve) {
  let maxDrawdown = 0;
  let maxDrawdownPercent = 0;

  for (const point of curve) {
    if (point.drawdown > maxDrawdown) maxDrawdown = point.drawdown;
    if (point.drawdownPercent > maxDrawdownPercent) maxDrawdownPercent = point.drawdownPercent;
  }

  return { maxDrawdown, maxDrawdownPercent };
}

/**
 * Per-trade return series for Sharpe ratio.
 * @param {import('../simulation/TradeSimulator.js').TradeResult[]} trades
 * @param {number} initialBalance
 * @returns {number[]}
 */
export function tradeReturns(trades, initialBalance) {
  let balance = initialBalance;
  return trades
    .sort((a, b) => a.exitTime - b.exitTime)
    .map((t) => {
      const ret = balance > 0 ? t.profit / balance : 0;
      balance += t.profit;
      return ret;
    });
}

/**
 * Calculate Sharpe ratio from trade returns.
 * @param {number[]} returns
 * @returns {number}
 */
export function calcSharpeRatio(returns) {
  if (returns.length < 2) return 0;

  const mean = returns.reduce((s, r) => s + r, 0) / returns.length;
  const variance = returns.reduce((s, r) => s + (r - mean) ** 2, 0) / (returns.length - 1);
  const std = Math.sqrt(variance);

  return std > 0 ? (mean / std) * Math.sqrt(returns.length) : 0;
}
