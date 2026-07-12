import { createChart, CrosshairMode, LineStyle } from '../vendor/lightweight-charts.mjs';

const COLORS = {
  bg: '#0b0f14',
  grid: '#1e2a38',
  text: '#8b9cb3',
  up: '#22c55e',
  down: '#ef4444',
  ema50: '#38bdf8',
  ema200: '#a78bfa',
  rsi: '#f59e0b',
};

/** Cố định độ rộng price scale — tránh lệch trục thời gian giữa chart giá và RSI */
const RIGHT_SCALE_WIDTH = 84;

const RSI_BANDS = {
  low: [28, 32],
  mid: [48, 52],
  high: [68, 72],
};

export class RsiZoneChart {
  #wrapEl;
  #bodyEl;
  #mainEl;
  #rsiEl;
  #mainChart;
  #rsiChart;
  #candles = [];
  #candleSeries;
  #ema50Series;
  #ema200Series;
  #rsiSeries;
  #rsiBandLines = [];
  #rsiData = [];
  #showEma50 = true;
  #showEma200 = true;
  #syncing = false;
  #resizeObserver;
  #resizeTimer;
  #onCrosshair;
  #mounted = false;
  #hasInitialFit = false;
  #savedLogicalRange = null;

  constructor(mainEl, rsiEl, { wrapEl, bodyEl, onCrosshair } = {}) {
    this.#mainEl = mainEl;
    this.#rsiEl = rsiEl;
    this.#wrapEl = wrapEl ?? mainEl.parentElement;
    this.#bodyEl = bodyEl ?? this.#wrapEl?.parentElement;
    this.#onCrosshair = onCrosshair;
  }

