import { createChart, CrosshairMode, LineStyle } from '../vendor/lightweight-charts.mjs';

const COLORS = {
  bg: '#0b0f14',
  grid: '#1e2a38',
  text: '#8b9cb3',
  up: '#22c55e',
  down: '#ef4444',
  ema50: '#38bdf8',
  ema200: '#a78bfa',
  ema800: '#f97316',
  rsi: '#f59e0b',
  divergenceBull: '#22c55e',
  divergenceBear: '#ef4444',
};

const RSI_SCALE_ID = 'rsi';
const RIGHT_SCALE_WIDTH = 84;
const PANE_GAP = 0.03;

const RSI_BANDS = {
  low: [28, 32],
  mid: [48, 52],
  high: [68, 72],
};

const DEFAULT_VISIBLE_BARS = 320;

function isFiniteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

/**
 * Một chart Lightweight Charts duy nhất — giá + RSI dùng chung trục thời gian.
 * Tránh lệch khi pan/zoom (hai chart độc lập hay bị lệch ở vùng giá mới nhất).
 */
export class RsiZoneChart {
  #hostEl;
  #wrapEl;
  #bodyEl;
  #rsiPanel;
  #chart;
  #candles = [];
  #candleSeries;
  #ema50Series;
  #ema200Series;
  #ema800Series;
  #rsiSeries;
  #rsiBandLines = [];
  #priceDivergenceSeries = [];
  #rsiDivergenceSeries = [];
  #rsiData = [];
  #showEma50 = true;
  #showEma200 = true;
  #showEma800 = true;
  #showDivergences = true;
  #resizeObserver;
  #resizeTimer;
  #onCrosshair;
  #mounted = false;
  #hasInitialFit = false;
  #savedLogicalRange = null;
  #tradePriceLines = [];
  #selectedTradeId = null;

  constructor(hostEl, { wrapEl, bodyEl, rsiPanel, onCrosshair } = {}) {
    this.#hostEl = hostEl;
    this.#wrapEl = wrapEl ?? hostEl?.parentElement;
    this.#bodyEl = bodyEl ?? this.#wrapEl?.parentElement;
    this.#rsiPanel = rsiPanel;
    this.#onCrosshair = onCrosshair;
  }

