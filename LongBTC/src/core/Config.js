/**
 * Application-wide configuration.
 * All magic numbers and defaults live here — never hardcode in other modules.
 * @module core/Config
 */

/** @typedef {'BTCUSD'} Symbol */
/** @typedef {'H1'|'H4'|'D1'|'W'} Timeframe */

/**
 * Immutable application configuration object.
 */
export const Config = Object.freeze({
  APP_NAME: 'BTC Long-Term Research Lab',
  APP_VERSION: '2.0.0',
  APP_SHORT_NAME: 'LongBTC',

  /** Primary research symbol. */
  SYMBOLS: Object.freeze(['BTCUSD']),

  /** Long-term analysis timeframes. */
  TIMEFRAMES: Object.freeze(['W', 'D1', 'H4']),

  /** Default symbol and timeframe on first launch. */
  DEFAULT_SYMBOL: 'BTCUSD',
  DEFAULT_TIMEFRAME: 'W',

  /** UI layout dimensions (pixels). */
  LAYOUT: Object.freeze({
    TOPBAR_HEIGHT: 40,
    SIDEBAR_WIDTH: 220,
    SIDEBAR_COLLAPSED_WIDTH: 52,
    STATUSBAR_HEIGHT: 28,
    PANEL_MIN_WIDTH: 200,
    PANEL_MIN_HEIGHT: 150,
    RESIZE_HANDLE_SIZE: 4,
  }),

  /** LocalStorage keys for persistence. */
  STORAGE_KEYS: Object.freeze({
    WORKSPACE: 'longbtc_workspace',
    SETTINGS: 'longbtc_settings',
    SIDEBAR_COLLAPSED: 'longbtc_sidebar_collapsed',
    PANEL_SIZES: 'longbtc_panel_sizes',
    STRATEGIES: 'parl_strategies',
    STRATEGY_RESULTS: 'parl_strategy_results',
    SIMULATION_CONFIG: 'parl_simulation_config',
    SIMULATION_RESULTS: 'parl_simulation_results',
    STATISTICS_RESULTS: 'parl_statistics_results',
    REPORT_RESULTS: 'parl_report_results',
    RESEARCH_RESULTS: 'parl_research_results',
    SCORED_SIGNALS: 'parl_scored_signals',
    SCORING_WEIGHTS: 'parl_scoring_weights',
    STRATEGY_COMPARE: 'parl_strategy_compare',
  }),

  /** IndexedDB database name and schema version. */
  DB_NAME: 'longbtc_data',
  DB_VERSION: 2,

  /** IndexedDB object store names. */
  DB_STORES: Object.freeze({
    CANDLES: 'candles',
    METADATA: 'metadata',
    RESULTS: 'results',
  }),

  /** Batch size for IndexedDB bulk writes. */
  DB_BATCH_SIZE: 5000,

  /** Milliseconds per timeframe (extensible). */
  TIMEFRAME_MS: Object.freeze({
    M15: 15 * 60 * 1000,
    M30: 30 * 60 * 1000,
    H1: 60 * 60 * 1000,
    H4: 4 * 60 * 60 * 1000,
    D1: 24 * 60 * 60 * 1000,
    W: 7 * 24 * 60 * 60 * 1000,
  }),

  /** Live BTC price source (Binance public API, BTCUSDT as BTCUSD proxy). */
  BTC_LIVE: Object.freeze({
    BINANCE_API: 'https://api.binance.com/api/v3',
    SYMBOL: 'BTCUSDT',
  }),

  /** Default sample data size for demo generation. */
  SAMPLE_CANDLE_COUNT: 2000,

  /** Performance targets. */
  TARGET_FPS: 60,

  /** Default risk-reward ratios for future optimization. */
  DEFAULT_RR_OPTIONS: Object.freeze([1, 1.5, 2, 2.5, 3, 4, 5]),

  /** Chart rendering options. */
  CHART: Object.freeze({
    DEFAULT_VISIBLE_BARS: 150,
    EMA_PERIODS: Object.freeze([200]),
    PRICE_PRECISION: 2,
    MIN_MOVE: 0.01,
    /** Vertical gap between candles and chart top/bottom (fraction of pane). */
    PRICE_SCALE_MARGINS: Object.freeze({ top: 0.1, bottom: 0.1 }),
    /** Extra padding when signal levels + axis labels are shown. */
    SIGNAL_PRICE_SCALE_MARGINS: Object.freeze({ top: 0.18, bottom: 0.18 }),
    PRICE_SCALE_MIN_WIDTH: 80,
    SIGNAL_PRICE_SCALE_MIN_WIDTH: 100,
    TIME_RIGHT_OFFSET: 10,
    SIGNAL_TIME_RIGHT_OFFSET: 18,
    /** Expand autoscale range beyond candles + overlay prices. */
    SIGNAL_AUTOSCALE_PADDING_RATIO: 0.12,
  }),

  /** Replay engine options. */
  REPLAY: Object.freeze({
    LOOKBACK_BARS: 50,
    BASE_INTERVAL_MS: 500,
    SPEED_NORMAL: 1,
    SPEED_FAST: 4,
    SPEED_ULTRA: 16,
  }),

  /** Strategy engine defaults. */
  STRATEGY: Object.freeze({
    MIN_WARMUP_BARS: 50,
    DEFAULT_RR: 2,
    DEFAULT_CONFIDENCE: 50,
  }),

  /** Trade simulation defaults. */
  SIMULATION: Object.freeze({
    SPREAD_PIPS: 1.5,
    SLIPPAGE_PIPS: 0.5,
    COMMISSION_PER_LOT: 7,
    DEFAULT_LOT_SIZE: 0.1,
    PIP_VALUE_PER_LOT: 10,
    MAX_BARS_IN_TRADE: 200,
    PENDING_MAX_BARS: 10,
    TRAILING_STOP_PIPS: 0,
    BREAK_EVEN_AT_R: 0,
    PARTIAL_CLOSE_AT_R: 0,
    PARTIAL_CLOSE_PERCENT: 50,
    INITIAL_BALANCE: 10000,
    DEFAULT_MIN_AI_SCORE: 65,
  }),

  /** Research optimizer defaults. */
  OPTIMIZER: Object.freeze({
    MAX_COMBINATIONS: 500,
    DEFAULT_RANK_METRIC: 'expectancy',
    MONTE_CARLO_ITERATIONS: 1000,
    WALK_FORWARD_FOLDS: 5,
    IN_SAMPLE_RATIO: 0.7,
    OOS_RATIO: 0.15,
    STEP_RATIO: 0.1,
    /** Max grid rows persisted to IndexedDB (stats only, no trades/signals). */
    PERSIST_GRID_TOP: 100,
    /** Run walk-forward on best grid combo by default. */
    AUTO_WALK_FORWARD_AFTER_GRID: true,
  }),

  /** AI signal scoring factor weights (must sum to 1.0). */
  SCORING: Object.freeze({
    WEIGHTS: Object.freeze({
      trend: 0.15,
      momentum: 0.12,
      location: 0.13,
      volatility: 0.10,
      priceActionQuality: 0.15,
      rr: 0.12,
      session: 0.13,
      spread: 0.10,
    }),
  }),

  /** Long-term BTC analysis defaults. */
  ANALYSIS: Object.freeze({
    DEFAULT_SYMBOL: 'BTCUSD',
    PREFERRED_TIMEFRAMES: Object.freeze(['W', 'D1']),
    SWING_REVERSAL_PCT: Object.freeze({ W: 0.12, D1: 0.08, H4: 0.05 }),
  }),

  /** Performance optimization settings. */
  PERFORMANCE: Object.freeze({
    MAX_CHART_RENDER_BARS: 50000,
    WORKER_THRESHOLD: 10000,
    WORKER_POOL_SIZE: 4,
    /** Min grid combos before dispatching parallel worker chunks. */
    GRID_PARALLEL_MIN_COMBOS: 4,
  }),
});

/**
 * Returns a deep-cloned user settings object with defaults applied.
 * @returns {Record<string, unknown>}
 */
export function getDefaultSettings() {
  return {
    theme: 'dark',
    symbol: Config.DEFAULT_SYMBOL,
    timeframe: Config.DEFAULT_TIMEFRAME,
    sidebarCollapsed: false,
    panelSizes: {
      left: 280,
      bottom: 200,
    },
  };
}
