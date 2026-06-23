/**
 * Lightweight Charts wrapper — candlesticks, EMA overlays, resize handling.
 * @module chart/ChartEngine
 */

import { createChart } from '../../vendor/lightweight-charts.mjs';
import { Config } from '../core/Config.js';
import { toChartCandle, toChartCandles } from './CandleAdapter.js';
import { getChartOptions, getCandlestickColors, getEmaColor, getPriceFormat } from './ChartTheme.js';
import { buildEmaLineData } from './EMAIndicator.js';
import {
  MARKER_ROLE_COLORS,
  styleForSetupLevel,
  TRADE_LEVEL_STYLES,
} from './SetupAnnotationStyles.js';
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

  /** @type {'normal'|'signal'} */
  #paddingMode = 'normal';

  /** @type {import('../utils/chartNavigation.js').ChartSignalHighlight|null} */
  #activeHighlight = null;

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
    if (this.#activeHighlight) {
      this.refreshSignalScale();
    }
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

    const markers = [];

    for (const level of highlight.setup?.levels ?? []) {
      const style = styleForSetupLevel(level.kind);
      this.#priceLines.push(this.#candleSeries.createPriceLine({
        price: level.price,
        color: style.color,
        lineWidth: 2,
        lineStyle: style.lineStyle,
        axisLabelVisible: true,
        title: level.label,
      }));
      if (level.priceTo != null && level.priceTo !== level.price) {
        this.#priceLines.push(this.#candleSeries.createPriceLine({
          price: level.priceTo,
          color: style.color,
          lineWidth: 1,
          lineStyle: style.lineStyle,
          axisLabelVisible: false,
          title: '',
        }));
      }
    }

    for (const spec of [
      { key: 'entry', price: highlight.entry },
      { key: 'sl', price: highlight.sl },
      { key: 'tp', price: highlight.tp },
    ]) {
      const style = TRADE_LEVEL_STYLES[spec.key];
      this.#priceLines.push(this.#candleSeries.createPriceLine({
        price: spec.price,
        color: style.color,
        lineWidth: 2,
        lineStyle: style.lineStyle,
        axisLabelVisible: true,
        title: style.title ?? spec.key.toUpperCase(),
      }));
    }

    const isLong = highlight.direction === 'long';
    const entryTime = Math.floor(candle.timestamp / 1000);

    for (const m of highlight.setup?.markers ?? []) {
      const t = Math.floor(m.time / 1000);
      const role = m.role ?? 'entry';
      const color = MARKER_ROLE_COLORS[role] ?? '#94a3b8';
      let shape = 'circle';
      let position = 'aboveBar';

      if (role === 'breakout') {
        shape = 'circle';
        position = isLong ? 'belowBar' : 'aboveBar';
      } else if (role === 'sweep') {
        shape = isLong ? 'arrowUp' : 'arrowDown';
        position = isLong ? 'belowBar' : 'aboveBar';
      } else if (role === 'entry') {
        shape = isLong ? 'arrowUp' : 'arrowDown';
        position = isLong ? 'belowBar' : 'aboveBar';
      } else if (role === 'confirm') {
        shape = isLong ? 'arrowUp' : 'arrowDown';
        position = isLong ? 'belowBar' : 'aboveBar';
      }

      markers.push({
        time: t,
        position,
        color,
        shape,
        text: m.label,
      });
    }

    if (!markers.some((m) => m.time === entryTime)) {
      markers.push({
        time: entryTime,
        position: isLong ? 'belowBar' : 'aboveBar',
        color: TRADE_LEVEL_STYLES.entry.color,
        shape: isLong ? 'arrowUp' : 'arrowDown',
        text: 'Entry',
      });
    }

    markers.sort((a, b) => a.time - b.time);
    this.#candleSeries.setMarkers(markers);
    this.#activeHighlight = highlight;
    this.#applyViewportPadding('signal');
    this.#applySignalAutoscale(highlight);
    this.focusOnCandleIndex(index);
  }

  /** Remove signal marker and price lines. */
  clearSignalOverlay() {
    this.#candleSeries?.setMarkers([]);
    for (const line of this.#priceLines) {
      this.#candleSeries?.removePriceLine(line);
    }
    this.#priceLines = [];
    this.#activeHighlight = null;
    this.#applyViewportPadding('normal');
    this.#candleSeries?.applyOptions({ autoscaleInfoProvider: undefined });
  }

  /**
   * @param {'normal'|'signal'} mode
   */
  #applyViewportPadding(mode) {
    if (!this.#chart || this.#paddingMode === mode) return;
    this.#paddingMode = mode;

    const isSignal = mode === 'signal';
    const chartCfg = Config.CHART;

    this.#chart.applyOptions({
      rightPriceScale: {
        scaleMargins: isSignal
          ? { ...chartCfg.SIGNAL_PRICE_SCALE_MARGINS }
          : { ...chartCfg.PRICE_SCALE_MARGINS },
        minimumWidth: isSignal
          ? chartCfg.SIGNAL_PRICE_SCALE_MIN_WIDTH
          : chartCfg.PRICE_SCALE_MIN_WIDTH,
      },
      timeScale: {
        rightOffset: isSignal
          ? chartCfg.SIGNAL_TIME_RIGHT_OFFSET
          : chartCfg.TIME_RIGHT_OFFSET,
      },
    });
  }

  /**
   * @param {import('../utils/chartNavigation.js').ChartSignalHighlight} highlight
   */
  #applySignalAutoscale(highlight) {
    if (!this.#candleSeries) return;

    const extraPrices = this.#collectOverlayPrices(highlight);
    const pad = Config.CHART.SIGNAL_AUTOSCALE_PADDING_RATIO;

    this.#candleSeries.applyOptions({
      autoscaleInfoProvider: (original) => {
        const base = original();
        if (!base?.priceRange) return base;

        let minValue = base.priceRange.minValue;
        let maxValue = base.priceRange.maxValue;

        for (const price of extraPrices) {
          minValue = Math.min(minValue, price);
          maxValue = Math.max(maxValue, price);
        }

        const span = Math.max(maxValue - minValue, Config.CHART.MIN_MOVE * 10);
        return {
          priceRange: {
            minValue: minValue - span * pad,
            maxValue: maxValue + span * pad,
          },
        };
      },
    });
  }

  /**
   * @param {import('../utils/chartNavigation.js').ChartSignalHighlight} highlight
   * @returns {number[]}
   */
  #collectOverlayPrices(highlight) {
    const prices = [highlight.entry, highlight.sl, highlight.tp];
    for (const level of highlight.setup?.levels ?? []) {
      prices.push(level.price);
      if (level.priceTo != null) prices.push(level.priceTo);
    }
    return prices;
  }

  /**
   * Re-apply autoscale after candle data changes while signal overlay is active.
   */
  refreshSignalScale() {
    if (!this.#activeHighlight) return;
    this.#chart?.priceScale('right').applyOptions({ autoScale: true });
  }

  /**
   * Scroll chart so the signal candle is centered with context bars.
   * @param {number} index - Index in currently displayed candle array
   * @param {number} [contextBars=35]
   */
  focusOnCandleIndex(index, contextBars = 35) {
    if (!this.#chart) return;
    const from = Math.max(0, index - contextBars);
    const to = index + (this.#paddingMode === 'signal' ? 12 : 8);
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
