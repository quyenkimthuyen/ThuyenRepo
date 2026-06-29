/**
 * DCA / long-hold research guide per psychology phase — calibrated on BTC weekly history.
 * @module analysis/PsychologyInvestGuide
 */

import { PSYCHOLOGY_PHASES } from './BtcCycleConfig.js';
import { psychologyBandAtTime } from './PsychologyBands.js';
import { analyzeCurrentCycle } from './HalvingCycleAnalyzer.js';

/**
 * @typedef {'excellent'|'good'|'moderate'|'cautious'|'avoid'} InvestTier
 * @typedef {{
 *   phaseId: string,
 *   safetyScore: number,
 *   effectivenessScore: number,
 *   tier: InvestTier,
 *   dcaStance: string,
 *   summaryVi: string,
 *   actionsVi: string[],
 *   risksVi: string[],
 *   historical: {
 *     sampleWeeks: number,
 *     forward12wMedianPct: number,
 *     forward26wMedianPct: number,
 *     forward26wWinRatePct: number,
 *   },
 * }} PhaseInvestGuide
 */

/** BTCUSD W, halving-adaptive phases, through Jun 2026 — offline calibration. */
const HISTORICAL_STATS = Object.freeze({
  hope: { sampleWeeks: 56, forward12wMedianPct: 15.3, forward26wMedianPct: 50.6, forward26wWinRatePct: 80 },
  relief: { sampleWeeks: 52, forward12wMedianPct: 18.3, forward26wMedianPct: 55.4, forward26wWinRatePct: 87 },
  optimism: { sampleWeeks: 32, forward12wMedianPct: 68.6, forward26wMedianPct: 37.1, forward26wWinRatePct: 91 },
  excitement: { sampleWeeks: 32, forward12wMedianPct: -16.2, forward26wMedianPct: 15.9, forward26wWinRatePct: 81 },
  thrill: { sampleWeeks: 51, forward12wMedianPct: 31.0, forward26wMedianPct: 22.2, forward26wWinRatePct: 63 },
  euphoria: { sampleWeeks: 53, forward12wMedianPct: -9.0, forward26wMedianPct: -39.6, forward26wWinRatePct: 25 },
  anxiety: { sampleWeeks: 40, forward12wMedianPct: -25.1, forward26wMedianPct: -31.7, forward26wWinRatePct: 0 },
  denial: { sampleWeeks: 32, forward12wMedianPct: -13.1, forward26wMedianPct: -17.9, forward26wWinRatePct: 38 },
  fear: { sampleWeeks: 33, forward12wMedianPct: -2.0, forward26wMedianPct: 32.6, forward26wWinRatePct: 58 },
  capitulation: { sampleWeeks: 35, forward12wMedianPct: 22.5, forward26wMedianPct: 61.1, forward26wWinRatePct: 86 },
  depression: { sampleWeeks: 35, forward12wMedianPct: -1.9, forward26wMedianPct: 37.9, forward26wWinRatePct: 60 },
});

