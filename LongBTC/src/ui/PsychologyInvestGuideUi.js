/**
 * Psychology DCA invest guide UI blocks.
 * @module ui/PsychologyInvestGuideUi
 */

import { el } from '../utils/dom.js';
import { PSYCHOLOGY_PHASES } from '../analysis/BtcCycleConfig.js';
import {
  getPhaseInvestGuide,
  getAllPhaseInvestGuides,
  investTierLabel,
} from '../analysis/PsychologyInvestGuide.js';

const TIER_CLASS = {
  excellent: 'psych-invest-tier-excellent',
  good: 'psych-invest-tier-good',
  moderate: 'psych-invest-tier-moderate',
  cautious: 'psych-invest-tier-cautious',
  avoid: 'psych-invest-tier-avoid',
};

/**
 * @param {string} activePhaseId
 * @returns {HTMLElement}
 */
export function renderPsychologyInvestGuide(activePhaseId) {
  const current = getPhaseInvestGuide(activePhaseId);
  const wrap = el('div', { class: 'psych-invest-guide' });

  wrap.appendChild(el('p', { class: 'psych-invest-intro' }, [
    'Khuy\u1ebfn ngh\u1ecb DCA d\u00e0i h\u1ea1n d\u1ef1a tr\u00ean l\u1ecbch s\u1eed BTCUSD W (halving + neo ATH). ',
    'S\u1ed1 li\u1ec7u: l\u1ee3i nhu\u1eadn median sau 12/26 tu\u1ea7n khi mua t\u1ea1i giai \u0111o\u1ea1n \u0111\u00f3. ',
    'Kh\u00f4ng ph\u1ea3i l\u1eddi khuy\u00ean \u0111\u1ea7u t\u01b0.',
  ]));

  if (current) {
    wrap.appendChild(renderCurrentPhaseCard(current));
  }

  wrap.appendChild(el('h4', { class: 'psych-invest-subtitle' }, [
    'X\u1ebfp h\u1ea1ng theo hi\u1ec7u qu\u1ea3 l\u1ecbch s\u1eed (26 tu\u1ea7n)',
  ]));
  wrap.appendChild(renderInvestTable(activePhaseId));

  wrap.appendChild(el('h4', { class: 'psych-invest-subtitle' }, [
    'Chi ti\u1ebft t\u1eebng giai \u0111o\u1ea1n',
  ]));
  wrap.appendChild(renderInvestCards(activePhaseId));

  return wrap;
}

/**
 * @param {import('../analysis/PsychologyInvestGuide.js').PhaseInvestGuide} guide
 * @returns {HTMLElement}
 */
function renderCurrentPhaseCard(guide) {
  const phase = PSYCHOLOGY_PHASES.find((p) => p.id === guide.phaseId);
  const h = guide.historical;

  return el('div', {
    class: `psych-invest-current ${TIER_CLASS[guide.tier] ?? ''}`,
    style: phase ? `border-color:${phase.color}` : undefined,
  }, [
    el('div', { class: 'psych-invest-current-head' }, [
      el('span', { class: 'psych-invest-current-label' }, ['Giai \u0111o\u1ea1n hi\u1ec7n t\u1ea1i']),
      el('span', {
        class: 'psych-invest-tier-badge',
        style: phase ? `background:${phase.color}33;color:${phase.color}` : undefined,
      }, [investTierLabel(guide.tier)]),
    ]),
    el('p', { class: 'psych-invest-current-title' }, [
      phase?.labelVi ?? guide.phaseId,
      el('span', { class: 'psych-invest-current-en' }, [` (${phase?.label ?? ''})`]),
    ]),
    el('p', { class: 'psych-invest-summary' }, [guide.summaryVi]),
    el('p', { class: 'psych-invest-stance' }, [guide.dcaStance]),
    el('div', { class: 'psych-invest-metrics' }, [
      metricChip('Median 26w', `${h.forward26wMedianPct >= 0 ? '+' : ''}${h.forward26wMedianPct.toFixed(1)}%`),
      metricChip('Th\u1eafng 26w', `${h.forward26wWinRatePct.toFixed(0)}%`),
      metricChip('M\u1eabu', `${h.sampleWeeks} tu\u1ea7n`),
      metricChip('An to\u00e0n', `${guide.safetyScore}/5`),
      metricChip('Hi\u1ec7u qu\u1ea3', `${guide.effectivenessScore}/5`),
    ]),
    el('div', { class: 'psych-invest-columns' }, [
      el('div', { class: 'psych-invest-col' }, [
        el('strong', {}, ['N\u00ean l\u00e0m']),
        el('ul', { class: 'psych-invest-list' },
          guide.actionsVi.map((t) => el('li', {}, [t]))
        ),
      ]),
      el('div', { class: 'psych-invest-col' }, [
        el('strong', {}, ['R\u1ee7i ro']),
        el('ul', { class: 'psych-invest-list' },
          guide.risksVi.map((t) => el('li', {}, [t]))
        ),
      ]),
    ]),
  ]);
}

