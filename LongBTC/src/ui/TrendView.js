/**
 * BTC trend analysis view — swing structure and trend segments.
 * @module ui/TrendView
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import { getLastAnalysis } from '../analysis/LongTermAnalysisEngine.js';
import { trendLabelVi } from '../analysis/TrendAnalyzer.js';
import {
  renderAnalysisHeader,
  renderMetricGrid,
  renderNoAnalysis,
  renderTable,
  formatAnalysisDate,
  formatPct,
} from './AnalysisViewHelpers.js';

class TrendViewImpl {
  /** @type {Function|null} */
  #unsub = null;

  /**
   * @param {HTMLElement} container
   */
  mount(container) {
    container.innerHTML = '';
    container.classList.add('analysis-view');

    container.appendChild(renderAnalysisHeader(
      'Xu h??ng t?ng / gi?m / ?i ngang',
      'Phân tích c?u trúc swing (HH/HL, LH/LL) và các ?o?n xu h??ng',
      'trend'
    ));

    const body = el('div', { class: 'analysis-body', id: 'trend-body' });
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

    const t = analysis.overallTrend;
    const trendColor = t.direction === 'uptrend' ? '#22c55e'
      : t.direction === 'downtrend' ? '#ef4444' : '#94a3b8';

    body.appendChild(renderMetricGrid([
      { label: 'Xu h??ng t?ng th?', value: trendLabelVi(t.direction), color: trendColor, hint: t.reason },
      { label: '?? tin c?y', value: `${t.confidence}%` },
      { label: 'S? swing pivot', value: String(analysis.pivots.length) },
      { label: 'S? ?o?n xu h??ng', value: String(analysis.segments.length) },
    ]));

    const pivotRows = analysis.pivots.slice(-12).map((p) => [
      p.type === 'high' ? '??nh' : '?áy',
      formatAnalysisDate(p.timestamp),
      `$${p.price.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
      String(p.index),
    ]);
    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Swing g?n nh?t']));
    body.appendChild(renderTable(['Lo?i', 'Th?i gian', 'Giá', 'Ch? s? n?n'], pivotRows));

    const segRows = analysis.segments.slice(-10).map((s) => [
      trendLabelVi(s.direction),
      formatAnalysisDate(s.startTime),
      formatAnalysisDate(s.endTime),
      formatPct(s.changePct),
      String(s.durationBars),
    ]);
    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['?o?n xu h??ng']));
    body.appendChild(renderTable(
      ['H??ng', 'B?t ??u', 'K?t thúc', 'Thay ??i', 'S? n?n'],
      segRows
    ));

    body.appendChild(el('div', { class: 'analysis-info-box' }, [
      el('h4', {}, ['Cách ??c']),
      el('ul', {}, [
        el('li', {}, ['Xu h??ng t?ng: Higher High (HH) + Higher Low (HL)']),
        el('li', {}, ['Xu h??ng gi?m: Lower High (LH) + Lower Low (LL)']),
        el('li', {}, ['?i ngang: c?u trúc swing h?n h?p ho?c phân k?']),
      ]),
    ]));
  }

  unmount() {
    this.#unsub?.();
    this.#unsub = null;
  }
}

export const TrendView = new TrendViewImpl();
