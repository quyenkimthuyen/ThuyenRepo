
/**
 * BTC long-term analysis dashboard.
 * @module ui/AnalysisDashboardView
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import { getLastAnalysis } from '../analysis/LongTermAnalysisEngine.js';
import {
  renderAnalysisHeader,
  renderMetricGrid,
  renderNoAnalysis,
  buildDashboardMetrics,
} from './AnalysisViewHelpers.js';

class AnalysisDashboardViewImpl {
  #container = null;
  #unsub = null;

  mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.add('analysis-view');

    container.appendChild(renderAnalysisHeader(
      'Tổng quan nghiên cứu BTC',
      'Chu kỳ 4 năm → Xu hướng → Sóng Elliott → Chu kỳ tâm lý thị trường',
      'dashboard'
    ));

    const body = el('div', { class: 'analysis-body', id: 'dashboard-body' });
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

    body.appendChild(renderMetricGrid(buildDashboardMetrics(analysis)));

    body.appendChild(el('div', { class: 'analysis-summary-box' }, [
      el('h3', {}, ['Tóm tắt phân tích']),
      el('p', {}, [analysis.summary]),
    ]));

    body.appendChild(el('div', { class: 'analysis-pipeline' }, [
      el('h3', {}, ['Quy trình phân tích']),
      el('ol', { class: 'analysis-pipeline-steps' }, [
        el('li', {}, [`① Chu kỳ halving: ${analysis.currentCycle.phaseLabel} (${analysis.currentCycle.progressPct.toFixed(1)}%)`]),
        el('li', {}, [`② Xu hướng: ${analysis.overallTrend.reason}`]),
        el('li', {}, [`③ Elliott: ${analysis.elliott.summary}`]),
        el('li', {}, [`④ Tâm lý: ${analysis.psychology.description}`]),
      ]),
    ]));
  }

  unmount() {
    this.#unsub?.();
    this.#unsub = null;
    this.#container = null;
  }
}

export const AnalysisDashboardView = new AnalysisDashboardViewImpl();