/** @type {Record<string, Omit<PhaseInvestGuide, 'phaseId'|'historical'>>} */
const GUIDE_COPY = {
  hope: {
    safetyScore: 4,
    effectivenessScore: 4,
    tier: 'good',
    dcaStance: 'DCA \u0111\u1ec1u \u2014 x\u00e2y v\u1ecb th\u1ebf core',
    summaryVi: 'Sau halving / \u0111\u00e1y: l\u1ecbch s\u1eed cho l\u1ee3i nhu\u1eadn 26 tu\u1ea7n trung v\u1ecb ~+51%, th\u1eafng 80% m\u1eabu. An to\u00e0n t\u01b0\u01a1ng \u0111\u1ed1i cho t\u00edch l\u0169y d\u00e0i h\u1ea1n.',
    actionsVi: [
      'B\u1eaft \u0111\u1ea7u ho\u1eb7c duy tr\u00ec DCA theo k\u1ebf ho\u1ea1ch',
      'Chia 3\u20136 th\u00e1ng, kh\u00f4ng all-in',
      'Ghi r\u00f5 thesis halving 4 n\u0103m',
    ],
    risksVi: ['Sideway k\u00e9o d\u00e0i', 'Bi\u1ebfn \u0111\u1ed9ng v\u1eabn cao so v\u1edbi t\u00e0i s\u1ea3n truy\u1ec1n th\u1ed1ng'],
  },
  relief: {
    safetyScore: 4,
    effectivenessScore: 5,
    tier: 'excellent',
    dcaStance: 'DCA \u0111\u1ec1u \u2014 giai \u0111o\u1ea1n hi\u1ec7u qu\u1ea3 l\u1ecbch s\u1eed',
    summaryVi: 'Trung v\u1ecb 26 tu\u1ea7n ~+55%, t\u1ef7 l\u1ec7 th\u1eafng 87% \u2014 m\u1ed9t trong c\u00e1c v\u00f9ng t\u00edch l\u0169y t\u1ed1t nh\u1ea5t sau stress.',
    actionsVi: [
      'Ti\u1ebfp t\u1ee5c DCA n\u1ebfu ch\u01b0a \u0111\u1ee7 allocation',
      'T\u0103ng nh\u1eb9 size n\u1ebfu k\u1ebf ho\u1ea1ch cho ph\u00e9p',
    ],
    risksVi: ['\u0110\u1eebng t\u0103ng \u0111\u00f2n b\u1ea9y v\u00ec c\u1ea3m gi\u00e1c an to\u00e0n'],
  },
  optimism: {
    safetyScore: 3,
    effectivenessScore: 5,
    tier: 'good',
    dcaStance: 'DCA v\u1eeba ph\u1ea3i \u2014 uptrend r\u00f5',
    summaryVi: 'L\u1ee3i nhu\u1eadn ng\u1eafn h\u1ea1n m\u1ea1nh (median 12w ~+69%) nh\u01b0ng bi\u1ebfn \u0111\u1ed9ng t\u0103ng. 91% m\u1eabu d\u01b0\u01a1ng sau 26 tu\u1ea7n.',
    actionsVi: [
      'Gi\u1eef DCA nh\u01b0ng kh\u00f4ng t\u0103ng g\u1ea5p size',
      'Theo d\u00f5i xu h\u01b0\u1edbng swing',
    ],
    risksVi: ['FOMO t\u0103ng t\u1ed1c', 'Pullback 20\u201330% v\u1eabn th\u01b0\u1eddng g\u1eb7p'],
  },
  excitement: {
    safetyScore: 2,
    effectivenessScore: 2,
    tier: 'cautious',
    dcaStance: 'Gi\u1ea3m DCA \u2014 pullback ng\u1eafn h\u1ea1n th\u01b0\u1eddng \u00e2m',
    summaryVi: 'Median 12 tu\u1ea7n \u00e2m (-16%). D\u00e0i h\u01a1n c\u00f3 th\u1ec3 h\u1ed3i nh\u01b0ng entry ng\u1eafn h\u1ea1n k\u00e9m.',
    actionsVi: [
      'Ch\u1ec9 DCA ph\u1ea7n nh\u1ecf n\u1ebfu thi\u1ebfu v\u1ecb th\u1ebf',
      'Kh\u00f4ng vay mua',
    ],
    risksVi: ['Bull trap', 'T\u0103ng t\u1ed1c tr\u01b0\u1edbc khi r\u00f9ng'],
  },
  thrill: {
    safetyScore: 2,
    effectivenessScore: 3,
    tier: 'cautious',
    dcaStance: 'H\u1ea1n ch\u1ebf mua th\u00eam \u2014 g\u1ea7n \u0111\u1ec9nh',
    summaryVi: 'Trung v\u1ecb 26w ~+22% nh\u01b0ng ph\u00e2n b\u1ed1 r\u1ed9ng; 63% m\u1eabu th\u1eafng. R\u1ee7i ro \u0111\u1ea3o chi\u1ec1u t\u0103ng.',
    actionsVi: [
      'Gi\u1eef v\u1ecb th\u1ebf, kh\u00f4ng t\u0103ng m\u1ea1nh',
      'Chu\u1ea9n b\u1ecb k\u1ebf ho\u1ea1ch ch\u1ed1t l\u1eebng ph\u1ea7n',
    ],
    risksVi: ['\u0110\u00f2n b\u1ea9y h\u1ec7 th\u1ed1ng', 'Gi\u1ea3m 30\u201350% sau \u0111\u1ec9nh kh\u00f4ng hi\u1ebfm'],
  },
  euphoria: {
    safetyScore: 1,
    effectivenessScore: 1,
    tier: 'avoid',
    dcaStance: 'D\u1eebng mua th\u00eam \u2014 \u01b0u ti\u00ean b\u1ea3o to\u00e0n',
    summaryVi: 'L\u1ecbch s\u1eed x\u1ea5u nh\u1ea5t: median 26 tu\u1ea7n ~-40%, ch\u1ec9 25% m\u1eabu d\u01b0\u01a1ng. \u0110\u1ec9nh c\u1ea3m x\u00fac.',
    actionsVi: [
      'Ch\u1ed1t l\u1eebng ph\u1ea7n theo k\u1ebf ho\u1ea1ch',
      'Kh\u00f4ng DCA m\u1edbi',
      'Gi\u1ea3m \u0111\u00f2n b\u1ea9y',
    ],
    risksVi: ['Bear market 12\u201318 th\u00e1ng', 'M\u1ea5t 50%+ t\u1eeb \u0111\u1ec9nh'],
  },
  anxiety: {
    safetyScore: 1,
    effectivenessScore: 1,
    tier: 'avoid',
    dcaStance: 'Tr\u00e1nh mua m\u1edbi \u2014 ch\u1edd x\u00e1c nh\u1eadn',
    summaryVi: '0% m\u1eabu d\u01b0\u01a1ng sau 26 tu\u1ea7n trong l\u1ecbch s\u1eed; median ~-32%.',
    actionsVi: [
      'Kh\u00f4ng panic sell to\u00e0n b\u1ed9 n\u1ebfu thesis d\u00e0i h\u1ea1n',
      'Ch\u1edd giai \u0111o\u1ea1n fear/capitulation \u0111\u1ec3 DCA',
    ],
    risksVi: ['Ti\u1ebfp t\u1ee5c gi\u1ea3m s\u00e2u', 'B\u00e1n \u0111\u00e1y c\u1ea3m t\u00ednh'],
  },
  denial: {
    safetyScore: 1,
    effectivenessScore: 1,
    tier: 'avoid',
    dcaStance: 'Kh\u00f4ng b\u1eaft dao \u2014 DCA r\u1ea5t ch\u1eadm',
    summaryVi: 'Median 26w ~-18%, 38% th\u1eafng. Bear \u0111ang ti\u1ebfp di\u1ec5n.',
    actionsVi: [
      'Review allocation, gi\u1ea3m r\u1ee7i ro n\u1ebfu qu\u00e1 tr\u1ecdng',
      'Kh\u00f4ng average down m\u00f9',
    ],
    risksVi: ['Gi\u1ea3m th\u00eam 20\u201340%', 'Th\u1eddi gian h\u1ed3i ph\u1ee5c d\u00e0i'],
  },
  fear: {
    safetyScore: 3,
    effectivenessScore: 3,
    tier: 'moderate',
    dcaStance: 'DCA ch\u1eadm \u2014 v\u00f9ng chuy\u1ec3n bear\u2192t\u00edch',
    summaryVi: 'Median 26w ~+33%, 58% th\u1eafng. Bi\u1ebfn \u0111\u1ed9ng cao nh\u01b0ng b\u1eaft \u0111\u1ea7u c\u1ea3i thi\u1ec7n so v\u1edbi denial.',
    actionsVi: [
      'DCA nh\u1ecf \u0111\u1ec1u n\u1ebfu c\u00f2n runway d\u00e0i',
      'Tr\u00e1nh quy\u1ebft \u0111\u1ecbnh l\u00fac ho\u1ea3ng lo\u1ea1n',
    ],
    risksVi: ['C\u00f3 th\u1ec3 test l\u1ea1i \u0111\u00e1y', 'Tin x\u1ea5u li\u00ean ti\u1ebfp'],
  },
  capitulation: {
    safetyScore: 5,
    effectivenessScore: 5,
    tier: 'excellent',
    dcaStance: 'DCA t\u00edch c\u1ef1c (v\u1ed1n d\u01b0) \u2014 v\u00f9ng t\u1ed1t nh\u1ea5t l\u1ecbch s\u1eed',
    summaryVi: 'Median 26w ~+61%, 86% th\u1eafng \u2014 hi\u1ec7u qu\u1ea3 v\u00e0 an to\u00e0n nh\u1ea5t cho t\u00edch l\u0169y d\u00e0i h\u1ea1n.',
    actionsVi: [
      'T\u0103ng DCA c\u00f3 k\u1eb7 ho\u1ea1ch (kh\u00f4ng all-in 1 l\u1ea7n)',
      'Chia nhi\u1ec1u \u0111\u1ee3t trong 2\u20133 th\u00e1ng',
    ],
    risksVi: ['C\u00f3 th\u1ec3 \u0111au th\u00eam tr\u01b0\u1edbc khi \u0111\u00e1y', 'Kh\u00f4ng timing \u0111\u00e1y tuy\u1ec7t \u0111\u1ed1i'],
  },
  depression: {
    safetyScore: 4,
    effectivenessScore: 4,
    tier: 'good',
    dcaStance: 'DCA \u0111\u1ec1u \u2014 \u201cnh\u00e0m ch\u00e1n\u201d tr\u01b0\u1edbc halving',
    summaryVi: 'Median 26w ~+38%, 60% th\u1eafng. Sideway \u00e2m \u1ec9 nh\u01b0ng l\u1ecbch s\u1eed \u1ee9ng h\u1ed7 DCA ki\u00ean nh\u1eabn.',
    actionsVi: [
      'DCA t\u1ef1 \u0111\u1ed9ng, b\u1ecf qua noise',
      'Chu\u1ea9n b\u1ecb cho halving ti\u1ebfp theo',
    ],
    risksVi: ['K\u00e9o d\u00e0i nhi\u1ec1u th\u00e1ng', 'M\u1ea5t ki\u00ean nh\u1eabn'],
  },
};

