from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def w(rel, s):
    text = s.encode("utf-8").decode("unicode_escape")
    (ROOT / rel).write_text(text, encoding="utf-8")
    print(rel, "OK" if "\ufffd" not in text and "??" not in text else "CHECK")


w(
    "src/ui/CycleView.js",
    r"""
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
  #unsub = null;

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
  }

  #render(body) {
    const analysis = getLastAnalysis();
    body.innerHTML = '';

    if (!analysis) {
      body.appendChild(renderNoAnalysis());
      return;
    }

    const c = analysis.currentCycle;
    body.appendChild(renderMetricGrid([
      { label: 'Halving hi\u1ec7n t\u1ea1i', value: c.halvingLabel, hint: formatAnalysisDate(c.halvingTime) },
      { label: 'Ti\u1ebfn \u0111\u1ed9 chu k\u1ef3', value: `${c.progressPct.toFixed(1)}%`, color: c.phaseColor },
      { label: 'Giai \u0111o\u1ea1n', value: c.phaseLabel, color: c.phaseColor },
      { label: 'Ng\u00e0y t\u1eeb halving', value: String(c.daysSinceHalving) },
      { label: '\u0110\u1ebfn halving ti\u1ebfp', value: `~${c.daysToNextHalving} ng\u00e0y` },
      { label: 'Halving ti\u1ebfp theo (\u01b0\u1edbc t\u00ednh)', value: formatAnalysisDate(c.nextHalvingEstimate) },
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
    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['L\u1ecbch s\u1eed Halving']));
    body.appendChild(renderTable(['S\u1ef1 ki\u1ec7n', 'Ng\u00e0y', 'Ph\u1ea7n th\u01b0\u1edfng kh\u1ed1i'], halvingRows));

    if (analysis.historicalCycles.length > 0) {
      const cycleRows = analysis.historicalCycles.map((hc) => [
        `#${hc.cycleIndex}`,
        formatAnalysisDate(hc.startTime),
        `$${hc.startPrice.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
        `$${hc.highPrice.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
        `$${hc.lowPrice.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
        formatPct(hc.changePct),
      ]);
      body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Hi\u1ec7u su\u1ea5t theo chu k\u1ef3']));
      body.appendChild(renderTable(
        ['Chu k\u1ef3', 'B\u1eaft \u0111\u1ea7u', 'Gi\u00e1 m\u1edf', '\u0110\u1ec9nh', '\u0110\u00e1y', 'Thay \u0111\u1ed5i'],
        cycleRows
      ));
    }

    body.appendChild(el('div', { class: 'cycle-phase-legend' }, [
      el('h3', { class: 'analysis-section-title' }, ['4 giai \u0111o\u1ea1n chu k\u1ef3']),
      el('div', { class: 'cycle-phase-chips' }, [
        ['accumulation', 'T\u00edch l\u0169y'],
        ['markup', 'T\u0103ng tr\u01b0\u1edfng'],
        ['distribution', 'Ph\u00e2n ph\u1ed1i'],
        ['markdown', 'Gi\u1ea3m gi\u00e1'],
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
""",
)

w(
    "src/ui/ElliottView.js",
    r"""
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
      'S\u00f3ng Elliott',
      '\u0110\u1ebfm s\u00f3ng xung (1-5) v\u00e0 \u0111i\u1ec1u ch\u1ec9nh (ABC) d\u1ef1a tr\u00ean c\u1ea5u tr\u00fac swing',
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
      : e.structure === 'correction' ? '\u0110i\u1ec1u ch\u1ec9nh (Correction)' : 'Ch\u01b0a x\u00e1c \u0111\u1ecbnh';

    body.appendChild(renderMetricGrid([
      { label: 'C\u1ea5u tr\u00fac', value: structureLabel },
      { label: 'S\u1ed1 s\u00f3ng nh\u1eadn di\u1ec7n', value: String(e.waves.length) },
      { label: 'T\u00f3m t\u1eaft', value: e.waves.length > 0 ? `S\u00f3ng ${e.waves[e.waves.length - 1].waveNumber}` : '\u2014', hint: e.summary },
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
      body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Chi ti\u1ebft s\u00f3ng']));
      body.appendChild(renderTable(
        ['S\u00f3ng', 'B\u1eaft \u0111\u1ea7u', 'K\u1ebft th\u00fac', 'Gi\u00e1 \u0111\u1ea7u', 'Gi\u00e1 cu\u1ed1i', '%', 'T\u00e2m l\u00fd'],
        waveRows
      ));
    }

    body.appendChild(el('div', { class: 'analysis-info-box' }, [
      el('h4', {}, ['Quy t\u1eafc Elliott c\u01a1 b\u1ea3n']),
      el('ul', {}, [
        el('li', {}, ['S\u00f3ng 3 th\u01b0\u1eddng m\u1ea1nh nh\u1ea5t, kh\u00f4ng ng\u1eafn nh\u1ea5t']),
        el('li', {}, ['S\u00f3ng 2 kh\u00f4ng v\u01b0\u1ee3t \u0111\u00e1y s\u00f3ng 1; s\u00f3ng 4 kh\u00f4ng ch\u1ed3ng s\u00f3ng 1']),
        el('li', {}, ['\u0110i\u1ec1u ch\u1ec9nh ABC: A v\u00e0 C c\u00f9ng h\u01b0\u1edbng, B ng\u01b0\u1ee3c h\u01b0\u1edbng']),
        el('li', {}, ['\u0110\u00e2y l\u00e0 heuristic nghi\u00ean c\u1ee9u \u2014 n\u00ean x\u00e1c nh\u1eadn th\u1ee7 c\u00f4ng tr\u00ean bi\u1ec3u \u0111\u1ed3']),
      ]),
    ]));
  }

  unmount() {
    this.#unsub?.();
    this.#unsub = null;
  }
}

export const ElliottView = new ElliottViewImpl();
""",
)

