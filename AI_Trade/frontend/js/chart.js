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

const HIT_PX = 12;

export class TradeChart {
  #mainEl;
  #rsiEl;
  #mainChart;
  #rsiChart;
  #candles;
  #candleSeries;
  #ema50Series;
  #ema200Series;
  #rsiSeries;
  /** @type {{ role: string, line: object, price: number }[]} */
  #overlayLines = [];
  #onClick;
  #onLevelDrag;
  #showEma50 = true;
  #showEma200 = true;
  #showRsi = true;
  #dragState = null;
  #suppressClick = false;
  #boundPointerDown;
  #boundPointerMove;
  #boundPointerUp;

  constructor(mainEl, rsiEl, { onClick, onLevelDrag } = {}) {
    this.#mainEl = mainEl;
    this.#rsiEl = rsiEl;
    this.#onClick = onClick;
    this.#onLevelDrag = onLevelDrag;
    this.#boundPointerDown = (e) => this.#onPointerDown(e);
    this.#boundPointerMove = (e) => this.#onPointerMove(e);
    this.#boundPointerUp = (e) => this.#onPointerUp(e);
  }

  mount() {
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
    };
    this.#mainChart.timeScale().subscribeVisibleLogicalRangeChange(sync);

    this.#mainChart.subscribeClick((param) => this.#handleClick(param));

    this.#mainEl.addEventListener('pointerdown', this.#boundPointerDown);
    this.#mainEl.addEventListener('pointermove', this.#boundPointerMove);
    this.#mainEl.addEventListener('pointerup', this.#boundPointerUp);
    this.#mainEl.addEventListener('pointercancel', this.#boundPointerUp);

    window.addEventListener('resize', () => this.#resize());
  }

  #resize() {
    this.#mainChart.applyOptions({ width: this.#mainEl.clientWidth, height: this.#mainEl.clientHeight });
    this.#rsiChart.applyOptions({ width: this.#rsiEl.clientWidth, height: this.#rsiEl.clientHeight });
  }

  #localY(event) {
    const rect = this.#mainEl.getBoundingClientRect();
    return event.clientY - rect.top;
  }

  #hitTestLine(y) {
    let best = null;
    let bestDist = HIT_PX + 1;
    for (const item of this.#overlayLines) {
      const lineY = this.#candleSeries.priceToCoordinate(item.price);
      if (lineY == null) continue;
      const dist = Math.abs(lineY - y);
      if (dist <= HIT_PX && dist < bestDist) {
        best = item.role;
        bestDist = dist;
      }
    }
    return best;
  }

  #setChartInteraction(enabled) {
    this.#mainChart.applyOptions({
      handleScroll: enabled,
      handleScale: enabled,
    });
  }

  #onPointerDown(event) {
    if (!this.#overlayLines.length) return;
    const role = this.#hitTestLine(this.#localY(event));
    if (!role) return;

    this.#dragState = { role, moved: false };
    this.#mainEl.setPointerCapture(event.pointerId);
    this.#setChartInteraction(false);
    this.#mainEl.classList.add('dragging-level');
    event.preventDefault();
    event.stopPropagation();
  }

  #onPointerMove(event) {
    if (!this.#dragState) {
      const role = this.#hitTestLine(this.#localY(event));
      this.#mainEl.classList.toggle('can-drag-level', Boolean(role));
      return;
    }

    const y = this.#localY(event);
    const price = this.#candleSeries.coordinateToPrice(y);
    if (price == null) return;

    this.#dragState.moved = true;
    this.#setLinePrice(this.#dragState.role, Number(price.toFixed(5)), true);
    event.preventDefault();
  }

  #onPointerUp(event) {
    if (!this.#dragState) return;

    if (this.#dragState.moved) {
      this.#suppressClick = true;
    }

    this.#dragState = null;
    this.#setChartInteraction(true);
    this.#mainEl.classList.remove('dragging-level');
    if (this.#mainEl.hasPointerCapture(event.pointerId)) {
      this.#mainEl.releasePointerCapture(event.pointerId);
    }
  }

  #setLinePrice(role, price, notify) {
    const item = this.#overlayLines.find((o) => o.role === role);
    if (!item || price == null || Number.isNaN(price)) return;
    item.price = price;
    item.line.applyOptions({ price });
    if (notify) {
      this.#onLevelDrag?.({ role, price });
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
    this.#mainChart.timeScale().fitContent();
    this.#rsiChart.timeScale().fitContent();
  }

  setOverlay({ entry, sl, tp, direction }) {
    this.clearOverlay();
    const levels = [
      { role: 'entry', price: entry, color: COLORS.entry, title: direction === 'short' ? 'SELL' : 'BUY' },
      { role: 'sl', price: sl, color: COLORS.sl, title: 'SL' },
      { role: 'tp', price: tp, color: COLORS.tp, title: 'TP' },
    ];

    for (const lv of levels) {
      if (lv.price == null || Number.isNaN(Number(lv.price))) continue;
      const price = Number(lv.price);
      const line = this.#candleSeries.createPriceLine({
        price,
        color: lv.color,
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: lv.title,
      });
      this.#overlayLines.push({ role: lv.role, line, price });
    }
  }

  clearOverlay() {
    for (const item of this.#overlayLines) {
      this.#candleSeries.removePriceLine(item.line);
    }
    this.#overlayLines = [];
    this.#mainEl.classList.remove('can-drag-level', 'dragging-level');
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
    this.#mainChart.timeScale().scrollToPosition(-20, false);
    this.#mainChart.timeScale().setVisibleRange({
      from: unixSec - 3600 * 24 * 14,
      to: unixSec + 3600 * 24 * 7,
    });
  }
}