const TIER_LABEL = {
  excellent: 'R\u1ea5t t\u1ed1t',
  good: 'T\u1ed1t',
  moderate: 'Trung b\u00ecnh',
  cautious: 'Th\u1eadn tr\u1ecdng',
  avoid: 'Tr\u00e1nh mua th\u00eam',
};

/**
 * @param {string} phaseId
 * @returns {PhaseInvestGuide|undefined}
 */
export function getPhaseInvestGuide(phaseId) {
  const copy = GUIDE_COPY[phaseId];
  const historical = HISTORICAL_STATS[phaseId];
  if (!copy || !historical) return undefined;

  return { phaseId, historical, ...copy };
}

/**
 * All guides sorted by historical effectiveness (26w median).
 * @returns {PhaseInvestGuide[]}
 */
export function getAllPhaseInvestGuides() {
  return PSYCHOLOGY_PHASES
    .map((p) => getPhaseInvestGuide(p.id))
    .filter((g) => g != null)
    .sort((a, b) => b.effectivenessScore - a.effectivenessScore
      || b.historical.forward26wMedianPct - a.historical.forward26wMedianPct);
}

/**
 * Top phases for DCA by historical 26w median return.
 * @param {number} [limit=5]
 * @returns {PhaseInvestGuide[]}
 */
