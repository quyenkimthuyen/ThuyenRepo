/**
 * Multi-cycle psychology history timeline (halving calendar bands).
 * @module ui/PsychologyHistoryTimeline
 */

import { el } from '../utils/dom.js';
import { historyYear } from '../analysis/PsychologyBands.js';

/**
 * @typedef {import('../analysis/PsychologyBands.js').PsychologyBand} PsychologyBand
 * @typedef {{
 *   halvingLabel: string,
 *   cycleIndex: number,
 *   startTime: number,
 *   endTime: number,
 *   bands: PsychologyBand[],
 *   isCurrent: boolean,
 *   progressPct: number,
 * }} PsychologyCycleHistory
 */

/**
 * @param {{
 *   cycles: PsychologyCycleHistory[],
 *   cursorTs?: number,
 *   compact?: boolean,
 *   title?: string,
 * }} opts
 * @returns {HTMLElement}
 */
export function renderPsychologyHistory(opts) {
  const { cycles, cursorTs, compact = false, title } = opts;

  const root = el('div', {
    class: `psychology-history${compact ? ' psychology-history-compact' : ''}`,
  });

  if (title) {
    root.appendChild(el('p', { class: 'psychology-history-intro' }, [title]));
  }

  const list = el('div', { class: 'psychology-history-cycles' });

  for (const cycle of cycles) {
    const startY = historyYear(cycle.startTime);
    const endY = historyYear(cycle.endTime);
    const halvingShort = cycle.halvingLabel.replace('Halving ', 'H');

    const row = el('div', {
      class: `psychology-history-cycle${cycle.isCurrent ? ' is-current' : ''}`,
    }, [
      el('div', { class: 'psychology-history-cycle-head' }, [
        el('span', { class: 'psychology-history-cycle-label' }, [
          `${cycle.halvingLabel} \u00b7 ${startY}\u2013${endY}`,
        ]),
        cycle.isCurrent
          ? el('span', { class: 'psychology-history-cycle-badge' }, ['\u0110ang xem'])
          : null,
      ].filter(Boolean)),
      renderCycleTrack(cycle, cursorTs),
    ]);

    list.appendChild(row);
  }

  root.appendChild(list);
  return root;
}

/**
 * @param {PsychologyCycleHistory} cycle
 * @param {number} [cursorTs]
 * @returns {HTMLElement}
 */
function renderCycleTrack(cycle, cursorTs) {
  const span = cycle.endTime - cycle.startTime;
  const track = el('div', { class: 'psychology-history-track' });

  for (const band of cycle.bands) {
    const widthPct = span > 0 ? ((band.endTime - band.startTime) / span) * 100 : 0;
    if (widthPct < 0.2) continue;

    const isAtCursor = cursorTs != null
      && cursorTs >= band.startTime
      && cursorTs < band.endTime;

    track.appendChild(el('div', {
      class: `psychology-history-seg${isAtCursor ? ' is-at-cursor' : ''}`,
      style: `flex:${Math.max(0.5, widthPct)};--phase-color:${band.phase.color}`,
      title: `${band.phase.labelVi} (${band.phase.label})`,
    }, [
      widthPct >= (cycle.bands.length > 8 ? 6 : 4)
        ? el('span', { class: 'psychology-history-seg-label' }, [band.phase.labelVi])
        : null,
    ].filter(Boolean)));
  }

  const wrap = el('div', { class: 'psychology-history-track-wrap' }, [track]);

  if (cycle.isCurrent && cycle.progressPct > 0) {
    wrap.appendChild(el('div', {
      class: 'psychology-history-marker',
      style: `left:${Math.min(99, Math.max(0, cycle.progressPct))}%`,
      title: `Ti\u1ebfn \u0111\u1ed9 chu k\u1ef3: ${cycle.progressPct.toFixed(1)}%`,
    }));
  }

  return wrap;
}

/**
 * Visible chart range as one continuous psychology band row.
 * @param {PsychologyBand[]} bands
 * @param {number} fromTs
 * @param {number} toTs
 * @param {number} [cursorTs]
 * @returns {HTMLElement|null}
 */
export function renderPsychologyRangeHistory(bands, fromTs, toTs, cursorTs) {
  if (bands.length === 0 || toTs <= fromTs) return null;

  const span = toTs - fromTs;
  const track = el('div', { class: 'psychology-history-track psychology-history-track-range' });

  for (const band of bands) {
    const clipStart = Math.max(band.startTime, fromTs);
    const clipEnd = Math.min(band.endTime, toTs);
    if (clipEnd <= clipStart) continue;

    const widthPct = ((clipEnd - clipStart) / span) * 100;
    const isAtCursor = cursorTs != null
      && cursorTs >= band.startTime
      && cursorTs < band.endTime;

    track.appendChild(el('div', {
      class: `psychology-history-seg${isAtCursor ? ' is-at-cursor' : ''}`,
      style: `flex:${Math.max(0.5, widthPct)};--phase-color:${band.phase.color}`,
      title: `${band.halvingLabel} \u00b7 ${band.phase.labelVi}`,
    }, [
      widthPct >= 5
        ? el('span', { class: 'psychology-history-seg-label' }, [band.phase.labelVi])
        : null,
    ].filter(Boolean)));
  }

  if (cursorTs != null && cursorTs >= fromTs && cursorTs <= toTs) {
    const leftPct = ((cursorTs - fromTs) / span) * 100;
    return el('div', { class: 'psychology-history-track-wrap' }, [
      track,
      el('div', {
        class: 'psychology-history-marker',
        style: `left:${Math.min(99, Math.max(0, leftPct))}%`,
      }),
    ]);
  }

  return el('div', { class: 'psychology-history-track-wrap' }, [track]);
}
