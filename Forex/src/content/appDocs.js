/**
 * In-app documentation content — overview, usage, shortcuts, strategies.
 * @module content/appDocs
 */

import { Config } from '../core/Config.js';

/**
 * @typedef {'h2'|'h3'|'p'|'ul'|'ol'|'table'|'code'|'callout'|'steps'} BlockType
 */

/**
 * @typedef {Object} DocBlock
 * @property {BlockType} type
 * @property {string} [text]
 * @property {string[]} [items]
 * @property {string[]} [headers]
 * @property {string[][]} [rows]
 * @property {Array<{ title: string, body: string }>} [steps]
 * @property {'info'|'warn'|'tip'} [variant]
 */

/**
 * @typedef {Object} DocSection
 * @property {string} id
 * @property {string} title
 * @property {string} icon
 * @property {DocBlock[]} blocks
 */

/** @type {DocSection[]} */
export const DOC_SECTIONS = [
  {
    id: 'overview',
    title: 'Overview',
    icon: '🏠',
    blocks: [
      {
        type: 'p',
        text: `${Config.APP_NAME} (PARL) is a frontend-only research platform for Price Action traders. It answers: “Does this setup, on this pair/timeframe, with these parameters, have real edge after spread?” — not “should I trade live right now?”`,
      },
      {
        type: 'callout',
        variant: 'info',
        text: 'All data stays in your browser (IndexedDB + LocalStorage). No backend, no broker connection, no auto-trading.',
      },
      {
        type: 'h3',
        text: 'Problems traders face',
      },
      {
        type: 'ul',
        items: [
          'Unknown which PA setup (B&R, EMA pullback, liquidity grab) actually has edge on real data.',
          'Hindsight bias when reviewing charts manually.',
          'Shallow backtests — signals counted without spread, SL/TP, trailing.',
          'Too many signals — hard to know which deserve a visual review.',
          'Parameter tweaking without walk-forward or Monte Carlo validation.',
          'Fragmented toolchain — data, chart, and Excel in different places.',
        ],
      },
      {
        type: 'h3',
        text: 'How PARL helps',
      },
      {
        type: 'table',
        headers: ['Pain point', 'Module'],
        rows: [
          ['Which setup works?', 'Strategies (bar-by-bar scan) → Simulation (realistic trade engine)'],
          ['Avoid hindsight', 'Chart + Replay; click AI Signals to verify setup at signal time'],
          ['Filter signals', 'AI Signals — 0–100 score, Min score slider'],
          ['Optimize parameters', 'Optimizer — grid search, walk-forward, Monte Carlo'],
          ['Measure results', 'Statistics + Reports — expectancy, PF, drawdown, heatmaps'],
          ['Manage OHLCV', 'Data Manager — local IndexedDB import/export'],
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'Best for: systematic PA research before risking real money. Not a live trading bot.',
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'PARL does NOT: connect to brokers, place live orders, replace a trading journal, or guarantee wins. AI Signals filters display quality only — Simulation still uses all scan signals unless you tighten strategy params.',
      },
      {
        type: 'h3',
        text: 'Supported symbols & timeframes',
      },
      {
        type: 'ul',
        items: [
          `Symbols: ${Config.SYMBOLS.join(', ')} (extensible in Config.js)`,
          `Timeframes: ${Config.TIMEFRAMES.join(', ')}`,
          'Built-in strategies: Break & Retest, EMA Pullback, Liquidity Grab, Session Liquidity Sweep',
        ],
      },
      {
        type: 'h3',
        text: 'Research workflow',
      },
      {
        type: 'steps',
        steps: [
          { title: 'Import data', body: 'Data Manager — CSV/JSON or reload bundled defaults per Symbol+TF.' },
          { title: 'Scan strategies', body: 'Strategies — bar-by-bar signals (entry, SL, TP).' },
          { title: 'Filter & verify', body: 'AI Signals — Min score → click signal → Chart with setup annotations.' },
          { title: 'Simulate trades', body: 'Simulation — spread, slippage, SL/TP, trailing.' },
          { title: 'Analyze results', body: 'Statistics, Reports, Optimizer.' },
        ],
      },
    ],
  },
  {
    id: 'install',
    title: 'Installation',
    icon: '⚡',
    blocks: [
      {
        type: 'h3',
        text: 'Run locally',
      },
      {
        type: 'p',
        text: 'PARL is a static web app. Serve the Forex folder with any HTTP server (ES modules require http://, not file://).',
      },
      {
        type: 'code',
        text: `cd Forex
python3 -m http.server 8080
# Open http://localhost:8080`,
      },
      {
        type: 'h3',
        text: 'Requirements',
      },
      {
        type: 'ul',
        items: [
          'Modern browser (Chrome, Firefox, Edge — ES2023 modules + IndexedDB)',
          'Python 3 or any static file server',
          'No Node.js, npm, or database server needed',
        ],
      },
      {
        type: 'callout',
        variant: 'tip',
        text: 'First launch: go to Data Manager (Ctrl+2) and reload default data or import your OHLCV CSV.',
      },
    ],
  },
  {
    id: 'usage',
    title: 'Usage guide',
    icon: '📖',
    blocks: [
      {
        type: 'h3',
        text: '1. Data Manager (Ctrl+2)',
      },
      {
        type: 'ul',
        items: [
          'Import CSV/JSON or .gz compressed files',
          'Export candles for backup',
          'Reload bundled default data from data/defaults/',
          'View gap detection and candle counts per symbol',
        ],
      },
      {
        type: 'h3',
        text: '2. Chart & Replay (Ctrl+1)',
      },
      {
        type: 'ul',
        items: [
          'Candlestick chart with EMA 20/50 overlays',
          'Replay mode: Play, Pause, Next/Prev candle, Jump to date (UTC)',
          'Replay never shows future candles (no lookahead)',
          'Large datasets: chart renders last 50,000 bars for performance',
        ],
      },
      {
        type: 'h3',
        text: '3. Strategies (Ctrl+3)',
      },
      {
        type: 'ul',
        items: [
          'Select strategy plugin and configure parameters',
          'Run Selected or Run All Enabled strategies',
          'Signals saved locally; export as JSON',
          'Logic follows docs/STRATEGY_SPECIFICATION.md',
        ],
      },
      {
        type: 'h3',
        text: '4. Compare (Ctrl+4)',
      },
      {
        type: 'ul',
        items: [
          'Run multiple strategies on the same symbol/timeframe',
          'Ranks by expectancy using current Simulation trade settings',
          'Tick strategies to include; best row highlighted',
        ],
      },
      {
        type: 'h3',
        text: '5. Simulation (Ctrl+5)',
      },
      {
        type: 'ul',
        items: [
          'Mode 1: one setup, one pair — full trade engine backtest',
          'Configure spread, slippage, lot size, trailing, break-even, partial close',
          'Optional AI score filter — trade only signals ≥ min score',
          'Compare vs all signals — side-by-side baseline vs filtered summary',
          'Results feed Statistics, Reports, and Monte Carlo automatically',
        ],
      },
      {
        type: 'h3',
        text: '6. Statistics (Ctrl+6)',
      },
      {
        type: 'ul',
        items: [
          'Expectancy, profit factor, max drawdown, Sharpe ratio, streaks',
          'Equity curve and drawdown charts',
          'Export statistics JSON',
        ],
      },
      {
        type: 'h3',
        text: '7. Reports (Ctrl+7)',
      },
      {
        type: 'ul',
        items: [
          'Dashboard summary cards and equity curve',
          'Heatmaps by month, day, hour, session, strategy, pair, timeframe',
          'Export: Trades CSV, Report JSON, Dashboard PNG, Print/PDF',
        ],
      },
      {
        type: 'callout',
        variant: 'info',
        text: 'Updated 28 Jun 2025: separate Sensitivity tab; Suggest from data / Restore defaults / Apply best to Strategy; parallel grid (≥4 combos); form persists across tabs; WR/Exp/Net chart for gridded params.',
      },
      {
        type: 'h3',
        text: '8. Optimizer (Ctrl+8)',
      },
      {
        type: 'ul',
        items: [
          'Grid Search — test parameter combinations (max 500 combos); parallel workers when ≥4 combos',
          'Suggest from data — volatility-based grid hints from current candles',
          'Restore defaults — reset parameter grids per strategy',
          'Apply best to Strategy — save rank #1 combo to Strategies',
          'Sensitivity tab — WR / Expectancy / Net Profit chart per gridded parameter',
          'Grid form persists when switching Optimizer tabs (per strategy, current session)',
          'Auto walk-forward on best combo after grid (default on)',
          'Walk Forward — rolling in-sample / out-of-sample validation',
          'Monte Carlo — shuffle trade order for risk distribution (uses last simulation)',
          'Large results stored in IndexedDB (no localStorage quota errors)',
        ],
      },
      {
        type: 'h3',
        text: '9. AI Signals (Ctrl+9)',
      },
      {
        type: 'ul',
        items: [
          'Auto-scored after each strategy scan (0–100)',
          'Factors: trend, momentum, location, volatility, PA quality, RR, session, spread',
          'Filter list by minimum score — use Simulation AI filter to backtest filtered signals only',
        ],
      },
    ],
  },
  {
    id: 'shortcuts',
    title: 'Keyboard shortcuts',
    icon: '⌨️',
    blocks: [
      {
        type: 'table',
        headers: ['Shortcut', 'Action'],
        rows: [
          ['Ctrl+B', 'Toggle sidebar'],
          ['Ctrl+1', 'Chart'],
          ['Ctrl+2', 'Data Manager'],
          ['Ctrl+3', 'Strategies'],
          ['Ctrl+4', 'Compare'],
          ['Ctrl+5', 'Simulation'],
          ['Ctrl+6', 'Statistics'],
          ['Ctrl+7', 'Reports'],
          ['Ctrl+8', 'Optimizer'],
          ['Ctrl+9', 'AI Signals'],
          ['Ctrl+0 / F1', 'Documentation (this page)'],
        ],
      },
      {
        type: 'h3',
        text: 'Chart replay (when Chart view is active)',
      },
      {
        type: 'table',
        headers: ['Key', 'Action'],
        rows: [
          ['Space', 'Play / Pause'],
          ['→', 'Next candle'],
          ['←', 'Previous candle'],
          ['Home', 'Reset replay'],
          ['End', 'Go live (all candles)'],
        ],
      },
    ],
  },
  {
    id: 'strategies',
    title: 'Strategies',
    icon: '⚙️',
    blocks: [
      {
        type: 'p',
        text: 'All strategy logic is defined in docs/STRATEGY_SPECIFICATION.md. Eight built-in Price Action setups:',
      },
      {
        type: 'h3',
        text: 'Break & Retest (break-retest)',
      },
      {
        type: 'p',
        text: 'Trade breakouts that retest the broken swing level. Params: breakoutPips, retestMaxBars, rr, swingLookback.',
      },
      {
        type: 'h3',
        text: 'EMA Pullback (ema-pullback)',
      },
      {
        type: 'p',
        text: 'Enter on pullbacks to EMA in a trending market. Uses EMA20/EMA50 alignment and confirmation candles.',
      },
      {
        type: 'h3',
        text: 'Liquidity Grab (liquidity-grab)',
      },
      {
        type: 'p',
        text: 'Fade false breakouts beyond swing highs/lows (stop hunt). Single-bar entry with wick rejection.',
      },
      {
        type: 'h3',
        text: 'Session Liquidity Sweep (session-liquidity-sweep)',
      },
      {
        type: 'p',
        text: 'Fade session-boundary sweeps (Asian/London/swing levels) during active UTC hours. Two-phase: sweep bar arms pending setup, confirmation bar triggers entry. Params: asianEndHour, londonEndHour, sessionStartHour, sessionEndHour, grabPips, wickRatio, confirmMaxBars, minVolatilityRatio, usePrevAsian, swingLookback, rr. Best researched on EURUSD H1.',
      },
      {
        type: 'h3',
        text: 'Inside Bar Breakout (inside-bar-breakout)',
      },
      {
        type: 'p',
        text: 'Mother bar + inside bar consolidation, then breakout in EMA trend direction. Params: trendEma, motherMinRangePips, breakoutBufferPips, maxWaitBars, rr.',
      },
      {
        type: 'h3',
        text: 'Pin Bar Rejection (pin-bar-rejection)',
      },
      {
        type: 'p',
        text: 'Pin-bar rejection at swing support/resistance (touch zone, no sweep required). Params: swingLookback, retestTolerancePips, minWickRatio, maxBodyRatio, rr.',
      },
      {
        type: 'callout',
        variant: 'warn',
        text: 'PARL researches setups — it does not predict price or auto-trade. Always validate results with walk-forward and Monte Carlo.',
      },
    ],
  },
  {
    id: 'storage',
    title: 'Data & storage',
    icon: '💾',
    blocks: [
      {
        type: 'h3',
        text: 'Where data is saved',
      },
      {
        type: 'table',
        headers: ['Storage', 'Content'],
        rows: [
          ['IndexedDB (parl_data)', 'OHLCV candles + large results (simulation, stats, reports, optimizer, AI scores, compare)'],
          ['LocalStorage', 'Settings, strategy parameter configs, panel sizes'],
        ],
      },
      {
        type: 'h3',
        text: 'CSV import format',
      },
      {
        type: 'code',
        text: 'timestamp,datetime,open,high,low,close,volume',
      },
      {
        type: 'p',
        text: 'Clear browser site data to reset everything. Export important results before clearing.',
      },
    ],
  },
  {
    id: 'faq',
    title: 'FAQ',
    icon: '❓',
    blocks: [
      {
        type: 'h3',
        text: 'No candles on chart?',
      },
      {
        type: 'p',
        text: 'Import or reload default data in Data Manager for your symbol/timeframe, then reload Chart.',
      },
      {
        type: 'h3',
        text: 'Statistics / Reports empty?',
      },
      {
        type: 'p',
        text: 'Run Simulation first (Ctrl+5). Statistics and Reports update automatically when simulation completes.',
      },
      {
        type: 'h3',
        text: 'Monte Carlo says no trades?',
      },
      {
        type: 'p',
        text: 'Monte Carlo uses trades from the last simulation. Run Simulation before Optimizer → Monte Carlo tab.',
      },
      {
        type: 'h3',
        text: 'Grid search too slow?',
      },
      {
        type: 'p',
        text: `Reduce combinations (max ${Config.OPTIMIZER.MAX_COMBINATIONS}). ≥4 combos run in parallel on Web Workers (4 threads) when available.`,
      },
      {
        type: 'h3',
        text: 'Sensitivity tab empty?',
      },
      {
        type: 'p',
        text: 'Run Grid Search first. The chart only shows parameters included in that grid run, with at least two distinct values.',
      },
      {
        type: 'h3',
        text: 'Lost Grid Search inputs when switching tabs?',
      },
      {
        type: 'p',
        text: 'Current builds keep the grid form per strategy while the app stays open. Reloading the page clears it — use Restore defaults to reset grids.',
      },
    ],
  },
];

/**
 * Get a documentation section by ID.
 * @param {string} id
 * @returns {DocSection|undefined}
 */
export function getDocSection(id) {
  return DOC_SECTIONS.find((s) => s.id === id);
}
