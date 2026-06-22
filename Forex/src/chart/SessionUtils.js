/**
 * Forex trading session detection (UTC-based).
 * @module chart/SessionUtils
 */

/** @typedef {'Tokyo'|'London'|'New York'|'Sydney'|'Off-hours'} Session */

/**
 * Determine the active forex session for a UTC timestamp.
 * Sessions overlap — returns the most liquid session at that hour.
 * @param {number} timestamp - Epoch milliseconds
 * @returns {Session}
 */
export function getSession(timestamp) {
  const hour = new Date(timestamp).getUTCHours();

  if (hour >= 12 && hour < 21) return 'New York';
  if (hour >= 7 && hour < 16) return 'London';
  if (hour >= 0 && hour < 9) return 'Tokyo';
  if (hour >= 21 || hour < 0) return 'Sydney';

  return 'Off-hours';
}

/**
 * Session display colors for UI badges.
 * @param {Session} session
 * @returns {string}
 */
export function getSessionColor(session) {
  const colors = {
    Tokyo: '#a855f7',
    London: '#3b82f6',
    'New York': '#22c55e',
    Sydney: '#f59e0b',
    'Off-hours': '#5a6a82',
  };
  return colors[session] ?? '#5a6a82';
}
