/**
 * Win/loss streak calculations.
 * @module statistics/StreakCalculator
 */

/**
 * @typedef {Object} StreakStats
 * @property {number} longestWinStreak
 * @property {number} longestLoseStreak
 * @property {number} currentStreak
 * @property {'win'|'loss'|'none'} currentStreakType
 */

/**
 * Compute longest win and lose streaks from trade outcomes.
 * @param {import('../simulation/TradeSimulator.js').TradeResult[]} trades
 * @returns {StreakStats}
 */
export function calcStreaks(trades) {
  const sorted = [...trades].sort((a, b) => a.exitTime - b.exitTime);

  let longestWin = 0;
  let longestLose = 0;
  let currentWin = 0;
  let currentLose = 0;

  for (const trade of sorted) {
    if (trade.outcome === 'win') {
      currentWin++;
      currentLose = 0;
      longestWin = Math.max(longestWin, currentWin);
    } else if (trade.outcome === 'loss') {
      currentLose++;
      currentWin = 0;
      longestLose = Math.max(longestLose, currentLose);
    } else {
      currentWin = 0;
      currentLose = 0;
    }
  }

  const last = sorted[sorted.length - 1];
  let currentStreakType = 'none';
  let currentStreak = 0;
  if (last?.outcome === 'win') {
    currentStreakType = 'win';
    currentStreak = currentWin;
  } else if (last?.outcome === 'loss') {
    currentStreakType = 'loss';
    currentStreak = currentLose;
  }

  return {
    longestWinStreak: longestWin,
    longestLoseStreak: longestLose,
    currentStreak,
    currentStreakType,
  };
}
