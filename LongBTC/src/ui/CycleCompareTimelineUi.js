/**
 * Halving cycle comparison timeline UI (4 progress tracks).
 * @module ui/CycleCompareTimelineUi
 */

import { el } from '../utils/dom.js';
import { buildHalvingCycleCompare } from '../analysis/CycleCompareTimeline.js';
import { CYCLE_PHASE_RANGES } from '../analysis/BtcCycleConfig.js';

/**
 * @param {number} [now]
 * @returns {HTMLElement}
 */
export function renderCycleCompareTimeline(now = Date.now()) {
  const data = buildHalvingCycleCompare(now);
  const marker = data.currentProgressPct;

  const root = el('div', { class: 'cycle-compare-timeline' });

  root.appendChild(el('div', { class: 'cycle-compare-head' }, [
    el('h3', { class: 'cycle-compare-title' }, ['B\u1ea1n \u0111ang \u1edf \u0111\u00e2u trong chu k\u1ef3 halving?']),
    el('p', { class: 'cycle-compare-sub' }, [
      `V\u1ecb tr\u00ed hi\u1ec7n t\u1ea1i: ${marker.toFixed(1)}% chu k\u1ef3 ${data.currentHalvingLabel} \u00b7 ${data.currentPhaseLabel}`,
    ]),
  ]));

  const tracks = el('div', { class: 'cycle-compare-tracks' });

  for (const row of data.rows) {
    const label = row.isCurrent
      ? `${row.startYear} \u2192 nay (\u0111ang di\u1ec5n ra)`
      : `${row.startYear} \u2192 ${row.endYear ?? '?'}`;

    const track = el('div', {
      class: `cycle-compare-row${row.isCurrent ? ' is-current' : ''}`,
    }, [
      el('div', { class: 'cycle-compare-row-head' }, [
        el('span', { class: 'cycle-compare-year' }, [String(row.startYear)]),
        el('span', { class: 'cycle-compare-pct' }, [`${row.progressPct.toFixed(0)}%`]),
      ]),
      el('div', { class: 'cycle-compare-track-wrap' }, [
        el('div', { class: 'cycle-compare-track' }, [
          el('div', {
            class: 'cycle-compare-fill',
            style: `width:${Math.min(100, row.progressPct)}%;background:${row.isCurrent ? row.phaseColor : '#334155'}`,
          }),
          el('div', {
            class: 'cycle-compare-marker',
            style: `left:${Math.min(99, marker)}%`,
            title: `V\u1ecb tr\u00ed hi\u1ec7n t\u1ea1i: ${marker.toFixed(1)}%`,
          }),
        ]),
        el('span', { class: 'cycle-compare-row-label' }, [label]),
      ]),
    ]);

    if (row.isCurrent) {
      track.appendChild(el('span', { class: 'cycle-compare-badge' }, ['Hi\u1ec7n t\u1ea1i']));
    }

    tracks.appendChild(track);
  }

  const ruler = data.phaseRuler;
  const phaseSegments = Object.values(CYCLE_PHASE_RANGES).map((range) =>
    el('div', {
      class: 'cycle-compare-phase-seg',
      style: `left:${range.start * 100}%;width:${(range.end - range.start) * 100}%;background:${range.color}`,
      title: range.label,
    })
  );

  tracks.appendChild(el('div', { class: 'cycle-compare-row is-ruler' }, [
    el('div', { class: 'cycle-compare-row-head' }, [
      el('span', { class: 'cycle-compare-year' }, ['Hi\u1ec7n t\u1ea1i']),
      el('span', { class: 'cycle-compare-pct' }, [`${ruler.markerPct.toFixed(0)}%`]),
    ]),
    el('div', { class: 'cycle-compare-track-wrap' }, [
      el('div', { class: 'cycle-compare-track cycle-compare-track--phases' }, [
        ...phaseSegments,
        el('div', {
          class: 'cycle-compare-marker cycle-compare-marker--strong',
          style: `left:${Math.min(99, ruler.markerPct)}%`,
          title: `${ruler.phaseLabel} \u00b7 ${ruler.markerPct.toFixed(1)}%`,
        }),
      ]),
      el('span', { class: 'cycle-compare-row-label' }, [
        `B\u1ea1n \u0111ang \u1edf \u0111\u00e2y \u00b7 ${ruler.phaseLabel}`,
      ]),
    ]),
    el('span', { class: 'cycle-compare-badge' }, ['\u0110i\u1ec3m so s\u00e1nh']),
  ]));

  root.appendChild(tracks);

  root.appendChild(el('div', { class: 'cycle-compare-legend' }, [
    el('span', { class: 'cycle-compare-legend-item' }, [
      el('span', { class: 'cycle-compare-swatch cycle-compare-swatch--done' }),
      'Chu k\u1ef3 \u0111\u00e3 k\u1ebft th\u00fac',
    ]),
    el('span', { class: 'cycle-compare-legend-item' }, [
      el('span', { class: 'cycle-compare-swatch cycle-compare-swatch--marker' }),
      `V\u1ea1ch d\u1ecdc = ${marker.toFixed(0)}% (v\u1ecb tr\u00ed hi\u1ec7n t\u1ea1i tr\u00ean m\u1ecdi chu k\u1ef3)`,
    ]),
    ...Object.entries(CYCLE_PHASE_RANGES).map(([, range]) =>
      el('span', { class: 'cycle-compare-legend-item' }, [
        el('span', {
          class: 'cycle-compare-swatch',
          style: `background:${range.color}`,
        }),
        range.label,
      ])
    ),
  ]));

  return root;
}
