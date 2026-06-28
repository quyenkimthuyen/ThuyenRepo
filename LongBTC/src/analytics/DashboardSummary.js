/**
 * Dashboard summary cards derived from simulation and statistics.
 * @module analytics/DashboardSummary
 */

/** @typedef {import('../statistics/StatisticsCalculator.js').PerformanceStats} PerformanceStats */

/**
 * @typedef {Object} DashboardCard
 * @property {string} id
 * @property {string} label
 * @property {string} value
 * @property {string} [hint]
 * @property {'positive'|'negative'|'neutral'} tone
 */

/**
 * Build dashboard summary cards for the reports view.
 * @param {Object} params
 * @param {string} params.strategyId
 * @param {string} params.symbol
 * @param {string} params.timeframe
 * @param {PerformanceStats} params.stats
 * @param {number} [params.signalCount]
 * @param {number} [params.durationMs]
 * @returns {DashboardCard[]}
 */
export function buildDashboardCards({
  strategyId,
  symbol,
  timeframe,
  stats,
  signalCount = 0,
  durationMs = 0,
}) {
  const pf = stats.profitFactor === Infinity ? '∞' : stats.profitFactor.toFixed(2);

  return [
    {
      id: 'netProfit',
      label: 'Net Profit',
      value: `$${stats.netProfit.toFixed(2)}`,
      tone: stats.netProfit > 0 ? 'positive' : stats.netProfit < 0 ? 'negative' : 'neutral',
    },
    {
      id: 'winRate',
      label: 'Win Rate',
      value: `${stats.winRate.toFixed(1)}%`,
      hint: `${stats.wins}W / ${stats.losses}L`,
      tone: stats.winRate >= 50 ? 'positive' : 'neutral',
    },
    {
      id: 'profitFactor',
      label: 'Profit Factor',
      value: pf,
      tone: stats.profitFactor >= 1 ? 'positive' : 'negative',
    },
    {
      id: 'expectancy',
      label: 'Expectancy',
      value: `$${stats.expectancy.toFixed(2)}`,
      tone: stats.expectancy > 0 ? 'positive' : stats.expectancy < 0 ? 'negative' : 'neutral',
    },
    {
      id: 'maxDrawdown',
      label: 'Max Drawdown',
      value: `$${stats.maxDrawdown.toFixed(2)}`,
      hint: `${stats.maxDrawdownPercent.toFixed(1)}%`,
      tone: 'negative',
    },
    {
      id: 'totalTrades',
      label: 'Total Trades',
      value: String(stats.totalTrades),
      hint: signalCount ? `${signalCount} signals` : undefined,
      tone: 'neutral',
    },
    {
      id: 'setup',
      label: 'Setup',
      value: strategyId,
      hint: `${symbol} · ${timeframe}`,
      tone: 'neutral',
    },
    {
      id: 'runtime',
      label: 'Sim Duration',
      value: durationMs ? `${durationMs} ms` : '—',
      tone: 'neutral',
    },
  ];
}