  mount() {
    if (this.#mounted) return;

    const width = this.#chartWidth();
    const priceScale = {
      borderColor: COLORS.grid,
      minimumWidth: RIGHT_SCALE_WIDTH,
      autoScale: true,
    };

    const common = {
      layout: { background: { color: COLORS.bg }, textColor: COLORS.text },
      grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: priceScale,
      leftPriceScale: { visible: false },
      localization: { locale: 'en-US' },
    };

    const timeScale = {
      borderColor: COLORS.grid,
      timeVisible: true,
      secondsVisible: false,
      rightOffset: 6,
      barSpacing: 6,
      fixLeftEdge: false,
      fixRightEdge: false,
    };

    const mainInteractions = {
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      },
      handleScale: {
        mouseWheel: true,
        pinch: true,
        axisPressedMouseMove: { time: true, price: true },
      },
    };

    this.#mainChart = createChart(this.#mainEl, {
      ...common,
      ...mainInteractions,
      width,
      height: this.#mainHeight(),
      timeScale,
    });

    this.#candleSeries = this.#mainChart.addCandlestickSeries({
      upColor: COLORS.up,
      downColor: COLORS.down,
      borderVisible: false,
      wickUpColor: COLORS.up,
      wickDownColor: COLORS.down,
    });
    this.#ema50Series = this.#mainChart.addLineSeries({
      color: COLORS.ema50,
      lineWidth: 2,
      title: 'EMA50',
      priceLineVisible: false,
      lastValueVisible: true,
    });
    this.#ema200Series = this.#mainChart.addLineSeries({
      color: COLORS.ema200,
      lineWidth: 2,
      title: 'EMA200',
      priceLineVisible: false,
      lastValueVisible: true,
    });

    this.#rsiChart = createChart(this.#rsiEl, {
      ...common,
      width,
      height: this.#rsiEl.clientHeight || 220,
      timeScale: {
        ...timeScale,
        timeVisible: false,
        borderVisible: false,
      },
      handleScroll: {
        mouseWheel: false,
        pressedMouseMove: false,
        horzTouchDrag: false,
        vertTouchDrag: false,
      },
      handleScale: {
        mouseWheel: false,
        pinch: false,
        axisPressedMouseMove: { time: false, price: false },
      },
    });

    this.#rsiSeries = this.#rsiChart.addLineSeries({
      color: COLORS.rsi,
      lineWidth: 2,
      title: 'RSI H4',
      priceLineVisible: false,
      lastValueVisible: true,
    });
    this.#rsiChart.priceScale('right').applyOptions({
      scaleMargins: { top: 0.08, bottom: 0.08 },
      minimumWidth: RIGHT_SCALE_WIDTH,
    });
    this.#applyRsiScale();
    this.#drawRsiBands();
    this.#lockPriceScaleWidths();

    this.#mainChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (this.#syncing || !range) return;
      this.#savedLogicalRange = range;
      this.#syncing = true;
      this.#rsiChart.timeScale().setVisibleLogicalRange(range);
      this.#syncing = false;
    });

    this.#mainChart.subscribeCrosshairMove((param) => {
      this.#syncCrosshair(param);
      this.#emitCrosshair(param);
    });

    const observeEl = this.#bodyEl || this.#wrapEl || this.#mainEl;
    this.#resizeObserver = new ResizeObserver(() => {
      clearTimeout(this.#resizeTimer);
      this.#resizeTimer = setTimeout(() => this.#resize(), 80);
    });
    this.#resizeObserver.observe(observeEl);
    this.#mounted = true;
    requestAnimationFrame(() => this.#resize());
  }

  #chartWidth() {
    const bodyW = this.#bodyEl?.clientWidth ?? 0;
    const wrapW = this.#wrapEl?.clientWidth ?? 0;
    const mainW = this.#mainEl?.clientWidth ?? 0;
    return Math.max(bodyW, wrapW, mainW, 320);
  }

  #mainHeight() {
    const wrapH = this.#wrapEl?.clientHeight ?? 0;
    return Math.max(wrapH, this.#mainEl.clientHeight, 280);
  }

  #lockPriceScaleWidths() {
    const w = RIGHT_SCALE_WIDTH;
    this.#mainChart.priceScale('right').applyOptions({ minimumWidth: w });
    this.#rsiChart.priceScale('right').applyOptions({ minimumWidth: w });
  }

  #applyRsiScale() {
    this.#rsiSeries.applyOptions({
      autoscaleInfoProvider: () => ({ priceRange: { minValue: 0, maxValue: 100 } }),
    });
  }

  #drawRsiBands() {
    for (const line of this.#rsiBandLines) {
      try { this.#rsiSeries.removePriceLine(line); } catch { /* */ }
    }
    this.#rsiBandLines = [];
    const specs = [
      { range: RSI_BANDS.low, color: 'rgba(239, 68, 68, 0.7)', title: '30' },
      { range: RSI_BANDS.mid, color: 'rgba(56, 189, 248, 0.7)', title: '50' },
      { range: RSI_BANDS.high, color: 'rgba(34, 197, 94, 0.7)', title: '70' },
    ];
    for (const spec of specs) {
      for (const price of spec.range) {
        this.#rsiBandLines.push(
          this.#rsiSeries.createPriceLine({
            price,
            color: spec.color,
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: spec.title,
          }),
        );
      }
    }
  }

  #syncCrosshair(param) {
    if (!param?.time) {
      this.#rsiChart.clearCrosshairPosition();
      return;
    }
    const time = this.#nearestCandle(param.time)?.time ?? param.time;
    const value = this.#rsiData.find((p) => p.time === time)?.value;
    if (value == null) {
      this.#rsiChart.clearCrosshairPosition();
      return;
    }
    this.#rsiChart.setCrosshairPosition(value, time, this.#rsiSeries);
  }

  #emitCrosshair(param) {
    if (!param?.time || !this.#candles.length) {
      this.#onCrosshair?.(null);
      return;
    }
    const candle = this.#nearestCandle(param.time);
    const rsi = this.#rsiData.find((p) => p.time === candle?.time)?.value;
    this.#onCrosshair?.({ candle, rsi, time: candle?.time });
  }

  #nearestCandle(time) {
    if (!this.#candles.length) return null;
    let best = this.#candles[0];
    let diff = Math.abs(best.time - time);
    for (const c of this.#candles) {
      const d = Math.abs(c.time - time);
      if (d < diff) { best = c; diff = d; }
    }
    return best;
  }

  #alignSeries(candles, points, forwardFill = false) {
    const byTime = new Map((points || []).map((p) => [p.time, p.value]));
    let last = null;
    const out = [];
    for (const c of candles) {
      let v = byTime.get(c.time);
      if (v != null && !Number.isNaN(v)) {
        last = v;
        out.push({ time: c.time, value: v });
      } else if (forwardFill && last != null) {
        out.push({ time: c.time, value: last });
      }
    }
    return out;
  }

  #captureRange() {
    return this.#mainChart?.timeScale().getVisibleLogicalRange() ?? this.#savedLogicalRange;
  }

  #restoreRange(range) {
    if (!range || !this.#mainChart) return;
    this.#syncing = true;
    this.#mainChart.timeScale().setVisibleLogicalRange(range);
    this.#rsiChart.timeScale().setVisibleLogicalRange(range);
    this.#syncing = false;
    this.#savedLogicalRange = range;
  }

  #resize() {
    const width = this.#chartWidth();
    const mainHeight = this.#mainHeight();
    const rsiHeight = Math.max(this.#rsiEl.clientHeight || 0, 120);
    if (width <= 0 || mainHeight <= 0) return;

    const range = this.#captureRange();
    this.#mainChart?.applyOptions({ width, height: mainHeight });
    this.#rsiChart?.applyOptions({ width, height: rsiHeight });
    this.#lockPriceScaleWidths();
    this.#restoreRange(range);
  }

  setData({ candles, indicators }, { fit = false } = {}) {
    const range = this.#captureRange();
    const shouldFit = fit || !this.#hasInitialFit;

    this.#candles = candles;
    this.#candleSeries.setData(candles);
    const ema50 = this.#alignSeries(candles, indicators?.ema50);
    const ema200 = this.#alignSeries(candles, indicators?.ema200);
    const rsiData = this.#alignSeries(candles, indicators?.rsi14_h4, true);
    this.#rsiData = rsiData;
    this.#ema50Series.setData(this.#showEma50 ? ema50 : []);
    this.#ema200Series.setData(this.#showEma200 ? ema200 : []);
    this.#rsiSeries.setData(rsiData);

    requestAnimationFrame(() => {
      this.#resize();
      if (shouldFit) {
        this.#mainChart.timeScale().fitContent();
        this.#syncRsiFromMain();
        this.#hasInitialFit = true;
        this.#savedLogicalRange = this.#captureRange();
      } else {
        this.#restoreRange(range);
      }
      this.#lockPriceScaleWidths();
    });
  }

  #syncRsiFromMain() {
    const range = this.#mainChart.timeScale().getVisibleLogicalRange();
    if (!range) return;
    this.#syncing = true;
    this.#rsiChart.timeScale().setVisibleLogicalRange(range);
    this.#syncing = false;
  }

  setMarkers(markers) {
    this.#candleSeries.setMarkers(markers || []);
  }

  focusTime(time) {
    const idx = this.#candles.findIndex((c) => c.time === time);
    if (idx < 0) return;
    const range = { from: Math.max(0, idx - 80), to: Math.min(this.#candles.length - 1, idx + 80) };
    this.#restoreRange(range);
  }

  zoomIn() {
    const range = this.#captureRange();
    if (!range) return;
    const center = (range.from + range.to) / 2;
    const span = (range.to - range.from) * 0.75;
    this.#restoreRange({ from: center - span / 2, to: center + span / 2 });
  }

  zoomOut() {
    const range = this.#captureRange();
    if (!range) return;
    const center = (range.from + range.to) / 2;
    const span = Math.min((range.to - range.from) * 1.35, this.#candles.length);
    this.#restoreRange({
      from: Math.max(0, center - span / 2),
      to: Math.min(this.#candles.length - 1, center + span / 2),
    });
  }

  fitContent() {
    this.#mainChart.timeScale().fitContent();
    this.#syncRsiFromMain();
    this.#savedLogicalRange = this.#captureRange();
  }

  scrollToLatest() {
    if (!this.#candles.length) return;
    const span = this.#savedLogicalRange
      ? this.#savedLogicalRange.to - this.#savedLogicalRange.from
      : 120;
    const to = this.#candles.length - 1;
    this.#restoreRange({ from: Math.max(0, to - span), to });
  }

  applyEmaVisibility(show50, show200, indicators) {
    this.#showEma50 = show50;
    this.#showEma200 = show200;
    if (!this.#candles.length) return;
    const range = this.#captureRange();
    this.#ema50Series.setData(show50 ? this.#alignSeries(this.#candles, indicators?.ema50) : []);
    this.#ema200Series.setData(show200 ? this.#alignSeries(this.#candles, indicators?.ema200) : []);
    this.#restoreRange(range);
  }

  resize() {
    this.#resize();
  }
}
