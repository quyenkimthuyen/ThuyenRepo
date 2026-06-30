/**
 * Personal DCA plan panel (dashboard).
 * @module ui/DcaPlanPanel
 */

import { el } from '../utils/dom.js';
import {
  loadDcaPlan,
  saveDcaPlan,
  recommendFromAnalysis,
} from '../analysis/DcaPlanEngine.js';

/**
 * @param {import('../analysis/LongTermAnalysisEngine.js').LongTermAnalysisResult} analysis
 * @param {{ onChange?: () => void }} [options]
 * @returns {HTMLElement}
 */
export function renderDcaPlanPanel(analysis, options = {}) {
  let plan = loadDcaPlan();
  const rec = () => recommendFromAnalysis(analysis, plan);

  const root = el('div', { class: 'dca-plan-panel' });

  function paintRecommendation() {
    const r = rec();
    const recEl = root.querySelector('.dca-plan-rec');
    if (!recEl) return;
    recEl.innerHTML = '';
    recEl.appendChild(el('div', { class: 'dca-plan-rec-head' }, [
      el('span', { class: 'dca-plan-rec-title' }, ['G\u1ee3i \u00fd th\u00e1ng n\u00e0y']),
      el('span', { class: `dca-plan-tier dca-plan-tier--${r.tier}` }, [r.tierLabelVi]),
    ]));
    recEl.appendChild(el('p', { class: 'dca-plan-rec-phase' }, [
      `Giai \u0111o\u1ea1n: ${analysis.psychology.labelVi} \u00b7 ${r.actionVi}`,
    ]));
    recEl.appendChild(el('div', { class: 'dca-plan-rec-amounts' }, [
      el('div', { class: 'dca-plan-amount' }, [
        el('span', { class: 'dca-plan-amount-val' }, [`$${r.suggestedMonthlyUsd.toLocaleString()}`]),
        el('span', { class: 'dca-plan-amount-lbl' }, ['DCA \u0111\u1ec1 xu\u1ea5t / th\u00e1ng']),
      ]),
      el('div', { class: 'dca-plan-amount' }, [
        el('span', { class: 'dca-plan-amount-val' }, [`${(r.multiplier * 100).toFixed(0)}%`]),
        el('span', { class: 'dca-plan-amount-lbl' }, ['so v\u1edbi k\u1ebf ho\u1ea1ch g\u1ed1c']),
      ]),
      el('div', { class: 'dca-plan-amount' }, [
        el('span', { class: 'dca-plan-amount-val' }, [
          r.allocationGapPct != null ? `${r.allocationGapPct >= 0 ? '+' : ''}${r.allocationGapPct.toFixed(0)}%` : '\u2014',
        ]),
        el('span', { class: 'dca-plan-amount-lbl' }, ['vs m\u1ee5c ti\u00eau allocation']),
      ]),
    ]));
    if (r.stressNoteVi) {
      recEl.appendChild(el('p', { class: 'dca-plan-stress' }, [r.stressNoteVi]));
    }
  }

  root.appendChild(el('h3', { class: 'dca-plan-title' }, ['K\u1ebf ho\u1ea1ch DCA c\u00e1 nh\u00e2n']));
  root.appendChild(el('p', { class: 'dca-plan-disclaimer' }, [
    'Khung nghi\u00ean c\u1ee9u \u2014 kh\u00f4ng ph\u1ea3i l\u1eddi khuy\u00ean \u0111\u1ea7u t\u01b0. \u0110i\u1ec1u ch\u1ec9nh theo t\u00ecnh h\u00ecnh t\u00e0i ch\u00ednh th\u1ef1c t\u1ebf.',
  ]));

  const form = el('div', { class: 'dca-plan-form' }, [
    field('DCA c\u01a1 s\u1edf / th\u00e1ng (USD)', 'number', String(plan.monthlyBudgetUsd), 'dca-budget', { min: '0', step: '50' }),
    field('M\u1ee5c ti\u00eau % BTC trong danh m\u1ee5c', 'number', String(plan.targetBtcPct), 'dca-target', { min: '0', max: '100', step: '1' }),
    field('% BTC hi\u1ec7n t\u1ea1i (tu\u1ef3 ch\u1ecdn)', 'number', plan.currentBtcPct != null ? String(plan.currentBtcPct) : '', 'dca-current', { min: '0', max: '100', step: '0.5', placeholder: 'VD: 8' }),
  ]);
  root.appendChild(form);

  root.appendChild(el('div', { class: 'dca-plan-rec' }));

  root.appendChild(el('button', {
    class: 'btn btn-secondary btn-sm dca-plan-save',
    type: 'button',
  }, ['L\u01b0u k\u1ebf ho\u1ea1ch']));

  form.addEventListener('input', () => {
    plan = readPlanFromForm(form);
  });

  root.querySelector('.dca-plan-save')?.addEventListener('click', () => {
    plan = readPlanFromForm(form);
    saveDcaPlan(plan);
    paintRecommendation();
    options.onChange?.();
  });

  paintRecommendation();
  return root;
}

/**
 * @param {string} label
 * @param {string} type
 * @param {string} value
 * @param {string} id
 * @param {Record<string, string>} [attrs]
 */
function field(label, type, value, id, attrs = {}) {
  return el('label', { class: 'dca-plan-field' }, [
    el('span', { class: 'dca-plan-field-label' }, [label]),
    el('input', {
      class: 'dca-plan-input',
      type,
      id,
      value,
      ...attrs,
    }),
  ]);
}

/**
 * @param {HTMLElement} form
 */
function readPlanFromForm(form) {
  const budget = Number(/** @type {HTMLInputElement} */ (form.querySelector('#dca-budget'))?.value);
  const target = Number(/** @type {HTMLInputElement} */ (form.querySelector('#dca-target'))?.value);
  const currentRaw = /** @type {HTMLInputElement} */ (form.querySelector('#dca-current'))?.value;
  return loadDcaPlan({
    monthlyBudgetUsd: budget,
    targetBtcPct: target,
    currentBtcPct: currentRaw === '' ? null : Number(currentRaw),
  });
}
