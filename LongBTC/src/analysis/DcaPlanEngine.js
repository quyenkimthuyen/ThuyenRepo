/**
 * Personal DCA plan + phase-based sizing (research framework, not financial advice).
 * @module analysis/DcaPlanEngine
 */

import { loadFromStorage, saveToStorage } from '../utils/dom.js';
import { PSYCHOLOGY_PHASES } from './BtcCycleConfig.js';
import { getPhaseInvestGuide, investTierLabel } from './PsychologyInvestGuide.js';

/**
 * @typedef {{
 *   monthlyBudgetUsd: number,
 *   targetBtcPct: number,
 *   currentBtcPct: number|null,
 *   notes: string,
 * }} DcaPlan
 * @typedef {{
 *   plan: DcaPlan,
 *   phaseId: string,
 *   phaseLabelVi: string,
 *   tier: string,
 *   tierLabelVi: string,
 *   multiplier: number,
 *   baseMonthlyUsd: number,
 *   suggestedMonthlyUsd: number,
 *   actionVi: string,
 *   allocationGapPct: number|null,
 *   stressNoteVi: string|null,
 * }} DcaRecommendation
 */

const STORAGE_KEY = 'longbtc_dca_plan';

/** @type {Record<string, number>} */
export const TIER_DCA_MULTIPLIER = Object.freeze({
  excellent: 1.5,
  good: 1.0,
  moderate: 0.75,
  cautious: 0.5,
  avoid: 0,
});

/** @returns {DcaPlan} */
export function defaultDcaPlan() {
  return {
    monthlyBudgetUsd: 500,
    targetBtcPct: 10,
    currentBtcPct: null,
    notes: '',
  };
}

/**
 * @param {Partial<DcaPlan>} [patch]
 * @returns {DcaPlan}
 */
export function loadDcaPlan(patch = {}) {
  const stored = loadFromStorage(STORAGE_KEY, null);
  const base = { ...defaultDcaPlan(), ...(stored && typeof stored === 'object' ? stored : {}) };
  return {
    monthlyBudgetUsd: Math.max(0, Number(patch.monthlyBudgetUsd ?? base.monthlyBudgetUsd) || 0),
    targetBtcPct: Math.min(100, Math.max(0, Number(patch.targetBtcPct ?? base.targetBtcPct) || 0)),
    currentBtcPct: patch.currentBtcPct !== undefined
      ? (patch.currentBtcPct == null || patch.currentBtcPct === ''
        ? null
        : Math.min(100, Math.max(0, Number(patch.currentBtcPct))))
      : base.currentBtcPct,
    notes: String(patch.notes ?? base.notes ?? ''),
  };
}

/**
 * @param {DcaPlan} plan
 */
export function saveDcaPlan(plan) {
  saveToStorage(STORAGE_KEY, plan);
}

/**
 * @param {string} phaseId
 * @param {DcaPlan} plan
 * @param {{ drawdownFromHighPct?: number|null }} [context]
 * @returns {DcaRecommendation}
 */
export function buildDcaRecommendation(phaseId, plan, context = {}) {
  const guide = getPhaseInvestGuide(phaseId);
  const phase = PSYCHOLOGY_PHASES.find((p) => p.id === phaseId);
  const tier = guide?.tier ?? 'moderate';
  const multiplier = TIER_DCA_MULTIPLIER[tier] ?? 0.75;
  const baseMonthlyUsd = plan.monthlyBudgetUsd;
  const suggestedMonthlyUsd = Math.round(baseMonthlyUsd * multiplier);

  let actionVi;
  if (multiplier === 0) {
    actionVi = 'T\u1ea1m d\u1eebng DCA m\u1edbi \u2014 \u01b0u ti\u00ean b\u1ea3o to\u00e0n v\u1ecb th\u1ebf';
  } else if (multiplier >= 1.25) {
    actionVi = 'C\u00f3 th\u1ec3 t\u0103ng DCA trong khung k\u1ebf ho\u1ea1ch (kh\u00f4ng vay, kh\u00f4ng all-in)';
  } else if (multiplier < 1) {
    actionVi = 'Gi\u1ea3m t\u1ed1c DCA so v\u1edbi k\u1ebf ho\u1ea1ch g\u1ed1c';
  } else {
    actionVi = 'Duy tr\u00ec DCA \u0111\u1ec1u theo k\u1ebf ho\u1ea1ch';
  }

  const allocationGapPct = plan.currentBtcPct != null
    ? plan.targetBtcPct - plan.currentBtcPct
    : null;

  let stressNoteVi = null;
  const dd = context.drawdownFromHighPct;
  if (plan.currentBtcPct != null && dd != null && Number.isFinite(dd) && dd < 0) {
    const furtherDrop = 50;
    const portfolioHit = (plan.currentBtcPct / 100) * furtherDrop;
    stressNoteVi = `N\u1ebfu BTC gi\u1ea3m th\u00eam ${furtherDrop}% t\u1eeb \u0111\u00e2y, danh m\u1ee5c c\u00f3 th\u1ec3 m\u1ea5t th\u00eam ~${portfolioHit.toFixed(1)}% (ch\u1ec9 ph\u1ea7n BTC).`;
  } else if (allocationGapPct != null && allocationGapPct > 5) {
    stressNoteVi = `B\u1ea1n \u0111ang thi\u1ebfu ~${allocationGapPct.toFixed(0)}% so v\u1edbi m\u1ee5c ti\u00eau ${plan.targetBtcPct}% BTC \u2014 DCA ki\u00ean nh\u1eabn, kh\u00f4ng v\u1ed9i.`;
  }

  return {
    plan,
    phaseId,
    phaseLabelVi: phase?.labelVi ?? phaseId,
    tier,
    tierLabelVi: investTierLabel(/** @type {import('./PsychologyInvestGuide.js').InvestTier} */ (tier)),
    multiplier,
    baseMonthlyUsd,
    suggestedMonthlyUsd,
    actionVi,
    allocationGapPct,
    stressNoteVi,
  };
}

/**
 * @param {import('./LongTermAnalysisEngine.js').LongTermAnalysisResult} analysis
 * @param {DcaPlan} [plan]
 * @returns {DcaRecommendation}
 */
export function recommendFromAnalysis(analysis, plan = loadDcaPlan()) {
  return buildDcaRecommendation(
    analysis.psychology.phaseId,
    plan,
    { drawdownFromHighPct: analysis.cycleExtremes.drawdownFromHighPct }
  );
}