export function getBestDcaPhases(limit = 5) {
  return [...getAllPhaseInvestGuides()]
    .sort((a, b) => b.historical.forward26wMedianPct - a.historical.forward26wMedianPct)
    .slice(0, limit);
}

/**
 * @param {InvestTier} tier
 * @returns {string}
 */
export function investTierLabel(tier) {
  return TIER_LABEL[tier] ?? tier;
}

/**
 * Recompute forward-return stats from candles (optional live refresh).
 * @param {import('../data/Candle.js').Candle[]} candles
 * @param {number} [horizonWeeks=26]
 * @returns {Record<string, { sampleWeeks: number, forward12wMedianPct: number, forward26wMedianPct: number, forward26wWinRatePct: number }>}
 */
export function computePhaseHistoricalStats(candles, horizonWeeks = 26) {
  if (candles.length < horizonWeeks + 5) return {};

  const end = analyzeCurrentCycle(candles[candles.length - 1].timestamp).nextHalvingEstimate;
  /** @type {Record<string, { r12: number[], r26: number[] }>} */
  const buckets = {};

  const h12 = 12;
  for (let i = 0; i < candles.length - horizonWeeks; i++) {
    const band = psychologyBandAtTime(candles[i].timestamp, end, candles);
    if (!band) continue;
    const id = band.phase.id;
    if (!buckets[id]) buckets[id] = { r12: [], r26: [] };
    if (i + h12 < candles.length) {
      buckets[id].r12.push(((candles[i + h12].close - candles[i].close) / candles[i].close) * 100);
    }
    buckets[id].r26.push(
      ((candles[i + horizonWeeks].close - candles[i].close) / candles[i].close) * 100
    );
  }

  const med = (arr) => {
    if (!arr.length) return 0;
    const s = [...arr].sort((a, b) => a - b);
    return s[Math.floor(s.length / 2)];
  };

  /** @type {ReturnType<typeof computePhaseHistoricalStats>} */
  const out = {};
  for (const [id, { r12, r26 }] of Object.entries(buckets)) {
    out[id] = {
      sampleWeeks: r26.length,
      forward12wMedianPct: med(r12),
      forward26wMedianPct: med(r26),
      forward26wWinRatePct: r26.length ? (r26.filter((r) => r > 0).length / r26.length) * 100 : 0,
    };
  }
  return out;
}
