
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
  #unsub = null;

  mount(container) {
    container.innerHTML = '';
    container.classList.add('analysis-view');

    container.appendChild(renderAnalysisHeader(
      'Sóng Elliott',
      'Đếm sóng xung (1-5) và điều chỉnh (ABC) dựa trên cấu trúc swing',
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
      : e.structure === 'correction' ? 'Điều chỉnh (Correction)' : 'Chưa xác định';

    body.appendChild(renderMetricGrid([
      { label: 'Cấu trúc', value: structureLabel },
      { label: 'Số sóng nhận diện', value: String(e.waves.length) },
      { label: 'Tóm tắt', value: e.waves.length > 0 ? `Sóng ${e.waves[e.waves.length - 1].waveNumber}` : '—', hint: e.summary },
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
      body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Chi tiết sóng']));
      body.appendChild(renderTable(
        ['Sóng', 'Bắt đầu', 'Kết thúc', 'Giá đầu', 'Giá cuối', '%', 'Tâm lý'],
        waveRows
      ));
    }

    body.appendChild(el('div', { class: 'analysis-info-box' }, [
      el('h4', {}, ['Quy tắc Elliott cơ bản']),
      el('ul', {}, [
        el('li', {}, ['Sóng 3 thường mạnh nhất, không ngắn nhất']),
        el('li', {}, ['Sóng 2 không vượt đáy sóng 1; sóng 4 không chồng sóng 1']),
        el('li', {}, ['Điều chỉnh ABC: A và C cùng hướng, B ngược hướng']),
        el('li', {}, ['Đây là heuristic nghiên cứu — nên xác nhận thủ công trên biểu đồ']),
      ]),
    ]));
  }

  unmount() {
    this.#unsub?.();
    this.#unsub = null;
  }
}

export const ElliottView = new ElliottViewImpl();
