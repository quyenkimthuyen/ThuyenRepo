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
import {
  buildAnalysisMarkers,
  buildCyclePriceLines,
  buildElliottLineSeries,
  buildHalvingMarkers,
  buildTrendLineSeries,
  clipAnalysisToCandles,
} from './AnalysisOverlay.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('ChartEngine');

/**
 * @typedef {{
 *   timeMs: number,
 *   open: number,
 *   high: number,
 *   low: number,
 *   close: number,
 * }} CrosshairHit
 */

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

  /** @type {import('../../vendor/lightweight-charts.mjs').ISeriesApi<'Line'>[]} */
  #trendSeries = [];

  /** @type {import('../../vendor/lightweight-charts.mjs').ISeriesApi<'Line'>[]} */
  #elliottSeries = [];

  /** @type {import('../../vendor/lightweight-charts.mjs').IPriceLine[]} */
  #analysisPriceLines = [];

  /** @type {import('../analysis/LongTermAnalysisEngine.js').LongTermAnalysisResult|null} */
  #analysisOverlay = null;

  /** @type {(() => void)|null} */
  #timeScaleHandler = null;

  /** @type {((hit: CrosshairHit|null) => void)|null} */
  #crosshairHandler = null;

  /** @type {((param: import('../../vendor/lightweight-charts.mjs').MouseEventParams) => void)|null} */
  #crosshairListener = null;

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
   * Apply long-term BTC analysis overlays (swings, trends, cycle, Elliott, halving).
   * @param {import('../analysis/LongTermAnalysisEngine.js').LongTermAnalysisResult|null} analysis
   * @param {{
   *   candles?: import('../data/Candle.js').Candle[],
   *   showSwings?: boolean,
   *   showTrends?: boolean,
   *   showCycle?: boolean,
   *   showElliott?: boolean,
   *   showHalving?: boolean,
   * }} [options]
   */
  setAnalysisOverlay(analysis, options = {}) {
    this.clearAnalysisOverlay();
    if (!analysis || !this.#candleSeries || !this.#chart) return;

    const candles = options.candles ?? [];
    const clipped = candles.length > 0 ? clipAnalysisToCandles(analysis, candles) : analysis;
    this.#analysisOverlay = clipped;

    const showSwings = options.showSwings !== false;
    const showTrends = options.showTrends !== false;
    const showCycle = options.showCycle !== false;
    const showElliott = options.showElliott !== false;
    const showHalving = options.showHalving !== false;

    if (!this.#activeHighlight) {
      /** @type {Array<Record<string, unknown>>} */
      const markers = [];
      if (showSwings || showElliott) {
        markers.push(...buildAnalysisMarkers(clipped, candles, {
          maxSwingMarkers: showSwings ? 24 : 0,
        }).filter((m) => showSwings || !['\u0110\u1ec9nh', '\u0110\u00e1y'].includes(String(m.text))));
      }
      if (showHalving && candles.length > 0) {
        markers.push(...buildHalvingMarkers(candles));
      }
      if (markers.length > 0) {
        markers.sort((a, b) => a.time - b.time);
        this.#candleSeries.setMarkers(markers);
      }
    }

    if (showTrends && candles.length > 0) {
      for (const series of buildTrendLineSeries(clipped, candles)) {
        const line = this.#chart.addLineSeries({
          color: series.color,
          lineWidth: series.lineWidth,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        line.setData(series.data);
        this.#trendSeries.push(line);
      }
    }

    if (showElliott && candles.length > 0) {
      for (const series of buildElliottLineSeries(clipped, candles)) {
        const line = this.#chart.addLineSeries({
          color: series.color,
          lineWidth: series.lineWidth,
          lineStyle: 0,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        line.setData(series.data);
        this.#elliottSeries.push(line);
      }
    }

    if (showCycle) {
      for (const spec of buildCyclePriceLines(clipped)) {
        this.#analysisPriceLines.push(this.#candleSeries.createPriceLine({
          price: spec.price,
          color: spec.color,
          lineWidth: 1,
          lineStyle: spec.lineStyle ?? 2,
          axisLabelVisible: true,
          title: spec.title,
        }));
      }
    }
  }

  /** Remove analysis overlay lines and markers. */
  clearAnalysisOverlay() {
    for (const series of this.#trendSeries) {
      this.#chart?.removeSeries(series);
    }
    this.#trendSeries = [];

    for (const series of this.#elliottSeries) {
      this.#chart?.removeSeries(series);
    }
    this.#elliottSeries = [];

    for (const line of this.#analysisPriceLines) {
      this.#candleSeries?.removePriceLine(line);
    }
    this.#analysisPriceLines = [];

    this.#analysisOverlay = null;

    if (!this.#activeHighlight) {
      this.#candleSeries?.setMarkers([]);
    }
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
   * @returns {import('../../vendor/lightweight-charts.mjs').ITimeScaleApi|null}
   */
  getTimeScale() {
    return this.#chart?.timeScale() ?? null;
  }

  /**
   * @returns {number}
   */
  getChartWidth() {
    return this.#container?.clientWidth ?? 0;
  }

  /**
   * Plot area width (excludes right price scale).
   * @returns {number}
   */
  getPlotWidth() {
    const total = this.getChartWidth();
    if (!this.#chart || total <= 0) return total;
    const scaleW = this.#chart.priceScale('right').width();
    const plot = Math.max(0, total - scaleW);
    if (plot >= 10) return plot;
    return Math.max(0, Math.floor(total * 0.88));
  }

  /**
   * @returns {{ from: number, to: number }|null} milliseconds
   */
  getVisibleTimeRangeMs() {
    const range = this.#chart?.timeScale().getVisibleRange();
    if (!range) return null;
    return { from: range.from * 1000, to: range.to * 1000 };
  }

  /**
   * @param {() => void} callback
   */
  onVisibleRangeChange(callback) {
    this.offVisibleRangeChange();
    if (!this.#chart) return;
    this.#timeScaleHandler = callback;
    this.#chart.timeScale().subscribeVisibleLogicalRangeChange(this.#timeScaleHandler);
  }

  offVisibleRangeChange() {
    if (this.#chart && this.#timeScaleHandler) {
      this.#chart.timeScale().unsubscribeVisibleLogicalRangeChange(this.#timeScaleHandler);
    }
    this.#timeScaleHandler = null;
  }

  /**
   * @param {(hit: CrosshairHit|null) => void} callback
   */
  onCrosshairMove(callback) {
    this.offCrosshairMove();
    if (!this.#chart || !this.#candleSeries) return;

    this.#crosshairHandler = callback;
    this.#crosshairListener = (param) => {
      if (
        !param.time
        || param.point === undefined
        || param.point.x < 0
        || param.point.y < 0
      ) {
        callback(null);
        return;
      }

      const bar = param.seriesData.get(this.#candleSeries);
      if (!bar) {
        callback(null);
        return;
      }

      callback({
        timeMs: Number(param.time) * 1000,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      });
    };

    this.#chart.subscribeCrosshairMove(this.#crosshairListener);
  }

  offCrosshairMove() {
    if (this.#chart && this.#crosshairListener) {
      this.#chart.unsubscribeCrosshairMove(this.#crosshairListener);
    }
    this.#crosshairListener = null;
    this.#crosshairHandler = null;
  }

  /**
   * Destroy chart and release resources.
   */
  destroy() {
    this.#resizeObserver?.disconnect();
    this.#resizeObserver = null;
    this.offVisibleRangeChange();
    this.offCrosshairMove();
    this.clearAnalysisOverlay();
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
