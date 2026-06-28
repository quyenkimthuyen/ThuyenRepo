/**
 * BTC long-term analysis dashboard � overview of cycle, trend, Elliott, psychology.
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
  /** @type {HTMLElement|null} */
  #container = null;

  /** @type {Function|null} */
  #unsub = null;

  mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.add('analysis-view');

    container.appendChild(renderAnalysisHeader(
      'T?ng quan nghi�n c?u BTC',
      'Chu k? 4 n?m ② Xu h??ng ? S�ng Elliott ① Chu k? t�m l� th? tr??ng',
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
      el('h3', {}, ['T�m t?t ph�n t�ch']),
      el('p', {}, [analysis.summary]),
    ]));

    body.appendChild(el('div', { class: 'analysis-pipeline' }, [
      el('h3', {}, ['Quy tr�nh ph�n t�ch']),
      el('ol', { class: 'analysis-pipeline-steps' }, [
        el('li', {}, [`① Chu k? halving: ${analysis.currentCycle.phaseLabel} (${analysis.currentCycle.progressPct.toFixed(1)}%)`]),
        el('li', {}, [`② Xu h??ng: ${analysis.overallTrend.reason}`]),
        el('li', {}, [`③ Elliott: ${analysis.elliott.summary}`]),
        el('li', {}, [`? T�m l�: ${analysis.psychology.description}`]),
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
