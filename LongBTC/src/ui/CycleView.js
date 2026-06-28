/**
 * BTC 4-year halving cycle analysis view.
 * @module ui/CycleView
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import { BTC_HALVING_EVENTS } from '../analysis/BtcCycleConfig.js';
import { getLastAnalysis } from '../analysis/LongTermAnalysisEngine.js';
import {
  renderAnalysisHeader,
  renderMetricGrid,
  renderNoAnalysis,
  renderTable,
  formatAnalysisDate,
  formatPct,
} from './AnalysisViewHelpers.js';
import { cyclePhaseColor } from '../chart/AnalysisOverlay.js';

class CycleViewImpl {
  /** @type {Function|null} */
  #unsub = null;

  /**
   * @param {HTMLElement} container
   */
  mount(container) {
    container.innerHTML = '';
    container.classList.add('analysis-view');

    container.appendChild(renderAnalysisHeader(
      'Chu k? 4 n?m BTC',
      'Xác ??nh v? trí trong chu k? halving và các giai ?o?n tích l?y / t?ng / phân ph?i / gi?m',
      'cycle'
    ));

    const body = el('div', { class: 'analysis-body', id: 'cycle-body' });
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

    const c = analysis.currentCycle;
    body.appendChild(renderMetricGrid([
      { label: 'Halving hi?n t?i', value: c.halvingLabel, hint: formatAnalysisDate(c.halvingTime) },
      { label: 'Ti?n ?? chu k?', value: `${c.progressPct.toFixed(1)}%`, color: c.phaseColor },
      { label: 'Giai ?o?n', value: c.phaseLabel, color: c.phaseColor },
      { label: 'Ngày t? halving', value: String(c.daysSinceHalving) },
      { label: '??n halving ti?p', value: `~${c.daysToNextHalving} ngày` },
      {
        label: 'Halving ti?p theo (??c tính)',
        value: formatAnalysisDate(c.nextHalvingEstimate),
      },
    ]));

    body.appendChild(el('div', { class: 'cycle-progress-bar' }, [
      el('div', {
        class: 'cycle-progress-fill',
        style: `width:${c.progressPct}%;background:${c.phaseColor}`,
      }),
    ]));

    const halvingRows = BTC_HALVING_EVENTS.map((h) => [
      h.label,
      formatAnalysisDate(h.timestamp),
      h.blockReward,
    ]);
    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['L?ch s? Halving']));
    body.appendChild(renderTable(['S? ki?n', 'Ngày', 'Ph?n th??ng kh?i'], halvingRows));

    if (analysis.historicalCycles.length > 0) {
      const cycleRows = analysis.historicalCycles.map((hc) => [
        `#${hc.cycleIndex}`,
        formatAnalysisDate(hc.startTime),
        `$${hc.startPrice.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
        `$${hc.highPrice.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
        `$${hc.lowPrice.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
        formatPct(hc.changePct),
      ]);
      body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Hi?u su?t theo chu k?']));
      body.appendChild(renderTable(
        ['Chu k?', 'B?t ??u', 'Giá m?', '??nh', '?áy', 'Thay ??i'],
        cycleRows
      ));
    }

    body.appendChild(el('div', { class: 'cycle-phase-legend' }, [
      el('h3', { class: 'analysis-section-title' }, ['4 giai ?o?n chu k?']),
      el('div', { class: 'cycle-phase-chips' }, [
        ['accumulation', 'Tích l?y'],
        ['markup', 'T?ng tr??ng'],
        ['distribution', 'Phân ph?i'],
        ['markdown', 'Gi?m giá'],
      ].map(([phase, label]) =>
        el('span', {
          class: 'cycle-phase-chip',
          style: `border-color:${cyclePhaseColor(phase)};color:${cyclePhaseColor(phase)}`,
        }, [label])
      )),
    ]));
  }

  unmount() {
    this.#unsub?.();
    this.#unsub = null;
  }
}

export const CycleView = new CycleViewImpl();
