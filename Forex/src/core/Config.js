/**
 * Application-wide configuration.
 * All magic numbers and defaults live here — never hardcode in other modules.
 * @module core/Config
 */

/** @typedef {'EURUSD'|'GBPUSD'} Symbol */
/** @typedef {'H1'} Timeframe */

/**
 * Immutable application configuration object.
 */
export const Config = Object.freeze({
  APP_NAME: 'Price Action Research Lab',
  APP_VERSION: '0.4.0',
  APP_SHORT_NAME: 'PARL',

  /** Supported trading symbols (extensible). */
  SYMBOLS: Object.freeze(['EURUSD', 'GBPUSD']),

  /** Supported timeframes (extensible). */
  TIMEFRAMES: Object.freeze(['H1']),

  /** Default symbol and timeframe on first launch. */
  DEFAULT_SYMBOL: 'EURUSD',
  DEFAULT_TIMEFRAME: 'H1',

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
    WORKSPACE: 'parl_workspace',
    SETTINGS: 'parl_settings',
    SIDEBAR_COLLAPSED: 'parl_sidebar_collapsed',
    PANEL_SIZES: 'parl_panel_sizes',
    STRATEGIES: 'parl_strategies',
    STRATEGY_RESULTS: 'parl_strategy_results',
  }),

  /** IndexedDB database name and schema version. */
  DB_NAME: 'parl_data',
  DB_VERSION: 1,

  /** IndexedDB object store names. */
  DB_STORES: Object.freeze({
    CANDLES: 'candles',
    METADATA: 'metadata',
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
    EMA_PERIODS: Object.freeze([20, 50]),
    PRICE_PRECISION: 5,
    MIN_MOVE: 0.00001,
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
