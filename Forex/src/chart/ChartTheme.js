/**
 * Chart color theme aligned with the application design system.
 * @module chart/ChartTheme
 */

import { Config } from '../core/Config.js';

/**
 * Lightweight Charts theme options for dark trading UI.
 * @returns {Record<string, unknown>}
 */
export function getChartOptions() {
  return {
    layout: {
      background: { color: '#0f1419' },
      textColor: '#8b9cb3',
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 11,
    },
    grid: {
      vertLines: { color: '#1a2230' },
      horzLines: { color: '#1a2230' },
    },
    crosshair: {
      mode: 0,
      vertLine: {
        color: '#3b82f6',
        width: 1,
        style: 2,
        labelBackgroundColor: '#3b82f6',
      },
      horzLine: {
        color: '#3b82f6',
        width: 1,
        style: 2,
        labelBackgroundColor: '#3b82f6',
      },
    },
    rightPriceScale: {
      borderColor: '#2a3548',
      scaleMargins: { ...Config.CHART.PRICE_SCALE_MARGINS },
      minimumWidth: Config.CHART.PRICE_SCALE_MIN_WIDTH,
    },
    timeScale: {
      borderColor: '#2a3548',
      timeVisible: true,
      secondsVisible: false,
      rightOffset: Config.CHART.TIME_RIGHT_OFFSET,
      barSpacing: 8,
      minBarSpacing: 2,
    },
    handleScroll: { mouseWheel: true, pressedMouseMove: true },
    handleScale: { mouseWheel: true, pinch: true },
  };
}

/**
 * Candlestick series colors.
 * @returns {Record<string, string>}
 */
export function getCandlestickColors() {
  return {
    upColor: '#22c55e',
    downColor: '#ef4444',
    borderUpColor: '#22c55e',
    borderDownColor: '#ef4444',
    wickUpColor: '#22c55e',
    wickDownColor: '#ef4444',
  };
}

/**
 * EMA line series colors by period.
 * @param {number} period
 * @returns {string}
 */
export function getEmaColor(period) {
  const colors = { 20: '#3b82f6', 50: '#f59e0b', 100: '#a855f7', 200: '#ec4899' };
  return colors[period] ?? '#06b6d4';
}

/**
 * Price format options for forex pairs.
 * @returns {Record<string, unknown>}
 */
export function getPriceFormat() {
  return {
    type: 'price',
    precision: Config.CHART.PRICE_PRECISION,
    minMove: Config.CHART.MIN_MOVE,
  };
}
