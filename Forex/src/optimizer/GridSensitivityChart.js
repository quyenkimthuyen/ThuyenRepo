/**
 * Canvas chart for grid-search parameter sensitivity.
 * @module optimizer/GridSensitivityChart
 */

/** @typedef {import('./GridSensitivity.js').SensitivityPoint} SensitivityPoint */

/**
 * @typedef {Object} SensitivityChartOptions
 * @property {boolean} [showWinRate=true]
 * @property {boolean} [showExpectancy=true]
 * @property {boolean} [showNetProfit=true]
 */

const COLORS = {
  grid: '#2a3548',
  text: '#94a3b8',
  winRate: '#22c55e',
  expectancy: '#3b82f6',
  netProfit: '#f59e0b',
};

const PADDING = { top: 32, right: 56, bottom: 40, left: 48 };

/**
 * @param {CanvasRenderingContext2D} ctx
 * @param {number} x
 * @param {number} y
 * @param {string} text
 * @param {'left'|'center'|'right'} align
 */
function drawLabel(ctx, x, y, text, align = 'center') {
  ctx.fillStyle = COLORS.text;
  ctx.font = '11px system-ui, sans-serif';
  ctx.textAlign = align;
  ctx.textBaseline = 'middle';
  ctx.fillText(text, x, y);
}

/**
 * @param {number} value
 * @param {number} min
 * @param {number} max
 * @param {number} height
 * @param {number} top
 * @returns {number}
 */
function mapY(value, min, max, height, top) {
  const range = max - min || 1;
  return top + height - ((value - min) / range) * height;
}

/**
 * @param {number[]} values
 * @returns {{ min: number, max: number }}
 */
function dollarRange(values) {
  if (!values.length) return { min: -1, max: 1 };
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) {
    min -= 1;
    max += 1;
  } else {
    const pad = (max - min) * 0.1;
    min -= pad;
    max += pad;
  }
  return { min, max };
}

/**
 * @param {CanvasRenderingContext2D} ctx
 * @param {SensitivityPoint[]} series
 * @param {(point: SensitivityPoint) => number} getY
 * @param {number} yMin
 * @param {number} yMax
 * @param {number} plotH
 * @param {(index: number) => number} xAt
 * @param {string} color
 * @param {boolean} [dashed]
 */
function drawSeriesLine(ctx, series, getY, yMin, yMax, plotH, xAt, color, dashed = false) {
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 2;
  if (dashed) ctx.setLineDash([5, 4]);
  else ctx.setLineDash([]);

  ctx.beginPath();
  series.forEach((point, i) => {
    const x = xAt(i);
    const y = mapY(getY(point), yMin, yMax, plotH, PADDING.top);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  series.forEach((point, i) => {
    const x = xAt(i);
    const y = mapY(getY(point), yMin, yMax, plotH, PADDING.top);
    ctx.beginPath();
    ctx.arc(x, y, 3.5, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.setLineDash([]);
}

/**
 * Draw sensitivity chart onto a canvas.
 * @param {HTMLCanvasElement} canvas
 * @param {SensitivityPoint[]} series
 * @param {string} paramLabel
 * @param {SensitivityChartOptions} [options]
 * @returns {boolean} false when there is nothing meaningful to plot
 */
export function drawGridSensitivityChart(canvas, series, paramLabel, options = {}) {
  const showWinRate = options.showWinRate !== false;
  const showExpectancy = options.showExpectancy !== false;
  const showNetProfit = options.showNetProfit !== false;

  if (!showWinRate && !showExpectancy && !showNetProfit) return false;

  const ctx = canvas.getContext('2d');
  if (!ctx || series.length < 2) return false;

  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, rect.width * dpr);
  canvas.height = Math.max(1, rect.height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const w = rect.width;
  const h = rect.height;
  const plotW = w - PADDING.left - PADDING.right;
  const plotH = h - PADDING.top - PADDING.bottom;

  ctx.clearRect(0, 0, w, h);

  const wrMin = 0;
  const wrMax = 100;

  /** @type {number[]} */
  const dollarValues = [];
  if (showExpectancy) dollarValues.push(...series.map((p) => p.expectancy));
  if (showNetProfit) dollarValues.push(...series.map((p) => p.netProfit));
  const { min: dollarMin, max: dollarMax } = dollarRange(dollarValues);

  ctx.strokeStyle = COLORS.grid;
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = PADDING.top + (plotH * i) / 4;
    ctx.beginPath();
    ctx.moveTo(PADDING.left, y);
    ctx.lineTo(PADDING.left + plotW, y);
    ctx.stroke();
  }

  const xAt = (index) => PADDING.left + (index / (series.length - 1)) * plotW;

  if (showWinRate) {
    drawSeriesLine(ctx, series, (p) => p.winRate, wrMin, wrMax, plotH, xAt, COLORS.winRate);
  }

  if (showExpectancy && showNetProfit) {
    drawSeriesLine(ctx, series, (p) => p.expectancy, dollarMin, dollarMax, plotH, xAt, COLORS.expectancy);
    drawSeriesLine(ctx, series, (p) => p.netProfit, dollarMin, dollarMax, plotH, xAt, COLORS.netProfit, true);
  } else if (showExpectancy) {
    drawSeriesLine(ctx, series, (p) => p.expectancy, dollarMin, dollarMax, plotH, xAt, COLORS.expectancy);
  } else if (showNetProfit) {
    drawSeriesLine(ctx, series, (p) => p.netProfit, dollarMin, dollarMax, plotH, xAt, COLORS.netProfit);
  }

  if (showWinRate) {
    for (let i = 0; i <= 4; i++) {
      const wr = wrMax - ((wrMax - wrMin) * i) / 4;
      const y = PADDING.top + (plotH * i) / 4;
      drawLabel(ctx, PADDING.left - 8, y, `${wr.toFixed(0)}%`, 'right');
    }
  }

  if (showExpectancy || showNetProfit) {
    for (let i = 0; i <= 4; i++) {
      const val = dollarMax - ((dollarMax - dollarMin) * i) / 4;
      const y = PADDING.top + (plotH * i) / 4;
      drawLabel(ctx, PADDING.left + plotW + 8, y, `$${val.toFixed(0)}`, 'left');
    }
  }

  series.forEach((point, i) => {
    const x = xAt(i);
    const label = typeof point.paramValue === 'number'
      ? Number.isInteger(point.paramValue) ? String(point.paramValue) : point.paramValue.toFixed(1)
      : String(point.paramValue);
    drawLabel(ctx, x, h - 14, label);
  });

  let legendX = PADDING.left;
  const legendY = 12;
  const items = [
    showWinRate && { color: COLORS.winRate, label: 'WR' },
    showExpectancy && { color: COLORS.expectancy, label: 'Exp' },
    showNetProfit && { color: COLORS.netProfit, label: showExpectancy ? 'Net (--) ' : 'Net' },
  ].filter(Boolean);

  for (const item of items) {
    if (!item) continue;
    ctx.fillStyle = item.color;
    ctx.fillRect(legendX, legendY - 5, 10, 10);
    drawLabel(ctx, legendX + 14, legendY, item.label, 'left');
    legendX += ctx.measureText(item.label).width + 28;
  }

  drawLabel(ctx, w / 2, h - 2, paramLabel, 'center');

  return true;
}
