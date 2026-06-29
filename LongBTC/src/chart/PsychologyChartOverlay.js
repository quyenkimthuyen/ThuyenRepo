/**
 * Time-synced psychology background zones on the price chart.
 * Uses Lightweight Charts time scale coordinates (stays aligned on pan/zoom).
 * @module chart/PsychologyChartOverlay
 */

import { el } from '../utils/dom.js';
import { buildPsychologyBandsForRange } from '../analysis/PsychologyBands.js';

/**
 * @param {HTMLElement} chartContainer
 * @returns {HTMLElement}
 */
export function mountPsychologyChartBg(chartContainer) {
  const bg = el('div', {
    class: 'chart-phase-bg chart-phase-bg--psych-only',
    id: 'chart-psychology-bg',
    hidden: true,
  });
  chartContainer.insertBefore(bg, chartContainer.firstChild);
  return bg;
}

/**
 * @param {import('../data/Candle.js').Candle[]} candles
 * @param {number} tsMs
 * @returns {number}
 */
function nearestCandleIndex(candles, tsMs) {
  let index = 0;
  for (let i = 0; i < candles.length; i++) {
    if (candles[i].timestamp <= tsMs) index = i;
    else break;
  }
  return index;
}

/**
 * Map timestamp to x in the chart pane (same coordinate system as candles).
 * @param {import('../../vendor/lightweight-charts.mjs').ITimeScaleApi|null} timeScale
 * @param {number} tsMs
 * @param {import('../data/Candle.js').Candle[]} candles
 * @returns {number|null}
 */
function timeToPx(timeScale, tsMs, candles) {
  if (!timeScale) return null;

  const sec = Math.floor(tsMs / 1000);
  let x = timeScale.timeToCoordinate(sec);
  if (x !== null && Number.isFinite(x)) return x;

  if (candles.length === 0) return null;

  const barSec = Math.floor(candles[nearestCandleIndex(candles, tsMs)].timestamp / 1000);
  x = timeScale.timeToCoordinate(barSec);
  if (x !== null && Number.isFinite(x)) return x;

  return null;
}

/**
 * @param {number|null} x1
 * @param {number|null} x2
 * @param {number} plotWidth
 * @returns {{ left: number, width: number }|null}
 */
function segmentPx(x1, x2, plotWidth) {
  if (x1 === null && x2 === null) return null;
  const a = x1 ?? 0;
  const b = x2 ?? plotWidth;
  const left = Math.max(0, Math.min(a, b));
  const right = Math.min(plotWidth, Math.max(a, b));
  const width = right - left;
  if (width < 1) return null;
  return { left, width };
}

/**
 * Visible time bounds in ms (prefers chart time scale; falls back to candle indices).
 * @param {import('../../vendor/lightweight-charts.mjs').ITimeScaleApi|null} timeScale
 * @param {import('../data/Candle.js').Candle[]} candles
 * @param {number} fallbackFrom
 * @param {number} fallbackTo
 * @returns {{ from: number, to: number }}
 */
function viewBoundsMs(timeScale, candles, fallbackFrom, fallbackTo) {
  const visibleRange = timeScale?.getVisibleRange?.();
  if (visibleRange) {
    return { from: visibleRange.from * 1000, to: visibleRange.to * 1000 };
  }

  const logical = timeScale?.getVisibleLogicalRange?.();
  if (logical && candles.length > 0) {
    const fromIdx = Math.max(0, Math.min(candles.length - 1, Math.floor(logical.from)));
    const toIdx = Math.max(0, Math.min(candles.length - 1, Math.ceil(logical.to)));
    return {
      from: candles[fromIdx].timestamp,
      to: candles[toIdx].timestamp,
    };
  }

  return { from: fallbackFrom, to: fallbackTo };
}

/**
 * Band segment in pane pixels; clip to visible window using time intersection.
 * @param {import('../../vendor/lightweight-charts.mjs').ITimeScaleApi|null} timeScale
 * @param {{ startTime: number, endTime: number }} band
 * @param {import('../data/Candle.js').Candle[]} candles
 * @param {number} paneWidth
 * @param {number} viewFromMs
 * @param {number} viewToMs
 * @returns {{ left: number, width: number }|null}
 */
