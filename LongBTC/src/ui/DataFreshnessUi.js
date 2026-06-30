/**
 * Data freshness banner for analysis views.
 * @module ui/DataFreshnessUi
 */

import { el } from '../utils/dom.js';
import { describeDataFreshness } from '../analysis/DataFreshness.js';

/**
 * @param {number} lastTimestampMs
 * @param {string} timeframe
 * @param {string} [symbol='BTCUSD']
 * @returns {HTMLElement}
 */
export function renderDataFreshnessBanner(lastTimestampMs, timeframe, symbol = 'BTCUSD') {
  const info = describeDataFreshness(lastTimestampMs, timeframe);
  const levelClass = `data-freshness--${info.level}`;

  return el('div', {
    class: `data-freshness-banner ${levelClass}`,
    title: `N\u1ebfn cu\u1ed1i: ${new Date(lastTimestampMs).toISOString()}`,
  }, [
    el('span', { class: 'data-freshness-icon' }, [info.warn ? '\u26a0\ufe0f' : '\u2713']),
    el('span', { class: 'data-freshness-text' }, [
      `${symbol} ${timeframe}: d\u1eef li\u1ec7u c\u0169 ${info.labelVi}`,
      info.warn ? ' \u2014 n\u00ean b\u1ea5m C\u1eadp nh\u1eadt gi\u00e1 m\u1edbi' : '',
    ]),
  ]);
}

/**
 * Compact chip for toolbars / table cells.
 * @param {number} lastTimestampMs
 * @param {string} timeframe
 * @returns {string}
 */
export function dataFreshnessChipText(lastTimestampMs, timeframe) {
  const info = describeDataFreshness(lastTimestampMs, timeframe);
  const prefix = info.level === 'fresh' ? '' : '\u26a0 ';
  return `${prefix}${info.labelVi}`;
}
