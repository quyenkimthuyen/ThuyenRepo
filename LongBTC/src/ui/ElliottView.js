/**
 * Elliott Wave analysis view.
 * @module ui/ElliottView
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import { getLastAnalysis } from '../analysis/LongTermAnalysisEngine.js';
import { wavePsychologyHint } from '../analysis/ElliottWaveAnalyzer.js';
import {
  renderAnalysisHeader,
  renderMetricGrid,
  renderNoAnalysis,
  renderTable,
  formatAnalysisDate,
  formatPct,
} from './AnalysisViewHelpers.js';

class ElliottViewImpl {
  /** @type {Function|null} */
  #unsub = null;

  /**
   * @param {HTMLElement} container
   */
  mount(container) {
    container.innerHTML = '';
    container.classList.add('analysis-view');

    container.appendChild(renderAnalysisHeader(
      'Sóng Elliott',
      '??m sóng xung (1-5) và ?i?u ch?nh (ABC) d?a trên c?u trúc swing',
      'elliott'
    ));

    const body = el('div', { class: 'analysis-body', id: 'elliott-body' });
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

    const e = analysis.elliott;
    const structureLabel = e.structure === 'impulse' ? 'Xung (Impulse)'
      : e.structure === 'correction' ? '?i?u ch?nh (Correction)' : 'Ch?a xác ??nh';

    body.appendChild(renderMetricGrid([
      { label: 'C?u trúc', value: structureLabel },
      { label: 'S? sóng nh?n di?n', value: String(e.waves.length) },
      { label: 'Tóm t?t', value: e.waves.length > 0 ? `Sóng ${e.waves[e.waves.length - 1].waveNumber}` : '—', hint: e.summary },
    ]));

    body.appendChild(el('p', { class: 'analysis-note' }, [e.summary]));

    if (e.waves.length > 0) {
      const waveRows = e.waves.map((w) => [
        w.label,
        formatAnalysisDate(w.startTime),
        formatAnalysisDate(w.endTime),
        `$${w.startPrice.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
        `$${w.endPrice.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
        formatPct(((w.endPrice - w.startPrice) / w.startPrice) * 100),
        wavePsychologyHint(w.waveNumber, analysis.overallTrend.direction),
      ]);
      body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Chi ti?t sóng']));
      body.appendChild(renderTable(
        ['Sóng', 'B?t ??u', 'K?t thúc', 'Giá ??u', 'Giá cu?i', '%', 'Tâm lý'],
        waveRows
      ));
    }

    body.appendChild(el('div', { class: 'analysis-info-box' }, [
      el('h4', {}, ['Quy t?c Elliott c? b?n']),
      el('ul', {}, [
        el('li', {}, ['Sóng 3 th??ng m?nh nh?t, không ng?n nh?t']),
        el('li', {}, ['Sóng 2 không v??t ?áy sóng 1; sóng 4 không ch?ng sóng 1']),
        el('li', {}, ['?i?u ch?nh ABC: A và C cùng h??ng, B ng??c h??ng']),
        el('li', {}, ['?ây là heuristic nghiên c?u — nên xác nh?n th? công trên bi?u ??']),
      ]),
    ]));
  }

  unmount() {
    this.#unsub?.();
    this.#unsub = null;
  }
}

export const ElliottView = new ElliottViewImpl();