function bandSegmentPx(timeScale, band, candles, paneWidth, viewFromMs, viewToMs) {
  if (band.endTime <= viewFromMs || band.startTime >= viewToMs) return null;

  const clipStart = Math.max(band.startTime, viewFromMs);
  const clipEnd = Math.min(band.endTime, viewToMs);
  const lastTs = candles.length > 0 ? candles[candles.length - 1].timestamp : 0;

  let x1 = timeToPx(timeScale, clipStart, candles);
  let x2 = timeToPx(timeScale, clipEnd, candles);

  if (x1 === null && clipStart <= viewFromMs) x1 = 0;
  if (x2 === null && clipEnd >= viewToMs) x2 = paneWidth;
  if (x1 === null && clipStart > lastTs) {
    x1 = timeToPx(timeScale, lastTs, candles);
  }
  if (x2 === null && clipEnd > lastTs) {
    x2 = paneWidth;
  }
  if (x1 !== null && x2 !== null && x2 <= x1) {
    x2 = paneWidth;
  }

  return segmentPx(x1, x2, paneWidth);
}

/**
 * @param {HTMLElement} bg
 * @param {{
 *   timeScale: import('../../vendor/lightweight-charts.mjs').ITimeScaleApi|null,
 *   plotWidth: number,
 *   candles: import('../data/Candle.js').Candle[],
 *   currentCycleEnd: number,
 *   rangeFromTs: number,
 *   rangeToTs: number,
 *   cursorTs: number,
 *   visible: boolean,
 * }} opts
 */
export function updatePsychologyChartBg(bg, opts) {
  const {
    timeScale, plotWidth, candles, currentCycleEnd,
    rangeFromTs, rangeToTs, cursorTs, visible,
  } = opts;

  if (!bg) return 0;

  const paneWidth = timeScale?.width?.() ?? plotWidth;
  if (!visible || paneWidth < 10 || !Number.isFinite(currentCycleEnd)) {
    bg.hidden = true;
    return 0;
  }

  const view = viewBoundsMs(timeScale, candles, rangeFromTs, rangeToTs);
  const viewFromMs = view.from;
  const viewToMs = view.to;

  const bandFrom = Math.min(rangeFromTs, viewFromMs) - 7 * 24 * 60 * 60 * 1000;
  const bandTo = Math.max(rangeToTs, viewToMs) + 7 * 24 * 60 * 60 * 1000;

  const bands = buildPsychologyBandsForRange(
    bandFrom,
    bandTo,
    currentCycleEnd
  );

  bg.hidden = false;
  bg.style.width = `${paneWidth}px`;
  bg.style.left = '0';
  bg.style.right = 'auto';
  bg.style.marginRight = '';

  bg.innerHTML = '';
  let rendered = 0;

  for (const band of bands) {
    const px = bandSegmentPx(
      timeScale,
      band,
      candles,
      paneWidth,
      viewFromMs,
      viewToMs
    );
    if (!px) continue;

    rendered++;
    const isAtCursor = cursorTs >= band.startTime && cursorTs < band.endTime;
    const title = [
      band.halvingLabel,
      'T\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng',
      band.phase.labelVi,
      `(${band.phase.label})`,
    ].join(' \u00b7 ');

    const showLabel = px.width >= 40;

    bg.appendChild(el('div', {
      class: `chart-phase-bg-seg chart-phase-bg-seg--psych${isAtCursor ? ' is-at-cursor' : ''}`,
      style: `left:${px.left}px;width:${px.width}px;--phase-color:${band.phase.color}`,
      title,
      dataset: {
        startTime: String(band.startTime),
        endTime: String(band.endTime),
      },
    }, showLabel ? [
      el('span', { class: 'chart-phase-bg-label chart-phase-bg-label--psych' }, [band.phase.labelVi]),
    ] : []));
  }

  if (rendered === 0 && bands.length > 0) {
    bg.hidden = true;
  }

  return rendered;
}

/**
 * Update only cursor highlight without rebuilding band geometry.
 * @param {HTMLElement} bg
 * @param {number} cursorTs
 */
export function highlightPsychologyChartBgAtCursor(bg, cursorTs) {
  if (!bg || bg.hidden) return;
  for (const seg of bg.querySelectorAll('.chart-phase-bg-seg--psych')) {
    const start = Number(seg.dataset.startTime);
    const end = Number(seg.dataset.endTime);
    if (!Number.isFinite(start) || !Number.isFinite(end)) continue;
    seg.classList.toggle('is-at-cursor', cursorTs >= start && cursorTs < end);
  }
}
