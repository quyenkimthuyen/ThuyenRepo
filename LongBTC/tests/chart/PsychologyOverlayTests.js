/**
 * Psychology chart overlay geometry tests.
 * Run: node tests/chart/PsychologyOverlayTests.js
 */

import { createSuite, header, footer } from '../harness.js';
import { __psychologyOverlayTest } from '../../src/chart/PsychologyChartOverlay.js';

const { bandSegmentPx } = __psychologyOverlayTest;
const s = createSuite('Psychology Overlay');
header('Psychology Overlay');

const WEEK = 7 * 24 * 60 * 60 * 1000;
const paneWidth = 800;

/**
 * Mock time scale simulating max zoom (fractional logical span ~1 bar).
 * @param {number} barCount
 */
function mockTightZoomScale(barCount = 1.2) {
  const visibleFrom = 1_700_000_000;
  const visibleTo = visibleFrom + 7 * 24 * 3600;
  const span = visibleTo - visibleFrom;

  return {
    width: () => paneWidth,
    getVisibleRange: () => ({ from: visibleFrom, to: visibleTo }),
    getVisibleLogicalRange: () => ({ from: 100, to: 100 + barCount }),
    timeToCoordinate: (sec) => {
      if (sec < visibleFrom || sec > visibleTo) return null;
      const t = (sec - visibleFrom) / span;
      const x = t * paneWidth;
      return Math.round(x * 100) / 100;
    },
    logicalToCoordinate: (idx) => {
      const logical = { from: 100, to: 100 + barCount };
      const t = (idx - logical.from) / (logical.to - logical.from);
      return t * paneWidth;
    },
  };
}

const candles = [
  { timestamp: 1_700_000_000 * 1000, open: 1, high: 1, low: 1, close: 1 },
  { timestamp: (1_700_000_000 + 7 * 24 * 3600) * 1000, open: 1, high: 1, low: 1, close: 1 },
];

const timeScale = mockTightZoomScale(1.2);
const viewFromMs = 1_700_000_000 * 1000;
const viewToMs = (1_700_000_000 + 7 * 24 * 3600) * 1000;

const band = {
  startTime: viewFromMs - 30 * WEEK,
  endTime: viewToMs + 30 * WEEK,
};

const px = bandSegmentPx(timeScale, band, candles, paneWidth, viewFromMs, viewToMs);

s.assert('PO-01: segment exists at max zoom', px != null);
s.assert('PO-02: full-viewport clip spans pane', px != null && px.width >= paneWidth * 0.9);
s.assert('PO-03: segment within pane', px != null && px.left >= 0 && px.left + px.width <= paneWidth + 1);

/** Same-bar coords (x2 <= x1) must not stretch to pane edge. */
const sameBarScale = {
  width: () => paneWidth,
  getVisibleRange: () => ({ from: 1_700_000_000, to: 1_700_000_000 + 3600 }),
  getVisibleLogicalRange: () => ({ from: 50, to: 51 }),
  timeToCoordinate: () => 400,
  logicalToCoordinate: () => 400,
};

const samePx = bandSegmentPx(
  sameBarScale,
  { startTime: viewFromMs, endTime: viewToMs },
  candles,
  paneWidth,
  viewFromMs,
  viewToMs
);

s.assert('PO-04: same-bar coords bounded', samePx != null && samePx.width <= 30);

/** Regression: inverted/same coords must not stretch to pane right edge. */
const midBugScale = {
  width: () => paneWidth,
  getVisibleRange: () => ({ from: 1_700_000_000, to: 1_700_000_000 + 7 * 24 * 3600 }),
  getVisibleLogicalRange: () => ({ from: 200, to: 201 }),
  timeToCoordinate: () => 600,
  logicalToCoordinate: () => 600,
};

const midPx = bandSegmentPx(
  midBugScale,
  { startTime: viewFromMs, endTime: viewToMs },
  candles,
  paneWidth,
  viewFromMs,
  viewToMs
);

s.assert('PO-05: no stretch to right edge', midPx != null && midPx.left + midPx.width <= 630);

process.exit(footer(s.finish()));
