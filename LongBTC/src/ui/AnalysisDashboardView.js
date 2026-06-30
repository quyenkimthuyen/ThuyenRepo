
/**
 * BTC long-term analysis dashboard.
 * @module ui/AnalysisDashboardView
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import DataManager from '../data/DataManager.js';
import { getLastAnalysis } from '../analysis/LongTermAnalysisEngine.js';
import {
  renderAnalysisHeader,
  renderMetricGrid,
  renderNoAnalysis,
  buildDashboardMetrics,
} from './AnalysisViewHelpers.js';
import { renderDcaPlanPanel } from './DcaPlanPanel.js';
import { renderDataFreshnessBanner } from './DataFreshnessUi.js';
import { renderCycleCompareTimeline } from './CycleCompareTimelineUi.js';

class AnalysisDashboardViewImpl {
  #container = null;
  #unsub = null;
  #dataUnsub = null;

  mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.add('analysis-view');

    container.appendChild(renderAnalysisHeader(
      'T\u1ed5ng quan nghi\u00ean c\u1ee9u BTC',
      'Chu k\u1ef3 4 n\u0103m \u2192 Xu h\u01b0\u1edbng \u2192 S\u00f3ng Elliott \u2192 Chu k\u1ef3 t\u00e2m l\u00fd',
      'dashboard'
    ));

    const body = el('div', { class: 'analysis-body', id: 'dashboard-body' });
    container.appendChild(body);
    this.#render(body);

    this.#unsub = bus.on(Events.ANALYSIS_COMPLETE, () => this.#render(body));
    this.#dataUnsub = bus.on(Events.DATA_UPDATED, () => this.#render(body));
  }

  async #render(body) {
    const analysis = getLastAnalysis();
    body.innerHTML = '';

    const freshnessSlot = el('div', { id: 'dashboard-freshness' });
    body.appendChild(freshnessSlot);
    await this.#paintFreshness(freshnessSlot, analysis?.timeframe ?? 'W');

    if (!analysis) {
      body.appendChild(renderNoAnalysis());
      return;
    }

    body.appendChild(renderMetricGrid(buildDashboardMetrics(analysis)));
    body.appendChild(renderCycleCompareTimeline());
    body.appendChild(renderDcaPlanPanel(analysis));

    body.appendChild(el('div', { class: 'analysis-summary-box' }, [
      el('h3', {}, ['T\u00f3m t\u1eaft ph\u00e2n t\u00edch']),
      el('p', {}, [analysis.summary]),
    ]));

    body.appendChild(el('div', { class: 'analysis-pipeline' }, [
      el('h3', {}, ['Quy tr\u00ecnh ph\u00e2n t\u00edch']),
      el('ol', { class: 'analysis-pipeline-steps' }, [
        el('li', {}, [`\u2460 Chu k\u1ef3 halving: ${analysis.currentCycle.phaseLabel} (${analysis.currentCycle.progressPct.toFixed(1)}%)`]),
        el('li', {}, [`\u2461 Xu h\u01b0\u1edbng: ${analysis.overallTrend.reason}`]),
        el('li', {}, [`\u2462 Elliott: ${analysis.elliott.summary}`]),
        el('li', {}, [`\u2463 T\u00e2m l\u00fd: ${analysis.psychology.description}`]),
      ]),
    ]));
  }

  /**
   * @param {HTMLElement} slot
   * @param {string} timeframe
   */
  async #paintFreshness(slot, timeframe) {
    const datasets = await DataManager.listDatasets();
    const meta = datasets.find((d) => d.symbol === 'BTCUSD' && d.timeframe === timeframe)
      ?? datasets.find((d) => d.symbol === 'BTCUSD' && d.timeframe === 'W');
    slot.innerHTML = '';
    if (meta?.lastTimestamp) {
      slot.appendChild(renderDataFreshnessBanner(meta.lastTimestamp, meta.timeframe, meta.symbol));
    }
  }

  unmount() {
    this.#unsub?.();
    this.#dataUnsub?.();
    this.#unsub = null;
    this.#dataUnsub = null;
    this.#container = null;
  }
}

export const AnalysisDashboardView = new AnalysisDashboardViewImpl();
