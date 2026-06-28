/**
 * Abstract base class for all Price Action strategy plugins.
 * Every strategy must extend this and implement the lifecycle methods.
 * @module strategy/BaseStrategy
 */

import { applyDefaults, validateParams } from './ParameterSchema.js';
import { isValidSignal } from './Signal.js';
import { createLogger } from '../utils/logger.js';

/**
 * @typedef {import('./ParameterSchema.js').ParamDefinition} ParamDefinition
 * @typedef {import('./Signal.js').Signal} Signal
 * @typedef {import('./StrategyContext.js').StrategyContext} StrategyContext
 * @typedef {import('../data/Candle.js').Candle} Candle
 */

/**
 * Base strategy plugin — implement initialize, calculate, generateSignal, validate.
 */
export class BaseStrategy {
  /** @type {string} Unique plugin identifier */
  static id = 'base';

  /** @type {string} Display name */
  static name = 'Base Strategy';

  /** @type {string} */
  static description = '';

  /** @type {string} */
  static version = '1.0.0';

  /** @type {string} */
  static category = 'Price Action';

  /** @type {Record<string, unknown>} */
  #params = {};

  /** @type {Record<string, unknown>} */
  #state = {};

  /** @type {ReturnType<typeof createLogger>} */
  #log = createLogger(this.constructor.name);

  /**
   * Return the parameter schema for this strategy.
   * @returns {ParamDefinition[]}
   */
  getParameterSchema() {
    return [];
  }

  /**
   * Minimum bars required before generating signals.
   * @returns {number}
   */
  getWarmupBars() {
    return 50;
  }

  /**
   * Initialize strategy with user parameters.
   * @param {Record<string, unknown>} params
   */
  initialize(params = {}) {
    const schema = this.getParameterSchema();
    this.#params = applyDefaults(schema, params);

    const { valid, errors } = validateParams(schema, this.#params);
    if (!valid) {
      throw new Error(`Invalid parameters: ${errors.join('; ')}`);
    }

    this.#state = {};
    this.onInitialize();
    this.#log.info('Initialized', this.#params);
  }

  /**
   * Set symbol/timeframe for the current scan run.
   * @param {{ symbol: string, timeframe: string }} ctx
   */
  setRunContext(ctx) {
    this._setState('symbol', ctx.symbol);
    this._setState('timeframe', ctx.timeframe);
  }

  /**
   * Hook for subclasses after parameter validation.
   */
  onInitialize() {}

  /**
   * Update internal state using only data up to index (no lookahead).
   * @param {Candle[]} candles
   * @param {number} index
   */
  calculate(candles, index) {
    // Subclasses override to maintain rolling state
  }

  /**
   * Attempt to generate a signal at the current bar.
   * @param {StrategyContext} ctx
   * @returns {Signal|null}
   */
  generateSignal(ctx) {
    return null;
  }

  /**
   * Validate a generated signal meets strategy-specific rules.
   * @param {Signal} signal
   * @returns {boolean}
   */
  validate(signal) {
    return isValidSignal(signal);
  }

  /**
   * Get current parameters.
   * @returns {Record<string, unknown>}
   */
  getParams() {
    return { ...this.#params };
  }

  /**
   * Get internal state (for debugging).
   * @returns {Record<string, unknown>}
   */
  getState() {
    return { ...this.#state };
  }

  /**
   * @protected
   * @param {string} key
   * @param {unknown} value
   */
  _setState(key, value) {
    this.#state[key] = value;
  }

  /**
   * @protected
   * @param {string} key
   * @returns {unknown}
   */
  _getState(key) {
    return this.#state[key];
  }

  /**
   * @protected
   * @param {string} key
   * @returns {unknown}
   */
  _getParam(key) {
    return this.#params[key];
  }

  /**
   * Return plugin metadata for the registry.
   * @returns {Object}
   */
  getMetadata() {
    const Ctor = /** @type {typeof BaseStrategy} */ (this.constructor);
    return {
      id: Ctor.id,
      name: Ctor.name,
      description: Ctor.description,
      version: Ctor.version,
      category: Ctor.category,
      warmupBars: this.getWarmupBars(),
      parameters: this.getParameterSchema(),
    };
  }
}
