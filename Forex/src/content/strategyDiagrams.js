/**
 * Inline strategy diagrams — no external fetch (works with any HTTP root).
 * @module content/strategyDiagrams
 */

/** @type {Record<string, string>} */
export const STRATEGY_DIAGRAMS = {
  'break-retest-long': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 720" role="img" aria-label="Break and Retest Long">
  <rect fill="#0f1419" width="380" height="720" rx="8"/>
  <text x="190" y="28" text-anchor="middle" fill="#e2e8f0" font-size="14" font-weight="700">Break &amp; Retest — LONG</text>
  <rect x="16" y="44" width="348" height="180" rx="6" fill="#151c26" stroke="#2a3548"/>
  <text x="28" y="64" fill="#3b82f6" font-size="11" font-weight="700">1. Swing High (khang cu)</text>
  <line x1="40" y1="120" x2="340" y2="120" stroke="#f59e0b" stroke-width="2" stroke-dasharray="5 4"/>
  <line x1="100" y1="140" x2="100" y2="105" stroke="#8b9cb3" stroke-width="2"/>
  <rect x="92" y="115" width="14" height="20" fill="#ef4444"/>
  <line x1="180" y1="138" x2="180" y2="108" stroke="#8b9cb3" stroke-width="2"/>
  <rect x="172" y="115" width="14" height="18" fill="#ef4444"/>
  <rect x="16" y="240" width="348" height="180" rx="6" fill="#151c26" stroke="#2a3548"/>
  <text x="28" y="260" fill="#3b82f6" font-size="11" font-weight="700">2. Breakout</text>
  <line x1="40" y1="310" x2="340" y2="310" stroke="#f59e0b" stroke-width="2" stroke-dasharray="5 4"/>
  <text x="40" y="302" fill="#94a3b8" font-size="11">close &gt;= level + breakoutPips</text>
  <line x1="160" y1="330" x2="160" y2="285" stroke="#8b9cb3" stroke-width="2"/>
  <rect x="152" y="292" width="14" height="30" fill="#22c55e"/>
  <rect x="16" y="436" width="348" height="200" rx="6" fill="#151c26" stroke="#2a3548"/>
  <text x="28" y="456" fill="#3b82f6" font-size="11" font-weight="700">3. Retest + tin hieu LONG</text>
  <line x1="40" y1="500" x2="340" y2="500" stroke="#f59e0b" stroke-width="2" stroke-dasharray="5 4"/>
  <line x1="160" y1="520" x2="160" y2="485" stroke="#8b9cb3" stroke-width="2"/>
  <rect x="152" y="492" width="14" height="22" fill="#22c55e"/>
  <line x1="50" y1="545" x2="330" y2="545" stroke="#3b82f6" stroke-width="2"/>
  <text x="50" y="562" fill="#3b82f6" font-size="11">Entry = close nen retest</text>
  <line x1="50" y1="575" x2="330" y2="575" stroke="#ef4444" stroke-width="2" stroke-dasharray="4 3"/>
  <text x="50" y="592" fill="#ef4444" font-size="11">SL duoi day retest</text>
  <line x1="50" y1="470" x2="330" y2="470" stroke="#22c55e" stroke-width="2" stroke-dasharray="4 3"/>
  <text x="50" y="487" fill="#22c55e" font-size="11">TP = entry + RR x R</text>
  <text x="190" y="680" text-anchor="middle" fill="#94a3b8" font-size="11">Tin hieu tai nen retest (khong phai nen breakout)</text>
</svg>`,

  'ema-pullback-long': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 720" role="img" aria-label="EMA Pullback Long">
  <rect fill="#0f1419" width="380" height="720" rx="8"/>
  <text x="190" y="28" text-anchor="middle" fill="#e2e8f0" font-size="14" font-weight="700">EMA Pullback — LONG</text>
  <rect x="16" y="44" width="348" height="160" rx="6" fill="#151c26" stroke="#2a3548"/>
  <text x="28" y="64" fill="#3b82f6" font-size="11" font-weight="700">1. Xu huong tang</text>
  <text x="28" y="88" fill="#94a3b8" font-size="11">EMA20 &gt; EMA50, gia tren EMA50</text>
  <path d="M40,150 C120,145 200,138 280,132 340,128" fill="none" stroke="#a855f7" stroke-width="2" stroke-dasharray="5 4"/>
  <path d="M40,165 C120,155 200,142 280,128 340,118" fill="none" stroke="#3b82f6" stroke-width="2.5"/>
  <rect x="16" y="220" width="348" height="200" rx="6" fill="#151c26" stroke="#2a3548"/>
  <text x="28" y="240" fill="#3b82f6" font-size="11" font-weight="700">2. Pullback cham EMA20</text>
  <rect x="40" y="268" width="300" height="36" rx="4" fill="rgba(59,130,246,0.15)" stroke="#3b82f6" stroke-dasharray="4 3"/>
  <line x1="180" y1="318" x2="180" y2="272" stroke="#8b9cb3" stroke-width="2"/>
  <rect x="172" y="280" width="14" height="28" fill="#22c55e"/>
  <rect x="16" y="436" width="348" height="200" rx="6" fill="#151c26" stroke="#2a3548"/>
  <text x="28" y="456" fill="#3b82f6" font-size="11" font-weight="700">3. Entry cung nen pullback</text>
  <text x="28" y="500" fill="#94a3b8" font-size="11">Nen xac nhan tang, close &gt; EMA20</text>
  <text x="28" y="548" fill="#22c55e" font-size="11">Entry = close | SL duoi day | TP theo RR</text>
  <text x="190" y="680" text-anchor="middle" fill="#94a3b8" font-size="11">Low van tren EMA50 — khong pha slow EMA</text>
</svg>`,

  'liquidity-grab-short': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 720" role="img" aria-label="Liquidity Grab Short">
  <rect fill="#0f1419" width="380" height="720" rx="8"/>
  <text x="190" y="28" text-anchor="middle" fill="#e2e8f0" font-size="14" font-weight="700">Liquidity Grab — SHORT</text>
  <rect x="16" y="44" width="348" height="140" rx="6" fill="#151c26" stroke="#2a3548"/>
  <text x="28" y="64" fill="#3b82f6" font-size="11" font-weight="700">1. Swing High</text>
  <line x1="40" y1="110" x2="340" y2="110" stroke="#f59e0b" stroke-width="2" stroke-dasharray="5 4"/>
  <rect x="16" y="200" width="348" height="220" rx="6" fill="#151c26" stroke="#2a3548"/>
  <text x="28" y="220" fill="#3b82f6" font-size="11" font-weight="700">2. Nen grab (1 nen)</text>
  <rect x="40" y="235" width="300" height="55" rx="4" fill="rgba(239,68,68,0.12)"/>
  <line x1="190" y1="235" x2="190" y2="310" stroke="#8b9cb3" stroke-width="2"/>
  <rect x="182" y="278" width="14" height="24" fill="#ef4444"/>
  <text x="28" y="300" fill="#94a3b8" font-size="11">High quet tren level, close &lt; level</text>
  <text x="28" y="316" fill="#94a3b8" font-size="11">Rau tren lon + nen giam xac nhan</text>
  <rect x="16" y="436" width="348" height="180" rx="6" fill="#151c26" stroke="#2a3548"/>
  <text x="28" y="456" fill="#3b82f6" font-size="11" font-weight="700">3. Entry SHORT ngay</text>
  <text x="28" y="480" fill="#ef4444" font-size="11">SL tren dinh grab | TP theo RR</text>
  <text x="190" y="670" text-anchor="middle" fill="#94a3b8" font-size="11">Single-bar — khong cho retest</text>
</svg>`,

  'liquidity-grab-long': `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 720" role="img" aria-label="Liquidity Grab Long">
  <rect fill="#0f1419" width="380" height="720" rx="8"/>
  <text x="190" y="28" text-anchor="middle" fill="#e2e8f0" font-size="14" font-weight="700">Liquidity Grab — LONG</text>
  <rect x="16" y="44" width="348" height="140" rx="6" fill="#151c26" stroke="#2a3548"/>
  <text x="28" y="64" fill="#3b82f6" font-size="11" font-weight="700">1. Swing Low</text>
  <line x1="40" y1="130" x2="340" y2="130" stroke="#f59e0b" stroke-width="2" stroke-dasharray="5 4"/>
  <rect x="16" y="200" width="348" height="220" rx="6" fill="#151c26" stroke="#2a3548"/>
  <text x="28" y="220" fill="#3b82f6" font-size="11" font-weight="700">2. Nen grab (1 nen)</text>
  <rect x="40" y="248" width="300" height="55" rx="4" fill="rgba(34,197,94,0.12)"/>
  <line x1="190" y1="303" x2="190" y2="228" stroke="#8b9cb3" stroke-width="2"/>
  <rect x="182" y="250" width="14" height="22" fill="#22c55e"/>
  <text x="28" y="300" fill="#94a3b8" font-size="11">Low quet duoi level, close &gt; level</text>
  <text x="28" y="316" fill="#94a3b8" font-size="11">Rau duoi lon + nen tang xac nhan</text>
  <rect x="16" y="436" width="348" height="180" rx="6" fill="#151c26" stroke="#2a3548"/>
  <text x="28" y="456" fill="#3b82f6" font-size="11" font-weight="700">3. Entry LONG ngay</text>
  <text x="28" y="480" fill="#22c55e" font-size="11">SL duoi day grab | TP theo RR</text>
  <text x="190" y="670" text-anchor="middle" fill="#94a3b8" font-size="11">Doi xung voi SHORT o swing high</text>
</svg>`,
};

/**
 * @param {string} id
 * @returns {string|null}
 */
export function getStrategyDiagram(id) {
  return STRATEGY_DIAGRAMS[id] ?? null;
}
