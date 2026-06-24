/**
 * Lightweight publish/subscribe event bus for decoupled module communication.
 * @module core/EventBus
 */

/**
 * Central event dispatcher used across all modules.
 */
export class EventBus {
  /** @type {Map<string, Set<Function>>} */
  #listeners = new Map();

  /**
   * Subscribe to an event.
   * @param {string} event - Event name
   * @param {Function} callback - Handler function
   * @returns {Function} Unsubscribe function
   */
  on(event, callback) {
    if (!this.#listeners.has(event)) {
      this.#listeners.set(event, new Set());
    }
    this.#listeners.get(event).add(callback);
    return () => this.off(event, callback);
  }

  /**
   * Subscribe to an event once.
   * @param {string} event - Event name
   * @param {Function} callback - Handler function
   */
  once(event, callback) {
    const wrapper = (...args) => {
      this.off(event, wrapper);
      callback(...args);
    };
    this.on(event, wrapper);
  }

  /**
   * Unsubscribe from an event.
   * @param {string} event - Event name
   * @param {Function} callback - Handler to remove
   */
  off(event, callback) {
    const set = this.#listeners.get(event);
    if (set) {
      set.delete(callback);
      if (set.size === 0) {
        this.#listeners.delete(event);
      }
    }
  }

  /**
   * Emit an event to all subscribers.
   * @param {string} event - Event name
   * @param {unknown} [payload] - Event data
   */
  emit(event, payload) {
    const set = this.#listeners.get(event);
    if (!set) return;
    for (const callback of set) {
      try {
        callback(payload);
      } catch (err) {
        console.error(`[EventBus] Error in handler for "${event}":`, err);
      }
    }
  }

  /**
   * Remove all listeners for a given event, or all events.
   * @param {string} [event] - Optional event name
   */
  clear(event) {
    if (event) {
      this.#listeners.delete(event);
    } else {
      this.#listeners.clear();
    }
  }
}

/** Application-wide singleton event bus. */
export const bus = new EventBus();

/** Well-known event names used across the application. */
export const Events = Object.freeze({
  APP_READY: 'app:ready',
  APP_ERROR: 'app:error',
  APP_DATA_RESET: 'app:data:reset',
  MODULE_LOADED: 'module:loaded',
  MODULE_ERROR: 'module:error',
  NAVIGATE: 'ui:navigate',
  VIEW_ACTIVE: 'ui:view:active',
  PANEL_RESIZE: 'ui:panel:resize',
  SIDEBAR_TOGGLE: 'ui:sidebar:toggle',
  THEME_CHANGE: 'ui:theme:change',
  SETTINGS_CHANGE: 'settings:change',
  DATA_UPDATED: 'data:updated',
  DATA_IMPORTED: 'data:imported',
  DATA_EXPORTED: 'data:exported',
  DATA_ERROR: 'data:error',
  LOG_MESSAGE: 'ui:log',
  CHART_LOAD: 'chart:load',
  CHART_LOADED: 'chart:loaded',
  CHART_SIGNAL_REVIEW: 'chart:signal:review',
  REPLAY_TICK: 'replay:tick',
  REPLAY_STATE: 'replay:state',
  REPLAY_COMMAND: 'replay:command',
  STRATEGY_REGISTERED: 'strategy:registered',
  STRATEGY_RUN: 'strategy:run',
  STRATEGY_PARAMS_CHANGED: 'strategy:params:changed',
  SIGNALS_GENERATED: 'signals:generated',
  SIMULATION_RUN: 'simulation:run',
  SIMULATION_COMPLETE: 'simulation:complete',
  TRADE_CLOSED: 'trade:closed',
  STATISTICS_COMPUTED: 'statistics:computed',
  REPORT_GENERATED: 'report:generated',
  OPTIMIZATION_COMPLETE: 'optimization:complete',
  WALK_FORWARD_COMPLETE: 'walkforward:complete',
  MONTE_CARLO_COMPLETE: 'montecarlo:complete',
  SIGNALS_SCORED: 'signals:scored',
  DOCS_OPEN: 'docs:open',
});
