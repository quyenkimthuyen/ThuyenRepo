
/**
 * BTC 4-year halving cycle analysis view.
 * @module ui/CycleView
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import DataManager from '../data/DataManager.js';
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
import { renderCycleCompareTimeline } from './CycleCompareTimelineUi.js';

class CycleViewImpl {
  #unsub = null;
  #dataUnsub = null;

  mount(container) {
    container.innerHTML = '';
    container.classList.add('analysis-view');

    container.appendChild(renderAnalysisHeader(
      'Chu k\u1ef3 4 n\u0103m BTC',
      'X\u00e1c \u0111\u1ecbnh v\u1ecb tr\u00ed trong chu k\u1ef3 halving v\u00e0 c\u00e1c giai \u0111o\u1ea1n t\u00edch l\u0169y / t\u0103ng / ph\u00e2n ph\u1ed1i / gi\u1ea3m',
      'cycle'
    ));

    const body = el('div', { class: 'analysis-body', id: 'cycle-body' });
    container.appendChild(body);
    this.#render(body);
    this.#unsub = bus.on(Events.ANALYSIS_COMPLETE, () => this.#render(body));
    this.#dataUnsub = bus.on(Events.DATA_UPDATED, () => this.#render(body));
  }

  async #render(body) {
    const analysis = getLastAnalysis();
    body.innerHTML = '';

    if (!analysis) {
      body.appendChild(renderNoAnalysis());
      return;
    }

    const c = analysis.currentCycle;
    body.appendChild(renderMetricGrid([
      { label: 'Halving hiện tại', value: c.halvingLabel, hint: formatAnalysisDate(c.halvingTime) },
      { label: 'Tiến độ chu kỳ', value: `${c.progressPct.toFixed(1)}%`, color: c.phaseColor },
      { label: 'Giai đoạn', value: c.phaseLabel, color: c.phaseColor },
      { label: 'Ngày từ halving', value: String(c.daysSinceHalving) },
      { label: 'ĝến halving tiếp', value: `~${c.daysToNextHalving} ngày` },
      { label: 'Halving tiếp theo (ước tính)', value: formatAnalysisDate(c.nextHalvingEstimate) },
    ]));

    body.appendChild(el('div', { class: 'cycle-progress-bar' }, [
      el('div', {
        class: 'cycle-progress-fill',
        style: `width:${c.progressPct}%;background:${c.phaseColor}`,
      }),
    ]));

    const candles = await DataManager.getCandles('BTCUSD', analysis.timeframe ?? 'W');
    body.appendChild(renderCycleCompareTimeline(candles));

    const halvingRows = BTC_HALVING_EVENTS.map((h) => [
      h.label,
      formatAnalysisDate(h.timestamp),
      h.blockReward,
    ]);
    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Lịch sử Halving']));
    body.appendChild(renderTable(['Sự kiện', 'Ngày', 'Phần thưởng khối'], halvingRows));

    if (analysis.historicalCycles.length > 0) {
      const cycleRows = analysis.historicalCycles.map((hc) => [
        `#${hc.cycleIndex}`,
        formatAnalysisDate(hc.startTime),
        `$${hc.startPrice.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
        `$${hc.highPrice.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
        `$${hc.lowPrice.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
        formatPct(hc.changePct),
      ]);
      body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Hiệu suất theo chu kỳ']));
      body.appendChild(renderTable(
        ['Chu kỳ', 'Bắt đầu', 'Giá mở', 'ĝỉnh', 'ĝáy', 'Thay đổi'],
        cycleRows
      ));
    }

    body.appendChild(el('div', { class: 'cycle-phase-legend' }, [
      el('h3', { class: 'analysis-section-title' }, ['4 giai đoạn chu kỳ']),
      el('div', { class: 'cycle-phase-chips' }, [
        ['accumulation', 'Tích lũy'],
        ['markup', 'Tăng trưởng'],
        ['distribution', 'Phân phối'],
        ['markdown', 'Giảm giá'],
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
    this.#dataUnsub?.();
    this.#unsub = null;
    this.#dataUnsub = null;
  }
}

export const CycleView = new CycleViewImpl();
