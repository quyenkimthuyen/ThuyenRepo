import { createChart, CrosshairMode, LineStyle } from "/static/vendor/lightweight-charts.mjs";

export function createPriceChart(container) {
  const chart = createChart(container, {
    layout: { background: { color: "#0f1419" }, textColor: "#8b9bb4" },
    grid: { vertLines: { color: "#1e2836" }, horzLines: { color: "#1e2836" } },
    crosshair: { mode: CrosshairMode.Normal },
    rightPriceScale: { borderColor: "#2a3548" },
    timeScale: { borderColor: "#2a3548", timeVisible: true },
  });
  const candles = chart.addCandlestickSeries({
    upColor: "#3ecf8e",
    downColor: "#ff6b6b",
    borderVisible: false,
    wickUpColor: "#3ecf8e",
    wickDownColor: "#ff6b6b",
  });
  const ema50 = chart.addLineSeries({ color: "#f0b429", lineWidth: 1 });
  const ema200 = chart.addLineSeries({ color: "#9b59b6", lineWidth: 1 });
  return { chart, candles, ema50, ema200 };
}

export function createRsiChart(container) {
  const chart = createChart(container, {
    layout: { background: { color: "#0f1419" }, textColor: "#8b9bb4" },
    grid: { vertLines: { color: "#1e2836" }, horzLines: { color: "#1e2836" } },
    rightPriceScale: { borderColor: "#2a3548" },
    timeScale: { borderColor: "#2a3548", visible: false },
    height: container.clientHeight,
  });
  const rsi = chart.addLineSeries({ color: "#3d8bfd", lineWidth: 2 });
  const bands = [28, 32, 48, 52, 68, 72];
  bands.forEach((v, i) => {
    rsi.createPriceLine({
      price: v,
      color: i % 2 === 0 ? "#4a5568" : "#2d3748",
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: false,
    });
  });
  return { chart, rsi };
}

export function syncCharts(a, b) {
  let lock = false;
  const link = (src, dst) => {
    src.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (lock || !range) return;
      lock = true;
      dst.timeScale().setVisibleLogicalRange(range);
      lock = false;
    });
  };
  link(a, b);
  link(b, a);
}
