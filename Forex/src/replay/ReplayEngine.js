/**
 * Candle-by-candle replay engine.
 * Never exposes future candles beyond the current index.
 * @module replay/ReplayEngine
 */

import { Config } from '../core/Config.js';
import { createLogger } from '../utils/logger.js';

const log = createLogger('ReplayEngine');

/**
 * @typedef {'live'|'replay'} ReplayMode
 * @typedef {'idle'|'playing'|'paused'} ReplayStatus
 */

/**
 * @typedef {Object} ReplayState
 * @property {ReplayMode} mode
 * @property {ReplayStatus} status
 * @property {number} index - Current visible candle index (inclusive)
 * @property {number} total
 * @property {number} speed
 */

/**
 * Controls candle-by-candle replay without lookahead bias.
 */
export class ReplayEngine {
  /** @type {import('../data/Candle.js').Candle[]} */
  #candles = [];

  /** @type {number} */
  #index = 0;

  /** @type {ReplayMode} */
  #mode = 'live';

  /** @type {ReplayStatus} */
  #status = 'idle';

  /** @type {number} */
  #speed = Config.REPLAY.SPEED_NORMAL;

  /** @type {ReturnType<typeof setInterval>|null} */
  #timer = null;

  /** @type {Function|null} */
  #onTick = null;

  /** @type {Function|null} */
  #onStateChange = null;

  /**
   * Register tick callback — fired on each candle step.
   * @param {Function} callback
   */
  onTick(callback) {
    this.#onTick = callback;
  }

  /**
   * Register state change callback.
   * @param {Function} callback
   */
  onStateChange(callback) {
    this.#onStateChange = callback;
  }

  /**
   * Load candle data. Defaults to live mode showing all candles.
   * @param {import('../data/Candle.js').Candle[]} candles
   */
  load(candles) {
    this.stop();
    this.#candles = candles;
    this.#mode = 'live';
    this.#status = 'idle';
    this.#index = candles.length > 0 ? candles.length - 1 : 0;
    this.#emitState();
    log.info(`Loaded ${candles.length} candles`);
  }

  /**
   * Get candles visible at the current replay position.
   * In live mode, returns all candles.
   * @returns {import('../data/Candle.js').Candle[]}
   */
  getVisibleCandles() {
    if (this.#candles.length === 0) return [];
    if (this.#mode === 'live') return this.#candles;
    return this.#candles.slice(0, this.#index + 1);
  }

  /**
   * @returns {import('../data/Candle.js').Candle|undefined}
   */
  getCurrentCandle() {
    return this.#candles[this.#index];
  }

  /**
   * @returns {ReplayState}
   */
  getState() {
    return {
      mode: this.#mode,
      status: this.#status,
      index: this.#index,
      total: this.#candles.length,
      speed: this.#speed,
    };
  }

  /**
   * Switch to live mode — reveal all candles.
   */
  goLive() {
    this.stop();
    this.#mode = 'live';
    this.#index = this.#candles.length - 1;
    this.#status = 'idle';
    this.#emitState();
    this.#emitTick(true);
  }

  /**
   * Enter replay mode at the lookback starting point.
   */
  resetReplay() {
    this.stop();
    this.#mode = 'replay';
    this.#index = Math.min(
      Config.REPLAY.LOOKBACK_BARS,
      Math.max(0, this.#candles.length - 1)
    );
    this.#status = 'paused';
    this.#emitState();
    this.#emitTick(true);
  }

  /**
   * Start auto-play at the current speed.
   */
  play() {
    if (this.#candles.length === 0) return;

    if (this.#mode === 'live') {
      this.resetReplay();
    }

    if (this.#index >= this.#candles.length - 1) {
      this.resetReplay();
    }

    this.#status = 'playing';
    this.#emitState();
    this.#startTimer();
  }

  /** Pause auto-play. */
  pause() {
    this.#status = 'paused';
    this.#stopTimer();
    this.#emitState();
  }

  /** Stop playback and reset timer. */
  stop() {
    this.#status = 'idle';
    this.#stopTimer();
  }

  /**
   * Advance one candle. Returns false if at end.
   * @returns {boolean}
   */
  next() {
    if (this.#mode === 'live') {
      this.resetReplay();
    }

    if (this.#index >= this.#candles.length - 1) {
      this.pause();
      return false;
    }

    this.#index++;
    this.#emitState();
    this.#emitTick();
    return true;
  }

  /**
   * Step back one candle. Returns false if at start.
   * @returns {boolean}
   */
  prev() {
    if (this.#mode === 'live') {
      this.#mode = 'replay';
      this.#index = this.#candles.length - 1;
    }

    if (this.#index <= 0) return false;

    this.#index--;
    this.#status = 'paused';
    this.#stopTimer();
    this.#emitState();
    this.#emitTick(true);
    return true;
  }

  /**
   * Set playback speed multiplier.
   * @param {number} speed
   */
  setSpeed(speed) {
    this.#speed = speed;
    if (this.#status === 'playing') {
      this.#stopTimer();
      this.#startTimer();
    }
    this.#emitState();
  }

  /**
   * Jump to a specific date — only reveals candles up to that point.
   * @param {number} timestamp - Epoch milliseconds
   */
  jumpToDate(timestamp) {
    this.pause();

    if (this.#candles.length === 0) return;

    let targetIndex = 0;
    for (let i = 0; i < this.#candles.length; i++) {
      if (this.#candles[i].timestamp <= timestamp) {
        targetIndex = i;
      } else {
        break;
      }
    }

    this.#mode = 'replay';
    this.#index = targetIndex;
    this.#emitState();
    this.#emitTick(true);
  }

  #startTimer() {
    this.#stopTimer();
    const interval = Config.REPLAY.BASE_INTERVAL_MS / this.#speed;

    this.#timer = setInterval(() => {
      if (!this.next()) {
        this.pause();
      }
    }, interval);
  }

  #stopTimer() {
    if (this.#timer !== null) {
      clearInterval(this.#timer);
      this.#timer = null;
    }
  }

  /**
   * @param {boolean} [fullRefresh=false] - Force full data reset (for rewind)
   */
  #emitTick(fullRefresh = false) {
    this.#onTick?.({
      candle: this.getCurrentCandle(),
      visible: this.getVisibleCandles(),
      index: this.#index,
      total: this.#candles.length,
      fullRefresh,
    });
  }

  #emitState() {
    this.#onStateChange?.(this.getState());
  }

  /** Release resources. */
  destroy() {
    this.stop();
    this.#candles = [];
    this.#onTick = null;
    this.#onStateChange = null;
  }
}
