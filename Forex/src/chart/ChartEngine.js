/**
 * Lightweight Charts wrapper — candlesticks, EMA overlays, resize handling.
 * @module chart/ChartEngine
 */

import { createChart } from '../../vendor/lightweight-charts.mjs';
import { Config } from '../core/Config.js';
import { toChartCandle, toChartCandles } from './CandleAdapter.js';
import { getChartOptions, getCandlestickColors, getEmaColor, getPriceFormat } from './ChartTheme.js';
import { buildEmaLineData } from './EMAIndicator.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('ChartEngine');

/**
 * Professional candlestick chart powered by Lightweight Charts.
 */
export class ChartEngine {
  /** @type {import('../../vendor/lightweight-charts.mjs').IChartApi|null} */
  #chart = null;

  /** @type {import('../../vendor/lightweight-charts.mjs').ISeriesApi<'Candlestick'>|null} */
  #candleSeries = null;

  /** @type {Map<number, import('../../vendor/lightweight-charts.mjs').ISeriesApi<'Line'>>} */
  #emaSeries = new Map();

  /** @type {HTMLElement|null} */
  #container = null;

  /** @type {ResizeObserver|null} */
  #resizeObserver = null;

  /** @type {boolean} */
  #showEma = true;

  /** @type {import('../../vendor/lightweight-charts.mjs').IPriceLine[]} */
  #priceLines = [];

  /**
   * Create the chart inside a DOM container.
   * @param {HTMLElement} container
   */
  mount(container) {
    this.#container = container;
    this.#chart = createChart(container, {
      ...getChartOptions(),
      width: container.clientWidth,
      height: container.clientHeight,
    });

    this.#candleSeries = this.#chart.addCandlestickSeries({
      ...getCandlestickColors(),
      priceFormat: getPriceFormat(),
    });

    this.#initEmaSeries();
    this.#observeResize();
    log.info('Chart mounted');
  }

  /**
   * Replace all visible candle data (used on load, jump, rewind).
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {{ fit?: boolean }} [options]
   */
  setCandles(candles, options = {}) {
    if (!this.#candleSeries) return;

    this.#candleSeries.setData(toChartCandles(candles));
    this.#updateEma(candles);
    if (options.fit !== false) {
      this.#chart?.timeScale().fitContent();
    }
  }

  /**
   * Draw entry / SL / TP and a marker at the signal candle.
   * @param {import('../utils/chartNavigation.js').ChartSignalHighlight} highlight
   * @param {import('../data/Candle.js').Candle[]} visibleCandles
   */
  setSignalOverlay(highlight, visibleCandles) {
    this.clearSignalOverlay();
    if (!this.#candleSeries || !highlight || visibleCandles.length === 0) return;

    const index = this.#findCandleIndex(visibleCandles, highlight.time);
    const candle = visibleCandles[index];
    if (!candle) return;

    const markerTime = Math.floor(candle.timestamp / 1000);
    const isLong = highlight.direction === 'long';

    this.#candleSeries.setMarkers([
      {
        time: markerTime,
        position: isLong ? 'belowBar' : 'aboveBar',
        color: isLong ? '#22c55e' : '#ef4444',
        shape: isLong ? 'arrowUp' : 'arrowDown',
        text: 'Entry',
      },
    ]);

    const specs = [
      { price: highlight.entry, color: '#3b82f6', title: 'Entry' },
      { price: highlight.sl, color: '#ef4444', title: 'SL' },
      { price: highlight.tp, color: '#22c55e', title: 'TP' },
    ];

    for (const spec of specs) {
      const line = this.#candleSeries.createPriceLine({
        price: spec.price,
        color: spec.color,
        lineWidth: 2,
        lineStyle: 2,
        axisLabelVisible: true,
        title: spec.title,
      });
      this.#priceLines.push(line);
    }

    this.focusOnCandleIndex(index);
  }

  /** Remove signal marker and price lines. */
  clearSignalOverlay() {
    this.#candleSeries?.setMarkers([]);
    for (const line of this.#priceLines) {
      this.#candleSeries?.removePriceLine(line);
    }
    this.#priceLines = [];
  }

  /**
   * Scroll chart so the signal candle is centered with context bars.
   * @param {number} index - Index in currently displayed candle array
   * @param {number} [contextBars=35]
   */
  focusOnCandleIndex(index, contextBars = 35) {
    if (!this.#chart) return;
    const from = Math.max(0, index - contextBars);
    const to = index + 8;
    this.#chart.timeScale().setVisibleLogicalRange({ from, to });
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   * @param {number} timeMs
   * @returns {number}
   */
  #findCandleIndex(candles, timeMs) {
    let index = 0;
    for (let i = 0; i < candles.length; i++) {
      if (candles[i].timestamp <= timeMs) index = i;
      else break;
    }
    return index;
  }

  /**
   * Append or update the latest candle (used during replay forward step).
   * @param {import('../data/Candle.js').Candle} candle
   * @param {import('../data/Candle.js').Candle[]} allVisible - All visible candles for EMA
   */
  updateCandle(candle, allVisible) {
    if (!this.#candleSeries) return;

    this.#candleSeries.update(toChartCandle(candle));
    this.#updateEma(allVisible);
    this.#chart?.timeScale().scrollToRealTime();
  }

  /**
   * Toggle EMA overlay visibility.
   * @param {boolean} visible
   */
  setEmaVisible(visible) {
    this.#showEma = visible;
    for (const series of this.#emaSeries.values()) {
      series.applyOptions({ visible });
    }
  }

  /**
   * Scroll chart to show the latest candle.
   */
  scrollToLatest() {
    this.#chart?.timeScale().scrollToRealTime();
  }

  /**
   * Destroy chart and release resources.
   */
  destroy() {
    this.#resizeObserver?.disconnect();
    this.#resizeObserver = null;
    this.#chart?.remove();
    this.#chart = null;
    this.#candleSeries = null;
    this.#priceLines = [];
    this.#emaSeries.clear();
    log.info('Chart destroyed');
  }

  #initEmaSeries() {
    if (!this.#chart) return;

    for (const period of Config.CHART.EMA_PERIODS) {
      const series = this.#chart.addLineSeries({
        color: getEmaColor(period),
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: true,
        title: `EMA${period}`,
        visible: this.#showEma,
      });
      this.#emaSeries.set(period, series);
    }
  }

  /**
   * @param {import('../data/Candle.js').Candle[]} candles
   */
  #updateEma(candles) {
    if (!this.#showEma) return;

    for (const period of Config.CHART.EMA_PERIODS) {
      const series = this.#emaSeries.get(period);
      if (!series) continue;
      series.setData(buildEmaLineData(candles, period));
    }
  }

  #observeResize() {
    if (!this.#container || !this.#chart) return;

    this.#resizeObserver = new ResizeObserver(() => {
      if (!this.#container || !this.#chart) return;
      this.#chart.applyOptions({
        width: this.#container.clientWidth,
        height: this.#container.clientHeight,
      });
    });

    this.#resizeObserver.observe(this.#container);
  }
}
