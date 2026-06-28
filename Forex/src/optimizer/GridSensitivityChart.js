/**
 * Canvas chart for grid-search parameter sensitivity (WR + expectancy).
 * @module optimizer/GridSensitivityChart
 */

/** @typedef {import('./GridSensitivity.js').SensitivityPoint} SensitivityPoint */

const COLORS = {
  grid: '#2a3548',
  text: '#94a3b8',
  winRate: '#22c55e',
  expectancy: '#3b82f6',
};

const PADDING = { top: 28, right: 52, bottom: 40, left: 48 };

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
 * Draw dual-axis sensitivity chart onto a canvas.
 * @param {HTMLCanvasElement} canvas
 * @param {SensitivityPoint[]} series
 * @param {string} paramLabel
 * @returns {boolean} false when there is nothing meaningful to plot
 */
export function drawGridSensitivityChart(canvas, series, paramLabel) {
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
  const expValues = series.map((p) => p.expectancy);
  let expMin = Math.min(...expValues);
  let expMax = Math.max(...expValues);
  if (expMin === expMax) {
    expMin -= 1;
    expMax += 1;
  } else {
    const pad = (expMax - expMin) * 0.1;
    expMin -= pad;
    expMax += pad;
  }

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

  ctx.strokeStyle = COLORS.winRate;
  ctx.lineWidth = 2;
  ctx.beginPath();
  series.forEach((point, i) => {
    const x = xAt(i);
    const y = mapY(point.winRate, wrMin, wrMax, plotH, PADDING.top);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = COLORS.winRate;
  series.forEach((point, i) => {
    const x = xAt(i);
    const y = mapY(point.winRate, wrMin, wrMax, plotH, PADDING.top);
    ctx.beginPath();
    ctx.arc(x, y, 3.5, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.strokeStyle = COLORS.expectancy;
  ctx.lineWidth = 2;
  ctx.beginPath();
  series.forEach((point, i) => {
    const x = xAt(i);
    const y = mapY(point.expectancy, expMin, expMax, plotH, PADDING.top);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = COLORS.expectancy;
  series.forEach((point, i) => {
    const x = xAt(i);
    const y = mapY(point.expectancy, expMin, expMax, plotH, PADDING.top);
    ctx.beginPath();
    ctx.arc(x, y, 3.5, 0, Math.PI * 2);
    ctx.fill();
  });

  for (let i = 0; i <= 4; i++) {
    const wr = wrMax - ((wrMax - wrMin) * i) / 4;
    const y = PADDING.top + (plotH * i) / 4;
    drawLabel(ctx, PADDING.left - 8, y, `${wr.toFixed(0)}%`, 'right');
  }

  for (let i = 0; i <= 4; i++) {
    const exp = expMax - ((expMax - expMin) * i) / 4;
    const y = PADDING.top + (plotH * i) / 4;
    drawLabel(ctx, PADDING.left + plotW + 8, y, `$${exp.toFixed(0)}`, 'left');
  }

  series.forEach((point, i) => {
    const x = xAt(i);
    const label = typeof point.paramValue === 'number'
      ? Number.isInteger(point.paramValue) ? String(point.paramValue) : point.paramValue.toFixed(1)
      : String(point.paramValue);
    drawLabel(ctx, x, h - 14, label);
  });

  drawLabel(ctx, PADDING.left, 12, 'Win Rate', 'left');
  ctx.fillStyle = COLORS.winRate;
  ctx.fillRect(PADDING.left + 62, 8, 10, 10);
  drawLabel(ctx, PADDING.left + 78, 12, 'WR', 'left');

  ctx.fillStyle = COLORS.expectancy;
  ctx.fillRect(PADDING.left + 108, 8, 10, 10);
  drawLabel(ctx, PADDING.left + 124, 12, 'Expectancy', 'left');

  drawLabel(ctx, w / 2, h - 2, paramLabel, 'center');

  return true;
}
