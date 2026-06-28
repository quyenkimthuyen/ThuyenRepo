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

  mount(container) {
    container.innerHTML = '';
    container.classList.add('analysis-view');

    container.appendChild(renderAnalysisHeader(
      'S�ng Elliott',
      '??m s�ng xung (1-5) v� ?i?u ch?nh (ABC) d?a tr�n c?u tr�c swing',
      'elliott'
    ));

    const body = el('div', { class: 'analysis-body', id: 'elliott-body' });
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

    const e = analysis.elliott;
    const structureLabel = e.structure === 'impulse' ? 'Xung (Impulse)'
      : e.structure === 'correction' ? '?i?u ch?nh (Correction)' : 'Ch?a x�c ??nh';

    body.appendChild(renderMetricGrid([
      { label: 'C?u tr�c', value: structureLabel },
      { label: 'S? s�ng nh?n di?n', value: String(e.waves.length) },
      { label: 'T�m t?t', value: e.waves.length > 0 ? `S�ng ${e.waves[e.waves.length - 1].waveNumber}` : '�', hint: e.summary },
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
      body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Chi ti?t s�ng']));
      body.appendChild(renderTable(
        ['S�ng', 'B?t ??u', 'K?t th�c', 'Gi� ??u', 'Gi� cu?i', '%', 'T�m l�'],
        waveRows
      ));
    }

    body.appendChild(el('div', { class: 'analysis-info-box' }, [
      el('h4', {}, ['Quy t?c Elliott c? b?n']),
      el('ul', {}, [
        el('li', {}, ['S�ng 3 th??ng m?nh nh?t, kh�ng ng?n nh?t']),
        el('li', {}, ['S�ng 2 kh�ng v??t ?�y s�ng 1; s�ng 4 kh�ng ch?ng s�ng 1']),
        el('li', {}, ['?i?u ch?nh ABC: A v� C c�ng h??ng, B ng??c h??ng']),
        el('li', {}, ['?�y l� heuristic nghi�n c?u � n�n x�c nh?n th? c�ng tr�n bi?u ??']),
      ]),
    ]));
  }

  unmount() {
    this.#unsub?.();
    this.#unsub = null;
  }
}

export const ElliottView = new ElliottViewImpl();