  mount() {
    if (this.#mounted || !this.#hostEl) return;

    const width = this.#chartWidth();
    const height = this.#chartHeight();

    this.#chart = createChart(this.#hostEl, {
      layout: { background: { color: COLORS.bg }, textColor: COLORS.text },
      grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: {
        borderColor: COLORS.grid,
        minimumWidth: RIGHT_SCALE_WIDTH,
        autoScale: true,
      },
      leftPriceScale: { visible: false },
      timeScale: {
        borderColor: COLORS.grid,
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 6,
        barSpacing: 6,
        fixLeftEdge: false,
        fixRightEdge: false,
      },
      localization: { locale: 'en-US' },
      width,
      height,
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

    this.#candleSeries = this.#chart.addCandlestickSeries({
      upColor: COLORS.up,
      downColor: COLORS.down,
      borderVisible: false,
      wickUpColor: COLORS.up,
      wickDownColor: COLORS.down,
    });
    this.#ema50Series = this.#chart.addLineSeries({
      color: COLORS.ema50,
      lineWidth: 2,
      title: 'EMA50',
      priceLineVisible: false,
      lastValueVisible: false,
    });
    this.#ema200Series = this.#chart.addLineSeries({
      color: COLORS.ema200,
      lineWidth: 2,
      title: 'EMA200',
      priceLineVisible: false,
      lastValueVisible: false,
    });
    this.#ema800Series = this.#chart.addLineSeries({
      color: COLORS.ema800,
      lineWidth: 2,
      title: 'EMA800',
      priceLineVisible: false,
      lastValueVisible: false,
    });

    this.#rsiSeries = this.#chart.addLineSeries({
      color: COLORS.rsi,
      lineWidth: 2,
      title: 'RSI H4',
      priceScaleId: RSI_SCALE_ID,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    this.#chart.priceScale(RSI_SCALE_ID).applyOptions({
      scaleMargins: { top: 0.68, bottom: PANE_GAP },
      minimumWidth: RIGHT_SCALE_WIDTH,
      borderVisible: false,
    });
    this.#applyRsiScale();
    this.#drawRsiBands();
    this.#updatePaneMargins();

    this.#chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (range) this.#savedLogicalRange = range;
    });

    this.#chart.subscribeCrosshairMove((param) => this.#emitCrosshair(param));

    const observeEl = this.#bodyEl || this.#hostEl;
    this.#resizeObserver = new ResizeObserver(() => {
      clearTimeout(this.#resizeTimer);
      this.#resizeTimer = setTimeout(() => this.#resize(), 80);
    });
    this.#resizeObserver.observe(observeEl);
    if (this.#rsiPanel) this.#resizeObserver.observe(this.#rsiPanel);

    this.#mounted = true;
    requestAnimationFrame(() => this.#resize(true));
  }

  #chartWidth() {
    const bodyW = this.#bodyEl?.clientWidth ?? 0;
    const wrapW = this.#wrapEl?.clientWidth ?? 0;
    const hostW = this.#hostEl?.clientWidth ?? 0;
    return Math.max(bodyW, wrapW, hostW, 320);
  }

  #chartHeight() {
    const bodyH = this.#bodyEl?.clientHeight ?? 0;
    return Math.max(bodyH, this.#hostEl?.clientHeight ?? 0, 360);
  }

  /** Chia vùng dọc: giá trên, RSI dưới — khớp splitter UI. */
  #updatePaneMargins() {
    if (!this.#chart) return;
    const bodyH = this.#bodyEl?.clientHeight ?? 0;
    const rsiPanelH = this.#rsiPanel?.clientHeight ?? 240;
    const bottomFrac = bodyH > 0
      ? Math.min(0.58, Math.max(0.18, rsiPanelH / bodyH))
      : 0.32;
    const topFrac = 1 - bottomFrac;

    this.#chart.priceScale('right').applyOptions({
      scaleMargins: { top: PANE_GAP, bottom: bottomFrac + PANE_GAP },
    });
    this.#chart.priceScale(RSI_SCALE_ID).applyOptions({
      scaleMargins: { top: topFrac + PANE_GAP, bottom: PANE_GAP },
      minimumWidth: RIGHT_SCALE_WIDTH,
    });
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

  #emitCrosshair(param) {
    if (!param?.time || !this.#candles.length) {
      this.#onCrosshair?.(null);
      return;
    }
    const candle = this.#nearestCandle(param.time);
    const rsi = candle ? this.#rsiValueAt(candle.time) : null;
    this.#onCrosshair?.({ candle, rsi, time: candle?.time });
  }

  #rsiValueAt(time) {
    const exact = this.#rsiData.find((p) => p.time === time);
    if (exact) return exact.value;
    const candle = this.#nearestCandle(time);
    return candle ? this.#rsiData.find((p) => p.time === candle.time)?.value : null;
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

  #snapTime(time) {
    if (!isFiniteNumber(time)) return null;
    return this.#nearestCandle(time)?.time ?? time;
  }

  #alignRsiSeries(candles, points) {
    const byTime = new Map(
      (points || [])
        .filter((p) => isFiniteNumber(p?.time) && isFiniteNumber(p?.value))
        .map((p) => [p.time, p.value]),
    );
    let last = null;
    const out = [];
    for (const c of candles) {
      const v = byTime.get(c.time);
      if (v != null && !Number.isNaN(v)) {
        last = v;
        out.push({ time: c.time, value: v });
      } else if (last != null) {
        out.push({ time: c.time, value: last });
      } else {
        out.push({ time: c.time });
      }
    }
    return out;
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
      const v = byTime.get(c.time);
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
      this.#chart?.timeScale().getVisibleLogicalRange() ?? this.#savedLogicalRange,
    );
  }

  #setMainRange(range) {
    const safeRange = this.#normalizeRange(range);
    if (!safeRange || !this.#chart) return;
    this.#chart.timeScale().setVisibleLogicalRange(safeRange);
    this.#savedLogicalRange = safeRange;
  }

  #resize(force = false) {
    const width = this.#chartWidth();
    const height = this.#chartHeight();
    if (width <= 0 || height <= 0) return;
    this.#chart?.applyOptions({ width, height });
    this.#updatePaneMargins();
    if (force && this.#savedLogicalRange) {
      this.#setMainRange(this.#savedLogicalRange);
    }
  }

  setData({ candles, indicators, divergences }, { fit = false } = {}) {
    const range = this.#captureRange();
    const shouldShowLatest = !fit && !this.#hasInitialFit;

    this.#candles = this.#sanitizeCandles(candles);
    this.#candleSeries.setData(this.#candles);
    const ema50 = this.#alignSeries(this.#candles, indicators?.ema50);
    const ema200 = this.#alignSeries(this.#candles, indicators?.ema200);
    const ema800 = this.#alignSeries(this.#candles, indicators?.ema800);
    const rsiData = this.#alignRsiSeries(this.#candles, indicators?.rsi14_h4);
    this.#rsiData = rsiData.filter((p) => isFiniteNumber(p.value));
    this.#ema50Series.setData(this.#showEma50 ? ema50 : []);
    this.#ema200Series.setData(this.#showEma200 ? ema200 : []);
    this.#ema800Series.setData(this.#showEma800 ? ema800 : []);
    this.#rsiSeries.setData(rsiData);
    this.setDivergences(divergences, { show: this.#showDivergences });

    requestAnimationFrame(() => {
      this.#resize(true);
      if (fit) {
        this.#chart.timeScale().fitContent();
        this.#hasInitialFit = true;
        this.#savedLogicalRange = this.#captureRange();
      } else if (shouldShowLatest) {
        this.scrollToLatest(DEFAULT_VISIBLE_BARS);
        this.#hasInitialFit = true;
      } else if (range) {
        this.#setMainRange(range);
      }
    });
  }

  setMarkers(markers) {
    const cleanMarkers = (markers || [])
      .filter((marker) => isFiniteNumber(marker?.time))
      .sort((a, b) => a.time - b.time);
    this.#candleSeries.setMarkers(cleanMarkers);
  }

  setDivergences(divergences, { show = true } = {}) {
    for (const series of this.#priceDivergenceSeries) {
      try { this.#chart.removeSeries(series); } catch { /* */ }
    }
    for (const series of this.#rsiDivergenceSeries) {
      try { this.#chart.removeSeries(series); } catch { /* */ }
    }
    this.#priceDivergenceSeries = [];
    this.#rsiDivergenceSeries = [];
    this.#showDivergences = show;
    if (!show || !divergences?.length) return;

    for (const d of divergences) {
      if (
        !isFiniteNumber(d?.start_time)
        || !isFiniteNumber(d?.end_time)
        || !isFiniteNumber(d?.rsi_start)
        || !isFiniteNumber(d?.rsi_end)
        || !isFiniteNumber(d?.price_start)
        || !isFiniteNumber(d?.price_end)
      ) {
        continue;
      }
      const startTime = this.#snapTime(d.start_time);
      const endTime = this.#snapTime(d.end_time);
      if (startTime == null || endTime == null) continue;
      const color = d.type === 'bullish' ? COLORS.divergenceBull : COLORS.divergenceBear;

      const priceSeries = this.#chart.addLineSeries({
        color,
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      priceSeries.setData([
        { time: startTime, value: d.price_start },
        { time: endTime, value: d.price_end },
      ]);
      this.#priceDivergenceSeries.push(priceSeries);

      const rsiSeries = this.#chart.addLineSeries({
        color,
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        priceScaleId: RSI_SCALE_ID,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      rsiSeries.setData([
        { time: startTime, value: d.rsi_start },
        { time: endTime, value: d.rsi_end },
      ]);
      this.#rsiDivergenceSeries.push(rsiSeries);
    }
  }

  setTradeMarkers(trades, { show = true } = {}) {
    if (!show || !trades?.length) {
      this.setMarkers([]);
      return;
    }
    const markers = [];
    for (const t of trades) {
      const win = t.result === 'win';
      const isLong = t.direction !== 'short';
      markers.push({
        time: t.entry_time,
        position: isLong ? 'belowBar' : 'aboveBar',
        color: win ? '#22c55e' : '#ef4444',
        shape: isLong ? 'arrowUp' : 'arrowDown',
        text: `#${t.id} ${isLong ? 'L' : 'S'}`,
      });
      markers.push({
        time: t.exit_time,
        position: isLong ? 'aboveBar' : 'belowBar',
        color: win ? '#4ade80' : '#f87171',
        shape: 'circle',
        text: ['tp', 'rsi_tp'].includes(t.exit_reason) ? 'TP' : t.exit_reason === 'sl' ? 'SL' : 'X',
      });
    }
    this.setMarkers(markers);
  }

  #clearTradePriceLines() {
    for (const line of this.#tradePriceLines) {
      try { this.#candleSeries.removePriceLine(line); } catch { /* */ }
    }
    this.#tradePriceLines = [];
  }

  highlightTrade(trade) {
    this.#clearTradePriceLines();
    if (!trade) {
      this.#selectedTradeId = null;
      return;
    }
    this.#selectedTradeId = trade.id;
    const specs = [
      { price: trade.entry_price, color: '#38bdf8', title: 'Entry' },
      { price: trade.sl_price, color: '#ef4444', title: 'SL' },
      { price: trade.tp_price, color: '#22c55e', title: 'TP' },
    ];
    for (const spec of specs) {
      if (!isFiniteNumber(spec.price)) continue;
      this.#tradePriceLines.push(
        this.#candleSeries.createPriceLine({
          price: spec.price,
          color: spec.color,
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: spec.title,
        }),
      );
    }
    this.focusTradeRange(trade.entry_time, trade.exit_time, { center: 'entry' });
  }

  focusTradeRange(entryTime, exitTime, { center = 'entry' } = {}) {
    if (!this.#candles.length) return;
    if (!isFiniteNumber(entryTime)) return;
    const entryIdx = this.#candles.findIndex((c) => c.time === entryTime);
    const exitIdx = isFiniteNumber(exitTime)
      ? this.#candles.findIndex((c) => c.time === exitTime)
      : -1;
    const fromIdx = entryIdx >= 0 ? entryIdx : this.#indexNearest(entryTime);
    const toIdx = exitIdx >= 0 ? exitIdx : fromIdx;
    if (fromIdx < 0) return;

    if (center === 'entry') {
      const span = Math.max(80, toIdx - fromIdx + 40);
      this.#setMainRange({
        from: Math.max(0, fromIdx - Math.round(span * 0.2)),
        to: Math.min(this.#candles.length - 1, fromIdx + span),
      });
      return;
    }

    this.#setMainRange({
      from: Math.max(0, fromIdx - 30),
      to: Math.min(this.#candles.length - 1, Math.max(toIdx, fromIdx) + 30),
    });
  }

  #indexNearest(time) {
    if (!this.#candles.length) return -1;
    let best = 0;
    let diff = Math.abs(this.#candles[0].time - time);
    for (let i = 1; i < this.#candles.length; i += 1) {
      const d = Math.abs(this.#candles[i].time - time);
      if (d < diff) { best = i; diff = d; }
    }
    return best;
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
    this.#chart.timeScale().fitContent();
    this.#savedLogicalRange = this.#captureRange();
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

  applyEmaVisibility(show50, show200, show800, indicators) {
    this.#showEma50 = show50;
    this.#showEma200 = show200;
    this.#showEma800 = show800;
    if (!this.#candles.length) return;
    this.#ema50Series.setData(show50 ? this.#alignSeries(this.#candles, indicators?.ema50) : []);
    this.#ema200Series.setData(show200 ? this.#alignSeries(this.#candles, indicators?.ema200) : []);
    this.#ema800Series.setData(show800 ? this.#alignSeries(this.#candles, indicators?.ema800) : []);
  }

  resize() {
    this.#resize(true);
  }
}