w(
    "src/ui/PsychologyView.js",
    r"""
/**
 * Market psychology cycle view.
 * @module ui/PsychologyView
 */

import { bus, Events } from '../core/EventBus.js';
import { el } from '../utils/dom.js';
import { getLastAnalysis } from '../analysis/LongTermAnalysisEngine.js';
import { PSYCHOLOGY_PHASES } from '../analysis/BtcCycleConfig.js';
import {
  renderAnalysisHeader,
  renderMetricGrid,
  renderNoAnalysis,
} from './AnalysisViewHelpers.js';

class PsychologyViewImpl {
  #unsub = null;

  mount(container) {
    container.innerHTML = '';
    container.classList.add('analysis-view');

    container.appendChild(renderAnalysisHeader(
      'Chu k\u1ef3 t\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng',
      'X\u00e1c \u0111\u1ecbnh giai \u0111o\u1ea1n t\u00e2m l\u00fd d\u1ef1a tr\u00ean chu k\u1ef3 4 n\u0103m, xu h\u01b0\u1edbng v\u00e0 s\u00f3ng Elliott',
      'psychology'
    ));

    const body = el('div', { class: 'analysis-body', id: 'psychology-body' });
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

    const p = analysis.psychology;

    body.appendChild(el('div', {
      class: 'psychology-hero',
      style: `border-color:${p.color}`,
    }, [
      el('span', { class: 'psychology-hero-label' }, ['Giai \u0111o\u1ea1n hi\u1ec7n t\u1ea1i']),
      el('span', { class: 'psychology-hero-value', style: `color:${p.color}` }, [p.labelVi]),
      el('span', { class: 'psychology-hero-en' }, [p.label]),
      el('span', { class: 'psychology-hero-confidence' }, [`${p.confidence}% tin c\u1eady`]),
    ]));

    body.appendChild(el('p', { class: 'psychology-description' }, [p.description]));

    body.appendChild(renderMetricGrid([
      { label: '\u0110\u00f3ng g\u00f3p t\u1eeb chu k\u1ef3', value: analysis.currentCycle.phaseLabel, hint: p.cycleContribution },
      { label: '\u0110\u00f3ng g\u00f3p t\u1eeb xu h\u01b0\u1edbng', value: analysis.overallTrend.direction, hint: p.trendContribution },
      { label: '\u0110\u00f3ng g\u00f3p t\u1eeb Elliott', value: p.waveContribution },
    ]));

    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['V\u00f2ng t\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng']));
    body.appendChild(this.#renderWheel(p.phaseId));

    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Timeline chu k\u1ef3 t\u00e2m l\u00fd']));
    body.appendChild(this.#renderTimeline(analysis));
  }

  #renderWheel(activePhaseId) {
    const wheel = el('div', { class: 'psychology-wheel' });
    for (const phase of PSYCHOLOGY_PHASES) {
      const isActive = phase.id === activePhaseId;
      wheel.appendChild(el('div', {
        class: `psychology-wheel-item${isActive ? ' active' : ''}`,
        style: isActive ? `background:${phase.color}22;border-color:${phase.color}` : undefined,
      }, [
        el('span', { class: 'psychology-wheel-vi' }, [phase.labelVi]),
        el('span', { class: 'psychology-wheel-en' }, [phase.label]),
      ]));
    }
    return wheel;
  }

  #renderTimeline(analysis) {
    const track = el('div', { class: 'psychology-timeline' });
    const progress = analysis.currentCycle.progressPct;

    for (const item of analysis.psychologyTimeline) {
      track.appendChild(el('div', {
        class: 'psychology-timeline-segment',
        style: `flex:${item.endPct - item.startPct};background:${item.phase.color}33`,
        title: `${item.phase.labelVi} (${item.startPct.toFixed(0)}\u2013${item.endPct.toFixed(0)}%)`,
      }, [
        el('span', { class: 'psychology-timeline-label' }, [item.phase.labelVi]),
      ]));
    }

    return el('div', { class: 'psychology-timeline-wrap' }, [
      track,
      el('div', {
        class: 'psychology-timeline-marker',
        style: `left:${Math.min(99, progress)}%`,
        title: `V\u1ecb tr\u00ed hi\u1ec7n t\u1ea1i: ${progress.toFixed(1)}%`,
      }),
    ]);
  }

  unmount() {
    this.#unsub?.();
    this.#unsub = null;
  }
}

export const PsychologyView = new PsychologyViewImpl();
""",
)

