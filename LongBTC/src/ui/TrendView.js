/**
 * BTC trend analysis view.
 * @module ui/TrendView
 */
import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import { getLastAnalysis } from '../analysis/LongTermAnalysisEngine.js';
import { trendLabelVi } from '../analysis/TrendAnalyzer.js';
import { renderAnalysisHeader, renderMetricGrid, renderNoAnalysis, renderTable, formatAnalysisDate, formatPct } from './AnalysisViewHelpers.js';

class TrendViewImpl {
  #unsub = null;
  mount(container) {
    container.innerHTML = '';
    container.classList.add('analysis-view');
    container.appendChild(renderAnalysisHeader(
      'Xu hướng tăng / giảm / đi ngang',
      'Phân tích cấu trúc swing (HH/HL, LH/LL) và các đoạn xu hướng',
      'trend'
    ));
    const body = el('div', { class: 'analysis-body', id: 'trend-body' });
    container.appendChild(body);
    this.#render(body);
    this.#unsub = bus.on(Events.ANALYSIS_COMPLETE, () => this.#render(body));
  }
  #render(body) {
    const analysis = getLastAnalysis();
    body.innerHTML = '';
    if (!analysis) { body.appendChild(renderNoAnalysis()); return; }
    const t = analysis.overallTrend;
    const trendColor = t.direction === 'uptrend' ? '#22c55e' : t.direction === 'downtrend' ? '#ef4444' : '#94a3b8';
    body.appendChild(renderMetricGrid([
      { label: 'Xu hướng tổng thể', value: trendLabelVi(t.direction), color: trendColor, hint: t.reason },
      { label: 'Độ tin cậy', value: `${t.confidence}%` },
      { label: 'Số swing pivot', value: String(analysis.pivots.length) },
      { label: 'Số đoạn xu hướng', value: String(analysis.segments.length) },
    ]));
    const pivotRows = analysis.pivots.slice(-12).map((p) => [
      p.type === 'high' ? 'Đỉnh' : 'Đáy',
      formatAnalysisDate(p.timestamp),
      `$${p.price.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
      String(p.index),
    ]);
    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Swing gần nhất']));
    body.appendChild(renderTable(['Loại', 'Thời gian', 'Giá', 'Chỉ số nến'], pivotRows));
    const segRows = analysis.segments.slice(-10).map((s) => [
      trendLabelVi(s.direction), formatAnalysisDate(s.startTime), formatAnalysisDate(s.endTime),
      formatPct(s.changePct), String(s.durationBars),
    ]);
    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Đoạn xu hướng']));
    body.appendChild(renderTable(['Hướng', 'Bắt đầu', 'Kết thúc', 'Thay đổi', 'Số nến'], segRows));
    body.appendChild(el('div', { class: 'analysis-info-box' }, [
      el('h4', {}, ['Cách đọc']),
      el('ul', {}, [
        el('li', {}, ['Xu hướng tăng: Higher High (HH) + Higher Low (HL)']),
        el('li', {}, ['Xu hƱớng giảm: Lower High (LH) + Lower Low (LL)']),
        el('li', {}, ['Đi ngang: cấu trúc swing hỗn hợp hoặc phân kỳ']),
      ]),
    ]));
  }
  unmount() { this.#unsub?.(); this.#unsub = null; }
}
export const TrendView = new TrendViewImpl();
