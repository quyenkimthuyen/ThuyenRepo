/**
 * Historical DCA backtest: blind (fixed) vs phase-aware sizing.
 * @module analysis/DcaBacktestEngine
 */

import { BTC_HALVING_EVENTS } from './BtcCycleConfig.js';
import { analyzeCurrentCycle } from './HalvingCycleAnalyzer.js';
import { psychologyBandAtTime } from './PsychologyBands.js';
import { getPhaseInvestGuide } from './PsychologyInvestGuide.js';
import { TIER_DCA_MULTIPLIER } from './DcaPlanEngine.js';

/**
 * @typedef {import('../data/Candle.js').Candle} Candle
 * @typedef {{
 *   time: number,
 *   usdSpent: number,
 *   btcHeld: number,
 *   totalInvested: number,
 *   portfolioValue: number,
 * }} DcaBacktestPoint
 * @typedef {{
 *   totalInvested: number,
 *   btcHeld: number,
 *   avgCostUsd: number,
 *   finalPrice: number,
 *   finalValueUsd: number,
 *   returnPct: number,
 *   maxDrawdownPct: number,
 *   buyCount: number,
 *   curve: DcaBacktestPoint[],
 * }} DcaBacktestResult
 * @typedef {{
 *   ok: boolean,
 *   reason?: string,
 *   startMs: number,
 *   endMs: number,
 *   monthCount: number,
 *   monthlyBudgetUsd: number,
 *   blind: DcaBacktestResult,
 *   phase: DcaBacktestResult,
 *   edgeUsd: number,
 *   edgeReturnPct: number,
 *   winner: 'phase'|'blind'|'tie',
 * }} DcaBacktestReport
 */

/** Default start: halving #2 (2016). */
export const DEFAULT_DCA_BACKTEST_START = BTC_HALVING_EVENTS[1].timestamp;

/**
 * @param {number} ts
 * @returns {string}
 */
function monthKey(ts) {
  const d = new Date(ts);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth()).padStart(2, '0')}`;
}

/**
 * First weekly candle of each UTC month on/after startMs.
 * @param {Candle[]} candles
 * @param {number} startMs
 * @returns {Candle[]}
 */
export function collectMonthlyBuyCandles(candles, startMs) {
  const seen = new Set();
  /** @type {Candle[]} */
  const buys = [];

  for (const c of candles) {
    if (c.timestamp < startMs) continue;
    const key = monthKey(c.timestamp);
    if (seen.has(key)) continue;
    seen.add(key);
    buys.push(c);
  }

  return buys;
}

/**
 * @param {number} ts
 * @param {Candle[]} candles
 * @returns {number}
 */
export function phaseMultiplierAt(ts, candles) {
  const cycle = analyzeCurrentCycle(ts);
  const band = psychologyBandAtTime(ts, cycle.nextHalvingEstimate, candles);
  const phaseId = band?.phase?.id;
  if (!phaseId) return 1;
  const tier = getPhaseInvestGuide(phaseId)?.tier ?? 'moderate';
  return TIER_DCA_MULTIPLIER[tier] ?? 0.75;
}

/**
 * @param {Candle[]} buyCandles
 * @param {Candle[]} allCandles
 * @param {'blind'|'phase'} mode
 * @param {number} monthlyBudgetUsd
 * @returns {DcaBacktestResult}
 */
export function simulateDcaPath(buyCandles, allCandles, mode, monthlyBudgetUsd) {
  let btcHeld = 0;
  let totalInvested = 0;
  let peakValue = 0;
  let maxDrawdownPct = 0;
  /** @type {DcaBacktestPoint[]} */
  const curve = [];

  for (const c of buyCandles) {
    const mult = mode === 'blind' ? 1 : phaseMultiplierAt(c.timestamp, allCandles);
    const usdSpent = monthlyBudgetUsd * mult;
    if (usdSpent > 0) {
      btcHeld += usdSpent / c.close;
      totalInvested += usdSpent;
    }
    const portfolioValue = btcHeld * c.close;
    peakValue = Math.max(peakValue, portfolioValue);
    if (peakValue > 0) {
      const dd = ((portfolioValue - peakValue) / peakValue) * 100;
      maxDrawdownPct = Math.min(maxDrawdownPct, dd);
    }
    curve.push({
      time: c.timestamp,
      usdSpent,
      btcHeld,
      totalInvested,
      portfolioValue,
    });
  }

  const last = buyCandles[buyCandles.length - 1];
  const finalPrice = last.close;
  const finalValueUsd = btcHeld * finalPrice;
  const returnPct = totalInvested > 0
    ? ((finalValueUsd - totalInvested) / totalInvested) * 100
    : 0;

  return {
    totalInvested,
    btcHeld,
    avgCostUsd: btcHeld > 0 ? totalInvested / btcHeld : 0,
    finalPrice,
    finalValueUsd,
    returnPct,
    maxDrawdownPct,
    buyCount: curve.filter((p) => p.usdSpent > 0).length,
    curve,
  };
}

/**
 * @param {Candle[]} candles — weekly BTCUSD recommended
 * @param {{ monthlyBudgetUsd?: number, startMs?: number }} [options]
 * @returns {DcaBacktestReport}
 */
export function runDcaBacktest(candles, options = {}) {
  const monthlyBudgetUsd = Math.max(0, options.monthlyBudgetUsd ?? 500);
  const startMs = options.startMs ?? DEFAULT_DCA_BACKTEST_START;
  const buyCandles = collectMonthlyBuyCandles(candles, startMs);

  if (buyCandles.length < 3) {
    return {
      ok: false,
      reason: 'Kh\u00f4ng \u0111\u1ee7 d\u1eef li\u1ec7u n\u1ebfn (c\u1ea7n BTCUSD W t\u1eeb 2016).',
      startMs,
      endMs: 0,
      monthCount: 0,
      monthlyBudgetUsd,
      blind: emptyResult(),
      phase: emptyResult(),
      edgeUsd: 0,
      edgeReturnPct: 0,
      winner: 'tie',
    };
  }

  const blind = simulateDcaPath(buyCandles, candles, 'blind', monthlyBudgetUsd);
  const phase = simulateDcaPath(buyCandles, candles, 'phase', monthlyBudgetUsd);
  const edgeUsd = phase.finalValueUsd - blind.finalValueUsd;
  const edgeReturnPct = phase.returnPct - blind.returnPct;
  let winner = 'tie';
  if (edgeUsd > 1) winner = 'phase';
  else if (edgeUsd < -1) winner = 'blind';

  return {
    ok: true,
    startMs,
    endMs: buyCandles[buyCandles.length - 1].timestamp,
    monthCount: buyCandles.length,
    monthlyBudgetUsd,
    blind,
    phase,
    edgeUsd,
    edgeReturnPct,
    winner,
  };
}

/** @returns {DcaBacktestResult} */
function emptyResult() {
  return {
    totalInvested: 0,
    btcHeld: 0,
    avgCostUsd: 0,
    finalPrice: 0,
    finalValueUsd: 0,
    returnPct: 0,
    maxDrawdownPct: 0,
    buyCount: 0,
    curve: [],
  };
}
