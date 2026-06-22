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
  APP_VERSION: '0.1.0',
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
  }),

  /** IndexedDB database name (used in Phase 2). */
  DB_NAME: 'parl_data',
  DB_VERSION: 1,

  /** Performance targets. */
  TARGET_FPS: 60,

  /** Default risk-reward ratios for future optimization. */
  DEFAULT_RR_OPTIONS: Object.freeze([1, 1.5, 2, 2.5, 3, 4, 5]),
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
