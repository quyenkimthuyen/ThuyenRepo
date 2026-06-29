
/**
 * Market psychology cycle view.
 * @module ui/PsychologyView
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import { getLastAnalysis } from '../analysis/LongTermAnalysisEngine.js';
import { buildPsychologyCycleHistory } from '../analysis/PsychologyBands.js';
import { PSYCHOLOGY_PHASES } from '../analysis/BtcCycleConfig.js';
import {
  renderAnalysisHeader,
  renderMetricGrid,
  renderNoAnalysis,
} from './AnalysisViewHelpers.js';
import { renderPsychologyHistory } from './PsychologyHistoryTimeline.js';
import { renderPsychologyInvestGuide } from './PsychologyInvestGuideUi.js';

class PsychologyViewImpl {
  #unsub = null;

  mount(container) {
    container.innerHTML = '';
    container.classList.add('analysis-view');

    container.appendChild(renderAnalysisHeader(
      'Chu k\u1ef3 t\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng',
      'Giai \u0111o\u1ea1n t\u00e2m l\u00fd, l\u1ecbch s\u1eed gi\u00e1 v\u00e0 khuy\u1ebfn ngh\u1ecb DCA d\u00e0i h\u1ea1n',
      'psychology'
    ));

    const body = el('div', { class: 'analysis-body', id: 'psychology-body' });
    container.appendChild(body);
    this.#render(body);
    this.#unsub = bus.on(Events.ANALYSIS_COMPLETE, () => this.#render(body));
  }

  #render(body) {
    const analysis = getLastAnalysis();
    body.innerHTML = '';

    if (!analysis) {
      body.appendChild(renderNoAnalysis());
      return;
    }

    const p = analysis.psychology;

    body.appendChild(el('div', {
      class: 'psychology-hero',
      style: `border-color:${p.color}`,
    }, [
      el('span', { class: 'psychology-hero-label' }, ['Giai \u0111o\u1ea1n hi\u1ec7n t\u1ea1i']),
      el('span', { class: 'psychology-hero-value', style: `color:${p.color}` }, [p.labelVi]),
      el('span', { class: 'psychology-hero-en' }, [p.label]),
      el('span', { class: 'psychology-hero-confidence' }, [`${p.confidence}% tin c\u1eady`]),
    ]));

    body.appendChild(el('p', { class: 'psychology-description' }, [p.description]));

    body.appendChild(renderMetricGrid([
      { label: 'Chu k\u1ef3 halving', value: analysis.currentCycle.phaseLabel, hint: p.cycleContribution },
      { label: 'Xu h\u01b0\u1edbng', value: analysis.overallTrend.direction, hint: p.trendContribution },
      { label: 'Elliott', value: p.waveContribution },
    ]));

    body.appendChild(el('h3', { class: 'analysis-section-title' }, [
      'Khuy\u1ebfn ngh\u1ecb DCA theo l\u1ecbch s\u1eed gi\u00e1',
    ]));
    body.appendChild(renderPsychologyInvestGuide(p.phaseId));

    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['V\u00f2ng t\u00e2m l\u00fd']));
    body.appendChild(this.#renderWheel(p.phaseId));

    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Timeline chu k\u1ef3 hi\u1ec7n t\u1ea1i']));
    body.appendChild(this.#renderTimeline(analysis));

    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['L\u1ecbch s\u1eed chu k\u1ef3 t\u00e2m l\u00fd']));
    body.appendChild(renderPsychologyHistory({
      cycles: buildPsychologyCycleHistory(
        analysis.currentCycle.nextHalvingEstimate,
        analysis.analyzedAt
      ),
      cursorTs: analysis.analyzedAt,
      title: 'C\u00e1c giai \u0111o\u1ea1n theo l\u1ecbch halving (2012\u2013nay).',
    }));
  }

  #renderWheel(activePhaseId) {
    const wheel = el('div', { class: 'psychology-wheel' });
    for (const phase of PSYCHOLOGY_PHASES) {
      const isActive = phase.id === activePhaseId;
      wheel.appendChild(el('div', {
        class: `psychology-wheel-item${isActive ? ' active' : ''}`,
        style: isActive ? `background:${phase.color}22;border-color:${phase.color}` : undefined,
      }, [
        el('span', { class: 'psychology-wheel-vi' }, [phase.labelVi]),
        el('span', { class: 'psychology-wheel-en' }, [phase.label]),
      ]));
    }
    return wheel;
  }

  #renderTimeline(analysis) {
    const track = el('div', { class: 'psychology-timeline' });
    const progress = analysis.currentCycle.progressPct;

    for (const item of analysis.psychologyTimeline) {
      track.appendChild(el('div', {
        class: 'psychology-timeline-segment',
        style: `flex:${item.endPct - item.startPct};background:${item.phase.color}33`,
        title: `${item.phase.labelVi} (${item.startPct.toFixed(0)}\u2013${item.endPct.toFixed(0)}%)`,
      }, [
        el('span', { class: 'psychology-timeline-label' }, [item.phase.labelVi]),
      ]));
    }

    return el('div', { class: 'psychology-timeline-wrap' }, [
      track,
      el('div', {
        class: 'psychology-timeline-marker',
        style: `left:${Math.min(99, progress)}%`,
        title: `V\u1ecb tr\u00ed: ${progress.toFixed(1)}%`,
      }),
    ]);
  }

  unmount() {
    this.#unsub?.();
    this.#unsub = null;
  }
}

export const PsychologyView = new PsychologyViewImpl();
