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
  entry: '#3b82f6',
  sl: '#ef4444',
  tp: '#22c55e',
};

export class TradeChart {
  #wrapEl;
  #mainEl;
  #rsiEl;
  #dragLayer;
  #mainChart;
  #rsiChart;
  #candles;
  #candleSeries;
  #ema50Series;
  #ema200Series;
  #rsiSeries;
  /** @type {{ role: string, line: object, price: number, handle?: HTMLElement }[]} */
  #overlayLines = [];
  #onClick;
  #onLevelDrag;
  #showEma50 = true;
  #showEma200 = true;
  #showRsi = true;
  #dragState = null;
  #suppressClick = false;
  #priceFocus = null;
  #boundPointerMove;
  #boundPointerUp;

  constructor(mainEl, rsiEl, { onClick, onLevelDrag } = {}) {
    this.#wrapEl = mainEl.parentElement;
    this.#mainEl = mainEl;
    this.#rsiEl = rsiEl;
    this.#onClick = onClick;
    this.#onLevelDrag = onLevelDrag;
    this.#boundPointerMove = (e) => this.#onPointerMove(e);
    this.#boundPointerUp = (e) => this.#onPointerUp(e);
  }

  mount() {
    this.#dragLayer = document.createElement('div');
    this.#dragLayer.className = 'price-drag-layer';
    this.#wrapEl.appendChild(this.#dragLayer);

    const common = {
      layout: { background: { color: COLORS.bg }, textColor: COLORS.text },
      grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: COLORS.grid },
      timeScale: { borderColor: COLORS.grid, timeVisible: true, secondsVisible: false },
    };

