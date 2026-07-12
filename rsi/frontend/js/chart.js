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

const RIGHT_SCALE_MIN_WIDTH = 78;

const RSI_BANDS = {
  low: [28, 32],
  mid: [48, 52],
  high: [68, 72],
};

export class RsiZoneChart {
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
  #onCrosshair;
  #mounted = false;

  constructor(mainEl, rsiEl, { onCrosshair } = {}) {
    this.#mainEl = mainEl;
    this.#rsiEl = rsiEl;
    this.#onCrosshair = onCrosshair;
  }

  mount() {
    if (this.#mounted) return;

    const width = this.#mainEl.clientWidth || 800;
    const priceScale = { borderColor: COLORS.grid, minimumWidth: RIGHT_SCALE_MIN_WIDTH };
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
    };

    this.#mainChart = createChart(this.#mainEl, {
      ...common,
      width,
      height: this.#mainEl.clientHeight || 400,
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
      width: this.#rsiEl.clientWidth || width,
      height: this.#rsiEl.clientHeight || 220,
      timeScale: {
        ...timeScale,
        timeVisible: true,
      },
      handleScroll: { mouseWheel: false, pressedMouseMove: false, horzTouchDrag: false },
      handleScale: {
        mouseWheel: false,
        pinch: false,
        axisPressedMouseMove: { time: false, price: true },
      },
    });

    this.#rsiSeries = this.#rsiChart.addLineSeries({
      color: COLORS.rsi,
      lineWidth: 2,
      title: 'RSI H4',
      priceLineVisible: false,
    });
    this.#rsiChart.priceScale('right').applyOptions({ scaleMargins: { top: 0.08, bottom: 0.08 } });
    this.#applyRsiScale();
    this.#drawRsiBands();

    const syncRange = (range) => {
      if (this.#syncing || !range) return;
      this.#syncing = true;
      this.#rsiChart.timeScale().setVisibleLogicalRange(range);
      this.#syncing = false;
      this.#syncPriceScaleWidth();
    };

    const syncFromRsi = (range) => {
      if (this.#syncing || !range) return;
      this.#syncing = true;
      this.#mainChart.timeScale().setVisibleLogicalRange(range);
      this.#syncing = false;
      this.#syncPriceScaleWidth();
    };

    this.#mainChart.timeScale().subscribeVisibleLogicalRangeChange(syncRange);
    this.#rsiChart.timeScale().subscribeVisibleLogicalRangeChange(syncFromRsi);

    this.#mainChart.subscribeCrosshairMove((param) => {
      this.#syncCrosshair(param);
      this.#emitCrosshair(param);
    });

    this.#resizeObserver = new ResizeObserver(() => this.#resize());
    this.#resizeObserver.observe(this.#mainEl.parentElement || this.#mainEl);
    this.#mounted = true;
    requestAnimationFrame(() => this.#resize());
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

  #syncPriceScaleWidth() {
    const mainW = this.#mainChart.priceScale('right').width();
    const rsiW = this.#rsiChart.priceScale('right').width();
    const w = Math.max(mainW, rsiW, RIGHT_SCALE_MIN_WIDTH);
    this.#mainChart.priceScale('right').applyOptions({ minimumWidth: w });
    this.#rsiChart.priceScale('right').applyOptions({ minimumWidth: w });
  }

  #syncCrosshair(param) {
    if (!param?.time) {
      this.#rsiChart.clearCrosshairPosition();
      return;
    }
    const time = this.#nearestCandle(param.time)?.time ?? param.time;
    let value = param.seriesData?.get(this.#rsiSeries)?.value;
    if (value == null) value = this.#rsiData.find((p) => p.time === time)?.value;
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

  #resize() {
    const wrap = this.#mainEl.parentElement;
    const w = Math.max(wrap?.clientWidth ?? 0, this.#mainEl.clientWidth, 320);
    const totalH = wrap?.clientHeight ?? 600;
    const rsiH = Math.max(this.#rsiEl.clientHeight, 180);
    const mainH = Math.max(totalH - rsiH - 40, 240);
    this.#mainChart?.applyOptions({ width: w, height: mainH });
    this.#rsiChart?.applyOptions({ width: w, height: rsiH });
    this.#syncPriceScaleWidth();
    this.#syncRsiTimeScale();
  }

  #syncRsiTimeScale() {
    const range = this.#mainChart.timeScale().getVisibleLogicalRange();
    if (!range) return;
    this.#syncing = true;
    this.#rsiChart.timeScale().setVisibleLogicalRange(range);
    this.#syncing = false;
  }

  setData({ candles, indicators }) {
    this.#candles = candles;
    this.#candleSeries.setData(candles);
    const ema50 = this.#alignSeries(candles, indicators?.ema50);
    const ema200 = this.#alignSeries(candles, indicators?.ema200);
    const rsiData = this.#alignSeries(candles, indicators?.rsi14_h4, true);
    this.#rsiData = rsiData;
    this.#ema50Series.setData(this.#showEma50 ? ema50 : []);
    this.#ema200Series.setData(this.#showEma200 ? ema200 : []);
    this.#rsiSeries.setData(rsiData);
    this.#resize();
    this.#mainChart.timeScale().fitContent();
    this.#syncRsiTimeScale();
  }

  setMarkers(markers) {
    this.#candleSeries.setMarkers(markers || []);
  }

  focusTime(time) {
    const idx = this.#candles.findIndex((c) => c.time === time);
    if (idx < 0) return;
    const range = { from: Math.max(0, idx - 60), to: Math.min(this.#candles.length - 1, idx + 60) };
    this.#mainChart.timeScale().setVisibleLogicalRange(range);
    this.#syncRsiTimeScale();
  }

  setShowEma50(v) {
    this.#showEma50 = v;
    if (this.#candles.length) {
      const ema50 = this.#alignSeries(this.#candles, []);
      this.#ema50Series.setData(v ? ema50 : []);
    }
  }

  setShowEma200(v) {
    this.#showEma200 = v;
  }

  toggleEma(ema50, ema200) {
    this.#showEma50 = ema50;
    this.#showEma200 = ema200;
    if (!this.#candles.length) return;
    // Re-apply from last indicators stored in series - need to re-set from parent
  }

  applyEmaVisibility(show50, show200, indicators) {
    this.#showEma50 = show50;
    this.#showEma200 = show200;
    if (!this.#candles.length) return;
    this.#ema50Series.setData(show50 ? this.#alignSeries(this.#candles, indicators?.ema50) : []);
    this.#ema200Series.setData(show200 ? this.#alignSeries(this.#candles, indicators?.ema200) : []);
  }
}