/**
 * @param {string} label
 * @param {string} value
 * @returns {HTMLElement}
 */
function metricChip(label, value) {
  return el('span', { class: 'psych-invest-metric', title: label }, [
    el('span', { class: 'psych-invest-metric-val' }, [value]),
    el('span', { class: 'psych-invest-metric-lbl' }, [label]),
  ]);
}

/**
 * @param {string} activePhaseId
 * @returns {HTMLElement}
 */
function renderInvestTable(activePhaseId) {
  const table = el('table', { class: 'psych-invest-table' });
  const guides = getAllPhaseInvestGuides()
    .sort((a, b) => b.historical.forward26wMedianPct - a.historical.forward26wMedianPct);

  table.appendChild(el('thead', {}, [
    el('tr', {}, [
      el('th', {}, ['Giai \u0111o\u1ea1n']),
      el('th', {}, ['\u0110\u00e1nh gi\u00e1']),
      el('th', {}, ['Med. 26w']),
      el('th', {}, ['% th\u1eafng']),
      el('th', {}, ['DCA']),
    ]),
  ]));

  const tbody = el('tbody');
  for (const g of guides) {
    const phase = PSYCHOLOGY_PHASES.find((p) => p.id === g.phaseId);
    const h = g.historical;
    const isActive = g.phaseId === activePhaseId;
    tbody.appendChild(el('tr', {
      class: `psych-invest-row${isActive ? ' is-active' : ''} ${TIER_CLASS[g.tier] ?? ''}`,
    }, [
      el('td', {}, [
        el('span', {
          class: 'psych-invest-phase-dot',
          style: phase ? `background:${phase.color}` : undefined,
        }),
        phase?.labelVi ?? g.phaseId,
      ]),
      el('td', {}, [investTierLabel(g.tier)]),
      el('td', {}, [`${h.forward26wMedianPct >= 0 ? '+' : ''}${h.forward26wMedianPct.toFixed(1)}%`]),
      el('td', {}, [`${h.forward26wWinRatePct.toFixed(0)}%`]),
      el('td', {}, [g.dcaStance.split(' \u2014 ')[0] ?? g.dcaStance]),
    ]));
  }
  table.appendChild(tbody);
  return el('div', { class: 'psych-invest-table-wrap' }, [table]);
}

/**
 * @param {string} activePhaseId
 * @returns {HTMLElement}
 */
function renderInvestCards(activePhaseId) {
  const grid = el('div', { class: 'psych-invest-grid' });
  for (const g of getAllPhaseInvestGuides()) {
    const phase = PSYCHOLOGY_PHASES.find((p) => p.id === g.phaseId);
    const isActive = g.phaseId === activePhaseId;
    grid.appendChild(el('div', {
      class: `psych-invest-card ${TIER_CLASS[g.tier] ?? ''}${isActive ? ' is-active' : ''}`,
      style: phase ? `border-left-color:${phase.color}` : undefined,
    }, [
      el('div', { class: 'psych-invest-card-head' }, [
        el('span', { class: 'psych-invest-card-title' }, [phase?.labelVi ?? g.phaseId]),
        el('span', { class: 'psych-invest-tier-badge' }, [investTierLabel(g.tier)]),
      ]),
      el('p', { class: 'psych-invest-card-stance' }, [g.dcaStance]),
      el('p', { class: 'psych-invest-card-stat' }, [
        `26w: ${g.historical.forward26wMedianPct >= 0 ? '+' : ''}${g.historical.forward26wMedianPct.toFixed(1)}% \u00b7 `,
        `${g.historical.forward26wWinRatePct.toFixed(0)}% th\u1eafng`,
      ]),
    ]));
  }
  return grid;
}