    this.#mainChart = createChart(this.#mainEl, {
      ...common,
      width: this.#mainEl.clientWidth,
      height: this.#mainEl.clientHeight,
    });
    this.#candleSeries = this.#mainChart.addCandlestickSeries({
      upColor: COLORS.up,
      downColor: COLORS.down,
      borderVisible: false,
      wickUpColor: COLORS.up,
      wickDownColor: COLORS.down,
    });
    this.#ema50Series = this.#mainChart.addLineSeries({ color: COLORS.ema50, lineWidth: 2, title: 'EMA50' });
    this.#ema200Series = this.#mainChart.addLineSeries({ color: COLORS.ema200, lineWidth: 2, title: 'EMA200' });

    this.#rsiChart = createChart(this.#rsiEl, {
      ...common,
      width: this.#rsiEl.clientWidth,
      height: this.#rsiEl.clientHeight,
    });
    this.#rsiSeries = this.#rsiChart.addLineSeries({ color: COLORS.rsi, lineWidth: 2, title: 'RSI' });
    this.#rsiChart.priceScale('right').applyOptions({ scaleMargins: { top: 0.1, bottom: 0.1 } });

    const sync = (range) => {
      if (range) this.#rsiChart.timeScale().setVisibleLogicalRange(range);
      this.#updateHandlePositions();
    };
    this.#mainChart.timeScale().subscribeVisibleLogicalRangeChange(sync);

    this.#mainChart.subscribeClick((param) => this.#handleClick(param));

    window.addEventListener('pointermove', this.#boundPointerMove);
    window.addEventListener('pointerup', this.#boundPointerUp);
    window.addEventListener('pointercancel', this.#boundPointerUp);
    window.addEventListener('resize', () => this.#resize());
  }

  #resize() {
    this.#mainChart.applyOptions({ width: this.#mainEl.clientWidth, height: this.#mainEl.clientHeight });
    this.#rsiChart.applyOptions({ width: this.#rsiEl.clientWidth, height: this.#rsiEl.clientHeight });
    this.#updateHandlePositions();
  }

  #chartY(event) {
    const rect = this.#mainEl.getBoundingClientRect();
    return event.clientY - rect.top;
  }

  #setChartInteraction(enabled) {
    this.#mainChart.applyOptions({
      handleScroll: enabled,
      handleScale: enabled,
    });
  }

  #onHandlePointerDown(role, event) {
    if (!this.#overlayLines.length) return;
    this.#dragState = { role, moved: false, pointerId: event.pointerId };
    this.#setChartInteraction(false);
    this.#wrapEl.classList.add('dragging-level');
    event.preventDefault();
    event.stopPropagation();
  }

  #onPointerMove(event) {
    if (!this.#dragState || event.pointerId !== this.#dragState.pointerId) return;

    const y = this.#chartY(event);
    const price = this.#candleSeries.coordinateToPrice(y);
    if (price == null) return;

    this.#dragState.moved = true;
    this.#setLinePrice(this.#dragState.role, Number(price.toFixed(5)), true);
    event.preventDefault();
  }

  #onPointerUp(event) {
    if (!this.#dragState || event.pointerId !== this.#dragState.pointerId) return;

    if (this.#dragState.moved) {
      this.#suppressClick = true;
    }

    this.#dragState = null;
    this.#setChartInteraction(true);
    this.#wrapEl.classList.remove('dragging-level');
  }

  #setLinePrice(role, price, notify) {
    const item = this.#overlayLines.find((o) => o.role === role);
    if (!item || price == null || Number.isNaN(price)) return;
    item.price = price;
    item.line.applyOptions({ price });
    this.#updateHandlePositions();
    if (notify) {
      this.#onLevelDrag?.({ role, price });
    }
  }

  #createHandle(role, label) {
    const handle = document.createElement('div');
    handle.className = `price-drag-handle ${role}`;
    handle.dataset.label = label;
    handle.addEventListener('pointerdown', (e) => this.#onHandlePointerDown(role, e));
    this.#dragLayer.appendChild(handle);
    return handle;
  }

  #updateHandlePositions() {
    for (const item of this.#overlayLines) {
      if (!item.handle) continue;
      const y = this.#candleSeries.priceToCoordinate(item.price);
      if (y == null || Number.isNaN(y)) {
        item.handle.style.display = 'none';
        continue;
      }
      item.handle.style.display = 'block';
      item.handle.style.top = `${y}px`;
    }
  }

  #handleClick(param) {
    if (this.#suppressClick) {
      this.#suppressClick = false;
      return;
    }
    if (!param.point || !param.time || !this.#candles?.length) return;
    const price = this.#candleSeries.coordinateToPrice(param.point.y);
    const candle = this.#nearestCandle(param.time);
    if (!candle || price == null) return;
    this.#onClick?.({ time: candle.time, candle, price });
  }

  #nearestCandle(time) {
    if (!this.#candles?.length) return null;
    let best = this.#candles[0];
    let bestDiff = Math.abs(best.time - time);
    for (const c of this.#candles) {
      const d = Math.abs(c.time - time);
      if (d < bestDiff) {
        best = c;
        bestDiff = d;
      }
    }
    return best;
  }

  setData({ candles, indicators }) {
    this.#candles = candles;
    this.#candleSeries.setData(candles);
    this.#ema50Series.setData(this.#showEma50 ? indicators?.ema50 ?? [] : []);
    this.#ema200Series.setData(this.#showEma200 ? indicators?.ema200 ?? [] : []);
    this.#rsiSeries.setData(this.#showRsi ? indicators?.rsi14 ?? [] : []);
    if (!this.#priceFocus) {
      this.#mainChart.timeScale().fitContent();
      this.#rsiChart.timeScale().fitContent();
    }
    this.#updateHandlePositions();
  }

  #applyPriceFocus() {
    if (!this.#priceFocus) {
      this.#candleSeries.applyOptions({ autoscaleInfoProvider: undefined });
      this.#mainChart.priceScale('right').applyOptions({ autoScale: true });
      return;
    }
    const { min, max } = this.#priceFocus;
    this.#candleSeries.applyOptions({
      autoscaleInfoProvider: () => ({
        priceRange: { minValue: min, maxValue: max },
      }),
    });
    this.#mainChart.priceScale('right').applyOptions({ autoScale: true });
  }

  focusSetup({ time, entry, sl, tp }) {
    const prices = [entry, sl, tp].filter((p) => p != null && !Number.isNaN(Number(p))).map(Number);
    if (prices.length) {
      const minP = Math.min(...prices);
      const maxP = Math.max(...prices);
      const pad = Math.max((maxP - minP) * 0.4, 0.0015);
      this.#priceFocus = { min: minP - pad, max: maxP + pad };
      this.#applyPriceFocus();
    }

    if (time != null && this.#candles?.length) {
      const anchor = this.#nearestCandle(time)?.time ?? time;
      const from = anchor - 3600 * 24 * 5;
      const to = anchor + 3600 * 24 * 12;
      this.#mainChart.timeScale().setVisibleRange({ from, to });
      this.#rsiChart.timeScale().setVisibleRange({ from, to });
    }

    requestAnimationFrame(() => this.#updateHandlePositions());
  }

  clearPriceFocus() {
    this.#priceFocus = null;
    this.#applyPriceFocus();
  }

  setOverlay({ entry, sl, tp, direction }) {
    this.clearOverlay();
    const levels = [
      { role: 'entry', price: entry, color: COLORS.entry, title: direction === 'short' ? 'SELL' : 'BUY' },
      { role: 'sl', price: sl, color: COLORS.sl, title: 'SL' },
      { role: 'tp', price: tp, color: COLORS.tp, title: 'TP' },
    ];

    for (const lv of levels) {
      if (lv.price == null || lv.price === '' || Number.isNaN(Number(lv.price))) continue;
      const price = Number(lv.price);
      const line = this.#candleSeries.createPriceLine({
        price,
        color: lv.color,
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: lv.title,
      });
      const handle = this.#createHandle(lv.role, lv.title);
      this.#overlayLines.push({ role: lv.role, line, price, handle });
    }

    requestAnimationFrame(() => this.#updateHandlePositions());
  }

  clearOverlay() {
    for (const item of this.#overlayLines) {
      this.#candleSeries.removePriceLine(item.line);
      item.handle?.remove();
    }
    this.#overlayLines = [];
    this.#wrapEl?.classList.remove('dragging-level');
  }

  clearFocus() {
    this.clearPriceFocus();
  }

  toggleEma50(on) {
    this.#showEma50 = on;
    this.#ema50Series.applyOptions({ visible: on });
  }

  toggleEma200(on) {
    this.#showEma200 = on;
    this.#ema200Series.applyOptions({ visible: on });
  }

  toggleRsi(on) {
    this.#showRsi = on;
    this.#rsiEl.style.display = on ? 'block' : 'none';
    this.#resize();
  }

  scrollToTime(unixSec) {
    this.focusSetup({ time: unixSec, entry: null, sl: null, tp: null });
  }
}
