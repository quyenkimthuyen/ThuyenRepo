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

const LEVEL_STYLE = {
  entry: { color: COLORS.entry, tag: 'ENTRY' },
  sl: { color: COLORS.sl, tag: 'STOP LOSS' },
  tp: { color: COLORS.tp, tag: 'TAKE PROFIT' },
};

/** Đồng bộ độ rộng price scale phải — tránh lệch cột nến giữa chart giá và RSI */
const RIGHT_SCALE_MIN_WIDTH = 78;

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
  /** @type {object[]} */
  #rsiBandLines = [];
  /** @type {{ low: number[], mid: number[], high: number[] } | null} */
  #rsiBands = null;
  /** @type {{ role: string, series: object, price: number, row?: HTMLElement }[]} */
  #overlayLines = [];
  #overlayStartTime = null;
  #overlayDirection = 'long';
  #overlayInteractive = true;
  #onClick;
  #onLevelDrag;
  #showEma50 = true;
  #showEma200 = true;
  #showRsi = true;
  /** @type {object[]} */
  #baseMarkers = [];
  /** @type {object[]} */
  #importantBarsData = [];
  /** @type {object[]} */
  #importantMarkers = [];
  /** @type {object[]} */
  #sequenceMarkers = [];
  #selectedBarTime = null;
  #onImportantBarHover;
  #dragState = null;
  #suppressClick = false;
  #priceFocus = null;
  #pendingFocus = null;
  #boundPointerMove;
  #boundPointerUp;
  #resizeObserver = null;
  #mounted = false;
  #syncingTimeScale = false;
  /** @type {{ time: number, value: number }[]} */
  #rsiData = [];
  #bodyEl = null;

  constructor(mainEl, rsiEl, { onClick, onLevelDrag, onImportantBarHover } = {}) {
    this.#wrapEl = mainEl.parentElement;
    this.#mainEl = mainEl;
    this.#rsiEl = rsiEl;
    this.#onClick = onClick;
    this.#onLevelDrag = onLevelDrag;
    this.#onImportantBarHover = onImportantBarHover;
    this.#boundPointerMove = (e) => this.#onPointerMove(e);
    this.#boundPointerUp = (e) => this.#onPointerUp(e);
  }

  mount() {
    if (this.#mounted) return;
    if (!this.#mainEl || !this.#rsiEl) {
      throw new Error('Chart container not found (#chartMain / #chartRsi)');
    }
    if (!this.#wrapEl) this.#wrapEl = this.#mainEl;

    this.#dragLayer = document.createElement('div');
    this.#dragLayer.className = 'price-drag-layer';
    (this.#wrapEl.classList?.contains('chart-wrap') ? this.#wrapEl : this.#mainEl).appendChild(
      this.#dragLayer,
    );

    const { width, height } = this.#mainSize();
    const priceScaleOpts = {
      borderColor: COLORS.grid,
      minimumWidth: RIGHT_SCALE_MIN_WIDTH,
    };
    const common = {
      layout: { background: { color: COLORS.bg }, textColor: COLORS.text },
      grid: { vertLines: { color: COLORS.grid }, horzLines: { color: COLORS.grid } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: priceScaleOpts,
      leftPriceScale: { visible: false },
      timeScale: { borderColor: COLORS.grid, timeVisible: true, secondsVisible: false },
      localization: { locale: 'en-US' },
    };

    const timeScaleOpts = {
      borderColor: COLORS.grid,
      timeVisible: true,
      secondsVisible: false,
      rightOffset: 6,
      barSpacing: 6,
      fixLeftEdge: false,
      fixRightEdge: false,
    };

    this.#bodyEl = this.#mainEl.closest('#chartBody');

    this.#mainChart = createChart(this.#mainEl, { ...common, width, height, timeScale: timeScaleOpts });
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
      width: this.#rsiEl.clientWidth || width,
      height: this.#rsiEl.clientHeight || 220,
      timeScale: {
        ...timeScaleOpts,
        timeVisible: false,
        borderVisible: false,
      },
      handleScroll: {
        mouseWheel: false,
        pressedMouseMove: false,
        horzTouchDrag: false,
      },
      handleScale: {
        mouseWheel: false,
        pinch: false,
        axisPressedMouseMove: { time: false, price: true },
      },
    });
    this.#rsiSeries = this.#rsiChart.addLineSeries({ color: COLORS.rsi, lineWidth: 2, title: 'RSI H4' });
    this.#rsiChart.priceScale('right').applyOptions({ scaleMargins: { top: 0.08, bottom: 0.08 } });
    this.#applyRsiScale();

    const onLogicalRange = (range) => {
      if (this.#syncingTimeScale || !range) return;
      this.#syncingTimeScale = true;
      this.#rsiChart.timeScale().setVisibleLogicalRange(range);
      this.#syncingTimeScale = false;
      this.#syncPriceScaleWidth();
      this.#refreshOverlayLines();
      this.#refreshOverlayGeometry();
    };
    this.#mainChart.timeScale().subscribeVisibleLogicalRangeChange(onLogicalRange);

    this.#mainChart.subscribeClick((param) => this.#handleClick(param));
    this.#mainChart.subscribeCrosshairMove((param) => {
      this.#handleCrosshair(param);
      this.#syncCrosshairToRsi(param);
    });
    window.addEventListener('pointermove', this.#boundPointerMove);
    window.addEventListener('pointerup', this.#boundPointerUp);
    window.addEventListener('pointercancel', this.#boundPointerUp);

    const observeEl = this.#bodyEl || (this.#wrapEl?.classList?.contains('chart-wrap') ? this.#wrapEl : this.#mainEl);
    this.#resizeObserver = new ResizeObserver(() => this.#resize());
    this.#resizeObserver.observe(observeEl);
    if (this.#bodyEl && observeEl !== this.#bodyEl) {
      this.#resizeObserver.observe(this.#wrapEl);
    }
    this.#mounted = true;
    requestAnimationFrame(() => this.#resize());
  }

  isMounted() {
    return this.#mounted;
  }

  #chartWidth() {
    const bodyW = this.#bodyEl?.clientWidth ?? 0;
    const mainW = this.#mainEl?.clientWidth ?? 0;
    const rsiW = this.#rsiEl?.clientWidth ?? 0;
    return Math.max(bodyW, mainW, rsiW, 320);
  }

  #mainSize() {
    const wrapH = this.#wrapEl?.clientHeight ?? 0;
    const wrapW = this.#chartWidth();
    return {
      width: wrapW,
      height: Math.max(this.#mainEl.clientHeight, wrapH, 280),
    };
  }

  #resize() {
    const width = this.#chartWidth();
    const mainHeight = Math.max(this.#mainEl.clientHeight, this.#wrapEl?.clientHeight ?? 0, 280);
    const rsiHeight = Math.max(this.#rsiEl.clientHeight || 0, 80);
    if (width <= 0 || mainHeight <= 0) return;
    this.#mainChart?.applyOptions({ width, height: mainHeight });
    this.#rsiChart?.applyOptions({ width, height: rsiHeight });
    this.#syncPriceScaleWidth();
    if (this.#showRsi) this.#syncRsiTimeScale();
    this.#refreshOverlayGeometry();
  }

  #syncPriceScaleWidth() {
    if (!this.#mainChart || !this.#rsiChart) return;
    const mainScale = this.#mainChart.priceScale('right');
    const rsiScale = this.#rsiChart.priceScale('right');
    const width = Math.max(
      mainScale.width(),
      rsiScale.width(),
      RIGHT_SCALE_MIN_WIDTH,
    );
    mainScale.applyOptions({ minimumWidth: width });
    rsiScale.applyOptions({ minimumWidth: width });
  }

  #syncCrosshairToRsi(param) {
    if (!this.#showRsi || !this.#rsiChart) return;
    if (!param?.time) {
      this.#rsiChart.clearCrosshairPosition();
      return;
    }
    const candle = this.#nearestCandle(param.time);
    const time = candle?.time ?? param.time;
    let value = param.seriesData?.get(this.#rsiSeries)?.value;
    if (value == null) value = this.#rsiValueAtTime(time);
    if (value == null) {
      this.#rsiChart.clearCrosshairPosition();
      return;
    }
    this.#rsiChart.setCrosshairPosition(value, time, this.#rsiSeries);
  }

  #rsiValueAtTime(time) {
    const point = this.#rsiData.find((p) => p.time === time);
    return point?.value ?? null;
  }

  #chartY(event) {
    return event.clientY - this.#mainEl.getBoundingClientRect().top;
  }

  #setChartInteraction(enabled) {
    this.#mainChart.applyOptions({ handleScroll: enabled, handleScale: enabled });
  }

  #lineEndTime(startTime) {
    const idx = this.#candleIndex(startTime);
    if (idx < 0) return startTime;
    let endIdx = Math.min(this.#candles.length - 1, idx + 56);
    const vis = this.#mainChart.timeScale().getVisibleLogicalRange();
    if (vis) endIdx = Math.max(endIdx, Math.min(this.#candles.length - 1, Math.floor(vis.to)));
    return this.#candles[endIdx].time;
  }

  #createLevelSeries(color) {
    return this.#mainChart.addLineSeries({
      color,
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      lineType: 0,
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      pointMarkersVisible: false,
    });
  }

  #setLevelLineData(series, startTime, price) {
    if (!series || startTime == null || price == null) return;
    const end = this.#lineEndTime(startTime);
    series.setData([
      { time: startTime, value: price },
      { time: end, value: price },
    ]);
  }

  #formatPrice(price) {
    return Number(price).toFixed(5);
  }

  #entryTag() {
    return this.#overlayDirection === 'short' ? 'SELL' : 'BUY';
  }

  #levelLabel(role, price) {
    if (role === 'entry') return `${this.#entryTag()}  ${this.#formatPrice(price)}`;
    const tag = LEVEL_STYLE[role]?.tag ?? role.toUpperCase();
    return `${tag}  ${this.#formatPrice(price)}`;
  }

  #createLevelRow(role, price) {
    const style = LEVEL_STYLE[role];
    const row = document.createElement('div');
    row.className = `level-row ${role}`;
    row.innerHTML = `
      <div class="level-label">${this.#levelLabel(role, price)}</div>
      <div class="level-drag-zone" title="Kéo để chỉnh giá"></div>
    `;
    row.querySelector('.level-drag-zone').addEventListener('pointerdown', (e) => {
      this.#onHandlePointerDown(role, e);
    });
    this.#dragLayer.appendChild(row);
    return row;
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
    const price = this.#candleSeries.coordinateToPrice(this.#chartY(event));
    if (price == null) return;
    this.#dragState.moved = true;
    this.#setLinePrice(this.#dragState.role, Number(price.toFixed(5)), true);
    event.preventDefault();
  }

  #onPointerUp(event) {
    if (!this.#dragState || event.pointerId !== this.#dragState.pointerId) return;
    if (this.#dragState.moved) this.#suppressClick = true;
    this.#dragState = null;
    this.#setChartInteraction(true);
    this.#wrapEl.classList.remove('dragging-level');
  }

  #setLinePrice(role, price, notify) {
    const item = this.#overlayLines.find((o) => o.role === role);
    if (!item || price == null || Number.isNaN(price)) return;
    item.price = price;
    this.#setLevelLineData(item.series, this.#overlayStartTime, price);
    const label = item.row?.querySelector('.level-label');
    if (label) label.textContent = this.#levelLabel(role, price);
    this.#refreshOverlayGeometry();
    if (notify) this.#onLevelDrag?.({ role, price });
  }

  #refreshOverlayLines() {
    if (!this.#overlayStartTime) return;
    for (const item of this.#overlayLines) {
      this.#setLevelLineData(item.series, this.#overlayStartTime, item.price);
    }
  }

  #refreshOverlayGeometry() {
    if (!this.#overlayStartTime || !this.#overlayLines.length) return;
    if (!this.#overlayInteractive) return;
    const startX = this.#mainChart.timeScale().timeToCoordinate(this.#overlayStartTime);
    const endX = this.#mainEl.clientWidth - 8;
    if (startX == null || Number.isNaN(startX)) return;

    for (const item of this.#overlayLines) {
      const y = this.#candleSeries.priceToCoordinate(item.price);
      if (!item.row || y == null || Number.isNaN(y)) {
        item.row?.classList.add('hidden');
        continue;
      }
      item.row.classList.remove('hidden');
      const left = Math.max(0, Math.min(startX, endX - 80));
      const width = Math.max(40, endX - left);
      item.row.style.top = `${y}px`;
      item.row.style.left = `${left}px`;
      item.row.style.width = `${width}px`;
    }
  }

  #setEntryMarker() {
    if (!this.#overlayStartTime) {
      this.#candleSeries.setMarkers([]);
      return;
    }
    const isLong = this.#overlayDirection === 'long';
    this.#candleSeries.setMarkers([
      {
        time: this.#overlayStartTime,
        position: isLong ? 'belowBar' : 'aboveBar',
        color: COLORS.entry,
        shape: isLong ? 'arrowUp' : 'arrowDown',
        text: this.#entryTag(),
      },
    ]);
  }

  #handleCrosshair(param) {
    if (!param?.time || !this.#importantBarsData?.length) {
      this.#onImportantBarHover?.(null);
      return;
    }
    const bar = this.#findImportantBar(param.time);
    this.#onImportantBarHover?.(bar);
  }

  #findImportantBar(time) {
    const candle = this.#nearestCandle(time);
    if (!candle) return null;
    return this.#importantBarsData.find((b) => b.time === candle.time) || null;
  }

  setSelectedImportantBar(time) {
    this.#selectedBarTime = time ?? null;
    this.#refreshImportantMarkers();
  }

  #refreshImportantMarkers() {
    if (!this.#importantBarsData?.length) return;
    this.showImportantBars(this.#importantBarsData);
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

  #candleIndex(time) {
    if (!this.#candles?.length || time == null) return -1;
    const anchor = this.#nearestCandle(time)?.time ?? time;
    let idx = this.#candles.findIndex((c) => c.time === anchor);
    if (idx >= 0) return idx;
    for (let i = 0; i < this.#candles.length; i++) {
      if (this.#candles[i].time >= anchor) return i;
    }
    return this.#candles.length - 1;
  }

  #alignSeriesToCandles(candles, points, { forwardFill = false } = {}) {
    if (!candles?.length) return [];
    const byTime = new Map((points ?? []).map((p) => [p.time, p.value]));
    let last = null;
    const out = [];
    for (const c of candles) {
      let value = byTime.get(c.time);
      if (value != null && !Number.isNaN(value)) {
        last = value;
        out.push({ time: c.time, value });
      } else if (forwardFill && last != null) {
        out.push({ time: c.time, value: last });
      } else {
        out.push({ time: c.time });
      }
    }
    return out;
  }

  #applyRsiScale() {
    this.#rsiSeries.applyOptions({
      autoscaleInfoProvider: () => ({
        priceRange: { minValue: 0, maxValue: 100 },
      }),
    });
    this.#rsiChart.priceScale('right').applyOptions({ autoScale: true });
  }

  #refreshRsiBandLines() {
    if (!this.#rsiSeries) return;
    for (const line of this.#rsiBandLines) {
      try {
        this.#rsiSeries.removePriceLine(line);
      } catch {
        /* ignore */
      }
    }
    this.#rsiBandLines = [];
    const bands = this.#rsiBands;
    if (!bands || !this.#showRsi) return;

    const specs = [
      { range: bands.low, color: 'rgba(239, 68, 68, 0.85)', title: '30' },
      { range: bands.mid, color: 'rgba(56, 189, 248, 0.9)', title: '50' },
      { range: bands.high, color: 'rgba(34, 197, 94, 0.85)', title: '70' },
    ];
    for (const spec of specs) {
      const [lo, hi] = spec.range || [];
      for (const price of [lo, hi]) {
        if (price == null || Number.isNaN(Number(price))) continue;
        this.#rsiBandLines.push(
          this.#rsiSeries.createPriceLine({
            price: Number(price),
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

  setRsiBands(bands) {
    this.#rsiBands = bands || null;
    this.#refreshRsiBandLines();
    this.#applyRsiScale();
  }

  clearRsiBands() {
    this.#rsiBands = null;
    this.#refreshRsiBandLines();
    this.#applyRsiScale();
  }

  getRsiBands() {
    return this.#rsiBands;
  }

  #syncRsiTimeScale() {
    if (!this.#mainChart || !this.#rsiChart) return;
    const logical = this.#mainChart.timeScale().getVisibleLogicalRange();
    if (!logical) return;
    this.#syncingTimeScale = true;
    this.#rsiChart.timeScale().setVisibleLogicalRange(logical);
    this.#syncingTimeScale = false;
    this.#syncPriceScaleWidth();
  }

  setData({ candles, indicators }) {
    this.#candles = candles;
    this.#candleSeries.setData(candles);
    const ema50 = this.#alignSeriesToCandles(candles, indicators?.ema50);
    const ema200 = this.#alignSeriesToCandles(candles, indicators?.ema200);
    const rsiRaw = indicators?.rsi14_h4?.length ? indicators.rsi14_h4 : indicators?.rsi14;
    const rsiData = this.#alignSeriesToCandles(candles, rsiRaw, { forwardFill: true });
    this.#rsiData = rsiData.filter((p) => p.value != null && !Number.isNaN(p.value));
    this.#ema50Series.setData(this.#showEma50 ? ema50 : []);
    this.#ema200Series.setData(this.#showEma200 ? ema200 : []);
    this.#rsiSeries.setData(this.#showRsi ? rsiData : []);
    this.#resize();

    if (this.#pendingFocus) {
      const pending = this.#pendingFocus;
      this.#pendingFocus = null;
      this.focusSetup(pending);
    } else if (!this.#priceFocus) {
      this.#mainChart.timeScale().fitContent();
      this.#syncRsiTimeScale();
    }
    this.#refreshOverlayLines();
    this.#refreshOverlayGeometry();
  }

  #applyPriceFocus() {
    if (!this.#priceFocus) {
      this.#candleSeries.applyOptions({ autoscaleInfoProvider: undefined });
      this.#mainChart.priceScale('right').applyOptions({ autoScale: true });
      return;
    }
    const { min, max } = this.#priceFocus;
    this.#candleSeries.applyOptions({
      autoscaleInfoProvider: () => ({ priceRange: { minValue: min, maxValue: max } }),
    });
    this.#mainChart.priceScale('right').applyOptions({ autoScale: true });
  }

  focusSetup({ time, entry, sl, tp }) {
    if (!this.#candles?.length) {
      this.#pendingFocus = { time, entry, sl, tp };
      return;
    }

    const prices = [entry, sl, tp].filter((p) => p != null && !Number.isNaN(Number(p))).map(Number);
    if (prices.length) {
      const minP = Math.min(...prices);
      const maxP = Math.max(...prices);
      const pad = Math.max((maxP - minP) * 0.5, 0.0025);
      this.#priceFocus = { min: minP - pad, max: maxP + pad };
      this.#applyPriceFocus();
    }

    if (time != null) {
      const anchor = this.#nearestCandle(time)?.time ?? time;
      const idx = this.#candleIndex(anchor);
      const half = 50;
      const range = {
        from: Math.max(0, idx - half),
        to: Math.min(this.#candles.length - 1, idx + half),
      };
      this.#mainChart.timeScale().setVisibleLogicalRange(range);
      this.#syncRsiTimeScale();
    }

    requestAnimationFrame(() => {
      this.#refreshOverlayLines();
      this.#refreshOverlayGeometry();
      this.#mainChart.priceScale('right').applyOptions({ autoScale: true });
    });
  }

  clearPriceFocus() {
    this.#priceFocus = null;
    this.#pendingFocus = null;
    this.#applyPriceFocus();
  }

  updateLevelPrices({ entry, sl, tp }) {
    if (entry != null && !Number.isNaN(Number(entry))) {
      this.#setLinePrice('entry', Number(entry), false);
    }
    if (sl != null && !Number.isNaN(Number(sl))) {
      this.#setLinePrice('sl', Number(sl), false);
    }
    if (tp != null && !Number.isNaN(Number(tp))) {
      this.#setLinePrice('tp', Number(tp), false);
    }
  }

  hasOverlay() {
    return this.#overlayLines.length > 0;
  }

  setOverlay({ time, entry, sl, tp, direction, interactive = true }) {
    this.clearOverlay();

    const startTime = time != null ? this.#nearestCandle(time)?.time ?? time : null;
    this.#overlayStartTime = startTime;
    this.#overlayDirection = direction || 'long';
    this.#overlayInteractive = interactive;

    const levels = [
      { role: 'entry', price: entry },
      { role: 'sl', price: sl },
      { role: 'tp', price: tp },
    ];

    for (const lv of levels) {
      if (lv.price == null || lv.price === '' || Number.isNaN(Number(lv.price)) || !startTime) continue;
      const price = Number(lv.price);
      const color = LEVEL_STYLE[lv.role].color;
      const series = this.#createLevelSeries(color);
      this.#setLevelLineData(series, startTime, price);
      const row = interactive ? this.#createLevelRow(lv.role, price) : null;
      this.#overlayLines.push({ role: lv.role, series, price, row });
    }

    this.#setEntryMarker();
    requestAnimationFrame(() => this.#refreshOverlayGeometry());
  }

  #applyMarkers() {
    const merged = [...this.#baseMarkers, ...this.#importantMarkers, ...this.#sequenceMarkers].sort(
      (a, b) => a.time - b.time,
    );
    this.#candleSeries.setMarkers(merged);
  }

  showSequenceWindow(centerTime, windowSize = 5) {
    this.#sequenceMarkers = [];
    if (!centerTime || !this.#candles?.length || !windowSize) {
      this.#applyMarkers();
      return;
    }
    const idx = this.#candleIndex(centerTime);
    if (idx < 0) return;
    const start = Math.max(0, idx - windowSize + 1);
    for (let j = start; j <= idx; j++) {
      const c = this.#candles[j];
      if (!c) continue;
      this.#sequenceMarkers.push({
        time: c.time,
        position: 'belowBar',
        color: j === idx ? '#a855f7' : '#6366f1',
        shape: 'circle',
        text: j === idx ? '●' : '',
      });
    }
    this.#applyMarkers();
  }

  clearSequenceWindow() {
    this.#sequenceMarkers = [];
    this.#applyMarkers();
  }

  showImportantBars(bars) {
    this.#importantBarsData = bars || [];
    if (!bars?.length) {
      this.#importantMarkers = [];
      this.#applyMarkers();
      return;
    }
    this.#importantMarkers = bars.map((bar) => {
      const tag =
        bar.confirmed_tags?.[0] ||
        bar.primary_tag ||
        (bar.suggested_tags?.[0] ?? '');
      const label = tag ? tag.slice(0, 4) : String(bar.score);
      const score = Number(bar.score) || 0;
      const confirmed = bar.user_confirmed;
      const selected = this.#selectedBarTime === bar.time;
      let color = score >= 70 ? '#fbbf24' : score >= 50 ? '#38bdf8' : '#64748b';
      if (confirmed) color = '#22c55e';
      if (selected) color = '#a855f7';
      return {
        time: bar.time,
        position: 'aboveBar',
        color,
        shape: selected ? 'square' : 'circle',
        text: confirmed ? `✓${label.slice(0, 3)}` : label,
      };
    });
    this.#applyMarkers();
  }

  clearImportantBars() {
    this.#importantBarsData = [];
    this.#selectedBarTime = null;
    this.#importantMarkers = [];
    this.clearSequenceWindow();
  }

  showSetupMarkers(setups) {
    if (!setups?.length) {
      this.#baseMarkers = [];
      this.#applyMarkers();
      return;
    }
    this.#baseMarkers = setups.map((s) => {
      const time = Math.floor(new Date(s.entry_time).getTime() / 1000);
      const isLong = s.direction === 'long';
      const win = s.result === 'win';
      const loss = s.result === 'loss';
      return {
        time: this.#nearestCandle(time)?.time ?? time,
        position: isLong ? 'belowBar' : 'aboveBar',
        color: win ? COLORS.up : loss ? COLORS.down : COLORS.entry,
        shape: isLong ? 'arrowUp' : 'arrowDown',
        text: (s.result || 'setup').slice(0, 3).toUpperCase(),
      };
    });
    this.#applyMarkers();
  }

  showTradeMarkers(trades) {
    if (!trades?.length) {
      this.#baseMarkers = [];
      this.#applyMarkers();
      return;
    }
    this.#baseMarkers = trades.map((t) => {
      const time = Math.floor(new Date(t.entry_time).getTime() / 1000);
      const isLong = t.direction === 'long';
      const win = t.result === 'win';
      return {
        time: this.#nearestCandle(time)?.time ?? time,
        position: isLong ? 'belowBar' : 'aboveBar',
        color: win ? COLORS.up : COLORS.down,
        shape: isLong ? 'arrowUp' : 'arrowDown',
        text: win ? 'W' : 'L',
      };
    });
    this.#applyMarkers();
  }

  viewTrade(trade) {
    const time = Math.floor(new Date(trade.entry_time).getTime() / 1000);
    const payload = {
      time,
      entry: trade.entry,
      sl: trade.sl,
      tp: trade.tp,
      direction: trade.direction,
    };
    this.focusSetup(payload);
    this.setOverlay({ ...payload, interactive: false });
  }

  viewSetup(setup, { interactive = false } = {}) {
    const time = Math.floor(new Date(setup.entry_time).getTime() / 1000);
    const payload = {
      time,
      entry: Number(setup.entry_price),
      sl: Number(setup.stop_loss),
      tp: Number(setup.take_profit),
      direction: setup.direction,
    };
    this.focusSetup(payload);
    this.setOverlay({ ...payload, interactive });
  }

  clearOverlay() {
    for (const item of this.#overlayLines) {
      try {
        this.#mainChart.removeSeries(item.series);
      } catch {
        item.series.setData([]);
      }
      item.row?.remove();
    }
    this.#overlayLines = [];
    this.#overlayStartTime = null;
    this.#baseMarkers = [];
    this.#applyMarkers();
    this.#wrapEl?.classList.remove('dragging-level');
  }

  clearFocus() {
    this.clearPriceFocus();
  }

  resetViewport() {
    this.clearPriceFocus();
    if (!this.#candles?.length || !this.#mainChart) return;
    this.#mainChart.timeScale().fitContent();
    if (this.#showRsi) this.#syncRsiTimeScale();
    requestAnimationFrame(() => {
      this.#refreshOverlayLines();
      this.#refreshOverlayGeometry();
    });
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
    const panel = this.#rsiEl?.closest('.rsi-panel');
    const splitter = document.getElementById('chartSplitter');
    if (panel) panel.style.display = on ? '' : 'none';
    else this.#rsiEl.style.display = on ? 'block' : 'none';
    if (splitter) splitter.style.display = on ? '' : 'none';
    this.#refreshRsiBandLines();
    this.#resize();
    if (on) this.#syncRsiTimeScale();
  }

  scrollToTime(unixSec) {
    this.focusSetup({ time: unixSec, entry: null, sl: null, tp: null });
  }

  resize() {
    this.#resize();
  }
}
