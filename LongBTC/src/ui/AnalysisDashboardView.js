/**
 * BTC long-term analysis dashboard — overview of cycle, trend, Elliott, psychology.
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

/**
 * Analysis dashboard view.
 */
class AnalysisDashboardViewImpl {
  /** @type {HTMLElement|null} */
  #container = null;

  /** @type {Function|null} */
  #unsub = null;

  /**
   * @param {HTMLElement} container
   */
  mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.add('analysis-view');

    container.appendChild(renderAnalysisHeader(
      'T?ng quan nghiên c?u BTC',
      'Chu k? 4 n?m ? Xu h??ng ? Sóng Elliott ? Chu k? tâm lý th? tr??ng',
      'dashboard'
    ));

    const body = el('div', { class: 'analysis-body', id: 'dashboard-body' });
    container.appendChild(body);
    this.#render(body);

    this.#unsub = bus.on(Events.ANALYSIS_COMPLETE, () => this.#render(body));
  }

  /**
   * @param {HTMLElement} body
   */
  #render(body) {
    const analysis = getLastAnalysis();
    body.innerHTML = '';

    if (!analysis) {
      body.appendChild(renderNoAnalysis());
      return;
    }

    body.appendChild(renderMetricGrid(buildDashboardMetrics(analysis)));

    body.appendChild(el('div', { class: 'analysis-summary-box' }, [
      el('h3', {}, ['Tóm t?t phân tích']),
      el('p', {}, [analysis.summary]),
    ]));

    body.appendChild(el('div', { class: 'analysis-pipeline' }, [
      el('h3', {}, ['Quy trình phân tích']),
      el('ol', { class: 'analysis-pipeline-steps' }, [
        el('li', {}, [`? Chu k? halving: ${analysis.currentCycle.phaseLabel} (${analysis.currentCycle.progressPct.toFixed(1)}%)`]),
        el('li', {}, [`? Xu h??ng: ${analysis.overallTrend.reason}`]),
        el('li', {}, [`? Elliott: ${analysis.elliott.summary}`]),
        el('li', {}, [`? Tâm lý: ${analysis.psychology.description}`]),
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
