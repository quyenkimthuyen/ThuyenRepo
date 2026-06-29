/**
 * Compact psychology insight card below chart replay (not on price canvas).
 * @module ui/ChartPsychologyInsight
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import { psychologyBandAtTime } from '../analysis/PsychologyBands.js';

/**
 * @typedef {import('../analysis/LongTermAnalysisEngine.js').LongTermAnalysisResult} AnalysisResult
 */

/**
 * @param {HTMLElement} parent
 * @returns {HTMLElement}
 */
export function mountChartPsychologyInsight(parent) {
  const card = el('div', {
    class: 'chart-psychology-insight',
    id: 'chart-psychology-insight',
    hidden: true,
  });
  parent.appendChild(card);
  return card;
}

/**
 * @param {HTMLElement} card
 * @param {{
 *   analysis: AnalysisResult|null,
 *   cursorTs: number,
 *   visible: boolean,
 * }} opts
 */
export function updateChartPsychologyInsight(card, opts) {
  const { analysis, cursorTs, visible } = opts;
  if (!card) return;

  if (!visible || !analysis) {
    card.hidden = true;
    return;
  }

  card.hidden = false;
  const p = analysis.psychology;
  const calendar = psychologyBandAtTime(
    cursorTs,
    analysis.currentCycle.nextHalvingEstimate
  );
  const progress = analysis.currentCycle.progressPct;

  card.innerHTML = '';
  card.appendChild(el('div', { class: 'chart-psychology-insight-head' }, [
    el('div', { class: 'chart-psychology-insight-title-wrap' }, [
      el('span', { class: 'chart-psychology-insight-icon' }, ['\u{1F9E0}']),
      el('span', { class: 'chart-psychology-insight-title' }, ['T\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng']),
    ]),
    el('button', {
      type: 'button',
      class: 'btn btn-sm chart-psychology-insight-link',
      onclick: () => bus.emit(Events.NAVIGATE, { view: 'psychology' }),
    }, ['Ph\u00e2n t\u00edch chi ti\u1ebft \u2192']),
  ]));

  card.appendChild(el('div', { class: 'chart-psychology-insight-body' }, [
    el('div', {
      class: 'chart-psychology-insight-hero',
      style: `border-color:${p.color}`,
    }, [
      el('span', { class: 'chart-psychology-insight-kicker' }, ['\u0110\u00e1nh gi\u00e1 theo gi\u00e1']),
      el('span', { class: 'chart-psychology-insight-phase', style: `color:${p.color}` }, [p.labelVi]),
      el('span', { class: 'chart-psychology-insight-confidence' }, [`${p.confidence}% tin c\u1eady`]),
    ]),
    el('div', { class: 'chart-psychology-insight-calendar' }, [
      el('span', { class: 'chart-psychology-insight-calendar-label' }, ['L\u1ecbch chu k\u1ef3 halving']),
      el('span', { class: 'chart-psychology-insight-calendar-value' }, [
        calendar
          ? `${calendar.halvingLabel.replace('Halving ', 'Halving #')}: ${calendar.phase.labelVi}`
          : 'Ngo\u00e0i v\u00f9ng chu k\u1ef3',
      ]),
    ]),
    el('p', { class: 'chart-psychology-insight-desc' }, [p.description]),
    renderCycleTimeline(analysis, progress),
  ]));
}

/**
 * @param {AnalysisResult} analysis
 * @param {number} progress
 * @returns {HTMLElement}
 */
function renderCycleTimeline(analysis, progress) {
  const track = el('div', { class: 'chart-psychology-insight-timeline' });

  for (const item of analysis.psychologyTimeline) {
    const isActive = item.phase.id === analysis.psychology.phaseId
      || (progress >= item.startPct && progress < item.endPct);
    track.appendChild(el('div', {
      class: `chart-psychology-insight-seg${isActive ? ' is-active' : ''}`,
      style: `flex:${Math.max(1, item.endPct - item.startPct)};--phase-color:${item.phase.color}`,
      title: `${item.phase.labelVi} (${item.startPct.toFixed(0)}\u2013${item.endPct.toFixed(0)}%)`,
    }, [
      el('span', { class: 'chart-psychology-insight-seg-label' }, [item.phase.labelVi]),
    ]));
  }

  return el('div', { class: 'chart-psychology-insight-timeline-wrap' }, [
    el('span', { class: 'chart-psychology-insight-timeline-caption' }, [
      `Chu k\u1ef3 hi\u1ec7n t\u1ea1i \u00b7 ${progress.toFixed(1)}%`,
    ]),
    el('div', { class: 'chart-psychology-insight-timeline-track' }, [track]),
    el('div', {
      class: 'chart-psychology-insight-marker',
      style: `left:${Math.min(99, Math.max(0, progress))}%`,
    }),
  ]);
}
