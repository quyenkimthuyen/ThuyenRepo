
/**
 * Market psychology cycle view.
 * @module ui/PsychologyView
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import { getLastAnalysis } from '../analysis/LongTermAnalysisEngine.js';
import { PSYCHOLOGY_PHASES } from '../analysis/BtcCycleConfig.js';
import {
  renderAnalysisHeader,
  renderMetricGrid,
  renderNoAnalysis,
} from './AnalysisViewHelpers.js';

class PsychologyViewImpl {
  #unsub = null;

  mount(container) {
    container.innerHTML = '';
    container.classList.add('analysis-view');

    container.appendChild(renderAnalysisHeader(
      'Chu kỳ tâm lý thị trường',
      'Xác định giai đoạn tâm lý dựa trên chu kỳ 4 năm, xu hướng và sóng Elliott',
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
      el('span', { class: 'psychology-hero-label' }, ['Giai đoạn hiện tại']),
      el('span', { class: 'psychology-hero-value', style: `color:${p.color}` }, [p.labelVi]),
      el('span', { class: 'psychology-hero-en' }, [p.label]),
      el('span', { class: 'psychology-hero-confidence' }, [`${p.confidence}% tin cậy`]),
    ]));

    body.appendChild(el('p', { class: 'psychology-description' }, [p.description]));

    body.appendChild(renderMetricGrid([
      { label: 'Đóng góp từ chu kỳ', value: analysis.currentCycle.phaseLabel, hint: p.cycleContribution },
      { label: 'Đóng góp từ xu hướng', value: analysis.overallTrend.direction, hint: p.trendContribution },
      { label: 'Đóng góp từ Elliott', value: p.waveContribution },
    ]));

    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Vòng tâm lý thị trường']));
    body.appendChild(this.#renderWheel(p.phaseId));

    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Timeline chu kỳ tâm lý']));
    body.appendChild(this.#renderTimeline(analysis));
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
        title: `${item.phase.labelVi} (${item.startPct.toFixed(0)}–${item.endPct.toFixed(0)}%)`,
      }, [
        el('span', { class: 'psychology-timeline-label' }, [item.phase.labelVi]),
      ]));
    }

    return el('div', { class: 'psychology-timeline-wrap' }, [
      track,
      el('div', {
        class: 'psychology-timeline-marker',
        style: `left:${Math.min(99, progress)}%`,
        title: `Vị trí hiện tại: ${progress.toFixed(1)}%`,
      }),
    ]);
  }

  unmount() {
    this.#unsub?.();
    this.#unsub = null;
  }
}

export const PsychologyView = new PsychologyViewImpl();
