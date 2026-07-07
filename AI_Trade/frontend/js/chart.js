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
  #mainEl;
  #rsiEl;
  #mainChart;
  #rsiChart;
  #candles;
  #candleSeries;
  #ema50Series;
  #ema200Series;
  #rsiSeries;
  #priceLines = [];
  #onClick;
  #showEma50 = true;
  #showEma200 = true;
  #showRsi = true;

  constructor(mainEl, rsiEl, { onClick } = {}) {
    this.#mainEl = mainEl;
    this.#rsiEl = rsiEl;
    this.#onClick = onClick;
  }

  mount() {
    const common = {
      layout: { background: { color: COLORS.bg }, textColor: COLORS.text },
      grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: COLORS.grid },
      timeScale: { borderColor: COLORS.grid, timeVisible: true, secondsVisible: false },
    };

    this.#mainChart = createChart(this.#mainEl, { ...common, width: this.#mainEl.clientWidth, height: this.#mainEl.clientHeight });
    this.#candleSeries = this.#mainChart.addCandlestickSeries({
      upColor: COLORS.up,
      downColor: COLORS.down,
      borderVisible: false,
      wickUpColor: COLORS.up,
      wickDownColor: COLORS.down,
    });
    this.#ema50Series = this.#mainChart.addLineSeries({ color: COLORS.ema50, lineWidth: 2, title: 'EMA50' });
    this.#ema200Series = this.#mainChart.addLineSeries({ color: COLORS.ema200, lineWidth: 2, title: 'EMA200' });

    this.#rsiChart = createChart(this.#rsiEl, { ...common, width: this.#rsiEl.clientWidth, height: this.#rsiEl.clientHeight });
    this.#rsiSeries = this.#rsiChart.addLineSeries({ color: COLORS.rsi, lineWidth: 2, title: 'RSI' });
    this.#rsiChart.priceScale('right').applyOptions({ scaleMargins: { top: 0.1, bottom: 0.1 } });

    const sync = (range) => {
      if (range) this.#rsiChart.timeScale().setVisibleLogicalRange(range);
    };
    this.#mainChart.timeScale().subscribeVisibleLogicalRangeChange(sync);

    this.#mainChart.subscribeClick((param) => this.#handleClick(param));
    this.#mainChart.subscribeCrosshairMove(() => {});

    window.addEventListener('resize', () => this.#resize());
  }

  #resize() {
    this.#mainChart.applyOptions({ width: this.#mainEl.clientWidth, height: this.#mainEl.clientHeight });
    this.#rsiChart.applyOptions({ width: this.#rsiEl.clientWidth, height: this.#rsiEl.clientHeight });
  }

  #handleClick(param) {
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
    const addLine = (price, color, title) => {
      if (price == null || Number.isNaN(price)) return;
      this.#priceLines.push(
        this.#candleSeries.createPriceLine({
          price,
          color,
          lineWidth: 2,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title,
        }),
      );
    };
    addLine(entry, COLORS.entry, direction === 'short' ? 'SELL' : 'BUY');
    addLine(sl, COLORS.sl, 'SL');
    addLine(tp, COLORS.tp, 'TP');
  }

  clearOverlay() {
    for (const line of this.#priceLines) this.#candleSeries.removePriceLine(line);
    this.#priceLines = [];
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
    // lightweight-charts uses UTCTimestamp (seconds)
    this.#mainChart.timeScale().setVisibleRange({
      from: unixSec - 3600 * 24 * 14,
      to: unixSec + 3600 * 24 * 7,
    });
  }
}
