/**
 * Timeframe utilities tests — H1, H4, D1, W alignment.
 * Run: node tests/data/TimeframeTests.js
 */

import { createSuite, header, footer } from '../harness.js';
import {
  alignToTimeframe,
  nextCandleTime,
  getTimeframeMs,
  formatTimestamp,
  parseDatetimeLocalAsUtc,
  timestampToDatetimeLocalValue,
  findNearestCandleIndex,
} from '../../src/data/TimeframeUtils.js';

const s = createSuite('Timeframe Utils');
header('Timeframe Utils');

const H = 3600000;
const D = 86400000;
const W = 7 * D;

{
  s.assert('TF-01: H1 interval', getTimeframeMs('H1') === H);
  s.assert('TF-02: H4 interval', getTimeframeMs('H4') === 4 * H);
  s.assert('TF-03: D1 interval', getTimeframeMs('D1') === D);
  s.assert('TF-04: W interval', getTimeframeMs('W') === W);
  s.assertThrows('TF-05: Unknown TF throws', () => getTimeframeMs('M5'));
}

{
  const ts = Date.UTC(2024, 5, 3, 10, 30, 0);
  s.assert('TF-06: H1 align', alignToTimeframe(ts, 'H1') === Date.UTC(2024, 5, 3, 10, 0, 0));
  s.assert('TF-07: H4 align', alignToTimeframe(ts, 'H4') === Date.UTC(2024, 5, 3, 8, 0, 0));
  s.assert('TF-08: D1 align midnight', alignToTimeframe(ts, 'D1') === Date.UTC(2024, 5, 3, 0, 0, 0));
}

{
  const monday = Date.UTC(2024, 5, 3, 15, 0, 0);
  const wednesday = Date.UTC(2024, 5, 5, 12, 0, 0);
  s.assertEq('TF-09: W align Monday', alignToTimeframe(monday, 'W'), Date.UTC(2024, 5, 3, 0, 0, 0));
  s.assertEq('TF-10: W align from Wed', alignToTimeframe(wednesday, 'W'), Date.UTC(2024, 5, 3, 0, 0, 0));
}

{
  const d1 = Date.UTC(2024, 0, 15, 0, 0, 0);
  s.assertEq('TF-11: next D1', nextCandleTime(d1, 'D1'), d1 + D);
  s.assertEq('TF-12: next W', nextCandleTime(d1, 'W'), d1 + W);
  s.assertEq('TF-13: next H4', nextCandleTime(d1, 'H4'), d1 + 4 * H);
}

{
  const ts = Date.UTC(2024, 5, 3, 10, 0, 0);
  s.assert('TF-14: formatTimestamp', formatTimestamp(ts).includes('2024-06-03'));
}

{
  const ts = Date.UTC(2024, 5, 3, 14, 30, 0);
  s.assertEq('TF-15: datetime-local value', timestampToDatetimeLocalValue(ts), '2024-06-03T14:30');
  s.assertEq('TF-16: parse UTC input', parseDatetimeLocalAsUtc('2024-06-03T14:30'), ts);
  s.assert('TF-17: parse rejects invalid', Number.isNaN(parseDatetimeLocalAsUtc('bad')));
}

{
  const bars = [
    { timestamp: Date.UTC(2024, 0, 1, 10, 0, 0) },
    { timestamp: Date.UTC(2024, 0, 1, 11, 0, 0) },
    { timestamp: Date.UTC(2024, 0, 1, 12, 0, 0) },
  ];
  s.assertEq('TF-18: nearest exact', findNearestCandleIndex(bars, bars[1].timestamp), 1);
  s.assertEq('TF-19: nearest before first', findNearestCandleIndex(bars, bars[0].timestamp - 1), 0);
  s.assertEq('TF-20: nearest after last', findNearestCandleIndex(bars, bars[2].timestamp + 1), 2);
  s.assertEq(
    'TF-21: nearest between bars',
    findNearestCandleIndex(bars, Date.UTC(2024, 0, 1, 11, 45, 0)),
    2
  );
}

process.exit(footer(s.finish()));
