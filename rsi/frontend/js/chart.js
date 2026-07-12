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

const RIGHT_SCALE_WIDTH = 84;

const RSI_BANDS = {
  low: [28, 32],
  mid: [48, 52],
  high: [68, 72],
};

const DEFAULT_VISIBLE_BARS = 320;

function isFiniteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

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
  #syncRaf = 0;
  #onCrosshair;
  #mounted = false;
  #hasInitialFit = false;
  #savedLogicalRange = null;
  #interacting = false;
  #wheelEndTimer = 0;
  #lastW = 0;
  #lastMainH = 0;
  #lastRsiH = 0;

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

    this.#mainChart = createChart(this.#mainEl, {
      ...common,
      width,
      height: this.#mainHeight(),
      timeScale,
      kineticScroll: { mouse: true, touch: true },
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
      lastValueVisible: false,
    });
    this.#ema200Series = this.#mainChart.addLineSeries({
      color: COLORS.ema200,
      lineWidth: 2,
      title: 'EMA200',
      priceLineVisible: false,
      lastValueVisible: false,
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
      lastValueVisible: false,
    });
    this.#rsiChart.priceScale('right').applyOptions({
      scaleMargins: { top: 0.08, bottom: 0.08 },
      minimumWidth: RIGHT_SCALE_WIDTH,
    });
    this.#applyRsiScale();
    this.#drawRsiBands();

    this.#mainChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (this.#syncing || !range) return;
      this.#savedLogicalRange = range;
      this.#scheduleRsiSync(range);
    });

    this.#mainChart.subscribeCrosshairMove((param) => {
      this.#syncCrosshair(param);
      this.#emitCrosshair(param);
    });

    this.#bindInteractionGuards();

    const observeEl = this.#bodyEl || this.#wrapEl || this.#mainEl;
    this.#resizeObserver = new ResizeObserver(() => {
      if (this.#interacting) return;
      clearTimeout(this.#resizeTimer);
      this.#resizeTimer = setTimeout(() => this.#resize(), 150);
    });
    this.#resizeObserver.observe(observeEl);
    this.#mounted = true;
    requestAnimationFrame(() => this.#resize(true));
  }

  #bindInteractionGuards() {
    const root = this.#mainEl;
    const start = () => { this.#interacting = true; };
    const stop = () => {
      this.#interacting = false;
      requestAnimationFrame(() => this.#resize());
    };

    root.addEventListener('pointerdown', start);
    root.addEventListener('wheel', start, { passive: true });
    window.addEventListener('pointerup', stop);
    window.addEventListener('pointercancel', stop);
    root.addEventListener('wheel', () => {
      clearTimeout(this.#wheelEndTimer);
      this.#wheelEndTimer = setTimeout(() => { this.#interacting = false; }, 120);
    }, { passive: true });
  }

  #scheduleRsiSync(range) {
    const safeRange = this.#normalizeRange(range);
    if (!safeRange) return;
    cancelAnimationFrame(this.#syncRaf);
    this.#syncRaf = requestAnimationFrame(() => {
      if (this.#syncing) return;
      this.#syncing = true;
      this.#rsiChart.timeScale().setVisibleLogicalRange(safeRange);
      this.#syncing = false;
    });
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
    const byTime = new Map(
      (points || [])
        .filter((p) => isFiniteNumber(p?.time) && isFiniteNumber(p?.value))
        .map((p) => [p.time, p.value]),
    );
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

  #sanitizeCandles(candles) {
    return (candles || []).filter((c) => (
      isFiniteNumber(c?.time)
      && isFiniteNumber(c?.open)
      && isFiniteNumber(c?.high)
      && isFiniteNumber(c?.low)
      && isFiniteNumber(c?.close)
    ));
  }

  #normalizeRange(range) {
    if (!range || !isFiniteNumber(range.from) || !isFiniteNumber(range.to)) return null;
    if (range.to <= range.from) return null;
    if (!this.#candles.length) return range;
    const from = Math.max(0, Math.min(this.#candles.length - 1, range.from));
    const to = Math.max(0, Math.min(this.#candles.length - 1, range.to));
    if (to <= from) return null;
    return { from, to };
  }

  #captureRange() {
    return this.#normalizeRange(
      this.#mainChart?.timeScale().getVisibleLogicalRange() ?? this.#savedLogicalRange,
    );
  }

  #setMainRange(range) {
    const safeRange = this.#normalizeRange(range);
    if (!safeRange || !this.#mainChart) return;
    this.#syncing = true;
    this.#mainChart.timeScale().setVisibleLogicalRange(safeRange);
    this.#syncing = false;
    this.#savedLogicalRange = safeRange;
    this.#scheduleRsiSync(safeRange);
  }

  #syncRsiFromMain() {
    const range = this.#mainChart?.timeScale().getVisibleLogicalRange();
    if (!range) return;
    this.#scheduleRsiSync(range);
  }

  #resize(force = false) {
    const width = this.#chartWidth();
    const mainHeight = this.#mainHeight();
    const rsiHeight = Math.max(this.#rsiEl.clientHeight || 0, 120);
    if (width <= 0 || mainHeight <= 0) return;

    if (
      !force
      && Math.abs(width - this.#lastW) < 2
      && Math.abs(mainHeight - this.#lastMainH) < 2
      && Math.abs(rsiHeight - this.#lastRsiH) < 2
    ) {
      return;
    }

    this.#lastW = width;
    this.#lastMainH = mainHeight;
    this.#lastRsiH = rsiHeight;

    this.#mainChart?.applyOptions({ width, height: mainHeight });
    this.#rsiChart?.applyOptions({ width, height: rsiHeight });
    this.#syncRsiFromMain();
  }

  setData({ candles, indicators }, { fit = false } = {}) {
    const range = this.#captureRange();
    const shouldShowLatest = !fit && !this.#hasInitialFit;

    this.#candles = this.#sanitizeCandles(candles);
    this.#candleSeries.setData(this.#candles);
    const ema50 = this.#alignSeries(this.#candles, indicators?.ema50);
    const ema200 = this.#alignSeries(this.#candles, indicators?.ema200);
    const rsiData = this.#alignSeries(this.#candles, indicators?.rsi14_h4, true);
    this.#rsiData = rsiData;
    this.#ema50Series.setData(this.#showEma50 ? ema50 : []);
    this.#ema200Series.setData(this.#showEma200 ? ema200 : []);
    this.#rsiSeries.setData(rsiData);

    requestAnimationFrame(() => {
      this.#resize(true);
      if (fit) {
        this.#mainChart.timeScale().fitContent();
        this.#hasInitialFit = true;
        this.#savedLogicalRange = this.#captureRange();
        this.#syncRsiFromMain();
      } else if (shouldShowLatest) {
        this.scrollToLatest(DEFAULT_VISIBLE_BARS);
        this.#hasInitialFit = true;
      } else if (range) {
        this.#setMainRange(range);
      }
    });
  }

  setMarkers(markers) {
    this.#candleSeries.setMarkers((markers || []).filter((marker) => isFiniteNumber(marker?.time)));
  }

  focusTime(time) {
    const idx = this.#candles.findIndex((c) => c.time === time);
    if (idx < 0) return;
    this.#setMainRange({
      from: Math.max(0, idx - 80),
      to: Math.min(this.#candles.length - 1, idx + 80),
    });
  }

  zoomIn() {
    const range = this.#captureRange();
    if (!range) return;
    const center = (range.from + range.to) / 2;
    const span = (range.to - range.from) * 0.75;
    this.#setMainRange({ from: center - span / 2, to: center + span / 2 });
  }

  zoomOut() {
    const range = this.#captureRange();
    if (!range) return;
    const center = (range.from + range.to) / 2;
    const span = Math.min((range.to - range.from) * 1.35, this.#candles.length);
    this.#setMainRange({
      from: Math.max(0, center - span / 2),
      to: Math.min(this.#candles.length - 1, center + span / 2),
    });
  }

  fitContent() {
    this.#mainChart.timeScale().fitContent();
    this.#savedLogicalRange = this.#captureRange();
    this.#syncRsiFromMain();
  }

  scrollToLatest(targetBars) {
    if (!this.#candles.length) return;
    const span = isFiniteNumber(targetBars)
      ? targetBars
      : this.#savedLogicalRange
        ? this.#savedLogicalRange.to - this.#savedLogicalRange.from
        : 120;
    const to = this.#candles.length - 1;
    this.#setMainRange({ from: Math.max(0, to - span), to });
  }

  applyEmaVisibility(show50, show200, indicators) {
    this.#showEma50 = show50;
    this.#showEma200 = show200;
    if (!this.#candles.length) return;
    this.#ema50Series.setData(show50 ? this.#alignSeries(this.#candles, indicators?.ema50) : []);
    this.#ema200Series.setData(show200 ? this.#alignSeries(this.#candles, indicators?.ema200) : []);
  }

  resize() {
    this.#resize(true);
  }
}
