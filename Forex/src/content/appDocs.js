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
        text: `${Config.APP_NAME} (PARL) is a frontend-only research platform for Price Action setups. It is NOT a trading bot — use it to discover which setup, pair, timeframe, and parameters perform best.`,
      },
      {
        type: 'callout',
        variant: 'info',
        text: 'All data stays in your browser (IndexedDB + LocalStorage). No backend, no server required.',
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
          'Built-in strategies: Break & Retest, EMA Pullback, Liquidity Grab',
        ],
      },
      {
        type: 'h3',
        text: 'Research workflow',
      },
      {
        type: 'steps',
        steps: [
          { title: 'Import data', body: 'Data Manager — import CSV/JSON or generate sample candles.' },
          { title: 'Scan strategies', body: 'Strategies — run scan to generate signals (bar-by-bar, no lookahead).' },
          { title: 'Simulate trades', body: 'Simulation — backtest with spread, slippage, SL/TP, trailing.' },
          { title: 'Analyze results', body: 'Statistics, Reports, Optimizer, AI Signals.' },
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
        text: 'First launch: go to Data Manager (Ctrl+2) and generate sample data or import your OHLCV CSV.',
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
          'Generate sample data for quick testing',
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
          'Replay mode: Play, Pause, Next/Prev candle, Jump to date',
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
        text: '4. Simulation (Ctrl+4)',
      },
      {
        type: 'ul',
        items: [
          'Mode 1: one setup, one pair — full trade engine backtest',
          'Configure spread, slippage, lot size, trailing, break-even, partial close',
          'Results feed Statistics, Reports, and Monte Carlo automatically',
        ],
      },
      {
        type: 'h3',
        text: '5. Statistics (Ctrl+5)',
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
        text: '6. Reports (Ctrl+6)',
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
        type: 'h3',
        text: '7. Optimizer (Ctrl+7)',
      },
      {
        type: 'ul',
        items: [
          'Grid Search — test parameter combinations (max 500 combos)',
          'Walk Forward — rolling in-sample / out-of-sample validation',
          'Monte Carlo — shuffle trade order for risk distribution (uses last simulation)',
        ],
      },
      {
        type: 'h3',
        text: '8. AI Signals (Ctrl+8)',
      },
      {
        type: 'ul',
        items: [
          'Auto-scored after each strategy scan (0–100)',
          'Factors: trend, momentum, location, volatility, PA quality, RR, session, spread',
          'Filter by minimum score with slider',
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
          ['Ctrl+4', 'Simulation'],
          ['Ctrl+5', 'Statistics'],
          ['Ctrl+6', 'Reports'],
          ['Ctrl+7', 'Optimizer'],
          ['Ctrl+8', 'AI Signals'],
          ['Ctrl+9 / F1', 'Documentation (this page)'],
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
        text: 'All strategy logic is defined in docs/STRATEGY_SPECIFICATION.md. Three built-in Price Action setups:',
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
        text: 'Fade false breakouts beyond swing highs/lows (stop hunt). Requires wick rejection and close back inside range.',
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
          ['IndexedDB (parl_data)', 'OHLCV candle history'],
          ['LocalStorage', 'Settings, strategy params, simulation & statistics results'],
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
        text: 'Import data in Data Manager or generate sample data for your symbol/timeframe, then reload Chart.',
      },
      {
        type: 'h3',
        text: 'Statistics / Reports empty?',
      },
      {
        type: 'p',
        text: 'Run Simulation first (Ctrl+4). Statistics and Reports update automatically when simulation completes.',
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
        text: `Reduce parameter combinations (max ${Config.OPTIMIZER.MAX_COMBINATIONS}). Web Workers activate automatically for large datasets (≥${Config.PERFORMANCE.WORKER_THRESHOLD.toLocaleString()} candles).`,
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
