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
   */
  setCandles(candles) {
    if (!this.#candleSeries) return;

    this.#candleSeries.setData(toChartCandles(candles));
    this.#updateEma(candles);
    this.#chart?.timeScale().fitContent();
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