w(
    "src/ui/AnalysisDashboardView.js",
    r"""
/**
 * BTC long-term analysis dashboard.
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
  #container = null;
  #unsub = null;

  mount(container) {
    this.#container = container;
    container.innerHTML = '';
    container.classList.add('analysis-view');

    container.appendChild(renderAnalysisHeader(
      'T\u1ed5ng quan nghi\u00ean c\u1ee9u BTC',
      'Chu k\u1ef3 4 n\u0103m \u2192 Xu h\u01b0\u1edbng \u2192 S\u00f3ng Elliott \u2192 Chu k\u1ef3 t\u00e2m l\u00fd th\u1ecb tr\u01b0\u1eddng',
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

  unmount() {
    this.#unsub?.();
    this.#unsub = null;
    this.#container = null;
  }
}

export const AnalysisDashboardView = new AnalysisDashboardViewImpl();
""",
)

w(
    "src/ui/TrendView.js",
    r"""
/**
 * BTC trend analysis view.
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
  #unsub = null;

  mount(container) {
    container.innerHTML = '';
    container.classList.add('analysis-view');
    container.appendChild(renderAnalysisHeader(
      'Xu h\u01b0\u1edbng t\u0103ng / gi\u1ea3m / \u0111i ngang',
      'Ph\u00e2n t\u00edch c\u1ea5u tr\u00fac swing (HH/HL, LH/LL) v\u00e0 c\u00e1c \u0111o\u1ea1n xu h\u01b0\u1edbng',
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
    if (!analysis) {
      body.appendChild(renderNoAnalysis());
      return;
    }
    const t = analysis.overallTrend;
    const trendColor = t.direction === 'uptrend' ? '#22c55e'
      : t.direction === 'downtrend' ? '#ef4444' : '#94a3b8';
    body.appendChild(renderMetricGrid([
      { label: 'Xu h\u01b0\u1edbng t\u1ed5ng th\u1ec3', value: trendLabelVi(t.direction), color: trendColor, hint: t.reason },
      { label: '\u0110\u1ed9 tin c\u1eady', value: `${t.confidence}%` },
      { label: 'S\u1ed1 swing pivot', value: String(analysis.pivots.length) },
      { label: 'S\u1ed1 \u0111o\u1ea1n xu h\u01b0\u1edbng', value: String(analysis.segments.length) },
    ]));
    const pivotRows = analysis.pivots.slice(-12).map((p) => [
      p.type === 'high' ? '\u0110\u1ec9nh' : '\u0110\u00e1y',
      formatAnalysisDate(p.timestamp),
      `$${p.price.toLocaleString('en-US', { maximumFractionDigits: 0 })}`,
      String(p.index),
    ]);
    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['Swing g\u1ea7n nh\u1ea5t']));
    body.appendChild(renderTable(['Lo\u1ea1i', 'Th\u1eddi gian', 'Gi\u00e1', 'Ch\u1ec9 s\u1ed1 n\u1ebfn'], pivotRows));
    const segRows = analysis.segments.slice(-10).map((s) => [
      trendLabelVi(s.direction),
      formatAnalysisDate(s.startTime),
      formatAnalysisDate(s.endTime),
      formatPct(s.changePct),
      String(s.durationBars),
    ]);
    body.appendChild(el('h3', { class: 'analysis-section-title' }, ['\u0110o\u1ea1n xu h\u01b0\u1edbng']));
    body.appendChild(renderTable(
      ['H\u01b0\u1edbng', 'B\u1eaft \u0111\u1ea7u', 'K\u1ebft th\u00fac', 'Thay \u0111\u1ed5i', 'S\u1ed1 n\u1ebfn'],
      segRows
    ));
    body.appendChild(el('div', { class: 'analysis-info-box' }, [
      el('h4', {}, ['C\u00e1ch \u0111\u1ecdc']),
      el('ul', {}, [
        el('li', {}, ['Xu h\u01b0\u1edbng t\u0103ng: Higher High (HH) + Higher Low (HL)']),
        el('li', {}, ['Xu h\u01b0\u1edbng gi\u1ea3m: Lower High (LH) + Lower Low (LL)']),
        el('li', {}, ['\u0110i ngang: c\u1ea5u tr\u00fac swing h\u1ed7n h\u1ee3p ho\u1eb7c ph\u00e2n k\u1ef3']),
      ]),
    ]));
  }

  unmount() {
    this.#unsub?.();
    this.#unsub = null;
  }
}

export const TrendView = new TrendViewImpl();
""",
)
